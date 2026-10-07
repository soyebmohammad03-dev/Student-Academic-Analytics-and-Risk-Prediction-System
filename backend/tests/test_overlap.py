import pandas as pd

from analytics.data.overlap import find_overlap
from tests.factories import make_rows


def frame(rows):
    return pd.DataFrame(rows)


def test_overlap_separates_unambiguous_and_ambiguous_matches():
    # Profiles are distinguished by age; absences differs per row and is not a match key.
    math = frame(make_rows(1, age=15) + make_rows(2, age=16) + make_rows(1, age=18))
    por = frame(make_rows(1, age=15) + make_rows(1, age=16) + make_rows(1, age=20))

    report = find_overlap(math, por)

    assert report.unambiguous_matches == 1  # age 15: unique in both files
    assert report.ambiguous_profiles == 1  # age 16: two math students share the profile
    assert report.join_pairs == 3  # plain join counts 1 + 2 * 1
    assert report.math_rows_matched == 3
    assert report.portuguese_rows_matched == 2
