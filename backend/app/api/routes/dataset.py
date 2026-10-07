from typing import Annotated

from fastapi import APIRouter, Query

from analytics.data import Cohort
from app.api.deps import DatasetStoreDep
from app.schemas.dataset import (
    CohortOverlap,
    DatasetQuality,
    DatasetRecords,
    DatasetSchema,
    DatasetSummary,
    ErrorResponse,
)

router = APIRouter(
    prefix="/dataset",
    responses={
        422: {"model": ErrorResponse, "description": "Invalid query parameters"},
        503: {"model": ErrorResponse, "description": "Dataset has not been downloaded"},
    },
)

MAX_PAGE_SIZE = 100

CohortQuery = Annotated[Cohort, Query(description="Which cohort to read.")]


@router.get("/summary", response_model=DatasetSummary)
def summary(store: DatasetStoreDep, cohort: CohortQuery) -> DatasetSummary:
    return store.summary(cohort)


@router.get("/schema", response_model=DatasetSchema)
def schema(store: DatasetStoreDep, cohort: CohortQuery) -> DatasetSchema:
    return store.schema(cohort)


@router.get("/quality", response_model=DatasetQuality)
def quality(store: DatasetStoreDep, cohort: CohortQuery) -> DatasetQuality:
    return store.quality(cohort)


@router.get("/records", response_model=DatasetRecords)
def records(
    store: DatasetStoreDep,
    cohort: CohortQuery,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 25,
    search: Annotated[
        str | None,
        Query(max_length=100, description="Case-insensitive substring match on any value."),
    ] = None,
) -> DatasetRecords:
    return store.records(cohort, page=page, page_size=page_size, search=search)


@router.get("/overlap", response_model=CohortOverlap)
def overlap(store: DatasetStoreDep) -> CohortOverlap:
    return store.overlap()
