"""Export P3 result tables (no hand-copied numbers; CONVENTIONS §5).

Reads the aggregated P3 tables in outputs/metrics/p3/ (scripts/run_p3_loso_baseline.py aggregate) and writes:
  paper/tables/p3_*.csv                                  small paper-facing tables (committed)
  the generated block of docs/P3_STRICT_LOSO_BASELINE_REPORT.md between the BEGIN/END markers
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_text  # noqa: E402

BEGIN, END = "<!-- BEGIN GENERATED P3 TABLES -->", "<!-- END GENERATED P3 TABLES -->"
SUBJECTS = ("User01", "User02", "User07")
UNIT = {"temperature": "°C", "humidity": "%RH"}


def read(name: str) -> list[dict]:
    with open(paths.PROJECT_ROOT / "outputs" / "metrics" / "p3" / f"{name}.csv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def f3(x) -> str:
    return f"{float(x):.3f}"


def md(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main() -> int:
    summary, by_seed, by_fold = read("tcn_outer_summary"), read("tcn_outer_by_seed"), read("tcn_outer_by_fold")
    sel, tm, strata = read("tcn_selected_configs"), read("training_mean_by_fold"), read("secondary_strata")
    pooled, inner = read("secondary_window_weighted_pooled"), read("tcn_inner_search")
    tables = paths.PROJECT_ROOT / "paper" / "tables"
    write_csv(tables / "p3_primary_summary.csv", summary, list(summary[0]))
    write_csv(tables / "p3_tcn_outer_by_seed.csv", by_seed, list(by_seed[0]))
    write_csv(tables / "p3_selected_configs.csv", sel, list(sel[0]))
    write_csv(tables / "p3_training_mean_by_fold.csv", tm, list(tm[0]))
    keep = [r for r in strata if r["stratum_type"] != "per_night_mae" and (r["model"] == "training_mean"
                                                                           or r["seed"] == "mean")]
    cols = ["model", "fold", "subject_id", "stratum_type", "stratum", "target", "metric", "value", "seed_sd",
            "n_windows"]
    write_csv(tables / "p3_secondary_strata.csv", [{c: r.get(c, "") for c in cols} for r in keep], cols)

    parts = []
    # T1 primary
    rows = []
    for t in ("temperature", "humidity"):
        for metric in ("mae", "rmse"):
            for model in ("training_mean", "tcn_raw"):
                r = next(x for x in summary if x["model"] == model and x["target"] == t and x["metric"] == metric)
                rows.append([f"{t} ({UNIT[t]})", metric.upper(), "training-mean" if model == "training_mean"
                             else "RAW TCN (seed mean)", *[f3(r[s]) for s in SUBJECTS], f3(r["unweighted_subject_mean"])])
    parts.append("**Table P3-1 — Primary endpoints (held-out subject; unweighted mean over the three subjects).**\n\n"
                 + md(["Target", "Metric", "Model", *SUBJECTS, "Unweighted mean"], rows))
    # T2 bias
    rows = []
    for t in ("temperature", "humidity"):
        for model in ("training_mean", "tcn_raw"):
            r = next(x for x in summary if x["model"] == model and x["target"] == t and x["metric"] == "bias")
            rows.append([f"{t} ({UNIT[t]})", "training-mean" if model == "training_mean" else "RAW TCN (seed mean)",
                         *[f3(r[s]) for s in SUBJECTS], f3(r["unweighted_subject_mean"])])
    parts.append("**Table P3-2 — Bias (mean prediction − truth; secondary).**\n\n"
                 + md(["Target", "Model", *SUBJECTS, "Unweighted mean"], rows))
    # T3 per seed
    rows = []
    for r in by_seed:
        rows.append([r["fold"], r["held_out_subject"], r["seed"], r["target"], f3(r["mae"]), f3(r["rmse"]),
                     f3(r["bias"]), r["n_windows"]])
    parts.append("**Table P3-3 — RAW TCN outer test per seed.**\n\n"
                 + md(["Fold", "Held out", "Seed", "Target", "MAE", "RMSE", "Bias", "Test windows"], rows))
    # T4 seed spread
    rows = [[r["fold"], r["held_out_subject"], r["target"], r["metric"].upper(), f3(r["seed_mean"]), f3(r["seed_sd"]),
             f3(r["seed_min"]), f3(r["seed_max"])] for r in by_fold if r["metric"] in ("mae", "rmse")]
    parts.append("**Table P3-4 — Seed variability (seeds 0/1/2).**\n\n"
                 + md(["Fold", "Held out", "Target", "Metric", "Mean", "SD", "Min", "Max"], rows))
    # T5 selection
    rows = [[r["fold"], r["held_out_subject"], r["selected_index"], r["channels"], r["kernel_size"], r["dropout"],
             r["lr"], f3(r["inner_A_criterion"]), r["inner_A_best_epoch"], f3(r["inner_B_criterion"]),
             r["inner_B_best_epoch"], f3(r["selection_score"]), r["final_epochs"]] for r in sel]
    parts.append("**Table P3-5 — Selected RAW-TCN configuration per outer fold (inner validation only).**\n\n"
                 + md(["Fold", "Held out", "Cfg", "Channels", "Kernel", "Dropout", "LR", "Inner A crit.",
                       "A best ep.", "Inner B crit.", "B best ep.", "Score", "Final epochs"], rows))
    # T6 inner score spread
    rows = []
    for f in sorted({r["fold"] for r in inner}):
        sc = sorted(float(r["mean_criterion"]) for r in inner if r["fold"] == f)
        rows.append([f, f3(sc[0]), f3(sc[1]), f3(sorted(sc)[len(sc) // 2]), f3(sc[-1])])
    parts.append("**Table P3-6 — Inner-search score range over the 16 configurations (selection criterion).**\n\n"
                 + md(["Fold", "Best", "Second", "Median", "Worst"], rows))
    # T7 strata
    rows = []
    for r in keep:
        if r["stratum_type"] in ("device", "sensor_phase", "channel_quality_phase", "device_x_channel_quality_phase") \
                and r["metric"] in ("mae", "bias"):
            rows.append([r["subject_id"], r["stratum_type"], r["stratum"], r["target"], r["metric"].upper(),
                         "training-mean" if r["model"] == "training_mean" else "RAW TCN (seed mean)", f3(r["value"]),
                         f3(r["seed_sd"]) if r.get("seed_sd") else "", r["n_windows"]])
    parts.append("**Table P3-7 — Device and phase diagnostics (secondary; interpretation only).**\n\n"
                 + md(["Subject", "Stratum type", "Stratum", "Target", "Metric", "Model", "Value", "Seed SD",
                       "Windows"], rows))
    # T8 per-night + pooled
    rows = []
    for r in strata:
        if r["stratum_type"] == "per_night_mae" and (r["model"] == "training_mean" or r["seed"] == "mean"):
            rows.append([r["subject_id"], r["target"], "training-mean" if r["model"] == "training_mean"
                         else "RAW TCN (seed mean)", r["stratum"], f3(r["value"])])
    parts.append("**Table P3-8 — Per-night MAE distribution (secondary).**\n\n"
                 + md(["Subject", "Target", "Model", "Quantile", "Per-night MAE"], rows))
    rows = [[r["model"], r["seed"], r["target"], r["metric"].upper(), f3(r["value"]), r["n_windows"]]
            for r in pooled if r["metric"] in ("mae", "rmse")]
    parts.append("**Table P3-9 — Window-weighted pooled metric over all test windows (secondary, not primary).**\n\n"
                 + md(["Model", "Seed", "Target", "Metric", "Value", "Windows"], rows))
    block = f"{BEGIN}\n\n" + "\n\n".join(parts) + f"\n\n{END}"
    rep = paths.PROJECT_ROOT / "docs" / "P3_STRICT_LOSO_BASELINE_REPORT.md"
    text = rep.read_text(encoding="utf-8").replace("\r\n", "\n")
    if BEGIN not in text or END not in text:
        raise SystemExit("report lacks the generated-table markers")
    pre, rest = text.split(BEGIN, 1)
    _, post = rest.split(END, 1)
    write_text(rep, pre + block + post)
    print("wrote paper/tables/p3_*.csv and the generated block of the P3 report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
