"""Compare a clean-checkout P3 reproduction with the reference P3 runs (criterion fixed before the final runs).

Pass criterion (docs/P3_STRICT_LOSO_BASELINE_REPORT.md §3):
  - final RAW-TCN runs (3 folds x seeds 0/1/2): every MAE and RMSE per target within 1e-6 (°C / %RH);
  - training-mean runs (3 folds): every metric within 1e-9;
  - identical selected configuration, epochs, seeds and frozen-input hashes in run_meta.json.
Usage: python scripts/verify_p3_reproduction.py --reference outputs/runs/p3 --candidate <clean>/outputs/runs/p3
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.io_guard import write_json  # noqa: E402

TOL_FINAL, TOL_MEAN = 1e-6, 1e-9
META_KEYS = ("config", "seed", "fold", "held_out_subject", "final_epochs", "selected_index", "protocol_sha256",
             "split_sha256", "canonical_primary_content_sha256", "p2_tag_commit", "n_train_windows",
             "n_test_windows")


def metrics(d: Path) -> dict[tuple[str, str], float]:
    with open(d / "metrics.csv", encoding="utf-8", newline="") as fh:
        return {(r["target"], r["metric"]): float(r["value"]) for r in csv.DictReader(fh)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("outputs/metrics/p3/reproduction_check.json"))
    a = ap.parse_args()
    runs = [("training_mean", f"fold{f}", TOL_MEAN, ("mae", "rmse", "bias")) for f in (1, 2, 3)]
    runs += [("final", f"fold{f}_seed{s}", TOL_FINAL, ("mae", "rmse")) for f in (1, 2, 3) for s in (0, 1, 2)]
    rows, ok = [], True
    for kind, name, tol, keys in runs:
        ref, cand = a.reference / kind / name, a.candidate / kind / name
        mr, mc = metrics(ref), metrics(cand)
        diffs = {f"{t}/{k}": abs(mr[(t, k)] - mc[(t, k)]) for (t, k) in mr if k in keys}
        worst = max(diffs.values())
        meta_r = json.loads((ref / "run_meta.json").read_text(encoding="utf-8"))
        meta_c = json.loads((cand / "run_meta.json").read_text(encoding="utf-8"))
        meta_diff = [k for k in META_KEYS if meta_r.get(k) != meta_c.get(k)]
        passed = worst <= tol and not meta_diff
        ok &= passed
        rows.append({"run": f"{kind}/{name}", "tolerance": tol, "max_abs_diff": worst, "meta_differences": meta_diff,
                     "passed": passed, "reference_commit": meta_r.get("git_commit"),
                     "candidate_commit": meta_c.get("git_commit"),
                     "candidate_dirty": meta_c.get("git_dirty_tracked_files")})
        print(f"{kind}/{name}: max |diff| {worst:.3g} (tol {tol:g}) meta {'ok' if not meta_diff else meta_diff}"
              f" -> {'PASS' if passed else 'FAIL'}")
    write_json(a.out, {"criterion": {"final_mae_rmse_abs": TOL_FINAL, "training_mean_abs": TOL_MEAN},
                       "passed": ok, "runs": rows})
    print("reproduction:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
