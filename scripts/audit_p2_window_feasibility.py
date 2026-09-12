"""P2 structural window-feasibility audit (docs/P2_PROTOCOL_FREEZE_REPORT.md §5).

Canonical-only. Compares the three candidate window representations on structure alone: timestamps, continuity,
coverage kept, window counts and label availability (validity flags). No target value, model, loss or error metric
is computed; window candidates are never chosen by model performance.

Output: outputs/qa/p2/window_feasibility.csv (+ .json with run metadata). Not committed.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.evaluation.canonical_input import verify_canonical  # noqa: E402
from src.evaluation.p2_protocol import load_structure, window_feasibility  # noqa: E402
from src.evaluation.protocol import load_protocol, window_spec  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=0, help="recorded for convention; the audit uses no randomness")
    args = ap.parse_args()
    t0 = time.time()
    before = verify_canonical()
    st = load_structure(with_flags=True)
    rows = []
    durations = [load_protocol()["window"]["duration_s"], *load_protocol()["window"]["sensitivity_candidates_s"]]
    for d in durations:
        spec = window_spec(d)
        for r in window_feasibility(st, spec):
            rows.append({"duration_s": d, "stride_s": spec.stride_s, "n_steps": spec.n_steps, **r})
    if verify_canonical() != before:
        print("ERROR: canonical_v1 changed during the run", file=sys.stderr)
        return 3
    out = paths.repo_path("outputs/qa/p2")
    cols = list(dict.fromkeys(k for r in rows for k in r))
    write_csv(out / "window_feasibility.csv", [{k: r.get(k) for k in cols} for r in rows], cols)
    write_json(out / "window_feasibility.json", {"seed": args.seed, "input": before, "durations_s": durations,
                                                  "runtime_s": round(time.time() - t0, 1)})
    print(f"window feasibility: {len(rows)} rows -> outputs/qa/p2/window_feasibility.csv ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
