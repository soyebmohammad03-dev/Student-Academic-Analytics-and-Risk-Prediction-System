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
| 5     | Machine learning & model evaluation         | ✅ Complete |
| 6     | Interpretability & academic risk analysis   | ✅ Complete |
| 7     | End-to-end backend integration              | ✅ Complete |
| 8     | Complete Apple-style frontend               | ✅ Complete |
| 9     | Final validation, documentation & presentation readiness | ✅ Complete |

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

## Phase 5 — Machine learning & model evaluation ✅
- `backend/analytics/ml/`:
  - model registry with bounded search spaces;
  - nested cross-validation (5 × 5) on the training split, and one-off test scoring;
  - metrics, including ROC-AUC from scores with undefined cases handled;
  - a CV-only selection rule (one SE, simplest model);
  - error analysis and automated diagnostics;
  - comparison tables, persistence, a prediction service and a generated report.
- Models:
  - baselines: mean predictor, majority class;
  - regression: linear regression, decision tree, random forest;
  - classification: logistic regression, decision tree, k-NN, SVM (RBF), random forest.
  Class imbalance is handled with balanced class weights, without resampling.
- Results for both cohorts × three scenarios (early, mid-year, full history), with
  scenario and cohort comparisons and a zero-grade sensitivity check.
- 12 selected pipelines persisted with metadata and checksums (git-ignored;
  `python -m analytics.ml.train` regenerates them).
- API: `/models`, `/models/{regression,classification,evaluations,scenario-comparison,
  cohort-comparison,selected}` and `POST /models/predict`.
- `docs/ML_RESULTS.md`, generated from the training run.
- The model-comparison page was built in Phase 8.

## Phase 6 — Interpretability & academic risk analysis ✅
- `backend/analytics/interpret/`:
  - attribute-level interventional Shapley values (permutation sampling; exact
    additivity; seeded and bounded);
  - permutation importance on the test set (plus a G3 > 0 check), mean |Shapley|,
    impurity importance and coefficients;
  - probability calibration;
  - individual explanations, single-attribute and scenario sensitivity experiments.

  No model was retrained, and SHAP was not added (see METHODOLOGY §7.2).
- `backend/analytics/risk/`:
  - group-level risk profiles for school-related attributes, with Wilson CIs and BH
    tests;
  - evidence-checked, non-punitive suggestions with a disclaimer.
- API: `/interpretability/{importance,explain,sensitivity,scenario-sensitivity}` and
  `/risk/{profiles,suggestions,insights}`. Insights keep the individual, group and
  suggestion layers separate.
- `docs/INTERPRETABILITY.md`, generated by `python -m analytics.interpret.build`.
- A functional Risk Analysis page (profiles and importance). The prediction form and
  the separate Interpretability page followed in Phase 8.

## Phase 7 — End-to-end backend integration ✅
- `analytics/pipeline.py`: one `AnalyticsPipeline` owns every cache, with one entry per
  cohort or artefact file version. It provides independent steps, `readiness()` and
  `summary()`. The API services are now thin views over it, and each cohort is
  prepared once instead of three times.
- New endpoints: `/ready`, `/dashboard/summary` and `/pipeline/summary`, with observed
  facts kept separate from model evaluation.
- Model lifecycle: integrity checks cover checksum, scikit-learn version, estimator
  class and inputs. Corrupted artefacts return 503 instead of crashing. Requests never
  train or download.
- One error format for every status, including 404, 405 and 500, with no paths or
  tracebacks. Unknown model names return 422. Invalid cohort files return 503
  `dataset_invalid`.
- Structured JSON logging and request ids.
- Phase 6 importance ranking corrected (by value, not magnitude); results rebuilt
  without retraining.
- `docs/API.md` reference with measured request times; integration tests on synthetic
  and real data.

## Phase 8 — Complete Apple-style frontend ✅
- Every page reads real API responses; nothing is a mock-up:
  - **Dashboard:** observed cohort facts (counts, at-risk share with Wilson CI, G3
    distribution, data quality) kept apart from the selected models' CV and test
    scores; research-question findings, group highlights, model reliance and live
    readiness with fix commands.
  - **Model Comparison:** scenario chart (CV mean ± SD, held-out test, baseline), a
    leaderboard of every model with CV and test metrics labelled separately and
    per-fold dots, the CV-only selection rationale, confusion matrix or residual
    analysis, visible weak-recall warnings, cohort comparison and metric definitions.
  - **Prediction:** a form generated from `/dataset/schema`; only the scenario's inputs
    (G1/G2 only where allowed, never G3); client-side validation; optional fill from a
    dataset row; final grade and academic-risk flag shown separately with model,
    scenario, honest probability handling and test metrics; Shapley explanations;
    observed group statistics and evidence-checked suggestions kept separate; an
    educational-use disclaimer.
  - **Interpretability:** importance per method on its own scale, calibration, and for
    one dataset row an explanation, a single-attribute sensitivity experiment on a fixed
    output scale and the scenario comparison.
  - **Risk Analysis:** definition, profiles with intervals and small-group marking,
    two-way tables, and the classifiers' held-out recall/precision in a separate,
    model-derived section.
  - **Methodology:** dataset, reference paper, validation, statistics, EDA, models,
    evaluation, scenarios, academic risk, interpretability, leakage prevention and
    limitations, consistent with `docs/METHODOLOGY.md`.
- Shared components: metric cards, accessible tooltips, callouts and result-kind badges,
  loading/empty/error states, labelled toolbars, keyboard-navigable segmented controls,
  form fields, and charts (grade strip, confusion matrix, scenario chart, explanation,
  sensitivity).
- Shared state: cohort and scenario synchronised across pages (URL first, then
  `sessionStorage`; no student records stored). GET and POST hooks abort superseded
  requests, so stale responses never replace newer ones.
- Skip link, visible focus, mobile navigation sheet, responsive layouts, light and dark
  themes. Verified in a browser on desktop and mobile widths with the real API.
- Frontend tests: 25 → 58 (7 → 13 files) covering page rendering, API integration, cohort and
  scenario changes, loading/error/empty states, chart data, prediction validation,
  leakage prevention and keyboard interaction.

## Phase 9 — Final validation, documentation & presentation readiness ✅
- **Scientific audit** against the data and artefacts: cohort sizes and at-risk counts,
  raw-file checksums, no `G3`/`at_risk` in any persisted pipeline, scenario-correct
  grades, and the CV-only selection rule reproducing all 12 choices
  (METHODOLOGY §9). Stale statements fixed: `/project` reported finished modules as in
  progress, and the data dictionary still described a completed sensitivity check as
  planned.
- **Fresh-clone reproducibility**: clone → install → download → train → interpret →
  tests → API ready → frontend build, all passing; regenerated documents identical except
  a numpy patch version ([docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md)).
- **Interface fixes**: no flash of default cohort/scenario (client-only views); phone
  layouts for the dashboard model matrix and a sticky model column in the leaderboard;
  no page-level horizontal overflow from 320 px up; WCAG AA contrast in both themes;
  definition-list, scroll-region and table-header semantics
  ([docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md)).
- **Automated accessibility**: axe-core in Vitest for every page view, and in the browser
  on all routes at five widths and both themes (0 violations).
- **Cross-browser**: Chromium and WebKit verified; Firefox could not be launched on the
  test machine and is documented as untested.
- **Security and dependencies**: `pip-audit` found no known vulnerabilities; production npm
  dependencies have none (five advisories affect only the dev-time ESLint toolchain, whose
  suggested fix is a breaking downgrade); no secrets, data or artefacts tracked; security
  posture documented (no authentication or rate limiting — local prototype).
- **Repository showcase**: rewritten README with banner, badges, Mermaid architecture,
  workflow diagram, generated results tables (tested against the artefacts) and real
  screenshots; architecture diagrams and security notes; GitHub description and topics;
  `LICENSE` restored to the standard MIT text with the dataset terms in `NOTICE`.
- **CI**: GitHub Actions runs Ruff, pytest, ESLint, TypeScript, Vitest and the production
  build on every push, without downloading data or training models.

The nine-phase roadmap is complete.
