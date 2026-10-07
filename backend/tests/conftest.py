import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from tests.factories import make_rows, write_cohort


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(environment="test", data_dir=tmp_path / "data", models_dir=tmp_path / "models")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


@pytest.fixture
def dataset(settings: Settings) -> Settings:
    """Synthetic cohorts: 30 math rows and 12 portuguese rows."""
    write_cohort(settings.raw_data_dir / "student-mat.csv", make_rows(30))
    write_cohort(settings.raw_data_dir / "student-por.csv", make_rows(12, school="MS"))
    return settings
