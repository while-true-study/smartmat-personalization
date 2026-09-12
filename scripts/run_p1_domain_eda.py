"""P1 domain-shift EDA (research/p1-domain-eda). Canonical-only: reads data/interim/canonical_v1/primary.parquet.

Verifies the canonical files against their build record before and after the run, refuses raw paths, and writes
descriptive tables and figures to outputs/eda/p1/ (regenerable, not committed). No model, split, window,
resampling, normalisation or clipping.

Outputs: domain_slice_summary.csv, pressure_distribution.csv, target_distribution.csv, domain_distance_matrix.csv,
monthly_distribution.csv, time_of_night_summary.csv, control_event_summary.csv, pressure_target_relation.csv,
figures/*.png, p1_run_meta.json
"""
from __future__ import annotations

import argparse
import platform
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pyarrow as pa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.evaluation.canonical_input import load_primary, verify_canonical  # noqa: E402
from src.evaluation.p1_eda import COLUMNS, run_all  # noqa: E402

TABLES = ("domain_slice_summary", "pressure_distribution", "target_distribution", "domain_distance_matrix",
          "monthly_distribution", "time_of_night_summary", "control_event_summary", "pressure_target_relation")


def columns(rows: list[dict]) -> list[str]:
    cols: list[str] = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    return cols


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=0, help="recorded for convention; the EDA uses no randomness")
    ap.add_argument("--no-figures", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    before = verify_canonical()
    res = run_all(load_primary(COLUMNS))
    out = paths.repo_path("outputs/eda/p1")
    for name in TABLES:
        write_csv(out / f"{name}.csv", res[name], columns(res[name]))
    figs = []
    if not args.no_figures:
        from src.evaluation.p1_figures import make_all
        figs = make_all(res, out / "figures")
    after = verify_canonical()
    if after != before:
        print("ERROR: canonical_v1 changed during the run", file=sys.stderr)
        return 3
    write_json(out / "p1_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"), "seed": args.seed,
        "input": before, "input_unchanged_after_run": after == before, "tables": list(TABLES), "figures": figs,
        "python": platform.python_version(), "numpy": np.__version__, "pyarrow": pa.__version__,
        "runtime_s": round(time.time() - t0, 1)})
    print(f"P1 EDA done in {time.time() - t0:.0f} s -> outputs/eda/p1 ({len(TABLES)} tables, {len(figs)} figures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
