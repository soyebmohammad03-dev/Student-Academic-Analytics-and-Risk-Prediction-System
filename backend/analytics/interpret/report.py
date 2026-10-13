"""Render docs/INTERPRETABILITY.md from the interpretability run and the cohort data.

Every number is computed: global importance from ``models/interpretability.json`` and
group-level risk profiles from the official files. A test checks the committed copy.
"""

from __future__ import annotations

from pathlib import Path

from analytics.interpret.results import ImportanceResult, InterpretabilityRun
from analytics.risk.results import RiskProfiles

OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "INTERPRETABILITY.md"
TOP = 8
SUBJECT = {"math": "Mathematics", "portuguese": "Portuguese language"}


def _f(value, digits=3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _column(result: ImportanceResult) -> list[str]:
    cells = []
    for item in [i for i in result.items if i.value != 0][:TOP]:
        value = (
            f"{item.value:+.3f}" if result.method == "standardised_coefficient" else _f(item.value)
        )
        cells.append(f"{item.label} ({value})")
    return cells


def _importance_lines(run: InterpretabilityRun, cohort: str) -> list[str]:
    lines = ["### Global feature importance", ""]
    for item in (i for i in run.items if i.cohort == cohort):
        lines += [f"#### {item.task} · {item.scenario} · {item.model_label}", ""]
        headers = [m.method_label for m in item.methods]
        columns = [_column(m) for m in item.methods]
        lines += [
            "| Rank | " + " | ".join(headers) + " |",
            "| --- | " + " | ".join("---" for _ in headers) + " |",
        ]
        for rank in range(max(len(c) for c in columns)):
            cells = [c[rank] if rank < len(c) else "" for c in columns]
            lines.append(f"| {rank + 1} | " + " | ".join(cells) + " |")
        lines += [
            "",
            "Attributes with a value of exactly 0 (not used by the model) are omitted.",
            "",
            "Units and data:",
            "",
        ]
        lines += [f"- *{m.method_label}*: {m.unit}. {m.data}" for m in item.methods]
        lines.append("")
        if item.calibration:
            c = item.calibration
            lines += [
                f"Probability calibration on the test set (n = {c.n}): mean predicted "
                f"{c.mean_predicted:.3f} vs observed at-risk rate {c.observed_rate:.3f}; "
                f"Brier score {c.brier:.3f}.",
                "",
                "| Predicted probability | n | Mean predicted | Observed rate |",
                "| --- | --- | --- | --- |",
                *(
                    f"| {b.low:.1f}–{b.high:.1f} | {b.n} | {_f(b.mean_predicted)} "
                    f"| {_f(b.observed_rate)} |"
                    for b in c.bins
                ),
                "",
            ]
    return lines


def _profile_lines(p: RiskProfiles) -> list[str]:
    lines = [
        "### Academic-risk profiles (group-level statistics)",
        "",
        f"Cohort: {p.at_risk} of {p.n} students below the pass mark ({p.risk_percent:.1f}%, "
        f"95% CI {100 * p.risk_ci.low:.1f}–{100 * p.risk_ci.high:.1f}%).",
        "",
        "| Attribute | Group | n | At risk | 95% CI | Reliable |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for s in p.single:
        for g in s.groups:
            lines.append(
                f"| {s.label} | {g.label} | {g.n} | {g.risk_percent:.1f}% "
                f"| {100 * g.risk_ci.low:.1f}–{100 * g.risk_ci.high:.1f}% "
                f"| {'yes' if g.reliable else 'no'} |"
            )
    lines += [
        "",
        "| Attribute | Test | Cramér's V | p (BH-adjusted) |",
        "| --- | --- | --- | --- |",
        *(
            f"| {s.label} | {s.test} | {_f(s.cramers_v)} ({s.magnitude}) | {_f(s.p_adjusted)} |"
            for s in p.single
        ),
        "",
    ]
    for pair in p.pairs:
        lines += [
            f"**{pair.rows_label} × {pair.columns_label}** (at-risk %, n):",
            "",
        ]
        columns = list(dict.fromkeys((c.column, c.column_label) for c in pair.cells))
        rows = list(dict.fromkeys((c.row, c.row_label) for c in pair.cells))
        lines += [
            "| | " + " | ".join(label for _, label in columns) + " |",
            "| --- | " + " | ".join("---" for _ in columns) + " |",
        ]
        for r_key, r_label in rows:
            cells = []
            for c_key, _ in columns:
                cell = next(c for c in pair.cells if c.row == r_key and c.column == c_key)
                if cell.risk_percent is None:
                    cells.append("— (0)")
                else:
                    mark = "" if cell.reliable else "†"
                    cells.append(f"{cell.risk_percent:.0f}% ({cell.n}){mark}")
            lines.append(f"| {r_label} | " + " | ".join(cells) + " |")
        lines.append("")
        if any(not c.reliable and c.n for c in pair.cells):
            lines += ["† fewer than 10 students.", ""]
    lines += [f"- {n}" for n in p.notes] + [""]
    return lines


def render(run: InterpretabilityRun, profiles: dict[str, RiskProfiles]) -> str:
    lines = [
        "# Interpretability and academic-risk analysis",
        "",
        "> Generated by `python -m analytics.interpret.build` from the persisted models and "
        "the official UCI files. Do not edit by hand. Methodology: "
        "[METHODOLOGY.md §7](METHODOLOGY.md"
        "#7-interpretability-and-academic-risk-analysis-phase-6).",
        "",
        "Everything here describes **how the selected models use their inputs** or **what "
        "is observed across groups of students**. Nothing here is causal. Importance "
        "values from different methods have different units and are not compared with "
        "each other. Academic risk means a final grade below 10; it is not dropout.",
        "",
        f"Permutation repeats: {run.permutation_repeats}. Shapley samples per test student: "
        f"{run.shapley_samples}. Seed: {run.random_state}.",
        "",
    ]
    for cohort, subject in SUBJECT.items():
        if not any(i.cohort == cohort for i in run.items):
            continue
        lines += [f"## {subject}", ""]
        lines += _importance_lines(run, cohort)
        if cohort in profiles:
            lines += _profile_lines(profiles[cohort])
    return "\n".join(lines)
