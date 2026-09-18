"""P10 parts R and M: reproduction check and median baselines (protocol v1.4; D-064).
Logic: src/evaluation/p10_level_baselines.py. Design: docs/P10_LEVEL_BASELINE_HISTORY_PLAN.md §3–§4.

  python scripts/run_p10_level_baselines.py [--output-root DIR]

Exit code 0 only if every reproduction check passes; otherwise only the check table is written.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation import p5_personalization as P5  # noqa: E402
from src.evaluation import p10_level_baselines as P10  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output-root", type=Path)
    a = ap.parse_args()
    P10.set_output_root(a.output_root)
    P10.load_config()
    print("design:", P10.design_hashes(), flush=True)
    sess = P5.P5Session(echo=False)
    tables, prov = P10.analyse(sess)
    out = P10.write_tables(tables, prov)
    print(f"reproduction: {prov['n_checks']} checks, {prov['n_failed']} failed, max abs diff {prov['max_abs_diff']:.3g}")
    for r in [r for r in tables["reproduction_check"] if not r["passed"]][:40]:
        print("FAILED:", r)
    print(f"wrote {out}")
    return 0 if prov["reproduction_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
