"""Transparent model-selection rule, applied to cross-validation results only.

For each cohort, task and scenario:

1. Take the primary metric's mean over the outer folds of nested cross-validation:
   **RMSE** for regression (error on the grade scale, penalising large misses) and
   **F1 for the at-risk class** for classification (balances recall — finding students
   who will fall below the pass mark — against precision — not flagging students who
   will pass; accuracy is not used because a model that flags nobody is already 67%
   or 85% accurate).
2. Find the best candidate (baselines excluded) and its standard error,
   SE = SD of its fold values / √folds.
3. Every candidate whose mean is within one SE of the best is treated as performing
   equivalently given the fold-to-fold noise ("one-standard-error rule").
4. Among those, choose the simplest model (lowest complexity rank: linear, then tree,
   then distance/kernel, then forest). Simpler models are easier to explain and
   audit, which matters for a model that flags students.

The held-out test set plays no part. Test scores are reported for the chosen model and
for every other model, but they never change the choice.
"""

from __future__ import annotations

import math

from analytics.ml.config import Task
from analytics.ml.results import ModelResult, Selection

PRIMARY_METRIC = {Task.REGRESSION: "rmse", Task.CLASSIFICATION: "f1"}
LOWER_IS_BETTER = {"rmse": True, "mae": True, "mse": True}
METRIC_LABEL = {
    "rmse": "RMSE",
    "mae": "MAE",
    "mse": "MSE",
    "r2": "R²",
    "f1": "F1",
    "roc_auc": "ROC-AUC",
    "recall": "recall",
    "precision": "precision",
    "accuracy": "accuracy",
    "balanced_accuracy": "balanced accuracy",
    "specificity": "specificity",
}


def better(metric: str, a: float, b: float) -> bool:
    return a < b if LOWER_IS_BETTER.get(metric, False) else a > b


def select(results: list[ModelResult]) -> Selection:
    """Apply the rule to the results of one (cohort, task, scenario)."""
    first = results[0]
    task, metric = first.task, PRIMARY_METRIC[first.task]
    candidates = [r for r in results if not r.baseline and r.cv[metric].mean is not None]
    baseline = next((r for r in results if r.baseline), None)
    if not candidates:
        raise ValueError("No candidate model has a defined cross-validation score.")

    lower = LOWER_IS_BETTER.get(metric, False)
    best = min(candidates, key=lambda r: r.cv[metric].mean * (1 if lower else -1))
    summary = best.cv[metric]
    se = (summary.std or 0.0) / math.sqrt(summary.defined_folds)
    bound = summary.mean + se if lower else summary.mean - se
    within = [
        r
        for r in candidates
        if (r.cv[metric].mean <= bound if lower else r.cv[metric].mean >= bound)
    ]
    chosen = min(within, key=lambda r: (r.complexity, r.model))

    baseline_mean = baseline.cv[metric].mean if baseline else None
    beats = baseline_mean is None or better(metric, chosen.cv[metric].mean, baseline_mean)
    name = METRIC_LABEL[metric]
    if chosen is best:
        reason = (
            f"{chosen.label} has the best mean cross-validated {name} "
            f"({chosen.cv[metric].mean:.3f})"
        )
        others = [r.label for r in within if r is not chosen]
        reason += (
            f"; {', '.join(others)} {'is' if len(others) == 1 else 'are'} also within one "
            f"standard error ({se:.3f}) but not simpler."
            if others
            else f"; no other model is within one standard error ({se:.3f})."
        )
    else:
        reason = (
            f"{best.label} has the best mean cross-validated {name} ({summary.mean:.3f}). "
            f"{chosen.label} ({chosen.cv[metric].mean:.3f}) is within one standard error "
            f"({se:.3f}) and is simpler, so it is selected."
        )
    if baseline_mean is not None:
        reason += f" The baseline's cross-validated {name} is {baseline_mean:.3f}" + (
            "." if beats else "; the selected model does not improve on it."
        )
    return Selection(
        cohort=first.cohort,
        task=task,
        scenario=first.scenario,
        model=chosen.model,
        label=chosen.label,
        primary_metric=metric,
        best_model=best.model,
        best_mean=summary.mean,
        tolerance=se,
        within_tolerance=[r.model for r in within],
        beats_baseline=beats,
        baseline_mean=baseline_mean,
        reason=reason,
    )
