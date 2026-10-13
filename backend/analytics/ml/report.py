"""Render docs/ML_RESULTS.md from a training run's ``ml_results.json``.

Every number comes from the persisted results of ``python -m analytics.ml.train``;
nothing is typed by hand. The training CLI writes the document, and a test checks that
the committed copy matches the local results whenever they exist.
"""

from __future__ import annotations

from pathlib import Path

from analytics.ml.comparison import cohort_comparison, scenario_comparison
from analytics.ml.config import Task
from analytics.ml.registry import MODELS
from analytics.ml.results import CohortResults, MlResults, ModelResult, Num
from analytics.ml.selection import METRIC_LABEL
from analytics.preprocessing import SCENARIOS, Scenario

OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "ML_RESULTS.md"
SCENARIO_ORDER = (Scenario.EARLY, Scenario.MID_YEAR, Scenario.FULL_HISTORY)


def _f(value: Num, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _ms(result: ModelResult, metric: str, digits: int = 3) -> str:
    s = result.cv[metric]
    if s.mean is None:
        return "—"
    return f"{s.mean:.{digits}f} ± {_f(s.std, digits)}"


def _name(result: ModelResult, selected: set[tuple[Task, Scenario, str]]) -> str:
    label = result.label
    if (result.task, result.scenario, result.model) in selected:
        label = f"**{label}** ✓"
    return label


def _run_section(results: MlResults) -> list[str]:
    run = results.run
    software = ", ".join(f"{k} {v}" for k, v in run.software.items())
    lines = [
        "## Run configuration",
        "",
        "| Setting | Value |",
        "| --- | --- |",
        f"| Random seed | {run.random_state} (split, CV shuffling and every estimator) |",
        f"| Train / test split | stratified on `at_risk`, test share {run.test_size:g} |",
        f"| Regression CV | `{run.cv_strategy[Task.REGRESSION]}` |",
        f"| Classification CV | `{run.cv_strategy[Task.CLASSIFICATION]}` |",
        f"| CV design | nested: {run.cv_folds} outer folds for performance; grid search with "
        f"{run.cv_folds} inner folds inside each outer training portion |",
        f"| Tuning metric | regression {run.tuning_metric[Task.REGRESSION]}; "
        f"classification {run.tuning_metric[Task.CLASSIFICATION]} |",
        f"| Selection metric | regression CV {run.selection_metric[Task.REGRESSION]}; "
        f"classification CV {run.selection_metric[Task.CLASSIFICATION]} (one-SE rule, then "
        "simplest) |",
        "| Classification threshold | the estimator's own rule: P(at risk) > 0.5, or SVM "
        "decision score > 0 |",
        f"| Search mode | {run.search} |",
        f"| Software | {software} |",
        "",
        "## Models and search spaces",
        "",
        "| Task | Model | Class weight | Search space | Combinations |",
        "| --- | --- | --- | --- | --- |",
    ]
    first = results.cohorts[0]
    for task, models in (
        (Task.REGRESSION, first.regression),
        (Task.CLASSIFICATION, first.classification),
    ):
        seen = set()
        for r in models:
            if r.model in seen:
                continue
            seen.add(r.model)
            space = (
                "; ".join(
                    f"`{k}` ∈ {{{', '.join(str(v) for v in values)}}}"
                    for k, values in r.search_space.items()
                )
                or "none (fitted as is)"
            )
            lines.append(
                f"| {task} | {r.label} | {r.class_weight or '—'} | {space} | {r.candidates} |"
            )
    lines.append("")
    lines += ["Strengths and weaknesses:", ""]
    for task in Task:
        for spec in MODELS[task]:
            lines.append(f"- *{spec.label}* ({task}): {spec.strengths} {spec.weaknesses}")
    lines.append("")
    return lines


def _regression_table(c: CohortResults, selected) -> list[str]:
    lines = [
        "| Scenario | Model | CV MAE | CV RMSE | CV R² | Test MAE | Test RMSE | Test R² |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for scenario in SCENARIO_ORDER:
        for r in (r for r in c.regression if r.scenario is scenario):
            lines.append(
                f"| {scenario} | {_name(r, selected)} | {_ms(r, 'mae', 2)} | {_ms(r, 'rmse', 2)} "
                f"| {_ms(r, 'r2')} | {_f(r.test['mae'], 2)} | {_f(r.test['rmse'], 2)} "
                f"| {_f(r.test['r2'])} |"
            )
    return lines


def _classification_table(c: CohortResults, selected) -> list[str]:
    lines = [
        "| Scenario | Model | CV F1 | CV ROC-AUC | CV recall | Test acc. | Test bal. acc. "
        "| Test precision | Test recall | Test specificity | Test F1 | Test ROC-AUC |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for scenario in SCENARIO_ORDER:
        for r in (r for r in c.classification if r.scenario is scenario):
            t = r.test
            lines.append(
                f"| {scenario} | {_name(r, selected)} | {_ms(r, 'f1')} | {_ms(r, 'roc_auc')} "
                f"| {_ms(r, 'recall')} | {_f(t['accuracy'])} | {_f(t['balanced_accuracy'])} "
                f"| {_f(t['precision'])} | {_f(t['recall'])} | {_f(t['specificity'])} "
                f"| {_f(t['f1'])} | {_f(t['roc_auc'])} |"
            )
    return lines


def _scenario_lines(results: MlResults, c: CohortResults) -> list[str]:
    lines = [
        "### Scenario comparison (selected model per scenario)",
        "",
        "| Task | Scenario | Selected model | CV primary metric | Test primary metric "
        "| Baseline CV | Secondary (CV) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for task in Task:
        comparison = scenario_comparison(results, c.cohort, task)
        metric = comparison.primary_metric
        secondary = "r2" if task is Task.REGRESSION else "roc_auc"
        for row in comparison.rows:
            lines.append(
                f"| {task} | {SCENARIOS[row.scenario].label} | {row.selected_label} "
                f"| {METRIC_LABEL[metric]} {_f(row.cv[metric])} ± {_f(row.cv_std[metric])} "
                f"| {_f(row.test[metric])} | {_f(row.baseline_cv[metric])} "
                f"| {METRIC_LABEL[secondary]} {_f(row.cv[secondary])} |"
            )
    lines += ["", comparison.note, ""]
    return lines


def _error_lines(c: CohortResults) -> list[str]:
    lines = ["### Error analysis (selected models, test set)", ""]
    for e in c.regression_errors:
        r = e.residuals
        lines += [
            f"**Regression · {e.scenario} · {e.model}** (n = {e.n}): residual (actual − "
            f"predicted) mean {_f(r.mean, 2)}, SD {_f(r.std, 2)}, range {_f(r.min, 1)} to "
            f"{_f(r.max, 1)}; {100 * r.within_1:.0f}% within ±1 and {100 * r.within_2:.0f}% "
            "within ±2 grade points.",
            "",
            "| Band | n | MAE | Mean residual |",
            "| --- | --- | --- | --- |",
            *(
                f"| {b.band} | {b.n} | {_f(b.mae, 2)} | {_f(b.mean_residual, 2)} |"
                for b in e.by_band
            ),
            "",
            *(f"- {p}" for p in e.patterns),
            "",
        ]
    for e in c.classification_errors:
        m = e.confusion
        lines += [
            f"**Classification · {e.scenario} · {e.model}** (n = {e.n}): TP {m.tp}, FN {m.fn}, "
            f"FP {m.fp}, TN {m.tn}; "
            + "; ".join(f"{o.label.lower()} {o.correct}/{o.n} correct" for o in e.by_class)
            + ".",
            "",
            *(f"- {p}" for p in e.patterns),
            "",
        ]
    if c.zero_grade_sensitivity:
        lines += [
            "### Zero-grade sensitivity (exploratory)",
            "",
            "| Scenario | Model | Train rows with G3 = 0 removed | Test n (G3 > 0) "
            "| RMSE trained on all | RMSE trained without zeros | MAE all | MAE without zeros |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for z in c.zero_grade_sensitivity:
            lines.append(
                f"| {z.scenario} | {z.model} | {z.train_zeros_removed} | {z.test_n} "
                f"| {_f(z.all_rows_model['rmse'], 2)} | {_f(z.without_zeros_model['rmse'], 2)} "
                f"| {_f(z.all_rows_model['mae'], 2)} | {_f(z.without_zeros_model['mae'], 2)} |"
            )
        lines += ["", c.zero_grade_sensitivity[0].note, ""]
    return lines


def _diagnostic_lines(c: CohortResults) -> list[str]:
    lines = ["### Automated diagnostics", ""]
    items = [
        f"- {d.level}: {r.task} · {r.scenario} · {r.label} — {d.message}"
        for r in [*c.regression, *c.classification]
        for d in r.diagnostics
    ]
    return lines + (items or ["- None."]) + [""]


def _cohort_section(results: MlResults, c: CohortResults) -> list[str]:
    selected = {(s.task, s.scenario, s.model) for s in c.selections}
    t = c.target
    lines = [
        f"## {c.subject} (n = {c.n})",
        "",
        f"- Train / test: {c.n_train} / {c.n_test} students.",
        f"- Final grade G3: mean {t.mean:.2f}, SD {t.std:.2f}, median {t.median:g}, range "
        f"{t.minimum}–{t.maximum}; {t.zero_count} students with G3 = 0.",
    ]
    for part in ("all", "train", "test"):
        b = c.risk[part]
        lines.append(
            f"- Academic risk ({part}): {b.at_risk} at risk ({b.at_risk_percent:.1f}%), "
            f"{b.not_at_risk} not at risk ({b.not_at_risk_percent:.1f}%)."
        )
    lines += [
        "",
        "### Regression (target G3)",
        "",
        "CV values are mean ± SD over the outer folds of nested CV on the training set. "
        "✓ marks the selected model.",
        "",
        *_regression_table(c, selected),
        "",
        "### Classification (target at_risk = G3 < 10)",
        "",
        *_classification_table(c, selected),
        "",
        "### Selection",
        "",
        *(f"- **{s.task} · {s.scenario}**: {s.reason}" for s in c.selections),
        "",
        *_scenario_lines(results, c),
        *_error_lines(c),
        *_diagnostic_lines(c),
    ]
    return lines


def render(results: MlResults) -> str:
    lines = [
        "# Machine-learning results",
        "",
        "> Generated by `python -m analytics.ml.train` from the official UCI files. Do not "
        "edit by hand. Methodology: [METHODOLOGY.md §6](METHODOLOGY.md#6-machine-learning-"
        "and-evaluation-phase-5).",
        "",
        "Targets: the final grade **G3** (regression) and **academic risk**, G3 below 10 "
        "(classification). Academic risk is not dropout: the dataset records no dropout. "
        "All results are associations learned from observational data from two schools.",
        "",
        *_run_section(results),
    ]
    for c in results.cohorts:
        lines += _cohort_section(results, c)

    comparison = cohort_comparison(results)
    lines += [
        "## Cohort comparison",
        "",
        "| Cohort | n | Train / test | G3 mean (SD) | At risk |",
        "| --- | --- | --- | --- | --- |",
        *(
            f"| {r.subject} | {r.n} | {r.n_train} / {r.n_test} | {r.target.mean:.2f} "
            f"({r.target.std:.2f}) | {r.risk['all'].at_risk} "
            f"({r.risk['all'].at_risk_percent:.1f}%) |"
            for r in comparison.cohorts
        ),
        "",
        "| Task | Scenario | "
        + " | ".join(f"{r.subject}: selected (CV / test primary)" for r in comparison.cohorts)
        + " |",
        "| --- | --- | " + " | ".join("---" for _ in comparison.cohorts) + " |",
    ]
    for task in Task:
        for scenario in SCENARIO_ORDER:
            cells = []
            for r in comparison.cohorts:
                s = next((x for x in r.selected if x.task is task and x.scenario is scenario), None)
                cells.append(
                    "—" if s is None else f"{s.label} ({_f(s.cv_primary)} / {_f(s.test_primary)})"
                )
            lines.append(f"| {task} | {scenario} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Selected models that differ between cohorts:",
        "",
        *([f"- {d}" for d in comparison.differences] or ["- None."]),
        "",
        "## Interpretability (Phase 6)",
        "",
        "Global feature importance for each selected model (permutation importance on the "
        "test set, mean absolute Shapley values, impurity importance or coefficients), "
        "probability calibration of the selected classifiers, and group-level academic-risk "
        "profiles are generated separately from the persisted models in "
        "[INTERPRETABILITY.md](INTERPRETABILITY.md) by `python -m analytics.interpret.build`. "
        "No model was retrained for them.",
        "",
        "## Limitations",
        "",
        "- One held-out test set per cohort (79 and 130 students). Test scores are single "
        "estimates with wide uncertainty; the nested-CV means and SDs are the more stable "
        "summary.",
        "- G1 and G2 are interim grades of the same school year. The full-history and "
        "mid-year scenarios reflect how much the final grade is already known from them, "
        "not a better understanding of students.",
        "- Early-scenario results describe what background, behavioural and school attributes "
        "are associated with; they are not causal and not a prediction of dropout.",
        "- Both cohorts come from two schools in one region and one year. Performance on other "
        "schools or years is unknown.",
        "- Students with G3 = 0 are kept in every result. Every one of them has 0 recorded "
        "absences (Phase 4), which suggests a G3 of 0 can mean the final evaluation was not "
        "taken; the sensitivity table shows how much they weigh on regression error.",
        "- Classification uses each estimator's default decision rule. A different threshold "
        "trades recall against precision; the threshold was not tuned.",
        "",
    ]
    return "\n".join(lines)


# --- README summary --------------------------------------------------------------

README = Path(__file__).resolve().parents[3] / "README.md"
README_START = "<!-- results:start (generated by `python -m analytics.ml.train --report-only`) -->"
README_END = "<!-- results:end -->"
_SUBJECT = {"math": "Mathematics", "portuguese": "Portuguese"}
_SCENARIO = {"early": "Early", "mid_year": "Mid-year", "full_history": "Full history"}


def readme_results(results: MlResults) -> str:
    """The selected-model tables shown in README.md, rendered from the training run."""

    def find(c: CohortResults, task: Task, scenario: str, model: str) -> ModelResult:
        return next(r for r in getattr(c, task) if r.scenario == scenario and r.model == model)

    def baseline(c: CohortResults, task: Task, scenario: str) -> ModelResult:
        return next(r for r in getattr(c, task) if r.scenario == scenario and r.baseline)

    lines = [
        README_START,
        "",
        "**Final grade (regression).** Lower RMSE/MAE is better; the baseline predicts the "
        "training mean.",
        "",
        "| Cohort | Scenario | Selected model | CV RMSE (mean ± SD) | Test RMSE | Test MAE "
        "| Test R² | Baseline test RMSE |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    order = {s: i for i, s in enumerate(SCENARIOS)}
    for c in results.cohorts:
        for s in sorted(
            (s for s in c.selections if s.task == "regression"), key=lambda s: order[s.scenario]
        ):
            m, b = find(c, "regression", s.scenario, s.model), baseline(c, "regression", s.scenario)
            lines.append(
                f"| {_SUBJECT[c.cohort]} | {_SCENARIO[s.scenario]} | {m.label} "
                f"| {_ms(m, 'rmse', 2)} | {_f(m.test['rmse'], 2)} | {_f(m.test['mae'], 2)} "
                f"| {_f(m.test['r2'], 2)} | {_f(b.test['rmse'], 2)} |"
            )
    lines += [
        "",
        "**Academic risk (classification, positive class = G3 < 10).** The majority-class "
        "baseline has recall 0 and F1 0.",
        "",
        "| Cohort | Scenario | Selected model | CV F1 (mean ± SD) | Test F1 | Test recall "
        "| Test precision | Test ROC-AUC |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for c in results.cohorts:
        for s in sorted(
            (s for s in c.selections if s.task == "classification"),
            key=lambda s: order[s.scenario],
        ):
            m = find(c, "classification", s.scenario, s.model)
            lines.append(
                f"| {_SUBJECT[c.cohort]} | {_SCENARIO[s.scenario]} | {m.label} "
                f"| {_ms(m, 'f1', 2)} | {_f(m.test['f1'], 2)} | {_f(m.test['recall'], 2)} "
                f"| {_f(m.test['precision'], 2)} | {_f(m.test['roc_auc'], 2)} |"
            )
    lines += [
        "",
        f"Training run of {results.run.created_at[:10]}; held-out test sets of "
        + " and ".join(f"{c.n_test} ({_SUBJECT[c.cohort]})" for c in results.cohorts)
        + " students. Full tables, folds and error analysis: "
        "[docs/ML_RESULTS.md](docs/ML_RESULTS.md).",
        "",
        README_END,
    ]
    return "\n".join(lines)


def update_readme(results: MlResults, path: Path = README) -> bool:
    """Replace the generated block in README.md. Returns False if the markers are missing."""
    text = path.read_text(encoding="utf-8")
    start, end = text.find(README_START), text.find(README_END)
    if start < 0 or end < 0:
        return False
    path.write_text(
        text[:start] + readme_results(results) + text[end + len(README_END) :], encoding="utf-8"
    )
    return True
