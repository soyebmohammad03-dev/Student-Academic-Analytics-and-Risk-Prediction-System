"""Feature scenarios: which predictors are legitimately available at prediction time.

``G1`` and ``G2`` are grades from earlier in the same school year and are strongly
related to the final grade ``G3``. Whether they may be used depends on *when* a
prediction is made, so every feature set belongs to exactly one named scenario.

- ``full_history``: all non-grade attributes + G1 + G2. Prediction late in the year.
- ``mid_year``:     all non-grade attributes + G1.      Prediction after the first period.
- ``early``:        non-grade attributes only.          Early warning, before any grade.

The scenarios answer different questions; none is "better" by default. ``full_history``
measures how predictable the final grade is once interim grades exist (expected to be
high, largely because G1/G2 measure the same construct). ``early`` measures what
background, behavioural and school attributes can say before any grade is known —
lower accuracy is expected and is the relevant figure for early support.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from analytics.data.dictionary import COLUMNS
from analytics.preprocessing.features import ENGINEERED_FEATURES
from analytics.preprocessing.targets import TARGET_COLUMNS


class Scenario(StrEnum):
    FULL_HISTORY = "full_history"
    MID_YEAR = "mid_year"
    EARLY = "early"


@dataclass(frozen=True)
class ScenarioSpec:
    scenario: Scenario
    label: str
    description: str
    prior_grades: tuple[str, ...]


SCENARIOS: dict[Scenario, ScenarioSpec] = {
    Scenario.FULL_HISTORY: ScenarioSpec(
        Scenario.FULL_HISTORY,
        "Full academic history",
        "Non-grade attributes plus first- and second-period grades (G1, G2).",
        ("G1", "G2"),
    ),
    Scenario.MID_YEAR: ScenarioSpec(
        Scenario.MID_YEAR,
        "Mid-year",
        "Non-grade attributes plus the first-period grade (G1).",
        ("G1",),
    ),
    Scenario.EARLY: ScenarioSpec(
        Scenario.EARLY,
        "Early warning (no grades)",
        "Non-grade attributes only; no grade from the current year.",
        (),
    ),
}

PRIOR_GRADES: tuple[str, ...] = tuple(c.name for c in COLUMNS if c.role == "prior_grade")
_REPLACED = {f.replaces for f in ENGINEERED_FEATURES if f.replaces}

#: Non-grade attributes from the dictionary, minus raw columns replaced by engineered ones.
BASE_FEATURES: tuple[str, ...] = tuple(
    c.name for c in COLUMNS if c.role == "feature" and c.name not in _REPLACED
) + tuple(f.name for f in ENGINEERED_FEATURES)


class LeakageError(ValueError):
    """Raised when a feature set would contain an outcome or an unavailable grade."""


def feature_columns(scenario: Scenario) -> tuple[str, ...]:
    columns = BASE_FEATURES + SCENARIOS[Scenario(scenario)].prior_grades
    assert_no_leakage(columns, scenario)
    return columns


def assert_no_leakage(columns, scenario: Scenario) -> None:
    columns = set(columns)
    if leaked := columns & TARGET_COLUMNS:
        raise LeakageError(f"Outcome columns used as predictors: {sorted(leaked)}")
    allowed = set(SCENARIOS[Scenario(scenario)].prior_grades)
    if unavailable := (columns & set(PRIOR_GRADES)) - allowed:
        raise LeakageError(f"{sorted(unavailable)} not available in the '{scenario}' scenario")
