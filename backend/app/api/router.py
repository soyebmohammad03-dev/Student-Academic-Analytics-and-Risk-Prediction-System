"""Top-level API router. Each analytics module registers its own route module here."""

from fastapi import APIRouter

from app.api.routes import (
    dataset,
    health,
    interpretability,
    models,
    preprocessing,
    project,
    statistics,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(project.router, tags=["project"])
api_router.include_router(dataset.router, tags=["dataset"])
api_router.include_router(preprocessing.router, tags=["preprocessing"])
api_router.include_router(statistics.router, tags=["statistics"])
api_router.include_router(statistics.eda_router, tags=["eda"])
api_router.include_router(models.router, tags=["models"])
api_router.include_router(interpretability.router, tags=["interpretability"])
api_router.include_router(interpretability.risk_router, tags=["risk"])
