import pytest
from fastapi.testclient import TestClient

from analytics.data import Cohort, load_cohort
from analytics.ml import SearchMode, TrainingConfig, save, train_cohort
from analytics.preprocessing import prepare_cohort
from app.core.config import Settings, get_settings
from app.main import create_app
from tests.factories import VALID_ROW, make_varied_rows, write_cohort

CONFIG = TrainingConfig(cv_folds=3, search=SearchMode.MINIMAL, n_jobs=1)


@pytest.fixture(scope="module")
def models_dir(tmp_path_factory):
    raw = tmp_path_factory.mktemp("raw")
    write_cohort(raw / "student-mat.csv", make_varied_rows(150, seed=21))
    write_cohort(raw / "student-por.csv", make_varied_rows(160, seed=22))
    trained = [train_cohort(prepare_cohort(load_cohort(raw, c)), CONFIG) for c in Cohort]
    directory = tmp_path_factory.mktemp("models")
    save(trained, CONFIG, directory)
    return directory


@pytest.fixture
def api(tmp_path, models_dir) -> TestClient:
    settings = Settings(environment="test", data_dir=tmp_path / "data", models_dir=models_dir)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _features(*grades: str) -> dict:
    record = {k: v for k, v in VALID_ROW.items() if k not in {"G1", "G2", "G3"}}
    return {**record, **{g: VALID_ROW[g] for g in grades}}


def test_catalog_lists_models_and_selected(api):
    body = api.get("/api/v1/models").json()

    assert body["trained"] is True
    assert body["run"]["random_state"] == 42 and body["run"]["cv_folds"] == 3
    keys = {(m["task"], m["key"]) for m in body["models"]}
    assert ("classification", "svm") in keys and ("regression", "mean_baseline") in keys
    assert len(body["selected"]) == 12


def test_catalog_without_training_still_describes_models(client):
    body = client.get("/api/v1/models").json()
    assert body["trained"] is False and body["selected"] == [] and len(body["models"]) == 10


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/models/regression?cohort=math",
        "/api/v1/models/classification?cohort=math",
        "/api/v1/models/scenario-comparison?cohort=math&task=regression",
        "/api/v1/models/cohort-comparison",
        "/api/v1/models/selected?cohort=math&task=regression&scenario=early",
    ],
)
def test_results_endpoints_report_untrained_state(client, path):
    response = client.get(path)
    assert response.status_code == 503
    assert response.json()["code"] == "models_unavailable"
    assert "analytics.ml.train" in response.json()["detail"]


@pytest.mark.parametrize("cohort", ["math", "portuguese"])
def test_regression_and_classification_tables(api, cohort):
    reg = api.get("/api/v1/models/regression", params={"cohort": cohort}).json()
    cls = api.get("/api/v1/models/classification", params={"cohort": cohort}).json()

    assert reg["cohort"] == cls["cohort"] == cohort
    assert len(reg["rows"]) == 12 and len(cls["rows"]) == 18
    assert {"cv_rmse", "test_r2"} <= set(reg["rows"][0]) and "cv_f1" not in reg["rows"][0]
    assert {"cv_roc_auc", "test_recall", "test_balanced_accuracy"} <= set(cls["rows"][0])
    assert "test_rmse" not in cls["rows"][0]
    assert sum(r["selected"] for r in reg["rows"]) == 3
    assert sum(r["selected"] for r in cls["rows"]) == 3


def test_scenario_and_cohort_comparisons(api):
    scenarios = api.get(
        "/api/v1/models/scenario-comparison",
        params={"cohort": "portuguese", "task": "classification"},
    ).json()
    cohorts = api.get("/api/v1/models/cohort-comparison").json()

    assert [r["scenario"] for r in scenarios["rows"]] == ["early", "mid_year", "full_history"]
    assert scenarios["primary_metric"] == "f1"
    assert "not predict dropout" in scenarios["note"]
    assert [c["cohort"] for c in cohorts["cohorts"]] == ["math", "portuguese"]
    assert cohorts["cohorts"][0]["n"] == 150 and len(cohorts["cohorts"][0]["selected"]) == 6


def test_evaluations_and_selected_detail(api):
    params = {"cohort": "math", "task": "classification", "scenario": "mid_year"}
    evaluations = api.get("/api/v1/models/evaluations", params=params).json()
    detail = api.get("/api/v1/models/selected", params=params).json()

    assert len(evaluations) == 6
    assert all(len(e["cv"]["f1"]["folds"]) == 3 for e in evaluations)
    assert detail["metadata"]["feature_columns"][-1] == "G1"
    assert detail["metadata"]["model"] == detail["selection"]["model"]
    assert detail["classification_errors"]["confusion"] is not None
    assert detail["regression_errors"] is None


def test_predict_endpoint(api):
    body = {
        "cohort": "math",
        "task": "classification",
        "scenario": "full_history",
        "features": _features("G1", "G2"),
    }
    response = api.post("/api/v1/models/predict", json=body)

    assert response.status_code == 200
    out = response.json()
    assert isinstance(out["at_risk"], bool) and out["predicted_grade"] is None
    assert out["scenario"] == "full_history"


@pytest.mark.parametrize(
    ("features", "fragment"),
    [
        ({**_features(), "G3": 12}, "Outcome"),
        ({**_features("G1")}, "not available"),
        ({**_features(), "sex": "X"}, "sex"),
    ],
)
def test_predict_rejects_invalid_records(api, features, fragment):
    body = {"cohort": "math", "task": "regression", "scenario": "early", "features": features}
    response = api.post("/api/v1/models/predict", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_record"
    assert fragment in response.json()["detail"]


def test_predict_rejects_unknown_task_and_unpersisted_models(api):
    bad = {"cohort": "math", "task": "dropout", "scenario": "early", "features": _features()}
    assert api.post("/api/v1/models/predict", json=bad).json()["code"] == "invalid_request"

    selected = api.get(
        "/api/v1/models/selected",
        params={"cohort": "math", "task": "regression", "scenario": "early"},
    ).json()["metadata"]["model"]
    other = next(k for k in ("linear_regression", "decision_tree") if k != selected)
    body = {**bad, "task": "regression", "model": other}
    response = api.post("/api/v1/models/predict", json=body)
    assert response.status_code == 404 and response.json()["code"] == "model_not_available"
