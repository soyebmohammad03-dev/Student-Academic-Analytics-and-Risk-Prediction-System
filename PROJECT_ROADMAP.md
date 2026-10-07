# Project Roadmap

**Student Academic Analytics and Risk Prediction System**

Each phase ends with code review, test verification, a git status check, one
meaningful commit and a push. Phases are never combined into a single commit.

| Phase | Name                                        | Status      |
| ----- | ------------------------------------------- | ----------- |
| 1     | Foundation & architecture                   | ✅ Complete |
| 2     | Real dataset & Data Explorer                | ✅ Complete |
| 3     | Preprocessing & feature engineering         | ✅ Complete |
| 4     | Statistics & exploratory data analysis      | ✅ Complete |
| 5     | Machine learning & model evaluation         | Planned     |
| 6     | Interpretability & academic risk analysis   | Planned     |
| 7     | End-to-end backend integration              | Planned     |
| 8     | Complete Apple-style frontend               | Planned     |
| 9     | Final validation, documentation & presentation readiness | Planned |

The roadmap was revised to nine phases after Phase 2. Preprocessing now comes before
statistics so that both statistics and modelling build on the same analytical dataset.

## Phase 1 — Foundation & architecture ✅
- Repository structure and documentation.
- FastAPI skeleton: config, health and project-metadata endpoints.
- Next.js shell with the design system and navigation.
- Linting, tests, Git/GitHub.

## Phase 2 — Real dataset & Data Explorer ✅
- Checksum-verified download of the official UCI archive.
- Loader and structured validation. Both official files pass every check.
- Data dictionary for all 33 attributes.
- Approximate cross-cohort matching, with its assumptions stated.
- Dataset API: summary, schema, quality, records, overlap.
- Functional Data Explorer page.

## Phase 3 — Preprocessing & feature engineering ✅
- `backend/analytics/preprocessing/`: raw → validated → analytical data layers. No
  rows removed and the raw files are never written.
- Targets: `G3` (regression) and `at_risk = G3 < 10` (classification, academic risk;
  not dropout).
- Leakage-aware feature scenarios: `full_history` (G1+G2), `mid_year` (G1) and
  `early` (no grades). A `ScenarioGuard` makes it impossible to mix them.
- scikit-learn `Pipeline`/`ColumnTransformer`:
  - one-hot encoding for binary and nominal variables, with categories fixed by the
    dictionary;
  - documented ordinal codes kept;
  - optional scaling;
  - training-set imputation.
- Two justified engineered features: `has_past_failures` and `log_absences`. Rejected
  candidates are documented with reasons.
- Reproducible stratified 80/20 split (`random_state=42`), shared by both tasks.
- Preprocessing quality report and `GET /api/v1/preprocessing/summary`.

## Phase 4 — Statistics & exploratory data analysis ✅
- `backend/analytics/statistics/`:
  - descriptive statistics and G1–G3 distributions;
  - Spearman/Pearson correlations with CIs;
  - assumption-driven group comparisons: Welch's t, Mann–Whitney, ANOVA, Welch's ANOVA,
    Kruskal–Wallis, with Tukey / Games–Howell / Dunn post-hoc tests;
  - chi-square/Fisher with Cramér's V;
  - effect sizes with 95% CIs, and outlier screening.
- Nine research questions. RQ1–RQ6b are confirmatory, Holm-corrected; RQ7–RQ8 are
  exploratory, Benjamini–Hochberg-corrected.
- Zero-grade sensitivity analyses: every G3 = 0 student has 0 absences.
- EDA chart data: univariate, bivariate, heatmap, risk profile and cross-tab.
- `docs/STATISTICAL_FINDINGS.md`, generated from code.
- API: `/statistics/*` and `/eda/charts`.
- Functional Statistical Analysis and EDA pages with reusable, accessible SVG charts.
  Final polish is Phase 8.

## Phase 5 — Machine learning & model evaluation
- Baselines: mean predictor and majority class.
- Regression candidates: Linear (regularised), Decision Tree, Random Forest.
- Classification candidates: Logistic Regression, Decision Tree, Random Forest, KNN
  and SVM. Each is retained only where the evidence supports it.
- Every model is a `Pipeline(build_preprocessor(scenario), estimator)`, run with
  stratified CV on the training split and tuned only where justified. The held-out
  test split is used once.
- Metrics:
  - regression: MAE, MSE, RMSE, R²;
  - classification: accuracy, precision, recall, F1, ROC-AUC, confusion matrix.
- Results reported per cohort and per scenario.
- A sensitivity check on `G3 = 0` rows. Phase 4 found that every such student has 0
  absences, and that this changes the absence–G3 relationship in Mathematics.
- Persisted artifacts with metadata.

## Phase 6 — Interpretability & academic risk analysis
- Permutation importance, partial dependence and per-prediction explanations.
- Risk-factor summaries by student group, with uncertainty communicated.
  Associations only, no causal claims.

## Phase 7 — End-to-end backend integration
- Statistics, model and prediction endpoints, with model loading and input validation.
- Consistent error handling and performance checks.

## Phase 8 — Complete Apple-style frontend
- Statistical Analysis, EDA, Model Comparison, Prediction and Risk Analysis pages.
- A consistent chart system, accessibility and a responsive review.

## Phase 9 — Final validation, documentation & presentation readiness
- End-to-end verification and a reproducibility check from a clean clone.
- Final README and methodology write-up, screenshots, and a limitations and ethics
  section.
- Presentation material.
