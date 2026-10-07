"""Preprocessing metadata for the API. Reuses the cached, validated cohorts."""

from __future__ import annotations

import threading

from analytics.data import Cohort
from analytics.preprocessing import (
    ENGINEERED_FEATURES,
    REGRESSION_TARGET,
    RISK_LABEL,
    RISK_THRESHOLD,
    SCENARIOS,
    PreprocessingReport,
    Scenario,
    build_report,
    prepare_cohort,
)
from app.schemas import preprocessing as s
from app.services.dataset import CohortEntry, DatasetStore

#: (cohort, scenario) -> (cohort entry the report was built from, report)
_cache: dict[tuple[Cohort, Scenario], tuple[CohortEntry, PreprocessingReport]] = {}
_lock = threading.Lock()


def _report(cohort: Cohort, entry: CohortEntry, scenario: Scenario) -> PreprocessingReport:
    """Build once per cohort version; a re-downloaded file yields a new entry and report."""
    key = (cohort, scenario)
    with _lock:
        cached = _cache.get(key)
        if cached is None or cached[0] is not entry:
            dataset = prepare_cohort(entry.loaded, entry.report)
            cached = (entry, build_report(dataset, scenario))
            _cache[key] = cached
        return cached[1]


def _risk(dist) -> s.RiskDistributionOut:
    return s.RiskDistributionOut(
        at_risk=dist.at_risk, not_at_risk=dist.not_at_risk, at_risk_share=dist.at_risk_share
    )


def preprocessing_summary(
    store: DatasetStore, cohort: Cohort, scenario: Scenario
) -> s.PreprocessingSummary:
    report = _report(cohort, store.get(cohort), scenario)
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
