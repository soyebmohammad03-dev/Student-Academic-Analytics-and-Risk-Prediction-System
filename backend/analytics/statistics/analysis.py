"""Lazily computed statistical analyses for one cohort version.

Each analysis is computed at most once per instance; the owner (``AnalyticsPipeline``)
creates a new instance whenever the cohort file changes.
"""

from __future__ import annotations

import threading
from functools import cached_property

import pandas as pd

from analytics import statistics as stats
from analytics.statistics import models as m


class CohortAnalysis:
    def __init__(self, cohort: str, data: pd.DataFrame):
        self.cohort = str(cohort)
        self.data = data
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
