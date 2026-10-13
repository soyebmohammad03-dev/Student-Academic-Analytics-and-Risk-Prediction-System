"""Model results and predictions for the API.

Results are read from ``models/ml_results.json`` (written by
``python -m analytics.ml.train``) and cached until the file changes. The API never
trains models itself.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from pathlib import Path

from analytics.data import Cohort
from analytics.ml import ModelArtifactError, PredictionService
from analytics.ml.config import Task
from analytics.ml.persistence import RESULTS_FILE, load_metadata, load_results
from analytics.ml.registry import MODELS, search_space
from analytics.ml.results import MlResults
from analytics.preprocessing import Scenario
from app.schemas import models as s


class ModelStore:
    def __init__(self, models_dir: Path) -> None:
        self.models_dir = models_dir
        self.predictions = PredictionService(models_dir)
        self._cached: tuple[tuple[int, int], MlResults] | None = None
        self._lock = threading.Lock()

    def results(self) -> MlResults:
        """Raises ``ModelArtifactError`` when no training run exists."""
        path = self.models_dir / RESULTS_FILE
        stat = path.stat() if path.is_file() else None
        stamp = (stat.st_mtime_ns, stat.st_size) if stat else (0, 0)
        with self._lock:
            if self._cached is None or self._cached[0] != stamp or not stat:
                self._cached = (stamp, load_results(self.models_dir))
            return self._cached[1]

    def catalog(self) -> s.ModelCatalog:
        models = [
            s.ModelInfo(
                task=spec.task,
                key=spec.key,
                label=spec.label,
                family=spec.family,
                baseline=spec.baseline,
                class_weight=spec.class_weight,
                search_space={k.split("__", 1)[1]: v for k, v in search_space(spec).items()},
                strengths=spec.strengths,
                weaknesses=spec.weaknesses,
            )
            for task in Task
            for spec in MODELS[task]
        ]
        try:
            results = self.results()
        except ModelArtifactError:
            return s.ModelCatalog(trained=False, run=None, models=models, selected=[])
        return s.ModelCatalog(
            trained=True,
            run=results.run,
            models=models,
            selected=[
                s.SelectedModelRef(
                    cohort=Cohort(c.cohort),
                    task=sel.task,
                    scenario=sel.scenario,
                    model=sel.model,
                    label=sel.label,
                )
                for c in results.cohorts
                for sel in c.selections
            ],
        )

    def selected(self, cohort: Cohort, task: Task, scenario: Scenario) -> s.SelectedModelDetail:
        results = self.results().cohort(str(cohort))
        meta = load_metadata(self.models_dir, str(cohort), task, scenario)

        def match(items):
            return next((i for i in items if i.scenario is scenario), None)

        selection = next(
            (sel for sel in results.selections if sel.task is task and sel.scenario is scenario),
            None,
        )
        if selection is None:
            raise ModelArtifactError(f"No selection recorded for {cohort} / {task} / {scenario}.")
        regression = task is Task.REGRESSION
        return s.SelectedModelDetail(
            metadata=meta,
            selection=selection,
            regression_errors=match(results.regression_errors) if regression else None,
            classification_errors=None if regression else match(results.classification_errors),
            zero_grade_sensitivity=match(results.zero_grade_sensitivity) if regression else None,
        )


@lru_cache
def get_model_store(models_dir: Path) -> ModelStore:
    return ModelStore(models_dir)
