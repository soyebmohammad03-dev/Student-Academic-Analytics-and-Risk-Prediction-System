/** Types for /statistics and /eda responses. Mirror backend/analytics/statistics/models.py. */

export type Num = number | null;
export interface Interval {
  low: Num;
  high: Num;
  confidence: number;
}
export interface ValueCount {
  value: number;
  count: number;
}

export interface NumericSummary {
  variable: string;
  label: string;
  scale: string;
  n: number;
  mean: Num;
  mean_ci: Interval;
  median: Num;
  modes: number[];
  minimum: Num;
  maximum: Num;
  range: Num;
  variance: Num;
  std: Num;
  q1: Num;
  q3: Num;
  iqr: Num;
  skewness: Num;
  kurtosis: Num;
  note: string | null;
}

export interface DescriptiveStatistics {
  cohort: string;
  n: number;
  numeric: NumericSummary[];
  categorical: Array<{
    variable: string;
    label: string;
    n: number;
    mode: string[];
    categories: Array<{ value: string; label: string; count: number; percent: number }>;
  }>;
}

export interface Distributions {
  cohort: string;
  grades: Array<{
    variable: string;
    label: string;
    summary: NumericSummary;
    counts: ValueCount[];
    zero_count: number;
    shape: { skewness: Num; kurtosis: Num; shapiro_p: Num; description: string };
    summary_excluding_zeros: NumericSummary | null;
  }>;
  risk: {
    threshold: number;
    n: number;
    at_risk: number;
    proportion: number;
    proportion_ci: Interval;
    zero_grade_at_risk: number;
  };
  observations: string[];
}

export interface Correlation {
  x: string;
  y: string;
  x_label: string;
  y_label: string;
  method: "pearson" | "spearman";
  method_reason: string;
  r: Num;
  r_ci: Interval;
  p: Num;
  p_adjusted: Num;
  n: number;
  strength: string;
  interpretation: string;
  pearson_r: Num;
  spearman_r: Num;
}

export interface CorrelationMatrix {
  method: "spearman";
  variables: string[];
  labels: string[];
  r: Num[][];
  p_adjusted: Num[][];
  n: number;
}

export interface Correlations {
  cohort: string;
  key_pairs: Correlation[];
  key_pairs_correction: string;
  sensitivity_key_pairs: Correlation[];
  matrix: CorrelationMatrix;
}

export interface EffectSize {
  name: string;
  value: Num;
  ci: Interval | null;
  magnitude: string;
}

export interface GroupComparison {
  variable: string;
  variable_label: string;
  outcome: string;
  groups: Array<{
    key: string;
    label: string;
    n: number;
    mean: Num;
    mean_ci: Interval;
    std: Num;
    median: Num;
    q1: Num;
    q3: Num;
    small: boolean;
    box: BoxGroup;
  }>;
  normality: Array<{
    group: string;
    n: number;
    shapiro_p: Num;
    skewness: Num;
    adequate: boolean;
    basis: string;
  }>;
  variance: { test: string; statistic: Num; p: Num; equal_variances: boolean };
  test: string;
  family: "parametric" | "non-parametric";
  statistic_name: string;
  statistic: Num;
  df: string | null;
  p: Num;
  significant: boolean;
  effect_sizes: EffectSize[];
  rationale: string;
  posthoc_method: string | null;
  posthoc: Array<{
    group_a: string;
    group_b: string;
    estimate: Num;
    p_adjusted: Num;
    significant: boolean;
  }>;
  warnings: string[];
}

export interface ResearchQuestion {
  key: string;
  question: string;
  h0: string;
  h1: string;
  analysis: string;
  evidence: "confirmatory" | "exploratory";
  test: string;
  statistic: Num;
  p: Num;
  p_adjusted: Num;
  significant: boolean;
  effect: EffectSize | null;
  finding: string;
  sensitivity: string | null;
}

export interface ResearchQuestions {
  cohort: string;
  alpha: number;
  correction: string;
  items: ResearchQuestion[];
}

export interface Associations {
  cohort: string;
  correction: string;
  items: Array<{
    variable: string;
    label: string;
    rows: Array<{
      category: string;
      label: string;
      at_risk: number;
      n: number;
      risk_percent: number;
    }>;
    test: string;
    statistic: Num;
    dof: number | null;
    p: Num;
    p_adjusted: Num;
    cramers_v: Num;
    magnitude: string;
    warnings: string[];
  }>;
}

export interface Outliers {
  cohort: string;
  method: string;
  items: Array<{
    variable: string;
    label: string;
    n: number;
    lower_fence: Num;
    upper_fence: Num;
    below: number;
    above: number;
    count: number;
    proportion: number;
    z_count: number;
  }>;
  excluded: Record<string, string>;
}

export interface Histogram {
  variable: string;
  label: string;
  n: number;
  bins: Array<{ start: number; end: number; label: string; count: number }>;
}

export interface BarChartData {
  variable: string;
  label: string;
  n: number;
  bars: Array<{ key: string; label: string; count: number; percent: number }>;
}

export interface BoxGroup {
  key: string;
  label: string;
  n: number;
  whisker_low: Num;
  q1: Num;
  median: Num;
  q3: Num;
  whisker_high: Num;
  mean: Num;
  outliers: ValueCount[];
}

export interface BoxPlotData {
  variable: string;
  variable_label: string;
  outcome: string;
  groups: BoxGroup[];
}

export interface ScatterData {
  x: string;
  y: string;
  x_label: string;
  y_label: string;
  n: number;
  points: Array<{ x: number; y: number; count: number }>;
  spearman_r: Num;
}

export interface Eda {
  cohort: string;
  histograms: Histogram[];
  bars: BarChartData[];
  boxplots: BoxPlotData[];
  scatters: ScatterData[];
  heatmap: CorrelationMatrix;
  risk_profile: Array<{
    variable: string;
    label: string;
    statistic: "mean" | "percent";
    at_risk: Num;
    not_at_risk: Num;
    standardised_difference: Num;
  }>;
  crosstab: {
    rows_variable: string;
    columns_variable: string;
    outcome: string;
    row_labels: string[];
    column_labels: string[];
    cells: Array<{ row: string; column: string; n: number; mean: Num }>;
  };
}

export function cohortPath(path: string, cohort: string, extra?: Record<string, string>) {
  const params = new URLSearchParams({ cohort, ...extra });
  return `${path}?${params}`;
}
