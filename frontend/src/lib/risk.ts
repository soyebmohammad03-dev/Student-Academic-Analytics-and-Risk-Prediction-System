/** Types for /risk and /interpretability responses. Mirror backend/analytics/{risk,interpret}. */

import type { Cohort } from "./api";

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
