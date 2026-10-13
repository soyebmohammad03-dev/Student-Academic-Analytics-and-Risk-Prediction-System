"""Evaluation metrics.

Regression: MAE, MSE, RMSE and R² on the 0–20 grade scale.

Classification (positive class = at risk, label 1):

- accuracy, balanced accuracy (mean of recall and specificity)
- precision, recall (sensitivity), specificity, F1 for the at-risk class
- ROC-AUC from continuous scores (``predict_proba`` or ``decision_function``), never
  from hard labels
- the confusion matrix

Undefined values are ``None`` rather than NaN: precision when no student is predicted
at risk, and ROC-AUC when the evaluated students all belong to one class.
"""

from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)

REGRESSION_METRICS = ("mae", "mse", "rmse", "r2")
CLASSIFICATION_METRICS = (
    "accuracy",
    "balanced_accuracy",
    "precision",
    "recall",
    "specificity",
    "f1",
    "roc_auc",
)


def _ratio(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else numerator / denominator


def regression_metrics(y_true, y_pred) -> dict[str, float | None]:
    y_true, y_pred = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    mse = float(mean_squared_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred)) if np.ptp(y_true) > 0 else None
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mse": mse,
        "rmse": math.sqrt(mse),
        "r2": r2,
    }


def confusion(y_true, y_pred) -> dict[str, int]:
    """Counts with at risk (1) as the positive class."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def roc_auc(y_true, scores) -> float | None:
    """ROC-AUC from continuous scores; ``None`` when only one class is present."""
    y_true = np.asarray(y_true)
    if len(np.unique(y_true)) < 2:
        return None
    return float(roc_auc_score(y_true, np.asarray(scores, dtype=float)))


def classification_metrics(y_true, y_pred, scores) -> dict[str, float | None]:
    c = confusion(y_true, y_pred)
    tp, tn, fp, fn = c["tp"], c["tn"], c["fp"], c["fn"]
    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    specificity = _ratio(tn, tn + fp)
    if recall is None:
        f1 = None
    elif tp == 0:
        f1 = 0.0  # positives exist but none was found
    else:
        f1 = 2 * tp / (2 * tp + fp + fn)
    defined = [v for v in (recall, specificity) if v is not None]
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": sum(defined) / len(defined) if defined else None,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "roc_auc": roc_auc(y_true, scores),
    }


def positive_scores(estimator, X) -> np.ndarray:
    """Continuous at-risk scores: P(at risk) where available, else the decision function."""
    if hasattr(estimator, "predict_proba"):
        try:
            proba = estimator.predict_proba(X)
        except AttributeError:  # e.g. SVC without probability=True
            pass
        else:
            classes = list(estimator.classes_)
            if 1 in classes:
                return proba[:, classes.index(1)]
            return np.zeros(len(X))  # the model never saw an at-risk student
    if hasattr(estimator, "decision_function"):
        return np.asarray(estimator.decision_function(X), dtype=float)
    raise TypeError(f"{type(estimator).__name__} provides no continuous scores.")


def score_kind(estimator) -> str:
    try:
        estimator.predict_proba  # noqa: B018 — attribute probe
    except AttributeError:
        return "decision_function"
    return "probability"
