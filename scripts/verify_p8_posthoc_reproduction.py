"""Compare a clean rerun of the P8 post-hoc analyses with the reference outputs (D-057).

The candidate is produced by `python scripts/run_p8_posthoc.py all --output-root <dir>`: fresh initialization-control
runs and a fresh analysis from the same frozen P3/P5 inputs. Pass criterion:
  - every p8_*.csv metrics table: identical columns and rows, numeric cells within 1e-9 (reported: byte identity);
  - the nine control runs: final weights and predictions bitwise identical, identical design hashes;
  - identical design hashes and checks in the provenance.
Usage: python scripts/verify_p8_posthoc_reproduction.py --candidate <dir> [--reference outputs]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.io_guard import write_json  # noqa: E402
from src.evaluation import p5_personalization as P5  # noqa: E402
from src.evaluation.p3_loso import read_predictions, run_status  # noqa: E402

TOL = 1e-9
TABLES = ("by_seed", "summary", "not_estimable", "bootstrap", "loso", "loso_summary", "interpretation")


def read(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def cell_diff(a: str, b: str) -> float:
    if a == b:
        return 0.0
    try:
        return abs(float(a) - float(b))
    except ValueError:
        return float("inf")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference", type=Path, default=Path("outputs"))
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("outputs/metrics/p8_posthoc/p8_reproduction_check.json"))
    a = ap.parse_args()
    ok, rows = True, []
    for name in TABLES:
        ref, cand = (d / "metrics" / "p8_posthoc" / f"p8_{name}.csv" for d in (a.reference, a.candidate))
        r, c = read(ref), read(cand)
        same_shape = len(r) == len(c) and (not r or list(r[0]) == list(c[0]))
        worst = max((cell_diff(x[k], y[k]) for x, y in zip(r, c) for k in x), default=0.0) if same_shape else \
            float("inf")
        byte = ref.read_bytes() == cand.read_bytes()
        passed = same_shape and worst <= TOL
        ok &= passed
        rows.append({"table": f"p8_{name}.csv", "rows": len(r), "max_abs_diff": worst, "byte_identical": byte,
                     "passed": passed})
        print(f"p8_{name}.csv: {len(r)} rows, max |diff| {worst:.3g}, byte-identical {byte} -> "
              f"{'PASS' if passed else 'FAIL'}")
    pr, pc = (json.loads((d / "metrics" / "p8_posthoc" / "p8_posthoc_provenance.json").read_text(encoding="utf-8"))
              for d in (a.reference, a.candidate))
    frozen = lambda p: {k: v for k, v in p["inputs_sha256"].items() if k.startswith("p5/")}  # noqa: E731
    # control prediction files embed their run id, so their file digests differ; they are compared bitwise below
    design_same = pr["design"] == pc["design"] and pr["identities"] == pc["identities"] and frozen(pr) == frozen(pc) \
        and pr["checks"] == pc["checks"]
    ok &= design_same
    rows.append({"provenance": "design, identities and input digests identical", "passed": design_same})
    print(f"provenance design/identities/inputs identical: {design_same}")
    for subject in sorted(P5.subject_folds(), key=P5.subject_folds().get):
        for s in P5.seeds():
            rel = Path("runs") / "p8_posthoc" / "init_control" / subject / f"b14_seed{s}"
            dr, dc = a.reference / rel, a.candidate / rel
            if run_status(dc) != "complete":
                ok = False
                rows.append({"run": rel.as_posix(), "passed": False, "problem": "candidate run not complete"})
                print(f"{rel.as_posix()}: candidate not complete -> FAIL")
                continue
            mr, mc = (json.loads((d / "run_meta.json").read_text(encoding="utf-8")) for d in (dr, dc))
            weights = mr["weights_sha256"] == mc["weights_sha256"] and mr["init_weights_sha256"] == \
                mc["init_weights_sha256"]
            p_r, p_c = read_predictions(dr / "predictions.parquet"), read_predictions(dc / "predictions.parquet")
            bitwise = all(np.array_equal(p_r[k], p_c[k]) for k in ("y_true", "y_pred", "device_id", "window_start",
                                                                    "night_ordinal", "target"))
            hashes = all(mr[k] == mc[k] for k in ("plan_sha256_lf", "addendum_sha256_lf", "base_protocol_sha256",
                                                  "split_sha256", "canonical_primary_content_sha256"))
            passed = weights and bitwise and hashes
            ok &= passed
            rows.append({"run": rel.as_posix(), "weights_identical": weights, "predictions_bitwise": bitwise,
                         "design_hashes_identical": hashes, "passed": passed})
            print(f"{rel.as_posix()}: weights {weights} predictions {bitwise} hashes {hashes} -> "
                  f"{'PASS' if passed else 'FAIL'}")
    write_json(a.out, {"criterion": {"tables_abs": TOL, "control": "weights and predictions bitwise"},
                       "candidate_root": a.candidate.name, "passed": ok, "checks": rows})
    print("reproduction:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
