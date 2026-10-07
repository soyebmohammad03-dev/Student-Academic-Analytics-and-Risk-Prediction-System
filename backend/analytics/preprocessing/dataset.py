"""Analytical dataset: the single entry point later phases use to obtain data.

``prepare_cohort`` turns a validated cohort into an ``AnalyticalDataset``:

- ``raw``         the file exactly as read (text), never modified or written back
- ``validated``   typed values after validation
- ``analytical``  validated values + engineered features + targets (``G3``, ``at_risk``)

Feature matrices are only available through a named scenario, and always exclude the
outcome columns. No rows are removed: the official files contain no missing or
invalid values, and unusual-but-valid values (e.g. ``G3 = 0``, high absence counts)
are kept.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import train_test_split

from analytics.data import Cohort, LoadedCohort, ValidationReport, validate
from analytics.preprocessing.config import RANDOM_STATE, TEST_SIZE
from analytics.preprocessing.features import add_engineered_features
from analytics.preprocessing.scenarios import Scenario, assert_no_leakage, feature_columns
from analytics.preprocessing.targets import (
    REGRESSION_TARGET,
    RISK_LABEL,
    regression_target,
    risk_label,
)


class InvalidDatasetError(ValueError):
    """Raised when a cohort fails validation and must not be preprocessed."""


@dataclass(frozen=True)
class FeatureMatrix:
    """Predictors for one scenario. The scenario travels with the data."""

    scenario: Scenario
    X: pd.DataFrame

    @property
    def feature_names(self) -> list[str]:
        return list(self.X.columns)


@dataclass(frozen=True)
class Split:
    """Train/test partition shared by the regression and classification targets."""

    scenario: Scenario
    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train_regression: pd.Series
    y_test_regression: pd.Series
    y_train_risk: pd.Series
    y_test_risk: pd.Series
    random_state: int
    test_size: float

    @property
    def train_index(self) -> pd.Index:
        return self.X_train.index

    @property
    def test_index(self) -> pd.Index:
        return self.X_test.index


@dataclass(frozen=True)
class AnalyticalDataset:
    cohort: Cohort
    raw: pd.DataFrame
    validated: pd.DataFrame
    analytical: pd.DataFrame
    validation: ValidationReport

    def features(self, scenario: Scenario) -> FeatureMatrix:
        scenario = Scenario(scenario)
        columns = list(feature_columns(scenario))
        X = self.analytical[columns].copy()
        assert_no_leakage(X.columns, scenario)
        return FeatureMatrix(scenario=scenario, X=X)

    def regression_target(self) -> pd.Series:
        return self.analytical[REGRESSION_TARGET].copy()

    def risk_target(self) -> pd.Series:
        return self.analytical[RISK_LABEL].copy()

    def split(
        self,
        scenario: Scenario,
        *,
        test_size: float = TEST_SIZE,
        random_state: int = RANDOM_STATE,
    ) -> Split:
        """Stratified on ``at_risk`` so both sets keep the cohort's risk proportion.

        One split serves both tasks, so regression and classification results for a
        scenario are evaluated on the same students.
        """
        X = self.features(scenario).X
        train_idx, test_idx = train_test_split(
            X.index,
            test_size=test_size,
            random_state=random_state,
            stratify=self.analytical[RISK_LABEL],
        )
        train_idx, test_idx = train_idx.sort_values(), test_idx.sort_values()
        return Split(
            scenario=Scenario(scenario),
            X_train=X.loc[train_idx],
            X_test=X.loc[test_idx],
            y_train_regression=self.analytical.loc[train_idx, REGRESSION_TARGET],
            y_test_regression=self.analytical.loc[test_idx, REGRESSION_TARGET],
            y_train_risk=self.analytical.loc[train_idx, RISK_LABEL],
            y_test_risk=self.analytical.loc[test_idx, RISK_LABEL],
            random_state=random_state,
            test_size=test_size,
        )


def _model_ready(data: pd.DataFrame) -> pd.DataFrame:
    """Plain NumPy-backed dtypes for scikit-learn: float64 numbers, object categories.

    Nullable pandas dtypes use ``pd.NA``, which scikit-learn imputers and encoders do not
    treat as missing; ``NaN`` is the convention they expect.
    """
    out = {}
    for name, column in data.items():
        if pd.api.types.is_numeric_dtype(column):
            out[name] = column.astype("float64")
        else:
            out[name] = column.astype(object).where(column.notna(), float("nan"))
    return pd.DataFrame(out, index=data.index)


def prepare_cohort(
    loaded: LoadedCohort, validation: ValidationReport | None = None
) -> AnalyticalDataset:
    validation = validation or validate(loaded)
    if validation.status == "fail":
        failed = ", ".join(c.title for c in validation.checks if c.status == "fail")
        raise InvalidDatasetError(f"{loaded.info.filename} failed validation: {failed}")

    validated = loaded.data.copy()
    analytical = add_engineered_features(_model_ready(validated))
    analytical[REGRESSION_TARGET] = regression_target(validated)
    analytical[RISK_LABEL] = risk_label(validated)
    return AnalyticalDataset(
        cohort=loaded.info.cohort,
        raw=loaded.raw,
        validated=validated,
        analytical=analytical,
        validation=validation,
    )
