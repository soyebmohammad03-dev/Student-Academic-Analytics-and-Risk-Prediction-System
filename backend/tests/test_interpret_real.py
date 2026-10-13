"""Interpretability and risk analysis on the official files and persisted models.

Skipped until the dataset is downloaded and the models are trained.
"""

import pytest

from analytics.data import Cohort, load_cohort
from analytics.data.download import DEFAULT_RAW_DIR, verify
from analytics.interpret import CohortData, Interpreter
from analytics.interpret.attributes import attributes
from analytics.ml import PredictionService, Task
from analytics.ml.config import DEFAULT_MODELS_DIR
from analytics.ml.persistence import RESULTS_FILE
from analytics.preprocessing import TARGET_COLUMNS, Scenario, prepare_cohort
from analytics.risk import risk_profiles, suggest

pytestmark = [
    pytest.mark.skipif(bool(verify(DEFAULT_RAW_DIR)), reason="official dataset not downloaded"),
    pytest.mark.skipif(
        not (DEFAULT_MODELS_DIR / RESULTS_FILE).is_file(), reason="models not trained"
    ),
]


@pytest.fixture(scope="module")
def datasets():
    return {c: prepare_cohort(load_cohort(DEFAULT_RAW_DIR, c)) for c in Cohort}


@pytest.fixture(scope="module")
def interpreter(datasets):
    return Interpreter(
        PredictionService(DEFAULT_MODELS_DIR),
        lambda cohort, seed: CohortData.from_dataset(datasets[cohort], seed),
    )


def _test_record(dataset, scenario):
    split = dataset.split(scenario)
    row = dataset.validated.loc[split.test_index[0]]
    return {
        k: (v if isinstance(v, str) else int(v))
        for k, v in row.items()
        if k in attributes(scenario)
    }


@pytest.mark.parametrize("cohort", list(Cohort))
@pytest.mark.parametrize("task", list(Task))
@pytest.mark.parametrize("scenario", list(Scenario))
def test_real_explanations_are_additive_and_leak_free(
    datasets, interpreter, cohort, task, scenario
):
    record = _test_record(datasets[cohort], scenario)
    out = interpreter.explain(cohort, task, scenario, record, top=33, n_samples=64)
    e = out.explanation

    assert e.base_value + sum(c.contribution for c in e.contributions) == pytest.approx(
        e.prediction
    )
    assert {c.attribute for c in e.contributions} == set(attributes(scenario))
    assert not {c.attribute for c in e.contributions} & TARGET_COLUMNS
    assert out.prediction.model == interpreter.service.model(cohort, task, scenario)[0].model


@pytest.mark.parametrize(
    ("cohort", "n", "at_risk"), [(Cohort.MATH, 395, 130), (Cohort.PORTUGUESE, 649, 100)]
)
def test_real_profiles_use_every_student(datasets, cohort, n, at_risk):
    p = risk_profiles(datasets[cohort].analytical, str(cohort))
    assert (p.n, p.at_risk) == (n, at_risk)
    for s in p.single:
        assert sum(g.n for g in s.groups) == n


@pytest.mark.parametrize("cohort", list(Cohort))
def test_real_suggestions_have_supported_evidence(datasets, cohort):
    record = _test_record(datasets[cohort], Scenario.EARLY) | {
        "failures": 2,
        "studytime": 1,
        "absences": 15,
    }
    out = suggest(datasets[cohort].analytical, str(cohort), record)
    for item in out.suggestions:
        assert item.evidence.supported and item.evidence.p < 0.05
        assert item.evidence.group_risk_percent > item.evidence.comparison_risk_percent
    for item in out.not_shown:
        assert not item.evidence.supported


def test_real_absence_sensitivity_reports_the_zero_grade_pattern(datasets, interpreter):
    record = _test_record(datasets[Cohort.MATH], Scenario.FULL_HISTORY)
    curve = interpreter.sensitivity(
        Cohort.MATH, Task.REGRESSION, Scenario.FULL_HISTORY, record, "absences"
    )
    assert "students with G3 = 0 have 0 recorded absences" in curve.note


interpretability = pytest.mark.skipif(
    not (DEFAULT_MODELS_DIR / "interpretability.json").is_file(),
    reason="interpretability not built (python -m analytics.interpret.build)",
)


@interpretability
def test_persisted_interpretability_covers_all_selected_models():
    from analytics.interpret.build import load

    run = load(DEFAULT_MODELS_DIR)
    service = PredictionService(DEFAULT_MODELS_DIR)
    assert len(run.items) == 12
    for item in run.items:
        meta, _ = service.model(item.cohort, item.task, item.scenario)
        assert item.model == meta.model
        for method in item.methods:
            assert not {i.attribute for i in method.items} & TARGET_COLUMNS
        if item.task is Task.REGRESSION:
            assert any("G3 > 0" in m.method_label for m in item.methods)


@interpretability
def test_interpretability_document_is_current(datasets):
    from analytics.interpret.build import load
    from analytics.interpret.report import OUTPUT, render

    profiles = {str(c): risk_profiles(d.analytical, str(c)) for c, d in datasets.items()}
    assert OUTPUT.read_text(encoding="utf-8") == render(load(DEFAULT_MODELS_DIR), profiles), (
        "docs/INTERPRETABILITY.md is stale: run `python -m analytics.interpret.build`"
    )
