import hashlib

import numpy as np
import pandas as pd
import pytest

from analytics.data import Cohort, load_cohort
from analytics.preprocessing import (
    RANDOM_STATE,
    RISK_LABEL,
    InvalidDatasetError,
    LeakageError,
    Scenario,
    assert_no_leakage,
    build_preprocessor,
    build_report,
    feature_columns,
    prepare_cohort,
    risk_label,
)
from tests.factories import make_varied_rows, write_cohort

FILES = {Cohort.MATH: "student-mat.csv", Cohort.PORTUGUESE: "student-por.csv"}


@pytest.fixture(params=list(Cohort), ids=str)
def cohort_dataset(request, tmp_path):
    """A varied synthetic file for each cohort (120 math rows, 160 portuguese rows)."""
    cohort = request.param
    rows = make_varied_rows(120 if cohort is Cohort.MATH else 160, seed=len(str(cohort)))
    path = write_cohort(tmp_path / FILES[cohort], rows)
    return prepare_cohort(load_cohort(tmp_path, cohort)), path


# --- Targets -------------------------------------------------------------------------


@pytest.mark.parametrize(("g3", "expected"), [(0, 1), (9, 1), (10, 0), (11, 0), (20, 0)])
def test_risk_label_is_g3_below_pass_mark(g3, expected):
    assert risk_label(pd.DataFrame({"G3": [g3]})).tolist() == [expected]


def test_targets_are_built_from_g3(cohort_dataset):
    dataset, _ = cohort_dataset
    g3 = dataset.validated["G3"].astype("int64")

    assert dataset.regression_target().tolist() == g3.tolist()
    assert dataset.risk_target().tolist() == (g3 < 10).astype(int).tolist()
    assert dataset.risk_target().name == RISK_LABEL


# --- Analytical data -----------------------------------------------------------------


def test_preprocessing_keeps_every_row_and_never_touches_the_raw_file(cohort_dataset):
    dataset, path = cohort_dataset
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    raw_copy = dataset.raw.copy()

    for scenario in Scenario:
        build_report(dataset, scenario)

    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    pd.testing.assert_frame_equal(dataset.raw, raw_copy)
    assert len(dataset.analytical) == len(dataset.raw)
    assert dataset.analytical.shape[1] == 33 + 2 + 1  # + engineered features + at_risk


def test_engineered_features(cohort_dataset):
    dataset, _ = cohort_dataset
    a = dataset.analytical

    assert a["has_past_failures"].tolist() == (a["failures"] > 0).astype(int).tolist()
    np.testing.assert_allclose(a["log_absences"], np.log1p(a["absences"]))


def test_invalid_cohort_is_refused(tmp_path):
    rows = make_varied_rows(10)
    rows[0]["G3"] = 25
    write_cohort(tmp_path / "student-mat.csv", rows)

    with pytest.raises(InvalidDatasetError, match="Grades"):
        prepare_cohort(load_cohort(tmp_path, Cohort.MATH))


# --- Scenarios and leakage -------------------------------------------------------------


def test_scenarios_differ_only_in_prior_grades():
    full, mid, early = (set(feature_columns(s)) for s in Scenario)

    assert full - early == {"G1", "G2"}
    assert mid - early == {"G1"}
    assert not early & {"G1", "G2"}


@pytest.mark.parametrize("scenario", list(Scenario))
def test_no_scenario_contains_an_outcome(scenario):
    columns = set(feature_columns(scenario))
    assert not columns & {"G3", "at_risk"}
    assert "absences" not in columns  # replaced by log_absences


@pytest.mark.parametrize(
    ("columns", "scenario"),
    [
        (["age", "G3"], Scenario.FULL_HISTORY),
        (["age", "at_risk"], Scenario.FULL_HISTORY),
        (["age", "G2"], Scenario.MID_YEAR),
        (["age", "G1"], Scenario.EARLY),
    ],
)
def test_leakage_guard_rejects_unavailable_columns(columns, scenario):
    with pytest.raises(LeakageError):
        assert_no_leakage(columns, scenario)


def test_feature_matrix_carries_its_scenario(cohort_dataset):
    dataset, _ = cohort_dataset
    matrix = dataset.features(Scenario.EARLY)

    assert matrix.scenario is Scenario.EARLY
    assert matrix.feature_names == list(feature_columns(Scenario.EARLY))


# --- Pipeline and encoding -------------------------------------------------------------


def test_pipeline_refuses_features_from_another_scenario(cohort_dataset):
    dataset, _ = cohort_dataset
    full = dataset.features(Scenario.FULL_HISTORY).X
    early = dataset.features(Scenario.EARLY).X

    with pytest.raises(LeakageError):
        build_preprocessor(Scenario.EARLY).fit(full)
    with pytest.raises(ValueError, match="missing"):
        build_preprocessor(Scenario.FULL_HISTORY).fit(early)

    fitted = build_preprocessor(Scenario.EARLY).fit(early)
    with pytest.raises(LeakageError):
        fitted.transform(full)


def test_pipeline_refuses_target_columns(cohort_dataset):
    dataset, _ = cohort_dataset
    X = dataset.features(Scenario.FULL_HISTORY).X.assign(G3=dataset.regression_target())

    with pytest.raises(LeakageError, match="G3"):
        build_preprocessor(Scenario.FULL_HISTORY).fit(X)


def test_categorical_encoding(cohort_dataset):
    dataset, _ = cohort_dataset
    X = dataset.features(Scenario.EARLY).X
    out = build_preprocessor(Scenario.EARLY, scale_numeric=False).fit_transform(X)

    # Nominal: one column per documented category, exactly one active per student.
    mjob = [c for c in out.columns if c.startswith("Mjob_")]
    assert sorted(mjob) == sorted(
        f"Mjob_{c}" for c in ["teacher", "health", "services", "at_home", "other"]
    )
    assert (out[mjob].sum(axis=1) == 1).all()
    # Binary: a single 0/1 column; yes/no keeps "yes".
    assert "higher_yes" in out.columns and "higher_no" not in out.columns
    assert out["higher_yes"].tolist() == (X["higher"] == "yes").astype(int).tolist()
    # Ordinal: documented integer codes preserved, not one-hot encoded.
    assert out["Medu"].tolist() == X["Medu"].tolist()
    assert not any(c.startswith("Medu_") for c in out.columns)
    assert not out.isna().any().any()


def test_encoding_is_identical_across_cohorts(tmp_path):
    names = []
    for cohort, seed in ((Cohort.MATH, 1), (Cohort.PORTUGUESE, 2)):
        write_cohort(tmp_path / FILES[cohort], make_varied_rows(40, seed=seed))
        X = prepare_cohort(load_cohort(tmp_path, cohort)).features(Scenario.EARLY).X
        names.append(list(build_preprocessor(Scenario.EARLY).fit(X).get_feature_names_out()))
    assert names[0] == names[1]


def test_unknown_category_is_rejected(cohort_dataset):
    dataset, _ = cohort_dataset
    X = dataset.features(Scenario.EARLY).X
    fitted = build_preprocessor(Scenario.EARLY).fit(X)

    with pytest.raises(ValueError):
        fitted.transform(X.assign(Mjob="astronaut"))


def test_missing_values_are_imputed_from_training_data(cohort_dataset):
    dataset, _ = cohort_dataset
    split = dataset.split(Scenario.EARLY)
    prep = build_preprocessor(Scenario.EARLY, scale_numeric=False).fit(split.X_train)

    incomplete = split.X_test.copy()
    incomplete.iloc[0, incomplete.columns.get_loc("age")] = np.nan
    out = prep.transform(incomplete)

    assert out["age"].iloc[0] == split.X_train["age"].median()


# --- Splitting -------------------------------------------------------------------------


def test_split_is_disjoint_complete_and_stratified(cohort_dataset):
    dataset, _ = cohort_dataset
    split = dataset.split(Scenario.EARLY)

    assert split.train_index.intersection(split.test_index).empty
    assert len(split.train_index) + len(split.test_index) == len(dataset.analytical)
    assert len(split.X_test) == pytest.approx(0.2 * len(dataset.analytical), abs=1)
    overall = dataset.risk_target().mean()
    assert split.y_train_risk.mean() == pytest.approx(overall, abs=0.02)
    assert split.y_test_risk.mean() == pytest.approx(overall, abs=0.05)
    assert split.y_train_regression.index.equals(split.X_train.index)


def test_split_is_reproducible_and_shared_across_scenarios(cohort_dataset):
    dataset, _ = cohort_dataset
    a = dataset.split(Scenario.EARLY)
    b = dataset.split(Scenario.EARLY)
    full = dataset.split(Scenario.FULL_HISTORY)
    other_seed = dataset.split(Scenario.EARLY, random_state=RANDOM_STATE + 1)

    assert a.test_index.equals(b.test_index)
    assert a.test_index.equals(full.test_index)
    assert not a.test_index.equals(other_seed.test_index)


def test_preprocessing_statistics_come_from_training_data_only(cohort_dataset):
    dataset, _ = cohort_dataset
    split = dataset.split(Scenario.FULL_HISTORY)
    prep = build_preprocessor(Scenario.FULL_HISTORY).fit(split.X_train)
    scaler = prep.named_steps["columns"].named_transformers_["numeric"].named_steps["scale"]
    numeric = list(prep.named_steps["columns"].transformers_[3][2])

    np.testing.assert_allclose(scaler.mean_, split.X_train[numeric].mean().to_numpy())
    assert not np.allclose(scaler.mean_, dataset.features(Scenario.FULL_HISTORY).X[numeric].mean())


# --- Report ----------------------------------------------------------------------------


def test_report_uses_actual_values(cohort_dataset):
    dataset, _ = cohort_dataset
    report = build_report(dataset, Scenario.EARLY)
    risk = int(dataset.risk_target().sum())

    assert report.original_shape == (len(dataset.raw), 33)
    assert report.rows_removed == 0
    assert report.risk.at_risk == risk
    assert sum(report.target_counts.values()) == len(dataset.raw)
    assert report.split.train_risk.at_risk + report.split.test_risk.at_risk == risk
    excluded = {e.name for e in report.excluded_columns}
    assert {"G3", "at_risk", "G1", "G2", "absences"} <= excluded
    assert "failures" not in {o.name for o in report.outliers}
