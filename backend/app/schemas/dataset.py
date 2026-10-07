from typing import Literal

from pydantic import BaseModel, Field

from analytics.data import Cohort

CheckStatus = Literal["pass", "warning", "fail"]


class DatasetSource(BaseModel):
    name: str
    url: str
    license: str
    citation: str


class TargetInfo(BaseModel):
    name: str
    label: str
    description: str
    minimum: int
    maximum: int
    pass_mark: int = Field(description="Portuguese grading pass mark on the 0–20 scale.")
    prior_grades: list[str]


class DatasetSummary(BaseModel):
    cohort: Cohort
    subject: str
    filename: str
    source: DatasetSource
    rows: int
    columns: int
    numerical_columns: int
    categorical_columns: int
    missing_values: int
    duplicate_rows: int
    invalid_values: int
    validation_status: CheckStatus
    target: TargetInfo


class AllowedValueOut(BaseModel):
    code: str | int
    label: str


class ObservedColumn(BaseModel):
    missing: int
    invalid: int
    unique: int
    minimum: int | None
    maximum: int | None


class ColumnInfo(BaseModel):
    name: str
    position: int
    label: str
    description: str
    group: str
    measure: Literal["categorical", "numerical"]
    scale: Literal["binary", "nominal", "ordinal", "count", "grade"]
    role: Literal["feature", "prior_grade", "target"]
    dtype: Literal["string", "integer"]
    allowed_values: list[AllowedValueOut]
    minimum: int | None
    maximum: int | None
    notes: list[str]
    observed: ObservedColumn | None = Field(
        description="Values observed in this cohort; null if the column is absent from the file."
    )


class DatasetSchema(BaseModel):
    cohort: Cohort
    source: str
    columns: list[ColumnInfo]


class QualityCheck(BaseModel):
    key: str
    title: str
    status: CheckStatus
    summary: str
    affected: int


class QualityObservation(BaseModel):
    key: str
    title: str
    detail: str
    count: int


class ColumnQuality(BaseModel):
    name: str
    missing: int
    invalid: int
    invalid_examples: list[str]


class DatasetQuality(BaseModel):
    cohort: Cohort
    status: CheckStatus
    rows: int
    columns: int
    missing_values: int
    duplicate_rows: int
    invalid_values: int
    checks: list[QualityCheck]
    observations: list[QualityObservation]
    column_issues: list[ColumnQuality] = Field(
        description="Only columns with at least one missing or invalid value."
    )


class DatasetRecord(BaseModel):
    row: int = Field(description="1-based row position in the source file. Not a student ID.")
    values: dict[str, str | int | None]


class DatasetRecords(BaseModel):
    cohort: Cohort
    page: int
    page_size: int
    total: int = Field(description="Rows matching the search (all rows when no search).")
    total_pages: int
    search: str | None
    columns: list[str]
    items: list[DatasetRecord]


class CohortOverlap(BaseModel):
    method: str
    match_attributes: list[str]
    math_rows: int
    portuguese_rows: int
    join_pairs: int
    math_rows_matched: int
    portuguese_rows_matched: int
    unambiguous_matches: int
    ambiguous_profiles: int
    caveat: str


class ErrorResponse(BaseModel):
    code: str
    detail: str
