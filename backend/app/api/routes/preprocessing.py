from typing import Annotated

from fastapi import APIRouter, Query

from analytics.data import Cohort
from analytics.preprocessing import Scenario
from app.api.deps import DatasetStoreDep
from app.schemas.dataset import ErrorResponse
from app.schemas.preprocessing import PreprocessingSummary
from app.services.preprocessing import preprocessing_summary

router = APIRouter(
    prefix="/preprocessing",
    responses={
        422: {"model": ErrorResponse, "description": "Invalid query parameters"},
        503: {"model": ErrorResponse, "description": "Dataset has not been downloaded"},
    },
)


@router.get("/summary", response_model=PreprocessingSummary)
def summary(
    store: DatasetStoreDep,
    cohort: Annotated[Cohort, Query(description="Which cohort to preprocess.")],
    scenario: Annotated[Scenario, Query(description="Feature scenario.")] = Scenario.EARLY,
) -> PreprocessingSummary:
    return preprocessing_summary(store, cohort, scenario)
