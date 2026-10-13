from typing import Literal

from pydantic import BaseModel, Field

from analytics.pipeline import CohortOverview, ComponentStatus, SelectedModelSummary


class DashboardDataset(BaseModel):
    available: bool
    detail: str
    cohorts: list[CohortOverview]


class DashboardModels(BaseModel):
    available: bool
    detail: str
    trained_at: str | None
    selected: list[SelectedModelSummary] = Field(
        description="Cross-validated and held-out scores of each selected model."
    )


class DashboardSummary(BaseModel):
    status: Literal["ready", "degraded"]
    components: list[ComponentStatus]
    dataset: DashboardDataset
    models: DashboardModels
    notes: list[str]
