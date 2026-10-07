from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Query

from analytics.data import Cohort
from analytics.statistics import COMPARISON_VARIABLES
from analytics.statistics import models as m
from app.api.deps import DatasetStoreDep
from app.schemas.dataset import ErrorResponse
from app.services.statistics import get_analysis

ComparisonVariable = StrEnum("ComparisonVariable", {v: v for v in COMPARISON_VARIABLES})

CohortQuery = Annotated[Cohort, Query(description="Which cohort to analyse.")]

_errors = {
    422: {"model": ErrorResponse, "description": "Invalid query parameters"},
    503: {"model": ErrorResponse, "description": "Dataset has not been downloaded"},
}
router = APIRouter(prefix="/statistics", responses=_errors)
eda_router = APIRouter(prefix="/eda", responses=_errors)


@router.get("/descriptive", response_model=m.DescriptiveStatistics)
def descriptive(store: DatasetStoreDep, cohort: CohortQuery):
    """Numeric summaries for numerically coded variables; frequencies for categorical ones."""
    return get_analysis(store, cohort).descriptive


@router.get("/distributions", response_model=m.Distributions)
def distributions(store: DatasetStoreDep, cohort: CohortQuery):
    """G1, G2 and G3 distributions, shape, zero grades and the academic-risk proportion."""
    return get_analysis(store, cohort).distributions


@router.get("/correlations", response_model=m.Correlations)
def correlations(store: DatasetStoreDep, cohort: CohortQuery):
    """Key correlations with G3 (Holm-adjusted), a sensitivity view and a Spearman matrix."""
    return get_analysis(store, cohort).correlations


@router.get("/hypothesis-tests", response_model=m.ResearchQuestions)
def hypothesis_tests(store: DatasetStoreDep, cohort: CohortQuery):
    """Research questions with pre-specified tests, adjusted p-values and effect sizes."""
    return get_analysis(store, cohort).research_questions


@router.get("/group-comparisons", response_model=m.GroupComparison)
def group_comparison(
    store: DatasetStoreDep,
    cohort: CohortQuery,
    variable: Annotated[ComparisonVariable, Query(description="Grouping variable.")],
):
    """G3 compared across the groups of one variable, with assumption checks and post-hoc tests."""
    return get_analysis(store, cohort).comparison(str(variable))


@router.get("/associations", response_model=m.Associations)
def associations(store: DatasetStoreDep, cohort: CohortQuery):
    """Chi-square / Fisher tests between categorical variables and academic risk."""
    return get_analysis(store, cohort).associations


@router.get("/outliers", response_model=m.Outliers)
def outliers(store: DatasetStoreDep, cohort: CohortQuery):
    """IQR and z-score screening. Values are flagged, never removed."""
    return get_analysis(store, cohort).outliers


@eda_router.get("/charts", response_model=m.Eda)
def charts(store: DatasetStoreDep, cohort: CohortQuery):
    """Chart-ready univariate, bivariate and multivariate data (aggregated, no raw records)."""
    return get_analysis(store, cohort).eda
