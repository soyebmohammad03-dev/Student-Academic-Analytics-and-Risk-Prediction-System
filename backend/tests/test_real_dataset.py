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
