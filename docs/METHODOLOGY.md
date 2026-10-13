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

1. **Data validation** (Phase 2): load both cohorts, verify schema, types, ranges and
   duplicates.
2. **Preprocessing and feature engineering** (Phase 3, §4): targets, feature
   scenarios, encoding, engineered features, train/test split.
3. **Statistics and EDA** (Phase 4, §5):
   - Descriptive statistics: central tendency, dispersion, quartiles, shape.
   - Correlation: Pearson where the relationship is linear and approximately normal,
     Spearman for ordinal or non-normal data.
   - Inference: t-test / ANOVA where normality and equal variances hold, otherwise
     Mann–Whitney U / Kruskal–Wallis; chi-square (or Fisher's exact) for categorical
     associations.
   - Effect sizes (Cohen's d, η², Cramér's V, rank-biserial r) and multiple-comparison
     correction.
   - Univariate, bivariate and multivariate views; outliers; profiling.
4. **Modelling and evaluation** (Phase 5): candidate models compared with
   cross-validation, with tuning only where justified.
5. **Interpretation** (Phase 6): model-agnostic explanation and academic-risk insight.

Associations found in any phase are reported as associations. The data is
observational, cross-sectional and from two schools, so no analysis here supports
causal claims.

## 4. Preprocessing (Phase 3)

Implemented in `backend/analytics/preprocessing/`. The raw files are read, never
written. Every rule below is enforced in code and covered by tests.

### 4.1 Data layers

| Layer | Content |
| ----- | ------- |
| `raw` | The CSV exactly as read (text). Never modified. |
| `validated` | Typed values after the Phase 2 validation. A cohort that fails validation is refused. |
| `analytical` | Validated values + engineered features + targets (`G3`, `at_risk`). 36 columns. |

**No rows are removed.** The official files have no missing, invalid or duplicate
rows. Unusual but valid values are kept:

- `G3 = 0`: 38 Mathematics and 15 Portuguese students. These students are at risk by
  the definition below. Whether they represent a missed final evaluation cannot be
  determined from the data, and is a limitation. A sensitivity check that excludes
  them can be run in Phase 5.
- High absence counts are kept (see `log_absences`, §4.6).

### 4.2 Targets

| Column | Definition | Task |
| ------ | ---------- | ---- |
| `G3` | Final grade, integer 0–20 | Regression |
| `at_risk` | `1 if G3 < 10 else 0` | Binary classification |

10 is the pass mark of the Portuguese 0–20 scale, so `at_risk = 1` means the student
did not reach a passing final grade in the subject. The threshold is fixed in
`analytics/preprocessing/config.py`. On the official data, 130 of 395 Mathematics
students (32.9%) and 100 of 649 Portuguese students (15.4%) are at risk.

**Why `G3`.** `G3` is the final-year grade, the outcome the school records, and the
attribute UCI designates as the output target. `G1` and `G2` are interim grades from
the same year. They measure the same construct earlier, so they are treated as
*prior grades* (time-dependent inputs), never as targets.

### 4.3 Feature scenarios

`G1` and `G2` are strongly related to `G3`. Whether they are legitimate inputs depends
on *when* a prediction is made, so feature sets exist only as named scenarios:

| Scenario | Inputs | Encoded features | Represents |
| -------- | ------ | ---------------- | ---------- |
| `full_history` | non-grade attributes + `G1` + `G2` | 46 | Late-year prediction |
| `mid_year` | non-grade attributes + `G1` | 45 | After the first period |
| `early` | non-grade attributes only | 44 | Early warning, before any grade |

Both ends of the range are useful. They answer different questions, and neither is
better by default:

- `full_history` measures how predictable the final grade is once interim grades exist.
  High accuracy is expected, largely because `G1`/`G2` measure the same construct.
  That reflects the predictability of grades, not insight into causes.
- `early` measures what background, behavioural and school attributes alone can
  indicate. It corresponds to the point where support can still change the outcome.
  Lower accuracy is expected, and that figure is the relevant one for early warning.

The scenario named here (`early`) corresponds to the earlier documents' "C", and
`full_history` to "A". `mid_year` mirrors the intermediate setting of Cortez & Silva
(2008).

### 4.4 Leakage prevention

| Risk | Protection |
| ---- | ---------- |
| Outcome used as a predictor | `G3` and `at_risk` are in `TARGET_COLUMNS`; `feature_columns()` and `assert_no_leakage()` reject them for every scenario. |
| Interim grades used too early | `assert_no_leakage()` rejects `G1`/`G2` outside the scenarios that allow them. |
| Scenarios mixed by accident | `AnalyticalDataset.features(scenario)` returns a `FeatureMatrix` tagged with its scenario. Every preprocessor starts with a `ScenarioGuard`, which raises unless the input columns are exactly that scenario's feature set. Nothing is dropped silently. |
| Test data influencing preprocessing | Imputation and scaling statistics are learned in `fit` only. `build_preprocessor()` returns an unfitted `Pipeline`, intended to be combined with an estimator and fitted on the training split or CV folds. A test checks the scaler's means equal the training means. |
| Engineered features using outcomes | Engineered features are row-wise and stateless, and use only `failures` and `absences`. |
| Same student in train and test | Cohorts are modelled separately. No combined-cohort dataset is produced. |

### 4.5 Encoding

| Group | Columns | Encoding | Reason |
| ----- | ------- | -------- | ------ |
| Binary categorical | `school, sex, address, famsize, Pstatus, schoolsup, famsup, paid, activities, nursery, higher, internet, romantic` | One-hot, first documented category dropped. One 0/1 column each; yes/no fields keep `yes` (e.g. `higher_yes`). | Two levels need one indicator. |
| Nominal | `Mjob, Fjob, reason, guardian` | Full one-hot (17 columns). | No order exists, so none is invented. |
| Ordinal codes | `Medu, Fedu, traveltime, studytime, famrel, freetime, goout, Dalc, Walc, health` | Kept as documented integer codes; standardised when scaling is on. | UCI defines the order. Treating adjacent codes as equally spaced is an **assumption** (e.g. "5–10 h" vs "2–5 h" study time). Tree models only use the order. |
| Numeric | `age, failures, log_absences`, plus `G1`/`G2` where allowed | Numeric; standardised when scaling is on. | |
| Indicator | `has_past_failures` | Passed through (0/1). | |

- **Fixed categories.** They come from the data dictionary, not from the data, so both
  cohorts and every split produce identical columns. An undocumented category raises
  an error rather than being ignored.
- **Scaling.** Use `scale_numeric=True` for linear, distance and kernel models, and
  `False` for tree models.
- **Linear models.** Full one-hot for nominal variables is collinear with an intercept,
  so linear models should be regularised. Phase 5 will document the choice.

### 4.6 Engineered features

Only two features are added. Each one is justified by the observed data:

| Feature | Definition | Why | Leakage |
| ------- | ---------- | --- | ------- |
| `has_past_failures` | `failures > 0` | 79% (Mathematics) and 85% (Portuguese) of students have no past failures, so any-versus-none is the best-populated contrast. The count is kept too. | Past failures precede the year. |
| `log_absences` | `ln(1 + absences)`, replaces `absences` | Strong right skew (sample skewness 3.7 / 2.0; maxima 75 / 32). Reduces the leverage of extreme counts without removing them. | No grade used. **Caveat:** UCI does not state the period over which absences were counted. If they span the whole year, they are only partly known in the `early` scenario. |

Candidates that were considered and rejected, with reasons, are listed in
`docs/DATA_DICTIONARY.md`: grade trend, parental maximum education, study-time
regrouping, support count and an alcohol composite.

### 4.7 Missing values and outliers

- **Missing values.** The official files have none. As a safety net for later inference
  on user input, the pipeline imputes the training-set median (numeric, ordinal) or
  most frequent value (categorical). It never drops rows.
- **Outliers.** These are reported, not removed, using the Tukey 1.5·IQR rule on `age`,
  `absences`, `G1`, `G2` and `G3`. Counts for Mathematics:

  | Column | Outliers |
  | ------ | -------- |
  | `age` | 1 |
  | `absences` | 15 |
  | `G1` | 0 |
  | `G2` | 13 |
  | `G3` | 0 |

  `failures` is excluded, because its quartiles are all 0 and every non-zero value
  would be flagged. Values within the documented range are treated as genuine.

### 4.8 Train/test split and reproducibility

- **Split.** 80/20 within each cohort, stratified on `at_risk`, with `random_state = 42`
  (`config.py`). This gives Mathematics 316 / 79 and Portuguese 519 / 130 students.
  The at-risk share is preserved in both sets: 32.9% and 15.4%.
- **One split, both tasks.** The same split serves regression and classification, and
  is identical across scenarios. Results for a cohort are therefore compared on the
  same students.
- **Reproducibility.** Data is pinned by checksum, the seed and test size are fixed in
  code, categories are fixed by the dictionary, and every transformation is
  deterministic. Tests assert that splits are identical across runs.

### 4.9 Terminology

The dataset has **no dropout label**. The system predicts *academic performance* and
*academic risk* (risk of failing the final assessment). It must not be described as
dropout prediction unless a dataset with a genuine dropout outcome is added.

Dropout is not claimed because the data records only enrolled students' attributes
and grades. Nothing indicates whether a student later left school. A low or zero
`G3` is a performance outcome, and treating it as dropout would be an unsupported
inference.

## 5. Statistical analysis (Phase 4)

Implemented in `backend/analytics/statistics/`. Results for the official data are in
[STATISTICAL_FINDINGS.md](STATISTICAL_FINDINGS.md). That document is generated from
code, and a test fails if it goes stale.

### 5.1 Scope and data

- **Data.** Every analysis uses the Phase 3 analytical frame: validated values plus
  `at_risk`. All students are included, **including those with `G3 = 0`**.
- **Cohorts.** Mathematics and Portuguese are analysed separately. This keeps
  observations independent, because some students appear in both files.
- **No model training.** Nothing in this phase changes the data.

### 5.2 Research questions

Seven tests (RQ1–RQ6b) were fixed in advance as the **confirmatory family**. Two
further questions (RQ7, RQ8) are **exploratory**.

| RQ | Question | Pre-specified primary analysis |
| -- | -------- | ------------------------------ |
| RQ1 | Is weekly study time associated with G3? | Spearman ρ (study time is a 4-level ordinal code) |
| RQ2 | Do students with past failures perform differently? | Two-group comparison: no failures vs 1 or more |
| RQ3 | Are absences associated with G3? | Spearman ρ (skewed count) |
| RQ4 | Do grades differ between female and male students? | Two-group comparison |
| RQ5 | Is mother's education associated with G3? | Four-group comparison (levels 0–1 merged), with post-hoc tests |
| RQ6a | Is school support associated with G3? | Two-group comparison |
| RQ6b | Is family support associated with G3? | Two-group comparison |
| RQ7 | Which numeric variables relate most strongly to G3? | Exploratory ranking of Spearman ρ |
| RQ8 | Which categorical variables are associated with academic risk? | Exploratory chi-square tests with Cramér's V |

Hypotheses are two-sided. For example, RQ1 tests H0: ρ = 0 against H1: ρ ≠ 0.
"Two-group comparison" means the test is chosen by the rule in §5.3.

### 5.3 Test selection and assumption checks

The same rule applies to every group comparison, and it is fixed in code
(`comparisons.py`).

1. **Normality, per group.** A group is adequate for a mean-based test if Shapiro–Wilk
   does not reject normality. It is also adequate if n ≥ 30 and |skewness| ≤ 1, because
   the sampling distribution of the mean is then approximately normal (central limit
   theorem).
   - Shapiro–Wilk alone is not used as a gate. With hundreds of students it rejects
     trivial departures.
2. **Variance homogeneity.** Levene's test, median-centred (Brown–Forsythe), which is
   robust to non-normality.
3. **Choice of test:**

   | Groups | All adequate? | Variances | Test | Effect size | Post-hoc (if omnibus p < α) |
   | ------ | ------------- | --------- | ---- | ----------- | --------------------------- |
   | 2 | yes | any | Welch's t-test | Cohen's d with 95% CI; mean difference with 95% CI | — |
   | 2 | no | — | Mann–Whitney U | rank-biserial r | — |
   | 3+ | yes | equal | One-way ANOVA | η², ω² | Tukey HSD |
   | 3+ | yes | unequal | Welch's ANOVA | η², ω² | Games–Howell |
   | 3+ | no | — | Kruskal–Wallis H | η²_H | Dunn's test, Holm-adjusted |

   Welch's t-test is used rather than Student's t-test because it loses almost nothing
   when variances are equal and stays valid when they are not.
4. **Group sizes.** Groups below n = 10 are flagged as imprecise.
   - Mother's and father's education level 0 is merged with level 1, because very few
     students have level 0 (e.g. 3 mothers in Mathematics).
   - Absences are binned into 0 / 1–5 / 6–10 / 11–20 / 21+ for description only. The
     primary absence analysis uses the raw count.
5. **Independence.** Each row is a different student within one cohort.

### 5.4 Correlation

- **Spearman** is used when either variable is an ordinal code or a bounded count, or
  when normality of either variable is rejected.
- **Pearson** is used only when both variables are interval-scaled and normality is not
  rejected. In practice every key pair uses Spearman, because grades and counts are
  non-normal.
- Pearson's r is always reported alongside, for comparison.
- **Interval.** The 95% CI uses Fisher's z: standard error 1/√(n − 3) for Pearson, and
  the Bonett–Wright (2000) standard error for Spearman.
- **Matrix.** A Spearman matrix covers 16 numeric variables, with Benjamini–Hochberg
  adjustment across all pairs.

### 5.5 Categorical association

- **Test.** Pearson's chi-square test of independence between each categorical
  variable and `at_risk`, without Yates' correction.
- **Sparse tables.** For a 2×2 table with an expected count below 5, Fisher's exact test
  is used. Larger tables with more than 20% of expected counts below 5 are flagged.
- **Effect size.** Cramér's V, interpreted against Cohen's w benchmarks divided by
  √(min(r, c) − 1).
- **Output.** Contingency counts and the at-risk share per category, each with a Wilson
  95% CI, are returned with every test.

### 5.6 Significance, confidence intervals and effect sizes

- **Significance threshold.** α = 0.05, two-sided.
- **Confidence intervals.** 95%, using these methods:
  - means: t interval;
  - proportions: Wilson score interval;
  - correlations: Fisher z;
  - Cohen's d: normal approximation (Hedges & Olkin);
  - mean differences: Welch interval.
- **CIs are not adjusted for multiplicity.**
- **Effect sizes** are always reported and labelled with Cohen's conventional benchmarks:
  - r and ρ: 0.1 / 0.3 / 0.5;
  - d: 0.2 / 0.5 / 0.8;
  - η²: 0.01 / 0.06 / 0.14.

  These labels are rough guides, not judgements of practical importance. A result is
  never described as important because p < 0.05.

### 5.7 Multiple comparisons

| Family | Correction | Purpose |
| ------ | ---------- | ------- |
| Confirmatory: RQ1–RQ6b, 7 tests per cohort | Holm–Bonferroni | Controls the family-wise error rate; supports conclusions |
| Key correlations with G3: 6 pairs | Holm–Bonferroni | |
| Correlation matrix, association tests, RQ7, RQ8 | Benjamini–Hochberg | Controls the false discovery rate; exploratory |
| Post-hoc pairs | Tukey HSD / Games–Howell (built-in), Dunn + Holm | Within each omnibus test |

- Interactive group comparisons on the Statistical Analysis page are exploratory and
  are labelled as unadjusted.
- Only the confirmatory family should be cited as answering a research question.

### 5.8 Zero final grades: sensitivity

`G3 = 0` rows are kept in every primary analysis, as decided in Phase 3.

- **What the data shows.** In both cohorts, **every** student with `G3 = 0` has 0
  recorded absences. Among students with `G3 > 0` the figure is 21.6% (Mathematics)
  and 36.1% (Portuguese). This suggests that some zero grades may reflect a missed final
  evaluation rather than low attainment. The data cannot confirm this.
- **Sensitivity analyses.** Every confirmatory analysis, and every key correlation, is
  therefore also reported without these students. These re-runs are labelled
  exploratory, with unadjusted p-values.
- **Where it matters.** The absence–G3 relationship in Mathematics changes materially
  without zero grades (see the findings document). This is an input for Phase 5.

### 5.9 Outliers

- **Method.** Tukey fences (Q1 − 1.5·IQR, Q3 + 1.5·IQR) and |z| > 3, applied to age,
  absences, G1, G2 and G3.
- **Excluded.** `failures` (zero-inflated) and the bounded ordinal codes.
- **Reported:** fences, counts below and above, the share flagged, and the flagged
  values.
- **Nothing is removed.** Every value passed validation against the documented range,
  so an outlier here is an unusual student, not an error.

### 5.10 Exploratory data analysis

`eda.py` returns chart-ready aggregates. No raw records are sent.

- **Univariate:** histograms of G1/G2/G3 (integer bins 0–20) and absences (bins of 5);
  category counts.
- **Bivariate:** box plots of G3 by group (whiskers at 1.5·IQR, mean marked); scatter
  plots of G1, G2 and absences against G3, with identical points aggregated.
- **Multivariate:**
  - Spearman heatmap;
  - academic-risk profile: means or % yes for at-risk vs not-at-risk students, with
    Cohen's d;
  - mean G3 by study time × past failures, with cell sizes.

Charts use a validated colour palette that is safe for colour-vision deficiency. They
carry no 3D or decorative effects, and each has a "Show data" table, so no value
depends on colour alone.

### 5.11 Language and limitations

- **Association only.** Results are associations in observational, cross-sectional data
  from two Portuguese schools in one school year. Their wording follows the pattern
  "X is associated with G3", never "X causes" or "X predicts failure". A test checks
  generated text for causal phrasing.
- **Confounding and reverse direction are plausible.** For example, school support is
  associated with *lower* grades, most likely because support is given to students who
  are already struggling.
- **Self-reported and coarse measures.** Study time, alcohol use and similar variables
  are questionnaire codes.
- **Sample sizes differ by cohort.** Mathematics (n = 395) has less power than
  Portuguese (n = 649), so a non-significant result is not evidence of no relationship.
- **Statistics are not prediction.** Phase 5 models are evaluated separately, on
  held-out data.

## 6. Machine learning and evaluation (Phase 5)

Code: `backend/analytics/ml/`. Results: [`ML_RESULTS.md`](ML_RESULTS.md), generated from
the training run. Every number there comes from code; none is typed by hand.

### 6.1 Tasks and targets

| Task | Target | Models |
| --- | --- | --- |
| Regression | `G3`, the final grade (0–20) | mean baseline, linear regression, decision tree, random forest |
| Classification | `at_risk` = 1 when G3 < 10 | majority-class baseline, logistic regression, decision tree, k-nearest neighbours, SVM (RBF kernel), random forest |

`at_risk` is **academic risk**: the risk of a final grade below the pass mark. It is
not dropout. The dataset contains no dropout outcome, and no model here predicts one.

Cohorts are modelled separately. Mathematics and Portuguese are different subjects
with different grade and risk distributions (32.9% versus 15.4% at risk). There is no
student identifier to merge them safely (§2).

### 6.2 Scenarios

Every model is trained and evaluated under each scenario of §4.3. Each scenario sees
only its own columns, and `ScenarioGuard` rejects any other input:

| Scenario | Inputs | When it would be available |
| --- | --- | --- |
| `early` | non-grade attributes only | before any grade of the year |
| `mid_year` | + G1 | after the first grading period |
| `full_history` | + G1 + G2 | after the second grading period |

The comparison measures **information availability**. Phase 4 found that G1 and G2
correlate with G3 at ρ ≈ 0.88–0.96. A full-history model therefore mostly repeats
interim grades, and its higher scores do not make it a "smarter" model. The early
scenario is the realistic figure for early support. It still predicts academic risk,
not dropout.

### 6.3 Data splitting and cross-validation

1. **Test split.** The training set (80%) and the held-out test set (20%) are the
   Phase 3 split: stratified on `at_risk` with seed 42 (§4.8). Both tasks use the same
   students. The test set is scored once per model, after training is complete.
2. **Nested cross-validation on the training set.**
   - **Outer loop:** 5 folds. Regression uses `KFold`; classification uses
     `StratifiedKFold` on `at_risk`. Both are shuffled with seed 42.
   - **Inner loop:** in each outer training portion, `GridSearchCV` (5 inner folds, same
     splitter type) chooses hyperparameters.
   - **Scoring:** the tuned pipeline is scored on the outer validation fold.

   The reported CV mean ± SD therefore estimates the whole procedure, tuning included,
   without the optimism of reporting the best grid score.
3. **Final model.** `GridSearchCV` is run once more on the full training set, and the
   best configuration is refitted on all training students.

**Why 5 folds.** Each validation fold stays usable: about 63 students (≈ 21 at risk)
in Mathematics and about 104 (≈ 16 at risk) in Portuguese. With 10 folds, per-fold F1
and ROC-AUC for the minority class would rest on about 8–10 at-risk students.

**No preprocessing outside the pipeline.** Imputers, one-hot encoders and scalers are
the first step of every model `Pipeline`. They are fitted inside each outer fold, each
inner fold and the final fit, on exactly the rows being fitted. Engineered features
are stateless row-wise functions (§4.6). Tests check that a fold's fitted scaler means
equal that fold's training rows, and that altering the test set changes neither CV
scores nor chosen hyperparameters.

### 6.4 Hyperparameter search

Search is bounded and uses grids only (`analytics/ml/registry.py`). Linear regression
is fitted without tuning.

| Model | Grid |
| --- | --- |
| Decision tree (both tasks) | `max_depth` {3, 5, 8, None} × `min_samples_split` {2, 10, 20} × `min_samples_leaf` {1, 5, 10} (36) |
| Random forest (both tasks) | `n_estimators` {100, 300} × `max_depth` {None, 8} × `min_samples_split` {2, 10} × `min_samples_leaf` {1, 4} × `max_features` {1.0 or "sqrt", 0.33} (32) |
| Logistic regression | `C` {0.01, 0.1, 1, 10} (4) |
| k-nearest neighbours | `n_neighbors` {5, 11, 21, 31} × `weights` {uniform, distance} (8) |
| SVM (RBF) | `C` {0.1, 1, 10} × `gamma` {scale, 0.01} (6) |

Tuning metrics:
- **Regression:** RMSE.
- **Classification:** F1 for the at-risk class.

The test set is never involved.

### 6.5 Class imbalance

Risk counts and percentages are reported per cohort for all students, the training
set and the test set (`ML_RESULTS.md`):
- **Imbalance handling:** every classifier that supports it uses
  `class_weight="balanced"`.
- **k-NN:** it has no class weights. Its lower recall is reported as measured, not
  hidden.
- **No resampling:** there is no oversampling or SMOTE. Class weights are simpler for
  datasets of this size and avoid synthetic students. If resampling were ever
  added, it would belong inside the pipeline after the split.

### 6.6 Metrics

Regression metrics:
- **MAE:** mean absolute error, in grade points.
- **MSE:** mean squared error.
- **RMSE:** root mean squared error, in grade points.
- **R²:** proportion of variance explained.

Classification uses at risk as the positive class:

| Metric | Meaning here |
| --- | --- |
| Recall (sensitivity) | share of at-risk students who are flagged |
| Precision | share of flagged students who are actually at risk |
| Specificity | share of passing students not flagged |
| F1 | harmonic mean of precision and recall |
| Balanced accuracy | mean of recall and specificity |
| ROC-AUC | ranking quality of the continuous score, over all thresholds |
| Accuracy | reported, but never on its own (see baselines) |

ROC-AUC uses `predict_proba` where available and the SVM's `decision_function`
otherwise. It is **never computed from hard labels**.

Undefined values are `None`, never NaN:
- **ROC-AUC:** undefined when evaluated students are all one class.
- **Precision:** undefined when no student is flagged.

Class labels use each estimator's own decision rule: the more probable class, or the
sign of the SVM decision score. The threshold is not tuned.

**The recall–precision trade-off.** Missing an at-risk student (a false negative)
can mean no support is offered. Flagging a student who would pass (a false positive)
costs a follow-up conversation. Recall is therefore watched closely. It is not
maximised on its own, though: a model that flags everyone has recall 1 and is useless.
F1 balances the two, and ROC-AUC shows ranking quality independent of the threshold.
The right operating point depends on the cost of an intervention, which these data do
not provide.

### 6.7 Baselines

- **Regression:** a model that predicts the training mean for every student
  (`DummyRegressor`). Its cross-validated R² is about 0.
- **Classification:** a model that predicts the majority class, "not at risk", for
  every student (`DummyClassifier`):
  - accuracy 67% (Mathematics) or 85% (Portuguese);
  - recall 0, ROC-AUC 0.5, precision undefined.

  This is why accuracy is never reported without the baseline.

### 6.8 Model selection

Selection uses cross-validation only (`analytics/ml/selection.py`):

1. **Primary metric:** the mean over outer folds of RMSE (regression) or at-risk F1
   (classification).
2. **Best model:** the best candidate, with baselines excluded.
3. **One-standard-error rule:** any candidate within one SE (fold SD / √5) of the best
   is treated as performing equivalently.
4. **Choice:** the simplest of these, by complexity rank: linear < tree < k-NN < SVM <
   forest. Simpler models are easier to explain and audit.
5. **Baseline check:** the result records whether the choice beats the baseline.

Test scores are reported for every model but never change the choice. A model is not
chosen because it is popular, or because of a single test number.

### 6.9 Error analysis and diagnostics

Error analysis covers the selected models on the test set:

- **Regression:**
  - residual (actual − predicted) distribution;
  - MAE and mean residual by G3 band, with G3 = 0 isolated;
  - the 10 largest errors, by file row position only.
- **Classification:**
  - the confusion matrix and per-class results;
  - actual grades of false negatives and false positives;
  - how many G3 = 0 students were flagged.

Pattern notes are generated from the numbers, using thresholds fixed in
`analytics/ml/errors.py`.

**Zero-grade sensitivity (exploratory).** Each selected regression model is refitted
without G3 = 0 training students. It is compared with the selected model on the same
test students with G3 > 0. Zero grades stay in every primary result.

**Automated diagnostics.** These flag results for the quality review and never alter
them:
- R² or ROC-AUC ≥ 0.99 (possible leakage);
- a classifier predicting a single class;
- a test score more than 2 fold SDs from its CV mean;
- a model that does not beat its baseline.

### 6.10 Persistence and reproducibility

`python -m analytics.ml.train` reproduces everything. It verifies the dataset
checksums, then trains both cohorts. It writes:
- `models/ml_results.json`, with every model's folds, parameters and test scores;
- one fitted pipeline plus a JSON metadata file for each of the **12 selected models**;
- `docs/ML_RESULTS.md`.

Metadata includes:
- the cohort, task, scenario and model;
- the input and encoded feature names and the target;
- the threshold and score type;
- hyperparameters and the search space;
- the seed, CV strategy, sample sizes, and CV and test metrics;
- software versions, the dataset SHA-256, the artefact SHA-256 and a timestamp.

Pipelines are stored with `joblib`. Loading checks the SHA-256 and refuses an artefact
built with a different scikit-learn version. Model artefacts are git-ignored like the
data; the committed report records what they contained.

### 6.11 Prediction service

`analytics/ml/predict.py` accepts one feature record using the UCI attribute codes and
validates it against the data dictionary:
- G3 and `at_risk` are rejected as leakage;
- G1/G2 are rejected outside the scenarios that allow them.

It derives the engineered features and applies the persisted pipeline for the chosen
cohort, task and scenario. It returns either:
- a predicted grade, limited to 0–20; or
- an at-risk label with its score and score type.

Every result carries caveats. The API exposes this at `POST /api/v1/models/predict`;
the end-user form belongs to a later phase.

### 6.12 Limitations

- **One test set per cohort:** 79 and 130 students. Test scores are single, noisy
  estimates; nested-CV means and SDs are the stable summary.
- **Observational data:** two schools, one year. Models learn associations, not causes,
  and may not transfer to other schools, years or curricula.
- **Interim grades:** G1 and G2 dominate the mid-year and full-history scenarios.
  Those scenarios are not early warnings.
- **Absence timing:** the period that absences cover is undocumented (§4.6), so even
  the early scenario may contain information recorded during the year.
- **Zero grades:** G3 = 0 probably sometimes means the final evaluation was not taken.
  These students are hard to predict, and they inflate regression error.
- **Untuned threshold:** different recall/precision trade-offs need a threshold chosen
  with the costs of intervention in mind.
- **Linear-regression coefficients:** nominal attributes are fully one-hot encoded, so
  coefficients are not uniquely identified (the minimum-norm solution is used).
  Predictions are unaffected. Interpretation is Phase 6 work.

## 7. Interpretability and academic-risk analysis (Phase 6)

Code:
- `backend/analytics/interpret/` (explanations, importance, sensitivity);
- `backend/analytics/risk/` (profiles, suggestions).

Results: [`INTERPRETABILITY.md`](INTERPRETABILITY.md), generated by
`python -m analytics.interpret.build` from the 12 persisted Phase 5 models. **No model
is retrained.**

The project keeps four kinds of statement apart and never mixes them:

| Kind | Example | What it is not |
| --- | --- | --- |
| Model prediction | "predicted G3 = 9.4" | a fact about the student |
| Model explanation | "past failures raised the model's score by 0.21" | a reason the student has an outcome |
| Statistical association | "52% of students with one past failure were below 10" | a statement about any individual |
| Causal explanation | — | **never made**: the data are observational |

### 7.1 Unit of explanation: original attributes

Explanations and importances are reported per original UCI attribute (`Mjob`,
`absences`), not per encoded column. One-hot columns (`Mjob_teacher`) and engineered
features map back to their source: `has_past_failures` → `failures` and
`log_absences` → `absences`. When an attribute is perturbed, all of its
encoded and engineered columns change together and are recomputed with the training
code. No explanation evaluates an impossible input such as `failures = 2` with
`has_past_failures = 0`.

### 7.2 SHAP decision

The `shap` package is not installed, and it was not added. Its `TreeExplainer` and
`LinearExplainer` work on the encoded matrix. With them:
- one-hot columns and the engineered pairs (`failures`/`has_past_failures`,
  `absences`/`log_absences`) would be treated as independent players;
- background substitution would create inconsistent inputs;
- the selected SVM would need a separate, much slower kernel method.

Instead, `analytics/interpret/shapley.py` implements **interventional Shapley values by
permutation sampling** (Štrumbelj & Kononenko, 2014). This is the algorithm behind
`shap.PermutationExplainer`, with original attributes as players:

- one method for all five selected model types, so explanations are comparable across
  models;
- each sample walks from a background training student to the record in a random
  attribute order. It is exactly additive: base value + Σ contributions = model
  output;
- antithetic sampling (each order is also used reversed), a fixed seed (42) and a
  reported standard error for each contribution;
- bounded cost: `n_samples × (attributes + 1)` model evaluations in one batch. That
  is 1,024 samples (about 35,000 rows) for an on-demand explanation, which takes under
  a second for the selected forests, and 128 samples per test student for global
  summaries;
- verified by tests:
  - exact against a closed form for a pure interaction;
  - exact against attribute switching for a linear model;
  - additive and deterministic.

**What is explained:**
- **Regression:** the predicted G3.
- **Probability classifiers:** the model probability of academic risk.
- **SVM:** its decision score, labelled as not a probability.

The background is the cohort's training set (316 or 519 students). The base value is
the mean output over the sampled background students.

### 7.3 Global feature importance

These methods are reported separately, each with its own unit and limitations. Their
values are never compared with each other.

| Method | Models | Data | Unit |
| --- | --- | --- | --- |
| Permutation importance | all | held-out test set, 30 shuffles per attribute | increase in RMSE / decrease in ROC-AUC |
| Permutation importance, G3 > 0 only | regression | test students with G3 > 0 | increase in RMSE |
| Mean absolute Shapley value | all | every test student (labels not used), 128 samples each | output scale |
| Impurity-based importance | tree, forest | training data (from fitting) | share of impurity decrease |
| Model coefficients | linear, logistic | training data (from fitting) | per SD, or vs reference category |

- **Permutation importance on the test set** is an *evaluation-time diagnostic*. The
  test labels are scored but never used to fit or tune anything. Attributes that
  carry overlapping information (G1/G2, failures/higher) share importance.
- **The G3 > 0 variant** tests one specific concern. Every G3 = 0 student has 0
  recorded absences, so a model can use "0 absences" to predict a grade of 0.
- **Impurity importance** is biased towards attributes with many distinct values.
- **Coefficients** are conditional on all other inputs.
  - Linear-regression coefficients for fully one-hot nominal attributes are only
    identified relative to each other.
  - Logistic coefficients are on the log-odds scale and shrunk by L2 regularisation.

### 7.4 Probability interpretation and risk categories

The binary academic-risk label is unchanged: `at_risk = G3 < 10`.

- **Probabilities are reported only where the model outputs them:** logistic
  regression, decision tree and random forest. The SVM reports a decision score. A
  regression model never reports a probability.
- **Probabilities are not calibrated.** The selected classifiers were trained with
  balanced class weights. `INTERPRETABILITY.md` reports test-set calibration: mean
  predicted vs observed rate, Brier score and binned rates. In every case the mean
  predicted probability exceeds the observed at-risk rate. Probabilities are
  therefore presented as a way to order students, never as the chance that a student
  will fail.
- **No low/moderate/high categories are introduced.** There are no validated
  educational thresholds for them, and inventing cut-offs would present arbitrary
  numbers as standards. A classification result gives two things instead:
  - the model's own flag, from its decision rule (§6.6);
  - the score's percentile among training students, which is context, not a
    category.

### 7.5 Individual explanations

`POST /api/v1/interpretability/explain` returns:
- the prediction, with cohort, task, scenario and selected model;
- the largest contributions (default 10, at most 33), plus the sum of the rest;
- each contribution with its standard error and a raises/lowers/negligible direction,
  where negligible means within 2 SE of 0;
- the base value, the method, the background and the limitations.

Inputs are validated exactly as for prediction (§6.11):
- G3 and `at_risk` are rejected;
- G1/G2 are rejected outside their scenarios;
- undocumented values are rejected.

### 7.6 Sensitivity analysis

**Single-attribute sensitivity (`/interpretability/sensitivity`)** varies one attribute
over its documented values while every other input stays as entered:
- **Allowed attributes:** only school-related behaviours and support: study time,
  absences, going out, free time, travel time, activities, paid classes, family and
  school support, internet. Demographic and family-background attributes are
  excluded.
- **Absences:** use a fixed grid (0–30), capped at the cohort's training maximum.
- **Support:** each value reports how many training students have it. Values with
  fewer than 10 are marked sparse.
- **Zero-grade note:** absence curves carry a data-generated note about the G3 = 0 /
  0-absence pattern.

**Scenario sensitivity (`/interpretability/scenario-sensitivity`)** predicts the same
record under each scenario its grades allow.

These are model sensitivity experiments, not causal interventions. They show how a
model responds, not what would happen if a student changed something.

### 7.7 Group-level risk profiles

`analytics/risk/profiles.py` reports observed at-risk proportions for groups that are
pre-defined from school-related attributes:
- past failures, study time, absence band, school and family support, paid classes,
  plans for higher education, internet access;
- three two-way tables: any past failures × study time, absences and school support.

Each group gives n, the at-risk count, the percentage and a 95% Wilson interval. A
group is marked reliable when n ≥ 10. Each attribute also gets a chi-square or Fisher
test with Cramér's V, Benjamini–Hochberg-adjusted across the eight attributes.

Demographic attributes (sex, age, address, parents' jobs and education) are **not**
profiled here, so that no demographic group is labelled "high-risk". Their
associations remain in the Phase 4 statistics. No clustering is used: pre-defined,
interpretable groups answer the question without arbitrary clusters.

### 7.8 Suggestions for human review

`analytics/risk/suggestions.py` holds three rules:
- past failures → discuss earlier difficulties with an adviser;
- study time below 2 hours → review study routines;
- more than 10 absences → look at attendance patterns together.

A model flag adds a fourth suggestion: a supportive check-in and a consideration of
learning support.

- **Evidence requirement:** a rule is shown only if this cohort's data support it. The
  triggering group must have a higher observed at-risk proportion than the rest
  (Fisher's exact test, unadjusted p < 0.05, exploratory). Otherwise it is returned
  under `not_shown` with the evidence. The model-flag suggestion cites the model's
  held-out recall and precision.
- **Wording, checked by tests:**
  - addressed to a teacher or adviser and phrased as something to consider;
  - never punitive or disciplinary;
  - never a clinical, psychological or family judgement;
  - never a claim that changing an attribute will change a grade.
- **Excluded inputs:** demographic and family-background attributes never trigger a
  rule.
- **Disclaimer:** every response carries it.

`POST /api/v1/risk/insights` returns (A) the individual model explanation, (B) group
findings for the record's values, and (C) suggestions, as separate fields with a
reading note.

### 7.9 Limitations

- **Behaviour, not causes:** explanations and importances describe the selected models'
  behaviour on one dataset. A different, equally accurate model could rely on
  different attributes.
- **Atypical combinations:** interventional Shapley values and permutation importance
  break correlations between attributes. They can evaluate unusual combinations of
  inputs.
- **Small test sets:** with 79 and 130 students, permutation importances and
  calibration are noisy.
- **Observational groups:** group profiles describe observed students. Selection
  effects (for example, school support given to struggling students) and confounding
  are not removed.
- **Untested suggestions:** they are general prompts. They were not validated as
  interventions, and their evidence check is exploratory and unadjusted.
- **G3 = 0:** probably sometimes means the final evaluation was not taken. The G3 > 0
  permutation check shows that much of the Mathematics regression models' reliance on
  absences comes from these students. Without them, the early model shows no
  measurable reliance on absences, and the importance roughly halves for the mid-year
  and full-history models.

## 8. Integration and consistency (Phase 7)

The integrated backend computes nothing new. It guarantees that every endpoint reports
the same quantities in the same way:

- **One analytical dataset per cohort version.** Statistics, EDA, preprocessing
  reports, risk profiles, explanations and the dashboard all read the same prepared
  dataset. Tests check that the observed at-risk count is identical across
  `/dashboard/summary`, `/risk/profiles`, `/preprocessing/summary` and
  `/statistics/distributions` (130 of 395 in Mathematics, 100 of 649 in Portuguese).
- **Observed versus predicted.** The dashboard labels historical proportions
  `observed_historical`. These are students whose G3 was below 10, not future risk.
  Model scores are labelled `model_evaluation`. Predictions and probabilities appear
  only in prediction and explanation responses, where the probability caveats of §7.4
  apply.
- **Model metrics are read, never recomputed.** Dashboard and pipeline figures come
  from the recorded training run, and tests check that they equal
  `/models/{regression,classification}`.
- **No substitution.** An unsupported cohort, scenario, task or model is rejected with
  an explicit error. Each scenario's model only ever receives that scenario's inputs.
- **Importance ranking correction.** Permutation and mean |Shapley| importance are now
  ranked by value. Phase 6 had ranked them by absolute value, which could place a small
  negative permutation value (no measurable reliance) near the top. The values were
  unchanged; the ranking and the generated report were rebuilt without retraining.
