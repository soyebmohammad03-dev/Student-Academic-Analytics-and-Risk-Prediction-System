/** Types for /models responses. Mirror backend/analytics/ml/{results,comparison}.py. */

import type { Cohort } from "./api";
import type { Scenario, Task } from "./risk";

export type Num = number | null;
export type Metrics = Record<string, Num>;

export interface MetricSummary {
  mean: Num;
  std: Num;
  folds: Num[];
  defined_folds: number;
}

export interface Confusion {
  tn: number;
  fp: number;
  fn: number;
  tp: number;
}

export interface Diagnostic {
  level: "info" | "warning";
  code: string;
  message: string;
}

export interface ModelResult {
  cohort: Cohort;
  task: Task;
  scenario: Scenario;
  model: string;
  label: string;
  family: string;
  baseline: boolean;
  complexity: number;
  class_weight: string | null;
  search_space: Record<string, unknown[]>;
  candidates: number;
  best_params: Record<string, unknown>;
  outer_fold_params: Array<Record<string, unknown>>;
  cv: Record<string, MetricSummary>;
  test: Metrics;
  test_confusion: Confusion | null;
  test_predicted_positive: number | null;
  n_train: number;
  n_test: number;
  diagnostics: Diagnostic[];
}

export interface Selection {
  cohort: Cohort;
  task: Task;
  scenario: Scenario;
  model: string;
  label: string;
  primary_metric: string;
  best_model: string;
  best_mean: Num;
  tolerance: Num;
  within_tolerance: string[];
  beats_baseline: boolean;
  baseline_mean: Num;
  reason: string;
}

export interface RegressionErrors {
  cohort: Cohort;
  scenario: Scenario;
  model: string;
  n: number;
  metrics: Metrics;
  residuals: {
    mean: Num;
    std: Num;
    median: Num;
    q1: Num;
    q3: Num;
    min: Num;
    max: Num;
    within_1: number;
    within_2: number;
  };
  histogram: Array<{ start: number; end: number; label: string; count: number }>;
  by_band: Array<{ band: string; n: number; mae: Num; mean_residual: Num }>;
  largest: Array<{ row: number; actual: number; predicted: number; residual: number }>;
  patterns: string[];
}

export interface ClassificationErrors {
  cohort: Cohort;
  scenario: Scenario;
  model: string;
  n: number;
  threshold: number;
  score_kind: "probability" | "decision_function";
  confusion: Confusion;
  metrics: Metrics;
  by_class: Array<{ label: string; n: number; correct: number; rate: Num }>;
  false_negative_grades: Array<{ grade: number; count: number }>;
  false_positive_grades: Array<{ grade: number; count: number }>;
  zero_grade_detected: number;
  zero_grade_total: number;
  patterns: string[];
}

export interface ZeroGradeSensitivity {
  cohort: Cohort;
  scenario: Scenario;
  model: string;
  train_zeros_removed: number;
  test_n: number;
  all_rows_model: Metrics;
  without_zeros_model: Metrics;
  note: string;
}

export interface ArtifactMetadata {
  cohort: Cohort;
  task: Task;
  scenario: Scenario;
  model: string;
  label: string;
  feature_columns: string[];
  target: string;
  positive_class: string | null;
  threshold: Num;
  score_kind: "probability" | "decision_function" | null;
  best_params: Record<string, unknown>;
  cv_folds: number;
  cv_strategy: string;
  n_train: number;
  n_test: number;
  created_at: string;
}

export interface SelectedModelDetail {
  metadata: ArtifactMetadata;
  selection: Selection;
  regression_errors: RegressionErrors | null;
  classification_errors: ClassificationErrors | null;
  zero_grade_sensitivity: ZeroGradeSensitivity | null;
}

export interface ScenarioComparison {
  cohort: Cohort;
  task: Task;
  primary_metric: string;
  rows: Array<{
    scenario: Scenario;
    label: string;
    information: string;
    selected_model: string;
    selected_label: string;
    best_cv_model: string;
    cv: Metrics;
    cv_std: Metrics;
    test: Metrics;
    baseline_cv: Metrics;
    baseline_test: Metrics;
  }>;
  note: string;
}

export interface CohortComparison {
  cohorts: Array<{
    cohort: Cohort;
    subject: string;
    n: number;
    n_train: number;
    n_test: number;
    risk: Record<"all" | "train" | "test", { n: number; at_risk: number; at_risk_percent: number }>;
    selected: Array<{
      task: Task;
      scenario: Scenario;
      model: string;
      label: string;
      cv_primary: Num;
      test_primary: Num;
    }>;
  }>;
  differences: string[];
}

export interface ModelCatalog {
  trained: boolean;
  run: {
    created_at: string;
    random_state: number;
    cv_folds: number;
    test_size: number;
    cv_strategy: Record<Task, string>;
    tuning_metric: Record<Task, string>;
    selection_metric: Record<Task, string>;
    decision_threshold: number;
  } | null;
  models: Array<{
    task: Task;
    key: string;
    label: string;
    family: string;
    baseline: boolean;
    class_weight: string | null;
    strengths: string;
    weaknesses: string;
  }>;
  selected: Array<{ cohort: Cohort; task: Task; scenario: Scenario; model: string; label: string }>;
}

// --- Prediction ----------------------------------------------------------------

export type FeatureValue = string | number;
export type Features = Record<string, FeatureValue>;

export interface PredictionRequest {
  cohort: Cohort;
  task: Task;
  scenario: Scenario;
  features: Features;
}

export interface PredictionResult {
  cohort: Cohort;
  task: Task;
  scenario: Scenario;
  model: string;
  model_label: string;
  predicted_grade: Num;
  raw_prediction: Num;
  at_risk: boolean | null;
  score: Num;
  /** Only present when the model outputs probabilities (class-weighted, not calibrated). */
  probability: Num;
  score_kind: "probability" | "decision_function" | null;
  threshold: Num;
  model_test_metrics: Metrics;
  trained_at: string;
  caveats: string[];
}

// --- Metric vocabulary -----------------------------------------------------------

export interface MetricInfo {
  label: string;
  short: string;
  /** Whether a larger value is better. */
  higherIsBetter: boolean;
  definition: string;
}

/** Definitions shown in tooltips; wording follows docs/METHODOLOGY.md §6.6. */
export const metricInfo: Record<string, MetricInfo> = {
  mae: {
    label: "Mean absolute error",
    short: "MAE",
    higherIsBetter: false,
    definition: "Average size of the error, in grade points (0–20 scale). Lower is better.",
  },
  rmse: {
    label: "Root mean squared error",
    short: "RMSE",
    higherIsBetter: false,
    definition:
      "Error in grade points that penalises large misses more than MAE. Lower is better. Primary regression metric.",
  },
  mse: {
    label: "Mean squared error",
    short: "MSE",
    higherIsBetter: false,
    definition: "Average squared error, in squared grade points. Lower is better.",
  },
  r2: {
    label: "Coefficient of determination",
    short: "R²",
    higherIsBetter: true,
    definition:
      "Share of the variance in final grades explained by the model. 0 means no better than predicting the mean.",
  },
  f1: {
    label: "F1 score (at risk)",
    short: "F1",
    higherIsBetter: true,
    definition:
      "Harmonic mean of precision and recall for the at-risk class. Primary classification metric.",
  },
  recall: {
    label: "Recall (sensitivity)",
    short: "Recall",
    higherIsBetter: true,
    definition: "Share of students below the pass mark whom the model flagged.",
  },
  precision: {
    label: "Precision",
    short: "Precision",
    higherIsBetter: true,
    definition:
      "Share of flagged students who were actually below the pass mark. Undefined when no student is flagged.",
  },
  specificity: {
    label: "Specificity",
    short: "Specificity",
    higherIsBetter: true,
    definition: "Share of passing students who were not flagged.",
  },
  roc_auc: {
    label: "ROC-AUC",
    short: "ROC-AUC",
    higherIsBetter: true,
    definition:
      "How well the model's score ranks at-risk students above others, across all thresholds. 0.5 is chance.",
  },
  balanced_accuracy: {
    label: "Balanced accuracy",
    short: "Bal. acc.",
    higherIsBetter: true,
    definition: "Mean of recall and specificity; unaffected by class imbalance.",
  },
  accuracy: {
    label: "Accuracy",
    short: "Accuracy",
    higherIsBetter: true,
    definition:
      "Share of correct labels. Misleading on its own: predicting “not at risk” for everyone already scores the majority share.",
  },
};

export const regressionMetrics = ["mae", "rmse", "r2"] as const;
export const classificationMetrics = ["precision", "recall", "f1", "roc_auc"] as const;

export const scenarioInfo: Record<Scenario, { label: string; inputs: string; when: string }> = {
  early: {
    label: "Early",
    inputs: "Non-grade attributes only",
    when: "Before any grade of the year",
  },
  mid_year: {
    label: "Mid-year",
    inputs: "Non-grade attributes + G1",
    when: "After the first grading period",
  },
  full_history: {
    label: "Full history",
    inputs: "Non-grade attributes + G1 + G2",
    when: "After the second grading period",
  },
};

/** Grades a scenario allows as inputs. G3 is never an input. */
export function allowedGrades(scenario: Scenario): Array<"G1" | "G2"> {
  if (scenario === "full_history") return ["G1", "G2"];
  if (scenario === "mid_year") return ["G1"];
  return [];
}
