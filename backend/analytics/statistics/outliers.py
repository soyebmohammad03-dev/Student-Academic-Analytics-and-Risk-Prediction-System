"""Outlier screening. Values are flagged, never removed: a value outside the fences is
not an error unless it is impossible, and validation already rules impossible values out."""

from __future__ import annotations

import numpy as np
import pandas as pd

from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.statistics.config import IQR_MULTIPLIER, Z_THRESHOLD
from analytics.statistics.core import finite
from analytics.statistics.models import OutlierReport, Outliers, ValueCount

OUTLIER_VARIABLES = ("age", "absences", "G1", "G2", "G3")
EXCLUDED = {
    "failures": "Most students have 0 failures, so Q1 = Q3 = 0 and every non-zero count "
    "would be flagged; the IQR rule is not meaningful.",
    "ordinal codes": (
        "Bounded 1–4 / 1–5 / 0–4 scales cannot contain outliers in a meaningful sense."
    ),
}


def screen(values: pd.Series, name: str) -> OutlierReport:
    x = values.astype(float)
    q1, q3 = np.percentile(x, [25, 75])
    iqr = q3 - q1
    low, high = q1 - IQR_MULTIPLIER * iqr, q3 + IQR_MULTIPLIER * iqr
    below, above = int((x < low).sum()), int((x > high).sum())
    std = x.std(ddof=1)
    z_count = int((((x - x.mean()) / std).abs() > Z_THRESHOLD).sum()) if std > 0 else 0
    flagged = x[(x < low) | (x > high)].astype(int).value_counts().sort_index()
    return OutlierReport(
        variable=name,
        label=COLUMNS_BY_NAME[name].label,
        n=len(x),
        q1=finite(q1),
        q3=finite(q3),
        iqr=finite(iqr),
        lower_fence=finite(low),
        upper_fence=finite(high),
        below=below,
        above=above,
        count=below + above,
        proportion=(below + above) / len(x),
        z_count=z_count,
        flagged_values=[ValueCount(value=int(v), count=int(c)) for v, c in flagged.items()],
    )


def outliers(data: pd.DataFrame, cohort: str) -> Outliers:
    return Outliers(
        cohort=cohort,
        method=(
            f"Tukey fences (Q1 − {IQR_MULTIPLIER}·IQR, Q3 + {IQR_MULTIPLIER}·IQR) and |z| > "
            f"{Z_THRESHOLD}"
        ),
        items=[screen(data[v], v) for v in OUTLIER_VARIABLES],
        excluded=EXCLUDED,
    )
