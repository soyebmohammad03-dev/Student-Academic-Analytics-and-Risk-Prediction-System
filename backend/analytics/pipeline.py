"""Unified analytical pipeline: one entry point that coordinates every component.

``AnalyticsPipeline`` owns the caches for everything derived from the two kinds of
artefact the system reads, and nothing else:

- **cohort files** (``data/raw``): load → validate → prepare (Phase 2–3), then
  statistics and EDA (Phase 4) and risk profiles (Phase 6), all computed lazily and at
  most once per *cohort version*;
- **model artefacts** (``models/``): training results (Phase 5), persisted pipelines
  and interpretability results (Phase 6), read only.

A cache entry is keyed on the file's modification time and size, so a re-downloaded
cohort or a retrained model is picked up on the next request, and a stale result is
never served. Nothing here downloads data or trains models: those are explicit CLI
operations (``analytics.data.download``, ``analytics.ml.train``,
``analytics.interpret.build``).

Each step can be used on its own (``cohort``, ``statistics``, ``ml_results``,
``importance``, ``profiles``, ``interpreter``...). ``summary`` runs the steps for one
cohort and scenario and reports, step by step, what is available.

Usage outside the API::

    python -m analytics.pipeline --cohort math --scenario early
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, Field

from analytics.data import COHORTS, Cohort, LoadedCohort, ValidationReport, load_cohort, validate
from analytics.data.loader import cohort_path
from analytics.interpret import CohortData, Interpreter
from analytics.interpret.build import RESULTS_FILE as INTERPRETABILITY_FILE
from analytics.interpret.build import load as load_interpretability
from analytics.interpret.results import InterpretabilityRun, ModelInterpretation
from analytics.ml.config import Task
from analytics.ml.persistence import RESULTS_FILE, load_metadata, load_pipeline, load_results
from analytics.ml.predict import PredictionService
from analytics.ml.results import MlResults, ModelArtifactError
from analytics.ml.selection import PRIMARY_METRIC
from analytics.preprocessing import (
    RISK_THRESHOLD,
    SCENARIOS,
    AnalyticalDataset,
    PreprocessingReport,
    Scenario,
    build_report,
    feature_columns,
    prepare_cohort,
)
from analytics.risk.profiles import risk_profiles
from analytics.risk.results import RiskProfiles
from analytics.statistics.analysis import CohortAnalysis
from analytics.statistics.core import wilson_ci
from analytics.statistics.models import EffectSize, Interval

log = logging.getLogger("analytics.pipeline")

Stamp = tuple[int, int]
T = TypeVar("T")

COMMANDS = {
    "dataset": "python -m analytics.data.download",
    "models": "python -m analytics.ml.train",
    "interpretability": "python -m analytics.interpret.build",
}


def file_stamp(path: Path) -> Stamp | None:
    """(mtime_ns, size), or None when the file does not exist."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


class FileCache:
    """One value per file version. Thread-safe; rebuilt when the file changes."""

    def __init__(self) -> None:
        self._entries: dict[object, tuple[Stamp, object]] = {}
        self._lock = threading.Lock()

    def get(self, key: object, path: Path, build: Callable[[], T]) -> T:
        stamp = file_stamp(path)
        with self._lock:
            cached = self._entries.get(key)
            if stamp is not None and cached is not None and cached[0] == stamp:
                return cached[1]  # type: ignore[return-value]
        value = build()  # raises when the file is missing or invalid
        with self._lock:
            if stamp is not None:
                self._entries[key] = (stamp, value)
        return value


@dataclass(eq=False)
class CohortVersion:
    """One version of a cohort file and everything derived from it, computed lazily."""

    cohort: Cohort
    loaded: LoadedCohort
    validation: ValidationReport
    _explain_data: dict[int, CohortData] = field(default_factory=dict, repr=False)
    _reports: dict[Scenario, PreprocessingReport] = field(default_factory=dict, repr=False)

    @cached_property
    def dataset(self) -> AnalyticalDataset:
        """Raises ``InvalidDatasetError`` if validation failed."""
        return prepare_cohort(self.loaded, self.validation)

    @cached_property
    def statistics(self) -> CohortAnalysis:
        return CohortAnalysis(str(self.cohort), self.dataset.analytical)

    @cached_property
    def profiles(self) -> RiskProfiles:
        return risk_profiles(self.dataset.analytical, str(self.cohort))

    def preprocessing_report(self, scenario: Scenario) -> PreprocessingReport:
        if scenario not in self._reports:
            self._reports[scenario] = build_report(self.dataset, scenario)
        return self._reports[scenario]

    def explain_data(self, random_state: int) -> CohortData:
        if random_state not in self._explain_data:
            self._explain_data[random_state] = CohortData.from_dataset(self.dataset, random_state)
        return self._explain_data[random_state]


# --- Readiness and summaries (typed, reused as API schemas) --------------------------


ComponentState = Literal["available", "unavailable", "degraded"]


class ComponentStatus(BaseModel):
    key: Literal["api", "dataset", "statistics", "models", "interpretability"]
    label: str
    status: ComponentState
    detail: str
    action: str | None = Field(default=None, description="Command that makes it available.")


class Readiness(BaseModel):
    status: Literal["ready", "degraded"] = Field(
        description="ready = every component available; degraded = the API works but some "
        "analytical artefacts are missing or stale."
    )
    components: list[ComponentStatus]


class ObservedRisk(BaseModel):
    kind: Literal["observed_historical"] = "observed_historical"
    definition: str
    n: int
    at_risk: int
    percent: float
    ci: Interval


class GradeSummary(BaseModel):
    n: int
    mean: float
    median: float
    std: float
    minimum: int
    maximum: int
    zero_count: int


class CohortOverview(BaseModel):
    cohort: Cohort
    subject: str
    rows: int
    columns: int
    validation_status: str
    missing_values: int
    duplicate_rows: int
    invalid_values: int
    final_grade: GradeSummary | None
    observed_risk: ObservedRisk | None


class SelectedModelSummary(BaseModel):
    kind: Literal["model_evaluation"] = "model_evaluation"
    cohort: Cohort
    task: Task
    scenario: Scenario
    model: str
    label: str
    metric: str
    cv_mean: float | None
    cv_std: float | None
    test: float | None


class StepSummary(BaseModel):
    step: str
    status: Literal["available", "unavailable"]
    detail: str


class ResearchQuestionHeadline(BaseModel):
    key: str
    evidence: Literal["confirmatory", "exploratory"]
    p_adjusted: float | None
    significant: bool
    effect: EffectSize | None


class PipelineSummary(BaseModel):
    cohort: Cohort
    scenario: Scenario
    steps: list[StepSummary]
    overview: CohortOverview | None = None
    scenario_features: list[str] = Field(default_factory=list)
    research_questions: list[ResearchQuestionHeadline] = Field(default_factory=list)
    eda_charts: dict[str, int] = Field(default_factory=dict)
    selected_models: list[SelectedModelSummary] = Field(default_factory=list)
    top_attributes: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Per task: attributes ranked by held-out permutation importance.",
    )
    risk_profile_highlights: list[str] = Field(default_factory=list)


class AnalyticsPipeline:
    def __init__(self, raw_dir: Path, models_dir: Path):
        self.raw_dir = raw_dir
        self.models_dir = models_dir
        self._cache = FileCache()
        self._integrity: dict[str, tuple[Stamp | None, bool]] = {}
        self._integrity_lock = threading.Lock()
        self.predictions = PredictionService(models_dir)
        self.interpreter = Interpreter(
            self.predictions, lambda cohort, seed: self.cohort(cohort).explain_data(seed)
        )

    # --- 1–2. Cohort and scenario ---------------------------------------------------

    def cohort(self, cohort: Cohort) -> CohortVersion:
        """Load and validate once per file version. Raises ``DatasetNotFoundError``."""
        cohort = Cohort(cohort)

        def build() -> CohortVersion:
            loaded = load_cohort(self.raw_dir, cohort)
            report = validate(loaded)
            log.info(
                "cohort loaded",
                extra={"cohort": str(cohort), "rows": report.rows, "validation": report.status},
            )
            return CohortVersion(cohort, loaded, report)

        return self._cache.get(("cohort", cohort), cohort_path(self.raw_dir, cohort), build)

    def dataset(self, cohort: Cohort) -> AnalyticalDataset:
        return self.cohort(cohort).dataset

    # --- 3–4. Statistics and EDA -----------------------------------------------------

    def statistics(self, cohort: Cohort) -> CohortAnalysis:
        return self.cohort(cohort).statistics

    # --- 5. Trained ML results ---------------------------------------------------------

    def ml_results(self) -> MlResults:
        return self._cache.get(
            "ml_results", self.models_dir / RESULTS_FILE, lambda: load_results(self.models_dir)
        )

    # --- 6. Explanations ---------------------------------------------------------------

    def interpretability(self) -> InterpretabilityRun:
        return self._cache.get(
            "interpretability",
            self.models_dir / INTERPRETABILITY_FILE,
            lambda: load_interpretability(self.models_dir),
        )

    def importance(self, cohort: Cohort, task: Task, scenario: Scenario) -> ModelInterpretation:
        for item in self.interpretability().items:
            if (item.cohort, item.task, item.scenario) == (
                str(cohort),
                Task(task),
                Scenario(scenario),
            ):
                return item
        raise ModelArtifactError(f"No importance results for {cohort} / {task} / {scenario}.")

    # --- 7. Academic-risk analysis ------------------------------------------------------

    def profiles(self, cohort: Cohort) -> RiskProfiles:
        return self.cohort(cohort).profiles

    # --- Readiness ------------------------------------------------------------------------

    def _models_intact(self) -> tuple[bool, str]:
        """Every selected pipeline present, unaltered, loadable and matching its metadata."""
        results = self.ml_results()
        problems = []
        for c in results.cohorts:
            for s in c.selections:
                try:
                    meta = load_metadata(self.models_dir, c.cohort, s.task, s.scenario)
                    if meta.model != s.model:
                        problems.append(f"{c.cohort}/{s.task}/{s.scenario}: metadata disagrees")
                        continue
                    path = self.models_dir / "selected" / meta.artifact
                    stamp = file_stamp(path)
                    with self._integrity_lock:
                        cached = self._integrity.get(meta.artifact)
                    if cached is None or cached[0] != stamp or cached[1] is False:
                        load_pipeline(self.models_dir, meta)  # checksum, version, contents
                        with self._integrity_lock:
                            self._integrity[meta.artifact] = (stamp, True)
                except ModelArtifactError as exc:
                    problems.append(str(exc))
        if problems:
            return False, "; ".join(problems[:3])
        return True, f"{sum(len(c.selections) for c in results.cohorts)} selected models verified."

    def readiness(self) -> Readiness:
        components = [
            ComponentStatus(key="api", label="API", status="available", detail="Operational.")
        ]
        dataset_ok, problems = True, []
        for cohort, info in COHORTS.items():
            path = cohort_path(self.raw_dir, cohort)
            if not path.is_file():
                dataset_ok = False
                problems.append(f"{info.filename} missing")
                continue
            key = ("checksum", cohort)
            digest = self._cache.get(
                key, path, lambda p=path: hashlib.sha256(p.read_bytes()).hexdigest()
            )
            if digest != info.sha256:
                dataset_ok = False
                problems.append(f"{info.filename} does not match its pinned checksum")
        components.append(
            ComponentStatus(
                key="dataset",
                label="Dataset",
                status="available" if dataset_ok else "unavailable",
                detail="Both cohort files present and checksum-verified."
                if dataset_ok
                else "; ".join(problems) + ".",
                action=None if dataset_ok else COMMANDS["dataset"],
            )
        )

        stats_ok = dataset_ok and all(self.cohort(c).validation.status != "fail" for c in Cohort)
        components.append(
            ComponentStatus(
                key="statistics",
                label="Statistics and EDA",
                status="available" if stats_ok else "unavailable",
                detail="Computed on demand from the validated cohorts."
                if stats_ok
                else "Requires the validated dataset.",
                action=None if stats_ok else COMMANDS["dataset"],
            )
        )

        try:
            models_ok, detail = self._models_intact()
            models_state: ComponentState = "available" if models_ok else "degraded"
        except ModelArtifactError:
            models_ok, models_state, detail = False, "unavailable", "No training results."
        components.append(
            ComponentStatus(
                key="models",
                label="Trained models",
                status=models_state,
                detail=detail,
                action=None if models_ok else COMMANDS["models"],
            )
        )

        try:
            run = self.interpretability()
            if not models_ok:
                interp_state: ComponentState = "degraded"
                interp_detail = "Results exist but the models they describe are not available."
            elif run.models_created_at != self.ml_results().run.created_at:
                interp_state = "degraded"
                interp_detail = "Built from a different training run; rebuild it."
            else:
                interp_state, interp_detail = "available", f"{len(run.items)} models described."
        except ModelArtifactError:
            interp_state, interp_detail = "unavailable", "No interpretability results."
        if interp_state == "available" and not dataset_ok:
            interp_state = "degraded"
            interp_detail = "Global importance available; explanations need the dataset."
        components.append(
            ComponentStatus(
                key="interpretability",
                label="Interpretability",
                status=interp_state,
                detail=interp_detail,
                action=None if interp_state == "available" else COMMANDS["interpretability"],
            )
        )
        ready = all(c.status == "available" for c in components)
        return Readiness(status="ready" if ready else "degraded", components=components)

    # --- Summaries ----------------------------------------------------------------------------

    def overview(self, cohort: Cohort) -> CohortOverview:
        version = self.cohort(cohort)
        report = version.validation
        grade = risk = None
        if report.status != "fail":
            data = version.dataset.analytical
            g3 = data["G3"]
            grade = GradeSummary(
                n=len(g3),
                mean=float(g3.mean()),
                median=float(g3.median()),
                std=float(g3.std(ddof=1)),
                minimum=int(g3.min()),
                maximum=int(g3.max()),
                zero_count=int((g3 == 0).sum()),
            )
            n, at = len(data), int(data["at_risk"].sum())
            low, high = wilson_ci(at, n)
            risk = ObservedRisk(
                definition=(
                    f"Share of students in the historical data whose final grade G3 was below "
                    f"{RISK_THRESHOLD}. An observed proportion, not a prediction."
                ),
                n=n,
                at_risk=at,
                percent=100 * at / n,
                ci=Interval(low=low, high=high),
            )
        return CohortOverview(
            cohort=Cohort(cohort),
            subject=COHORTS[Cohort(cohort)].subject,
            rows=report.rows,
            columns=report.columns,
            validation_status=report.status,
            missing_values=report.missing_values,
            duplicate_rows=report.duplicate_rows,
            invalid_values=report.invalid_values,
            final_grade=grade,
            observed_risk=risk,
        )

    def selected_models(self, cohort: Cohort | None = None) -> list[SelectedModelSummary]:
        items = []
        for c in self.ml_results().cohorts:
            if cohort is not None and c.cohort != str(cohort):
                continue
            for s in c.selections:
                models = c.regression if s.task is Task.REGRESSION else c.classification
                r = next(m for m in models if m.scenario is s.scenario and m.model == s.model)
                metric = PRIMARY_METRIC[s.task]
                items.append(
                    SelectedModelSummary(
                        cohort=Cohort(c.cohort),
                        task=s.task,
                        scenario=s.scenario,
                        model=s.model,
                        label=s.label,
                        metric=metric,
                        cv_mean=r.cv[metric].mean,
                        cv_std=r.cv[metric].std,
                        test=r.test[metric],
                    )
                )
        return items

    def summary(self, cohort: Cohort, scenario: Scenario) -> PipelineSummary:
        """Run every step for one cohort and scenario; unavailable steps are reported."""
        cohort, scenario = Cohort(cohort), Scenario(scenario)
        out = PipelineSummary(cohort=cohort, scenario=scenario, steps=[])

        def step(name: str, run: Callable[[], str]) -> bool:
            try:
                detail = run()
            except (FileNotFoundError, ModelArtifactError, ValueError) as exc:
                out.steps.append(StepSummary(step=name, status="unavailable", detail=_public(exc)))
                return False
            out.steps.append(StepSummary(step=name, status="available", detail=detail))
            return True

        def load() -> str:
            out.overview = self.overview(cohort)
            return f"{out.overview.rows} students, validation {out.overview.validation_status}."

        if not step("dataset", load):
            for name in ("scenario", "statistics", "eda", "models", "explanations", "risk"):
                out.steps.append(
                    StepSummary(step=name, status="unavailable", detail="Requires the dataset.")
                )
            return out

        def prepare() -> str:
            self.dataset(cohort)
            out.scenario_features = list(feature_columns(scenario))
            return f"{SCENARIOS[scenario].label}: {len(out.scenario_features)} input columns."

        def statistics() -> str:
            rq = self.statistics(cohort).research_questions
            out.research_questions = [
                ResearchQuestionHeadline(
                    key=q.key,
                    evidence=q.evidence,
                    p_adjusted=q.p_adjusted,
                    significant=q.significant,
                    effect=q.effect,
                )
                for q in rq.items
            ]
            return f"{len(rq.items)} research questions ({rq.correction.rstrip('.')})."

        def eda() -> str:
            e = self.statistics(cohort).eda
            out.eda_charts = {
                "histograms": len(e.histograms),
                "bars": len(e.bars),
                "boxplots": len(e.boxplots),
                "scatters": len(e.scatters),
            }
            return f"{sum(out.eda_charts.values())} chart datasets plus heatmap and profile."

        def models() -> str:
            out.selected_models = [
                m for m in self.selected_models(cohort) if m.scenario is scenario
            ]
            return f"Selected models for both tasks (run {self.ml_results().run.created_at})."

        def explanations() -> str:
            for task in Task:
                item = self.importance(cohort, task, scenario)
                # The first permutation result uses the whole test set (see build.py).
                perm = next(m for m in item.methods if m.method == "permutation_test")
                out.top_attributes[str(task)] = [i.label for i in perm.items if i.value > 0][:5]
            return "Global importance of the selected models (permutation, held-out test set)."

        def risk() -> str:
            p = self.profiles(cohort)
            strongest = sorted(p.single, key=lambda s: -(s.cramers_v or 0))[:3]
            out.risk_profile_highlights = [
                f"{s.label}: Cramér's V {s.cramers_v:.2f} ({s.magnitude}), BH-adjusted p "
                f"{s.p_adjusted:.3g}."
                for s in strongest
            ]
            return (
                f"Observed risk {p.risk_percent:.1f}% across {len(p.single)} profiled attributes."
            )

        step("scenario", prepare)
        step("statistics", statistics)
        step("eda", eda)
        step("models", models)
        step("explanations", explanations)
        step("risk", risk)
        return out


def _public(exc: Exception) -> str:
    """A message safe to show outside the server (no file-system paths)."""
    from analytics.data import DatasetNotFoundError

    if isinstance(exc, DatasetNotFoundError):
        return f"Dataset not downloaded. Run `{COMMANDS['dataset']}`."
    return str(exc)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from analytics.data.download import DEFAULT_RAW_DIR
    from analytics.ml.config import DEFAULT_MODELS_DIR

    parser = argparse.ArgumentParser(description="Print the integrated pipeline summary.")
    parser.add_argument("--cohort", choices=[c.value for c in Cohort], default="math")
    parser.add_argument("--scenario", choices=[s.value for s in Scenario], default="early")
    args = parser.parse_args(argv)
    pipeline = AnalyticsPipeline(DEFAULT_RAW_DIR, DEFAULT_MODELS_DIR)
    print(pipeline.readiness().model_dump_json(indent=2))
    print(pipeline.summary(Cohort(args.cohort), Scenario(args.scenario)).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
