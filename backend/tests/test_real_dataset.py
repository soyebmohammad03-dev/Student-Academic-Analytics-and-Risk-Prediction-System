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
