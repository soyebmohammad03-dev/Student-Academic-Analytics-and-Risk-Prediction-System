# Project Roadmap

**Student Academic Analytics and Risk Prediction System**

Each phase ends with code review, test verification, a git status check, one
meaningful commit and a push. Phases are never combined into a single commit.

| Phase | Name                               | Status      |
| ----- | ---------------------------------- | ----------- |
| 1     | Project foundation                 | ✅ Complete |
| 2     | Data layer & Data Explorer         | ✅ Complete |
| 3     | Statistical analysis               | Planned     |
| 4     | Exploratory data analysis          | Planned     |
| 5     | Preprocessing & target formulation | Planned     |
| 6     | Modelling & model comparison       | Planned     |
| 7     | Interpretability & risk insights   | Planned     |
| 8     | Polish, documentation & release    | Planned     |

## Phase 1 — Project foundation
Repository structure, documentation, FastAPI skeleton (config, health, project
metadata), Next.js shell with design system and navigation, linting, tests, Git/GitHub.

## Phase 2 — Data layer & Data Explorer ✅
- Scripted, checksum-verified download of the official UCI archive into `data/raw/`.
- Loader and structured validation: columns, shape, types, allowed codes, ranges,
  missing values, duplicates. Both official files pass every check.
- Data dictionary for all 33 attributes (`docs/DATA_DICTIONARY.md`, generated from code).
- Approximate cross-cohort matching, with its assumptions stated.
- API: `/dataset/summary`, `/schema`, `/quality`, `/records` (paginated, searchable), `/overlap`.
- Frontend: Data Explorer with cohort switch, overview, plain-language quality report,
  searchable paginated table, dictionary, and loading, empty and error states.

## Phase 3 — Statistical analysis
- Descriptive statistics for every attribute.
- Normality and variance-homogeneity checks to choose parametric vs non-parametric tests.
- Pearson/Spearman correlations with p-values.
- t-test/Mann–Whitney, ANOVA/Kruskal–Wallis, chi-square/Fisher with effect sizes and
  multiple-comparison correction.
- API + Statistical Analysis page.

## Phase 4 — Exploratory data analysis
- Univariate, bivariate and multivariate views; correlation heatmap; outlier analysis.
- Focus factors: study time, absences, failures, G1/G2/G3, parental education,
  family/school support, demographic and social factors.
- Academic-performance profiling.
- API + EDA page with a restrained, consistent chart system.

## Phase 5 — Preprocessing & target formulation
- Final decision on risk threshold and `G3 = 0` handling, documented in `docs/METHODOLOGY.md`.
- Feature scenarios A / B / C (with G1+G2, G1 only, no grades).
- Reproducible scikit-learn preprocessing pipelines; engineered features.
- Leakage tests asserting that `G3` never appears as an input.

## Phase 6 — Modelling & model comparison
- Baselines (mean predictor, majority class).
- Regression: Linear, Decision Tree, Random Forest.
- Classification: candidates from Logistic Regression, Decision Tree, Random Forest,
  KNN, SVM — retained only where evidence supports them.
- Stratified cross-validation, hyperparameter tuning where justified, held-out test.
- Persisted artifacts with metadata; Model Comparison page.

## Phase 7 — Interpretability & risk insights
- Permutation importance and partial dependence; per-prediction explanations.
- Prediction API with input validation; Prediction and Risk Analysis pages.
- Clear communication of uncertainty and of which scenario a prediction uses.

## Phase 8 — Polish, documentation & release
- Accessibility and responsive review, performance, error states.
- Final README, methodology write-up, screenshots, limitations and ethics section.
- Optional deployment.
