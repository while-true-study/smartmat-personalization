"""Export P5 result tables and figures (no hand-copied numbers; CONVENTIONS §5).

Reads the aggregated tables in outputs/metrics/p5/ (scripts/run_p5_personalization.py aggregate) and writes:
  paper/tables/p5_*.csv                                     paper-facing tables (committed)
  paper/figures/p5_fig*.png                                 figures P5-1 … P5-4, drawn only from p5_figure_data.csv
  every generated block of docs/P5_PERSONALIZATION_REPORT.md between
  <!-- BEGIN GENERATED P5:<name> --> and <!-- END GENERATED P5:<name> --> markers
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from src.data import paths  # noqa: E402
from src.data.io_guard import open_for_write, write_csv, write_text  # noqa: E402

SUBJECTS = ("User01", "User02", "User07")
BUDGETS = ("0", "1", "3", "7", "14")
UNIT = {"temperature": "°C", "humidity": "%RH"}
MARK = re.compile(r"<!-- BEGIN GENERATED P5:(?P<name>[a-z_0-9]+) -->.*?<!-- END GENERATED P5:(?P=name) -->", re.S)
# categorical slots 1-3 of the validated default palette (dataviz); the cohort mean is drawn in primary ink
COLORS = {"User01": "#2a78d6", "User02": "#eb6834", "User07": "#1baf7a", "unweighted_mean": "#0b0b0b"}
MARKERS = {"User01": "o", "User02": "s", "User07": "^", "unweighted_mean": "D"}
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb"


def read(name: str) -> list[dict]:
    with open(paths.PROJECT_ROOT / "outputs" / "metrics" / "p5" / f"p5_{name}.csv", encoding="utf-8",
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
    out = paths.PROJECT_ROOT / "paper" / "tables"
    cols = ["subject_id", "fold", "budget_nights", "span", "target", "metric", "seed_mean", "seed_sd", "seed_min",
            "seed_max", "n_seeds", "n_windows", "n_nights"]
    for metric in ("mae", "rmse", "bias"):
        rows = [r for r in t["primary_summary"] if r["metric"] == metric]
        write_csv(out / f"p5_primary_{metric}.csv", rows, cols)
    write_csv(out / "p5_later_span_mae.csv", [r for r in t["later_summary"] if r["metric"] == "mae"], cols)
    for name, src in (("p5_adaptation_gain", "adaptation_gain"), ("p5_by_seed", "by_seed"),
                      ("p5_per_night", "per_night"), ("p5_budget_counts", "budget_counts")):
        rows = t[src]
        write_csv(out / f"{name}.csv", rows, list(dict.fromkeys(k for r in rows for k in r)))
    scols = ["subject_id", "budget_nights", "seed", "stratum_type", "stratum", "target", "metric", "value", "seed_sd",
             "n_windows", "n_nights"]
    for name, subj in (("p5_user02_device_strata", "User02"), ("p5_user01_sensor_phase", "User01")):
        write_csv(out / f"{name}.csv", [{c: r.get(c, "") for c in scols} for r in t["strata"]
                                        if r["subject_id"] == subj], scols)
    write_csv(out / "p5_figure_data.csv", figure_data(t), ["figure", "panel", "series", "budget_nights", "value",
                                                            "seed_min", "seed_max", "unit"])


def figure_data(t: dict[str, list[dict]]) -> list[dict]:
    rows = []
    summ = t["primary_summary"]
    for fig, target, metric in (("P5-1", "temperature", "mae"), ("P5-2", "humidity", "mae"),
                                ("P5-3", "temperature", "abs_bias"), ("P5-3", "humidity", "abs_bias")):
        for series in (*SUBJECTS, "unweighted_mean"):
            for b in BUDGETS:
                r = pick(summ, subject_id=series, budget_nights=b, target=target, metric=metric)
                rows.append({"figure": fig, "panel": target, "series": series, "budget_nights": b,
                             "value": r["seed_mean"], "seed_min": r["seed_min"], "seed_max": r["seed_max"],
                             "unit": UNIT[target]})
    for target in ("temperature", "humidity"):
        for dev in ("22480", "22482"):
            for b in BUDGETS:
                r = pick(t["strata"], subject_id="User02", budget_nights=b, seed="mean", stratum=dev, target=target,
                         metric="mae")
                vals = [float(x["value"]) for x in t["strata"] if x["subject_id"] == "User02" and x["seed"] != "mean"
                        and x["budget_nights"] == b and x["stratum"] == dev and x["target"] == target
                        and x["metric"] == "mae"]
                rows.append({"figure": "P5-4", "panel": target, "series": dev, "budget_nights": b,
                             "value": r["value"], "seed_min": min(vals), "seed_max": max(vals), "unit": UNIT[target]})
    return rows


def draw_figures(fd: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    xs = list(range(len(BUDGETS)))
    specs = [("p5_fig1_temperature_mae.png", "P5-1", ["temperature"], "Temperature MAE (°C)",
              "Figure P5-1 — Temperature MAE on the common primary test span"),
             ("p5_fig2_humidity_mae.png", "P5-2", ["humidity"], "Humidity MAE (%RH)",
              "Figure P5-2 — Humidity MAE on the common primary test span"),
             ("p5_fig3_abs_bias.png", "P5-3", ["temperature", "humidity"], "|bias|",
              "Figure P5-3 — Absolute bias on the common primary test span"),
             ("p5_fig4_user02_devices.png", "P5-4", ["temperature", "humidity"], "MAE",
              "Figure P5-4 — User02 residual MAE by mat")]
    out = paths.PROJECT_ROOT / "paper" / "figures"
    for fname, fig_id, panels, ylab, title in specs:
        fig, axes = plt.subplots(1, len(panels), figsize=(4.2 * len(panels) + 0.8, 3.4), squeeze=False)
        for ax, panel in zip(axes[0], panels):
            rows = [r for r in fd if r["figure"] == fig_id and r["panel"] == panel]
            series = list(dict.fromkeys(r["series"] for r in rows))
            for i, s in enumerate(series):
                pts = sorted((r for r in rows if r["series"] == s), key=lambda r: BUDGETS.index(r["budget_nights"]))
                y = [float(r["value"]) for r in pts]
                color = COLORS.get(s, ["#2a78d6", "#eb6834"][i % 2])
                mean = s == "unweighted_mean"
                ax.plot(xs, y, color=color, lw=2, ls="--" if mean else "-", marker=MARKERS.get(s, "os"[i % 2]),
                        ms=6, label="unweighted mean" if mean else s, zorder=3)
                if not mean:
                    lo = [float(r["seed_min"]) for r in pts]
                    hi = [float(r["seed_max"]) for r in pts]
                    ax.vlines(xs, lo, hi, color=color, lw=1, alpha=0.6, zorder=2)
                ax.annotate("mean" if mean else s, (xs[-1], y[-1]), xytext=(6, 0), textcoords="offset points",
                            va="center", fontsize=8, color=INK)
            ax.set_xticks(xs, BUDGETS)
            ax.set_xlabel("adaptation budget (nights; 0 = base model)")
            unit = rows[0]["unit"]
            ax.set_ylabel(f"{panel.capitalize()} {ylab} ({unit})" if fig_id in ("P5-3", "P5-4") else ylab)
            ax.grid(axis="y", color=GRID, lw=0.6)
            ax.set_xlim(-0.3, len(xs) - 0.2)
            ax.legend(frameon=False, fontsize=7.5, loc="best")
        fig.suptitle(title + " (seed mean; bars: seed min–max)", fontsize=9.5, color=INK)
        fig.tight_layout()
        with open_for_write(out / fname, "wb") as fh:
            fig.savefig(fh, format="png", dpi=160, metadata={"Software": None})
        plt.close(fig)


def blocks(t: dict[str, list[dict]]) -> dict[str, str]:
    b = {}
    cnt = t["budget_counts"]
    rows = [[r["subject_id"], r["fold"], r["budget_nights"], r["adaptation_nights"],
             f"{r['adaptation_first']}…{r['adaptation_last']}" if r["adaptation_first"] else "—",
             r["adaptation_windows"], r["buffer_nights"] or "—", r["primary_test_nights"], r["primary_test_windows"],
             r["later_test_nights"], r["later_test_windows"], f"{float(r['adaptation_lr']):g}"] for r in cnt]
    b["counts"] = ("**Table P5-1 — Budgets, nights and labelled windows (frozen split; plan committed before any "
                   "run).**\n\n" + md(["Subject", "Fold", "b", "Adapt. nights", "Adaptation span", "Adapt. windows",
                                       "Buffer night", "Primary nights", "Primary windows", "Later nights",
                                       "Later windows", "Adapt. LR"], rows))
    summ = t["primary_summary"]
    for metric, label in (("mae", "MAE"), ("rmse", "RMSE"), ("bias", "Bias")):
        rows = []
        for tgt in ("temperature", "humidity"):
            for s in (*SUBJECTS, "unweighted_mean"):
                cells = []
                for bb in BUDGETS:
                    r = pick(summ, subject_id=s, budget_nights=bb, target=tgt, metric=metric)
                    cells.append(f3(r["seed_mean"]) + (f" ± {f3(r['seed_sd'])}" if r["seed_sd"] else ""))
                rows.append([f"{tgt} ({UNIT[tgt]})", "unweighted mean" if s == "unweighted_mean" else s, *cells])
        b[f"primary_{metric}"] = (f"**Table P5-2{'abc'[['mae', 'rmse', 'bias'].index(metric)]} — {label} on the "
                                  "common primary test span (seed mean ± SD over seeds 0/1/2).**\n\n"
                                  + md(["Target", "Subject", *[f"b = {x}" for x in BUDGETS]], rows))
    gain = t["adaptation_gain"]
    rows = []
    for tgt in ("temperature", "humidity"):
        for s in (*SUBJECTS, "unweighted_mean"):
            for bb in BUDGETS[1:]:
                r = pick(gain, subject_id=s, budget_nights=bb, target=tgt)
                rows.append([tgt, "unweighted mean" if s == "unweighted_mean" else s, bb, f3(r["E0_mae"]),
                             f3(r["Eb_mae"]), sgn(r["delta_E"]), f"{float(r['G_pct']):+.1f} %",
                             f3(r["abs_bias_0"]), f3(r["abs_bias_b"]), sgn(r["C_b"]), f3(r["err_sd_0"]),
                             f3(r["err_sd_b"]), sgn(r["delta_err_sd"]),
                             f"{r['seeds_improved']}/3" if r.get("seeds_improved") not in ("", None)
                             else f"{r['subjects_improved']}/3 subj."])
    b["gain"] = ("**Table P5-3 — Adaptation effect on the primary span (seed means): ΔE = E₀ − E_b, G = ΔE / E₀, "
                 "C = |bias₀| − |bias_b|, error SD = √(RMSE² − bias²). Positive = better than the base model. Last "
                 "column: seeds whose adapted model beats its own base model (subject rows) or subjects with ΔE > 0 "
                 "(cohort row).**\n\n"
                 + md(["Target", "Subject", "b", "E₀", "E_b", "ΔE", "G", "\\|bias₀\\|", "\\|bias_b\\|", "C",
                       "Err SD₀", "Err SD_b", "ΔSD", "Improved"], rows))
    st = t["strata"]
    for key, subj, strata, title in (
            ("devices", "User02", ("22480", "22482", "22482/normal", "22482/p1_response_shift", "22482/p1_transition"),
             "Table P5-4 — User02 by mat (and 22482 quality phase), primary span, seed mean"),
            ("phases", "User01", ("s1", "s2"), "Table P5-5 — User01 by sensor phase, primary span, seed mean")):
        rows = []
        for tgt in ("temperature", "humidity"):
            for name in strata:
                for metric in ("mae", "rmse", "bias"):
                    hit = [r for r in st if r["subject_id"] == subj and r["seed"] == "mean" and r["stratum"] == name
                           and r["target"] == tgt and r["metric"] == metric]
                    if not hit:
                        continue
                    byb = {r["budget_nights"]: r for r in hit}
                    rows.append([tgt, name, metric.upper(), *[f3(byb[x]["value"]) for x in BUDGETS],
                                 byb["0"]["n_windows"], byb["0"]["n_nights"]])
        b[key] = f"**{title}.**\n\n" + md(["Target", "Stratum", "Metric", *[f"b = {x}" for x in BUDGETS], "Windows",
                                            "Nights"], rows)
    later = t["later_summary"]
    rows = []
    for tgt in ("temperature", "humidity"):
        for s in (*SUBJECTS, "unweighted_mean"):
            cells = [f3(pick(later, subject_id=s, budget_nights=x, target=tgt, metric="mae")["seed_mean"])
                     for x in BUDGETS]
            rows.append([tgt, "unweighted mean" if s == "unweighted_mean" else s, *cells])
    b["later"] = ("**Table P5-6 — Secondary: MAE on each budget's own later span (nights ≥ b + 2; the test set "
                  "changes with b, so this is not the budget comparison).**\n\n"
                  + md(["Target", "Subject", *[f"b = {x}" for x in BUDGETS]], rows))
    pn = t["per_night"]
    rows = []
    for tgt in ("temperature", "humidity"):
        for s in SUBJECTS:
            cells = []
            for x in BUDGETS:
                v = [float(r["mae"]) for r in pn if r["subject_id"] == s and r["budget_nights"] == x
                     and r["target"] == tgt and r["primary_test"] == "1"]
                q = np.percentile(v, [25, 50, 75])
                cells.append(f"{q[1]:.2f} [{q[0]:.2f}–{q[2]:.2f}]")
            rows.append([tgt, s, *cells])
    b["per_night"] = ("**Table P5-7 — Per-night MAE on the primary span: median [p25–p75] over nights × seeds "
                      "(secondary; the unit for P6).**\n\n" + md(["Target", "Subject", *[f"b = {x}" for x in BUDGETS]],
                                                                 rows))
    bs = t["by_seed"]
    rows = [[r["subject_id"], r["budget_nights"], r["seed"], r["target"], f3(r["mae"]), f3(r["rmse"]), f3(r["bias"]),
             r["n_windows"], r["n_nights"]] for r in bs if r["span"] == "primary"]
    b["by_seed"] = ("**Table P5-8 — Primary span per subject, budget and seed.**\n\n"
                    + md(["Subject", "b", "Seed", "Target", "MAE", "RMSE", "Bias", "Windows", "Nights"], rows))
    pooled = t["pooled_primary"]
    rows = []
    for tgt in ("temperature", "humidity"):
        for metric in ("mae", "rmse"):
            cells = []
            for x in BUDGETS:
                v = [float(r["value"]) for r in pooled if r["budget_nights"] == x and r["target"] == tgt
                     and r["metric"] == metric]
                cells.append(f"{sum(v) / len(v):.3f}")
            rows.append([tgt, metric.upper(), *cells])
    b["pooled"] = ("**Table P5-9 — Secondary: window-weighted pooled metric over the three subjects' primary spans "
                   "(seed mean).**\n\n" + md(["Target", "Metric", *[f"b = {x}" for x in BUDGETS]], rows))
    return b


def main() -> int:
    names = ("primary_summary", "later_summary", "adaptation_gain", "by_seed", "per_night", "strata",
             "budget_counts", "pooled_primary")
    t = {n: read(n) for n in names}
    export_csvs(t)
    draw_figures(figure_data(t))
    b = blocks(t)
    rep = paths.PROJECT_ROOT / "docs" / "P5_PERSONALIZATION_REPORT.md"
    text = rep.read_text(encoding="utf-8").replace("\r\n", "\n")
    found = {m.group("name") for m in MARK.finditer(text)}
    if found != set(b):
        raise SystemExit(f"report markers {sorted(found)} != generated blocks {sorted(b)}")
    text = MARK.sub(lambda m: f"<!-- BEGIN GENERATED P5:{m.group('name')} -->\n\n{b[m.group('name')]}\n\n"
                              f"<!-- END GENERATED P5:{m.group('name')} -->", text)
    write_text(rep, text)
    print(f"wrote paper/tables/p5_*.csv, paper/figures/p5_fig*.png and {len(b)} generated report blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
