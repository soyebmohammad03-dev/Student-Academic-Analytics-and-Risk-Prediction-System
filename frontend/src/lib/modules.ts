import {
  BookOpen,
  ChartScatter,
  Crosshair,
  GitCompareArrows,
  LayoutDashboard,
  type LucideIcon,
  ShieldAlert,
  Sigma,
  Table2,
} from "lucide-react";

export type ModuleStatus = "planned" | "in_progress" | "available";

export interface AppModule {
  key: string;
  title: string;
  href: string;
  icon: LucideIcon;
  /** Roadmap phase in which the module is delivered. */
  phase: number;
  status: ModuleStatus;
  summary: string;
  /** Scope of the module, mirrored from PROJECT_ROADMAP.md. */
  scope: string[];
  /** What already exists while the module is in progress. */
  progressNote?: string;
}

export const analysisModules: AppModule[] = [
  {
    key: "data",
    title: "Data Explorer",
    href: "/data-explorer",
    icon: Table2,
    phase: 2,
    status: "available",
    summary: "Browse both student cohorts with a validated schema and attribute dictionary.",
    scope: [
      "Checksum-verified download of the UCI dataset",
      "Schema validation: types, allowed values, ranges, duplicates",
      "Data dictionary for all 33 attributes",
      "Searchable, paginated record table with cohort switch",
    ],
  },
  {
    key: "statistics",
    title: "Statistical Analysis",
    href: "/statistics",
    icon: Sigma,
    phase: 4,
    status: "available",
    summary: "Descriptive, correlational and inferential statistics with effect sizes.",
    scope: [
      "Mean, median, mode, variance, standard deviation, range, quartiles",
      "Normality and variance-homogeneity checks",
      "Pearson and Spearman correlations with significance",
      "t-test / ANOVA, or Mann–Whitney / Kruskal–Wallis when assumptions fail",
      "Chi-square tests for categorical associations, with effect sizes",
    ],
  },
  {
    key: "eda",
    title: "Exploratory Analysis",
    href: "/eda",
    icon: ChartScatter,
    phase: 4,
    status: "available",
    summary: "Univariate, bivariate and multivariate patterns behind academic performance.",
    scope: [
      "Distributions, box plots and group comparisons",
      "Correlation heatmap and scatter analysis",
      "Outlier analysis",
      "Study time, absences, failures, family and school support, social factors",
      "Academic-performance profiling",
    ],
  },
];

export const modellingModules: AppModule[] = [
  {
    key: "prediction",
    title: "Prediction",
    href: "/prediction",
    icon: Crosshair,
    phase: 6,
    status: "in_progress",
    summary: "Predict final grade and academic risk under clearly stated input scenarios.",
    progressNote:
      "The prediction and explanation services are available through the API (POST /api/v1/models/predict, /api/v1/interpretability/explain and /api/v1/risk/insights). The input form is built in Phase 8.",
    scope: [
      "Validated input form for a single student profile",
      "Grade (regression) and academic-risk (classification) outputs",
      "Explicit scenario selection: full history (G1+G2), mid-year (G1) or early (no grades)",
      "Per-prediction explanation of contributing factors",
    ],
  },
  {
    key: "models",
    title: "Model Comparison",
    href: "/model-comparison",
    icon: GitCompareArrows,
    phase: 5,
    status: "in_progress",
    summary: "Cross-validated comparison of candidate models against simple baselines.",
    progressNote:
      "Models are trained and evaluated on the real dataset (Phase 5). Results are served by the API at /api/v1/models and summarised in docs/ML_RESULTS.md; this page is built in Phase 8.",
    scope: [
      "Baselines: mean predictor and majority class",
      "Regression: MAE, MSE, RMSE, R²",
      "Classification: accuracy, precision, recall, F1, ROC-AUC, confusion matrix",
      "Nested, stratified cross-validation and bounded grid-search tuning",
      "Early, mid-year and full-history scenarios compared for both cohorts",
    ],
  },
  {
    key: "risk",
    title: "Risk Analysis",
    href: "/risk-analysis",
    icon: ShieldAlert,
    phase: 6,
    status: "available",
    summary: "Interpretable insight into which factors are associated with academic risk.",
    scope: [
      "Observed academic risk by past failures, study time, absences and support, with 95% intervals",
      "Global importance of the selected models: permutation, Shapley, impurity and coefficients",
      "Probability calibration of the selected classifiers",
      "Individual explanations, sensitivity experiments and suggestions via the API",
    ],
  },
];

export const dashboardItem = {
  title: "Dashboard",
  href: "/",
  icon: LayoutDashboard,
} as const;

export const aboutItem = {
  title: "About & Methodology",
  href: "/about",
  icon: BookOpen,
} as const;

export const allModules: AppModule[] = [...analysisModules, ...modellingModules];

export function getModule(key: string): AppModule {
  const found = allModules.find((m) => m.key === key);
  if (!found) throw new Error(`Unknown module: ${key}`);
  return found;
}
