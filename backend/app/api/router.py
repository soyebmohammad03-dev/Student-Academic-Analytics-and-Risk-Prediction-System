"""Top-level API router. Each analytics module registers its own route module here."""

from fastapi import APIRouter

from app.api.routes import health, project

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(project.router, tags=["project"])
