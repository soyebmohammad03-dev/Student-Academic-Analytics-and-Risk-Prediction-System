"""Structured validation of a loaded cohort against the data dictionary.

Validation only *reports*. It never removes rows: values that are unusual but within
the documented range (for example a final grade of 0, or a high absence count) are
valid data and are kept for analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from analytics.data.dictionary import COLUMN_NAMES, COLUMNS, COLUMNS_BY_NAME, ColumnSpec
from analytics.data.loader import LoadedCohort

Status = Literal["pass", "warning", "fail"]
_SEVERITY: dict[Status, int] = {"pass": 0, "warning": 1, "fail": 2}


@dataclass(frozen=True)
class CheckResult:
    key: str
    title: str
    status: Status
    summary: str
    affected: int = 0


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    missing: int
    invalid: int
    unique: int
    minimum: int | None = None
    maximum: int | None = None
    #: Invalid values as they appear in the file (first few only).
    invalid_examples: tuple[str, ...] = ()


@dataclass(frozen=True)
class Observation:
    """A factual note about valid-but-noteworthy data. Not an error."""

    key: str
    title: str
    detail: str
    count: int


@dataclass(frozen=True)
class ValidationReport:
    rows: int
    columns: int
    checks: tuple[CheckResult, ...]
    profiles: tuple[ColumnProfile, ...]
    observations: tuple[Observation, ...] = field(default=())

    @property
    def status(self) -> Status:
        return max((c.status for c in self.checks), key=_SEVERITY.__getitem__, default="pass")

    @property
    def missing_values(self) -> int:
        return sum(p.missing for p in self.profiles)

    @property
    def invalid_values(self) -> int:
        return sum(p.invalid for p in self.profiles)

    @property
    def duplicate_rows(self) -> int:
        return next(c.affected for c in self.checks if c.key == "duplicates")


def _is_invalid(spec: ColumnSpec, raw: pd.Series, typed: pd.Series) -> pd.Series:
    """Boolean mask of present-but-invalid cells for one column."""
    present = raw.notna()
    if spec.measure == "categorical":
        return present & ~typed.isin([str(c) for c in spec.allowed_codes])
    unparsable = present & typed.isna()
    out_of_range = typed.notna() & ((typed < spec.minimum) | (typed > spec.maximum))
    return unparsable | out_of_range.fillna(False).astype(bool)


def profile_column(spec: ColumnSpec, raw: pd.Series, typed: pd.Series) -> ColumnProfile:
    invalid_mask = _is_invalid(spec, raw, typed)
    numeric = spec.measure == "numerical" and typed.notna().any()
    return ColumnProfile(
        name=spec.name,
        missing=int(raw.isna().sum()),
        invalid=int(invalid_mask.sum()),
        unique=int(typed.nunique(dropna=True)),
        minimum=int(typed.min()) if numeric else None,
        maximum=int(typed.max()) if numeric else None,
        invalid_examples=tuple(raw[invalid_mask].astype(str).unique()[:5]),
    )


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def validate(cohort: LoadedCohort) -> ValidationReport:
    raw, data, info = cohort.raw, cohort.data, cohort.info
    checks: list[CheckResult] = []

    actual = list(raw.columns)
    missing_cols = [c for c in COLUMN_NAMES if c not in actual]
    extra_cols = [c for c in actual if c not in COLUMNS_BY_NAME]
    if missing_cols or extra_cols:
        parts = []
        if missing_cols:
            parts.append(f"missing {', '.join(missing_cols)}")
        if extra_cols:
            parts.append(f"unexpected {', '.join(extra_cols)}")
        checks.append(
            CheckResult(
                "columns",
                "Expected columns",
                "fail",
                f"Column set differs from the data dictionary: {'; '.join(parts)}.",
                len(missing_cols) + len(extra_cols),
            )
        )
    elif actual != list(COLUMN_NAMES):
        checks.append(
            CheckResult(
                "columns",
                "Expected columns",
                "warning",
                "All 33 documented columns are present, but in a different order.",
            )
        )
    else:
        checks.append(
            CheckResult(
                "columns",
                "Expected columns",
                "pass",
                "All 33 documented columns are present, in the documented order.",
            )
        )

    rows = len(raw)
    checks.append(
        CheckResult(
            "shape",
            "Number of students",
            "pass" if rows == info.expected_rows else "warning",
            f"{rows} rows, matching the {info.expected_rows} published for this cohort."
            if rows == info.expected_rows
            else f"{rows} rows, but the published file has {info.expected_rows}.",
            abs(rows - info.expected_rows),
        )
    )

    specs = [s for s in COLUMNS if s.name in raw.columns]
    profiles = tuple(profile_column(s, raw[s.name], data[s.name]) for s in specs)
    by_name = {p.name: p for p in profiles}

    missing = sum(p.missing for p in profiles)
    checks.append(
        CheckResult(
            "missing",
            "Missing values",
            "pass" if missing == 0 else "fail",
            "Every cell has a value."
            if missing == 0
            else f"{_plural(missing, 'empty cell')} across "
            f"{_plural(sum(1 for p in profiles if p.missing), 'column')}.",
            missing,
        )
    )

    duplicates = int(data.duplicated().sum())
    checks.append(
        CheckResult(
            "duplicates",
            "Duplicate rows",
            "pass" if duplicates == 0 else "warning",
            "No two rows are identical across all attributes."
            if duplicates == 0
            else f"{_plural(duplicates, 'row')} exactly repeat an earlier row. "
            "The dataset has no student ID, so these may be distinct students with "
            "identical answers; they are kept.",
            duplicates,
        )
    )

    def value_check(key: str, title: str, names: list[str], scope: str) -> CheckResult:
        bad = [by_name[n] for n in names if n in by_name and by_name[n].invalid]
        count = sum(p.invalid for p in bad)
        if not count:
            return CheckResult(key, title, "pass", f"All {scope} are within documented values.")
        detail = ", ".join(f"{p.name} ({p.invalid})" for p in bad)
        return CheckResult(
            key, title, "fail", f"{_plural(count, 'invalid value')} in {detail}.", count
        )

    categorical = [s.name for s in specs if s.measure == "categorical"]
    binary_yes_no = [s.name for s in specs if s.allowed_codes == {"yes", "no"}]
    other_categorical = [n for n in categorical if n not in binary_yes_no]
    grades = [s.name for s in specs if s.scale == "grade"]
    ordinal = [s.name for s in specs if s.scale == "ordinal"]
    counts = [s.name for s in specs if s.scale == "count"]

    checks += [
        value_check("yes_no", "Yes/no answers", binary_yes_no, "yes/no fields"),
        value_check("categories", "Category codes", other_categorical, "category codes"),
        value_check("grades", "Grades G1, G2, G3", grades, "grades (0–20)"),
        value_check("scales", "Rating and coded scales", ordinal, "1–4 / 1–5 / 0–4 scale codes"),
        value_check(
            "counts",
            "Age, failures and absences",
            counts,
            "ages (15–22), failure counts (0–4) and absences (0–93)",
        ),
    ]

    return ValidationReport(
        rows=rows,
        columns=len(actual),
        checks=tuple(checks),
        profiles=profiles,
        observations=tuple(_observations(data)),
    )


def _observations(data: pd.DataFrame) -> list[Observation]:
    notes: list[Observation] = []
    if "G3" in data:
        zero = int((data["G3"] == 0).sum())
        if zero:
            notes.append(
                Observation(
                    "g3_zero",
                    "Final grade of 0",
                    f"{_plural(zero, 'student')} have a final grade (G3) of 0. This is within "
                    "the documented range, but may indicate a student who did not sit the "
                    "final evaluation. Rows are kept; handling is decided before modelling.",
                    zero,
                )
            )
    if "failures" in data:
        fours = int((data["failures"] == 4).sum())
        notes.append(
            Observation(
                "failures_coding",
                "Coding of past failures",
                "UCI documents 3 or more failures as the value 4, but this file contains "
                f"{'no 4s' if not fours else _plural(fours, 'value') + ' of 4'}; "
                "the value 3 is therefore read as '3 or more'.",
                fours,
            )
        )
    return notes
