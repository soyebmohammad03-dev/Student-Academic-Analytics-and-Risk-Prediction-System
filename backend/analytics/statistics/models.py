"""Typed results of the statistical and EDA analyses.

They are Pydantic models so that results are validated, serialisable and reusable
directly as API response schemas. Every float that could be undefined (e.g. a
variance of a single value) is optional and set to ``None`` rather than NaN.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Num = float | None


class Interval(BaseModel):
    low: Num
    high: Num
    confidence: float = 0.95


# --- Descriptive ---------------------------------------------------------------------


class NumericSummary(BaseModel):
    variable: str
    label: str
    scale: str = Field(description="Measurement scale from the data dictionary.")
    n: int
    mean: Num
    mean_ci: Interval
    median: Num
    modes: list[float] = Field(description="All most-frequent values (ties included).")
    minimum: Num
    maximum: Num
    range: Num
    variance: Num = Field(description="Sample variance (ddof = 1).")
    std: Num = Field(description="Sample standard deviation (ddof = 1).")
    q1: Num
    q3: Num
    iqr: Num
    skewness: Num = Field(description="Sample skewness (bias-corrected).")
    kurtosis: Num = Field(description="Excess kurtosis (bias-corrected); 0 for a normal.")
    note: str | None = None


class CategoryCount(BaseModel):
    value: str
    label: str
    count: int
    percent: float


class CategoricalSummary(BaseModel):
    variable: str
    label: str
    scale: str
    n: int
    mode: list[str]
    categories: list[CategoryCount]


class DescriptiveStatistics(BaseModel):
    cohort: str
    n: int
    numeric: list[NumericSummary]
    categorical: list[CategoricalSummary]


# --- Distributions ---------------------------------------------------------------------


class ValueCount(BaseModel):
    value: int
    count: int


class Shape(BaseModel):
    skewness: Num
    kurtosis: Num
    shapiro_w: Num
    shapiro_p: Num
    normality_rejected: bool
    description: str


class GradeDistribution(BaseModel):
    variable: str
    label: str
    summary: NumericSummary
    counts: list[ValueCount]
    zero_count: int
    shape: Shape
    summary_excluding_zeros: NumericSummary | None = Field(
        description="Sensitivity view only. Zero grades are valid and are never removed."
    )


class RiskSummary(BaseModel):
    threshold: int
    n: int
    at_risk: int
    proportion: float
    proportion_ci: Interval
    zero_grade_at_risk: int = Field(description="At-risk students whose G3 is exactly 0.")


class Distributions(BaseModel):
    cohort: str
    grades: list[GradeDistribution]
    risk: RiskSummary
    observations: list[str] = Field(description="Data-derived notes about zero grades.")


# --- Correlation ------------------------------------------------------------------------


class Correlation(BaseModel):
    x: str
    y: str
    x_label: str
    y_label: str
    method: Literal["pearson", "spearman"]
    method_reason: str
    r: Num
    r_ci: Interval
    p: Num
    p_adjusted: Num = None
    n: int
    strength: str
    direction: Literal["positive", "negative", "none"]
    interpretation: str
    pearson_r: Num = Field(description="Reported for comparison regardless of the primary method.")
    spearman_r: Num


class CorrelationMatrix(BaseModel):
    method: Literal["spearman"]
    variables: list[str]
    labels: list[str]
    r: list[list[Num]]
    p_adjusted: list[list[Num]] = Field(description="Benjamini–Hochberg across the matrix.")
    n: int


class Correlations(BaseModel):
    cohort: str
    key_pairs: list[Correlation]
    key_pairs_correction: str
    sensitivity_key_pairs: list[Correlation] = Field(
        description="Exploratory: the key pairs recomputed without students whose G3 is 0."
    )
    matrix: CorrelationMatrix


# --- Group comparisons ---------------------------------------------------------------------


class GroupSummary(BaseModel):
    key: str
    label: str
    n: int
    mean: Num
    mean_ci: Interval
    std: Num
    median: Num
    q1: Num
    q3: Num
    small: bool = Field(description="n below the minimum group size used for flagging.")
    box: BoxGroup = Field(description="Box-plot statistics (whiskers at 1.5·IQR).")


class NormalityCheck(BaseModel):
    group: str
    n: int
    shapiro_w: Num
    shapiro_p: Num
    skewness: Num
    adequate: bool
    basis: str


class VarianceCheck(BaseModel):
    test: str = "Levene (median-centred, Brown–Forsythe)"
    statistic: Num
    p: Num
    equal_variances: bool


class EffectSize(BaseModel):
    name: str
    value: Num
    ci: Interval | None = None
    magnitude: str


class PostHocComparison(BaseModel):
    group_a: str
    group_b: str
    estimate: Num = Field(description="Mean difference (a − b), or Dunn z for rank tests.")
    p_adjusted: Num
    significant: bool


class GroupComparison(BaseModel):
    variable: str
    variable_label: str
    outcome: str
    groups: list[GroupSummary]
    normality: list[NormalityCheck]
    variance: VarianceCheck
    test: str
    family: Literal["parametric", "non-parametric"]
    statistic_name: str
    statistic: Num
    df: str | None
    p: Num
    p_adjusted: Num = None
    significant: bool = Field(description="Unadjusted p < alpha.")
    effect_sizes: list[EffectSize]
    rationale: str
    posthoc_method: str | None
    posthoc: list[PostHocComparison]
    warnings: list[str]


# --- Categorical association -------------------------------------------------------------


class ContingencyRow(BaseModel):
    category: str
    label: str
    at_risk: int
    not_at_risk: int
    n: int
    risk_percent: float
    risk_ci: Interval


class Association(BaseModel):
    variable: str
    label: str
    outcome: str = "at_risk"
    rows: list[ContingencyRow]
    test: str
    statistic: Num
    dof: int | None
    p: Num
    p_adjusted: Num = None
    cramers_v: Num
    magnitude: str
    min_expected: Num
    warnings: list[str]


class Associations(BaseModel):
    cohort: str
    correction: str
    items: list[Association]


# --- Outliers --------------------------------------------------------------------------


class OutlierReport(BaseModel):
    variable: str
    label: str
    n: int
    q1: Num
    q3: Num
    iqr: Num
    lower_fence: Num
    upper_fence: Num
    below: int
    above: int
    count: int
    proportion: float
    z_count: int = Field(description="Values with |z| > 3.")
    flagged_values: list[ValueCount]


class Outliers(BaseModel):
    cohort: str
    method: str
    items: list[OutlierReport]
    excluded: dict[str, str]


# --- Research questions ---------------------------------------------------------------------


class ResearchQuestion(BaseModel):
    key: str
    question: str
    h0: str
    h1: str
    analysis: str
    evidence: Literal["confirmatory", "exploratory"]
    test: str
    statistic: Num
    p: Num
    p_adjusted: Num
    significant: bool = Field(description="Adjusted p < alpha.")
    effect: EffectSize | None
    finding: str
    sensitivity: str | None = Field(
        default=None,
        description="Exploratory re-run without G3 = 0 students (unadjusted p).",
    )


class ResearchQuestions(BaseModel):
    cohort: str
    alpha: float
    correction: str
    items: list[ResearchQuestion]


# --- EDA chart data ---------------------------------------------------------------------------


class HistogramBin(BaseModel):
    start: float
    end: float
    label: str
    count: int


class Histogram(BaseModel):
    variable: str
    label: str
    n: int
    bins: list[HistogramBin]


class Bar(BaseModel):
    key: str
    label: str
    count: int
    percent: float


class BarChart(BaseModel):
    variable: str
    label: str
    n: int
    bars: list[Bar]


class BoxGroup(BaseModel):
    key: str
    label: str
    n: int
    whisker_low: Num
    q1: Num
    median: Num
    q3: Num
    whisker_high: Num
    mean: Num
    outliers: list[ValueCount]


class BoxPlot(BaseModel):
    variable: str
    variable_label: str
    outcome: str
    groups: list[BoxGroup]


class ScatterPoint(BaseModel):
    x: float
    y: float
    count: int


class Scatter(BaseModel):
    x: str
    y: str
    x_label: str
    y_label: str
    n: int
    points: list[ScatterPoint] = Field(description="Identical (x, y) pairs are aggregated.")
    spearman_r: Num


class ProfileRow(BaseModel):
    variable: str
    label: str
    statistic: Literal["mean", "percent"]
    at_risk: Num
    not_at_risk: Num
    standardised_difference: Num = Field(
        description="Cohen's d (at risk − not at risk) for numeric rows."
    )


class CrossTabCell(BaseModel):
    row: str
    column: str
    n: int
    mean: Num


class CrossTab(BaseModel):
    rows_variable: str
    columns_variable: str
    outcome: str
    row_labels: list[str]
    column_labels: list[str]
    cells: list[CrossTabCell]


class Eda(BaseModel):
    cohort: str
    histograms: list[Histogram]
    bars: list[BarChart]
    boxplots: list[BoxPlot]
    scatters: list[Scatter]
    heatmap: CorrelationMatrix
    risk_profile: list[ProfileRow]
    crosstab: CrossTab
