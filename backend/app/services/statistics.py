"""Statistical results for the API, computed once per cohort version and cached."""

from __future__ import annotations

import threading
from functools import cached_property

import pandas as pd

from analytics import statistics as stats
from analytics.data import Cohort
from analytics.preprocessing import prepare_cohort
from analytics.statistics import models as m
from app.services.dataset import CohortEntry, DatasetStore


class CohortAnalysis:
    """Lazily computed analyses for one validated cohort."""

    def __init__(self, cohort: Cohort, entry: CohortEntry):
        self.cohort = str(cohort)
        self.data: pd.DataFrame = prepare_cohort(entry.loaded, entry.report).analytical
        self._comparisons: dict[str, m.GroupComparison] = {}
        self._lock = threading.Lock()

    @cached_property
    def descriptive(self) -> m.DescriptiveStatistics:
        return stats.describe(self.data, self.cohort)

    @cached_property
    def distributions(self) -> m.Distributions:
        return stats.distributions(self.data, self.cohort)

    @cached_property
    def correlations(self) -> m.Correlations:
        return stats.correlations(self.data, self.cohort)

    @cached_property
    def research_questions(self) -> m.ResearchQuestions:
        return stats.research_questions(self.data, self.cohort)

    @cached_property
    def associations(self) -> m.Associations:
        return stats.associations(self.data, self.cohort)

    @cached_property
    def outliers(self) -> m.Outliers:
        return stats.outliers(self.data, self.cohort)

    @cached_property
    def eda(self) -> m.Eda:
        return stats.eda(self.data, self.cohort)

    def comparison(self, variable: str) -> m.GroupComparison:
        with self._lock:
            if variable not in self._comparisons:
                self._comparisons[variable] = stats.compare_groups(self.data, variable)
            return self._comparisons[variable]


_cache: dict[Cohort, tuple[CohortEntry, CohortAnalysis]] = {}
_lock = threading.Lock()


def get_analysis(store: DatasetStore, cohort: Cohort) -> CohortAnalysis:
    """Rebuilds when the underlying cohort entry changes (e.g. after a re-download)."""
    entry = store.get(cohort)
    with _lock:
        cached = _cache.get(cohort)
        if cached is None or cached[0] is not entry:
            cached = (entry, CohortAnalysis(cohort, entry))
            _cache[cohort] = cached
        return cached[1]
