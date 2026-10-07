"""Generate docs/DATA_DICTIONARY.md from the data dictionary.

Usage (from backend/):  python -m analytics.data.docgen
"""

from pathlib import Path

from analytics.data.dictionary import COLUMNS, ColumnSpec


def to_markdown() -> str:
    """Render the dictionary as Markdown (used to generate docs/DATA_DICTIONARY.md)."""

    def values(spec: ColumnSpec) -> str:
        if spec.allowed:
            return "<br>".join(f"`{v.code}` {v.label}" for v in spec.allowed)
        return f"{spec.minimum}–{spec.maximum}"

    role_labels = {"feature": "Feature", "prior_grade": "Prior grade", "target": "**Target**"}
    lines = [
        "# Data Dictionary",
        "",
        "<!-- Generated from backend/analytics/data/dictionary.py. Do not edit by hand.",
        "     Regenerate with: cd backend && python -m analytics.data.docgen -->",
        "",
        "UCI Student Performance dataset (ID 320). Both cohorts (`student-mat.csv`,",
        "`student-por.csv`) share the same 33 attributes. Descriptions follow the",
        "`student.txt` notes distributed with the dataset; *Measure* follows the UCI",
        "classification (UCI lists coded ordinal scales such as `Medu` as numeric).",
        "",
        "| # | Column | Description | Group | Measure | Scale | Role | Allowed values / range |",
        "| - | ------ | ----------- | ----- | ------- | ----- | ---- | ---------------------- |",
    ]
    for spec in COLUMNS:
        lines.append(
            f"| {spec.position} | `{spec.name}` | {spec.description} | {spec.group} | "
            f"{spec.measure} | {spec.scale} | {role_labels[spec.role]} | {values(spec)} |"
        )
    lines += ["", "## Notes", ""]
    for spec in COLUMNS:
        for note in spec.notes:
            lines.append(f"- **`{spec.name}`**: {note}")
    lines += _derived_sections()
    lines += [
        "",
        "## Grades",
        "",
        "- `G1`: first-period grade, `G2`: second-period grade, `G3`: final grade.",
        "  All are on the Portuguese 0–20 scale, where 10 is the pass mark.",
        "- `G3` is the primary performance target. `G1` and `G2` are strongly related to it",
        "  and are treated as *prior grades*. They are only valid inputs when a prediction is",
        "  made after those periods (see `docs/METHODOLOGY.md`).",
        "- The dataset contains **no dropout label**, so no attribute here measures dropout.",
        "",
    ]
    return "\n".join(lines)


def _derived_sections() -> list[str]:
    # Imported here: preprocessing depends on the dictionary, not the other way round.
    from analytics.preprocessing import (
        ENGINEERED_FEATURES,
        REJECTED_FEATURES,
        RISK_LABEL,
        RISK_THRESHOLD,
    )

    lines = [
        "",
        "## Derived targets",
        "",
        "Created by `backend/analytics/preprocessing/targets.py`. "
        "Outcomes only — never predictors.",
        "",
        "| Column | Definition | Task |",
        "| ------ | ---------- | ---- |",
        "| `G3` | Final grade, 0–20 (as published) | Regression target |",
        f"| `{RISK_LABEL}` | 1 if `G3` < {RISK_THRESHOLD} (below the pass mark), else 0 | "
        "Classification target: academic risk, **not** dropout |",
        "",
        "## Engineered features",
        "",
        "Created by `backend/analytics/preprocessing/features.py`. Row-wise and stateless.",
        "",
        "| Feature | Definition | Reason | Leakage assessment |",
        "| ------- | ---------- | ------ | ------------------ |",
    ]
    for f in ENGINEERED_FEATURES:
        replaces = f" Replaces `{f.replaces}` in model inputs." if f.replaces else ""
        lines.append(f"| `{f.name}` | {f.definition}{replaces} | {f.reason} | {f.leakage} |")
    lines += ["", "Considered and not added:", ""]
    lines += [f"- **{name}**: {reason}" for name, reason in REJECTED_FEATURES]
    return lines + _grouping_section()


def _grouping_section() -> list[str]:
    from analytics.statistics.groups import GROUPINGS

    lines = [
        "",
        "## Analysis groupings (Phase 4)",
        "",
        "Groups used by statistical comparisons and charts (`analytics/statistics/groups.py`).",
        "They are fixed in advance and never tuned to results. Only these differ from raw codes:",
        "",
        "| Grouping | Groups | Note |",
        "| -------- | ------ | ---- |",
    ]
    for g in GROUPINGS.values():
        if g.note:
            levels = ", ".join(label for _, label in g.levels)
            lines.append(f"| `{g.variable}` | {levels} | {g.note} |")
    return lines


if __name__ == "__main__":  # pragma: no cover
    out = Path(__file__).resolve().parents[3] / "docs" / "DATA_DICTIONARY.md"
    out.write_text(to_markdown(), encoding="utf-8")
    print(f"Wrote {out}")
