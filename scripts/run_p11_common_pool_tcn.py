"""P11: retrain the frozen RAW-TCN on the P10 common endpoints and compare on the common test endpoints (protocol v1.5;
D-066). Logic: src/evaluation/p11_common_pool_tcn.py. Design: docs/P11_COMMON_POOL_TCN_PLAN.md.

  python scripts/run_p11_common_pool_tcn.py [--output-root DIR]

Post hoc and exploratory. Requires the committed P3 final predictions and the P10 Part H outputs; it reads them and
changes none of them. Complete runs are skipped on a re-run; the epoch selection is immutable once written.
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")      # before CUDA starts (deterministic cuBLAS)

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation import p5_personalization as P5  # noqa: E402
from src.evaluation import p11_common_pool_tcn as P11  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output-root", type=Path)
    a = ap.parse_args()
    P11.set_output_root(a.output_root)
    print("design:", P11.design_hashes(), flush=True)
    sess = P5.P5Session(echo=False)
    tables, val, prov = P11.run(sess, echo=lambda m: print(m, flush=True))
    out = P11.write_outputs(tables, val, prov)
    for r in tables["interpretation"]:
        if r["subject_id"] == "ALL":
            print(r)
    print(f"validation passed: {val['passed']}; wrote {out}")
    return 0 if val["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
