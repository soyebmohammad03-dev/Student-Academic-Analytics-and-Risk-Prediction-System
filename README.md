# Student Academic Analytics and Risk Prediction System

An integrated student-analytics system that moves from **statistical understanding**
of student data, through **exploratory analytics** and **reproducible preprocessing**,
to a **comparison of machine-learning models** that predict academic performance and
identify **academic risk** — presented through a modern, interpretable web application.

> **Status: Phase 3 of 9 complete — leakage-safe preprocessing and feature
> engineering.** The official UCI dataset is downloaded, verified and validated. The
> Data Explorer serves the real records. A reproducible scikit-learn preprocessing
> pipeline provides targets, scenario-specific feature matrices and stratified splits.
> No statistical analysis has been run and no model has been trained yet; those
> modules are marked as planned. See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md).

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
| Statistical analysis | Mean, median, mode, variance, SD, range, quartiles, distribution shape; Pearson/Spearman correlation with significance; t-test, ANOVA, chi-square, and non-parametric alternatives (Mann–Whitney, Kruskal–Wallis) when assumptions fail; effect sizes |
| Exploratory analysis | Univariate, bivariate and multivariate analysis; histograms, box plots, bar charts, scatter plots, correlation heatmaps; outliers; group comparisons; performance profiling |
| Preprocessing (implemented) | Targets, leakage-aware feature scenarios, one-hot/ordinal encoding with fixed categories, two justified engineered features, training-only imputation/scaling, stratified reproducible split |
| Modelling | Regression and classification candidates compared with cross-validation |
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

### Planned models

Selected on experimental evidence, not implemented wholesale.

- **Regression:** Linear Regression, Decision Tree, Random Forest
- **Classification:** Logistic Regression, Decision Tree, Random Forest, K-Nearest
  Neighbours, Support Vector Machine
- **Baselines:** mean predictor, majority class

### Evaluation metrics

- **Regression:** MAE, MSE, RMSE, R²
- **Classification:** Accuracy, Precision, Recall, F1-score, ROC-AUC, Confusion Matrix
- Stratified cross-validation and hyperparameter tuning where justified; a held-out
  test set used once for final reporting.

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
│   ├── analytics/      # Offline pipeline: data (Phase 2), preprocessing (Phase 3); stats/models later
│   └── tests/
├── frontend/           # Next.js application
├── data/               # raw/ and processed/ (git-ignored contents)
├── models/             # Trained artifacts (git-ignored)
├── notebooks/          # Exploration only
├── scripts/            # Developer helpers (check.sh)
├── docs/               # ARCHITECTURE.md, METHODOLOGY.md, DATA_DICTIONARY.md
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
| 4 | Statistics & exploratory data analysis | Planned |
| 5 | Machine learning & model evaluation | Planned |
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
