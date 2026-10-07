# Methodology

This document fixes the analytical decisions that must hold before any result is
reported. It will be extended phase by phase; nothing here is a result.

## 1. Research basis

Cortez, P., & Silva, A. M. G. (2008). *Using Data Mining to Predict Secondary School
Student Performance.* FUBUTEC 2008, pp. 5–12.

The paper applied data-mining models (Decision Trees, Random Forests, Neural Networks,
SVMs) to the same dataset under three input configurations: with both period grades
(G1, G2), with G1 only, and with no prior grades. It showed that prior grades dominate
predictive performance.

This project does **not** claim methodological novelty for any individual technique.
Its contribution is an integrated, reproducible workflow — statistics → EDA →
preprocessing → model comparison → interpretable risk insights — delivered as a
working system.

## 2. Data validation strategy

Implemented in Phase 2 (`backend/analytics/data/`). Every cohort file is checked
against the data dictionary, which follows UCI's `student.txt` notes:

| Check | Rule | Severity if broken |
| ----- | ---- | ------------------ |
| Columns | Exactly the 33 documented columns | fail (missing/extra), warning (order) |
| Shape | Row count equals the published file (395 / 649) | warning |
| Missing values | No empty cells | fail |
| Duplicates | No row identical to another across all 33 attributes | warning (rows kept: without an ID they may be distinct students) |
| Yes/no fields | Only `yes` / `no` | fail |
| Category codes | Only documented codes (e.g. `Mjob` ∈ teacher, health, services, at_home, other) | fail |
| Grades | `G1`, `G2`, `G3` integers in 0–20 | fail |
| Coded scales | `Medu`/`Fedu` 0–4, `traveltime`/`studytime` 1–4, ratings 1–5 | fail |
| Counts | `age` 15–22, `failures` 0–4, `absences` 0–93, integers only | fail |

Integrity is also checked before loading: each CSV must match a pinned SHA-256.

Validation reports and never deletes. Outliers that are within the documented range,
such as high absence counts or `G3 = 0`, are valid data. They are kept and, where
relevant, reported as observations. Both official files pass every check.

## 3. Pipeline

1. **Data validation** — load both cohorts, verify schema, types, ranges and duplicates.
2. **Descriptive statistics** — central tendency, dispersion, quartiles, distribution shape.
3. **Relationship analysis** — Pearson (linear, approximately normal) or Spearman
   (ordinal / non-normal) correlations with significance tests.
4. **Inferential statistics** — t-test / ANOVA where assumptions hold (normality,
   homogeneity of variance checked first); Mann–Whitney U / Kruskal–Wallis otherwise;
   chi-square (or Fisher's exact) for categorical associations. Effect sizes reported
   (Cohen's d, η², Cramér's V, rank-biserial r). Multiple-comparison correction applied
   where many tests are run.
5. **EDA** — univariate, bivariate and multivariate views; outlier analysis; profiling.
6. **Preprocessing** — encoding, scaling and feature engineering fitted on training
   folds only (scikit-learn `Pipeline`) to avoid train/test contamination.
7. **Modelling** — compare candidate models with cross-validation; tune where justified.
8. **Evaluation & interpretation** — held-out metrics, then model-agnostic explanation.

## 4. Target definition and leakage rules

These rules are binding for every prediction experiment.

### 4.1 Targets

| Task           | Target                                                       |
| -------------- | ------------------------------------------------------------ |
| Regression     | `G3` — final grade (0–20)                                    |
| Classification | `at_risk = 1 if G3 < 10 else 0` (below the Portuguese pass mark of 10/20) |

The exact threshold is a documented design choice and will be revisited in Phase 5
after inspecting the grade distribution.

**Why `G3`.** `G3` is the final-year grade, the outcome the school actually records,
and the attribute UCI designates as the output target. `G1` and `G2` are interim
grades from the same year: they measure the same construct earlier, so they are
treated as *prior grades* (time-dependent inputs), never as targets.

### 4.2 Leakage rules

- `G3` (and anything derived from it) is **never** an input feature for a model whose
  target is `G3` or `at_risk`.
- `G1` and `G2` are only legitimate inputs when the prediction is made *after* those
  periods. Every experiment is therefore run under explicitly named scenarios:

  | Scenario | Inputs                         | Represents                         |
  | -------- | ------------------------------ | ---------------------------------- |
  | **A**    | all non-grade attributes + G1 + G2 | late-year prediction            |
  | **B**    | all non-grade attributes + G1      | mid-year prediction             |
  | **C**    | non-grade attributes only          | early-warning, start of year    |

  Scenario C is the most useful for early intervention and the most honest test of
  non-grade factors; results from A will look stronger and must not be presented
  without that context.
- All preprocessing (imputation, scaling, encoding, feature selection) is fitted inside
  cross-validation folds.
- Students appearing in both the Mathematics and Portuguese files are not split across
  train and test sets when cohorts are combined. By default the cohorts are modelled
  separately. Because the data has no student ID, cross-cohort matching uses UCI's
  13-attribute profile and is approximate. On the official files UCI's join produces
  382 pairs, but only 358 profiles are unique in both files (see `data/README.md`).
- Records with `G3 = 0` are investigated before modelling (they may indicate students
  who did not sit the final assessment) and the handling decision is documented.

### 4.3 Terminology

The dataset has **no dropout label**. The system predicts *academic performance* and
*academic risk* (risk of failing the final assessment). It must not be described as
dropout prediction unless a dataset with a genuine dropout outcome is added.

Dropout is not claimed because the data records only enrolled students' attributes
and grades. Nothing indicates whether a student later left school. A low or zero
`G3` is a performance outcome, and treating it as dropout would be an unsupported
inference.

## 5. Evaluation

- Regression: MAE, MSE, RMSE, R².
- Classification: accuracy, precision, recall, F1, ROC-AUC, confusion matrix. Because
  `at_risk` is expected to be imbalanced, recall/F1 for the at-risk class and ROC-AUC
  are prioritised over accuracy, and a majority-class baseline is always reported.
- Stratified k-fold cross-validation with fixed random seeds; a held-out test set is
  touched only once for final reporting.
