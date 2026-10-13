from typing import Annotated

from fastapi import APIRouter, Query

from analytics.data import Cohort
from analytics.interpret.results import (
    ExplainedPrediction,
    ModelInterpretation,
    ScenarioSensitivity,
    SensitivityCurve,
)
from analytics.ml.config import Task
from analytics.preprocessing import Scenario
from analytics.risk.results import RiskProfiles, SuggestionSet
from app.api.deps import RiskServiceDep
from app.schemas.dataset import ErrorResponse
from app.schemas.interpretability import (
    ExplainRequest,
    RiskInsights,
    RiskRequest,
    ScenarioSensitivityRequest,
    SensitivityRequest,
)

ServiceDep = RiskServiceDep
_errors = {
    404: {"model": ErrorResponse, "description": "Model not persisted"},
    422: {"model": ErrorResponse, "description": "Invalid request or feature record"},
    503: {"model": ErrorResponse, "description": "Dataset or models not available"},
}
router = APIRouter(prefix="/interpretability", responses=_errors)
risk_router = APIRouter(prefix="/risk", responses=_errors)


@router.get("/importance", response_model=ModelInterpretation)
def importance(
    service: ServiceDep,
    cohort: Annotated[Cohort, Query()],
    task: Annotated[Task, Query()],
    scenario: Annotated[Scenario, Query()],
):
    """Global importance of the selected model, one entry per method (never compared)."""
    return service.importance(cohort, task, scenario)


@router.post("/explain", response_model=ExplainedPrediction)
def explain(service: ServiceDep, request: ExplainRequest):
    """Prediction plus Shapley contributions of each attribute (model behaviour, not cause)."""
    return service.interpreter.explain(
        request.cohort,
        request.task,
        request.scenario,
        request.features,
        request.model,
        top=request.top,
    )


@router.post("/sensitivity", response_model=SensitivityCurve)
def sensitivity(service: ServiceDep, request: SensitivityRequest):
    """Model output as one modifiable attribute varies, all other inputs fixed."""
    return service.interpreter.sensitivity(
        request.cohort,
        request.task,
        request.scenario,
        request.features,
        request.attribute,
        request.model,
    )


@router.post("/scenario-sensitivity", response_model=ScenarioSensitivity)
def scenario_sensitivity(service: ServiceDep, request: ScenarioSensitivityRequest):
    """The same record predicted under each scenario its grades allow."""
    return service.interpreter.scenario_sensitivity(request.cohort, request.task, request.features)


@risk_router.get("/profiles", response_model=RiskProfiles)
def profiles(service: ServiceDep, cohort: Annotated[Cohort, Query()]):
    """Observed academic-risk proportions for pre-defined student groups (group-level)."""
    return service.profiles(cohort)


@risk_router.post("/suggestions", response_model=SuggestionSet)
def suggestions(service: ServiceDep, request: RiskRequest):
    """Evidence-checked, non-punitive suggestions for a teacher or adviser to consider."""
    return service.suggestions(request.cohort, request.scenario, request.features)


@risk_router.post("/insights", response_model=RiskInsights)
def insights(service: ServiceDep, request: RiskRequest):
    """Individual explanation, group-level findings and suggestions, kept separate."""
    return service.insights(request.cohort, request.scenario, request.features)
