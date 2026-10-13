"""Dataset access for the API.

Cohorts are loaded and validated by ``AnalyticsPipeline`` once per file version (keyed
on modification time and size), so re-running the download script is picked up without
restarting the server, while ordinary requests never re-read the CSV. This module adds
the API-specific views: summary, schema, quality, paginated records and overlap.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass

import pandas as pd

from analytics.data import (
    COLUMNS,
    TARGET,
    Cohort,
    LoadedCohort,
    ValidationReport,
    find_overlap,
)
from analytics.data.dictionary import SOURCE as DICTIONARY_SOURCE
from analytics.pipeline import AnalyticsPipeline, CohortVersion
from app.schemas import dataset as s

PASS_MARK = 10
SOURCE = s.DatasetSource(
    name="UCI Student Performance (ID 320)",
    url="https://archive.ics.uci.edu/dataset/320/student+performance",
    license="CC BY 4.0",
    citation=(
        "Cortez, P., & Silva, A. M. G. (2008). Using Data Mining to Predict Secondary "
        "School Student Performance. FUBUTEC 2008, 5–12."
    ),
)


@dataclass(frozen=True)
class CohortEntry:
    loaded: LoadedCohort
    report: ValidationReport
    #: Lower-cased, space-joined cell values per row, for substring search.
    search_index: pd.Series
    #: The pipeline's cohort version (dataset, statistics, profiles, reports).
    version: CohortVersion


class DatasetStore:
    """API view of the cohorts. Loading, validation and caching live in the pipeline."""

    def __init__(self, pipeline: AnalyticsPipeline) -> None:
        self.pipeline = pipeline
        self.raw_dir = pipeline.raw_dir
        self._entries: dict[Cohort, CohortEntry] = {}
        self._lock = threading.Lock()

    def get(self, cohort: Cohort) -> CohortEntry:
        """The current cohort version (reloaded only when the file changes)."""
        version = self.pipeline.cohort(cohort)  # raises DatasetNotFoundError
        with self._lock:
            entry = self._entries.get(cohort)
            if entry is None or entry.version is not version:
                entry = CohortEntry(
                    loaded=version.loaded,
                    report=version.validation,
                    search_index=version.loaded.raw.fillna("").agg(" ".join, axis=1).str.lower(),
                    version=version,
                )
                self._entries[cohort] = entry
            return entry

    # --- Response builders -------------------------------------------------------

    def summary(self, cohort: Cohort) -> s.DatasetSummary:
        entry = self.get(cohort)
        info, report = entry.loaded.info, entry.report
        present = set(entry.loaded.raw.columns)
        return s.DatasetSummary(
            cohort=cohort,
            subject=info.subject,
            filename=info.filename,
            source=SOURCE,
            rows=report.rows,
            columns=report.columns,
            numerical_columns=sum(
                1 for c in COLUMNS if c.name in present and c.measure == "numerical"
            ),
            categorical_columns=sum(
                1 for c in COLUMNS if c.name in present and c.measure == "categorical"
            ),
            missing_values=report.missing_values,
            duplicate_rows=report.duplicate_rows,
            invalid_values=report.invalid_values,
            validation_status=report.status,
            target=s.TargetInfo(
                name=TARGET.name,
                label=TARGET.label,
                description=TARGET.description,
                minimum=TARGET.minimum or 0,
                maximum=TARGET.maximum or 20,
                pass_mark=PASS_MARK,
                prior_grades=[c.name for c in COLUMNS if c.role == "prior_grade"],
            ),
        )

    def schema(self, cohort: Cohort) -> s.DatasetSchema:
        profiles = {p.name: p for p in self.get(cohort).report.profiles}
        columns = []
        for spec in COLUMNS:
            profile = profiles.get(spec.name)
            columns.append(
                s.ColumnInfo(
                    name=spec.name,
                    position=spec.position,
                    label=spec.label,
                    description=spec.description,
                    group=spec.group,
                    measure=spec.measure,
                    scale=spec.scale,
                    role=spec.role,
                    dtype=spec.dtype,
                    allowed_values=[
                        s.AllowedValueOut(code=v.code, label=v.label) for v in spec.allowed
                    ],
                    minimum=spec.minimum,
                    maximum=spec.maximum,
                    notes=list(spec.notes),
                    observed=s.ObservedColumn(
                        missing=profile.missing,
                        invalid=profile.invalid,
                        unique=profile.unique,
                        minimum=profile.minimum,
                        maximum=profile.maximum,
                    )
                    if profile
                    else None,
                )
            )
        return s.DatasetSchema(cohort=cohort, source=DICTIONARY_SOURCE, columns=columns)

    def quality(self, cohort: Cohort) -> s.DatasetQuality:
        report = self.get(cohort).report
        return s.DatasetQuality(
            cohort=cohort,
            status=report.status,
            rows=report.rows,
            columns=report.columns,
            missing_values=report.missing_values,
            duplicate_rows=report.duplicate_rows,
            invalid_values=report.invalid_values,
            checks=[
                s.QualityCheck(
                    key=c.key,
                    title=c.title,
                    status=c.status,
                    summary=c.summary,
                    affected=c.affected,
                )
                for c in report.checks
            ],
            observations=[
                s.QualityObservation(key=o.key, title=o.title, detail=o.detail, count=o.count)
                for o in report.observations
            ],
            column_issues=[
                s.ColumnQuality(
                    name=p.name,
                    missing=p.missing,
                    invalid=p.invalid,
                    invalid_examples=list(p.invalid_examples),
                )
                for p in report.profiles
                if p.missing or p.invalid
            ],
        )

    def records(
        self, cohort: Cohort, *, page: int, page_size: int, search: str | None
    ) -> s.DatasetRecords:
        entry = self.get(cohort)
        data = entry.loaded.data
        term = (search or "").strip().lower() or None
        if term:
            data = data[entry.search_index.str.contains(term, regex=False)]

        total = len(data)
        start = (page - 1) * page_size
        window = data.iloc[start : start + page_size]
        items = [
            s.DatasetRecord(
                row=int(index) + 1,
                values={k: (None if pd.isna(v) else v) for k, v in row.items()},
            )
            for index, row in zip(window.index, window.to_dict("records"), strict=True)
        ]
        return s.DatasetRecords(
            cohort=cohort,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=max(1, math.ceil(total / page_size)),
            search=term,
            columns=list(data.columns),
            items=items,
        )

    def overlap(self) -> s.CohortOverlap:
        report = find_overlap(
            self.get(Cohort.MATH).loaded.data, self.get(Cohort.PORTUGUESE).loaded.data
        )
        return s.CohortOverlap(
            method=(
                "Rows are matched on the 13 student-descriptive attributes used by UCI's "
                "student-merge.R. There is no student identifier."
            ),
            match_attributes=list(report.match_attributes),
            math_rows=report.math_rows,
            portuguese_rows=report.portuguese_rows,
            join_pairs=report.join_pairs,
            math_rows_matched=report.math_rows_matched,
            portuguese_rows_matched=report.portuguese_rows_matched,
            unambiguous_matches=report.unambiguous_matches,
            ambiguous_profiles=report.ambiguous_profiles,
            caveat=(
                "Matching is approximate. Different students can share all 13 attributes, "
                "so only profiles unique in both files are treated as one-to-one matches. "
                "The plain join count can include the same student more than once."
            ),
        )


def get_store(pipeline: AnalyticsPipeline) -> DatasetStore:
    with _stores_lock:
        if id(pipeline) not in _stores:
            _stores[id(pipeline)] = DatasetStore(pipeline)
        return _stores[id(pipeline)]


_stores: dict[int, DatasetStore] = {}
_stores_lock = threading.Lock()
