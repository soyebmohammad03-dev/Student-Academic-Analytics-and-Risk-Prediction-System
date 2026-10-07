from typing import Literal

from pydantic import BaseModel

ModuleStatus = Literal["planned", "in_progress", "available"]


class AnalyticsModule(BaseModel):
    key: str
    name: str
    phase: int
    status: ModuleStatus


class DatasetStatus(BaseModel):
    name: str
    source_url: str
    available_locally: bool


class ProjectInfo(BaseModel):
    name: str
    version: str
    dataset: DatasetStatus
    modules: list[AnalyticsModule]
