"""Numerical building blocks: confidence intervals, effect sizes and p-value adjustment.

Every function is deterministic and verified against hand-computed values in
``tests/test_statistics_core.py``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from scipy import stats

from analytics.statistics.config import CONFIDENCE


def finite(value: float | None) -> float | None:
    """Return ``value`` as float, or None when missing or not finite (JSON-safe)."""
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _z(confidence: float = CONFIDENCE) -> float:
    return float(stats.norm.ppf(0.5 + confidence / 2))


# --- Confidence intervals ---------------------------------------------------------


def mean_ci(values: np.ndarray, confidence: float = CONFIDENCE) -> tuple[float, float]:
    """t-based interval for a mean."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 2:
        return (math.nan, math.nan)
    sem = values.std(ddof=1) / math.sqrt(n)
    half = float(stats.t.ppf(0.5 + confidence / 2, n - 1)) * sem
    return (values.mean() - half, values.mean() + half)


def wilson_ci(successes: int, n: int, confidence: float = CONFIDENCE) -> tuple[float, float]:
    """Wilson score interval for a proportion (well-behaved near 0 and 1)."""
    if n == 0:
        return (math.nan, math.nan)
    z = _z(confidence)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (centre - half, centre + half)


def correlation_ci(
    r: float, n: int, method: str, confidence: float = CONFIDENCE
) -> tuple[float, float]:
    """Fisher z interval. Spearman uses the Bonett–Wright (2000) standard error."""
    if n <= 3 or not math.isfinite(r) or abs(r) >= 1:
        return (math.nan, math.nan)
    se = math.sqrt((1 + r**2 / 2) / (n - 3)) if method == "spearman" else 1 / math.sqrt(n - 3)
    z = math.atanh(r)
    q = _z(confidence)
    return (math.tanh(z - q * se), math.tanh(z + q * se))


def welch_mean_difference_ci(
    a: np.ndarray, b: np.ndarray, confidence: float = CONFIDENCE
) -> tuple[float, float]:
    """Interval for mean(a) − mean(b) with Welch–Satterthwaite degrees of freedom."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    df = (va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1))
    half = float(stats.t.ppf(0.5 + confidence / 2, df)) * math.sqrt(va + vb)
    diff = a.mean() - b.mean()
    return (diff - half, diff + half)


# --- Effect sizes -------------------------------------------------------------------


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """Standardised mean difference (a − b) using the pooled standard deviation."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    n1, n2 = len(a), len(b)
    pooled = math.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    return (a.mean() - b.mean()) / pooled if pooled > 0 else math.nan


def cohens_d_ci(d: float, n1: int, n2: int, confidence: float = CONFIDENCE) -> tuple[float, float]:
    """Large-sample normal approximation (Hedges & Olkin, 1985)."""
    se = math.sqrt((n1 + n2) / (n1 * n2) + d**2 / (2 * (n1 + n2)))
    q = _z(confidence)
    return (d - q * se, d + q * se)


def rank_biserial(u_statistic: float, n1: int, n2: int) -> float:
    """From the Mann–Whitney U of the first group: positive when group 1 tends higher."""
    return 2 * u_statistic / (n1 * n2) - 1


def eta_squared(groups: Sequence[np.ndarray]) -> float:
    """SS_between / SS_total."""
    values = np.concatenate([np.asarray(g, float) for g in groups])
    grand = values.mean()
    ss_total = ((values - grand) ** 2).sum()
    ss_between = sum(len(g) * (np.mean(g) - grand) ** 2 for g in groups)
    return ss_between / ss_total if ss_total > 0 else math.nan


def omega_squared(groups: Sequence[np.ndarray]) -> float:
    """Less biased than eta squared for one-way ANOVA."""
    values = np.concatenate([np.asarray(g, float) for g in groups])
    n, k = len(values), len(groups)
    grand = values.mean()
    ss_total = ((values - grand) ** 2).sum()
    ss_between = sum(len(g) * (np.mean(g) - grand) ** 2 for g in groups)
    ms_within = (ss_total - ss_between) / (n - k)
    denom = ss_total + ms_within
    return (ss_between - (k - 1) * ms_within) / denom if denom > 0 else math.nan


def eta_squared_h(h: float, n: int, k: int) -> float:
    """Effect size for Kruskal–Wallis: (H − k + 1) / (n − k) (Tomczak & Tomczak, 2014)."""
    return (h - k + 1) / (n - k)


def cramers_v(chi2: float, n: int, rows: int, cols: int) -> float:
    return math.sqrt(chi2 / (n * (min(rows, cols) - 1))) if n and min(rows, cols) > 1 else math.nan


# --- Interpretation labels (conventional benchmarks; context matters) ---------------


def label_correlation(r: float) -> str:
    """Cohen (1988): 0.1 small, 0.3 medium, 0.5 large."""
    a = abs(r)
    return "negligible" if a < 0.1 else "weak" if a < 0.3 else "moderate" if a < 0.5 else "strong"


def label_d(d: float) -> str:
    """Cohen (1988): 0.2 small, 0.5 medium, 0.8 large."""
    a = abs(d)
    return "negligible" if a < 0.2 else "small" if a < 0.5 else "medium" if a < 0.8 else "large"


def label_eta(eta: float) -> str:
    """Cohen (1988): 0.01 small, 0.06 medium, 0.14 large."""
    return (
        "negligible"
        if eta < 0.01
        else "small"
        if eta < 0.06
        else "medium"
        if eta < 0.14
        else "large"
    )


def label_cramers_v(v: float, rows: int, cols: int) -> str:
    """Cohen's w benchmarks scaled by sqrt(min(r, c) − 1)."""
    df = min(rows, cols) - 1
    small, medium, large = (x / math.sqrt(df) for x in (0.1, 0.3, 0.5))
    return (
        "negligible" if v < small else "small" if v < medium else "medium" if v < large else "large"
    )


# --- Multiple comparisons ---------------------------------------------------------------


def holm(p_values: Sequence[float]) -> list[float]:
    """Holm–Bonferroni step-down adjustment (controls the family-wise error rate)."""
    p = np.asarray(p_values, float)
    m = len(p)
    order = np.argsort(p)
    adjusted = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[idx]))
        adjusted[idx] = running
    return adjusted.tolist()


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """Benjamini–Hochberg adjustment (controls the false discovery rate)."""
    if len(p_values) == 0:
        return []
    return stats.false_discovery_control(np.asarray(p_values, float), method="bh").tolist()


# --- Omnibus and post-hoc procedures not provided by SciPy ------------------------------


def welch_anova(groups: Sequence[np.ndarray]) -> tuple[float, float, float, float]:
    """Welch's heteroscedastic one-way ANOVA. Returns (F, df1, df2, p)."""
    k = len(groups)
    n = np.array([len(g) for g in groups], float)
    means = np.array([np.mean(g) for g in groups])
    variances = np.array([np.var(g, ddof=1) for g in groups])
    w = n / variances
    weighted_mean = (w * means).sum() / w.sum()
    a = (w * (means - weighted_mean) ** 2).sum() / (k - 1)
    tmp = (((1 - w / w.sum()) ** 2) / (n - 1)).sum()
    b = 1 + 2 * (k - 2) / (k**2 - 1) * tmp
    f = a / b
    df1, df2 = k - 1, (k**2 - 1) / (3 * tmp)
    return f, df1, df2, float(stats.f.sf(f, df1, df2))


def games_howell(a: np.ndarray, b: np.ndarray, k: int) -> tuple[float, float]:
    """Games–Howell pairwise test for unequal variances. Returns (mean diff a−b, p)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    df = (va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1))
    diff = a.mean() - b.mean()
    q = abs(diff) / math.sqrt((va + vb) / 2)
    return diff, float(stats.studentized_range.sf(q, k, df))


def dunn(groups: Sequence[np.ndarray]) -> list[tuple[int, int, float, float]]:
    """Dunn's test with tie correction. Returns (i, j, z, unadjusted p) for i < j."""
    values = np.concatenate([np.asarray(g, float) for g in groups])
    n = len(values)
    ranks = stats.rankdata(values)
    _, counts = np.unique(values, return_counts=True)
    tie_term = (counts**3 - counts).sum() / (12 * (n - 1))
    bounds = np.cumsum([0] + [len(g) for g in groups])
    mean_ranks = [ranks[bounds[i] : bounds[i + 1]].mean() for i in range(len(groups))]
    out = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            ni, nj = len(groups[i]), len(groups[j])
            se = math.sqrt((n * (n + 1) / 12 - tie_term) * (1 / ni + 1 / nj))
            z = (mean_ranks[i] - mean_ranks[j]) / se
            out.append((i, j, z, float(2 * stats.norm.sf(abs(z)))))
    return out
