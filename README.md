# Student Academic Analytics and Risk Prediction System

An integrated student-analytics system that moves from **statistical understanding**
of student data, through **exploratory analytics** and **reproducible preprocessing**,
to a **comparison of machine-learning models** that predict academic performance and
identify **academic risk** — presented through a modern, interpretable web application.

> **Status: Phase 5 of 9 complete — machine learning and model evaluation.**
> The official UCI dataset is validated and preprocessed without leakage. Statistical
> tests and EDA are shown in the Statistical Analysis and EDA pages. Regression (G3) and
> academic-risk classification models have been trained, tuned with nested
> cross-validation and evaluated for both cohorts and three information scenarios. Their
> results are served by the API and reported in
> [docs/ML_RESULTS.md](docs/ML_RESULTS.md). The model-comparison and prediction pages
> follow in later phases. See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md).

ISPA undergraduate AI / Data Analytics project.

---

## Problem statement

Schools hold rich data on students' backgrounds, habits and grades, but it is rarely
analysed systematically. Struggling students are often identified only after final
results are published, when it is too late to intervene. A system that explains
*which* factors are associated with poor performance — and estimates *who* is at
risk while there is still time to act — can support earlier, better-targeted support.

## Aim

To design and implement a reproducible analytical workflow that:

1. Describes the student population statistically and tests which factors are
   significantly associated with performance.
2. Explores patterns across academic, family, social and behavioural attributes.
3. Prepares the data through documented, leakage-free preprocessing and feature
   engineering.
4. Trains and compares multiple regression and classification models against baselines.
5. Translates model output into interpretable academic-risk insights in a web application.

The contribution is the **integrated workflow and its implementation**, not novelty of
any individual technique.

## Dataset

**UCI Student Performance** (UCI ID 320) — <https://archive.ics.uci.edu/dataset/320/student+performance>,
licensed CC BY 4.0, by P. Cortez and A. M. G. Silva. Two Portuguese secondary-school
cohorts:

| Cohort | File | Students | Attributes |
| ------ | ---- | -------- | ---------- |
| Mathematics | `student-mat.csv` | 395 | 33 |
| Portuguese language | `student-por.csv` | 649 | 33 |

Attributes cover demographics, family background, study time, absences, past
failures, social behaviour and three grades on the 0–20 scale: `G1` (first period),
`G2` (second period) and `G3` (final grade, the performance target). Every attribute
is described in [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

**Validation.** Both official files pass all checks: the documented columns, the
published row counts, no missing values, no duplicate rows, and no values outside the
documented codes or ranges. Some valid values are noted but not removed: 38 Maths and
15 Portuguese students have `G3 = 0`. Some students appear in both cohorts, but there
is no student ID, so matching is approximate (358 one-to-one matches; UCI's join gives
382 pairs). Details and limitations are in [data/README.md](data/README.md).

Data files are not committed. Download and verify them with one command (below).

The dataset contains **no dropout label**. This project therefore predicts final
performance and *academic risk* (risk of failing the final assessment) and does not
claim to predict dropout.

## Research reference

Cortez, P., & Silva, A. M. G. (2008). *Using Data Mining to Predict Secondary School
Student Performance.* In A. Brito & J. Teixeira (Eds.), Proceedings of the 5th Future
Business Technology Conference (FUBUTEC 2008), pp. 5–12. Porto, Portugal: EUROSIS.

## Proposed methodology

```
Student data → Validation → Preprocessing & feature engineering → Statistical
analysis & EDA → Model training → Evaluation & comparison → Interpretable
academic-risk insights → Web application
```

| Stage | Planned content |
| ----- | --------------- |
| Statistical analysis (implemented) | Descriptive statistics; Spearman/Pearson correlations with CIs; assumption-checked tests (Welch's t, Mann–Whitney, ANOVA, Welch's ANOVA, Kruskal–Wallis, chi-square/Fisher) with post-hoc tests; effect sizes with 95% CIs; Holm and Benjamini–Hochberg corrections |
| Exploratory analysis (implemented) | Histograms, bar charts, box plots, scatter plots, correlation heatmap, academic-risk profile, cross-tab, outlier screening |
| Preprocessing (implemented) | Targets, leakage-aware feature scenarios, one-hot/ordinal encoding with fixed categories, two justified engineered features, training-only imputation/scaling, stratified reproducible split |
| Modelling (implemented) | Baselines plus 3 regression and 5 classification models per cohort and scenario; nested cross-validation with bounded grid search; CV-only selection rule; held-out test set scored once |
| Interpretation | Model-agnostic feature importance and per-prediction explanations |

### Target definition and leakage control

Defined before any training — full detail in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

- **Regression target:** `G3`, the final grade (0–20).
- **Classification target:** `at_risk = 1 if G3 < 10`, below the pass mark. This is
  academic risk, not dropout. On the official data, 130 of 395 Mathematics students
  (32.9%) and 100 of 649 Portuguese students (15.4%) are at risk.
- `G3` and `at_risk` are **never** predictors. The code rejects them.
- `G1`/`G2` are only used when the prediction scenario legitimately has them:

  | Scenario | Inputs | Use |
  | -------- | ------ | --- |
  | `full_history` | non-grade attributes + G1 + G2 | late-year prediction |
  | `mid_year` | non-grade attributes + G1 | after the first period |
  | `early` | non-grade attributes only | early warning |

  A `ScenarioGuard` at the start of every preprocessor rejects any feature set that
  doesn't match its scenario. Neither end of the range is "better": `full_history`
  shows how predictable grades are once interim grades exist, and `early` shows what
  is knowable before any grade.

### Statistical analysis (Phase 4)

`backend/analytics/statistics/` answers nine research questions for each cohort.
**All results are associations in observational data; none implies cause.** Effect
sizes are always reported with significance.

Selected findings on the official data (all from
[docs/STATISTICAL_FINDINGS.md](docs/STATISTICAL_FINDINGS.md), which is generated from
code):

- **Past class failures.** These show the clearest non-grade association with lower
  final grades in both cohorts (large effect in Mathematics, d = 0.93; Holm p < .001).
  They are also the strongest categorical correlate of academic risk.
- **Mother's education.** Associated with G3 in both cohorts (small to medium effect).
- **Study time.** Weakly associated with G3 in Portuguese (ρ = 0.27). The association
  is not significant in Mathematics after Holm correction.
- **Interim grades.** G1 and G2 correlate very strongly with G3 (ρ ≈ 0.88–0.96). This
  is why the `early` scenario matters for Phase 5.
- **Zero final grades.** All 38 (Mathematics) and 15 (Portuguese) students with G3 = 0
  have zero recorded absences. Excluding them changes the absences–G3 correlation in
  Mathematics from ρ = 0.02 to −0.24. This is reported as a sensitivity analysis; no
  rows are removed.

Methods are in [docs/METHODOLOGY.md §5](docs/METHODOLOGY.md#5-statistical-analysis-phase-4):
test-selection rules, assumption checks, effect sizes, CIs, multiple-comparison control
and limitations.

### Preprocessing (Phase 3)

`backend/analytics/preprocessing/` turns a validated cohort into an analytical dataset
without removing rows or touching the raw files.

- **Encoding.** Binary categories become a single 0/1 column. Nominal categories (jobs,
  reason, guardian) are fully one-hot encoded. UCI's ordered codes (education, study
  time, ratings) are kept as ordinal integers.
- **Engineered features.** Two are added: `has_past_failures` and `log_absences`.
  Each has a documented reason and leakage assessment.
- **Training-only fitting.** Imputation and scaling are learned only on training data,
  inside a scikit-learn `Pipeline`.
- **Split.** 80/20, stratified on `at_risk`, `random_state=42`: Mathematics 316/79,
  Portuguese 519/130.

Details are in [docs/METHODOLOGY.md §4](docs/METHODOLOGY.md#4-preprocessing-phase-3)
and [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

### Machine learning (Phase 5)

`backend/analytics/ml/` trains every model for each cohort (Mathematics, Portuguese)
and scenario (`early`, `mid_year`, `full_history`):

- **Regression (G3):** mean baseline, linear regression, decision tree, random forest.
- **Classification (`at_risk`):** majority-class baseline, logistic regression,
  decision tree, k-nearest neighbours, SVM (RBF), random forest. Class imbalance is
  handled with `class_weight="balanced"`, with no resampling.
- **Protocol:** each model is a preprocessing + estimator `Pipeline`.
  - Nested cross-validation runs on the training set only: 5 outer folds, with a
    5-fold grid search inside each.
  - A final grid search refits on the full training set.
  - The held-out test set is scored once.
- **Metrics:**
  - regression: MAE, MSE, RMSE, R²;
  - classification: accuracy, balanced accuracy, precision, recall, specificity, F1,
    ROC-AUC (from scores), confusion matrix.
- **Selection:** the CV mean of RMSE (regression) or at-risk F1 (classification),
  using the one-standard-error rule and preferring the simpler model. Test scores
  never influence selection.

What the run shows (numbers in [docs/ML_RESULTS.md](docs/ML_RESULTS.md), generated
from the training run):

- **Baselines.** Every selected model beats its baseline. The majority-class
  baseline's accuracy, which matches the share of passing students, illustrates why
  accuracy is never reported alone.
- **Scenarios.** Performance rises sharply from `early` to `mid_year` to
  `full_history`. This reflects information availability: G1 and G2 are interim grades
  of the same year. It does not mean a "smarter" model.
- **Early scenario.** Without grades, models explain a modest share of G3 variance.
  They detect only part of the at-risk students. They are academic-risk estimates, not
  dropout predictions.
- **Cohorts differ.** The selected models are not the same for Mathematics and
  Portuguese. Both cohorts are reported separately.
- **Errors.** Errors concentrate in students with G3 = 0, who are over-predicted, and
  near the pass mark. A zero-grade sensitivity check is included.

Methods: [docs/METHODOLOGY.md §6](docs/METHODOLOGY.md#6-machine-learning-and-evaluation-phase-5).
Artefacts are regenerated with `python -m analytics.ml.train`
(see [models/README.md](models/README.md)).

## Technology stack

| Layer       | Technology |
| ----------- | ---------- |
| Analytics   | Python 3.12, pandas, NumPy, SciPy, scikit-learn |
| API         | FastAPI, Pydantic, pydantic-settings, Uvicorn |
| Frontend    | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| Quality     | pytest, Ruff, ESLint, Prettier, Vitest, Testing Library |

## Architecture

```
.
├── backend/
│   ├── app/            # FastAPI: config, routes, schemas, services
│   ├── analytics/      # data (Phase 2), preprocessing (Phase 3), statistics (Phase 4), ml (Phase 5)
│   └── tests/
├── frontend/           # Next.js application
├── data/               # raw/ and processed/ (git-ignored contents)
├── models/             # Trained artifacts (git-ignored; regenerated by analytics.ml.train)
├── notebooks/          # Exploration only
├── scripts/            # Developer helpers (check.sh)
├── docs/               # ARCHITECTURE, METHODOLOGY, DATA_DICTIONARY, STATISTICAL_FINDINGS, ML_RESULTS
└── PROJECT_ROADMAP.md
```

- Training is offline and separate from inference; the API only loads saved artifacts.
- `app` depends on `analytics`, never the reverse. The frontend talks only to the API.
- The UI renders only values returned by the API — no placeholder statistics.

Tests live beside the code they cover (`backend/tests`, `frontend/src/**/*.test.tsx`)
so each half of the stack can be checked independently.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Running locally

**Prerequisites:** Python 3.11+ (3.12 recommended), Node.js 20.9+, npm.
[uv](https://docs.astral.sh/uv/) is optional but recommended.

### Backend

```bash
cd backend
uv venv --python 3.12 .venv          # or: python3.12 -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"           # or: pip install -e ".[dev]"
python -m analytics.data.download    # fetch + checksum-verify the UCI dataset (once)
python -m analytics.ml.train         # train, evaluate and persist models (several minutes)
uvicorn app.main:app --reload --port 8000
```

API: <http://localhost:8000/api/v1/health> · Docs: <http://localhost:8000/docs>

| Endpoint (`/api/v1`) | Purpose |
| -------------------- | ------- |
| `GET /dataset/summary?cohort=math` | Dimensions, column types, quality counts, target |
| `GET /dataset/schema?cohort=math` | Data dictionary plus values observed in the cohort |
| `GET /dataset/quality?cohort=math` | Validation checks and observations |
| `GET /dataset/records?cohort=math&page=1&page_size=25&search=teacher` | Paginated records |
| `GET /dataset/overlap` | Approximate cross-cohort matching |
| `GET /preprocessing/summary?cohort=math&scenario=early` | Preprocessing quality report for a cohort and scenario |
| `GET /statistics/hypothesis-tests?cohort=math` | Research questions with tests, adjusted p-values and effect sizes |
| `GET /statistics/group-comparisons?cohort=math&variable=studytime` | Assumption-checked group comparison |
| `GET /statistics/{descriptive,distributions,correlations,associations,outliers}?cohort=math` | Other statistical results |
| `GET /eda/charts?cohort=math` | Chart-ready EDA aggregates |
| `GET /models` | Model definitions, search spaces, run configuration and selected models |
| `GET /models/{regression,classification}?cohort=math` | Model comparison tables (CV and test metrics) |
| `GET /models/scenario-comparison?cohort=math&task=classification` | Early → mid-year → full-history comparison |
| `GET /models/cohort-comparison` | Mathematics vs Portuguese |
| `GET /models/selected?cohort=math&task=regression&scenario=early` | Selected model metadata and error analysis |
| `GET /models/evaluations?cohort=math&task=regression&scenario=early` | Per-fold results and diagnostics |
| `POST /models/predict` | Prediction from a validated feature record |

`cohort` is `math` or `portuguese`. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
for error codes and limits.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: <http://localhost:3000>. The dashboard shows live backend status, and the Data
Explorer (`/data-explorer`) shows the dataset once the API is running.

### Quality checks

```bash
./scripts/check.sh
```

Runs Ruff, pytest, ESLint, TypeScript, Vitest and a production build.

## Roadmap

| Phase | Scope | Status |
| ----- | ----- | ------ |
| 1 | Foundation & architecture | ✅ Complete |
| 2 | Real dataset & Data Explorer | ✅ Complete |
| 3 | Preprocessing & feature engineering | ✅ Complete |
| 4 | Statistics & exploratory data analysis | ✅ Complete |
| 5 | Machine learning & model evaluation | ✅ Complete |
| 6 | Interpretability & academic risk analysis | Planned |
| 7 | End-to-end backend integration | Planned |
| 8 | Complete Apple-style frontend | Planned |
| 9 | Final validation, documentation & presentation readiness | Planned |

## Licence

The **software** in this repository is released under the [MIT License](LICENSE).
The **dataset** is not part of the repository. It is published by UCI under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), which requires attribution
to Cortez & Silva (2008). The MIT licence does not apply to the data.

## Limitations and ethics

Predictions describe statistical associations in one historical dataset from two
Portuguese schools and must not be used to make automated decisions about individual
students. Sensitive attributes (e.g. sex, family circumstances) will be analysed for
association but treated with care in any model intended for intervention support.
