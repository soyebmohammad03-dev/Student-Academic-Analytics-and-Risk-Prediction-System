"""End-to-end checks on the official files and persisted artefacts (skipped otherwise)."""

import pytest
from fastapi.testclient import TestClient

from analytics.data import Cohort, load_cohort
from analytics.data.download import DEFAULT_RAW_DIR, verify
from analytics.ml.config import DEFAULT_MODELS_DIR
from analytics.ml.persistence import RESULTS_FILE
from app.main import create_app

pytestmark = [
    pytest.mark.skipif(bool(verify(DEFAULT_RAW_DIR)), reason="official dataset not downloaded"),
    pytest.mark.skipif(
        not (DEFAULT_MODELS_DIR / "interpretability.json").is_file()
        or not (DEFAULT_MODELS_DIR / RESULTS_FILE).is_file(),
        reason="models or interpretability not built",
    ),
]

COHORTS = {"math": (395, 130), "portuguese": (649, 100)}
SCENARIOS = ["early", "mid_year", "full_history"]
#: Response-size budget for GET endpoints (bytes). The largest (EDA charts) is ~36 KB.
MAX_RESPONSE = 64_000


@pytest.fixture(scope="module")
def api():
    return TestClient(create_app())


def test_real_system_is_ready(api):
    body = api.get("/api/v1/ready").json()
    assert body["status"] == "ready", body
    assert {c["status"] for c in body["components"]} == {"available"}


def test_dashboard_matches_the_components_it_summarises(api):
    body = api.get("/api/v1/dashboard/summary").json()
    assert body["dataset"]["available"] and body["models"]["available"]
    selections = {
        (c["cohort"], c["task"], c["scenario"], c["model"])
        for c in api.get("/api/v1/models").json()["selected"]
    }
    assert {
        (m["cohort"], m["task"], m["scenario"], m["model"]) for m in body["models"]["selected"]
    } == selections

    for overview in body["dataset"]["cohorts"]:
        cohort = overview["cohort"]
        n, at_risk = COHORTS[cohort]
        risk = overview["observed_risk"]
        assert (overview["rows"], risk["n"], risk["at_risk"]) == (n, n, at_risk)
        assert risk["kind"] == "observed_historical"
        profiles = api.get("/api/v1/risk/profiles", params={"cohort": cohort}).json()
        prep = api.get(
            "/api/v1/preprocessing/summary", params={"cohort": cohort, "scenario": "early"}
        ).json()
        dist = api.get("/api/v1/statistics/distributions", params={"cohort": cohort}).json()
        assert profiles["at_risk"] == prep["risk"]["at_risk"] == dist["risk"]["at_risk"] == at_risk
        g3 = next(g for g in dist["grades"] if g["variable"] == "G3")
        assert overview["final_grade"]["mean"] == pytest.approx(g3["summary"]["mean"])
        assert overview["final_grade"]["zero_count"] == g3["zero_count"]


def test_model_metrics_match_their_training_run(api):
    dashboard = api.get("/api/v1/dashboard/summary").json()["models"]
    for item in dashboard["selected"]:
        table = api.get(f"/api/v1/models/{item['task']}", params={"cohort": item["cohort"]}).json()
        row = next(
            r
            for r in table["rows"]
            if r["scenario"] == item["scenario"] and r["model"] == item["model"]
        )
        assert row["selected"]
        metric = item["metric"]
        assert row[f"cv_{metric}"] == pytest.approx(item["cv_mean"])
        assert row[f"test_{metric}"] == pytest.approx(item["test"])


@pytest.mark.parametrize("cohort", list(COHORTS))
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_real_pipeline_summary_is_complete(api, cohort, scenario):
    body = api.get(
        "/api/v1/pipeline/summary", params={"cohort": cohort, "scenario": scenario}
    ).json()
    assert {s["status"] for s in body["steps"]} == {"available"}
    assert body["overview"]["rows"] == COHORTS[cohort][0]
    assert len(body["research_questions"]) == 9
    for task in ("regression", "classification"):
        assert body["top_attributes"][task], task
        assert "Final grade" not in body["top_attributes"][task]


@pytest.mark.parametrize("cohort", list(COHORTS))
@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("task", ["regression", "classification"])
def test_real_prediction_explanation_and_risk_flow(api, cohort, scenario, task):
    row = load_cohort(DEFAULT_RAW_DIR, Cohort(cohort)).data.iloc[0]
    allowed = {"G1": scenario != "early", "G2": scenario == "full_history"}
    features = {
        k: (v if isinstance(v, str) else int(v))
        for k, v in row.items()
        if k != "G3" and allowed.get(k, True)
    }
    body = {"cohort": cohort, "task": task, "scenario": scenario, "features": features}
    prediction = api.post("/api/v1/models/predict", json=body).json()
    explained = api.post("/api/v1/interpretability/explain", json={**body, "top": 5}).json()

    assert prediction["model"] == explained["prediction"]["model"]
    assert explained["prediction"]["raw_prediction"] == prediction["raw_prediction"]
    assert explained["prediction"]["score"] == prediction["score"]
    if task == "classification":
        insights = api.post(
            "/api/v1/risk/insights",
            json={"cohort": cohort, "scenario": scenario, "features": features},
        ).json()
        assert insights["individual"]["prediction"]["at_risk"] == prediction["at_risk"]
        assert all(g["kind"] == "group_statistics" for g in insights["group"])


def test_get_responses_stay_small_and_json_safe(api):
    paths = [
        "/api/v1/dashboard/summary",
        "/api/v1/ready",
        "/api/v1/models",
        "/api/v1/models/cohort-comparison",
    ]
    for cohort in COHORTS:
        paths += [
            f"/api/v1/dataset/{r}?cohort={cohort}"
            for r in ("summary", "schema", "quality", "records")
        ]
        paths += [
            f"/api/v1/statistics/{r}?cohort={cohort}"
            for r in ("descriptive", "distributions", "correlations", "hypothesis-tests",
                      "associations", "outliers")
        ]  # fmt: skip
        paths += [
            f"/api/v1/eda/charts?cohort={cohort}",
            f"/api/v1/risk/profiles?cohort={cohort}",
            f"/api/v1/models/regression?cohort={cohort}",
            f"/api/v1/models/classification?cohort={cohort}",
        ]
        for scenario in SCENARIOS:
            paths.append(f"/api/v1/pipeline/summary?cohort={cohort}&scenario={scenario}")
            for task in ("regression", "classification"):
                paths.append(
                    f"/api/v1/interpretability/importance?cohort={cohort}&task={task}&scenario={scenario}"
                )
    for path in paths:
        response = api.get(path)
        assert response.status_code == 200, path
        assert len(response.content) < MAX_RESPONSE, (path, len(response.content))
        assert "NaN" not in response.text and "Infinity" not in response.text, path
        assert (
            str(DEFAULT_RAW_DIR) not in response.text
            and str(DEFAULT_MODELS_DIR) not in response.text
        )
