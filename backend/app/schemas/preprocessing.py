from pydantic import BaseModel, Field

from analytics.data import Cohort
from analytics.preprocessing import Scenario


class ScenarioInfo(BaseModel):
    key: Scenario
    label: str
    description: str
    prior_grades: list[str]


class ExcludedColumnOut(BaseModel):
    name: str
    reason: str


class EngineeredFeatureOut(BaseModel):
    name: str
    definition: str
    reason: str
    leakage: str
    sources: list[str]
    replaces: str | None


class RiskDistributionOut(BaseModel):
    at_risk: int
    not_at_risk: int
    at_risk_share: float


class OutlierOut(BaseModel):
    name: str
    count: int
    lower_fence: float
    upper_fence: float


class SplitOut(BaseModel):
    train_rows: int
    test_rows: int
    train_risk: RiskDistributionOut
    test_risk: RiskDistributionOut
    test_size: float
    random_state: int
    stratified_on: str


class PreprocessingSummary(BaseModel):
    cohort: Cohort
    scenario: ScenarioInfo
    original_shape: tuple[int, int]
    analytical_shape: tuple[int, int]
    rows_removed: int
    feature_groups: dict[str, list[str]] = Field(
        description="Model input columns by encoding group, before encoding."
    )
    encoded_features: list[str] = Field(
        description="Columns produced by the preprocessor fitted on the training split."
    )
    engineered_features: list[EngineeredFeatureOut]
    excluded_columns: list[ExcludedColumnOut]
    missing_values: int
    missing_value_strategy: str
    regression_target: str
    risk_label: str
    risk_definition: str
    target_counts: dict[int, int] = Field(description="Students per final-grade value.")
    target_zero_count: int
    risk: RiskDistributionOut
    outliers: list[OutlierOut] = Field(description="Tukey 1.5·IQR counts; reported, not removed.")
    split: SplitOut
