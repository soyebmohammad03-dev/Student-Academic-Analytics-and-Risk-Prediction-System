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


def test_no_module_claims_to_be_available_in_phase_1(client):
    modules = client.get("/api/v1/project").json()["modules"]

    assert modules
    assert all(module["status"] == "planned" for module in modules)
