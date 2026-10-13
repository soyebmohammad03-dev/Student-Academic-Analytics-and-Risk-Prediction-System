"""Typed interpretability results, reused as API response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from analytics.ml.config import Task
from analytics.ml.predict import PredictionResult
from analytics.preprocessing import Scenario

Num = float | None

ImportanceMethod = Literal[
    "permutation_test",
    "mean_abs_shapley",
    "impurity_decrease",
    "standardised_coefficient",
]


class ImportanceItem(BaseModel):
    feature: str = Field(description="Attribute, or encoded feature for coefficients.")
    attribute: str = Field(description="Original UCI attribute the feature belongs to.")
    label: str
    value: float
    std: Num = Field(default=None, description="Spread over repeats, where applicable.")
    rank: int


class ImportanceResult(BaseModel):
    cohort: str
    task: Task
    scenario: Scenario
    model: str
    model_label: str
    method: ImportanceMethod
    method_label: str
    data: str = Field(description="Which data the values were computed on.")
    unit: str
    items: list[ImportanceItem]
    limitations: list[str]


class CalibrationBin(BaseModel):
    low: float
    high: float
    n: int
    mean_predicted: Num
    observed_rate: Num


class Calibration(BaseModel):
    """How the selected classifier's probabilities compare with test-set outcomes."""

    cohort: str
    scenario: Scenario
    model: str
    n: int
    brier: float
    mean_predicted: float
    observed_rate: float
    bins: list[CalibrationBin]
    note: str


class ModelInterpretation(BaseModel):
    cohort: str
    task: Task
    scenario: Scenario
    model: str
    model_label: str
    methods: list[ImportanceResult]
    calibration: Calibration | None = None


class InterpretabilityRun(BaseModel):
    schema_version: int
    created_at: str
    models_created_at: str
    random_state: int
    permutation_repeats: int
    shapley_samples: int
    software: dict[str, str]
    items: list[ModelInterpretation]


# --- Individual explanations -----------------------------------------------------------


class Contribution(BaseModel):
    attribute: str
    label: str
    value: str = Field(description="The record's value for this attribute.")
    contribution: float = Field(description="Shapley value on the model-output scale.")
    standard_error: float
    direction: Literal["raises", "lowers", "negligible"]


class Explanation(BaseModel):
    kind: Literal["individual_model_explanation"] = "individual_model_explanation"
    method: str
    output: str = Field(description="The model output being explained.")
    base_value: float = Field(description="Mean model output over the background sample.")
    prediction: float = Field(description="Model output for this record (before limiting).")
    contributions: list[Contribution] = Field(description="Largest absolute contributions.")
    other_attributes: int
    other_contribution: float = Field(description="Sum of the remaining contributions.")
    n_samples: int
    background: str
    background_size: int
    seed: int
    reading: str
    limitations: list[str]


class ExplainedPrediction(BaseModel):
    prediction: PredictionResult
    explanation: Explanation | None = None
    score_percentile: Num = Field(
        default=None,
        description="Share (%) of training students whose score is below this record's score.",
    )


# --- Sensitivity ------------------------------------------------------------------------


class SensitivityPoint(BaseModel):
    value: str
    label: str
    current: bool
    output: float = Field(description="Model output with only this attribute changed.")
    predicted_grade: Num = None
    at_risk: bool | None = None
    support: int = Field(description="Training students with this value of the attribute.")
    sparse: bool = Field(description="Fewer than the minimum supporting students.")


class SensitivityCurve(BaseModel):
    kind: Literal["model_sensitivity"] = "model_sensitivity"
    cohort: str
    task: Task
    scenario: Scenario
    model: str
    attribute: str
    label: str
    output: str
    points: list[SensitivityPoint]
    note: str


class ScenarioPrediction(BaseModel):
    scenario: Scenario
    model: str
    model_label: str
    output: float
    predicted_grade: Num = None
    at_risk: bool | None = None


class ScenarioSensitivity(BaseModel):
    kind: Literal["model_sensitivity"] = "model_sensitivity"
    cohort: str
    task: Task
    items: list[ScenarioPrediction]
    skipped: list[str] = Field(description="Scenarios whose grades were not provided.")
    note: str
