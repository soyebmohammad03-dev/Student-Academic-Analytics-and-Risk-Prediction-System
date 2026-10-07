import pytest

from tests.factories import make_varied_rows, write_cohort


@pytest.fixture
def api(client, settings):
    write_cohort(settings.raw_data_dir / "student-mat.csv", make_varied_rows(80, seed=3))
    write_cohort(settings.raw_data_dir / "student-por.csv", make_varied_rows(60, seed=4))
    return client


@pytest.mark.parametrize(("cohort", "rows"), [("math", 80), ("portuguese", 60)])
def test_summary_reports_shapes_targets_and_split(api, cohort, rows):
    body = api.get("/api/v1/preprocessing/summary", params={"cohort": cohort}).json()

    assert body["scenario"]["key"] == "early"
    assert body["original_shape"] == [rows, 33]
    assert body["analytical_shape"] == [rows, 36]
    assert body["rows_removed"] == 0
    assert body["risk"]["at_risk"] + body["risk"]["not_at_risk"] == rows
    assert body["split"]["train_rows"] + body["split"]["test_rows"] == rows
    assert "dropout" in body["risk_definition"]  # explicitly disclaimed
    assert not {"G1", "G2", "G3", "at_risk"} & set(body["encoded_features"])


def test_full_history_scenario_includes_prior_grades(api):
    body = api.get(
        "/api/v1/preprocessing/summary", params={"cohort": "math", "scenario": "full_history"}
    ).json()

    assert {"G1", "G2"} <= set(body["encoded_features"])
    assert "G3" not in body["encoded_features"]


def test_invalid_scenario_is_a_clear_422(api):
    response = api.get(
        "/api/v1/preprocessing/summary", params={"cohort": "math", "scenario": "with_g3"}
    )
    assert response.status_code == 422
    assert "full_history" in response.json()["detail"]


def test_missing_dataset_is_503(client):
    response = client.get("/api/v1/preprocessing/summary", params={"cohort": "math"})
    assert response.status_code == 503
