def test_project_info_reports_identity(client):
    body = client.get("/api/v1/project").json()

    assert body["name"] == "Student Academic Analytics and Risk Prediction System"
    assert body["dataset"]["name"] == "UCI Student Performance"


def test_dataset_reported_missing_when_not_downloaded(client):
    body = client.get("/api/v1/project").json()

    assert body["dataset"]["available_locally"] is False


def test_dataset_reported_available_when_files_present(client, settings):
    settings.raw_data_dir.mkdir(parents=True)
    for name in ("student-mat.csv", "student-por.csv"):
        (settings.raw_data_dir / name).write_text("school;sex\n")

    body = client.get("/api/v1/project").json()

    assert body["dataset"]["available_locally"] is True


def test_modules_match_the_delivered_frontend_pages(client):
    modules = client.get("/api/v1/project").json()["modules"]

    # Every module has a working page since Phase 8; none is planned or in progress.
    assert {m["key"] for m in modules} == {
        "data",
        "statistics",
        "eda",
        "models",
        "prediction",
        "interpretability",
        "risk",
    }
    assert {m["status"] for m in modules} == {"available"}
