"""Approximate identification of students who appear in both cohorts.

The dataset has no student identifier. UCI's own notes (``student-merge.R``) match
students across the two files by joining on 13 attributes that describe the student
rather than the course. This module applies the same attributes, but reports the
ambiguity a plain join hides: when several students share the same 13 values within
one cohort, a match cannot be attributed to a specific individual.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: Attributes used by UCI's student-merge.R to identify the same student.
MATCH_ATTRIBUTES: tuple[str, ...] = (
    "school",
    "sex",
    "age",
    "address",
    "famsize",
    "Pstatus",
    "Medu",
    "Fedu",
    "Mjob",
    "Fjob",
    "reason",
    "nursery",
    "internet",
)


@dataclass(frozen=True)
class OverlapReport:
    match_attributes: tuple[str, ...]
    math_rows: int
    portuguese_rows: int
    #: Rows in a plain inner join, as UCI's script computes (can count a student twice).
    join_pairs: int
    #: Math rows whose attribute profile appears at least once in the Portuguese file.
    math_rows_matched: int
    #: Portuguese rows whose attribute profile appears at least once in the Math file.
    portuguese_rows_matched: int
    #: Profiles that are unique in both files: the most defensible one-to-one matches.
    unambiguous_matches: int
    #: Matched profiles shared by more than one student in at least one file.
    ambiguous_profiles: int


def _profiles(frame: pd.DataFrame) -> pd.Series:
    return frame[list(MATCH_ATTRIBUTES)].astype(str).agg("|".join, axis=1)


def find_overlap(math: pd.DataFrame, portuguese: pd.DataFrame) -> OverlapReport:
    m, p = _profiles(math), _profiles(portuguese)
    m_counts, p_counts = m.value_counts(), p.value_counts()
    shared = m_counts.index.intersection(p_counts.index)

    unambiguous = int(((m_counts[shared] == 1) & (p_counts[shared] == 1)).sum())
    return OverlapReport(
        match_attributes=MATCH_ATTRIBUTES,
        math_rows=len(math),
        portuguese_rows=len(portuguese),
        join_pairs=int((m_counts[shared] * p_counts[shared]).sum()),
        math_rows_matched=int(m.isin(shared).sum()),
        portuguese_rows_matched=int(p.isin(shared).sum()),
        unambiguous_matches=unambiguous,
        ambiguous_profiles=len(shared) - unambiguous,
    )
