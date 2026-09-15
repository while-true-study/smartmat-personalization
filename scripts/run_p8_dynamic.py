"""P8 final dynamic-signal diagnostic (protocol v1.2 addendum; D-059). Logic: src/evaluation/p8_dynamic.py.

Design fixed in docs/P8_DYNAMIC_SIGNAL_PLAN.md and configs/experiments/v1.2/dynamic_signal_diagnostic.yaml before any
of the new metrics was computed. Reads existing predictions only (P5 runs, v1.1 control runs, frozen v1.1 tables);
the adaptation-only affine comparator runs only if the pre-specified trigger fires.
  python scripts/run_p8_dynamic.py [--output-root DIR]     DIR: clean invocation into a separate output root
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation import p8_dynamic as PD  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output-root", type=Path)
    a = ap.parse_args()
    PD.set_output_root(a.output_root)
    PD.load_config()
    print("design:", PD.design_hashes())
    tables, prov = PD.analyse()
    out = PD.write_tables(tables, prov)
    print("checks:", {k: v for k, v in prov["checks"].items() if not k.startswith("User")})
    print("affine trigger fired:", prov["affine_trigger"]["fired"],
          {t: v["qualifying_subjects"] for t, v in prov["affine_trigger"]["per_target"].items()})
    for h in tables["headlines"]:
        print(f"{h['condition']} b={h['budget_nights']} {h['target']}: {h['headline']} "
              f"(within {h['subjects_within_positive']}/3, pooled {h['subjects_pooled_positive']}/3)")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
