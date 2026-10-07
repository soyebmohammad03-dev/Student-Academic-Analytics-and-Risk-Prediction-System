"""Descriptive statistics. Numeric summaries only for numerically coded variables;
nominal variables get frequencies and the mode only."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from analytics.data.dictionary import COLUMNS, COLUMNS_BY_NAME
from analytics.statistics.config import IQR_MULTIPLIER
from analytics.statistics.core import finite, mean_ci
from analytics.statistics.models import (
    BoxGroup,
    CategoricalSummary,
    CategoryCount,
    DescriptiveStatistics,
    Interval,
    NumericSummary,
    ValueCount,
)

_ORDINAL_NOTE = (
    "Ordinal code: median, mode and quartiles are the primary summaries; the mean treats "
    "codes as equally spaced and is descriptive only."
)


def numeric_summary(values: pd.Series, name: str, label: str | None = None) -> NumericSummary:
    x = values.dropna().astype(float).to_numpy()
    spec = COLUMNS_BY_NAME.get(name)
    n = len(x)
    if n == 0:
        raise ValueError(f"No values for {name}")
    q1, median, q3 = np.percentile(x, [25, 50, 75])
    counts = pd.Series(x).value_counts()
    modes = sorted(counts[counts == counts.max()].index.tolist())
    low, high = mean_ci(x)
    return NumericSummary(
        variable=name,
        label=label or (spec.label if spec else name),
        scale=spec.scale if spec else "derived",
        n=n,
        mean=finite(x.mean()),
        mean_ci=Interval(low=finite(low), high=finite(high)),
        median=finite(median),
        modes=[float(m) for m in modes],
        minimum=finite(x.min()),
        maximum=finite(x.max()),
        range=finite(x.max() - x.min()),
        variance=finite(x.var(ddof=1)) if n > 1 else None,
        std=finite(x.std(ddof=1)) if n > 1 else None,
        q1=finite(q1),
        q3=finite(q3),
        iqr=finite(q3 - q1),
        skewness=finite(stats.skew(x, bias=False)) if n > 2 else None,
        kurtosis=finite(stats.kurtosis(x, bias=False)) if n > 3 else None,
        note=_ORDINAL_NOTE if spec and spec.scale == "ordinal" else None,
    )


def categorical_summary(values: pd.Series, name: str) -> CategoricalSummary:
    spec = COLUMNS_BY_NAME[name]
    present = values.dropna().astype(str)
    counts = present.value_counts()
    n = int(counts.sum())
    categories = [
        CategoryCount(
            value=str(v.code),
            label=v.label,
            count=int(counts.get(str(v.code), 0)),
            percent=100 * counts.get(str(v.code), 0) / n if n else 0.0,
        )
        for v in spec.allowed
    ]
    top = max(c.count for c in categories)
    return CategoricalSummary(
        variable=name,
        label=spec.label,
        scale=spec.scale,
        n=n,
        mode=[c.value for c in categories if c.count == top],
        categories=categories,
    )


def describe(data: pd.DataFrame, cohort: str) -> DescriptiveStatistics:
    numeric = [numeric_summary(data[c.name], c.name) for c in COLUMNS if c.measure == "numerical"]
    categorical = [
        categorical_summary(data[c.name], c.name) for c in COLUMNS if c.measure == "categorical"
    ]
    return DescriptiveStatistics(
        cohort=cohort, n=len(data), numeric=numeric, categorical=categorical
    )


def box_summary(key: str, label: str, y: np.ndarray) -> BoxGroup:
    q1, med, q3 = np.percentile(y, [25, 50, 75])
    low, high = q1 - IQR_MULTIPLIER * (q3 - q1), q3 + IQR_MULTIPLIER * (q3 - q1)
    inside = y[(y >= low) & (y <= high)]
    out = pd.Series(y[(y < low) | (y > high)]).astype(int).value_counts().sort_index()
    return BoxGroup(
        key=key,
        label=label,
        n=len(y),
        whisker_low=finite(inside.min()) if len(inside) else None,
        q1=finite(q1),
        median=finite(med),
        q3=finite(q3),
        whisker_high=finite(inside.max()) if len(inside) else None,
        mean=finite(y.mean()),
        outliers=[ValueCount(value=int(v), count=int(c)) for v, c in out.items()],
    )
