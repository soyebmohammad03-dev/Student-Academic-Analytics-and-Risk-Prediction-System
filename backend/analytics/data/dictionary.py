"""Data dictionary for the UCI Student Performance dataset (UCI ID 320).

Descriptions, codes and ranges follow the attribute notes shipped with the dataset
(``student.txt`` inside the official archive). This module is the single source of
truth for column metadata: validation, the API and ``docs/DATA_DICTIONARY.md``
(via ``analytics.data.docgen``) are all derived from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Measure = Literal["categorical", "numerical"]
Scale = Literal["binary", "nominal", "ordinal", "count", "grade"]
Role = Literal["feature", "prior_grade", "target"]
Group = Literal[
    "Demographic",
    "Family background",
    "School and study",
    "Social and lifestyle",
    "Health",
    "Grades",
]

SOURCE = "UCI Student Performance (ID 320), attribute notes in student.txt"


@dataclass(frozen=True)
class AllowedValue:
    code: str | int
    label: str


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    label: str
    description: str
    group: Group
    measure: Measure
    scale: Scale
    role: Role = "feature"
    #: Explicit codes for categorical and coded-ordinal columns.
    allowed: tuple[AllowedValue, ...] = ()
    #: Inclusive documented range for numerical columns.
    minimum: int | None = None
    maximum: int | None = None
    #: 1-based column position in the CSV files.
    position: int = 0
    notes: tuple[str, ...] = field(default=())

    @property
    def dtype(self) -> Literal["string", "integer"]:
        return "string" if self.measure == "categorical" else "integer"

    @property
    def allowed_codes(self) -> frozenset[str | int]:
        return frozenset(v.code for v in self.allowed)


def _codes(*pairs: tuple[str | int, str]) -> tuple[AllowedValue, ...]:
    return tuple(AllowedValue(code, label) for code, label in pairs)


_YES_NO = _codes(("yes", "Yes"), ("no", "No"))
_EDUCATION = _codes(
    (0, "None"),
    (1, "Primary education (4th grade)"),
    (2, "5th to 9th grade"),
    (3, "Secondary education"),
    (4, "Higher education"),
)
_JOBS = _codes(
    ("teacher", "Teacher"),
    ("health", "Health care related"),
    ("services", "Civil services (e.g. administrative or police)"),
    ("at_home", "At home"),
    ("other", "Other"),
)
_LOW_HIGH = _codes((1, "Very low"), (2, "Low"), (3, "Medium"), (4, "High"), (5, "Very high"))

COLUMNS: tuple[ColumnSpec, ...] = (
    ColumnSpec(
        "school",
        "School",
        "Student's school.",
        "Demographic",
        "categorical",
        "binary",
        allowed=_codes(("GP", "Gabriel Pereira"), ("MS", "Mousinho da Silveira")),
        position=1,
    ),
    ColumnSpec(
        "sex",
        "Sex",
        "Student's sex.",
        "Demographic",
        "categorical",
        "binary",
        allowed=_codes(("F", "Female"), ("M", "Male")),
        position=2,
    ),
    ColumnSpec(
        "age",
        "Age",
        "Student's age in years.",
        "Demographic",
        "numerical",
        "count",
        minimum=15,
        maximum=22,
        position=3,
    ),
    ColumnSpec(
        "address",
        "Home address type",
        "Student's home address type.",
        "Demographic",
        "categorical",
        "binary",
        allowed=_codes(("U", "Urban"), ("R", "Rural")),
        position=4,
    ),
    ColumnSpec(
        "famsize",
        "Family size",
        "Family size.",
        "Family background",
        "categorical",
        "binary",
        allowed=_codes(("LE3", "Less than or equal to 3"), ("GT3", "Greater than 3")),
        position=5,
    ),
    ColumnSpec(
        "Pstatus",
        "Parents' cohabitation",
        "Parent's cohabitation status.",
        "Family background",
        "categorical",
        "binary",
        allowed=_codes(("T", "Living together"), ("A", "Apart")),
        position=6,
    ),
    ColumnSpec(
        "Medu",
        "Mother's education",
        "Mother's education level.",
        "Family background",
        "numerical",
        "ordinal",
        allowed=_EDUCATION,
        minimum=0,
        maximum=4,
        position=7,
    ),
    ColumnSpec(
        "Fedu",
        "Father's education",
        "Father's education level.",
        "Family background",
        "numerical",
        "ordinal",
        allowed=_EDUCATION,
        minimum=0,
        maximum=4,
        position=8,
    ),
    ColumnSpec(
        "Mjob",
        "Mother's job",
        "Mother's job.",
        "Family background",
        "categorical",
        "nominal",
        allowed=_JOBS,
        position=9,
    ),
    ColumnSpec(
        "Fjob",
        "Father's job",
        "Father's job.",
        "Family background",
        "categorical",
        "nominal",
        allowed=_JOBS,
        position=10,
    ),
    ColumnSpec(
        "reason",
        "Reason for school choice",
        "Reason to choose this school.",
        "School and study",
        "categorical",
        "nominal",
        allowed=_codes(
            ("home", "Close to home"),
            ("reputation", "School reputation"),
            ("course", "Course preference"),
            ("other", "Other"),
        ),
        position=11,
    ),
    ColumnSpec(
        "guardian",
        "Guardian",
        "Student's guardian.",
        "Family background",
        "categorical",
        "nominal",
        allowed=_codes(("mother", "Mother"), ("father", "Father"), ("other", "Other")),
        position=12,
    ),
    ColumnSpec(
        "traveltime",
        "Travel time",
        "Home to school travel time.",
        "School and study",
        "numerical",
        "ordinal",
        allowed=_codes(
            (1, "Less than 15 minutes"),
            (2, "15 to 30 minutes"),
            (3, "30 minutes to 1 hour"),
            (4, "More than 1 hour"),
        ),
        minimum=1,
        maximum=4,
        position=13,
    ),
    ColumnSpec(
        "studytime",
        "Weekly study time",
        "Weekly study time.",
        "School and study",
        "numerical",
        "ordinal",
        allowed=_codes(
            (1, "Less than 2 hours"),
            (2, "2 to 5 hours"),
            (3, "5 to 10 hours"),
            (4, "More than 10 hours"),
        ),
        minimum=1,
        maximum=4,
        position=14,
    ),
    ColumnSpec(
        "failures",
        "Past class failures",
        "Number of past class failures (n if 1 <= n < 3, else 4).",
        "School and study",
        "numerical",
        "count",
        minimum=0,
        maximum=4,
        position=15,
        notes=(
            "UCI documents values of 3 or more as coded 4, but the published files "
            "contain 0-3 and no 4. Treat 3 as '3 or more' unless evidence suggests otherwise.",
        ),
    ),
    ColumnSpec(
        "schoolsup",
        "Extra educational support",
        "Extra educational support from the school.",
        "School and study",
        "categorical",
        "binary",
        allowed=_YES_NO,
        position=16,
    ),
    ColumnSpec(
        "famsup",
        "Family educational support",
        "Family educational support.",
        "Family background",
        "categorical",
        "binary",
        allowed=_YES_NO,
        position=17,
    ),
    ColumnSpec(
        "paid",
        "Extra paid classes",
        "Extra paid classes within the course subject (Math or Portuguese).",
        "School and study",
        "categorical",
        "binary",
        allowed=_YES_NO,
        position=18,
    ),
    ColumnSpec(
        "activities",
        "Extra-curricular activities",
        "Extra-curricular activities.",
        "Social and lifestyle",
        "categorical",
        "binary",
        allowed=_YES_NO,
        position=19,
    ),
    ColumnSpec(
        "nursery",
        "Attended nursery school",
        "Attended nursery school.",
        "School and study",
        "categorical",
        "binary",
        allowed=_YES_NO,
        position=20,
    ),
    ColumnSpec(
        "higher",
        "Wants higher education",
        "Wants to take higher education.",
        "School and study",
        "categorical",
        "binary",
        allowed=_YES_NO,
        position=21,
    ),
    ColumnSpec(
        "internet",
        "Internet at home",
        "Internet access at home.",
        "Family background",
        "categorical",
        "binary",
        allowed=_YES_NO,
        position=22,
    ),
    ColumnSpec(
        "romantic",
        "Romantic relationship",
        "With a romantic relationship.",
        "Social and lifestyle",
        "categorical",
        "binary",
        allowed=_YES_NO,
        position=23,
    ),
    ColumnSpec(
        "famrel",
        "Family relationships",
        "Quality of family relationships, from 1 (very bad) to 5 (excellent).",
        "Family background",
        "numerical",
        "ordinal",
        allowed=_codes((1, "Very bad"), (2, "Bad"), (3, "Average"), (4, "Good"), (5, "Excellent")),
        minimum=1,
        maximum=5,
        position=24,
    ),
    ColumnSpec(
        "freetime",
        "Free time",
        "Free time after school, from 1 (very low) to 5 (very high).",
        "Social and lifestyle",
        "numerical",
        "ordinal",
        allowed=_LOW_HIGH,
        minimum=1,
        maximum=5,
        position=25,
    ),
    ColumnSpec(
        "goout",
        "Going out",
        "Going out with friends, from 1 (very low) to 5 (very high).",
        "Social and lifestyle",
        "numerical",
        "ordinal",
        allowed=_LOW_HIGH,
        minimum=1,
        maximum=5,
        position=26,
    ),
    ColumnSpec(
        "Dalc",
        "Workday alcohol use",
        "Workday alcohol consumption, from 1 (very low) to 5 (very high).",
        "Social and lifestyle",
        "numerical",
        "ordinal",
        allowed=_LOW_HIGH,
        minimum=1,
        maximum=5,
        position=27,
    ),
    ColumnSpec(
        "Walc",
        "Weekend alcohol use",
        "Weekend alcohol consumption, from 1 (very low) to 5 (very high).",
        "Social and lifestyle",
        "numerical",
        "ordinal",
        allowed=_LOW_HIGH,
        minimum=1,
        maximum=5,
        position=28,
    ),
    ColumnSpec(
        "health",
        "Health status",
        "Current health status, from 1 (very bad) to 5 (very good).",
        "Health",
        "numerical",
        "ordinal",
        allowed=_codes((1, "Very bad"), (2, "Bad"), (3, "Average"), (4, "Good"), (5, "Very good")),
        minimum=1,
        maximum=5,
        position=29,
    ),
    ColumnSpec(
        "absences",
        "School absences",
        "Number of school absences.",
        "School and study",
        "numerical",
        "count",
        minimum=0,
        maximum=93,
        position=30,
    ),
    ColumnSpec(
        "G1",
        "First period grade",
        "First period grade in the course subject (Math or Portuguese).",
        "Grades",
        "numerical",
        "grade",
        role="prior_grade",
        minimum=0,
        maximum=20,
        position=31,
        notes=("Known after the first period. Only a legitimate input in scenarios A and B.",),
    ),
    ColumnSpec(
        "G2",
        "Second period grade",
        "Second period grade in the course subject (Math or Portuguese).",
        "Grades",
        "numerical",
        "grade",
        role="prior_grade",
        minimum=0,
        maximum=20,
        position=32,
        notes=("Known after the second period. Only a legitimate input in scenario A.",),
    ),
    ColumnSpec(
        "G3",
        "Final grade",
        "Final year grade in the course subject (Math or Portuguese); the output target.",
        "Grades",
        "numerical",
        "grade",
        role="target",
        minimum=0,
        maximum=20,
        position=33,
        notes=(
            "Primary performance target. Never used as an input to predict itself or a "
            "label derived from it.",
            "A value of 0 is within the documented range but may indicate a student who "
            "did not sit the final evaluation. Rows are kept and count as at risk "
            "(Phase 3); a sensitivity check is planned for Phase 5.",
        ),
    ),
)

COLUMN_NAMES: tuple[str, ...] = tuple(c.name for c in COLUMNS)
COLUMNS_BY_NAME: dict[str, ColumnSpec] = {c.name: c for c in COLUMNS}
TARGET = COLUMNS_BY_NAME["G3"]
