"""Preprocessing quality report, computed from the actual cohort data."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from analytics.data.dictionary import COLUMNS
from analytics.preprocessing.config import RANDOM_STATE, RISK_THRESHOLD, TEST_SIZE
from analytics.preprocessing.dataset import AnalyticalDataset
from analytics.preprocessing.features import ENGINEERED_FEATURES
from analytics.preprocessing.pipeline import build_preprocessor, column_groups
from analytics.preprocessing.scenarios import SCENARIOS, Scenario, feature_columns
from analytics.preprocessing.targets import REGRESSION_TARGET, RISK_LABEL


@dataclass(frozen=True)
class ExcludedColumn:
    name: str
    reason: str


#: Columns where the Tukey rule is meaningful. ``failures`` is excluded: it is zero for
#: most students, so its quartiles coincide and every non-zero count would be flagged.
OUTLIER_COLUMNS = ("age", "absences", "G1", "G2", "G3")


@dataclass(frozen=True)
class OutlierCount:
    """Tukey rule (outside Q1 − 1.5·IQR, Q3 + 1.5·IQR), reported only; nothing removed."""

    name: str
    count: int
    lower_fence: float
    upper_fence: float


@dataclass(frozen=True)
class RiskDistribution:
    at_risk: int
    not_at_risk: int

    @property
    def at_risk_share(self) -> float:
        total = self.at_risk + self.not_at_risk
        return self.at_risk / total if total else 0.0


@dataclass(frozen=True)
class SplitSummary:
    train_rows: int
    test_rows: int
    train_risk: RiskDistribution
    test_risk: RiskDistribution
    test_size: float
    random_state: int
    stratified_on: str


@dataclass(frozen=True)
class PreprocessingReport:
    cohort: str
    scenario: Scenario
    scenario_label: str
    original_shape: tuple[int, int]
    analytical_shape: tuple[int, int]
    feature_groups: dict[str, list[str]]
    engineered_features: list[str]
    excluded_columns: list[ExcludedColumn]
    rows_removed: int
    missing_values: int
    missing_value_strategy: str
    encoded_feature_names: list[str]
    target_counts: dict[int, int]
    target_zero_count: int
    risk_threshold: int
    risk: RiskDistribution
    outliers: list[OutlierCount]
    split: SplitSummary


def _risk(series: pd.Series) -> RiskDistribution:
    at_risk = int(series.sum())
    return RiskDistribution(at_risk=at_risk, not_at_risk=int(len(series) - at_risk))


def _excluded(scenario: Scenario) -> list[ExcludedColumn]:
    used = set(feature_columns(scenario))
    reasons = {
        REGRESSION_TARGET: "Outcome (final grade); regression target, never a predictor.",
        RISK_LABEL: f"Derived outcome (G3 < {RISK_THRESHOLD}); classification target.",
    }
    for engineered in ENGINEERED_FEATURES:
        if engineered.replaces:
            reasons[engineered.replaces] = f"Represented by `{engineered.name}`."
    out = [ExcludedColumn(REGRESSION_TARGET, reasons[REGRESSION_TARGET])]
    out.append(ExcludedColumn(RISK_LABEL, reasons[RISK_LABEL]))
    for spec in COLUMNS:
        if spec.name in used or spec.name == REGRESSION_TARGET:
            continue
        reason = reasons.get(spec.name) or (
            f"Prior grade not available in the '{scenario}' scenario."
            if spec.role == "prior_grade"
            else "Not used."
        )
        out.append(ExcludedColumn(spec.name, reason))
    return out


def _outliers(data: pd.DataFrame, columns: list[str]) -> list[OutlierCount]:
    out = []
    for name in columns:
        values = data[name].astype("float64")
        q1, q3 = values.quantile([0.25, 0.75])
        low, high = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        out.append(OutlierCount(name, int(((values < low) | (values > high)).sum()), low, high))
    return out


def build_report(dataset: AnalyticalDataset, scenario: Scenario) -> PreprocessingReport:
    scenario = Scenario(scenario)
    split = dataset.split(scenario)
    # Fitted on the training split only, exactly as in modelling, to list output columns.
    encoded = build_preprocessor(scenario).fit(split.X_train).get_feature_names_out()
    groups = column_groups(scenario)
    target = dataset.regression_target().astype("int64")
    X = dataset.features(scenario).X

    return PreprocessingReport(
        cohort=str(dataset.cohort),
        scenario=scenario,
        scenario_label=SCENARIOS[scenario].label,
        original_shape=dataset.raw.shape,
        analytical_shape=dataset.analytical.shape,
        feature_groups=groups,
        engineered_features=[f.name for f in ENGINEERED_FEATURES],
        excluded_columns=_excluded(scenario),
        rows_removed=len(dataset.raw) - len(dataset.analytical),
        missing_values=int(X.isna().sum().sum() + target.isna().sum()),
        missing_value_strategy=(
            "No rows dropped. Inside the pipeline, numeric and ordinal columns are imputed "
            "with the training-set median and categorical columns with the training-set "
            "most frequent value. The official files contain no missing values."
        ),
        encoded_feature_names=[str(n) for n in encoded],
        target_counts={int(k): int(v) for k, v in target.value_counts().sort_index().items()},
        target_zero_count=int((target == 0).sum()),
        risk_threshold=RISK_THRESHOLD,
        risk=_risk(dataset.risk_target()),
        outliers=_outliers(dataset.analytical, list(OUTLIER_COLUMNS)),
        split=SplitSummary(
            train_rows=len(split.X_train),
            test_rows=len(split.X_test),
            train_risk=_risk(split.y_train_risk),
            test_risk=_risk(split.y_test_risk),
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratified_on=RISK_LABEL,
        ),
    )
