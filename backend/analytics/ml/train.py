"""Train, evaluate, select and persist models for both cohorts.

Usage (from backend/, after downloading the dataset)::

    python -m analytics.ml.train                  # full documented search (several minutes)
    python -m analytics.ml.train --search minimal # quick smoke run (not for reporting)
    python -m analytics.ml.train --report-only    # rewrite docs/ML_RESULTS.md from results

Writes ``models/ml_results.json`` and the selected pipelines under ``models/selected/``.
A full-search run also regenerates ``docs/ML_RESULTS.md``.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from analytics.data import Cohort, load_cohort
from analytics.data.download import DEFAULT_RAW_DIR, verify
from analytics.ml.config import DEFAULT_MODELS_DIR, SearchMode, TrainingConfig
from analytics.ml.persistence import load_results, save
from analytics.ml.report import OUTPUT, render, update_readme
from analytics.ml.training import train_cohort
from analytics.preprocessing import prepare_cohort


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS_DIR)
    parser.add_argument("--search", choices=[m.value for m in SearchMode], default="full")
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument(
        "--report-only", action="store_true", help="Regenerate the report from saved results."
    )
    args = parser.parse_args(argv)

    if args.report_only:
        results = load_results(args.models_dir)
        if results.run.search != SearchMode.FULL:
            print("Saved results come from a minimal search; not reporting.", file=sys.stderr)
            return 1
        OUTPUT.write_text(render(results), encoding="utf-8")
        print(f"Wrote {OUTPUT}")
        if update_readme(results):
            print("Updated the results block in README.md")
        return 0

    if problems := verify(args.raw_dir):
        print("Dataset verification failed:", *problems, sep="\n  ", file=sys.stderr)
        print("Run `python -m analytics.data.download` first.", file=sys.stderr)
        return 1

    config = TrainingConfig(search=SearchMode(args.search), n_jobs=args.n_jobs)
    trained = []
    for cohort in Cohort:
        start = time.perf_counter()
        dataset = prepare_cohort(load_cohort(args.raw_dir, cohort))
        trained.append(train_cohort(dataset, config))
        print(f"{cohort}: trained in {time.perf_counter() - start:.0f}s", flush=True)

    results = save(trained, config, args.models_dir)
    count = sum(len(t.selected) for t in trained)
    print(f"Wrote results and {count} selected models to {args.models_dir}")
    if config.search is SearchMode.FULL:
        OUTPUT.write_text(render(results), encoding="utf-8")
        print(f"Wrote {OUTPUT}")
        if update_readme(results):
            print("Updated the results block in README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
