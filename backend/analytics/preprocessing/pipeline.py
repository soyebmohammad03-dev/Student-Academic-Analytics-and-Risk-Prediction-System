"""Reusable scikit-learn preprocessing for one feature scenario.

``build_preprocessor`` returns an unfitted ``Pipeline``. Every learned quantity
(imputation values, scaling statistics) is estimated in ``fit``, so in modelling it
must be fitted on training data only — ideally by placing it in front of an estimator
inside a single ``Pipeline`` that is fitted on the training split or CV folds.

Encoding decisions (see docs/METHODOLOGY.md):

- **Binary categorical** (school, sex, address, famsize, Pstatus and yes/no fields):
  one-hot with the first category dropped, giving one 0/1 column (e.g. ``higher_yes``).
- **Nominal** (Mjob, Fjob, reason, guardian): full one-hot encoding. No numeric order is
  invented. Categories are fixed from the data dictionary, so encodings are identical
  across cohorts and splits; an undocumented category raises an error.
- **Ordinal codes** (Medu, Fedu, traveltime, studytime, famrel, freetime, goout, Dalc,
  Walc, health): kept as their documented integer codes, because UCI defines an order.
  Treating code distances as equal is an assumption, stated in the methodology.
- **Numeric** (age, failures, log_absences, G1/G2 where allowed): kept numeric.
- **Indicators** (engineered 0/1 features): passed through.

Ordinal and numeric columns are standardised when ``scale_numeric`` is true (for
linear, distance and kernel models); tree models can use ``scale_numeric=False``.
Median / most-frequent imputers are included as a safety net: the official files have
no missing values, so they are no-ops on this data but keep inference well defined.
"""

from __future__ import annotations

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from analytics.data.dictionary import COLUMNS_BY_NAME
from analytics.preprocessing.features import ENGINEERED_BY_NAME
from analytics.preprocessing.scenarios import Scenario, assert_no_leakage, feature_columns


def _first_category_last_kept(name: str) -> list:
    """Category order for binary columns, so the kept column is the informative one."""
    codes = [v.code for v in COLUMNS_BY_NAME[name].allowed]
    return sorted(codes, key=lambda c: c == "yes") if set(codes) == {"yes", "no"} else codes


def column_groups(scenario: Scenario) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {
        "binary": [], "nominal": [], "ordinal": [], "numeric": [], "indicator": []
    }  # fmt: skip
    for name in feature_columns(scenario):
        engineered = ENGINEERED_BY_NAME.get(name)
        if engineered:
            groups[engineered.kind].append(name)
            continue
        spec = COLUMNS_BY_NAME[name]
        if spec.measure == "categorical":
            groups["binary" if spec.scale == "binary" else "nominal"].append(name)
        elif spec.scale == "ordinal":
            groups["ordinal"].append(name)
        else:
            groups["numeric"].append(name)
    return groups


class ScenarioGuard(BaseEstimator, TransformerMixin):
    """First pipeline step: input columns must be exactly the scenario's feature set.

    Prevents silently dropping or accepting columns from a different scenario, and
    rejects outcome columns outright.
    """

    def __init__(self, scenario: Scenario):
        self.scenario = scenario

    def _check(self, X: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(X, pd.DataFrame):
            raise TypeError("Preprocessing expects a pandas DataFrame with named columns.")
        assert_no_leakage(X.columns, self.scenario)
        expected = set(feature_columns(self.scenario))
        if set(X.columns) != expected:
            missing = sorted(expected - set(X.columns))
            extra = sorted(set(X.columns) - expected)
            raise ValueError(
                f"Columns do not match the '{self.scenario}' scenario "
                f"(missing: {missing}, unexpected: {extra})."
            )
        return X

    def fit(self, X, y=None):
        self._check(X)
        self.feature_names_in_ = list(X.columns)
        return self

    def transform(self, X):
        return self._check(X)

    def get_feature_names_out(self, input_features=None):
        return list(feature_columns(self.scenario))


def build_preprocessor(scenario: Scenario, *, scale_numeric: bool = True) -> Pipeline:
    groups = column_groups(scenario)

    def numeric_steps():
        steps = [("impute", SimpleImputer(strategy="median"))]
        if scale_numeric:
            steps.append(("scale", StandardScaler()))
        return Pipeline(steps)

    transformer = ColumnTransformer(
        [
            (
                "binary",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        (
                            "encode",
                            OneHotEncoder(
                                categories=[_first_category_last_kept(c) for c in groups["binary"]],
                                drop="first",
                                sparse_output=False,
                                dtype="int64",
                            ),
                        ),
                    ]
                ),
                groups["binary"],
            ),
            (
                "nominal",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        (
                            "encode",
                            OneHotEncoder(
                                categories=[
                                    [v.code for v in COLUMNS_BY_NAME[c].allowed]
                                    for c in groups["nominal"]
                                ],
                                handle_unknown="error",
                                sparse_output=False,
                                dtype="int64",
                            ),
                        ),
                    ]
                ),
                groups["nominal"],
            ),
            ("ordinal", numeric_steps(), groups["ordinal"]),
            ("numeric", numeric_steps(), groups["numeric"]),
            ("indicator", "passthrough", groups["indicator"]),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    return Pipeline([("guard", ScenarioGuard(scenario)), ("columns", transformer)]).set_output(
        transform="pandas"
    )
