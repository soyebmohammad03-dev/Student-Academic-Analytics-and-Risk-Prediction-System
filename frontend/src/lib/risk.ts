/** Types for /risk and /interpretability responses. Mirror backend/analytics/{risk,interpret}. */

import type { Cohort } from "./api";
import type { PredictionResult } from "./models";

export type Task = "regression" | "classification";
export type Scenario = "early" | "mid_year" | "full_history";

export interface Interval {
  low: number | null;
  high: number | null;
  confidence: number;
}

export interface ProfileGroup {
  key: string;
  label: string;
  n: number;
  at_risk: number;
  risk_percent: number;
  risk_ci: Interval;
  difference_from_overall: number;
  reliable: boolean;
}

export interface SingleProfile {
  variable: string;
  label: string;
  groups: ProfileGroup[];
  test: string;
  p: number | null;
  p_adjusted: number | null;
  cramers_v: number | null;
  magnitude: string;
  warnings: string[];
}

export interface PairCell {
  row: string;
  row_label: string;
  column: string;
  column_label: string;
  n: number;
  at_risk: number;
  risk_percent: number | null;
  risk_ci: Interval;
  reliable: boolean;
}

export interface RiskProfiles {
  kind: "group_statistics";
  cohort: Cohort;
  n: number;
  at_risk: number;
  risk_percent: number;
  risk_ci: Interval;
  threshold: number;
  single: SingleProfile[];
  pairs: Array<{
    rows_variable: string;
    rows_label: string;
    columns_variable: string;
    columns_label: string;
    cells: PairCell[];
  }>;
  notes: string[];
}

export interface ImportanceItem {
  feature: string;
  attribute: string;
  label: string;
  value: number;
  std: number | null;
  rank: number;
}

export interface ImportanceResult {
  cohort: Cohort;
  task: Task;
  scenario: Scenario;
  model: string;
  model_label: string;
  method:
    "permutation_test" | "mean_abs_shapley" | "impurity_decrease" | "standardised_coefficient";
  method_label: string;
  data: string;
  unit: string;
  items: ImportanceItem[];
  limitations: string[];
}

export interface ModelInterpretation {
  cohort: Cohort;
  task: Task;
  scenario: Scenario;
  model: string;
  model_label: string;
  methods: ImportanceResult[];
  calibration: {
    n: number;
    brier: number;
    mean_predicted: number;
    observed_rate: number;
    bins: Array<{
      low: number;
      high: number;
      n: number;
      mean_predicted: number | null;
      observed_rate: number | null;
    }>;
    note: string;
  } | null;
}

export const taskOptions = [
  { value: "classification", label: "Academic risk" },
  { value: "regression", label: "Final grade" },
] as const satisfies ReadonlyArray<{ value: Task; label: string }>;

export const scenarioOptions = [
  { value: "early", label: "Early" },
  { value: "mid_year", label: "Mid-year" },
  { value: "full_history", label: "Full history" },
] as const satisfies ReadonlyArray<{ value: Scenario; label: string }>;

// --- Individual explanations, sensitivity and insights ----------------------------

export interface Contribution {
  attribute: string;
  label: string;
  value: string;
  contribution: number;
  standard_error: number;
  direction: "raises" | "lowers" | "negligible";
}

export interface Explanation {
  kind: "individual_model_explanation";
  method: string;
  output: string;
  base_value: number;
  prediction: number;
  contributions: Contribution[];
  other_attributes: number;
  other_contribution: number;
  n_samples: number;
  background: string;
  background_size: number;
  seed: number;
  reading: string;
  limitations: string[];
}

export interface ExplainedPrediction {
  prediction: PredictionResult;
  explanation: Explanation;
  /** Classification only: percentile of the score among training students (context, not a category). */
  score_percentile: number | null;
}

export const sensitivityAttributes = [
  "studytime",
  "absences",
  "goout",
  "freetime",
  "traveltime",
  "activities",
  "paid",
  "famsup",
  "schoolsup",
  "internet",
] as const;
export type SensitivityAttribute = (typeof sensitivityAttributes)[number];

export interface Sensitivity {
  kind: "model_sensitivity";
  cohort: Cohort;
  task: Task;
  scenario: Scenario;
  model: string;
  attribute: SensitivityAttribute;
  label: string;
  output: string;
  points: Array<{
    value: string;
    label: string;
    current: boolean;
    output: number;
    predicted_grade: number | null;
    at_risk: boolean | null;
    support: number;
    sparse: boolean;
  }>;
  note: string;
}

export interface ScenarioSensitivity {
  kind: "model_sensitivity";
  cohort: Cohort;
  task: Task;
  items: Array<{
    scenario: Scenario;
    model: string;
    model_label: string;
    output: number;
    predicted_grade: number | null;
    at_risk: boolean | null;
  }>;
  skipped: Scenario[];
  note: string;
}

export interface GroupFinding {
  kind: "group_statistics";
  variable: string;
  label: string;
  group: string;
  n: number;
  risk_percent: number;
  risk_ci: Interval;
  reliable: boolean;
  cohort_risk_percent: number;
}

export interface Suggestion {
  kind: "general_educational_suggestion";
  key: string;
  text: string;
  trigger: string;
  evidence: {
    kind: string;
    summary: string;
    group_n: number | null;
    group_risk_percent: number | null;
    comparison_n: number | null;
    comparison_risk_percent: number | null;
    p: number | null;
    supported: boolean;
  };
}

export interface RiskInsights {
  individual: ExplainedPrediction;
  group: GroupFinding[];
  suggestions: {
    cohort: Cohort;
    suggestions: Suggestion[];
    not_shown: Suggestion[];
    disclaimer: string;
  };
  reading: string[];
}
