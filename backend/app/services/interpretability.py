"""Interpretability and risk analysis for the API.

Global importance is read from ``models/interpretability.json`` (written offline by
``python -m analytics.interpret.build``). Explanations, sensitivity experiments,
profiles and suggestions are computed on request from the persisted models and the
cached cohort data; each is bounded (one batched Shapley estimate per explanation).
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from typing import Any

from analytics.data import Cohort
from analytics.interpret import CohortData, Interpreter
from analytics.interpret.build import load as load_interpretability
from analytics.interpret.results import InterpretabilityRun, ModelInterpretation
from analytics.ml.config import Task
from analytics.ml.predict import validated_record
from analytics.ml.results import ModelArtifactError
from analytics.preprocessing import AnalyticalDataset, Scenario, prepare_cohort
from analytics.preprocessing.features import add_engineered_features
from analytics.risk import PROFILE_VARIABLES, risk_profiles, suggest
from analytics.risk.results import RiskProfiles, SuggestionSet
from analytics.statistics.groups import GROUPINGS
from app.schemas.interpretability import GroupFinding, RiskInsights
from app.services.dataset import CohortEntry, DatasetStore
from app.services.models import ModelStore


class RiskService:
    def __init__(self, store: DatasetStore, models: ModelStore):
        self.store = store
        self.models = models
        self.interpreter = Interpreter(models.predictions, self._cohort_data)
        self._datasets: dict[Cohort, tuple[CohortEntry, AnalyticalDataset]] = {}
        self._profiles: dict[Cohort, tuple[CohortEntry, RiskProfiles]] = {}
        self._run: tuple[tuple[int, int], InterpretabilityRun] | None = None
        self._lock = threading.Lock()

    def dataset(self, cohort: Cohort) -> AnalyticalDataset:
        entry = self.store.get(cohort)
        with self._lock:
            cached = self._datasets.get(cohort)
            if cached is None or cached[0] is not entry:
                cached = (entry, prepare_cohort(entry.loaded, entry.report))
                self._datasets[cohort] = cached
            return cached[1]

    def _cohort_data(self, cohort: Cohort, random_state: int) -> CohortData:
        return CohortData.from_dataset(self.dataset(cohort), random_state)

    # --- Global importance ------------------------------------------------------------

    def importance(self, cohort: Cohort, task: Task, scenario: Scenario) -> ModelInterpretation:
        path = self.models.models_dir / "interpretability.json"
        stat = path.stat() if path.is_file() else None
        stamp = (stat.st_mtime_ns, stat.st_size) if stat else (0, 0)
        with self._lock:
            if self._run is None or self._run[0] != stamp or not stat:
                self._run = (stamp, load_interpretability(self.models.models_dir))
            run = self._run[1]
        for item in run.items:
            if item.cohort == str(cohort) and item.task is task and item.scenario is scenario:
                return item
        raise ModelArtifactError(f"No importance results for {cohort} / {task} / {scenario}.")

    # --- Group-level and suggestions -------------------------------------------------

    def profiles(self, cohort: Cohort) -> RiskProfiles:
        entry = self.store.get(cohort)
        with self._lock:
            cached = self._profiles.get(cohort)
        if cached is None or cached[0] is not entry:
            cached = (entry, risk_profiles(self.dataset(cohort).analytical, str(cohort)))
            with self._lock:
                self._profiles[cohort] = cached
        return cached[1]

    def suggestions(
        self, cohort: Cohort, scenario: Scenario, record: Mapping[str, Any]
    ) -> SuggestionSet:
        validated_record(record, scenario)
        flag = self.models.predictions.predict(cohort, Task.CLASSIFICATION, scenario, record)
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


_services: dict[tuple[int, int], RiskService] = {}
_lock = threading.Lock()


def get_risk_service(store: DatasetStore, models: ModelStore) -> RiskService:
    key = (id(store), id(models))
    with _lock:
        if key not in _services:
            _services[key] = RiskService(store, models)
        return _services[key]
