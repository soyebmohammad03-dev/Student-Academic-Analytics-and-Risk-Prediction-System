"""API schemas for model results and predictions.

Result tables reuse the analytics Pydantic models directly; these add the catalogue,
the selected-model detail and the prediction request.
"""

from typing import Any

from pydantic import BaseModel, Field

from analytics.data import Cohort
from analytics.ml.config import Task
from analytics.ml.results import (
    ArtifactMetadata,
    ClassificationErrors,
    RegressionErrors,
    RunInfo,
    Selection,
    ZeroGradeSensitivity,
)
from analytics.preprocessing import Scenario


class ModelInfo(BaseModel):
    task: Task
    key: str
    label: str
    family: str
    baseline: bool
    class_weight: str | None
    search_space: dict[str, list[Any]]
    strengths: str
    weaknesses: str


class SelectedModelRef(BaseModel):
    cohort: Cohort
    task: Task
    scenario: Scenario
    model: str
    label: str


class ModelCatalog(BaseModel):
    trained: bool = Field(description="Whether a training run's results are available.")
    run: RunInfo | None
    models: list[ModelInfo]
    selected: list[SelectedModelRef] = Field(
        description="The persisted model for each cohort, task and scenario."
    )


class SelectedModelDetail(BaseModel):
    metadata: ArtifactMetadata
    selection: Selection
    regression_errors: RegressionErrors | None = None
    classification_errors: ClassificationErrors | None = None
    zero_grade_sensitivity: ZeroGradeSensitivity | None = None


class PredictionRequest(BaseModel):
    cohort: Cohort
    task: Task
    scenario: Scenario
    model: str | None = Field(
        default=None, description="Defaults to the selected (persisted) model."
    )
    features: dict[str, str | int | float] = Field(
        description=(
            "Attributes as recorded in the UCI files (e.g. absences as a count). G1/G2 only "
            "when the scenario allows them; G3 and at_risk are rejected."
        )
    )
