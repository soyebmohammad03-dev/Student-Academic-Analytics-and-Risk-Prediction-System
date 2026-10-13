"""Request and response schemas for interpretability and risk analysis."""

from typing import Literal

from pydantic import BaseModel, Field

from analytics.data import Cohort
from analytics.interpret.explain import SENSITIVITY_ATTRIBUTES
from analytics.interpret.results import ExplainedPrediction
from analytics.ml.config import Task
from analytics.preprocessing import Scenario
from analytics.risk.results import SuggestionSet
from analytics.statistics.models import Interval

Features = dict[str, str | int | float]
SensitivityAttribute = Literal[SENSITIVITY_ATTRIBUTES]  # type: ignore[valid-type]

_FEATURES = Field(
    description=(
        "Attributes as recorded in the UCI files. G1/G2 only when the scenario allows them; "
        "G3 and at_risk are rejected."
    )
)


class ExplainRequest(BaseModel):
    cohort: Cohort
    task: Task
    scenario: Scenario
    model: str | None = None
    features: Features = _FEATURES
    top: int = Field(default=10, ge=1, le=33, description="Contributions to return.")


class SensitivityRequest(BaseModel):
    cohort: Cohort
    task: Task
    scenario: Scenario
    model: str | None = None
    features: Features = _FEATURES
    attribute: SensitivityAttribute


class ScenarioSensitivityRequest(BaseModel):
    cohort: Cohort
    task: Task
    features: Features = Field(
        description="Attributes, optionally with G1 and/or G2; each scenario uses what it allows."
    )


class RiskRequest(BaseModel):
    cohort: Cohort
    scenario: Scenario = Field(description="Scenario of the classification model consulted.")
    features: Features = _FEATURES


class GroupFinding(BaseModel):
    kind: Literal["group_statistics"] = "group_statistics"
    variable: str
    label: str
    group: str
    n: int
    risk_percent: float
    risk_ci: Interval
    reliable: bool
    cohort_risk_percent: float


class RiskInsights(BaseModel):
    """Three separate kinds of information; they are never merged."""

    individual: ExplainedPrediction = Field(
        description="A. How the selected classification model treated this record."
    )
    group: list[GroupFinding] = Field(
        description="B. Observed academic risk among cohort students sharing each value."
    )
    suggestions: SuggestionSet = Field(description="C. General suggestions for human review.")
    reading: list[str]
