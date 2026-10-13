"""Interpretability and risk analysis on synthetic cohorts (behaviour, not findings)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analytics.data import Cohort, load_cohort
from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.interpret import SENSITIVITY_ATTRIBUTES, CohortData, Interpreter, shapley_values
from analytics.interpret.attributes import attributes, encoded_attribute, model_input
from analytics.interpret.build import build
from analytics.interpret.importance import (
    calibration,
    coefficient_importance,
    impurity_importance,
    permutation_importance,
)
from analytics.interpret.report import render
from analytics.ml import (
    InvalidRecordError,
    ModelNotAvailableError,
    PredictionService,
    SearchMode,
    Task,
    TrainingConfig,
    save,
    train_cohort,
)
from analytics.ml.registry import MODELS
from analytics.preprocessing import (
    TARGET_COLUMNS,
    LeakageError,
    Scenario,
    build_preprocessor,
    prepare_cohort,
)
from analytics.risk import DISCLAIMER, PROFILE_VARIABLES, RULES, risk_profiles, suggest
from analytics.risk.suggestions import MODEL_FLAG_TEXT
from tests.factories import VALID_ROW, make_varied_rows, write_cohort

FAST = TrainingConfig(cv_folds=3, search=SearchMode.MINIMAL, n_jobs=1)
DEMOGRAPHIC = {"sex", "age", "address", "famsize", "Pstatus", "Medu", "Fedu", "Mjob", "Fjob"}
FORBIDDEN = (
    "punish", "disciplin", "sanction", "lazy", "will fail", "certain", "guarantee",
    "dropout", "drop out", "diagnos", "depress", "disorder", "parenting", "bad student",
)  # fmt: skip


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    raw = tmp_path_factory.mktemp("raw")
    write_cohort(raw / "student-mat.csv", make_varied_rows(160, seed=31))
    write_cohort(raw / "student-por.csv", make_varied_rows(170, seed=32))
    datasets = {c: prepare_cohort(load_cohort(raw, c)) for c in Cohort}
    models_dir = tmp_path_factory.mktemp("models")
    save([train_cohort(datasets[c], FAST) for c in Cohort], FAST, models_dir)
    service = PredictionService(models_dir)
    interpreter = Interpreter(
        service, lambda cohort, seed: CohortData.from_dataset(datasets[cohort], seed)
    )
    return {"raw": raw, "models": models_dir, "data": datasets, "service": service,
            "interpreter": interpreter}  # fmt: skip


def _record(scenario: Scenario) -> dict:
    record = {k: v for k, v in VALID_ROW.items() if k not in {"G1", "G2", "G3"}}
    for grade in ("G1", "G2"):
        if grade in attributes(scenario):
            record[grade] = VALID_ROW[grade]
    return record


# --- Feature-name alignment -------------------------------------------------------------


@pytest.mark.parametrize("scenario", list(Scenario))
def test_every_encoded_feature_maps_to_a_scenario_attribute(env, scenario):
    data = env["data"][Cohort.MATH]
    X = data.features(scenario).X
    names = build_preprocessor(scenario).fit(X).get_feature_names_out()
    mapped = {encoded_attribute(n)[0] for n in names}

    assert mapped == set(attributes(scenario))
    assert not mapped & TARGET_COLUMNS
    assert encoded_attribute("has_past_failures")[0] == "failures"
    assert encoded_attribute("log_absences")[0] == "absences"
    assert encoded_attribute("Mjob_at_home") == ("Mjob", "Mother's job = At home")
    if scenario is Scenario.EARLY:
        assert not {"G1", "G2"} & mapped


def test_attributes_never_include_outcomes():
    for scenario in Scenario:
        assert not set(attributes(scenario)) & TARGET_COLUMNS
    assert "G2" not in attributes(Scenario.MID_YEAR) and "G1" in attributes(Scenario.MID_YEAR)


# --- Shapley estimator --------------------------------------------------------------------


def _frame(record: dict, scenario: Scenario) -> pd.Series:
    from analytics.ml.predict import validated_record

    return validated_record(record, scenario).iloc[0]


def test_shapley_is_exact_for_an_interaction_with_one_background_row():
    scenario = Scenario.EARLY
    x = _frame({**_record(scenario), "studytime": 4, "failures": 2}, scenario)
    z = _frame({**_record(scenario), "studytime": 1, "failures": 0}, scenario).to_frame().T

    def output(X):
        return X["studytime"].to_numpy() * X["failures"].to_numpy()

    est = shapley_values(output, x, z, scenario, n_samples=8, seed=1)
    names = list(est.attributes)
    # f(x) = 8, f(z) = 0; each attribute gets half of the interaction (antithetic pairs).
    phi_study = 0.5 * ((4 * 0 - 1 * 0) + (4 * 2 - 1 * 2))
    phi_fail = 0.5 * ((1 * 2 - 1 * 0) + (4 * 2 - 4 * 0))
    assert est.values[names.index("studytime")] == pytest.approx(phi_study)
    assert est.values[names.index("failures")] == pytest.approx(phi_fail)
    others = [
        v for n, v in zip(names, est.values, strict=True) if n not in {"studytime", "failures"}
    ]
    assert np.allclose(others, 0)
    assert est.base_value + est.values.sum() == pytest.approx(est.prediction) == pytest.approx(8)


def test_shapley_matches_closed_form_for_a_linear_model(env):
    scenario = Scenario.FULL_HISTORY
    meta, pipeline = env["service"].model(Cohort.MATH, Task.REGRESSION, scenario)
    data = env["data"][Cohort.MATH]
    background = data.analytical[list(attributes(scenario))].iloc[:40]
    x = _frame(_record(scenario), scenario)

    from sklearn.linear_model import LinearRegression

    linear = pipeline
    if not isinstance(pipeline.named_steps["model"], LinearRegression):
        from analytics.ml.registry import build_pipeline, get_spec

        linear = build_pipeline(get_spec(Task.REGRESSION, "linear_regression"), scenario, 0)
        split = data.split(scenario)
        linear.fit(split.X_train, split.y_train_regression)

    est = shapley_values(linear.predict, x, background, scenario, n_samples=64, seed=3)
    # For an additive model each sample's contribution is f_j(x_j) − f_j(z_j); the
    # average over the sampled z is exact, so compare with switching one attribute.
    rng = np.random.default_rng(3)
    _ = [rng.permutation(len(est.attributes)) for _ in range(32)]
    z_index = rng.integers(len(background), size=32)
    Z = background.iloc[np.concatenate([z_index, z_index])]
    for j, name in enumerate(est.attributes):
        switched = Z.copy()
        switched[name] = x[name]
        expected = np.mean(
            linear.predict(model_input(switched, scenario))
            - linear.predict(model_input(Z, scenario))
        )
        assert est.values[j] == pytest.approx(expected, abs=1e-8), name


def test_shapley_is_deterministic_and_validates_sample_count(env):
    scenario = Scenario.EARLY
    _, pipeline = env["service"].model(Cohort.MATH, Task.REGRESSION, scenario)
    bg = env["data"][Cohort.MATH].analytical[list(attributes(scenario))]
    x = _frame(_record(scenario), scenario)
    a = shapley_values(pipeline.predict, x, bg, scenario, n_samples=16, seed=5)
    b = shapley_values(pipeline.predict, x, bg, scenario, n_samples=16, seed=5)
    np.testing.assert_array_equal(a.values, b.values)
    with pytest.raises(ValueError):
        shapley_values(pipeline.predict, x, bg, scenario, n_samples=15)


# --- Global importance --------------------------------------------------------------------


@pytest.mark.parametrize("task", list(Task))
@pytest.mark.parametrize("scenario", list(Scenario))
def test_global_importance_methods_fit_the_model_type(env, task, scenario):
    meta, pipeline = env["service"].model(Cohort.PORTUGUESE, task, scenario)
    data = env["data"][Cohort.PORTUGUESE]
    split = data.split(scenario)
    names = list(attributes(scenario))
    y = split.y_test_regression if task is Task.REGRESSION else split.y_test_risk
    perm = permutation_importance(
        meta, pipeline, data.analytical.loc[split.test_index, names], y, repeats=3
    )

    assert [i.attribute for i in perm.items] != [] and {i.attribute for i in perm.items} == set(
        names
    )
    assert [i.rank for i in perm.items] == list(range(1, len(names) + 1))
    assert all(i.std is not None for i in perm.items)
    assert any("not evidence" in lim for lim in perm.limitations)

    estimator = pipeline.named_steps["model"]
    impurity = impurity_importance(meta, pipeline)
    coefficients = coefficient_importance(meta, pipeline)
    assert (impurity is not None) == hasattr(estimator, "feature_importances_")
    assert (coefficients is not None) == hasattr(estimator, "coef_")
    if impurity:
        assert sum(i.value for i in impurity.items) == pytest.approx(1.0)
        assert {i.attribute for i in impurity.items} <= set(names)
    if coefficients:
        assert [i.feature for i in coefficients.items if i.attribute in TARGET_COLUMNS] == []
        assert len(coefficients.items) == len(meta.encoded_features)


def test_calibration_only_for_probabilities(env):
    meta, _ = env["service"].model(Cohort.MATH, Task.CLASSIFICATION, Scenario.EARLY)
    scores = np.array([0.1, 0.3, 0.5, 0.9, 1.0])
    y = np.array([0, 0, 1, 1, 1])
    result = calibration(meta.model_copy(update={"score_kind": "probability"}), scores, y)
    assert sum(b.n for b in result.bins) == 5 and result.bins[-1].n == 2
    assert result.brier == pytest.approx(np.mean((scores - y) ** 2))
    assert (
        calibration(meta.model_copy(update={"score_kind": "decision_function"}), scores, y) is None
    )


# --- Individual explanations ----------------------------------------------------------


@pytest.mark.parametrize("cohort", list(Cohort))
@pytest.mark.parametrize("task", list(Task))
@pytest.mark.parametrize("scenario", list(Scenario))
def test_explanations_match_the_selected_model(env, cohort, task, scenario):
    out = env["interpreter"].explain(cohort, task, scenario, _record(scenario), top=5, n_samples=32)
    e, p = out.explanation, out.prediction
    meta, _ = env["service"].model(cohort, task, scenario)

    assert p.model == meta.model and (p.cohort, p.task, p.scenario) == (cohort, task, scenario)
    assert len(e.contributions) == 5 and e.other_attributes == len(attributes(scenario)) - 5
    total = e.base_value + sum(c.contribution for c in e.contributions) + e.other_contribution
    assert total == pytest.approx(e.prediction)
    assert not {c.attribute for c in e.contributions} & TARGET_COLUMNS
    if task is Task.REGRESSION:
        assert e.prediction == pytest.approx(p.raw_prediction)
        assert p.probability is None and out.score_percentile is None
    else:
        assert e.prediction == pytest.approx(p.score)
        assert 0 <= out.score_percentile <= 100
        assert (p.probability is not None) == (p.score_kind == "probability")
        assert ("not a probability" in e.output) == (p.score_kind == "decision_function")


def test_explanation_rejects_leakage_and_unpersisted_models(env):
    interp = env["interpreter"]
    with pytest.raises(LeakageError):
        interp.explain(
            Cohort.MATH, Task.REGRESSION, Scenario.EARLY, {**_record(Scenario.EARLY), "G3": 9}
        )
    with pytest.raises(LeakageError):
        interp.explain(
            Cohort.MATH, Task.REGRESSION, Scenario.EARLY, {**_record(Scenario.EARLY), "G2": 9}
        )
    with pytest.raises(InvalidRecordError):
        interp.explain(Cohort.MATH, Task.REGRESSION, Scenario.MID_YEAR, _record(Scenario.EARLY))
    chosen = env["service"].model(Cohort.MATH, Task.REGRESSION, Scenario.EARLY)[0].model
    other = next(s.key for s in MODELS[Task.REGRESSION] if s.key != chosen)
    with pytest.raises(ModelNotAvailableError):
        interp.explain(Cohort.MATH, Task.REGRESSION, Scenario.EARLY, _record(Scenario.EARLY), other)


# --- Sensitivity ------------------------------------------------------------------------


def test_sensitivity_varies_one_attribute_over_documented_values(env):
    interp = env["interpreter"]
    curve = interp.sensitivity(
        Cohort.MATH, Task.CLASSIFICATION, Scenario.EARLY, _record(Scenario.EARLY), "studytime"
    )
    codes = [str(v.code) for v in COLUMNS_BY_NAME["studytime"].allowed]
    assert [p.value for p in curve.points] == codes
    assert [p.current for p in curve.points].count(True) == 1
    data = CohortData.from_dataset(env["data"][Cohort.MATH], 42)
    assert sum(p.support for p in curve.points) == len(data.train)
    assert all(p.at_risk is not None and p.predicted_grade is None for p in curve.points)
    assert "not what would happen" in curve.note

    absences = interp.sensitivity(
        Cohort.MATH, Task.REGRESSION, Scenario.EARLY, _record(Scenario.EARLY), "absences"
    )
    assert all(0 <= p.predicted_grade <= 20 for p in absences.points)
    assert max(int(p.value) for p in absences.points) <= max(data.train["absences"].max(), 0)

    for attribute in ("sex", "Medu", "G1", "G3"):
        with pytest.raises(InvalidRecordError):
            interp.sensitivity(
                Cohort.MATH, Task.REGRESSION, Scenario.EARLY, _record(Scenario.EARLY), attribute
            )
    assert not set(SENSITIVITY_ATTRIBUTES) & DEMOGRAPHIC


def test_scenario_sensitivity_uses_only_available_grades(env):
    interp = env["interpreter"]
    full = interp.scenario_sensitivity(Cohort.MATH, Task.REGRESSION, _record(Scenario.FULL_HISTORY))
    early = interp.scenario_sensitivity(Cohort.MATH, Task.REGRESSION, _record(Scenario.EARLY))
    assert [i.scenario for i in full.items] == list(
        (Scenario.EARLY, Scenario.MID_YEAR, Scenario.FULL_HISTORY)
    )
    assert [i.scenario for i in early.items] == [Scenario.EARLY]
    assert early.skipped == ["mid_year", "full_history"]
    with pytest.raises(LeakageError):
        interp.scenario_sensitivity(
            Cohort.MATH, Task.REGRESSION, {**_record(Scenario.EARLY), "G3": 5}
        )


# --- Risk profiles --------------------------------------------------------------------------


@pytest.mark.parametrize("cohort", list(Cohort))
def test_risk_profiles_report_real_group_sizes(env, cohort):
    data = env["data"][cohort].analytical
    p = risk_profiles(data, str(cohort))
    n = len(data)

    assert p.n == n and p.at_risk == int(data["at_risk"].sum())
    assert [s.variable for s in p.single] == list(PROFILE_VARIABLES)
    assert not {s.variable for s in p.single} & DEMOGRAPHIC
    for s in p.single:
        assert sum(g.n for g in s.groups) == n
        assert sum(g.at_risk for g in s.groups) == p.at_risk
        for g in s.groups:
            assert g.risk_percent == pytest.approx(100 * g.at_risk / g.n)
            assert g.reliable == (g.n >= 10)
            assert g.risk_ci.low <= g.risk_percent / 100 <= g.risk_ci.high
        assert 0 <= s.p_adjusted <= 1
    for pair in p.pairs:
        assert sum(c.n for c in pair.cells) == n
        assert all(c.risk_percent is None for c in pair.cells if c.n == 0)
    assert any("not causal" in note for note in p.notes)


# --- Suggestions ------------------------------------------------------------------------------


def _texts():
    return [r.text for r in RULES] + [r.trigger_text for r in RULES] + [MODEL_FLAG_TEXT, DISCLAIMER]


def test_suggestion_wording_is_cautious_and_non_punitive():
    for text in _texts():
        lowered = text.lower()
        for word in FORBIDDEN:
            assert word not in lowered or (
                word in {"disciplin", "diagnos"} and text == DISCLAIMER
            ), (word, text)
    for rule in RULES:
        assert rule.text.startswith("Consider ")
    assert MODEL_FLAG_TEXT.startswith("Consider ")
    assert "must not be used for disciplinary decisions" in DISCLAIMER


def _risk_data(n_fail_risk: int) -> pd.DataFrame:
    """60 students: 20 with past failures (n_fail_risk at risk), 40 without (4 at risk)."""
    rows = []
    for i in range(60):
        failed = i < 20
        at_risk = (i < n_fail_risk) if failed else (i < 24)
        rows.append(
            {"failures": 1 if failed else 0, "studytime": 2, "absences": 0, "at_risk": int(at_risk)}
        )
    return pd.DataFrame(rows)


def test_suggestions_require_supporting_evidence():
    record = {**VALID_ROW, "failures": 2}
    shown = suggest(_risk_data(15), "math", record)
    hidden = suggest(_risk_data(3), "math", record)

    assert [s.key for s in shown.suggestions] == ["past_difficulties"]
    assert shown.suggestions[0].evidence.supported and shown.suggestions[0].evidence.p < 0.05
    assert shown.suggestions[0].evidence.group_n == 20
    assert hidden.suggestions == [] and [s.key for s in hidden.not_shown] == ["past_difficulties"]
    assert suggest(_risk_data(15), "math", {**VALID_ROW, "failures": 0}).suggestions == []


def test_suggestions_ignore_demographics_and_are_deterministic():
    data = _risk_data(15)
    base = {**VALID_ROW, "failures": 1}
    varied = {**base, "sex": "M", "age": 19, "Medu": 0, "Fedu": 4, "Mjob": "health", "address": "R"}
    a, b = suggest(data, "math", base), suggest(data, "math", varied)
    assert a.model_dump() == b.model_dump() == suggest(data, "math", base).model_dump()


def test_model_flag_suggestion_cites_model_performance(env):
    flag = env["service"].predict(
        Cohort.MATH, Task.CLASSIFICATION, Scenario.EARLY, _record(Scenario.EARLY)
    )
    flag = flag.model_copy(update={"at_risk": True})
    out = suggest(env["data"][Cohort.MATH].analytical, "math", _record(Scenario.EARLY), flag)
    item = next(s for s in out.suggestions if s.key == "model_flag")
    assert item.evidence.kind == "model_performance" and "can be wrong" in item.evidence.summary


# --- Build and report ----------------------------------------------------------------------


def test_build_covers_every_persisted_model_and_renders(env):
    run = build(env["raw"], env["models"], repeats=2, shapley_samples=8)
    assert len(run.items) == 12
    for item in run.items:
        methods = {m.method for m in item.methods}
        assert {"permutation_test", "mean_abs_shapley"} <= methods
        assert (item.calibration is not None) == (
            item.task is Task.CLASSIFICATION
            and env["service"].model(item.cohort, item.task, item.scenario)[0].score_kind
            == "probability"
        )
    profiles = {str(c): risk_profiles(env["data"][c].analytical, str(c)) for c in Cohort}
    text = render(run, profiles)
    assert "## Mathematics" in text and "## Portuguese language" in text
    for phrase in ("causes", "caused by", "leads to", "proves", "dropout prediction"):
        assert phrase not in text.lower()
