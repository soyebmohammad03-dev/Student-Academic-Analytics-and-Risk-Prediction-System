"""Preprocessing metadata for the API. Reports are cached per cohort version and scenario."""

from __future__ import annotations

from analytics.data import Cohort
from analytics.preprocessing import (
    ENGINEERED_FEATURES,
    REGRESSION_TARGET,
    RISK_LABEL,
    RISK_THRESHOLD,
    SCENARIOS,
    Scenario,
)
from app.schemas import preprocessing as s
from app.services.dataset import DatasetStore


def _risk(dist) -> s.RiskDistributionOut:
    return s.RiskDistributionOut(
        at_risk=dist.at_risk, not_at_risk=dist.not_at_risk, at_risk_share=dist.at_risk_share
    )


def preprocessing_summary(
    store: DatasetStore, cohort: Cohort, scenario: Scenario
) -> s.PreprocessingSummary:
    report = store.get(cohort).version.preprocessing_report(scenario)
    spec = SCENARIOS[scenario]
    return s.PreprocessingSummary(
        cohort=cohort,
        scenario=s.ScenarioInfo(
            key=scenario,
            label=spec.label,
            description=spec.description,
            prior_grades=list(spec.prior_grades),
        ),
        original_shape=report.original_shape,
        analytical_shape=report.analytical_shape,
        rows_removed=report.rows_removed,
        feature_groups=report.feature_groups,
        encoded_features=report.encoded_feature_names,
        engineered_features=[
            s.EngineeredFeatureOut(
                name=f.name,
                definition=f.definition,
                reason=f.reason,
                leakage=f.leakage,
                sources=list(f.sources),
                replaces=f.replaces,
            )
            for f in ENGINEERED_FEATURES
        ],
        excluded_columns=[
            s.ExcludedColumnOut(name=e.name, reason=e.reason) for e in report.excluded_columns
        ],
        missing_values=report.missing_values,
        missing_value_strategy=report.missing_value_strategy,
        regression_target=REGRESSION_TARGET,
        risk_label=RISK_LABEL,
        risk_definition=(
            f"{RISK_LABEL} = 1 if {REGRESSION_TARGET} < {RISK_THRESHOLD} (below the pass mark), "
            "else 0. Academic risk of not passing the final evaluation; not a dropout label."
        ),
        target_counts=report.target_counts,
        target_zero_count=report.target_zero_count,
        risk=_risk(report.risk),
        outliers=[
            s.OutlierOut(
                name=o.name, count=o.count, lower_fence=o.lower_fence, upper_fence=o.upper_fence
            )
            for o in report.outliers
        ],
        split=s.SplitOut(
            train_rows=report.split.train_rows,
            test_rows=report.split.test_rows,
            train_risk=_risk(report.split.train_risk),
            test_risk=_risk(report.split.test_risk),
            test_size=report.split.test_size,
            random_state=report.split.random_state,
            stratified_on=report.split.stratified_on,
        ),
    )
