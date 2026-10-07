# Student Academic Analytics and Risk Prediction System

An integrated student-analytics system that moves from **statistical understanding**
of student data, through **exploratory analytics** and **reproducible preprocessing**,
to a **comparison of machine-learning models** that predict academic performance and
identify **academic risk** — presented through a modern, interpretable web application.

> **Status: Phase 2 of 8 complete — validated data layer and Data Explorer.** The
> official UCI dataset can be downloaded and verified with one command, both cohorts
> pass validation, and the Data Explorer serves the real records. No statistical
> analysis has been run and no model has been trained yet; those modules are marked
> as planned. See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md).

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
Student data → Statistical analysis → Exploratory analysis → Preprocessing &
feature engineering → Model training → Evaluation & comparison → Interpretable
academic-risk insights → Web application
```

| Stage | Planned content |
| ----- | --------------- |
| Statistical analysis | Mean, median, mode, variance, SD, range, quartiles, distribution shape; Pearson/Spearman correlation with significance; t-test, ANOVA, chi-square, and non-parametric alternatives (Mann–Whitney, Kruskal–Wallis) when assumptions fail; effect sizes |
| Exploratory analysis | Univariate, bivariate and multivariate analysis; histograms, box plots, bar charts, scatter plots, correlation heatmaps; outliers; group comparisons; performance profiling |
| Preprocessing | Encoding, scaling, feature engineering fitted inside training folds only |
| Modelling | Regression and classification candidates compared with cross-validation |
| Interpretation | Model-agnostic feature importance and per-prediction explanations |

### Target definition and leakage control

Defined before any training — full detail in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

- **Regression target:** `G3`. **Classification target:** `at_risk = G3 < 10`
  (below the pass mark; threshold to be confirmed in Phase 5).
- `G3` is **never** used as an input to predict `G3` or a label derived from it.
- `G1`/`G2` are only used when the prediction scenario legitimately has them. Results
  are reported under three scenarios: **A** (with G1 + G2), **B** (with G1),
  **C** (no prior grades — early warning).

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
│   ├── analytics/      # Offline pipeline: data layer (Phase 2); statistics, EDA, modelling (later)
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
| 1 | Project foundation | ✅ Complete |
| 2 | Data layer & Data Explorer | ✅ Complete |
| 3 | Statistical analysis | Planned |
| 4 | Exploratory data analysis | Planned |
| 5 | Preprocessing & target formulation | Planned |
| 6 | Modelling & model comparison | Planned |
| 7 | Interpretability & risk insights | Planned |
| 8 | Polish, documentation & release | Planned |

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
