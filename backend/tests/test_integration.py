"""End-to-end integration of the backend on synthetic data (no network, no official files).

Covers the shared pipeline, readiness, dashboard and pipeline summaries, error bodies,
cache invalidation and the model lifecycle.
"""

from __future__ import annotations

import json
import os
import shutil

import joblib
import pytest
from fastapi.testclient import TestClient

from analytics.data import Cohort, load_cohort
from analytics.interpret.build import build
from analytics.interpret.build import save as save_interpretability
from analytics.ml import SearchMode, TrainingConfig, save, train_cohort
from analytics.ml.persistence import SELECTED_DIR, load_metadata, load_pipeline, sha256
from analytics.ml.results import ModelArtifactError
from analytics.pipeline import AnalyticsPipeline, FileCache
from analytics.preprocessing import Scenario, prepare_cohort
from app.core.config import Settings, get_settings
from app.main import create_app
from tests.factories import VALID_ROW, make_varied_rows, write_cohort

CONFIG = TrainingConfig(cv_folds=3, search=SearchMode.MINIMAL, n_jobs=1)
SCENARIOS = ["early", "mid_year", "full_history"]


@pytest.fixture(scope="module")
def artefacts(tmp_path_factory):
    """Synthetic cohorts, trained models and interpretability results, built once."""
    data_dir = tmp_path_factory.mktemp("data")
    raw = data_dir / "raw"
    write_cohort(raw / "student-mat.csv", make_varied_rows(150, seed=51))
    write_cohort(raw / "student-por.csv", make_varied_rows(160, seed=52))
    models_dir = tmp_path_factory.mktemp("models")
    trained = [train_cohort(prepare_cohort(load_cohort(raw, c)), CONFIG) for c in Cohort]
    save(trained, CONFIG, models_dir)
    save_interpretability(build(raw, models_dir, repeats=2, shapley_samples=8), models_dir)
    return data_dir, models_dir


def _client(data_dir, models_dir) -> TestClient:
    settings = Settings(environment="test", data_dir=data_dir, models_dir=models_dir)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def api(artefacts):
    return _client(*artefacts)


@pytest.fixture
def copy(artefacts, tmp_path):
    """A private, writable copy of the artefacts for tests that modify files."""
    data_dir, models_dir = artefacts
    shutil.copytree(data_dir, tmp_path / "data")
    shutil.copytree(models_dir, tmp_path / "models")
    return tmp_path / "data", tmp_path / "models"


def _features(*grades: str) -> dict:
    record = {k: v for k, v in VALID_ROW.items() if k not in {"G1", "G2", "G3"}}
    return {**record, **{g: VALID_ROW[g] for g in grades}}


GRADES = {"early": (), "mid_year": ("G1",), "full_history": ("G1", "G2")}


# --- Error contract -------------------------------------------------------------------


def test_every_error_uses_the_code_detail_shape(client, tmp_path):
    cases = {
        "/api/v1/does-not-exist": (404, "not_found"),
        "/api/v1/dataset/summary?cohort=chemistry": (422, "invalid_request"),
        "/api/v1/dataset/summary?cohort=math": (503, "dataset_unavailable"),
        "/api/v1/models/regression?cohort=math": (503, "models_unavailable"),
        "/api/v1/interpretability/importance?cohort=math&task=regression&scenario=late": (
            422,
            "invalid_request",
        ),
        "/api/v1/risk/profiles?cohort=math": (503, "dataset_unavailable"),
    }
    for path, (status, code) in cases.items():
        response = client.get(path)
        assert (response.status_code, response.json()["code"]) == (status, code), path
        assert set(response.json()) == {"code", "detail"}
    wrong_method = client.delete("/api/v1/health")
    assert (wrong_method.status_code, wrong_method.json()["code"]) == (405, "method_not_allowed")


def test_errors_never_expose_paths_or_settings(client, settings):
    for path in (
        "/api/v1/dataset/summary?cohort=math",
        "/api/v1/models/regression?cohort=math",
        "/api/v1/interpretability/importance?cohort=math&task=regression&scenario=early",
        "/api/v1/statistics/descriptive?cohort=portuguese",
    ):
        text = client.get(path).text
        assert str(settings.data_dir) not in text and str(settings.models_dir) not in text
        assert "/Users/" not in text and "/tmp" not in text and "/var/" not in text


def test_unexpected_errors_are_generic_and_logged(settings):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    @app.get("/explode")
    def explode():
        raise RuntimeError("internal detail /secret/path")

    response = TestClient(app, raise_server_exceptions=False).get("/explode")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error" and "secret" not in body["detail"]
    assert "request" in body["detail"]


def test_requests_carry_a_request_id(client):
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"
    assert len(client.get("/api/v1/health").headers["X-Request-ID"]) == 12


def test_invalid_cohort_file_is_reported_not_crashed(client, settings):
    rows = make_varied_rows(20, seed=1)
    columns = [c for c in rows[0] if c != "G3"]
    write_cohort(settings.raw_data_dir / "student-mat.csv", rows, columns=columns)
    assert client.get("/api/v1/dataset/quality", params={"cohort": "math"}).status_code == 200
    response = client.get("/api/v1/statistics/descriptive", params={"cohort": "math"})
    assert response.status_code == 503 and response.json()["code"] == "dataset_invalid"


# --- Readiness -------------------------------------------------------------------------


def test_readiness_without_artefacts_is_degraded_but_operational(client):
    body = client.get("/api/v1/ready").json()
    states = {c["key"]: c["status"] for c in body["components"]}
    assert body["status"] == "degraded"
    assert states == {
        "api": "available",
        "dataset": "unavailable",
        "statistics": "unavailable",
        "models": "unavailable",
        "interpretability": "unavailable",
    }
    actions = {c["key"]: c["action"] for c in body["components"]}
    assert actions["dataset"] == "python -m analytics.data.download"
    assert actions["models"] == "python -m analytics.ml.train"
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_readiness_reports_models_and_unofficial_data(api):
    states = {c["key"]: c for c in api.get("/api/v1/ready").json()["components"]}
    # Synthetic files are not the pinned official files.
    assert states["dataset"]["status"] == "unavailable"
    assert "checksum" in states["dataset"]["detail"]
    assert states["models"]["status"] == "available"
    assert states["models"]["detail"] == "12 selected models verified."


def test_readiness_detects_tampered_models_and_stale_interpretability(copy):
    data_dir, models_dir = copy
    artifact = next((models_dir / SELECTED_DIR).glob("*.joblib"))
    artifact.write_bytes(artifact.read_bytes() + b"tampered")
    run = json.loads((models_dir / "interpretability.json").read_text())
    run["models_created_at"] = "1999-01-01T00:00:00+00:00"
    (models_dir / "interpretability.json").write_text(json.dumps(run))

    states = {
        c["key"]: c for c in _client(data_dir, models_dir).get("/api/v1/ready").json()["components"]
    }
    assert states["models"]["status"] == "degraded" and "SHA-256" in states["models"]["detail"]
    assert states["interpretability"]["status"] == "degraded"


# --- Dashboard and pipeline summaries --------------------------------------------------


def test_dashboard_without_artefacts_reports_unavailability(client):
    body = client.get("/api/v1/dashboard/summary").json()
    assert body["dataset"] == {
        "available": False,
        "detail": body["dataset"]["detail"],
        "cohorts": [],
    }
    assert body["models"]["available"] is False and body["models"]["selected"] == []
    assert any("not predictions" in n for n in body["notes"])


def test_pipeline_summary_runs_every_step(api):
    for cohort in ("math", "portuguese"):
        for scenario in SCENARIOS:
            body = api.get(
                "/api/v1/pipeline/summary", params={"cohort": cohort, "scenario": scenario}
            ).json()
            steps = {s["step"]: s["status"] for s in body["steps"]}
            assert set(steps.values()) == {"available"}, (cohort, scenario, body["steps"])
            assert {m["task"] for m in body["selected_models"]} == {"regression", "classification"}
            assert all(m["scenario"] == scenario for m in body["selected_models"])
            assert body["overview"]["observed_risk"]["kind"] == "observed_historical"
            assert ("G2" in body["scenario_features"]) == (scenario == "full_history")


def test_pipeline_summary_without_data_marks_steps_unavailable(client):
    body = client.get("/api/v1/pipeline/summary?cohort=math&scenario=early").json()
    assert [s["status"] for s in body["steps"]] == ["unavailable"] * 7
    assert "/" not in body["steps"][0]["detail"].replace("from backend/", "")


# --- Cohort, scenario, task and model validation --------------------------------------


@pytest.mark.parametrize("cohort", ["math", "portuguese"])
@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("task", ["regression", "classification"])
def test_prediction_and_explanation_use_the_requested_model(api, cohort, scenario, task):
    body = {
        "cohort": cohort,
        "task": task,
        "scenario": scenario,
        "features": _features(*GRADES[scenario]),
    }
    prediction = api.post("/api/v1/models/predict", json=body).json()
    explained = api.post("/api/v1/interpretability/explain", json={**body, "top": 3}).json()
    selected = api.get(
        "/api/v1/models/selected", params={"cohort": cohort, "task": task, "scenario": scenario}
    ).json()["metadata"]

    assert prediction["model"] == explained["prediction"]["model"] == selected["model"]
    assert (prediction["cohort"], prediction["task"], prediction["scenario"]) == (
        cohort,
        task,
        scenario,
    )
    if task == "regression":
        assert prediction["probability"] is None and prediction["at_risk"] is None
    else:
        assert prediction["predicted_grade"] is None
        assert (prediction["probability"] is None) == (selected["score_kind"] != "probability")


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"cohort": "chemistry"}, "invalid_request"),
        ({"scenario": "late"}, "invalid_request"),
        ({"task": "dropout"}, "invalid_request"),
        ({"model": "gradient_boosting"}, "invalid_request"),
        ({"features": {**_features(), "G3": 10}}, "invalid_record"),
        ({"features": {**_features(), "at_risk": 1}}, "invalid_record"),
        ({"features": _features("G1")}, "invalid_record"),
        ({"features": {k: v for k, v in _features().items() if k != "age"}}, "invalid_record"),
        ({"features": {**_features(), "Mjob": "pilot"}}, "invalid_record"),
        ({"features": {**_features(), "absences": 200}}, "invalid_record"),
    ],
)
def test_prediction_rejects_invalid_requests(api, change, code):
    body = {
        "cohort": "math",
        "task": "regression",
        "scenario": "early",
        "features": _features(),
        **change,
    }
    for path in ("/api/v1/models/predict", "/api/v1/interpretability/explain"):
        response = api.post(path, json=body)
        assert response.status_code == 422 and response.json()["code"] == code, (path, change)


def test_known_but_unpersisted_model_is_not_substituted(api):
    meta = api.get(
        "/api/v1/models/selected",
        params={"cohort": "math", "task": "regression", "scenario": "early"},
    ).json()["metadata"]
    other = next(
        m for m in ("linear_regression", "decision_tree", "random_forest") if m != meta["model"]
    )
    body = {
        "cohort": "math",
        "task": "regression",
        "scenario": "early",
        "features": _features(),
        "model": other,
    }
    response = api.post("/api/v1/models/predict", json=body)
    assert response.status_code == 404 and response.json()["code"] == "model_not_available"


# --- Model lifecycle --------------------------------------------------------------------


def test_requests_never_train_or_download(api, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("training or downloading was triggered by a request")

    monkeypatch.setattr("analytics.ml.training.train_cohort", forbidden)
    monkeypatch.setattr("analytics.ml.evaluation.evaluate", forbidden)
    monkeypatch.setattr("analytics.data.download.fetch_archive", forbidden)
    monkeypatch.setattr("analytics.data.download.download", forbidden)
    body = {
        "cohort": "portuguese",
        "task": "classification",
        "scenario": "mid_year",
        "features": _features("G1"),
    }
    assert api.post("/api/v1/models/predict", json=body).status_code == 200
    assert api.post("/api/v1/interpretability/explain", json=body).status_code == 200
    assert api.get("/api/v1/ready").status_code == 200
    assert api.get("/api/v1/dashboard/summary").status_code == 200


def test_corrupted_or_mismatched_artifacts_are_refused(copy):
    data_dir, models_dir = copy
    meta = load_metadata(models_dir, "math", "regression", "early")
    path = models_dir / SELECTED_DIR / meta.artifact

    path.write_bytes(b"not a pickle")
    corrupted = meta.model_copy(update={"sha256": sha256(path)})
    with pytest.raises(ModelArtifactError, match="could not be loaded"):
        load_pipeline(models_dir, corrupted)

    other = load_metadata(models_dir, "math", "classification", "early")
    shutil.copy(models_dir / SELECTED_DIR / other.artifact, path)
    swapped = meta.model_copy(update={"sha256": sha256(path)})
    with pytest.raises(ModelArtifactError):
        load_pipeline(models_dir, swapped)

    (models_dir / SELECTED_DIR / f"{meta.artifact[:-7]}.json").write_text(swapped.model_dump_json())
    body = {"cohort": "math", "task": "regression", "scenario": "early", "features": _features()}
    response = _client(data_dir, models_dir).post("/api/v1/models/predict", json=body)
    assert response.status_code == 503 and response.json()["code"] == "models_unavailable"


def test_metadata_matches_each_artifact(artefacts):
    _, models_dir = artefacts
    for path in (models_dir / SELECTED_DIR).glob("*.json"):
        cohort, task, scenario = path.stem.split("__")
        meta = load_metadata(models_dir, cohort, task, scenario)
        pipeline = joblib.load(models_dir / SELECTED_DIR / meta.artifact)
        assert sha256(models_dir / SELECTED_DIR / meta.artifact) == meta.sha256
        assert list(pipeline[:-1].get_feature_names_out()) == meta.encoded_features
        assert (meta.cohort, meta.task, meta.scenario) == (cohort, task, scenario)


# --- Caching ---------------------------------------------------------------------------------


def test_file_cache_rebuilds_only_when_the_file_changes(tmp_path):
    path = tmp_path / "artefact.txt"
    path.write_text("one")
    cache, calls = FileCache(), []

    def build():
        calls.append(1)
        return path.read_text()

    assert cache.get("k", path, build) == cache.get("k", path, build) == "one"
    assert len(calls) == 1
    path.write_text("two!")
    os.utime(path, ns=(1, 1))
    assert cache.get("k", path, build) == "two!" and len(calls) == 2
    path.unlink()
    with pytest.raises(FileNotFoundError):
        cache.get("k", path, lambda: path.read_text())


def test_pipeline_reuses_one_cohort_version_across_components(artefacts):
    data_dir, models_dir = artefacts
    pipeline = AnalyticsPipeline(data_dir / "raw", models_dir)
    version = pipeline.cohort(Cohort.MATH)
    assert pipeline.cohort(Cohort.MATH) is version
    assert pipeline.statistics(Cohort.MATH) is version.statistics
    assert pipeline.statistics(Cohort.MATH).data is pipeline.dataset(Cohort.MATH).analytical
    assert pipeline.profiles(Cohort.MATH) is pipeline.profiles(Cohort.MATH)
    assert pipeline.ml_results() is pipeline.ml_results()


def test_no_stale_results_after_artefacts_change(copy):
    data_dir, models_dir = copy
    api = _client(data_dir, models_dir)
    before = api.get("/api/v1/dataset/summary", params={"cohort": "math"}).json()["rows"]
    stats_before = api.get("/api/v1/statistics/descriptive", params={"cohort": "math"}).json()["n"]
    run_before = api.get("/api/v1/models").json()["run"]["created_at"]

    write_cohort(data_dir / "raw" / "student-mat.csv", make_varied_rows(90, seed=9))
    results = json.loads((models_dir / "ml_results.json").read_text())
    results["run"]["created_at"] = "2030-01-01T00:00:00+00:00"
    (models_dir / "ml_results.json").write_text(json.dumps(results))

    assert before == stats_before == 150
    assert api.get("/api/v1/dataset/summary", params={"cohort": "math"}).json()["rows"] == 90
    assert api.get("/api/v1/statistics/descriptive", params={"cohort": "math"}).json()["n"] == 90
    assert api.get("/api/v1/risk/profiles", params={"cohort": "math"}).json()["n"] == 90
    assert api.get("/api/v1/models").json()["run"]["created_at"] != run_before


def test_cached_results_equal_fresh_computation(artefacts):
    from analytics.statistics import describe

    data_dir, models_dir = artefacts
    api = _client(data_dir, models_dir)
    first = api.get("/api/v1/statistics/descriptive", params={"cohort": "portuguese"}).json()
    second = api.get("/api/v1/statistics/descriptive", params={"cohort": "portuguese"}).json()
    fresh = describe(
        prepare_cohort(load_cohort(data_dir / "raw", Cohort.PORTUGUESE)).analytical, "portuguese"
    )
    assert first == second == json.loads(fresh.model_dump_json())


def test_scenarios_are_never_substituted(api):
    for scenario in SCENARIOS:
        body = api.get(
            "/api/v1/interpretability/importance",
            params={"cohort": "math", "task": "regression", "scenario": scenario},
        ).json()
        assert body["scenario"] == scenario
        assert {i["attribute"] for m in body["methods"] for i in m["items"]} >= (
            {"G2"} if scenario == "full_history" else set()
        )
        if scenario == Scenario.EARLY:
            assert not {"G1", "G2"} & {i["attribute"] for m in body["methods"] for i in m["items"]}


# --- Explicit regeneration commands ----------------------------------------------------


def test_training_command_refuses_unverified_data(artefacts, tmp_path):
    from analytics.ml.train import main

    data_dir, _ = artefacts
    out = tmp_path / "models"
    # Synthetic files do not match the pinned checksums, so nothing is trained or written.
    assert main(["--raw-dir", str(data_dir / "raw"), "--models-dir", str(out)]) == 1
    assert not out.exists()


def test_report_only_refuses_minimal_runs(artefacts):
    from analytics.ml.train import main

    _, models_dir = artefacts
    assert main(["--report-only", "--models-dir", str(models_dir)]) == 1


def test_corrupted_results_file_is_reported(copy):
    data_dir, models_dir = copy
    (models_dir / "ml_results.json").write_text("{not json")
    response = _client(data_dir, models_dir).get("/api/v1/models/regression?cohort=math")
    assert response.status_code == 503 and response.json()["code"] == "models_unavailable"
    states = {
        c["key"]: c["status"]
        for c in _client(data_dir, models_dir).get("/api/v1/ready").json()["components"]
    }
    assert states["models"] == "unavailable"
