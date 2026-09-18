"""P10 part H: pressure-summary models over 40-s, 300-s and 900-s histories under strict LOSO (protocol v1.4; D-064).
Logic: src/evaluation/p10_history.py. Design: docs/P10_LEVEL_BASELINE_HISTORY_PLAN.md §5–§6.

  python scripts/run_p10_history.py [--output-root DIR]

Requires the passing Part R check (outputs/metrics/p10/p10_level_baselines_provenance.json) and requirements-p10.txt.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation import p5_personalization as P5  # noqa: E402
from src.evaluation import p10_history as H  # noqa: E402
from src.evaluation import p10_level_baselines as LB  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output-root", type=Path)
    a = ap.parse_args()
    LB.set_output_root(a.output_root)
    H.load_history_config()
    rep = LB.metrics_dir() / "p10_level_baselines_provenance.json"
    if not rep.exists() or not json.loads(rep.read_text(encoding="utf-8"))["reproduction_passed"]:
        raise SystemExit("Part R reproduction check has not passed in this output root; Part H refused (plan §3)")
    print("design:", LB.design_hashes(), flush=True)
    sess = P5.P5Session(echo=False)
    tables, prov = H.run(sess, echo=lambda m: print(m, flush=True))
    out = H.write_tables(tables, prov)
    for r in tables["history_interpretation_summary"]:
        print(r)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
