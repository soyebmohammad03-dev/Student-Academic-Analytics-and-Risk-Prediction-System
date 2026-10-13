"""Statistical results for the API.

Analyses are computed lazily, once per cohort version, by the pipeline's
``CohortAnalysis`` (``analytics/statistics/analysis.py``).
"""

from __future__ import annotations

from analytics.data import Cohort
from analytics.statistics.analysis import CohortAnalysis
from app.services.dataset import DatasetStore


def get_analysis(store: DatasetStore, cohort: Cohort) -> CohortAnalysis:
    return store.get(cohort).version.statistics
