"""Target construction.

Two targets are derived from the final grade ``G3``:

- **Regression target** ``G3``: the final grade itself (integer, 0–20).
- **Classification target** ``at_risk``: 1 when ``G3 < RISK_THRESHOLD`` (below the pass
  mark of 10), else 0. This is *academic risk* — the risk of not passing the final
  evaluation. The dataset contains no dropout outcome and this is not a dropout label.

Both are outcomes. Neither may appear among predictor columns (see ``scenarios``).
"""

from __future__ import annotations

import pandas as pd

from analytics.preprocessing.config import RISK_THRESHOLD

REGRESSION_TARGET = "G3"
RISK_LABEL = "at_risk"
#: Every column that is, or is derived from, the outcome. Never a predictor.
TARGET_COLUMNS: frozenset[str] = frozenset({REGRESSION_TARGET, RISK_LABEL})


def regression_target(data: pd.DataFrame) -> pd.Series:
    return data[REGRESSION_TARGET].astype("int64").rename(REGRESSION_TARGET)


def risk_label(data: pd.DataFrame, threshold: int = RISK_THRESHOLD) -> pd.Series:
    """1 = at academic risk (final grade below the pass mark), 0 = not at risk."""
    return (data[REGRESSION_TARGET] < threshold).astype("int64").rename(RISK_LABEL)
