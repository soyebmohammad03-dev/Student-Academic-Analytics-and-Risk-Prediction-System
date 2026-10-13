# Student Academic Analytics and Risk Prediction System

An integrated student-analytics system that moves from **statistical understanding**
of student data, through **exploratory analytics** and **reproducible preprocessing**,
to a **comparison of machine-learning models** that predict academic performance and
identify **academic risk** — presented through a modern, interpretable web application.

> **Status: Phase 8 of 9 complete — interactive analytics frontend.**
> Every page now reads real results from the integrated FastAPI backend: a dashboard
> that separates observed historical data from model evaluation, the Data Explorer,
> statistical analysis, EDA, model comparison, a validated prediction form with
> explanations, interpretability, risk analysis and a methodology page. Cohort and
> scenario selections are shared across pages. Phase 9 (final validation and
> presentation) remains. See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) and the
> [API reference](docs/API.md).

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
| Interpretation (implemented) | Attribute-level Shapley explanations; permutation, Shapley, impurity and coefficient importance; probability calibration; model-sensitivity experiments; group risk profiles; evidence-checked suggestions |

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

### Interpretability and academic-risk analysis (Phase 6)

`backend/analytics/interpret/` and `backend/analytics/risk/` explain the 12 selected
models without retraining them. They keep four kinds of statement apart: model
prediction, model explanation, group-level association, and (never) causal claims.

- **Individual explanations.** Interventional Shapley values estimated by permutation
  sampling over the original attributes. One-hot and engineered columns therefore
  stay consistent, and one method covers forests, trees, linear models and the SVM.
  Explanations are exactly additive, seeded and bounded. The `shap` package was not
  added; [METHODOLOGY §7.2](docs/METHODOLOGY.md#72-shap-decision) explains why.
- **Global importance:**
  - permutation importance on the held-out test set, as an evaluation-time
    diagnostic;
  - mean absolute Shapley values;
  - impurity importance for trees and forests;
  - coefficients for linear models.

  Each is reported on its own scale with its limitations.
- **Probabilities.** These are reported only by models that output them. The selected
  classifiers were trained with class weights, and their probabilities over-predict
  the observed at-risk rate on the test set. They order students but are not
  calibrated chances. No low/moderate/high categories are invented.
- **Sensitivity experiments.** One school-related attribute is varied, with all other
  inputs held fixed. The same record can also be compared across scenarios. These
  show model behaviour, not interventions.
- **Risk profiles.** Observed at-risk shares, with 95% intervals, by past failures,
  study time, absences, support, paid classes, plans for higher education and
  internet. Demographic groups are deliberately not profiled.
- **Suggestions.** Non-punitive prompts for a teacher or adviser. Each is shown only
  when the cohort's data show higher observed risk for the triggering group, and every
  response carries a disclaimer.

Findings from the real data are in
[docs/INTERPRETABILITY.md](docs/INTERPRETABILITY.md), which is generated. For example,
past failures and interim grades dominate the selected models. In Mathematics, much of
the models' reliance on absences comes from the students with G3 = 0, all of whom have
0 recorded absences.

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
│   ├── analytics/      # data, preprocessing, statistics, ml, interpret + risk, pipeline (Phases 2–7)
│   └── tests/
├── frontend/           # Next.js application
├── data/               # raw/ and processed/ (git-ignored contents)
├── models/             # Trained artifacts (git-ignored; regenerated by analytics.ml.train)
├── notebooks/          # Exploration only
├── scripts/            # Developer helpers (check.sh)
├── docs/               # ARCHITECTURE, METHODOLOGY, API, DATA_DICTIONARY, STATISTICAL_FINDINGS, ML_RESULTS, INTERPRETABILITY
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

Setting up the data and models and starting the API are separate steps. The API never
downloads data or trains models; it reports what is missing at `/api/v1/ready`.

**One-time setup**, or whenever artefacts need regenerating:

```bash
cd backend
uv venv --python 3.12 .venv          # or: python3.12 -m venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"           # or: pip install -e ".[dev]"
python -m analytics.data.download    # fetch + checksum-verify the UCI dataset
python -m analytics.ml.train         # train, evaluate and persist models (~8 minutes)
python -m analytics.interpret.build  # global importance + docs/INTERPRETABILITY.md (~1 minute)
```

**Start the API** (normal operation, starts in seconds):

```bash
cd backend && source .venv/bin/activate
uvicorn app.main:app --port 8000     # add --reload while developing
curl -s localhost:8000/api/v1/ready  # "ready", or which component is missing and the fix
```

Optional settings (environment variables, or `backend/.env`; see `.env.example`):
`SAARPS_DATA_DIR`, `SAARPS_MODELS_DIR`, `SAARPS_CORS_ORIGINS`, `SAARPS_LOG_LEVEL`.
`python -m analytics.pipeline --cohort math --scenario early` prints the same
integrated summary offline.

API: <http://localhost:8000/api/v1/health> · OpenAPI docs: <http://localhost:8000/docs> ·
Reference with examples: [docs/API.md](docs/API.md).

| Endpoint (`/api/v1`) | Purpose |
| -------------------- | ------- |
| `GET /ready` | Component readiness: API, dataset, statistics, models, interpretability |
| `GET /dashboard/summary` | Observed cohort facts and selected-model evaluation, kept separate |
| `GET /pipeline/summary?cohort=math&scenario=early` | Every analytical step for one cohort and scenario |
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
| `GET /interpretability/importance?cohort=math&task=classification&scenario=early` | Global importance of the selected model, per method |
| `POST /interpretability/explain` | Prediction with attribute-level Shapley contributions |
| `POST /interpretability/sensitivity` · `/interpretability/scenario-sensitivity` | Model-sensitivity experiments |
| `GET /risk/profiles?cohort=math` | Observed academic risk by student group |
| `POST /risk/suggestions` · `POST /risk/insights` | Evidence-checked suggestions; individual, group and suggestion layers kept separate |

`cohort` is `math` or `portuguese`. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
for error codes and limits.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: <http://localhost:3000>. Start the API first (above); every page reads its
results from it and explains what to run when something is missing.

| Page | Route | Main endpoints |
| ---- | ----- | -------------- |
| Dashboard | `/` | `/dashboard/summary`, `/statistics/hypothesis-tests`, `/pipeline/summary`, `/statistics/distributions` |
| Data Explorer | `/data-explorer` | `/dataset/{summary,quality,schema,records,overlap}` |
| Statistical Analysis | `/statistics` | `/statistics/*` |
| Exploratory Analysis | `/eda` | `/eda/charts` |
| Model Comparison | `/model-comparison` | `/models/{evaluations,selected,scenario-comparison,cohort-comparison}` |
| Prediction | `/prediction` | `/dataset/schema`, `POST /models/predict`, `POST /interpretability/explain`, `POST /risk/insights` |
| Interpretability | `/interpretability` | `/interpretability/importance`, `POST /interpretability/{explain,sensitivity,scenario-sensitivity}` |
| Risk Analysis | `/risk-analysis` | `/risk/profiles`, `/models/scenario-comparison` |
| Methodology | `/about` | — (static, follows `docs/METHODOLOGY.md`) |

The selected cohort and scenario follow you between pages (URL parameters, then the
tab's `sessionStorage`; only those two values are stored). The prediction form is
generated from `/dataset/schema`, shows only the inputs the chosen scenario allows,
and never offers G3.

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
| 6 | Interpretability & academic risk analysis | ✅ Complete |
| 7 | End-to-end backend integration | ✅ Complete |
| 8 | Complete Apple-style frontend | ✅ Complete |
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
