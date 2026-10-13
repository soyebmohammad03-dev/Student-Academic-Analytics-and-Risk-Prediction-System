"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.dataset import DatasetStore, get_store
from app.services.models import ModelStore, get_model_store

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_dataset_store(settings: SettingsDep) -> DatasetStore:
    return get_store(settings.raw_data_dir)


DatasetStoreDep = Annotated[DatasetStore, Depends(get_dataset_store)]


def get_models(settings: SettingsDep) -> ModelStore:
    return get_model_store(settings.models_dir)


ModelStoreDep = Annotated[ModelStore, Depends(get_models)]
