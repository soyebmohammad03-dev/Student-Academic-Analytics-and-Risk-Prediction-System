"""Load a cohort CSV into a typed DataFrame.

Values are first read as raw text so that validation can see exactly what is in the
file (including anything that would not parse). The typed frame converts numerical
columns to nullable integers and categorical columns to strings; values that cannot be
converted become missing and are reported by validation rather than silently dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from analytics.data.cohorts import COHORTS, Cohort, CohortInfo
from analytics.data.dictionary import COLUMNS_BY_NAME

CSV_SEPARATOR = ";"


class DatasetNotFoundError(FileNotFoundError):
    """Raised when a cohort file has not been downloaded."""


@dataclass(frozen=True)
class LoadedCohort:
    info: CohortInfo
    path: Path
    #: Values exactly as read from the file (strings, NaN for empty cells).
    raw: pd.DataFrame
    #: Typed values: Int64 for numerical columns, string for categorical columns.
    data: pd.DataFrame


def cohort_path(raw_dir: Path, cohort: Cohort) -> Path:
    return raw_dir / COHORTS[cohort].filename


def load_cohort(raw_dir: Path, cohort: Cohort) -> LoadedCohort:
    info = COHORTS[cohort]
    path = cohort_path(raw_dir, cohort)
    if not path.is_file():
        raise DatasetNotFoundError(
            f"{info.filename} not found in {raw_dir}. "
            "Run `python -m analytics.data.download` from the backend directory."
        )

    raw = pd.read_csv(path, sep=CSV_SEPARATOR, dtype=str, keep_default_na=False, na_values=[""])
    return LoadedCohort(info=info, path=path, raw=raw, data=to_typed(raw))


def to_typed(raw: pd.DataFrame) -> pd.DataFrame:
    typed = {}
    for name in raw.columns:
        spec = COLUMNS_BY_NAME.get(name)
        column = raw[name]
        if spec is not None and spec.measure == "numerical":
            numbers = pd.to_numeric(column.str.strip(), errors="coerce")
            # Non-integral numbers are invalid for these integer-coded attributes.
            numbers = numbers.where(numbers.isna() | (numbers % 1 == 0))
            typed[name] = numbers.astype("Int64")
        else:
            typed[name] = column.str.strip().astype("string")
    return pd.DataFrame(typed, index=raw.index)
