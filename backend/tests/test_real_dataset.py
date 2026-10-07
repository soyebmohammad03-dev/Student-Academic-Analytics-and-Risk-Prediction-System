"""Integration checks against the official files. Skipped until they are downloaded."""

import pytest

from analytics.data import Cohort, find_overlap, load_cohort, validate
from analytics.data.download import DEFAULT_RAW_DIR, verify

pytestmark = pytest.mark.skipif(
    bool(verify(DEFAULT_RAW_DIR)), reason="official dataset not downloaded"
)


@pytest.mark.parametrize(("cohort", "rows"), [(Cohort.MATH, 395), (Cohort.PORTUGUESE, 649)])
def test_official_cohort_is_valid(cohort, rows):
    report = validate(load_cohort(DEFAULT_RAW_DIR, cohort))

    assert (report.rows, report.columns) == (rows, 33)
    assert report.status == "pass"
    assert report.missing_values == report.invalid_values == report.duplicate_rows == 0


def test_official_overlap_reproduces_uci_join_count():
    math = load_cohort(DEFAULT_RAW_DIR, Cohort.MATH).data
    por = load_cohort(DEFAULT_RAW_DIR, Cohort.PORTUGUESE).data
    report = find_overlap(math, por)

    assert report.join_pairs == 382  # the figure quoted in UCI's student.txt
    assert report.unambiguous_matches <= report.join_pairs


@pytest.mark.parametrize(
    ("cohort", "at_risk", "train", "test"),
    [(Cohort.MATH, 130, 316, 79), (Cohort.PORTUGUESE, 100, 519, 130)],
)
def test_official_preprocessing(cohort, at_risk, train, test):
    import hashlib

    from analytics.data import COHORTS
    from analytics.preprocessing import Scenario, build_report, prepare_cohort

    path = DEFAULT_RAW_DIR / COHORTS[cohort].filename
    dataset = prepare_cohort(load_cohort(DEFAULT_RAW_DIR, cohort))
    encoded = {s: len(build_report(dataset, s).encoded_feature_names) for s in Scenario}

    assert hashlib.sha256(path.read_bytes()).hexdigest() == COHORTS[cohort].sha256
    assert int(dataset.risk_target().sum()) == at_risk
    assert encoded == {Scenario.FULL_HISTORY: 46, Scenario.MID_YEAR: 45, Scenario.EARLY: 44}
    split = dataset.split(Scenario.EARLY)
    assert (len(split.X_train), len(split.X_test)) == (train, test)


# --- Phase 4: statistics on the official files -------------------------------------------

CAUSAL_PHRASES = (
    "causes",
    "caused by",
    "leads to",
    "results in",
    "proves",
    "because of",
    "effect of",
)


def _analytical(cohort):
    from analytics.preprocessing import prepare_cohort

    return prepare_cohort(load_cohort(DEFAULT_RAW_DIR, cohort)).analytical


@pytest.mark.parametrize(
    ("cohort", "n", "zeros"), [(Cohort.MATH, 395, 38), (Cohort.PORTUGUESE, 649, 15)]
)
def test_official_statistics_include_every_student(cohort, n, zeros):
    from analytics.statistics import describe, distributions

    data = _analytical(cohort)
    described = describe(data, str(cohort))
    g3 = next(g for g in distributions(data, str(cohort)).grades if g.variable == "G3")

    assert all(s.n == n for s in described.numeric)
    assert (g3.summary.n, g3.zero_count) == (n, zeros)


@pytest.mark.parametrize("cohort", list(Cohort))
def test_official_results_are_valid_and_non_causal(cohort):
    from analytics.statistics import (
        COMPARISON_VARIABLES,
        associations,
        compare_groups,
        correlations,
        research_questions,
    )

    data = _analytical(cohort)
    results = [
        research_questions(data, str(cohort)),
        correlations(data, str(cohort)),
        associations(data, str(cohort)),
        *(compare_groups(data, v) for v in COMPARISON_VARIABLES),
    ]
    for result in results:
        dumped = result.model_dump()
        text = result.model_dump_json()
        assert "NaN" not in text and "Infinity" not in text
        for phrase in CAUSAL_PHRASES:
            assert phrase not in text.lower(), (phrase, type(result).__name__)
        _check_p_values(dumped)


def _check_p_values(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"p", "p_adjusted", "shapiro_p"} and isinstance(value, float | int):
                assert 0 <= value <= 1
            _check_p_values(value)
    elif isinstance(node, list):
        for value in node:
            _check_p_values(value)


def test_official_findings_document_is_current():
    from analytics.statistics.findings import OUTPUT, render

    assert OUTPUT.read_text(encoding="utf-8") == render(), (
        "docs/STATISTICAL_FINDINGS.md is stale: run `python -m analytics.statistics.findings`"
    )


def test_official_raw_files_untouched_after_analysis():
    import hashlib

    from analytics.data import COHORTS
    from analytics.statistics import eda, research_questions

    for cohort in Cohort:
        data = _analytical(cohort)
        research_questions(data, str(cohort))
        eda(data, str(cohort))
        path = DEFAULT_RAW_DIR / COHORTS[cohort].filename
        assert hashlib.sha256(path.read_bytes()).hexdigest() == COHORTS[cohort].sha256
