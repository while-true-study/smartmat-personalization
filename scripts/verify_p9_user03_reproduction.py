"""Verify the P9 User03 results by a clean rerun (D-061): rebuild the external artifact in memory (it must equal the
committed manifest), retrain the nine source-only models into a separate root and compare the User03 predictions
bitwise with the reference runs.
  python scripts/verify_p9_user03_reproduction.py --root <dir>
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import p9_user03 as U  # noqa: E402
from src.data.io_guard import write_json  # noqa: E402
from src.evaluation import p3_loso as P3  # noqa: E402
from src.evaluation import p9_external as E  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, required=True)
    a = ap.parse_args()
    man = json.loads(U.manifest_path().read_text(encoding="utf-8"))
    res = U.build(write=False)
    rebuild_ok = (res["summary"]["coverage"] == man["coverage"]
                  and res["summary"]["reconstructed_rows"] == man["reconstructed_rows"]
                  and [s["sha256"] for s in res["summary"]["sources"]] == [s["sha256"] for s in man["sources"]])
    print("artifact rebuild equals the manifest:", rebuild_ok)
    reference = {(c, s): E.load_predictions(c, s) for c in E.CONFIGS for s in (0, 1, 2)}
    ref_root = E.run_root
    E.run_root = lambda: a.root / "runs" / "p9_user03"          # retrain into the separate root
    ew = E.user03_windows()
    sess = P3.P3Session(echo=False)
    src = E.source_windows(sess)
    checks = []
    for c in E.CONFIGS:
        for s in (0, 1, 2):
            E.run_model(sess, src, ew, c, s)
            same = bool(np.array_equal(E.load_predictions(c, s), reference[(c, s)]))
            checks.append({"config_fold": c, "seed": s, "predictions_bitwise_identical": same})
            print(f"config {c} seed {s}: bitwise {same}", flush=True)
    E.run_root = ref_root
    ok = rebuild_ok and all(x["predictions_bitwise_identical"] for x in checks)
    write_json(E.metrics_dir() / "p9_user03_reproduction_check.json",
               {"artifact_rebuild_equals_manifest": rebuild_ok, "runs": checks, "passed": ok,
                "candidate_root": a.root.name})
    print("reproduction:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
