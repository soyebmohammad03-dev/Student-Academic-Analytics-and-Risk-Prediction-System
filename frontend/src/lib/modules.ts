import {
  BookOpen,
  ChartScatter,
  Crosshair,
  GitCompareArrows,
  LayoutDashboard,
  ScanSearch,
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
    key: "models",
    title: "Model Comparison",
    href: "/model-comparison",
    icon: GitCompareArrows,
    phase: 5,
    status: "available",
    summary: "Cross-validated comparison of candidate models against simple baselines.",
    scope: [
      "Baselines: mean predictor and majority class",
      "Regression: MAE, RMSE, R²",
      "Classification: precision, recall, F1, ROC-AUC, confusion matrix",
      "Nested cross-validation separated from the held-out test set",
      "Early, mid-year and full-history scenarios compared for both cohorts",
    ],
  },
  {
    key: "prediction",
    title: "Prediction",
    href: "/prediction",
    icon: Crosshair,
    phase: 6,
    status: "available",
    summary: "Predict final grade and academic risk for one record under a stated scenario.",
    scope: [
      "Validated input form for a single student profile",
      "Grade (regression) and academic-risk (classification) outputs, shown separately",
      "Explicit scenario selection: early (no grades), mid-year (G1) or full history (G1+G2)",
      "Per-prediction explanation, observed group statistics and suggestions for review",
    ],
  },
  {
    key: "interpretability",
    title: "Interpretability",
    href: "/interpretability",
    icon: ScanSearch,
    phase: 6,
    status: "available",
    summary: "What the selected models rely on, globally and for one record.",
    scope: [
      "Global importance per method, each on its own scale",
      "Probability calibration of the selected classifiers",
      "Individual Shapley explanations",
      "Model sensitivity experiments for school-related attributes and scenarios",
    ],
  },
  {
    key: "risk",
    title: "Risk Analysis",
    href: "/risk-analysis",
    icon: ShieldAlert,
    phase: 6,
    status: "available",
    summary: "Observed academic risk across school-related groups, with uncertainty.",
    scope: [
      "Observed academic risk by past failures, study time, absences and support, with 95% intervals",
      "Two-way tables with sample sizes",
      "Selected classifiers' ability to find students below the pass mark",
      "Evidence-checked suggestions for human review",
    ],
  },
];

export const dashboardItem = {
  title: "Dashboard",
  href: "/",
  icon: LayoutDashboard,
} as const;

export const aboutItem = {
  title: "Methodology",
  href: "/about",
  icon: BookOpen,
} as const;

export const allModules: AppModule[] = [...analysisModules, ...modellingModules];
