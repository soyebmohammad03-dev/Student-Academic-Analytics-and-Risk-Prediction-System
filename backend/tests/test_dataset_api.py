import pytest


@pytest.fixture
def api(client, dataset):
    return client


def test_summary_reports_real_counts(api):
    body = api.get("/api/v1/dataset/summary", params={"cohort": "math"}).json()

    assert body["cohort"] == "math"
    assert body["subject"] == "Mathematics"
    assert (body["rows"], body["columns"]) == (30, 33)
    assert (body["numerical_columns"], body["categorical_columns"]) == (16, 17)
    assert body["missing_values"] == body["duplicate_rows"] == body["invalid_values"] == 0
    assert body["target"]["name"] == "G3"
    assert body["target"]["prior_grades"] == ["G1", "G2"]
    assert body["source"]["license"] == "CC BY 4.0"


def test_summary_switches_cohort(api):
    body = api.get("/api/v1/dataset/summary", params={"cohort": "portuguese"}).json()
    assert (body["subject"], body["rows"]) == ("Portuguese language", 12)


def test_schema_combines_dictionary_and_observed_values(api):
    columns = api.get("/api/v1/dataset/schema", params={"cohort": "math"}).json()["columns"]
    by_name = {c["name"]: c for c in columns}

    assert len(columns) == 33
    assert by_name["G3"]["role"] == "target"
    assert by_name["absences"]["observed"] == {
        "missing": 0, "invalid": 0, "unique": 30, "minimum": 0, "maximum": 29,
    }  # fmt: skip
    assert {"code": "yes", "label": "Yes"} in by_name["higher"]["allowed_values"]


def test_quality_lists_checks_and_status(api):
    body = api.get("/api/v1/dataset/quality", params={"cohort": "math"}).json()

    assert body["status"] == "warning"  # synthetic file has fewer rows than published
    assert {c["key"] for c in body["checks"]} >= {"columns", "missing", "duplicates", "grades"}
    assert body["column_issues"] == []


def test_records_paginate(api):
    first = api.get("/api/v1/dataset/records", params={"cohort": "math", "page_size": 10}).json()
    last = api.get(
        "/api/v1/dataset/records", params={"cohort": "math", "page_size": 10, "page": 3}
    ).json()

    assert (first["total"], first["total_pages"], len(first["items"])) == (30, 3, 10)
    assert first["items"][0]["row"] == 1
    assert first["items"][0]["values"]["G3"] == 12
    assert [i["row"] for i in last["items"]] == list(range(21, 31))
    assert len(first["columns"]) == 33


def test_records_page_past_end_is_empty(api):
    body = api.get("/api/v1/dataset/records", params={"cohort": "math", "page": 9}).json()
    assert body["items"] == [] and body["total"] == 30


def test_records_search_is_case_insensitive_substring(api, settings):
    from tests.factories import make_rows, write_cohort

    rows = make_rows(5)
    rows[3]["Fjob"] = "teacher"
    write_cohort(settings.raw_data_dir / "student-mat.csv", rows)

    body = api.get("/api/v1/dataset/records", params={"cohort": "math", "search": " TEACH "}).json()
    assert body["total"] == 1
    assert body["items"][0]["row"] == 4
    assert body["search"] == "teach"


@pytest.mark.parametrize(
    "params",
    [
        {"cohort": "physics"},
        {},
        {"cohort": "math", "page": 0},
        {"cohort": "math", "page_size": 101},
        {"cohort": "math", "search": "x" * 101},
    ],
)
def test_invalid_parameters_return_clear_422(api, params):
    response = api.get("/api/v1/dataset/records", params=params)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_request"
    assert body["detail"]


def test_invalid_cohort_message_names_the_options(api):
    detail = api.get("/api/v1/dataset/summary", params={"cohort": "physics"}).json()["detail"]
    assert "cohort" in detail and "math" in detail and "portuguese" in detail


def test_missing_dataset_returns_503_with_instructions(client):
    response = client.get("/api/v1/dataset/summary", params={"cohort": "math"})

    assert response.status_code == 503
    assert response.json()["code"] == "dataset_unavailable"
    assert "analytics.data.download" in response.json()["detail"]


def test_overlap_reports_method_and_caveat(api):
    body = api.get("/api/v1/dataset/overlap").json()

    assert len(body["match_attributes"]) == 13
    assert body["unambiguous_matches"] == 0  # synthetic cohorts use different schools
    assert "approximate" in body["caveat"].lower()
