"""Typed group-level risk profiles and suggestions, reused as API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from analytics.statistics.models import Interval

Num = float | None


class ProfileGroup(BaseModel):
    key: str
    label: str
    n: int
    at_risk: int
    risk_percent: float
    risk_ci: Interval
    difference_from_overall: float = Field(description="Percentage points versus the cohort.")
    reliable: bool = Field(description="At least the minimum group size (10 students).")


class SingleProfile(BaseModel):
    variable: str
    label: str
    groups: list[ProfileGroup]
    test: str
    p: Num
    p_adjusted: Num = Field(description="Benjamini–Hochberg across the profile variables.")
    cramers_v: Num
    magnitude: str
    warnings: list[str]


class PairCell(BaseModel):
    row: str
    row_label: str
    column: str
    column_label: str
    n: int
    at_risk: int
    risk_percent: Num = Field(description="Omitted (null) for empty cells.")
    risk_ci: Interval
    reliable: bool


class PairProfile(BaseModel):
    rows_variable: str
    rows_label: str
    columns_variable: str
    columns_label: str
    cells: list[PairCell]


class RiskProfiles(BaseModel):
    kind: Literal["group_statistics"] = "group_statistics"
    cohort: str
    n: int
    at_risk: int
    risk_percent: float
    risk_ci: Interval
    threshold: int
    single: list[SingleProfile]
    pairs: list[PairProfile]
    notes: list[str]


class Evidence(BaseModel):
    kind: Literal["group_statistics", "model_performance"]
    summary: str
    group_n: int | None = None
    group_risk_percent: Num = None
    comparison_n: int | None = None
    comparison_risk_percent: Num = None
    p: Num = Field(default=None, description="Fisher's exact test, two-sided, unadjusted.")
    supported: bool = Field(description="Whether the evidence check for showing it passed.")


class Suggestion(BaseModel):
    kind: Literal["general_educational_suggestion"] = "general_educational_suggestion"
    key: str
    text: str
    trigger: str = Field(description="The observable input that prompted it.")
    evidence: Evidence


class SuggestionSet(BaseModel):
    cohort: str
    suggestions: list[Suggestion]
    not_shown: list[Suggestion] = Field(
        description="Triggered, but the cohort's data did not support showing them."
    )
    disclaimer: str
