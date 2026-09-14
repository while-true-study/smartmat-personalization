"""Compare a clean-checkout P5 reproduction with the reference P5 runs (criterion fixed in D-045 before any P5 run).

Pass criterion:
  - the nine regenerated P3 base models have weights bitwise identical to the committed plan's hashes;
  - all 45 P5 runs (3 subjects x 5 budgets x seeds 0/1/2): every MAE, RMSE and bias, primary and later span,
    within 1e-6; predictions compared bitwise (reported); identical run identity and frozen-input hashes.
Usage: python scripts/verify_p5_reproduction.py --reference outputs/runs/p5 --candidate <clean>/outputs/runs/p5
       [--candidate-p3 <clean>/outputs/runs/p3]
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
from src.evaluation.p5_personalization import budgets, plan_yaml, seeds, subject_folds, weights_digest  # noqa: E402

TOL = 1e-6
META_KEYS = ("subject", "fold", "budget_nights", "seed", "adaptation_config", "adaptation_nights", "buffer_nights",
             "primary_test_nights", "n_adaptation_windows", "n_test_windows", "protocol_sha256", "split_sha256",
             "canonical_primary_content_sha256", "p3_selected_configs_sha256", "plan_sha256", "weights_sha256")


def metrics(d: Path) -> dict[tuple[str, str, str], float]:
    with open(d / "metrics.csv", encoding="utf-8", newline="") as fh:
        return {(r["span"], r["target"], r["metric"]): float(r["value"]) for r in csv.DictReader(fh)}


def main() -> int:
    import torch
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--candidate-p3", type=Path)
    ap.add_argument("--out", type=Path, default=Path("outputs/metrics/p5/p5_reproduction_check.json"))
    a = ap.parse_args()
    plan = yaml.safe_load(plan_yaml().read_text(encoding="utf-8"))
    rows, ok = [], True
    if a.candidate_p3 is not None:
        for subject, rec in plan["subjects"].items():
            for s, ck in rec["base_checkpoints"].items():
                p = a.candidate_p3 / "final" / f"fold{rec['fold']}_seed{s}" / "model.pt"
                w = weights_digest(torch.load(p, map_location="cpu", weights_only=True))
                same = w == ck["weights_sha256"]
                ok &= same
                rows.append({"run": f"p3/final/fold{rec['fold']}_seed{s}", "weights_identical": same})
                print(f"base fold {rec['fold']} seed {s}: weights {'identical' if same else 'DIFFER'}")
    for subject in sorted(subject_folds(), key=subject_folds().get):
        for b in budgets():
            for s in seeds():
                name = f"{subject}/b{b:02d}_seed{s}"
                ref, cand = a.reference / name, a.candidate / name
                if run_status(cand) != "complete":
                    rows.append({"run": name, "passed": False, "problem": "candidate run not complete"})
                    ok = False
                    print(f"{name}: candidate not complete -> FAIL")
                    continue
                mr, mc = metrics(ref), metrics(cand)
                worst = max(abs(mr[k] - mc[k]) for k in mr)
                pr, pc = read_predictions(ref / "predictions.parquet"), read_predictions(cand / "predictions.parquet")
                bitwise = all(np.array_equal(pr[c], pc[c]) for c in ("y_true", "y_pred", "night_id", "window_start",
                                                                     "device_id", "target", "primary_test"))
                meta_r = json.loads((ref / "run_meta.json").read_text(encoding="utf-8"))
                meta_c = json.loads((cand / "run_meta.json").read_text(encoding="utf-8"))
                meta_diff = [k for k in META_KEYS if meta_r.get(k) != meta_c.get(k)]
                passed = worst <= TOL and not meta_diff
                ok &= passed
                rows.append({"run": name, "tolerance": TOL, "max_abs_diff": worst,
                             "predictions_bitwise_identical": bitwise, "meta_differences": meta_diff,
                             "passed": passed, "candidate_commit": meta_c.get("git_commit"),
                             "candidate_dirty": meta_c.get("git_dirty_tracked_files")})
                print(f"{name}: max |diff| {worst:.3g} bitwise {bitwise} meta {'ok' if not meta_diff else meta_diff}"
                      f" -> {'PASS' if passed else 'FAIL'}")
    write_json(a.out, {"criterion": {"metrics_abs": TOL, "base_weights": "bitwise"}, "passed": ok, "runs": rows})
    print("reproduction:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
