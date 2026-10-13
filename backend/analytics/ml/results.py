"""Typed results of a training run.

Pydantic models so that results are validated, serialised to ``ml_results.json`` and
reused directly as API response schemas. Undefined metrics are ``None``, never NaN.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from analytics.ml.config import Task
from analytics.preprocessing import Scenario

Num = float | None


class ModelArtifactError(RuntimeError):
    """Results or a persisted model are missing, altered, or incompatible."""


Metrics = dict[str, Num]


class MetricSummary(BaseModel):
    mean: Num
    std: Num = Field(description="Sample standard deviation across folds (ddof = 1).")
    folds: list[Num]
    defined_folds: int = Field(description="Folds in which the metric was defined.")


class Confusion(BaseModel):
    """Rows: actual class; columns: predicted class. Positive class = at risk."""

    tn: int
    fp: int
    fn: int
    tp: int


class Diagnostic(BaseModel):
    level: Literal["info", "warning"]
    code: str
    message: str


class ModelResult(BaseModel):
    cohort: str
    task: Task
    scenario: Scenario
    model: str
    label: str
    family: str
    baseline: bool
    complexity: int
    class_weight: str | None
    search_space: dict[str, list[Any]]
    candidates: int = Field(description="Hyperparameter combinations searched (1 = none).")
    best_params: dict[str, Any] = Field(
        description="Chosen by inner cross-validation on the full training set."
    )
    outer_fold_params: list[dict[str, Any]] = Field(
        description="Parameters chosen inside each outer fold (nested CV)."
    )
    cv: dict[str, MetricSummary] = Field(description="Nested cross-validation on training data.")
    test: Metrics = Field(description="Held-out test set, evaluated once after training.")
    test_confusion: Confusion | None = None
    test_predicted_positive: int | None = None
    n_train: int
    n_test: int
    diagnostics: list[Diagnostic]


class Selection(BaseModel):
    cohort: str
    task: Task
    scenario: Scenario
    model: str
    label: str
    primary_metric: str
    best_model: str = Field(description="Model with the best mean CV value of the primary metric.")
    best_mean: Num
    tolerance: Num = Field(description="One standard error of the best model's fold values.")
    within_tolerance: list[str]
    beats_baseline: bool
    baseline_mean: Num
    reason: str


# --- Error analysis ----------------------------------------------------------------------


class ResidualSummary(BaseModel):
    mean: Num = Field(description="Mean residual (actual − predicted); > 0 means under-prediction.")
    std: Num
    median: Num
    q1: Num
    q3: Num
    min: Num
    max: Num
    within_1: float = Field(description="Share of students predicted within ±1 grade point.")
    within_2: float


class ResidualBin(BaseModel):
    start: float
    end: float
    label: str
    count: int


class GradeBand(BaseModel):
    band: str
    n: int
    mae: Num
    mean_residual: Num


class LargeError(BaseModel):
    row: int = Field(description="1-based row position in the source file (no identity).")
    actual: float
    predicted: float
    residual: float


class RegressionErrors(BaseModel):
    cohort: str
    scenario: Scenario
    model: str
    n: int
    metrics: Metrics
    residuals: ResidualSummary
    histogram: list[ResidualBin]
    by_band: list[GradeBand]
    largest: list[LargeError]
    patterns: list[str]


class GradeCount(BaseModel):
    grade: int
    count: int


class ClassOutcome(BaseModel):
    label: str
    n: int
    correct: int
    rate: Num = Field(description="Recall for at risk; specificity for not at risk.")


class ClassificationErrors(BaseModel):
    cohort: str
    scenario: Scenario
    model: str
    n: int
    threshold: float
    score_kind: Literal["probability", "decision_function"]
    confusion: Confusion
    metrics: Metrics
    by_class: list[ClassOutcome]
    false_negative_grades: list[GradeCount] = Field(
        description="Actual G3 of at-risk students the model missed."
    )
    false_positive_grades: list[GradeCount] = Field(
        description="Actual G3 of students flagged at risk who passed."
    )
    zero_grade_detected: int
    zero_grade_total: int
    patterns: list[str]


class ZeroGradeSensitivity(BaseModel):
    """Exploratory: the selected regression model retrained without G3 = 0 students."""

    cohort: str
    scenario: Scenario
    model: str
    train_zeros_removed: int
    test_n: int = Field(description="Test students with G3 > 0 used for both rows.")
    all_rows_model: Metrics
    without_zeros_model: Metrics
    note: str


# --- Cohort summary ------------------------------------------------------------------------


class ClassBalance(BaseModel):
    n: int
    at_risk: int
    not_at_risk: int
    at_risk_percent: float
    not_at_risk_percent: float


class TargetSummary(BaseModel):
    mean: float
    std: float
    median: float
    minimum: int
    maximum: int
    zero_count: int


class CohortResults(BaseModel):
    cohort: str
    subject: str
    n: int
    n_train: int
    n_test: int
    target: TargetSummary
    risk: dict[Literal["all", "train", "test"], ClassBalance]
    regression: list[ModelResult]
    classification: list[ModelResult]
    selections: list[Selection]
    regression_errors: list[RegressionErrors]
    classification_errors: list[ClassificationErrors]
    zero_grade_sensitivity: list[ZeroGradeSensitivity]


class RunInfo(BaseModel):
    schema_version: int
    created_at: str
    random_state: int
    cv_folds: int
    search: str
    test_size: float
    cv_strategy: dict[Task, str]
    tuning_metric: dict[Task, str]
    selection_metric: dict[Task, str]
    decision_threshold: float
    software: dict[str, str]
    dataset_sha256: dict[str, str]


class MlResults(BaseModel):
    run: RunInfo
    cohorts: list[CohortResults]

    def cohort(self, cohort: str) -> CohortResults:
        for item in self.cohorts:
            if item.cohort == str(cohort):
                return item
        raise ModelArtifactError(f"The training results contain no '{cohort}' cohort.")


class ArtifactMetadata(BaseModel):
    """Everything needed to trace a persisted model back to how it was produced."""

    cohort: str
    task: Task
    scenario: Scenario
    model: str
    label: str
    artifact: str
    sha256: str
    feature_columns: list[str] = Field(description="Input columns the pipeline expects.")
    encoded_features: list[str] = Field(description="Columns after preprocessing.")
    target: str
    positive_class: str | None
    threshold: float | None
    score_kind: Literal["probability", "decision_function"] | None
    best_params: dict[str, Any]
    search_space: dict[str, list[Any]]
    random_state: int
    cv_folds: int
    cv_strategy: str
    n_train: int
    n_test: int
    cv: dict[str, MetricSummary]
    test: Metrics
    software: dict[str, str]
    dataset_sha256: str
    created_at: str
