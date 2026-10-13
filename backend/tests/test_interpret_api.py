import pytest
from fastapi.testclient import TestClient

from analytics.data import Cohort, load_cohort
from analytics.interpret.build import build
from analytics.interpret.build import save as save_interpretability
from analytics.ml import SearchMode, TrainingConfig, save, train_cohort
from analytics.preprocessing import prepare_cohort
from app.core.config import Settings, get_settings
from app.main import create_app
from tests.factories import VALID_ROW, make_varied_rows, write_cohort

CONFIG = TrainingConfig(cv_folds=3, search=SearchMode.MINIMAL, n_jobs=1)


@pytest.fixture(scope="module")
def dirs(tmp_path_factory):
    data_dir = tmp_path_factory.mktemp("data")
    raw = data_dir / "raw"
    write_cohort(raw / "student-mat.csv", make_varied_rows(150, seed=41))
    write_cohort(raw / "student-por.csv", make_varied_rows(160, seed=42))
    models_dir = tmp_path_factory.mktemp("models")
    trained = [train_cohort(prepare_cohort(load_cohort(raw, c)), CONFIG) for c in Cohort]
    save(trained, CONFIG, models_dir)
    save_interpretability(build(raw, models_dir, repeats=2, shapley_samples=8), models_dir)
    return data_dir, models_dir


@pytest.fixture
def api(dirs) -> TestClient:
    data_dir, models_dir = dirs
    settings = Settings(environment="test", data_dir=data_dir, models_dir=models_dir)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _features(*grades: str) -> dict:
    record = {k: v for k, v in VALID_ROW.items() if k not in {"G1", "G2", "G3"}}
    return {**record, **{g: VALID_ROW[g] for g in grades}}


@pytest.mark.parametrize("cohort", ["math", "portuguese"])
@pytest.mark.parametrize("task", ["regression", "classification"])
def test_importance_endpoint(api, cohort, task):
    body = api.get(
        "/api/v1/interpretability/importance",
        params={"cohort": cohort, "task": task, "scenario": "mid_year"},
    ).json()
    assert body["cohort"] == cohort and body["task"] == task
    methods = [m["method"] for m in body["methods"]]
    assert "permutation_test" in methods and "mean_abs_shapley" in methods
    for m in body["methods"]:
        assert m["unit"] and m["limitations"]
        assert not {i["attribute"] for i in m["items"]} & {"G3", "at_risk"}


def test_explain_endpoint_returns_bounded_explanation(api):
    body = {
        "cohort": "portuguese",
        "task": "classification",
        "scenario": "full_history",
        "features": _features("G1", "G2"),
        "top": 4,
    }
    out = api.post("/api/v1/interpretability/explain", json=body)
    assert out.status_code == 200
    data = out.json()
    assert len(data["explanation"]["contributions"]) == 4
    assert data["explanation"]["kind"] == "individual_model_explanation"
    assert data["prediction"]["model"] and data["explanation"]["limitations"]
    assert len(out.text) < 20_000


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"features": {**_features(), "G3": 10}}, "invalid_record"),
        ({"features": _features("G1")}, "invalid_record"),
        ({"features": {**_features(), "studytime": 9}}, "invalid_record"),
        ({"features": _features(), "top": 0}, "invalid_request"),
        ({"features": _features(), "task": "dropout"}, "invalid_request"),
    ],
)
def test_explain_rejects_invalid_input(api, body, code):
    request = {"cohort": "math", "task": "regression", "scenario": "early", **body}
    response = api.post("/api/v1/interpretability/explain", json=request)
    assert response.status_code == 422 and response.json()["code"] == code


def test_sensitivity_endpoints(api):
    base = {"cohort": "math", "task": "regression", "scenario": "early", "features": _features()}
    curve = api.post(
        "/api/v1/interpretability/sensitivity", json={**base, "attribute": "studytime"}
    )
    assert curve.status_code == 200 and len(curve.json()["points"]) == 4
    assert curve.json()["kind"] == "model_sensitivity"
    bad = api.post("/api/v1/interpretability/sensitivity", json={**base, "attribute": "sex"})
    assert bad.status_code == 422

    scenarios = api.post(
        "/api/v1/interpretability/scenario-sensitivity",
        json={"cohort": "math", "task": "classification", "features": _features("G1")},
    ).json()
    assert [i["scenario"] for i in scenarios["items"]] == ["early", "mid_year"]
    assert scenarios["skipped"] == ["full_history"]


def test_profiles_suggestions_and_insights(api):
    profiles = api.get("/api/v1/risk/profiles", params={"cohort": "math"}).json()
    assert profiles["n"] == 150 and profiles["kind"] == "group_statistics"

    body = {"cohort": "math", "scenario": "early", "features": {**_features(), "failures": 2}}
    suggestions = api.post("/api/v1/risk/suggestions", json=body).json()
    assert "disclaimer" in suggestions
    assert all(s["kind"] == "general_educational_suggestion" for s in suggestions["suggestions"])

    insights = api.post("/api/v1/risk/insights", json=body).json()
    assert insights["individual"]["explanation"]["kind"] == "individual_model_explanation"
    assert insights["individual"]["prediction"]["task"] == "classification"
    assert all(g["kind"] == "group_statistics" for g in insights["group"])
    assert {g["variable"] for g in insights["group"]} >= {"failures", "studytime"}
    assert len(insights["reading"]) == 3


def test_endpoints_report_missing_artifacts(client):
    response = client.get(
        "/api/v1/interpretability/importance",
        params={"cohort": "math", "task": "regression", "scenario": "early"},
    )
    assert response.status_code == 503 and response.json()["code"] == "models_unavailable"
    missing_data = client.get("/api/v1/risk/profiles", params={"cohort": "math"})
    assert missing_data.status_code == 503
    assert missing_data.json()["code"] == "dataset_unavailable"
