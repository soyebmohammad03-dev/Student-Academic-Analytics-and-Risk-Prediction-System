import pytest

from analytics.data import Cohort, DatasetNotFoundError, load_cohort, validate
from analytics.data.dictionary import COLUMN_NAMES
from tests.factories import make_rows, write_cohort


def report_for(tmp_path, rows, columns=None):
    write_cohort(tmp_path / "student-mat.csv", rows, columns)
    return validate(load_cohort(tmp_path, Cohort.MATH))


def check(report, key):
    return next(c for c in report.checks if c.key == key)


def test_missing_file_raises_with_instructions(tmp_path):
    with pytest.raises(DatasetNotFoundError, match="analytics.data.download"):
        load_cohort(tmp_path, Cohort.MATH)


def test_loads_typed_columns_including_quoted_numbers(tmp_path):
    write_cohort(tmp_path / "student-mat.csv", make_rows(3, G1="7"))  # quoted, as in UCI file
    loaded = load_cohort(tmp_path, Cohort.MATH)

    assert loaded.data.shape == (3, 33)
    assert str(loaded.data["G1"].dtype) == "Int64"
    assert loaded.data["G1"].tolist() == [7, 7, 7]
    assert str(loaded.data["school"].dtype) == "string"


def test_valid_file_passes_all_value_checks(tmp_path):
    report = report_for(tmp_path, make_rows(5))

    assert report.missing_values == report.invalid_values == report.duplicate_rows == 0
    assert all(c.status == "pass" for c in report.checks if c.key != "shape")


def test_row_count_differing_from_published_file_is_a_warning(tmp_path):
    shape = check(report_for(tmp_path, make_rows(5)), "shape")
    assert shape.status == "warning"
    assert shape.affected == 395 - 5


def test_missing_values_are_detected(tmp_path):
    rows = make_rows(4)
    rows[1]["Mjob"] = ""
    rows[2]["G2"] = ""
    report = report_for(tmp_path, rows)

    assert report.missing_values == 2
    assert check(report, "missing").status == "fail"
    assert report.status == "fail"


def test_duplicate_rows_are_reported_not_removed(tmp_path):
    rows = make_rows(3)
    rows.append(dict(rows[0]))
    report = report_for(tmp_path, rows)

    assert report.duplicate_rows == 1
    assert check(report, "duplicates").status == "warning"
    assert report.rows == 4


@pytest.mark.parametrize(
    ("column", "value", "key"),
    [
        ("higher", "maybe", "yes_no"),
        ("Mjob", "pilot", "categories"),
        ("G3", 21, "grades"),
        ("G1", -1, "grades"),
        ("studytime", 5, "scales"),
        ("absences", 94, "counts"),
        ("failures", 5, "counts"),
        ("age", "abc", "counts"),
        ("age", 16.5, "counts"),
    ],
)
def test_impossible_values_fail_the_relevant_check(tmp_path, column, value, key):
    rows = make_rows(3)
    rows[0][column] = value
    report = report_for(tmp_path, rows)

    assert check(report, key).status == "fail"
    assert check(report, key).affected == 1
    profile = next(p for p in report.profiles if p.name == column)
    assert profile.invalid == 1
    assert profile.invalid_examples


def test_boundary_values_are_valid(tmp_path):
    rows = make_rows(2)
    rows[0].update(G3=0, absences=93, age=22, failures=4, Medu=0)
    rows[1].update(G3=20, age=15)
    report = report_for(tmp_path, rows)

    assert report.invalid_values == 0


def test_missing_and_extra_columns_fail_schema_check(tmp_path):
    columns = [c for c in COLUMN_NAMES if c != "romantic"] + ["student_id"]
    rows = [{**r, "student_id": i} for i, r in enumerate(make_rows(2))]
    result = check(report_for(tmp_path, rows, columns), "columns")

    assert result.status == "fail"
    assert "romantic" in result.summary and "student_id" in result.summary


def test_reordered_columns_is_only_a_warning(tmp_path):
    columns = list(reversed(COLUMN_NAMES))
    assert check(report_for(tmp_path, make_rows(2), columns), "columns").status == "warning"


def test_g3_zero_is_an_observation_not_an_error(tmp_path):
    report = report_for(tmp_path, make_rows(3, G3=0))

    assert check(report, "grades").status == "pass"
    zero = next(o for o in report.observations if o.key == "g3_zero")
    assert zero.count == 3
