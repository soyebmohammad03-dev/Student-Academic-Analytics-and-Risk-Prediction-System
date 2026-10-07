"""Leakage-safe preprocessing and feature engineering.

Typical use in later phases::

    from analytics.data import Cohort, load_cohort
    from analytics.preprocessing import Scenario, build_preprocessor, prepare_cohort

    dataset = prepare_cohort(load_cohort(raw_dir, Cohort.MATH))
    split = dataset.split(Scenario.EARLY)
    model = Pipeline([("prep", build_preprocessor(Scenario.EARLY)), ("clf", estimator)])
    model.fit(split.X_train, split.y_train_risk)   # preprocessing fitted on train only
"""

from analytics.preprocessing.config import RANDOM_STATE, RISK_THRESHOLD, TEST_SIZE
from analytics.preprocessing.dataset import (
    AnalyticalDataset,
    FeatureMatrix,
    InvalidDatasetError,
    Split,
    prepare_cohort,
)
from analytics.preprocessing.features import ENGINEERED_FEATURES, REJECTED_FEATURES
from analytics.preprocessing.pipeline import ScenarioGuard, build_preprocessor, column_groups
from analytics.preprocessing.report import PreprocessingReport, build_report
from analytics.preprocessing.scenarios import (
    SCENARIOS,
    LeakageError,
    Scenario,
    assert_no_leakage,
    feature_columns,
)
from analytics.preprocessing.targets import (
    REGRESSION_TARGET,
    RISK_LABEL,
    TARGET_COLUMNS,
    regression_target,
    risk_label,
)

__all__ = [
    "ENGINEERED_FEATURES",
    "RANDOM_STATE",
    "REGRESSION_TARGET",
    "REJECTED_FEATURES",
    "RISK_LABEL",
    "RISK_THRESHOLD",
    "SCENARIOS",
    "TARGET_COLUMNS",
    "TEST_SIZE",
    "AnalyticalDataset",
    "FeatureMatrix",
    "InvalidDatasetError",
    "LeakageError",
    "PreprocessingReport",
    "Scenario",
    "ScenarioGuard",
    "Split",
    "assert_no_leakage",
    "build_preprocessor",
    "build_report",
    "column_groups",
    "feature_columns",
    "prepare_cohort",
    "regression_target",
    "risk_label",
]
