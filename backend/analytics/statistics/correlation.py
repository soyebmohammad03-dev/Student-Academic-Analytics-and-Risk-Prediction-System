"""Correlation analysis.

Method rule (fixed in advance):

- **Spearman** when either variable is an ordinal code or a bounded count (from the data
  dictionary), or when normality of either variable is rejected (Shapiro–Wilk).
- **Pearson** only when both are interval-scaled and normality is not rejected.

Both coefficients are always reported, so the choice is transparent.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats

from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.statistics.config import ALPHA
from analytics.statistics.core import (
    benjamini_hochberg,
    correlation_ci,
    finite,
    holm,
    label_correlation,
)
from analytics.statistics.models import Correlation, CorrelationMatrix, Correlations, Interval

KEY_PAIRS: tuple[tuple[str, str], ...] = (
    ("studytime", "G3"),
    ("absences", "G3"),
    ("failures", "G3"),
    ("age", "G3"),
    ("G1", "G3"),
    ("G2", "G3"),
)

MATRIX_VARIABLES: tuple[str, ...] = (
    "age", "Medu", "Fedu", "traveltime", "studytime", "failures", "famrel", "freetime",
    "goout", "Dalc", "Walc", "health", "absences", "G1", "G2", "G3",
)  # fmt: skip


def _label(name: str) -> str:
    spec = COLUMNS_BY_NAME.get(name)
    return spec.label if spec else name


def choose_method(x: pd.Series, y: pd.Series, x_name: str, y_name: str) -> tuple[str, str]:
    for name in (x_name, y_name):
        spec = COLUMNS_BY_NAME.get(name)
        if spec and spec.scale == "ordinal":
            return "spearman", f"{name} is an ordinal code."
        if spec and spec.scale == "count" and name != "age":
            return "spearman", f"{name} is a bounded, skewed count."
    for name, values in ((x_name, x), (y_name, y)):
        if stats.shapiro(values.astype(float)).pvalue < ALPHA:
            return "spearman", f"Normality of {name} is rejected (Shapiro–Wilk)."
    return "pearson", "Both variables are interval-scaled and normality is not rejected."


def _interpret(r: float, x_label: str, y_label: str, method: str) -> str:
    strength = label_correlation(r)
    if strength == "negligible":
        return f"Negligible {method} association between {x_label.lower()} and {y_label.lower()}."
    direction = "higher" if r > 0 else "lower"
    return (
        f"A {strength} {'positive' if r > 0 else 'negative'} association: students with "
        f"higher {x_label.lower()} tend to have {direction} {y_label.lower()}. "
        "This is an association, not evidence of cause."
    )


def correlate(data: pd.DataFrame, x_name: str, y_name: str) -> Correlation:
    pair = data[[x_name, y_name]].dropna().astype(float)
    x, y = pair[x_name], pair[y_name]
    n = len(pair)
    method, reason = choose_method(x, y, x_name, y_name)
    spearman = stats.spearmanr(x, y)
    pearson = stats.pearsonr(x, y)
    r, p = (
        (spearman.statistic, spearman.pvalue)
        if method == "spearman"
        else (pearson.statistic, pearson.pvalue)
    )
    low, high = correlation_ci(float(r), n, method)
    return Correlation(
        x=x_name,
        y=y_name,
        x_label=_label(x_name),
        y_label=_label(y_name),
        method=method,
        method_reason=reason,
        r=finite(r),
        r_ci=Interval(low=finite(low), high=finite(high)),
        p=finite(p),
        n=n,
        strength=label_correlation(float(r)),
        direction="none"
        if label_correlation(float(r)) == "negligible"
        else ("positive" if r > 0 else "negative"),
        interpretation=_interpret(float(r), _label(x_name), _label(y_name), method),
        pearson_r=finite(pearson.statistic),
        spearman_r=finite(spearman.statistic),
    )


def spearman_matrix(data: pd.DataFrame, variables=MATRIX_VARIABLES) -> CorrelationMatrix:
    frame = data[list(variables)].astype(float)
    result = stats.spearmanr(frame)
    r = result.statistic
    p = result.pvalue
    k = len(variables)
    upper = [(i, j) for i in range(k) for j in range(i + 1, k)]
    adjusted = benjamini_hochberg([p[i][j] for i, j in upper])
    p_adj = [[0.0 if i == j else None for j in range(k)] for i in range(k)]
    for (i, j), value in zip(upper, adjusted, strict=True):
        p_adj[i][j] = p_adj[j][i] = finite(value)
    return CorrelationMatrix(
        method="spearman",
        variables=list(variables),
        labels=[_label(v) for v in variables],
        r=[[finite(r[i][j]) for j in range(k)] for i in range(k)],
        p_adjusted=p_adj,
        n=len(frame),
    )


def correlations(data: pd.DataFrame, cohort: str) -> Correlations:
    pairs = [correlate(data, x, y) for x, y in KEY_PAIRS]
    for pair, adjusted in zip(pairs, holm([c.p for c in pairs]), strict=True):
        pair.p_adjusted = finite(adjusted)
    nonzero = data[data["G3"] > 0]
    return Correlations(
        cohort=cohort,
        key_pairs=pairs,
        key_pairs_correction="Holm across the six key pairs",
        sensitivity_key_pairs=[correlate(nonzero, x, y) for x, y in KEY_PAIRS],
        matrix=spearman_matrix(data),
    )
