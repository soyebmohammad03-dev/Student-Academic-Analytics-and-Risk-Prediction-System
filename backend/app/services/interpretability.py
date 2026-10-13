"""Interpretability and risk analysis for the API.

Global importance comes from ``models/interpretability.json`` (written offline by
``python -m analytics.interpret.build``) and is cached by the pipeline until the file
changes. Explanations, sensitivity experiments and suggestions are computed on request
from the persisted models and the cached cohort data; each is bounded (one batched
Shapley estimate per explanation). Profiles are cached per cohort version.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Any

from analytics.data import Cohort
from analytics.interpret.results import ModelInterpretation
from analytics.ml.config import Task
from analytics.ml.predict import validated_record
from analytics.pipeline import AnalyticsPipeline
from analytics.preprocessing import AnalyticalDataset, Scenario
from analytics.preprocessing.features import add_engineered_features
from analytics.risk import PROFILE_VARIABLES, suggest
from analytics.risk.results import RiskProfiles, SuggestionSet
from analytics.statistics.groups import GROUPINGS
from app.schemas.interpretability import GroupFinding, RiskInsights


class RiskService:
    """API view of interpretability and risk analysis, backed by the shared pipeline."""

    def __init__(self, pipeline: AnalyticsPipeline):
        self.pipeline = pipeline
        self.interpreter = pipeline.interpreter

    def dataset(self, cohort: Cohort) -> AnalyticalDataset:
        return self.pipeline.dataset(cohort)

    # --- Global importance ------------------------------------------------------------

    def importance(self, cohort: Cohort, task: Task, scenario: Scenario) -> ModelInterpretation:
        return self.pipeline.importance(cohort, task, scenario)

    # --- Group-level and suggestions -------------------------------------------------

    def profiles(self, cohort: Cohort) -> RiskProfiles:
        return self.pipeline.profiles(cohort)

    def suggestions(
        self, cohort: Cohort, scenario: Scenario, record: Mapping[str, Any]
    ) -> SuggestionSet:
        validated_record(record, scenario)
        flag = self.pipeline.predictions.predict(cohort, Task.CLASSIFICATION, scenario, record)
        return suggest(self.dataset(cohort).analytical, str(cohort), record, flag)

    def group_findings(
        self, cohort: Cohort, scenario: Scenario, record: Mapping[str, Any]
    ) -> list[GroupFinding]:
        row = add_engineered_features(validated_record(record, scenario))
        profiles = self.profiles(cohort)
        findings = []
        for variable in PROFILE_VARIABLES:
            key = GROUPINGS[variable].assign(row).iloc[0]
            profile = next(p for p in profiles.single if p.variable == variable)
            group = next((g for g in profile.groups if g.key == key), None)
            if group is None:
                continue
            findings.append(
                GroupFinding(
                    variable=variable,
                    label=profile.label,
                    group=group.label,
                    n=group.n,
                    risk_percent=group.risk_percent,
                    risk_ci=group.risk_ci,
                    reliable=group.reliable,
                    cohort_risk_percent=profiles.risk_percent,
                )
            )
        return findings

    def insights(
        self, cohort: Cohort, scenario: Scenario, record: Mapping[str, Any], top: int = 10
    ) -> RiskInsights:
        return RiskInsights(
            individual=self.interpreter.explain(
                cohort, Task.CLASSIFICATION, scenario, record, top=top
            ),
            group=self.group_findings(cohort, scenario, record),
            suggestions=self.suggestions(cohort, scenario, record),
            reading=[
                "A (individual) describes how the selected model treated this record. It is a "
                "statistical estimate, not a judgement about the student.",
                "B (group) gives the observed share of cohort students below the pass mark "
                "among those who share each recorded value. It describes groups, not this "
                "student.",
                "C (suggestions) are general prompts for a teacher or adviser to consider, "
                "not instructions or causal claims.",
            ],
        )


_services: dict[int, RiskService] = {}
_lock = threading.Lock()


def get_risk_service(pipeline: AnalyticsPipeline) -> RiskService:
    with _lock:
        if id(pipeline) not in _services:
            _services[id(pipeline)] = RiskService(pipeline)
        return _services[id(pipeline)]
