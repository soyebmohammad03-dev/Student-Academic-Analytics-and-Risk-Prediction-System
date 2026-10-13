"""Train and evaluate every model for one cohort, then select and analyse.

``train_cohort`` is the single entry point. It never reads the test set during tuning
or selection: the test rows of the Phase 3 split are passed to ``evaluate`` only for the
final, one-off scoring of each fitted pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.base import clone
from sklearn.pipeline import Pipeline

from analytics.data import COHORTS, Cohort
from analytics.ml.config import Task, TrainingConfig
from analytics.ml.errors import classification_errors, regression_errors
from analytics.ml.evaluation import (
    Evaluation,
    FoldHook,
    evaluate,
    predict,
    score,
)
from analytics.ml.metrics import score_kind
from analytics.ml.registry import ESTIMATOR_STEP, MODELS, ModelSpec, search_space
from analytics.ml.results import (
    ClassBalance,
    CohortResults,
    Diagnostic,
    ModelResult,
    Selection,
    TargetSummary,
    ZeroGradeSensitivity,
)
from analytics.ml.selection import METRIC_LABEL, PRIMARY_METRIC, better, select
from analytics.preprocessing import AnalyticalDataset, Scenario, Split

#: Diagnostics thresholds (fixed in advance, see docs/METHODOLOGY.md §6).
SUSPICIOUS_SCORE = 0.99
GAP_IN_SDS = 2.0


@dataclass
class TrainedCohort:
    results: CohortResults
    #: Fitted pipelines of the selected models, keyed by (task, scenario).
    selected: dict[tuple[Task, Scenario], Evaluation] = field(default_factory=dict)


def _targets(split: Split, task: Task):
    if task is Task.REGRESSION:
        return split.y_train_regression, split.y_test_regression
    return split.y_train_risk, split.y_test_risk


def _balance(labels) -> ClassBalance:
    n, at_risk = len(labels), int(labels.sum())
    return ClassBalance(
        n=n,
        at_risk=at_risk,
        not_at_risk=n - at_risk,
        at_risk_percent=100 * at_risk / n,
        not_at_risk_percent=100 * (n - at_risk) / n,
    )


def diagnostics(ev: Evaluation, baseline: ModelResult | None) -> list[Diagnostic]:
    """Automated checks for the quality review. They flag; they never alter results."""
    spec, out = ev.spec, []
    metric = PRIMARY_METRIC[spec.task]
    for name in ("r2", "roc_auc"):
        values = [ev.test.get(name), ev.cv[name].mean if name in ev.cv else None]
        if any(v is not None and v >= SUSPICIOUS_SCORE for v in values):
            out.append(
                Diagnostic(
                    level="warning",
                    code="near_perfect",
                    message=f"{name} ≥ {SUSPICIOUS_SCORE}: check for leakage.",
                )
            )
    if spec.task is Task.CLASSIFICATION:
        predicted = set(np.unique(ev.test_predictions.y_pred).tolist())
        if len(predicted) == 1:
            out.append(
                Diagnostic(
                    level="info" if spec.baseline else "warning",
                    code="single_class",
                    message=(
                        "Predicts the same class for every test student"
                        + (" (expected for this baseline)." if spec.baseline else ".")
                    ),
                )
            )
        if ev.test.get("precision") is None:
            out.append(
                Diagnostic(
                    level="info",
                    code="precision_undefined",
                    message="Precision is undefined: no test student was predicted at risk.",
                )
            )
    cv, test = ev.cv[metric], ev.test.get(metric)
    if cv.mean is not None and cv.std and test is not None:
        gap = test - cv.mean
        if abs(gap) > GAP_IN_SDS * cv.std:
            out.append(
                Diagnostic(
                    level="info",
                    code="cv_test_gap",
                    message=(
                        f"Test {METRIC_LABEL[metric]} ({test:.3f}) differs from the CV mean "
                        f"({cv.mean:.3f}) by more than {GAP_IN_SDS:g} fold SDs ({cv.std:.3f}). "
                        "One test split is a single noisy estimate; the CV mean is the more "
                        "stable figure."
                    ),
                )
            )
    if (
        not spec.baseline
        and baseline is not None
        and baseline.cv[metric].mean is not None
        and cv.mean is not None
        and not better(metric, cv.mean, baseline.cv[metric].mean)
    ):
        out.append(
            Diagnostic(
                level="warning",
                code="no_better_than_baseline",
                message=f"Cross-validated {METRIC_LABEL[metric]} does not improve on the baseline.",
            )
        )
    return out


def _result(
    cohort: str, ev: Evaluation, split: Split, config: TrainingConfig, baseline
) -> ModelResult:
    spec = ev.spec
    return ModelResult(
        cohort=cohort,
        task=spec.task,
        scenario=ev.scenario,
        model=spec.key,
        label=spec.label,
        family=spec.family,
        baseline=spec.baseline,
        complexity=spec.complexity,
        class_weight=spec.class_weight,
        search_space={
            k.removeprefix(f"{ESTIMATOR_STEP}__"): v
            for k, v in search_space(spec, config.search).items()
        },
        candidates=ev.candidates,
        best_params=ev.best_params,
        outer_fold_params=ev.outer_fold_params,
        cv=ev.cv,
        test=ev.test,
        test_confusion=ev.test_confusion,
        test_predicted_positive=(
            int(ev.test_predictions.y_pred.sum()) if spec.task is Task.CLASSIFICATION else None
        ),
        n_train=len(split.X_train),
        n_test=len(split.X_test),
        diagnostics=diagnostics(ev, baseline),
    )


def _zero_grade_sensitivity(
    cohort: str, ev: Evaluation, split: Split
) -> ZeroGradeSensitivity | None:
    """Exploratory: refit the selected regression pipeline without G3 = 0 students."""
    keep_train = split.y_train_regression > 0
    keep_test = split.y_test_regression > 0
    if keep_train.all():
        return None
    X_test, y_test = split.X_test[keep_test], split.y_test_regression[keep_test]
    refit: Pipeline = clone(ev.pipeline).fit(
        split.X_train[keep_train], split.y_train_regression[keep_train]
    )
    return ZeroGradeSensitivity(
        cohort=cohort,
        scenario=ev.scenario,
        model=ev.spec.key,
        train_zeros_removed=int((~keep_train).sum()),
        test_n=int(keep_test.sum()),
        all_rows_model=score(
            Task.REGRESSION, predict(Task.REGRESSION, ev.pipeline, X_test, y_test)
        ),
        without_zeros_model=score(Task.REGRESSION, predict(Task.REGRESSION, refit, X_test, y_test)),
        note=(
            "Both models are scored on the same test students with G3 > 0. The selected "
            "hyperparameters are reused. Exploratory only: G3 = 0 students remain in every "
            "reported result."
        ),
    )


def _specs(task: Task, config: TrainingConfig) -> tuple[ModelSpec, ...]:
    specs = MODELS[task]
    if config.models is not None:
        specs = tuple(s for s in specs if s.baseline or s.key in config.models)
    return specs


def train_cohort(
    dataset: AnalyticalDataset,
    config: TrainingConfig | None = None,
    *,
    scenarios: tuple[Scenario, ...] = tuple(Scenario),
    tasks: tuple[Task, ...] = tuple(Task),
    on_fold: FoldHook | None = None,
) -> TrainedCohort:
    config = config or TrainingConfig()
    cohort = str(dataset.cohort)
    g3, risk = dataset.regression_target(), dataset.risk_target()
    results: dict[Task, list[ModelResult]] = {Task.REGRESSION: [], Task.CLASSIFICATION: []}
    selections: list[Selection] = []
    selected: dict[tuple[Task, Scenario], Evaluation] = {}
    reg_errors, cls_errors, sensitivity = [], [], []

    split = dataset.split(scenarios[0], random_state=config.random_state)
    for scenario in scenarios:
        split = dataset.split(scenario, random_state=config.random_state)
        for task in tasks:
            y_train, y_test = _targets(split, task)
            evaluations: list[Evaluation] = []
            batch: list[ModelResult] = []
            baseline = None
            for spec in _specs(task, config):
                ev = evaluate(
                    spec, scenario, split.X_train, y_train, split.X_test, y_test, config, on_fold
                )
                result = _result(cohort, ev, split, config, baseline)
                if spec.baseline:
                    baseline = result
                evaluations.append(ev)
                batch.append(result)
            results[task].extend(batch)

            choice = select(batch)
            selections.append(choice)
            chosen = next(e for e in evaluations if e.spec.key == choice.model)
            selected[(task, scenario)] = chosen
            if task is Task.REGRESSION:
                reg_errors.append(
                    regression_errors(cohort, scenario, choice.model, chosen.test_predictions)
                )
                if (item := _zero_grade_sensitivity(cohort, chosen, split)) is not None:
                    sensitivity.append(item)
            else:
                kind = score_kind(chosen.pipeline)
                cls_errors.append(
                    classification_errors(
                        cohort,
                        scenario,
                        choice.model,
                        chosen.test_predictions,
                        g3,
                        threshold=0.5 if kind == "probability" else 0.0,
                        score_kind=kind,
                    )
                )

    return TrainedCohort(
        results=CohortResults(
            cohort=cohort,
            subject=COHORTS[Cohort(cohort)].subject,
            n=len(g3),
            n_train=len(split.X_train),
            n_test=len(split.X_test),
            target=TargetSummary(
                mean=float(g3.mean()),
                std=float(g3.std(ddof=1)),
                median=float(g3.median()),
                minimum=int(g3.min()),
                maximum=int(g3.max()),
                zero_count=int((g3 == 0).sum()),
            ),
            risk={
                "all": _balance(risk),
                "train": _balance(split.y_train_risk),
                "test": _balance(split.y_test_risk),
            },
            regression=results[Task.REGRESSION],
            classification=results[Task.CLASSIFICATION],
            selections=selections,
            regression_errors=reg_errors,
            classification_errors=cls_errors,
            zero_grade_sensitivity=sensitivity,
        ),
        selected=selected,
    )
