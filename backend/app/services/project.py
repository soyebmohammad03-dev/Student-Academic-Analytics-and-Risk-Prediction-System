"""Project metadata and module status.

Module statuses are declared here rather than inferred, so the frontend never implies
that an analysis exists before it has actually been implemented.
"""

from analytics.data import COHORTS
from app import __version__
from app.core.config import Settings
from app.schemas.project import AnalyticsModule, DatasetStatus, ProjectInfo

DATASET_NAME = "UCI Student Performance"
DATASET_URL = "https://archive.ics.uci.edu/dataset/320/student+performance"
DATASET_FILES = tuple(info.filename for info in COHORTS.values())

MODULES: tuple[AnalyticsModule, ...] = (
    AnalyticsModule(key="data", name="Data Explorer", phase=2, status="available"),
    AnalyticsModule(key="statistics", name="Statistical Analysis", phase=4, status="planned"),
    AnalyticsModule(key="eda", name="Exploratory Data Analysis", phase=4, status="planned"),
    AnalyticsModule(key="prediction", name="Prediction", phase=6, status="planned"),
    AnalyticsModule(key="models", name="Model Comparison", phase=5, status="planned"),
    AnalyticsModule(key="risk", name="Risk Analysis", phase=6, status="planned"),
)


def dataset_available(settings: Settings) -> bool:
    return all((settings.raw_data_dir / name).is_file() for name in DATASET_FILES)


def get_project_info(settings: Settings) -> ProjectInfo:
    return ProjectInfo(
        name=settings.project_name,
        version=__version__,
        dataset=DatasetStatus(
            name=DATASET_NAME,
            source_url=DATASET_URL,
            available_locally=dataset_available(settings),
        ),
        modules=list(MODULES),
    )
