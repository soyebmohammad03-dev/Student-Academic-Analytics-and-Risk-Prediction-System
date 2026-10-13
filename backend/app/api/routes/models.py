from typing import Annotated

from fastapi import APIRouter, Query

from analytics.data import Cohort
from analytics.ml import comparison
from analytics.ml.config import Task
from analytics.ml.predict import PredictionResult
from analytics.ml.results import ModelResult
from analytics.preprocessing import Scenario
from app.api.deps import ModelStoreDep
from app.schemas.dataset import ErrorResponse
from app.schemas.models import ModelCatalog, PredictionRequest, SelectedModelDetail

CohortQuery = Annotated[Cohort, Query(description="Which cohort.")]
TaskQuery = Annotated[Task, Query(description="regression (G3) or classification (at_risk).")]
ScenarioQuery = Annotated[Scenario, Query(description="Feature scenario.")]

_unavailable = {"model": ErrorResponse, "description": "Models have not been trained"}
router = APIRouter(
    prefix="/models",
    responses={
        422: {"model": ErrorResponse, "description": "Invalid request"},
        503: _unavailable,
    },
)


@router.get("", response_model=ModelCatalog)
def catalog(store: ModelStoreDep):
    """Model definitions and search spaces, plus the selected model per cohort/task/scenario."""
    return store.catalog()


@router.get("/regression", response_model=comparison.RegressionTable)
def regression(store: ModelStoreDep, cohort: CohortQuery):
    """G3 regression: CV (mean ± SD) and test MAE, RMSE and R² for every scenario and model."""
    return comparison.regression_table(store.results(), cohort)


@router.get("/classification", response_model=comparison.ClassificationTable)
def classification(store: ModelStoreDep, cohort: CohortQuery):
    """Academic-risk classification: CV F1/ROC-AUC and test metrics for every model."""
    return comparison.classification_table(store.results(), cohort)


@router.get("/evaluations", response_model=list[ModelResult])
def evaluations(
    store: ModelStoreDep, cohort: CohortQuery, task: TaskQuery, scenario: ScenarioQuery
):
    """Full records: per-fold scores, chosen parameters, confusion matrix and diagnostics."""
    c = store.results().cohort(str(cohort))
    items = c.regression if task is Task.REGRESSION else c.classification
    return [r for r in items if r.scenario is scenario]


@router.get("/scenario-comparison", response_model=comparison.ScenarioComparison)
def scenario_comparison(store: ModelStoreDep, cohort: CohortQuery, task: TaskQuery):
    """Selected model per scenario (early → mid-year → full history) against the baseline."""
    return comparison.scenario_comparison(store.results(), cohort, task)


@router.get("/cohort-comparison", response_model=comparison.CohortComparison)
def cohort_comparison(store: ModelStoreDep):
    """Sample sizes, target and risk distributions, and selected models for both cohorts."""
    return comparison.cohort_comparison(store.results())


@router.get("/selected", response_model=SelectedModelDetail)
def selected(store: ModelStoreDep, cohort: CohortQuery, task: TaskQuery, scenario: ScenarioQuery):
    """Metadata, selection rationale and test-set error analysis of a persisted model."""
    return store.selected(cohort, task, scenario)


@router.post(
    "/predict",
    response_model=PredictionResult,
    responses={404: {"model": ErrorResponse, "description": "Model not persisted"}},
)
def predict(store: ModelStoreDep, request: PredictionRequest):
    """Predict G3 or academic risk for one validated feature record."""
    return store.predictions.predict(
        request.cohort, request.task, request.scenario, request.features, request.model
    )
