"""The two cohorts published in the UCI Student Performance dataset."""

from dataclasses import dataclass
from enum import StrEnum


class Cohort(StrEnum):
    MATH = "math"
    PORTUGUESE = "portuguese"


@dataclass(frozen=True)
class CohortInfo:
    cohort: Cohort
    subject: str
    filename: str
    #: Row count of the official file, used as a shape check.
    expected_rows: int
    #: SHA-256 of the official CSV, pinned for integrity verification.
    sha256: str


COHORTS: dict[Cohort, CohortInfo] = {
    Cohort.MATH: CohortInfo(
        cohort=Cohort.MATH,
        subject="Mathematics",
        filename="student-mat.csv",
        expected_rows=395,
        sha256="e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80",
    ),
    Cohort.PORTUGUESE: CohortInfo(
        cohort=Cohort.PORTUGUESE,
        subject="Portuguese language",
        filename="student-por.csv",
        expected_rows=649,
        sha256="a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f",
    ),
}
