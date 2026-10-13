"""Group definitions used by comparisons, associations and EDA.

Groupings are fixed in advance from the data dictionary, never tuned to the results.
Two are merged or binned, for documented reasons:

- Parental education: level 0 ("none") has very few students (e.g. 3 mothers in the
  Mathematics cohort), so 0 and 1 are merged into "Primary or less".
- Absences: a count from 0 to 93, binned into five descriptive bands. The primary
  analysis of absences uses the raw count (Spearman), not these bands.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from analytics.data.dictionary import COLUMNS_BY_NAME


@dataclass(frozen=True)
class Grouping:
    variable: str
    label: str
    #: Ordered (key, label) pairs.
    levels: tuple[tuple[str, str], ...]
    note: str | None = None

    def assign(self, data: pd.DataFrame) -> pd.Series:
        return _ASSIGNERS[self.variable](data).astype(str)


def _coded(name: str):
    def assign(data: pd.DataFrame) -> pd.Series:
        values = data[name]
        return values.astype("int64") if pd.api.types.is_numeric_dtype(values) else values

    return assign


def _levels(name: str) -> tuple[tuple[str, str], ...]:
    return tuple((str(v.code), v.label) for v in COLUMNS_BY_NAME[name].allowed)


def _education(name: str):
    return lambda d: d[name].astype("int64").clip(lower=1)


def _absence_band(data: pd.DataFrame) -> pd.Series:
    bins = [-1, 0, 5, 10, 20, float("inf")]
    labels = ["0", "1-5", "6-10", "11-20", "21+"]
    return pd.cut(data["absences"], bins=bins, labels=labels).astype(str)


_EDU_LEVELS = (
    ("1", "Primary or less"),
    ("2", "5th to 9th grade"),
    ("3", "Secondary"),
    ("4", "Higher education"),
)
_EDU_NOTE = "Level 0 (none) merged with level 1 because it has very few students."

GROUPINGS: dict[str, Grouping] = {
    "studytime": Grouping("studytime", "Weekly study time", _levels("studytime")),
    "failures": Grouping(
        "failures",
        "Past class failures",
        (("0", "None"), ("1", "1"), ("2", "2"), ("3", "3 or more")),
    ),
    "has_past_failures": Grouping(
        "has_past_failures", "Any past failures", (("0", "No past failures"), ("1", "1 or more"))
    ),
    "absence_band": Grouping(
        "absence_band",
        "School absences",
        (("0", "None"), ("1-5", "1–5"), ("6-10", "6–10"), ("11-20", "11–20"), ("21+", "21+")),
        note="Descriptive bands; the primary absence analysis uses the raw count.",
    ),
    "Medu": Grouping("Medu", "Mother's education", _EDU_LEVELS, note=_EDU_NOTE),
    "Fedu": Grouping("Fedu", "Father's education", _EDU_LEVELS, note=_EDU_NOTE),
    "sex": Grouping("sex", "Sex", _levels("sex")),
    "schoolsup": Grouping("schoolsup", "Extra school support", _levels("schoolsup")),
    "famsup": Grouping("famsup", "Family educational support", _levels("famsup")),
    "paid": Grouping("paid", "Extra paid classes", _levels("paid")),
    "higher": Grouping("higher", "Wants higher education", _levels("higher")),
    "internet": Grouping("internet", "Internet at home", _levels("internet")),
    "address": Grouping("address", "Home address type", _levels("address")),
    "school": Grouping("school", "School", _levels("school")),
    "romantic": Grouping("romantic", "Romantic relationship", _levels("romantic")),
}

_ASSIGNERS = {
    "studytime": _coded("studytime"),
    # UCI codes "3 or more" as 4 (the official files only contain 0–3).
    "failures": lambda d: d["failures"].astype("int64").clip(upper=3),
    "has_past_failures": _coded("has_past_failures"),
    "absence_band": _absence_band,
    "Medu": _education("Medu"),
    "Fedu": _education("Fedu"),
    **{k: _coded(k) for k in ("sex", "schoolsup", "famsup", "paid", "higher", "internet",
                              "address", "school", "romantic")},
}  # fmt: skip

#: Variables offered for group comparisons against G3 (API/selectors).
COMPARISON_VARIABLES: tuple[str, ...] = (
    "studytime", "has_past_failures", "failures", "absence_band", "Medu", "Fedu",
    "schoolsup", "famsup", "paid", "sex", "higher", "internet", "address",
)  # fmt: skip

#: Categorical variables tested for association with academic risk.
ASSOCIATION_VARIABLES: tuple[str, ...] = (
    "sex", "internet", "schoolsup", "famsup", "paid", "higher", "address", "school",
    "romantic", "Medu", "Fedu", "studytime", "has_past_failures",
)  # fmt: skip
