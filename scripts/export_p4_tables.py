"""Export P4 result tables (no hand-copied numbers; CONVENTIONS §5).

Reads the aggregated tables in outputs/metrics/p4/ (scripts/run_p4_feature_ablation.py aggregate) and writes:
  paper/tables/p4_*.csv                                    small paper-facing tables (committed)
  every generated block of docs/P4_FEATURE_ABLATION_REPORT.md between
  <!-- BEGIN GENERATED P4:<name> --> and <!-- END GENERATED P4:<name> --> markers
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_text  # noqa: E402
from src.evaluation.p4_ablation import ALL_FAMILIES, EFFECTS, P4_FAMILIES, STANDALONE, TRAINING_MEAN  # noqa: E402

SUBJECTS = ("User01", "User02", "User07")
UNIT = {"temperature": "°C", "humidity": "%RH"}
NAME = {TRAINING_MEAN: "training-mean", **{f: f for f in ALL_FAMILIES}}
MARK = re.compile(r"<!-- BEGIN GENERATED P4:(?P<name>[a-z_]+) -->.*?<!-- END GENERATED P4:(?P=name) -->", re.S)


def read(name: str) -> list[dict]:
    with open(paths.PROJECT_ROOT / "outputs" / "metrics" / "p4" / f"p4_{name}.csv", encoding="utf-8",
              newline="") as fh:
        return list(csv.DictReader(fh))


def f3(x) -> str:
    return f"{float(x):.3f}" if x not in ("", None) else ""


def sgn(x) -> str:
    return f"{float(x):+.3f}"


def md(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pick(rows: list[dict], **kw) -> dict:
    hit = [r for r in rows if all(str(r[k]) == str(v) for k, v in kw.items())]
    if len(hit) != 1:
        raise SystemExit(f"expected one row for {kw}, got {len(hit)}")
    return hit[0]


def export_csvs(t: dict[str, list[dict]]) -> None:
    """paper/tables/p4_*.csv. Missing "selected_configs" / "inner_search" are skipped: the public-release
    reproduction has no inner-search record (D-050)."""
    out = paths.PROJECT_ROOT / "paper" / "tables"
    for name in ("family_summary", "outer_by_seed", "selected_configs", "vs_raw", "vs_training_mean",
                 "incremental_effects", "seed_consistency", "bias_offset"):
        if name not in t and name == "selected_configs":
            continue
        rows = t[name]
        write_csv(out / f"p4_{'primary_summary' if name == 'family_summary' else name}.csv", rows, list(rows[0]))
    keep = [r for r in t["secondary_strata"] if r["stratum_type"] != "per_night_mae"
            and (r["model"] == TRAINING_MEAN or r["seed"] == "mean")]
    cols = ["model", "fold", "subject_id", "stratum_type", "stratum", "target", "metric", "value", "seed_sd",
            "n_windows", "source"]
    write_csv(out / "p4_secondary_strata.csv", [{c: r.get(c, "") for c in cols} for r in keep], cols)
    if "inner_search" in t:
        rng = inner_range(t["inner_search"])
        write_csv(out / "p4_inner_score_range.csv", rng, list(rng[0]))


def inner_range(inner: list[dict]) -> list[dict]:
    rows = []
    for fam in P4_FAMILIES:
        for f in ("1", "2", "3"):
            sc = sorted(float(r["mean_criterion"]) for r in inner if r["family"] == fam and r["fold"] == f)
            if len(sc) != 16:
                raise SystemExit(f"{fam} fold {f}: {len(sc)} inner scores")
            rows.append({"family": fam, "fold": f, "best": sc[0], "second": sc[1], "median": (sc[7] + sc[8]) / 2,
                         "worst": sc[-1]})
    return rows


def blocks(t: dict[str, list[dict]]) -> dict[str, str]:
    b = {}
    summ, sel = t["family_summary"], t["selected_configs"]
    # selected configurations
    rows = []
    for fam in ALL_FAMILIES:
        for f in ("1", "2", "3"):
            r = pick(sel, family=fam, fold=f)
            rows.append([fam, r["n_inputs"], f, r["held_out_subject"], r["selected_index"], r["channels"],
                         r["kernel_size"], r["dropout"], r["lr"], f3(r["inner_A_criterion"]),
                         r["inner_A_best_epoch"], f3(r["inner_B_criterion"]), r["inner_B_best_epoch"],
                         f3(r["selection_score"]), r["final_epochs"]])
    b["selected"] = ("**Table P4-1 — Selected configuration per family and outer fold (inner validation only; RAW "
                     "imported from P3).**\n\n"
                     + md(["Family", "Inputs", "Fold", "Held out", "Cfg", "Channels", "Kernel", "Dropout", "LR",
                           "Inner A crit.", "A best ep.", "Inner B crit.", "B best ep.", "Score", "Final epochs"],
                          rows))
    rows = [[r["family"], r["fold"], f3(r["best"]), f3(r["second"]), f3(r["median"]), f3(r["worst"])]
            for r in inner_range(t["inner_search"])]
    b["inner_range"] = ("**Table P4-2 — Inner-search criterion over the 16 configurations (P4 families).**\n\n"
                        + md(["Family", "Fold", "Best", "Second", "Median", "Worst"], rows))
    # primary endpoints
    for metric in ("mae", "rmse"):
        rows = []
        for tgt in ("temperature", "humidity"):
            for m in (TRAINING_MEAN, *ALL_FAMILIES):
                r = pick(summ, model=m, target=tgt, metric=metric)
                rows.append([f"{tgt} ({UNIT[tgt]})", NAME[m], *[f3(r[s]) for s in SUBJECTS],
                             f3(r["unweighted_subject_mean"]), r["rank_among_tcn_families"]])
        b[f"primary_{metric}"] = (f"**Table P4-3{'a' if metric == 'mae' else 'b'} — {metric.upper()} per held-out "
                                  "subject (TCN: seed mean of seeds 0/1/2) and unweighted mean over the three "
                                  "subjects. Rank among the six TCN families by unweighted mean (1 = lowest).**\n\n"
                                  + md(["Target", "Model", *SUBJECTS, "Unweighted mean", "Rank"], rows))
    # lowest cohort mean
    rows = []
    for tgt in ("temperature", "humidity"):
        for metric in ("mae", "rmse"):
            fams = [r for r in summ if r["target"] == tgt and r["metric"] == metric and r["model"] != TRAINING_MEAN]
            low = min(fams, key=lambda r: float(r["unweighted_subject_mean"]))
            tm = pick(summ, model=TRAINING_MEAN, target=tgt, metric=metric)
            raw = pick(summ, model="RAW", target=tgt, metric=metric)
            rows.append([f"{tgt} ({UNIT[tgt]})", metric.upper(), low["model"], f3(low["unweighted_subject_mean"]),
                         f3(raw["unweighted_subject_mean"]), f3(tm["unweighted_subject_mean"])])
    b["lowest"] = ("**Table P4-4 — Lowest unweighted mean among the six TCN families in this cohort.**\n\n"
                   + md(["Target", "Metric", "Lowest family", "Its mean", "RAW mean", "Training-mean"], rows))
    # seed spread
    rows = []
    for fam in ALL_FAMILIES:
        for tgt in ("temperature", "humidity"):
            cells = []
            for f, s in zip(("1", "2", "3"), SUBJECTS):
                r = pick(t["outer_by_fold"], family=fam, fold=f, target=tgt, metric="mae")
                cells.append(f"{f3(r['seed_mean'])} ± {f3(r['seed_sd'])} ({f3(r['seed_min'])}–{f3(r['seed_max'])})")
            rows.append([fam, tgt, *cells])
    b["seed_spread"] = ("**Table P4-5 — MAE seed mean ± SD (min–max) over seeds 0/1/2.**\n\n"
                        + md(["Family", "Target", *SUBJECTS], rows))
    # comparisons

    def comp_rows(rs: list[dict], label_key: str) -> list[list]:
        return [[r[label_key], r["target"], r["metric"].upper(), *[sgn(r[f"delta_{s}"]) for s in SUBJECTS],
                 sgn(r["delta_unweighted_mean"]), f"{100 * float(r['relative_delta_unweighted_mean']):+.1f} %",
                 f"{r['improved_subjects']}/3"] for r in rs]
    hdr = ["Comparison", "Target", "Metric", *[f"Δ {s}" for s in SUBJECTS], "Δ unweighted mean", "Relative",
           "Improved subjects"]
    eff = [dict(r, cmp=f"{r['effect']}: {r['first']} − {r['second']}") for r in t["incremental_effects"]]
    b["incremental"] = ("**Table P4-6 — Feature-added contributions (Δ = first − second, seed means; negative = "
                        "the added features lowered the error).**\n\n" + md(hdr, comp_rows(eff, "cmp")))
    st = [dict(r, cmp=f"{r['family']} − RAW") for r in t["vs_raw"] if r["comparison_type"].startswith("standalone")]
    b["standalone"] = ("**Table P4-7 — Standalone representations against RAW (representation sufficiency, not a "
                       "feature-added comparison).**\n\n" + md(hdr, comp_rows(st, "cmp")))
    rows = []
    for r in t["vs_training_mean"]:
        rows.append([r["family"], r["target"], r["metric"].upper(), *[sgn(r[f"delta_{s}"]) for s in SUBJECTS],
                     sgn(r["delta_unweighted_mean"]), f"{r['improved_subjects']}/3",
                     " / ".join(f"{r[f'seeds_better_{s}']}" for s in SUBJECTS)])
    b["vs_tm"] = ("**Table P4-8 — Each TCN family minus the training-mean predictor (seed means; negative = TCN "
                  "better). Last column: seeds (of 3) better than training-mean for User01 / User02 / User07.**\n\n"
                  + md(["Family", "Target", "Metric", *[f"Δ {s}" for s in SUBJECTS], "Δ unweighted mean",
                        "Better subjects", "Seeds better"], rows))
    rows = []
    for eid, label, a, bb in EFFECTS + STANDALONE:
        for tgt in ("temperature", "humidity"):
            r = pick(t["seed_consistency"], effect=eid, target=tgt, metric="mae")
            rows.append([f"{eid}: {a} − {bb}", tgt, f"{r['improved_fold_seeds']}/9",
                         " / ".join(r[f"improved_seeds_{s}"] for s in SUBJECTS), sgn(r["mean_delta"]),
                         sgn(r["min_delta"]), sgn(r["max_delta"])])
    b["seed_consistency"] = ("**Table P4-9 — MAE differences between runs with the same seed index (3 subjects × "
                             "3 seeds). Improved per subject: User01 / User02 / User07.**\n\n"
                             + md(["Comparison", "Target", "Improved of 9", "Improved per subject", "Mean Δ",
                                   "Min Δ", "Max Δ"], rows))
    # strata
    strata = [r for r in t["secondary_strata"] if r["stratum_type"] in
              ("sensor_phase", "device", "device_x_channel_quality_phase")
              and (r["model"] == TRAINING_MEAN or r["seed"] == "mean") and r["metric"] in ("mae", "bias")]
    keys = []
    for r in strata:
        k = (r["subject_id"], r["stratum_type"], r["stratum"], r["target"], r["metric"])
        if k not in keys:
            keys.append(k)
    rows = []
    for k in keys:
        vals = []
        for m in (TRAINING_MEAN, *ALL_FAMILIES):
            hit = [r for r in strata if (r["subject_id"], r["stratum_type"], r["stratum"], r["target"],
                                         r["metric"]) == k and r["model"] == m]
            vals.append(f3(hit[0]["value"]) if len(hit) == 1 else "")
        n = next(r["n_windows"] for r in strata if (r["subject_id"], r["stratum_type"], r["stratum"], r["target"],
                                                     r["metric"]) == k)
        rows.append([k[0], k[2], k[3], k[4].upper(), *vals, n])
    b["strata"] = ("**Table P4-10 — Device and phase strata (secondary; seed means; interpretation only).**\n\n"
                   + md(["Subject", "Stratum", "Target", "Metric", "Training-mean", *ALL_FAMILIES, "Windows"], rows))
    # bias / offset
    rows = []
    for s in SUBJECTS:
        for tgt in ("temperature", "humidity"):
            for m in (TRAINING_MEAN, *ALL_FAMILIES):
                r = pick(t["bias_offset"], model=m, subject_id=s, target=tgt)
                rows.append([s, tgt, NAME[m], f3(r["mae"]), sgn(r["bias"]), f3(r["abs_bias_over_mae"]),
                             f3(r["err_sd"]), sgn(r["delta_mae_vs_raw"]) if m != "RAW" else "",
                             sgn(r["delta_abs_bias_vs_raw"]) if m != "RAW" else "",
                             sgn(r["delta_err_sd_vs_raw"]) if m != "RAW" else ""])
    b["bias_offset"] = ("**Table P4-11 — Offset diagnostics (seed means): MAE, bias, \\|bias\\|/MAE and error SD "
                        "= √(RMSE² − bias²), with differences against RAW.**\n\n"
                        + md(["Subject", "Target", "Model", "MAE", "Bias", "\\|bias\\|/MAE", "Error SD",
                              "Δ MAE vs RAW", "Δ \\|bias\\| vs RAW", "Δ error SD vs RAW"], rows))
    # per seed
    rows = [[r["family"], r["fold"], r["held_out_subject"], r["seed"], r["target"], f3(r["mae"]), f3(r["rmse"]),
             f3(r["bias"]), r["n_windows"]] for r in t["outer_by_seed"]]
    b["per_seed"] = ("**Table P4-12 — Outer test per family, fold and seed (RAW rows: frozen P3).**\n\n"
                     + md(["Family", "Fold", "Held out", "Seed", "Target", "MAE", "RMSE", "Bias", "Test windows"],
                          rows))
    pooled = t["secondary_window_weighted_pooled"]
    rows = []
    for fam in P4_FAMILIES:
        for tgt in ("temperature", "humidity"):
            for metric in ("mae", "rmse"):
                v = [float(r["value"]) for r in pooled if r["family"] == fam and r["target"] == tgt
                     and r["metric"] == metric]
                rows.append([fam, tgt, metric.upper(), " / ".join(f3(x) for x in v), v and f3(sum(v) / len(v))])
    b["pooled"] = ("**Table P4-13 — Window-weighted pooled metric over all test windows (secondary; seeds 0 / 1 / 2 "
                   "and their mean; RAW and training-mean: Table P3-9).**\n\n"
                   + md(["Family", "Target", "Metric", "Seeds 0 / 1 / 2", "Mean"], rows))
    return b


def main() -> int:
    names = ("family_summary", "outer_by_seed", "outer_by_fold", "selected_configs", "inner_search", "vs_raw",
             "vs_training_mean", "incremental_effects", "seed_consistency", "bias_offset", "secondary_strata",
             "secondary_window_weighted_pooled")
    t = {n: read(n) for n in names}
    export_csvs(t)
    b = blocks(t)
    rep = paths.PROJECT_ROOT / "docs" / "P4_FEATURE_ABLATION_REPORT.md"
    text = rep.read_text(encoding="utf-8").replace("\r\n", "\n")
    found = {m.group("name") for m in MARK.finditer(text)}
    if found != set(b):
        raise SystemExit(f"report markers {sorted(found)} != generated blocks {sorted(b)}")
    text = MARK.sub(lambda m: f"<!-- BEGIN GENERATED P4:{m.group('name')} -->\n\n{b[m.group('name')]}\n\n"
                              f"<!-- END GENERATED P4:{m.group('name')} -->", text)
    write_text(rep, text)
    print(f"wrote paper/tables/p4_*.csv and {len(b)} generated blocks of the P4 report")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
