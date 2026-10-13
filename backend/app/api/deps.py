"""Shared FastAPI dependencies.

One ``AnalyticsPipeline`` per (data directory, models directory) owns every cache. The
stores below are thin API views over it.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from analytics.pipeline import AnalyticsPipeline
from app.core.config import Settings, get_settings
from app.services.dataset import DatasetStore, get_store
from app.services.interpretability import RiskService, get_risk_service
from app.services.models import ModelStore, get_model_store

SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def pipeline_for(raw_dir: Path, models_dir: Path) -> AnalyticsPipeline:
    return AnalyticsPipeline(raw_dir, models_dir)


def get_pipeline(settings: SettingsDep) -> AnalyticsPipeline:
    return pipeline_for(settings.raw_data_dir, settings.models_dir)


PipelineDep = Annotated[AnalyticsPipeline, Depends(get_pipeline)]


def get_dataset_store(pipeline: PipelineDep) -> DatasetStore:
    return get_store(pipeline)


def get_models(pipeline: PipelineDep) -> ModelStore:
    return get_model_store(pipeline)


def get_risk(pipeline: PipelineDep) -> RiskService:
    return get_risk_service(pipeline)


DatasetStoreDep = Annotated[DatasetStore, Depends(get_dataset_store)]
ModelStoreDep = Annotated[ModelStore, Depends(get_models)]
RiskServiceDep = Annotated[RiskService, Depends(get_risk)]
