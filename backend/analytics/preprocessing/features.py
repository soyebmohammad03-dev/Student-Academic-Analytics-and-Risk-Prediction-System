"""Engineered features.

Each feature is a deterministic, row-wise function of attributes recorded before the
final grade. Being stateless (nothing is learned from the data), computing them
before the train/test split cannot leak information between the two sets.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EngineeredFeature:
    name: str
    definition: str
    reason: str
    leakage: str
    #: Raw columns the feature is computed from.
    sources: tuple[str, ...]
    #: Raw column the feature replaces in model inputs, if any.
    replaces: str | None
    kind: str
    compute: Callable[[pd.DataFrame], pd.Series]


ENGINEERED_FEATURES: tuple[EngineeredFeature, ...] = (
    EngineeredFeature(
        name="has_past_failures",
        definition="1 if failures > 0, else 0.",
        reason=(
            "Most students have no past failures (79% in Mathematics, 85% in Portuguese), "
            "so the any-versus-none contrast is the most populated distinction in the "
            "variable. The count `failures` is kept alongside it."
        ),
        leakage=(
            "None. Past class failures precede the current school year and do not use "
            "any grade from it."
        ),
        sources=("failures",),
        replaces=None,
        kind="indicator",
        compute=lambda d: (d["failures"] > 0).astype("int64"),
    ),
    EngineeredFeature(
        name="log_absences",
        definition="ln(1 + absences).",
        reason=(
            "Absences are strongly right-skewed (sample skewness 3.7 in Mathematics, 2.0 "
            "in Portuguese; maxima 75 and 32). The log transform reduces the leverage of "
            "extreme counts on linear and distance-based models without removing any "
            "observation. Tree models are unaffected by this monotonic transform."
        ),
        leakage=(
            "Does not use any grade. Caveat: UCI does not document the period over which "
            "absences were counted; if they accumulate over the whole year, the value is "
            "only partially known at an early-warning point. Stated as a limitation of the "
            "early scenario."
        ),
        sources=("absences",),
        replaces="absences",
        kind="numeric",
        compute=lambda d: np.log1p(d["absences"].astype("float64")),
    ),
)

ENGINEERED_BY_NAME = {f.name: f for f in ENGINEERED_FEATURES}

#: Candidates that were considered and deliberately not added.
REJECTED_FEATURES: tuple[tuple[str, str], ...] = (
    (
        "grade_trend (G2 − G1)",
        "A linear combination of two inputs that are already present in the full-history "
        "scenario; adds collinearity without new information.",
    ),
    (
        "parent_max_edu (max of Medu, Fedu)",
        "Discards information that Medu and Fedu already carry individually.",
    ),
    (
        "studytime grouping",
        "studytime is already a 4-level ordinal code; regrouping it needs statistical "
        "evidence from Phase 4 that does not exist yet.",
    ),
    (
        "support_count (schoolsup + famsup + paid)",
        "Adds heterogeneous forms of support as if they were equivalent; the three "
        "indicators are kept separately.",
    ),
    (
        "alcohol composite (Dalc + Walc)",
        "No documented scale for combining the two ratings; both are kept as recorded.",
    ),
)


def add_engineered_features(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``data`` with every engineered feature appended."""
    out = data.copy()
    for feature in ENGINEERED_FEATURES:
        out[feature.name] = feature.compute(data)
    return out
