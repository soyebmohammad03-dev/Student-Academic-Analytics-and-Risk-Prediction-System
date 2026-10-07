"""Statistical analysis and exploratory data analysis (Phase 4).

All functions take the analytical frame from ``analytics.preprocessing`` (validated
values plus ``at_risk``). No rows are removed, including students with ``G3 = 0``.
Results describe associations in observational data and are never causal claims.
"""

from analytics.statistics.association import associate, associations
from analytics.statistics.comparisons import compare_groups
from analytics.statistics.correlation import correlate, correlations, spearman_matrix
from analytics.statistics.descriptive import describe
from analytics.statistics.distributions import distributions
from analytics.statistics.eda import eda
from analytics.statistics.groups import ASSOCIATION_VARIABLES, COMPARISON_VARIABLES, GROUPINGS
from analytics.statistics.outliers import outliers
from analytics.statistics.research import QUESTIONS, research_questions

__all__ = [
    "ASSOCIATION_VARIABLES",
    "COMPARISON_VARIABLES",
    "GROUPINGS",
    "QUESTIONS",
    "associate",
    "associations",
    "compare_groups",
    "correlate",
    "correlations",
    "describe",
    "distributions",
    "eda",
    "outliers",
    "research_questions",
    "spearman_matrix",
]
