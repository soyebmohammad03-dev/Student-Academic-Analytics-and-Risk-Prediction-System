"""Small, clearly synthetic cohort files for tests. Not real student data."""

from __future__ import annotations

import csv
from pathlib import Path

from analytics.data.dictionary import COLUMN_NAMES

VALID_ROW: dict[str, str | int] = {
    "school": "GP", "sex": "F", "age": 17, "address": "U", "famsize": "GT3",
    "Pstatus": "T", "Medu": 2, "Fedu": 3, "Mjob": "services", "Fjob": "other",
    "reason": "course", "guardian": "mother", "traveltime": 1, "studytime": 2,
    "failures": 0, "schoolsup": "no", "famsup": "yes", "paid": "no",
    "activities": "yes", "nursery": "yes", "higher": "yes", "internet": "yes",
    "romantic": "no", "famrel": 4, "freetime": 3, "goout": 3, "Dalc": 1, "Walc": 2,
    "health": 4, "absences": 0, "G1": 11, "G2": 12, "G3": 12,
}  # fmt: skip


def make_rows(count: int, **overrides) -> list[dict[str, str | int]]:
    """Distinct valid rows (absences varies so no two rows are identical)."""
    return [{**VALID_ROW, "absences": i, **overrides} for i in range(count)]


def write_cohort(path: Path, rows: list[dict], columns: list[str] | None = None) -> Path:
    """Write rows in the UCI layout: ';' separated, text values quoted."""
    columns = columns or list(COLUMN_NAMES)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";", quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([row.get(c, "") for c in columns])
    return path
