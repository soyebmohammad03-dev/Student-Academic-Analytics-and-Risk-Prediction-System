"""Machine learning on the official files. Skipped until the dataset is downloaded.

Training here uses the minimal search (3 folds) so the suite stays fast; the persisted
full-search results are checked separately when ``models/ml_results.json`` exists.
"""

import hashlib

import numpy as np
import pytest
from sklearn.model_selection import GridSearchCV

from analytics.data import COHORTS, Cohort, load_cohort
from analytics.data.download import DEFAULT_RAW_DIR, verify
from analytics.ml import SearchMode, Task, TrainingConfig, get_spec, train_cohort
from analytics.ml.config import DEFAULT_MODELS_DIR
from analytics.ml.evaluation import evaluate, nested_cv
from analytics.ml.persistence import RESULTS_FILE, load_results
from analytics.preprocessing import TARGET_COLUMNS, Scenario, feature_columns, prepare_cohort

pytestmark = pytest.mark.skipif(
    bool(verify(DEFAULT_RAW_DIR)), reason="official dataset not downloaded"
)

FAST = TrainingConfig(cv_folds=3, search=SearchMode.MINIMAL)
SIZES = {Cohort.MATH: (395, 316, 79, 130), Cohort.PORTUGUESE: (649, 519, 130, 100)}


def _dataset(cohort):
    return prepare_cohort(load_cohort(DEFAULT_RAW_DIR, cohort))


@pytest.fixture(scope="module")
def trained():
    return {cohort: train_cohort(_dataset(cohort), FAST) for cohort in Cohort}


@pytest.mark.parametrize("cohort", list(Cohort))
def test_both_cohorts_and_all_scenarios_train(trained, cohort):
    item = trained[cohort]
    c = item.results
    n, n_train, n_test, at_risk = SIZES[cohort]

    assert (c.n, c.n_train, c.n_test, c.risk["all"].at_risk) == (n, n_train, n_test, at_risk)
    assert {(t, s) for t, s in item.selected} == {(t, s) for t in Task for s in Scenario}
    assert {r.scenario for r in c.regression} == set(Scenario)
    assert "NaN" not in c.model_dump_json() and "Infinity" not in c.model_dump_json()


@pytest.mark.parametrize("cohort", list(Cohort))
def test_no_outcome_reaches_any_selected_model(trained, cohort):
    for (_, scenario), ev in trained[cohort].selected.items():
        guard = ev.pipeline.named_steps["prep"].named_steps["guard"]
        encoded = set(ev.pipeline[:-1].get_feature_names_out())
        assert list(guard.feature_names_in_) == list(feature_columns(scenario))
        assert not encoded & TARGET_COLUMNS
        assert not {"G3", "at_risk"} & set(guard.feature_names_in_)
        if scenario is Scenario.EARLY:
            assert not {"G1", "G2"} & encoded
        if scenario is Scenario.MID_YEAR:
            assert "G1" in encoded and "G2" not in encoded


@pytest.mark.parametrize("cohort", list(Cohort))
def test_metrics_are_within_valid_ranges(trained, cohort):
    c = trained[cohort].results
    for r in c.classification:
        for name, value in r.test.items():
            assert value is None or 0 <= value <= 1, (r.model, name)
        for summary in r.cv.values():
            assert all(v is None or 0 <= v <= 1 for v in summary.folds)
    for r in c.regression:
        assert r.test["rmse"] >= r.test["mae"] >= 0
        assert r.test["r2"] <= 1


def test_preprocessing_learns_only_from_each_training_fold():
    data = _dataset(Cohort.MATH)
    split = data.split(Scenario.FULL_HISTORY)
    checked = []

    def check(k, estimator, X_fit, X_val):
        pipeline = estimator.best_estimator_ if isinstance(estimator, GridSearchCV) else estimator
        columns = pipeline.named_steps["prep"].named_steps["columns"]
        scaler = columns.named_transformers_["numeric"].named_steps["scale"]
        names = list(scaler.feature_names_in_)
        np.testing.assert_allclose(scaler.mean_, X_fit[names].mean().to_numpy())
        assert not np.allclose(scaler.mean_, split.X_train[names].mean().to_numpy())
        assert not set(X_val.index) & set(X_fit.index)
        checked.append(k)

    spec = get_spec(Task.CLASSIFICATION, "logistic_regression")
    nested_cv(spec, Scenario.FULL_HISTORY, split.X_train, split.y_train_risk, FAST, check)
    assert checked == [0, 1, 2]


def test_test_set_is_unseen_during_tuning_and_cv():
    data = _dataset(Cohort.PORTUGUESE)
    split = data.split(Scenario.MID_YEAR)
    spec = get_spec(Task.REGRESSION, "decision_tree")
    config = TrainingConfig(cv_folds=3)  # the documented grid
    args = (spec, Scenario.MID_YEAR, split.X_train, split.y_train_regression)

    original = evaluate(*args, split.X_test, split.y_test_regression, config)
    shuffled = evaluate(*args, split.X_test.assign(G1=20.0), 20 - split.y_test_regression, config)

    assert original.best_params == shuffled.best_params
    assert original.outer_fold_params == shuffled.outer_fold_params
    assert original.cv["rmse"].folds == shuffled.cv["rmse"].folds
    assert original.test != shuffled.test


def test_raw_files_untouched_after_training(trained):
    for cohort in Cohort:
        path = DEFAULT_RAW_DIR / COHORTS[cohort].filename
        assert hashlib.sha256(path.read_bytes()).hexdigest() == COHORTS[cohort].sha256


# --- Persisted full-search results ------------------------------------------------------

persisted = pytest.mark.skipif(
    not (DEFAULT_MODELS_DIR / RESULTS_FILE).is_file(),
    reason="models not trained (python -m analytics.ml.train)",
)


@persisted
def test_persisted_results_are_a_full_run_on_the_pinned_data():
    results = load_results(DEFAULT_MODELS_DIR)
    assert results.run.search == "full" and results.run.cv_folds == 5
    assert results.run.dataset_sha256 == {str(c): i.sha256 for c, i in COHORTS.items()}


@persisted
def test_persisted_results_show_no_leakage_signals():
    results = load_results(DEFAULT_MODELS_DIR)
    for c in results.cohorts:
        for r in [*c.regression, *c.classification]:
            assert "near_perfect" not in {d.code for d in r.diagnostics}, (c.cohort, r.model)
        for s in c.selections:
            assert s.beats_baseline, (c.cohort, s.task, s.scenario)


@persisted
def test_ml_results_document_is_current():
    from analytics.ml.report import OUTPUT, render

    assert OUTPUT.read_text(encoding="utf-8") == render(load_results(DEFAULT_MODELS_DIR)), (
        "docs/ML_RESULTS.md is stale: run `python -m analytics.ml.train --report-only`"
    )


@persisted
def test_readme_results_match_the_training_run():
    from analytics.ml.report import README, README_END, README_START, readme_results

    text = README.read_text(encoding="utf-8")
    start, end = text.index(README_START), text.index(README_END) + len(README_END)
    assert text[start:end] == readme_results(load_results(DEFAULT_MODELS_DIR)), (
        "README.md results are stale: run `python -m analytics.ml.train --report-only`"
    )


@persisted
def test_persisted_models_predict_for_a_real_record():
    from analytics.ml import PredictionService

    service = PredictionService(DEFAULT_MODELS_DIR)
    row = load_cohort(DEFAULT_RAW_DIR, Cohort.PORTUGUESE).data.iloc[0]
    for scenario in Scenario:
        allowed = set(feature_columns(scenario)) | {"absences"}
        record = {k: (v if isinstance(v, str) else int(v)) for k, v in row.items() if k in allowed}
        for task in Task:
            out = service.predict(Cohort.PORTUGUESE, task, scenario, record)
            if task is Task.REGRESSION:
                assert 0 <= out.predicted_grade <= 20
            else:
                assert isinstance(out.at_risk, bool)
