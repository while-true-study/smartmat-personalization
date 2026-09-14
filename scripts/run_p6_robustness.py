"""P6 robustness and uncertainty analysis (analysis-only; D-047). Logic: src/evaluation/p6_robustness.py.

Reads frozen artifacts only (committed P5 tables, the P5 plan, the P5 run predictions and canonical_v1) and writes
outputs/metrics/p6/p6_*.csv plus p6_provenance.json. Nothing is trained, selected or re-evaluated.
  python scripts/run_p6_robustness.py            all analyses (A: bootstrap; B: drift, level, device/context)
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.evaluation import p5_personalization as P5  # noqa: E402
from src.evaluation import p6_robustness as P6  # noqa: E402
from src.evaluation import splits as S  # noqa: E402
from src.evaluation.p3_loso import read_predictions, run_status, sha256_file  # noqa: E402

CONSISTENCY_TOL = 1e-9


def write(name: str, rows: list[dict]) -> None:
    cols = list(dict.fromkeys(k for r in rows for k in r))
    write_csv(P6.metrics_dir() / f"p6_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)


def user02_predictions() -> tuple[dict, dict]:
    preds, shas = {}, {}
    for b in P5.budgets():
        for s in P5.seeds():
            d = P5.run_dir("User02", b, s)
            if run_status(d) != "complete":
                raise P6.P6Error(f"P5 run {d.name} is not verifiably complete")
            pr = read_predictions(d / "predictions.parquet")
            t, h = pr["target"] == "temperature", pr["target"] == "humidity"
            prim = pr["primary_test"][t].astype(bool)
            y = np.stack([pr["y_true"][t], pr["y_true"][h]], 1)[prim]
            p = np.stack([pr["y_pred"][t], pr["y_pred"][h]], 1)[prim]
            prov = {"device_id": pr["device_id"][t][prim].astype(str), "night_id": pr["night_id"][t][prim].astype(str),
                    "channel_quality_phase": pr["channel_quality_phase"][t][prim].astype(str),
                    "target_ts": pr["target_timestamp"][t][prim].astype("datetime64[s]").astype(np.int64)}
            preds[(b, s)] = (y, p, prov)
            shas[f"User02/b{b:02d}_seed{s}"] = sha256_file(d / "predictions.parquet")
    return preds, shas


def main() -> int:
    tables = P6.tables_dir()
    rows = P6.load_per_night()
    by_seed = P6.read_csv(tables / "p5_by_seed.csv")
    worst = P6.consistency_with_p5(rows, by_seed)
    if worst > CONSISTENCY_TOL:
        raise P6.P6Error(f"per-night table does not reproduce the P5 per-seed metrics (max |diff| {worst:g})")
    print(f"per-night table reproduces P5 primary per-seed metrics: max |diff| {worst:.2g}")

    # A.1 night-level paired bootstrap (seed 0 primary; seeds 1/2 separately)
    boot = P6.bootstrap_rows(rows, seeds=(P6.PRIMARY_SEED,))
    write("bootstrap", boot)
    write("bootstrap_seed_sensitivity", P6.bootstrap_rows(rows, seeds=(1, 2)))
    print(f"bootstrap: {len(boot)} primary rows (seed 0)")

    # B.4 drift sensitivity; s = 16 must reproduce the P5 primary seed-mean MAE
    drift = P6.drift_rows(rows)
    p5_mae = {(r["subject_id"], int(r["budget_nights"]), r["target"]): float(r["seed_mean"])
              for r in P6.read_csv(tables / "p5_primary_mae.csv") if r["subject_id"] != "unweighted_mean"}
    d16 = max(abs(r["Eb_mae"] - p5_mae[(r["subject_id"], r["budget_nights"], r["target"])])
              for r in drift if r["start_night"] == 16 and r["status"] == "evaluated")
    if d16 > CONSISTENCY_TOL:
        raise P6.P6Error(f"drift s=16 does not reproduce the P5 primary MAE (max |diff| {d16:g})")
    write("drift_sensitivity", drift)
    print(f"drift: {sum(r['status'] == 'evaluated' for r in drift)} evaluated rows; s=16 vs P5 max |diff| {d16:.2g}")

    # B.5 level trajectory (targets only, no model)
    plan = yaml.safe_load(P5.plan_yaml().read_text(encoding="utf-8"))
    pools = {s: rec["outer_target_scaler"]["mean"] for s, rec in plan["subjects"].items()}
    sess = P5.P5Session(echo=False)
    nights, spans = P6.level_rows(sess, pools)
    bias0 = {(r["subject_id"], r["target"]): float(r["seed_mean"]) for r in P6.read_csv(tables / "p5_primary_bias.csv")
             if r["subject_id"] != "unweighted_mean" and r["budget_nights"] == "0"}
    gain = {(r["subject_id"], r["target"], int(r["budget_nights"])): float(r["G_pct"])
            for r in P6.read_csv(tables / "p5_adaptation_gain.csv") if r["subject_id"] != "unweighted_mean"}
    write("level_trajectory", nights)
    write("level_spans", spans)
    write("level_consistency", P6.mismatch_consistency(spans, bias0, gain))
    print(f"level trajectory: {len(nights)} night rows")

    # A.2 / B.6 User02 device and heater-context strata
    preds, pred_shas = user02_predictions()
    events = P6.heater_events("User02")
    metrics, dboot = P6.device_context_rows(preds, events, tuple(P5.budgets()), tuple(P5.seeds()))
    write("user02_device_context", metrics)
    write("user02_device_context_bootstrap", dboot)
    print(f"User02 device/context: {len(metrics)} metric rows, {len(dboot)} bootstrap rows; "
          f"events: {', '.join(f'{d} {len(v[0])}' for d, v in events.items())}")

    resamples, rng_seed, level = P6.bootstrap_settings()
    write_json(P6.metrics_dir() / "p6_provenance.json", {
        "decision": "D-047", "bootstrap": {"unit": "night", "resamples": resamples, "seed": rng_seed,
                                           "level": level, "primary_seed": P6.PRIMARY_SEED},
        "drift_starts": list(P6.DRIFT_STARTS), "rolling_nights": P6.ROLLING_NIGHTS,
        "heater_window_s": P6.HEATER_WINDOW_S, "min_nights": P6.MIN_NIGHTS,
        "inputs_sha256_lf": {rel: S.file_sha256_lf(P6.paths.PROJECT_ROOT / rel) for rel in (
            "paper/tables/p5_per_night.csv", "paper/tables/p5_by_seed.csv", "paper/tables/p5_primary_mae.csv",
            "paper/tables/p5_primary_bias.csv", "paper/tables/p5_adaptation_gain.csv",
            "configs/experiments/v1.0/p5_personalization_plan.yaml")},
        "p5_predictions_sha256": pred_shas, "per_night_vs_p5_max_abs_diff": worst, "drift_s16_vs_p5": d16,
        "heater_events_per_device": {d: int(len(v[0])) for d, v in events.items()}})
    print("wrote outputs/metrics/p6/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
