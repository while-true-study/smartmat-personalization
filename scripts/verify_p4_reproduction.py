"""Compare a clean-checkout P4 reproduction with the reference P4 runs (criterion fixed in D-044 before any P4 run).

Pass criterion:
  - final runs (5 families x 3 folds x seeds 0/1/2 = 45): every MAE and RMSE per target within 1e-6; predictions
    are compared bitwise (reported); identical selected configuration, epochs, seed, inputs and frozen-input hashes;
  - re-run inner runs of every selected configuration (15 x inner A/B = 30): same best epoch, criterion within 1e-9.
Usage: python scripts/verify_p4_reproduction.py --reference outputs/runs/p4 --candidate <clean>/outputs/runs/p4
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.io_guard import write_json  # noqa: E402
from src.evaluation.p3_loso import read_predictions, run_status  # noqa: E402
from src.evaluation.p4_ablation import P4_FAMILIES, family_slug, selected_yaml  # noqa: E402

TOL_FINAL, TOL_INNER = 1e-6, 1e-9
META_KEYS = ("config", "seed", "fold", "held_out_subject", "family", "input_features", "final_epochs",
             "selected_index", "selection_sha256", "protocol_sha256", "split_sha256",
             "canonical_primary_content_sha256", "p2_tag_commit", "p3_tag_commit", "n_train_windows",
             "n_test_windows")


def metrics(d: Path) -> dict[tuple[str, str], float]:
    with open(d / "metrics.csv", encoding="utf-8", newline="") as fh:
        return {(r["target"], r["metric"]): float(r["value"]) for r in csv.DictReader(fh)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("outputs/metrics/p4/p4_reproduction_check.json"))
    a = ap.parse_args()
    doc = yaml.safe_load(selected_yaml().read_text(encoding="utf-8"))
    rows, ok = [], True
    for fam in P4_FAMILIES:
        folds = {int(k): v for k, v in doc["families"][fam]["folds"].items()}
        for f, sel in folds.items():
            for s in (0, 1, 2):
                name = f"{family_slug(fam)}/final/fold{f}_seed{s}"
                ref, cand = a.reference / name, a.candidate / name
                if run_status(cand) != "complete":
                    rows.append({"run": name, "passed": False, "problem": "candidate run not complete"})
                    ok = False
                    continue
                mr, mc = metrics(ref), metrics(cand)
                worst = max(abs(mr[k] - mc[k]) for k in mr if k[1] in ("mae", "rmse"))
                pr, pc = read_predictions(ref / "predictions.parquet"), read_predictions(cand / "predictions.parquet")
                bitwise = all(np.array_equal(pr[c], pc[c]) for c in ("y_true", "y_pred", "subject_id",
                                                                     "window_start", "target"))
                meta_r = json.loads((ref / "run_meta.json").read_text(encoding="utf-8"))
                meta_c = json.loads((cand / "run_meta.json").read_text(encoding="utf-8"))
                meta_diff = [k for k in META_KEYS if meta_r.get(k) != meta_c.get(k)]
                passed = worst <= TOL_FINAL and not meta_diff
                ok &= passed
                rows.append({"run": name, "tolerance": TOL_FINAL, "max_abs_diff": worst,
                             "predictions_bitwise_identical": bitwise, "meta_differences": meta_diff,
                             "passed": passed, "reference_commit": meta_r.get("git_commit"),
                             "candidate_commit": meta_c.get("git_commit"),
                             "candidate_dirty": meta_c.get("git_dirty_tracked_files")})
                print(f"{name}: max |diff| {worst:.3g} bitwise {bitwise} meta {'ok' if not meta_diff else meta_diff}"
                      f" -> {'PASS' if passed else 'FAIL'}")
            for inner in ("A", "B"):
                name = f"{family_slug(fam)}/inner/fold{f}_{inner}_cfg{sel['selected_index']:02d}"
                ref, cand = a.reference / name, a.candidate / name
                if run_status(cand) != "complete":
                    rows.append({"run": name, "passed": False, "problem": "candidate run not complete"})
                    ok = False
                    continue
                rr = json.loads((ref / "result.json").read_text(encoding="utf-8"))
                rc = json.loads((cand / "result.json").read_text(encoding="utf-8"))
                d = abs(rr["best_criterion"] - rc["best_criterion"])
                hist = (ref / "history.csv").read_bytes() == (cand / "history.csv").read_bytes()
                passed = rr["best_epoch"] == rc["best_epoch"] and d <= TOL_INNER
                ok &= passed
                rows.append({"run": name, "tolerance": TOL_INNER, "best_epoch_reference": rr["best_epoch"],
                             "best_epoch_candidate": rc["best_epoch"], "criterion_abs_diff": d,
                             "history_identical": hist, "passed": passed})
                print(f"{name}: best epoch {rr['best_epoch']}/{rc['best_epoch']} |d crit| {d:.3g} history "
                      f"{'identical' if hist else 'differs'} -> {'PASS' if passed else 'FAIL'}")
    write_json(a.out, {"criterion": {"final_mae_rmse_abs": TOL_FINAL, "inner_criterion_abs": TOL_INNER},
                       "passed": ok, "runs": rows})
    print("reproduction:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
