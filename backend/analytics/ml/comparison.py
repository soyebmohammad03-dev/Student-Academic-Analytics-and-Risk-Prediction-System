"""Standardised comparison tables derived from a training run.

Regression and classification tables are separate and never share metric columns.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from analytics.ml.config import Task
from analytics.ml.results import (
    ClassBalance,
    MlResults,
    ModelResult,
    Num,
    Selection,
    TargetSummary,
)
from analytics.ml.selection import PRIMARY_METRIC
from analytics.preprocessing import SCENARIOS, Scenario


class RegressionRow(BaseModel):
    cohort: str
    scenario: Scenario
    model: str
    label: str
    baseline: bool
    selected: bool
    cv_mae: Num
    cv_mae_std: Num
    cv_rmse: Num
    cv_rmse_std: Num
    cv_r2: Num
    cv_r2_std: Num
    test_mae: Num
    test_rmse: Num
    test_r2: Num


class ClassificationRow(BaseModel):
    cohort: str
    scenario: Scenario
    model: str
    label: str
    baseline: bool
    selected: bool
    cv_f1: Num
    cv_f1_std: Num
    cv_roc_auc: Num
    cv_roc_auc_std: Num
    cv_recall: Num
    cv_precision: Num
    test_accuracy: Num
    test_precision: Num
    test_recall: Num
    test_specificity: Num
    test_f1: Num
    test_roc_auc: Num
    test_balanced_accuracy: Num


class RegressionTable(BaseModel):
    cohort: str
    rows: list[RegressionRow]
    selections: list[Selection]


class ClassificationTable(BaseModel):
    cohort: str
    rows: list[ClassificationRow]
    selections: list[Selection]


class ScenarioRow(BaseModel):
    scenario: Scenario
    label: str
    information: str
    selected_model: str
    selected_label: str
    best_cv_model: str
    cv: dict[str, Num] = Field(description="Selected model, mean over outer folds.")
    cv_std: dict[str, Num]
    test: dict[str, Num] = Field(description="Selected model, held-out test set.")
    baseline_cv: dict[str, Num]
    baseline_test: dict[str, Num]


class ScenarioComparison(BaseModel):
    cohort: str
    task: Task
    primary_metric: str
    rows: list[ScenarioRow]
    note: str


class CohortSelection(BaseModel):
    task: Task
    scenario: Scenario
    model: str
    label: str
    cv_primary: Num
    test_primary: Num


class CohortRow(BaseModel):
    cohort: str
    subject: str
    n: int
    n_train: int
    n_test: int
    target: TargetSummary
    risk: dict[str, ClassBalance]
    selected: list[CohortSelection]


class CohortComparison(BaseModel):
    cohorts: list[CohortRow]
    differences: list[str] = Field(
        description="Task/scenario pairs where the selected model differs between cohorts."
    )


def _selected(selections: list[Selection], result: ModelResult) -> bool:
    return any(
        s.task == result.task and s.scenario == result.scenario and s.model == result.model
        for s in selections
    )


def regression_table(results: MlResults, cohort: str) -> RegressionTable:
    c = results.cohort(cohort)
    selections = [s for s in c.selections if s.task is Task.REGRESSION]
    rows = [
        RegressionRow(
            cohort=c.cohort,
            scenario=r.scenario,
            model=r.model,
            label=r.label,
            baseline=r.baseline,
            selected=_selected(selections, r),
            cv_mae=r.cv["mae"].mean,
            cv_mae_std=r.cv["mae"].std,
            cv_rmse=r.cv["rmse"].mean,
            cv_rmse_std=r.cv["rmse"].std,
            cv_r2=r.cv["r2"].mean,
            cv_r2_std=r.cv["r2"].std,
            test_mae=r.test["mae"],
            test_rmse=r.test["rmse"],
            test_r2=r.test["r2"],
        )
        for r in c.regression
    ]
    return RegressionTable(cohort=c.cohort, rows=rows, selections=selections)


def classification_table(results: MlResults, cohort: str) -> ClassificationTable:
    c = results.cohort(cohort)
    selections = [s for s in c.selections if s.task is Task.CLASSIFICATION]
    rows = [
        ClassificationRow(
            cohort=c.cohort,
            scenario=r.scenario,
            model=r.model,
            label=r.label,
            baseline=r.baseline,
            selected=_selected(selections, r),
            cv_f1=r.cv["f1"].mean,
            cv_f1_std=r.cv["f1"].std,
            cv_roc_auc=r.cv["roc_auc"].mean,
            cv_roc_auc_std=r.cv["roc_auc"].std,
            cv_recall=r.cv["recall"].mean,
            cv_precision=r.cv["precision"].mean,
            test_accuracy=r.test["accuracy"],
            test_precision=r.test["precision"],
            test_recall=r.test["recall"],
            test_specificity=r.test["specificity"],
            test_f1=r.test["f1"],
            test_roc_auc=r.test["roc_auc"],
            test_balanced_accuracy=r.test["balanced_accuracy"],
        )
        for r in c.classification
    ]
    return ClassificationTable(cohort=c.cohort, rows=rows, selections=selections)


def scenario_comparison(results: MlResults, cohort: str, task: Task) -> ScenarioComparison:
    task = Task(task)
    c = results.cohort(cohort)
    models = c.regression if task is Task.REGRESSION else c.classification
    rows = []
    for scenario in (Scenario.EARLY, Scenario.MID_YEAR, Scenario.FULL_HISTORY):
        selection = next(
            (s for s in c.selections if s.task is task and s.scenario is scenario), None
        )
        if selection is None:
            continue
        in_scenario = [r for r in models if r.scenario is scenario]
        chosen = next(r for r in in_scenario if r.model == selection.model)
        baseline = next(r for r in in_scenario if r.baseline)
        spec = SCENARIOS[scenario]
        rows.append(
            ScenarioRow(
                scenario=scenario,
                label=spec.label,
                information=spec.description,
                selected_model=chosen.model,
                selected_label=chosen.label,
                best_cv_model=selection.best_model,
                cv={k: v.mean for k, v in chosen.cv.items()},
                cv_std={k: v.std for k, v in chosen.cv.items()},
                test=dict(chosen.test),
                baseline_cv={k: v.mean for k, v in baseline.cv.items()},
                baseline_test=dict(baseline.test),
            )
        )
    return ScenarioComparison(
        cohort=c.cohort,
        task=task,
        primary_metric=PRIMARY_METRIC[task],
        rows=rows,
        note=(
            "The scenarios differ in what is known when the prediction is made, not in "
            "model quality. G1 and G2 are recorded during the same school year as G3 and "
            "are only available after the first and second grading periods. The early "
            "scenario estimates academic risk (G3 below 10); it does not predict dropout."
        ),
    )


def cohort_comparison(results: MlResults) -> CohortComparison:
    rows = []
    for c in results.cohorts:
        selected = []
        for s in c.selections:
            models = c.regression if s.task is Task.REGRESSION else c.classification
            r = next(m for m in models if m.scenario is s.scenario and m.model == s.model)
            metric = PRIMARY_METRIC[s.task]
            selected.append(
                CohortSelection(
                    task=s.task,
                    scenario=s.scenario,
                    model=s.model,
                    label=s.label,
                    cv_primary=r.cv[metric].mean,
                    test_primary=r.test[metric],
                )
            )
        rows.append(
            CohortRow(
                cohort=c.cohort,
                subject=c.subject,
                n=c.n,
                n_train=c.n_train,
                n_test=c.n_test,
                target=c.target,
                risk=dict(c.risk),
                selected=selected,
            )
        )

    differences = []
    if len(results.cohorts) > 1:
        by_key: dict[tuple[Task, Scenario], dict[str, str]] = {}
        for c in results.cohorts:
            for s in c.selections:
                by_key.setdefault((s.task, s.scenario), {})[c.subject] = s.label
        for (task, scenario), chosen in by_key.items():
            if len(set(chosen.values())) > 1:
                detail = "; ".join(f"{subject}: {label}" for subject, label in chosen.items())
                differences.append(f"{task}, {scenario}: {detail}.")
    return CohortComparison(cohorts=rows, differences=differences)
