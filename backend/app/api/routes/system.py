"""Readiness, dashboard summary and the integrated pipeline summary."""

from typing import Annotated

from fastapi import APIRouter, Query

from analytics.data import Cohort, DatasetNotFoundError
from analytics.ml.results import ModelArtifactError
from analytics.pipeline import PipelineSummary, Readiness
from analytics.preprocessing import InvalidDatasetError, Scenario
from app.api.deps import PipelineDep
from app.schemas.dataset import ErrorResponse
from app.schemas.system import DashboardDataset, DashboardModels, DashboardSummary

router = APIRouter()

NOTES = [
    "Observed figures (cohort sizes, grades, academic-risk proportions) describe the "
    "historical UCI data: the share of students whose final grade was below 10. They are "
    "not predictions of future risk.",
    "Model figures are evaluation scores of the selected models from their recorded "
    "training run (cross-validation on training data, one held-out test set).",
    "Academic risk means a final grade below 10; the dataset contains no dropout outcome.",
]


@router.get("/ready", response_model=Readiness)
def ready(pipeline: PipelineDep):
    """Which analytical components are available. The API itself is always operational
    when this responds; `degraded` means some artefacts are missing or stale."""
    return pipeline.readiness()


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard(pipeline: PipelineDep):
    """Real figures for the main dashboard; unavailable parts are reported, not invented."""
    readiness = pipeline.readiness()
    states = {c.key: c for c in readiness.components}

    cohorts, dataset_detail = [], states["dataset"].detail
    if states["dataset"].status == "available":
        try:
            cohorts = [pipeline.overview(c) for c in Cohort]
        except (DatasetNotFoundError, InvalidDatasetError):
            cohorts, dataset_detail = [], "The dataset could not be read."

    selected, trained_at = [], None
    models_ok = states["models"].status == "available"
    if models_ok:
        try:
            selected = pipeline.selected_models()
            trained_at = pipeline.ml_results().run.created_at
        except ModelArtifactError:
            models_ok = False
    return DashboardSummary(
        status=readiness.status,
        components=readiness.components,
        dataset=DashboardDataset(available=bool(cohorts), detail=dataset_detail, cohorts=cohorts),
        models=DashboardModels(
            available=models_ok,
            detail=states["models"].detail,
            trained_at=trained_at,
            selected=selected,
        ),
        notes=NOTES,
    )


@router.get(
    "/pipeline/summary",
    response_model=PipelineSummary,
    responses={422: {"model": ErrorResponse, "description": "Invalid query parameters"}},
)
def pipeline_summary(
    pipeline: PipelineDep,
    cohort: Annotated[Cohort, Query(description="Which cohort.")],
    scenario: Annotated[Scenario, Query(description="Feature scenario.")],
):
    """Every analytical step for one cohort and scenario, reporting what is available."""
    return pipeline.summary(cohort, scenario)
