import json

import pytest

from tests.factories import make_varied_rows, write_cohort

ENDPOINTS = [
    "/api/v1/statistics/descriptive",
    "/api/v1/statistics/distributions",
    "/api/v1/statistics/correlations",
    "/api/v1/statistics/hypothesis-tests",
    "/api/v1/statistics/associations",
    "/api/v1/statistics/outliers",
    "/api/v1/eda/charts",
]


@pytest.fixture
def api(client, settings):
    write_cohort(settings.raw_data_dir / "student-mat.csv", make_varied_rows(200, seed=11))
    write_cohort(settings.raw_data_dir / "student-por.csv", make_varied_rows(240, seed=12))
    return client


@pytest.mark.parametrize("cohort", ["math", "portuguese"])
@pytest.mark.parametrize("path", ENDPOINTS)
def test_endpoints_return_json_safe_results(api, path, cohort):
    response = api.get(path, params={"cohort": cohort})

    assert response.status_code == 200
    assert response.json()["cohort"] == cohort
    assert "NaN" not in response.text and "Infinity" not in response.text


def test_descriptive_counts_match_cohort_size(api):
    body = api.get("/api/v1/statistics/descriptive", params={"cohort": "portuguese"}).json()
    assert body["n"] == 240
    assert all(s["n"] == 240 for s in body["numeric"])


def test_group_comparison_endpoint(api):
    body = api.get(
        "/api/v1/statistics/group-comparisons", params={"cohort": "math", "variable": "Medu"}
    ).json()

    assert body["variable"] == "Medu"
    assert sum(g["n"] for g in body["groups"]) == 200
    assert body["test"] in {"One-way ANOVA", "Welch's ANOVA", "Kruskal–Wallis H"}
    assert 0 <= body["p"] <= 1


def test_hypothesis_tests_endpoint_has_adjusted_p_values(api):
    items = api.get("/api/v1/statistics/hypothesis-tests", params={"cohort": "math"}).json()[
        "items"
    ]
    for item in items:
        if item["evidence"] == "confirmatory":
            assert item["p"] <= item["p_adjusted"] <= 1


def test_eda_does_not_return_raw_records(api):
    body = api.get("/api/v1/eda/charts", params={"cohort": "math"}).json()
    assert len(json.dumps(body)) < 200_000
    assert sum(b["count"] for b in body["histograms"][2]["bins"]) == 200


@pytest.mark.parametrize(
    "params",
    [
        {"cohort": "math", "variable": "G3"},
        {"cohort": "math", "variable": "at_risk"},
        {"cohort": "x", "variable": "sex"},
    ],
)
def test_invalid_selection_is_422(api, params):
    response = api.get("/api/v1/statistics/group-comparisons", params=params)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_missing_dataset_is_503(client):
    assert (
        client.get("/api/v1/statistics/descriptive", params={"cohort": "math"}).status_code == 503
    )
