"""Cross-validation, hyperparameter tuning and held-out evaluation for one model.

Protocol for each (cohort, scenario, task, model):

1. **Nested cross-validation on the training set only.** The outer loop has
   ``CV_FOLDS`` folds (``KFold`` for regression, ``StratifiedKFold`` on ``at_risk`` for
   classification, shuffled with the fixed seed). Inside each outer training portion,
   ``GridSearchCV`` with the same kind of splitter chooses hyperparameters; the chosen
   pipeline is then scored on the outer validation fold, which played no part in
   either fitting or tuning. The outer scores therefore estimate the performance of
   the *whole procedure*, tuning included, without the optimism of reporting the best
   grid score.
2. **Final fit.** ``GridSearchCV`` is run once more on the full training set and the
   best pipeline is refitted on all training students.
3. **Test evaluation.** The final pipeline is scored once on the held-out test set.
   Test scores are never used for tuning or model selection.

Preprocessing lives inside the pipeline, so in every fit (outer folds, inner folds and
the final fit) imputers, encoders and scalers learn only from the rows being fitted.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.model_selection import GridSearchCV, KFold, StratifiedKFold
from sklearn.pipeline import Pipeline

from analytics.ml.config import Task, TrainingConfig
from analytics.ml.metrics import (
    CLASSIFICATION_METRICS,
    REGRESSION_METRICS,
    classification_metrics,
    confusion,
    positive_scores,
    regression_metrics,
)
from analytics.ml.registry import ESTIMATOR_STEP, ModelSpec, build_pipeline, search_space
from analytics.ml.results import Confusion, MetricSummary
from analytics.preprocessing import Scenario

#: Metric optimised by the inner grid search.
TUNING_SCORING = {Task.REGRESSION: "neg_root_mean_squared_error", Task.CLASSIFICATION: "f1"}
TUNING_LABEL = {Task.REGRESSION: "RMSE (lower is better)", Task.CLASSIFICATION: "F1 (at risk)"}
METRIC_NAMES = {Task.REGRESSION: REGRESSION_METRICS, Task.CLASSIFICATION: CLASSIFICATION_METRICS}

FoldHook = Callable[[int, BaseEstimator, pd.DataFrame, pd.DataFrame], None]


def splitter(task: Task, config: TrainingConfig) -> KFold | StratifiedKFold:
    cls = StratifiedKFold if Task(task) is Task.CLASSIFICATION else KFold
    return cls(n_splits=config.cv_folds, shuffle=True, random_state=config.random_state)


def describe_splitter(task: Task, config: TrainingConfig) -> str:
    if Task(task) is Task.CLASSIFICATION:
        return (
            f"StratifiedKFold(n_splits={config.cv_folds}, shuffle=True, "
            f"random_state={config.random_state}) on at_risk"
        )
    return f"KFold(n_splits={config.cv_folds}, shuffle=True, random_state={config.random_state})"


def tuned_estimator(
    spec: ModelSpec, scenario: Scenario, config: TrainingConfig
) -> Pipeline | GridSearchCV:
    pipeline = build_pipeline(spec, scenario, config.random_state)
    grid = search_space(spec, config.search)
    if not grid:
        return pipeline
    return GridSearchCV(
        pipeline,
        grid,
        scoring=TUNING_SCORING[spec.task],
        cv=splitter(spec.task, config),
        n_jobs=config.n_jobs,
        refit=True,
        error_score="raise",
    )


def fitted_pipeline(estimator) -> Pipeline:
    return estimator.best_estimator_ if isinstance(estimator, GridSearchCV) else estimator


def chosen_params(estimator) -> dict[str, Any]:
    if not isinstance(estimator, GridSearchCV):
        return {}
    prefix = f"{ESTIMATOR_STEP}__"
    return {k.removeprefix(prefix): v for k, v in sorted(estimator.best_params_.items())}


@dataclass(frozen=True)
class Predictions:
    """Test-set (or fold) predictions with the information needed for error analysis."""

    index: pd.Index
    y_true: np.ndarray
    y_pred: np.ndarray
    scores: np.ndarray | None


def predict(task: Task, pipeline, X: pd.DataFrame, y: pd.Series) -> Predictions:
    if Task(task) is Task.REGRESSION:
        return Predictions(X.index, y.to_numpy(), pipeline.predict(X).astype(float), None)
    # Labels use the estimator's own decision rule (the one grid search optimised):
    # the more probable class, or the sign of the SVM decision function.
    labels = np.asarray(pipeline.predict(X), dtype=int)
    return Predictions(X.index, y.to_numpy(), labels, positive_scores(pipeline, X))


def score(task: Task, predictions: Predictions) -> dict[str, float | None]:
    if Task(task) is Task.REGRESSION:
        return regression_metrics(predictions.y_true, predictions.y_pred)
    return classification_metrics(predictions.y_true, predictions.y_pred, predictions.scores)


def summarise(task: Task, folds: list[dict[str, float | None]]) -> dict[str, MetricSummary]:
    out = {}
    for name in METRIC_NAMES[Task(task)]:
        values = [f[name] for f in folds]
        defined = [v for v in values if v is not None]
        out[name] = MetricSummary(
            mean=statistics.fmean(defined) if defined else None,
            std=statistics.stdev(defined) if len(defined) > 1 else None,
            folds=values,
            defined_folds=len(defined),
        )
    return out


@dataclass
class Evaluation:
    spec: ModelSpec
    scenario: Scenario
    pipeline: Pipeline
    best_params: dict[str, Any]
    outer_fold_params: list[dict[str, Any]]
    candidates: int
    cv: dict[str, MetricSummary]
    test: dict[str, float | None]
    test_predictions: Predictions
    test_confusion: Confusion | None


def nested_cv(
    spec: ModelSpec,
    scenario: Scenario,
    X: pd.DataFrame,
    y: pd.Series,
    config: TrainingConfig,
    on_fold: FoldHook | None = None,
) -> tuple[list[dict[str, float | None]], list[dict[str, Any]]]:
    """Outer-fold metrics and the parameters chosen inside each outer fold."""
    metrics, params = [], []
    for k, (train, valid) in enumerate(splitter(spec.task, config).split(X, y)):
        X_fit, y_fit = X.iloc[train], y.iloc[train]
        X_val, y_val = X.iloc[valid], y.iloc[valid]
        estimator = tuned_estimator(spec, scenario, config).fit(X_fit, y_fit)
        if on_fold:
            on_fold(k, estimator, X_fit, X_val)
        metrics.append(score(spec.task, predict(spec.task, estimator, X_val, y_val)))
        params.append(chosen_params(estimator))
    return metrics, params


def evaluate(
    spec: ModelSpec,
    scenario: Scenario,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    config: TrainingConfig,
    on_fold: FoldHook | None = None,
) -> Evaluation:
    fold_metrics, fold_params = nested_cv(spec, scenario, X_train, y_train, config, on_fold)

    final = tuned_estimator(spec, scenario, config).fit(X_train, y_train)
    pipeline = fitted_pipeline(final)
    predictions = predict(spec.task, pipeline, X_test, y_test)
    grid = search_space(spec, config.search)
    return Evaluation(
        spec=spec,
        scenario=scenario,
        pipeline=pipeline,
        best_params=chosen_params(final),
        outer_fold_params=fold_params,
        candidates=int(np.prod([len(v) for v in grid.values()])) if grid else 1,
        cv=summarise(spec.task, fold_metrics),
        test=score(spec.task, predictions),
        test_predictions=predictions,
        test_confusion=(
            Confusion(**confusion(predictions.y_true, predictions.y_pred))
            if spec.task is Task.CLASSIFICATION
            else None
        ),
    )
