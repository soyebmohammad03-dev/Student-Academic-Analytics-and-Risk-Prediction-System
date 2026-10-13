"""Machine-learning layer on synthetic cohorts (mechanics, leakage, metrics, persistence).

The synthetic rows are random draws from each documented range, so model scores here
mean nothing; only behaviour is tested.
"""

from __future__ import annotations

import numpy as np
import pytest
import sklearn
from sklearn.model_selection import GridSearchCV, KFold, StratifiedKFold

from analytics.data import Cohort, load_cohort
from analytics.ml import (
    MODELS,
    InvalidRecordError,
    ModelArtifactError,
    ModelNotAvailableError,
    PredictionService,
    SearchMode,
    Task,
    TrainingConfig,
    build_pipeline,
    get_spec,
    load_results,
    record_frame,
    save,
    search_space,
    train_cohort,
)
from analytics.ml.evaluation import evaluate, nested_cv, splitter, tuned_estimator
from analytics.ml.metrics import (
    classification_metrics,
    positive_scores,
    regression_metrics,
    roc_auc,
    score_kind,
)
from analytics.ml.persistence import SELECTED_DIR, load_metadata, load_pipeline
from analytics.ml.report import render
from analytics.ml.results import MetricSummary, ModelResult
from analytics.ml.selection import select
from analytics.preprocessing import (
    TARGET_COLUMNS,
    LeakageError,
    Scenario,
    feature_columns,
    prepare_cohort,
)
from tests.factories import VALID_ROW, make_varied_rows, write_cohort

FAST = TrainingConfig(cv_folds=3, search=SearchMode.MINIMAL, n_jobs=1)


def _dataset(tmp_path, cohort=Cohort.MATH, n=150, seed=3):
    name = "student-mat.csv" if cohort is Cohort.MATH else "student-por.csv"
    write_cohort(tmp_path / name, make_varied_rows(n, seed=seed))
    return prepare_cohort(load_cohort(tmp_path, cohort))


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Both synthetic cohorts trained with the minimal search and saved once."""
    raw = tmp_path_factory.mktemp("raw")
    models_dir = tmp_path_factory.mktemp("models")
    items = [
        train_cohort(_dataset(raw, Cohort.MATH, 150, 3), FAST),
        train_cohort(_dataset(raw, Cohort.PORTUGUESE, 170, 4), FAST),
    ]
    results = save(items, FAST, models_dir)
    return items, results, models_dir


def _record(scenario: Scenario) -> dict:
    record = {k: v for k, v in VALID_ROW.items() if k not in {"G1", "G2", "G3"}}
    for grade in feature_columns(scenario):
        if grade in {"G1", "G2"}:
            record[grade] = VALID_ROW[grade]
    return record


# --- Model definitions and pipelines --------------------------------------------------


def test_registry_defines_the_required_models():
    assert [s.key for s in MODELS[Task.REGRESSION]] == [
        "mean_baseline",
        "linear_regression",
        "decision_tree",
        "random_forest",
    ]
    assert [s.key for s in MODELS[Task.CLASSIFICATION]] == [
        "majority_baseline",
        "logistic_regression",
        "decision_tree",
        "knn",
        "svm",
        "random_forest",
    ]
    for task, specs in MODELS.items():
        assert all(s.task is task for s in specs)
        assert len({s.complexity for s in specs}) == len(specs)  # unambiguous tie-breaks
        assert sum(s.baseline for s in specs) == 1


@pytest.mark.parametrize("task", list(Task))
@pytest.mark.parametrize("scenario", list(Scenario))
def test_every_model_builds_a_preprocessing_pipeline(task, scenario):
    for spec in MODELS[task]:
        pipeline = build_pipeline(spec, scenario, random_state=42)
        assert [name for name, _ in pipeline.steps] == ["prep", "model"]
        assert pipeline.named_steps["prep"].named_steps["guard"].scenario == scenario
        numeric = pipeline.named_steps["prep"].named_steps["columns"].transformers[3][1]
        assert ("scale" in numeric.named_steps) is spec.scale_numeric


def test_seeded_estimators_receive_the_random_state():
    for task in Task:
        for spec in MODELS[task]:
            params = spec.factory(7).get_params()
            if "random_state" in params:
                assert params["random_state"] == 7, spec.key


def test_classifiers_handle_imbalance_with_class_weights_not_resampling():
    for spec in MODELS[Task.CLASSIFICATION]:
        params = spec.factory(0).get_params()
        if "class_weight" in params and not spec.baseline:
            assert params["class_weight"] == "balanced", spec.key
            assert spec.class_weight == "balanced"
    assert get_spec(Task.CLASSIFICATION, "knn").class_weight is None


def test_search_spaces_are_compact_and_prefixed():
    for task in Task:
        for spec in MODELS[task]:
            full = search_space(spec)
            assert all(k.startswith("model__") for k in full)
            assert np.prod([len(v) for v in full.values()] or [1]) <= 36
            minimal = search_space(spec, SearchMode.MINIMAL)
            assert all(len(v) == 1 for v in minimal.values())
    assert search_space(get_spec(Task.REGRESSION, "linear_regression")) == {}
    rf = search_space(get_spec(Task.REGRESSION, "random_forest"))
    assert set(rf) == {
        f"model__{p}"
        for p in (
            "n_estimators",
            "max_depth",
            "min_samples_split",
            "min_samples_leaf",
            "max_features",
        )
    }


# --- Leakage and scenario isolation ---------------------------------------------------


@pytest.mark.parametrize("scenario", list(Scenario))
def test_fitted_pipelines_never_see_outcomes(tmp_path, scenario):
    data = _dataset(tmp_path)
    split = data.split(scenario)
    for task in Task:
        for spec in MODELS[task]:
            pipeline = build_pipeline(spec, scenario, 0)
            y = split.y_train_regression if task is Task.REGRESSION else split.y_train_risk
            pipeline.fit(split.X_train, y)
            encoded = set(pipeline[:-1].get_feature_names_out())
            assert not encoded & TARGET_COLUMNS
            assert set(pipeline.named_steps["prep"][0].feature_names_in_) == set(
                feature_columns(scenario)
            )


def test_pipeline_rejects_outcome_and_other_scenario_columns(tmp_path):
    data = _dataset(tmp_path)
    split = data.split(Scenario.EARLY)
    pipeline = build_pipeline(get_spec(Task.REGRESSION, "linear_regression"), Scenario.EARLY, 0)

    with pytest.raises(LeakageError):
        pipeline.fit(split.X_train.assign(G3=split.y_train_regression), split.y_train_regression)
    with pytest.raises(LeakageError):
        pipeline.fit(split.X_train.assign(G1=1.0), split.y_train_regression)


# --- Cross-validation -----------------------------------------------------------------


def test_splitters_are_seeded_and_stratified_for_classification(tmp_path):
    data = _dataset(tmp_path, n=200)
    split = data.split(Scenario.EARLY)
    reg, cls = splitter(Task.REGRESSION, FAST), splitter(Task.CLASSIFICATION, FAST)

    assert isinstance(reg, KFold) and not isinstance(reg, StratifiedKFold)
    assert isinstance(cls, StratifiedKFold)
    assert (reg.n_splits, reg.random_state, reg.shuffle) == (3, 42, True)
    y = split.y_train_risk
    overall = y.sum() / len(y)
    for _, valid in cls.split(split.X_train, y):
        assert abs(y.iloc[valid].sum() - overall * len(valid)) <= 1
    first = [v.tolist() for _, v in cls.split(split.X_train, y)]
    second = [v.tolist() for _, v in splitter(Task.CLASSIFICATION, FAST).split(split.X_train, y)]
    assert first == second


@pytest.mark.parametrize(
    ("task", "key"),
    [(Task.REGRESSION, "linear_regression"), (Task.CLASSIFICATION, "logistic_regression")],
)
def test_preprocessing_is_fitted_on_the_training_fold_only(tmp_path, task, key):
    data = _dataset(tmp_path)
    split = data.split(Scenario.MID_YEAR)
    y = split.y_train_regression if task is Task.REGRESSION else split.y_train_risk
    seen = []

    def check(k, estimator, X_fit, X_val):
        pipeline = estimator.best_estimator_ if isinstance(estimator, GridSearchCV) else estimator
        scaler = (
            pipeline.named_steps["prep"].named_steps["columns"].named_transformers_["numeric"]
        ).named_steps["scale"]
        columns = list(scaler.feature_names_in_)
        np.testing.assert_allclose(scaler.mean_, X_fit[columns].mean().to_numpy())
        assert not set(X_fit.index) & set(X_val.index)
        assert set(X_fit.index) | set(X_val.index) == set(split.X_train.index)
        seen.append(k)

    nested_cv(get_spec(task, key), Scenario.MID_YEAR, split.X_train, y, FAST, on_fold=check)
    assert seen == [0, 1, 2]


def test_tuning_and_cv_never_use_the_test_set(tmp_path):
    data = _dataset(tmp_path, n=160)
    split = data.split(Scenario.FULL_HISTORY)
    spec = get_spec(Task.CLASSIFICATION, "decision_tree")
    config = TrainingConfig(cv_folds=3, n_jobs=1)  # the real grid, so tuning has choices
    args = (spec, Scenario.FULL_HISTORY, split.X_train, split.y_train_risk)

    original = evaluate(*args, split.X_test, split.y_test_risk, config)
    poisoned_X = split.X_test.assign(G1=0.0, G2=20.0, age=22.0)
    poisoned = evaluate(*args, poisoned_X, 1 - split.y_test_risk, config)

    assert poisoned.best_params == original.best_params
    assert poisoned.outer_fold_params == original.outer_fold_params
    assert {k: v.folds for k, v in poisoned.cv.items()} == {
        k: v.folds for k, v in original.cv.items()
    }


def test_grid_search_wraps_the_whole_pipeline():
    spec = get_spec(Task.CLASSIFICATION, "svm")
    estimator = tuned_estimator(spec, Scenario.EARLY, FAST)
    assert isinstance(estimator, GridSearchCV)
    assert [n for n, _ in estimator.estimator.steps] == ["prep", "model"]
    assert estimator.scoring == "f1"
    assert isinstance(estimator.cv, StratifiedKFold)
    plain = tuned_estimator(get_spec(Task.REGRESSION, "linear_regression"), Scenario.EARLY, FAST)
    assert not isinstance(plain, GridSearchCV)


# --- Metrics ----------------------------------------------------------------------------


def test_regression_metrics_exact():
    m = regression_metrics([10, 12, 8, 14], [11, 12, 6, 14])
    assert m["mae"] == pytest.approx(0.75)
    assert m["mse"] == pytest.approx(1.25)
    assert m["rmse"] == pytest.approx(1.25**0.5)
    assert m["r2"] == pytest.approx(1 - 5 / 20)
    assert regression_metrics([5, 5], [4, 6])["r2"] is None  # undefined for a constant target


def test_classification_metrics_exact():
    y = [1, 1, 1, 0, 0, 0, 0, 0]
    pred = [1, 1, 0, 1, 0, 0, 0, 0]
    scores = [0.9, 0.8, 0.3, 0.6, 0.2, 0.1, 0.4, 0.05]
    m = classification_metrics(y, pred, scores)
    assert m["accuracy"] == pytest.approx(6 / 8)
    assert m["precision"] == pytest.approx(2 / 3)
    assert m["recall"] == pytest.approx(2 / 3)
    assert m["specificity"] == pytest.approx(4 / 5)
    assert m["f1"] == pytest.approx(2 / 3)
    assert m["balanced_accuracy"] == pytest.approx((2 / 3 + 4 / 5) / 2)
    # 15 positive/negative pairs; the 0.3 positive is out-ranked by 0.6 and 0.4.
    assert m["roc_auc"] == pytest.approx(13 / 15)


def test_roc_auc_uses_scores_not_labels():
    y = [1, 1, 0, 0]
    assert classification_metrics(y, [0, 0, 0, 0], [0.4, 0.3, 0.2, 0.1])["roc_auc"] == 1.0


def test_undefined_metrics_are_none():
    no_positive_predictions = classification_metrics([1, 0, 0], [0, 0, 0], [0.1, 0.1, 0.1])
    assert no_positive_predictions["precision"] is None
    assert no_positive_predictions["recall"] == 0.0 and no_positive_predictions["f1"] == 0.0
    assert no_positive_predictions["roc_auc"] == 0.5

    one_class = classification_metrics([0, 0, 0], [0, 1, 0], [0.1, 0.7, 0.2])
    assert one_class["roc_auc"] is None and one_class["recall"] is None
    assert one_class["f1"] is None and one_class["specificity"] == pytest.approx(2 / 3)
    assert roc_auc([1, 1], [0.2, 0.9]) is None


def test_scores_come_from_probabilities_or_decision_function(tmp_path):
    data = _dataset(tmp_path)
    split = data.split(Scenario.EARLY)
    X, y = split.X_train, split.y_train_risk
    logistic = build_pipeline(
        get_spec(Task.CLASSIFICATION, "logistic_regression"), Scenario.EARLY, 0
    )
    svm = build_pipeline(get_spec(Task.CLASSIFICATION, "svm"), Scenario.EARLY, 0)
    logistic.fit(X, y)
    svm.fit(X, y)

    np.testing.assert_allclose(positive_scores(logistic, X), logistic.predict_proba(X)[:, 1])
    np.testing.assert_allclose(positive_scores(svm, X), svm.decision_function(X))
    assert (score_kind(logistic), score_kind(svm)) == ("probability", "decision_function")


# --- Baselines, selection and diagnostics ------------------------------------------------


def test_baselines_are_trivial_predictors(trained):
    items, *_ = trained
    c = items[0].results
    for r in c.regression:
        if r.baseline:
            assert r.cv["r2"].mean <= 0.05
    for r in c.classification:
        if r.baseline:
            assert r.test["recall"] == 0.0 and r.test["precision"] is None
            assert r.test["roc_auc"] == 0.5
            assert r.test_predicted_positive == 0
            assert {d.code for d in r.diagnostics} >= {"single_class", "precision_undefined"}


def _result(model, mean, std, complexity, baseline=False, metric="rmse"):
    summary = MetricSummary(mean=mean, std=std, folds=[mean] * 5, defined_folds=5)
    task = Task.REGRESSION if metric == "rmse" else Task.CLASSIFICATION
    return ModelResult(
        cohort="math",
        task=task,
        scenario=Scenario.EARLY,
        model=model,
        label=model,
        family="x",
        baseline=baseline,
        complexity=complexity,
        class_weight=None,
        search_space={},
        candidates=1,
        best_params={},
        outer_fold_params=[],
        cv={metric: summary},
        test={metric: 0.0},
        n_train=10,
        n_test=2,
        diagnostics=[],
    )


def test_selection_prefers_the_simpler_model_within_one_standard_error():
    results = [
        _result("base", 4.0, 0.1, 0, baseline=True),
        _result("simple", 3.05, 0.2, 1),
        _result("complex", 3.0, 0.2, 3),  # SE = 0.2 / √5 ≈ 0.089
    ]
    choice = select(results)
    assert (choice.model, choice.best_model) == ("simple", "complex")
    assert choice.within_tolerance == ["simple", "complex"]
    assert choice.beats_baseline

    results[1] = _result("simple", 3.2, 0.2, 1)
    assert select(results).model == "complex"


def test_selection_maximises_f1_and_ignores_baselines():
    results = [
        _result("base", 0.0, 0.0, 0, baseline=True, metric="f1"),
        _result("a", 0.50, 0.05, 1, metric="f1"),
        _result("b", 0.70, 0.05, 2, metric="f1"),
    ]
    choice = select(results)
    assert choice.model == "b" and choice.primary_metric == "f1" and choice.baseline_mean == 0.0


def test_selection_flags_models_that_do_not_beat_the_baseline():
    results = [_result("base", 3.0, 0.1, 0, baseline=True), _result("a", 3.5, 0.1, 1)]
    choice = select(results)
    assert not choice.beats_baseline and "does not improve" in choice.reason


# --- Training run ------------------------------------------------------------------------


def test_training_covers_every_scenario_task_and_model(trained):
    items, results, _ = trained
    for item in items:
        c = item.results
        assert {(r.scenario, r.model) for r in c.regression} == {
            (s, spec.key) for s in Scenario for spec in MODELS[Task.REGRESSION]
        }
        assert len(c.classification) == 3 * len(MODELS[Task.CLASSIFICATION])
        assert len(c.selections) == 6 and len(item.selected) == 6
        assert len(c.regression_errors) == len(c.classification_errors) == 3
        for r in [*c.regression, *c.classification]:
            assert r.n_train + r.n_test == c.n
            assert all(len(m.folds) == FAST.cv_folds for m in r.cv.values())
        assert c.risk["train"].at_risk + c.risk["test"].at_risk == c.risk["all"].at_risk
        assert c.risk["all"].at_risk_percent + c.risk["all"].not_at_risk_percent == pytest.approx(
            100
        )
    assert "NaN" not in results.model_dump_json()


def test_error_analysis_is_consistent_with_test_predictions(trained):
    items, *_ = trained
    c = items[0].results
    for e in c.classification_errors:
        assert e.confusion.tp + e.confusion.fn == e.by_class[0].n
        assert sum(g.count for g in e.false_negative_grades) == e.confusion.fn
        assert sum(g.count for g in e.false_positive_grades) == e.confusion.fp
        assert all(g.grade < 10 for g in e.false_negative_grades)
        assert all(g.grade >= 10 for g in e.false_positive_grades)
    for e in c.regression_errors:
        assert sum(b.n for b in e.by_band) == e.n
        assert sum(b.count for b in e.histogram) == e.n
        assert len(e.largest) == 10
        assert all(r.row >= 1 for r in e.largest)
        assert abs(e.largest[0].residual) >= abs(e.largest[-1].residual)


def test_zero_grade_sensitivity_uses_only_nonzero_test_students(trained):
    items, *_ = trained
    c = items[0].results
    zeros_in_test = c.n_test - next(z.test_n for z in c.zero_grade_sensitivity)
    assert zeros_in_test >= 0
    for z in c.zero_grade_sensitivity:
        assert z.train_zeros_removed > 0
        assert set(z.all_rows_model) == set(z.without_zeros_model) == {"mae", "mse", "rmse", "r2"}


def test_training_is_reproducible(tmp_path):
    data = _dataset(tmp_path, n=120)
    config = TrainingConfig(cv_folds=3, search=SearchMode.MINIMAL, n_jobs=1)
    options = {"scenarios": (Scenario.EARLY,)}
    first = train_cohort(data, config, **options).results
    second = train_cohort(data, config, **options).results
    assert first.model_dump() == second.model_dump()


def test_report_renders_generated_numbers_without_causal_language(trained):
    _, results, _ = trained
    text = render(results)
    assert "## Mathematics" in text and "## Portuguese language" in text
    for phrase in ("causes", "caused by", "leads to", "proves", "dropout prediction"):
        assert phrase not in text.lower()


# --- Persistence --------------------------------------------------------------------------


def test_persistence_round_trip(trained):
    items, results, models_dir = trained
    assert load_results(models_dir) == results
    files = sorted(p.name for p in (models_dir / SELECTED_DIR).iterdir())
    assert len(files) == 24  # 12 pipelines + 12 metadata files

    ev = items[0].selected[(Task.CLASSIFICATION, Scenario.EARLY)]
    meta = load_metadata(models_dir, "math", Task.CLASSIFICATION, Scenario.EARLY)
    pipeline = load_pipeline(models_dir, meta)
    assert type(pipeline) is type(ev.pipeline)
    assert meta.model == ev.spec.key and meta.random_state == 42
    assert meta.feature_columns == list(feature_columns(Scenario.EARLY))
    assert not set(meta.encoded_features) & TARGET_COLUMNS
    assert meta.software["scikit-learn"] == sklearn.__version__
    assert meta.cv_folds == 3 and meta.n_train + meta.n_test == items[0].results.n


def test_persisted_pipeline_predicts_like_the_trained_one(trained, tmp_path):
    items, _, models_dir = trained
    data = _dataset(tmp_path, Cohort.MATH, 150, 3)
    split = data.split(Scenario.FULL_HISTORY)
    for task in Task:
        ev = items[0].selected[(task, Scenario.FULL_HISTORY)]
        meta = load_metadata(models_dir, "math", task, Scenario.FULL_HISTORY)
        loaded = load_pipeline(models_dir, meta)
        np.testing.assert_array_equal(
            loaded.predict(split.X_test), ev.pipeline.predict(split.X_test)
        )


def test_tampered_or_incompatible_artifacts_are_refused(trained, tmp_path):
    _, _, models_dir = trained
    meta = load_metadata(models_dir, "math", Task.REGRESSION, Scenario.EARLY)

    with pytest.raises(ModelArtifactError, match="SHA-256"):
        load_pipeline(models_dir, meta.model_copy(update={"sha256": "0" * 64}))
    other = {**meta.software, "scikit-learn": "0.0.1"}
    with pytest.raises(ModelArtifactError, match="scikit-learn 0.0.1"):
        load_pipeline(models_dir, meta.model_copy(update={"software": other}))
    with pytest.raises(ModelArtifactError):
        load_results(tmp_path)


# --- Prediction service --------------------------------------------------------------------


@pytest.mark.parametrize("scenario", list(Scenario))
def test_record_frame_matches_scenario_columns(scenario):
    X = record_frame(_record(scenario), scenario)
    assert list(X.columns) == list(feature_columns(scenario))
    assert X["log_absences"].iloc[0] == pytest.approx(np.log1p(VALID_ROW["absences"]))
    assert X["has_past_failures"].iloc[0] == 0


def test_record_validation_rejects_leakage_and_bad_values():
    early = _record(Scenario.EARLY)
    with pytest.raises(LeakageError):
        record_frame({**early, "G3": 12}, Scenario.EARLY)
    with pytest.raises(LeakageError):
        record_frame({**early, "at_risk": 0}, Scenario.EARLY)
    with pytest.raises(LeakageError):
        record_frame({**early, "G1": 10}, Scenario.EARLY)
    with pytest.raises(InvalidRecordError, match="Missing"):
        record_frame(early, Scenario.MID_YEAR)
    with pytest.raises(InvalidRecordError, match="Mjob"):
        record_frame({**early, "Mjob": "astronaut"}, Scenario.EARLY)
    with pytest.raises(InvalidRecordError, match="age"):
        record_frame({**early, "age": 40}, Scenario.EARLY)
    with pytest.raises(InvalidRecordError, match="studytime"):
        record_frame({**early, "studytime": 2.5}, Scenario.EARLY)
    with pytest.raises(InvalidRecordError, match="Unknown"):
        record_frame({**early, "student_id": "x"}, Scenario.EARLY)
    with pytest.raises(InvalidRecordError):
        record_frame({**early, "failures": True}, Scenario.EARLY)
    with pytest.raises(InvalidRecordError):
        record_frame({**early, "absences": float("nan")}, Scenario.EARLY)


def test_prediction_service_returns_structured_output(trained):
    _, _, models_dir = trained
    service = PredictionService(models_dir)

    reg = service.predict("math", "regression", "full_history", _record(Scenario.FULL_HISTORY))
    assert 0 <= reg.predicted_grade <= 20 and reg.at_risk is None
    assert reg.model_test_metrics["rmse"] is not None

    cls = service.predict(
        Cohort.PORTUGUESE, Task.CLASSIFICATION, Scenario.EARLY, _record(Scenario.EARLY)
    )
    assert isinstance(cls.at_risk, bool) and cls.predicted_grade is None
    assert cls.score_kind in {"probability", "decision_function"}
    assert any("not a prediction of dropout" in c for c in cls.caveats)
    if cls.score_kind == "probability":
        assert 0 <= cls.score <= 1 and cls.at_risk == (cls.score > 0.5)


def test_prediction_service_only_serves_persisted_models(trained):
    items, _, models_dir = trained
    service = PredictionService(models_dir)
    chosen = items[0].selected[(Task.REGRESSION, Scenario.EARLY)].spec.key
    other = next(s.key for s in MODELS[Task.REGRESSION] if s.key != chosen)

    assert (
        service.predict("math", "regression", "early", _record(Scenario.EARLY), chosen).model
        == chosen
    )
    with pytest.raises(ModelNotAvailableError):
        service.predict("math", "regression", "early", _record(Scenario.EARLY), other)


def test_regression_predictions_are_limited_to_the_grade_scale(trained):
    items, _, models_dir = trained
    service = PredictionService(models_dir)
    meta, pipeline = service.model("math", Task.REGRESSION, Scenario.FULL_HISTORY)

    class Extreme:
        def predict(self, X):
            return np.array([27.5])

    service._cache[meta.artifact] = (meta, Extreme())
    out = service.predict("math", "regression", "full_history", _record(Scenario.FULL_HISTORY))
    assert (out.predicted_grade, out.raw_prediction) == (20, 27.5)
    service._cache[meta.artifact] = (meta, pipeline)
