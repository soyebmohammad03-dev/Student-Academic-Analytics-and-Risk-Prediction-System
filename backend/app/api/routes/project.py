from fastapi import APIRouter

from app.api.deps import SettingsDep
from app.schemas.project import ProjectInfo
from app.services.project import get_project_info

router = APIRouter()


@router.get("/project", response_model=ProjectInfo)
def project_info(settings: SettingsDep) -> ProjectInfo:
    return get_project_info(settings)
