"""Export P6 tables, figures and report blocks (no hand-copied numbers; CONVENTIONS §5).

Reads outputs/metrics/p6/ (scripts/run_p6_robustness.py) and writes:
  paper/tables/p6_*.csv                               paper-facing tables (committed)
  paper/figures/p6_fig*.png                           figures P6-1 … P6-4, drawn from p6_figure_data.csv
  generated blocks of docs/P6_ROBUSTNESS_STATISTICAL_ANALYSIS_REPORT.md
  (<!-- BEGIN GENERATED P6:<name> --> … <!-- END GENERATED P6:<name> -->)
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import open_for_write, write_csv, write_text  # noqa: E402

SUBJECTS = ("User01", "User02", "User07")
BUDGETS = ("1", "3", "7", "14")
STARTS = ("12", "14", "16", "18", "21")
UNIT = {"temperature": "°C", "humidity": "%RH"}
MARK = re.compile(r"<!-- BEGIN GENERATED P6:(?P<name>[a-z_0-9]+) -->.*?<!-- END GENERATED P6:(?P=name) -->", re.S)
COLORS = {"User01": "#2a78d6", "User02": "#eb6834", "User07": "#1baf7a"}      # as in the P5 figures
MARKERS = {"User01": "o", "User02": "s", "User07": "^"}
INK, MUTED, GRID, SURFACE, BAND = "#0b0b0b", "#898781", "#e1e0d9", "#fcfcfb", "#f0efec"


def read(name: str) -> list[dict]:
    with open(paths.PROJECT_ROOT / "outputs" / "metrics" / "p6" / f"p6_{name}.csv", encoding="utf-8",
              newline="") as fh:
        return list(csv.DictReader(fh))


def f3(x) -> str:
    return f"{float(x):.3f}" if x not in ("", None) else ""


def sgn(x) -> str:
    return f"{float(x):+.3f}" if x not in ("", None) else ""


def md(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pick(rows: list[dict], **kw) -> dict:
    hit = [r for r in rows if all(str(r[k]) == str(v) for k, v in kw.items())]
    if len(hit) != 1:
        raise SystemExit(f"expected one row for {kw}, got {len(hit)}")
    return hit[0]


BOOT_COLS = ["subject_id", "target", "budget_nights", "metric", "seed", "n_nights", "n_windows", "base_value",
             "adapted_value", "point_estimate", "ci_lower", "ci_upper", "interval", "night_mean_delta",
             "night_median_delta", "proportion_nights_improved", "n_resamples", "rng_seed", "level"]


def export_csvs(t: dict[str, list[dict]]) -> None:
    out = paths.PROJECT_ROOT / "paper" / "tables"
    for metric, name in (("mae", "mae"), ("rmse", "rmse"), ("abs_bias", "bias")):
        write_csv(out / f"p6_bootstrap_{name}.csv", [r for r in t["bootstrap"] if r["metric"] == metric], BOOT_COLS)
    write_csv(out / "p6_bootstrap_seed_sensitivity.csv", t["bootstrap_seed_sensitivity"], BOOT_COLS)
    for src, name in (("drift_sensitivity", "p6_drift_sensitivity"),
                      ("level_trajectory", "p6_level_mismatch_trajectory"),
                      ("level_spans", "p6_level_mismatch_spans"),
                      ("level_consistency", "p6_level_mismatch_consistency"),
                      ("user02_device_context", "p6_user02_device_context"),
                      ("user02_device_context_bootstrap", "p6_user02_device_context_bootstrap")):
        rows = t[src]
        write_csv(out / f"{name}.csv", rows, list(dict.fromkeys(k for r in rows for k in r)))
    write_csv(out / "p6_figure_data.csv", figure_data(t), ["figure", "panel", "series", "x", "value", "lower",
                                                            "upper", "unit"])


def figure_data(t: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for fig, target in (("P6-1", "temperature"), ("P6-2", "humidity")):
        for s in SUBJECTS:
            for b in BUDGETS:
                r = pick(t["bootstrap"], subject_id=s, target=target, budget_nights=b, metric="mae")
                rows.append({"figure": fig, "panel": target, "series": s, "x": b, "value": r["point_estimate"],
                             "lower": r["ci_lower"], "upper": r["ci_upper"], "unit": UNIT[target]})
    for target in ("temperature", "humidity"):
        for b in BUDGETS:
            for s in SUBJECTS:
                for st in STARTS:
                    hit = [r for r in t["drift_sensitivity"] if r["subject_id"] == s and r["target"] == target
                           and r["budget_nights"] == b and r["start_night"] == st and r["status"] == "evaluated"]
                    if hit:
                        rows.append({"figure": "P6-3", "panel": f"{target}|b={b}", "series": s, "x": st,
                                     "value": hit[0]["G_pct"], "lower": hit[0]["seed_G_min"],
                                     "upper": hit[0]["seed_G_max"], "unit": "%"})
    for s, target in (("User07", "temperature"), ("User01", "humidity"), ("User02", "temperature")):
        for r in t["level_trajectory"]:
            if r["subject_id"] == s and r["target"] == target:
                rows.append({"figure": "P6-4", "panel": f"{s}|{target}", "series": "night_mean",
                             "x": r["night_ordinal"], "value": r["night_mean"], "lower": "", "upper": "",
                             "unit": UNIT[target]})
                rows.append({"figure": "P6-4", "panel": f"{s}|{target}", "series": "rolling_mean_7",
                             "x": r["night_ordinal"], "value": r["rolling_mean_7"], "lower": "", "upper": "",
                             "unit": UNIT[target]})
        for span in ("primary", "training_pool"):
            r = pick(t["level_spans"], subject_id=s, target=target, span=span)
            rows.append({"figure": "P6-4", "panel": f"{s}|{target}", "series": f"{span}_mean", "x": "",
                         "value": r["mean"], "lower": "", "upper": "", "unit": UNIT[target]})
    return rows


def draw_figures(fd: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                         "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
    out = paths.PROJECT_ROOT / "paper" / "figures"

    def save(fig, name):
        fig.tight_layout()
        with open_for_write(out / name, "wb") as fh:
            fig.savefig(fh, format="png", dpi=160, metadata={"Software": None})
        plt.close(fig)

    for fig_id, target, name in (("P6-1", "temperature", "p6_fig1_bootstrap_temperature.png"),
                                 ("P6-2", "humidity", "p6_fig2_bootstrap_humidity.png")):
        fig, ax = plt.subplots(figsize=(6.4, 3.8))
        ax.axhline(0, color=INK, lw=1, zorder=1)
        for i, s in enumerate(SUBJECTS):
            pts = [r for r in fd if r["figure"] == fig_id and r["series"] == s]
            xs = [BUDGETS.index(r["x"]) + (i - 1) * 0.18 for r in pts]
            y = [float(r["value"]) for r in pts]
            lo = [float(r["value"]) - float(r["lower"]) for r in pts]
            hi = [float(r["upper"]) - float(r["value"]) for r in pts]
            ax.errorbar(xs, y, yerr=[lo, hi], fmt=MARKERS[s], color=COLORS[s], ms=6, lw=1.5, capsize=3, label=s,
                        zorder=3)
        ax.set_xticks(range(len(BUDGETS)), BUDGETS)
        ax.set_xlabel("adaptation budget (nights)")
        ax.set_ylabel(f"ΔMAE = base − adapted ({UNIT[target]})")
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.legend(frameon=False, fontsize=8, loc="best")
        ax.set_title(f"Figure {fig_id} — {target.capitalize()}: paired night-level ΔMAE, seed 0\n"
                     "(point: full sample; bars: 95 % night-cluster bootstrap interval; > 0 = adaptation better)",
                     fontsize=9, color=INK)
        save(fig, name)

    for target in ("temperature", "humidity"):
        fig, axes = plt.subplots(1, 4, figsize=(13, 3.4), sharey=True)
        for ax, b in zip(axes, BUDGETS):
            ax.axhline(0, color=INK, lw=1, zorder=1)
            ax.axvline(16, color=MUTED, lw=1, ls=":", zorder=1)
            for s in SUBJECTS:
                pts = sorted((r for r in fd if r["figure"] == "P6-3" and r["panel"] == f"{target}|b={b}"
                              and r["series"] == s), key=lambda r: int(r["x"]))
                xs = [int(r["x"]) for r in pts]
                ax.plot(xs, [float(r["value"]) for r in pts], color=COLORS[s], marker=MARKERS[s], lw=2, ms=5,
                        label=s, zorder=3)
                ax.vlines(xs, [float(r["lower"]) for r in pts], [float(r["upper"]) for r in pts], color=COLORS[s],
                          lw=1, alpha=0.6, zorder=2)
            ax.set_title(f"b = {b} nights", fontsize=9, color=INK)
            ax.set_xticks([int(x) for x in STARTS])
            ax.set_xlabel("evaluation start night")
            ax.grid(axis="y", color=GRID, lw=0.6)
        axes[0].set_ylabel(f"{target.capitalize()} adaptation gain G (%)")
        axes[-1].legend(frameon=False, fontsize=8, loc="best")
        fig.suptitle(f"Figure P6-3 — {target.capitalize()}: drift sensitivity (post-hoc; seed mean, bars: seed "
                     "min–max; dotted: frozen primary start 16; b = 14 needs start ≥ 16)", fontsize=9.5, color=INK)
        save(fig, f"p6_fig3_drift_{target}.png")

    panels = [("User07", "temperature"), ("User01", "humidity"), ("User02", "temperature")]
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
    for ax, (s, target) in zip(axes, panels):
        key = f"{s}|{target}"
        nights = sorted((r for r in fd if r["panel"] == key and r["series"] == "night_mean"), key=lambda r: int(r["x"]))
        roll = sorted((r for r in fd if r["panel"] == key and r["series"] == "rolling_mean_7"),
                      key=lambda r: int(r["x"]))
        ax.axvspan(0.5, 14.5, color=BAND, zorder=0, label="adaptation nights (b ≤ 14)")
        ax.axvline(15.5, color=MUTED, lw=1, ls=":", zorder=1, label="primary test from night 16")
        ax.scatter([int(r["x"]) for r in nights], [float(r["value"]) for r in nights], s=9, color=MUTED, zorder=2,
                   label="night mean")
        ax.plot([int(r["x"]) for r in roll], [float(r["value"]) for r in roll], color=COLORS[s], lw=2, zorder=3,
                label="rolling mean (7 nights)")
        for series, ls, lab in (("primary_mean", "--", "primary-span mean"),
                                ("training_pool_mean", "-.", "base training-pool mean")):
            v = float(next(r["value"] for r in fd if r["panel"] == key and r["series"] == series))
            ax.axhline(v, color=INK, lw=1, ls=ls, zorder=2, label=lab)
        ax.set_title(f"{s} {target}", fontsize=9, color=INK)
        ax.set_xlabel("recorded night (ordinal)")
        ax.set_ylabel(f"{target} ({UNIT[target]})")
        ax.grid(axis="y", color=GRID, lw=0.6)
    axes[0].legend(frameon=False, fontsize=7, loc="best")
    fig.suptitle("Figure P6-4 — Night-level target trajectory (post-hoc descriptive; no model)", fontsize=9.5,
                 color=INK)
    save(fig, "p6_fig4_level_trajectory.png")


def blocks(t: dict[str, list[dict]]) -> dict[str, str]:
    b = {}
    bt = t["bootstrap"]
    for metric, key, label in (("mae", "boot_mae", "ΔMAE"), ("rmse", "boot_rmse", "ΔRMSE"),
                               ("abs_bias", "boot_bias", "Δ|bias| (= C_b)")):
        rows = []
        for tgt in ("temperature", "humidity"):
            for s in SUBJECTS:
                for bb in BUDGETS:
                    r = pick(bt, subject_id=s, target=tgt, budget_nights=bb, metric=metric)
                    rows.append([tgt, s, bb, f3(r["base_value"]), f3(r["adapted_value"]), sgn(r["point_estimate"]),
                                 f"[{sgn(r['ci_lower'])}, {sgn(r['ci_upper'])}]", r["interval"].replace("_", " "),
                                 sgn(r["night_median_delta"]), f"{float(r['proportion_nights_improved']):.2f}",
                                 r["n_nights"]])
        b[key] = (f"**Table P6-{['boot_mae', 'boot_rmse', 'boot_bias'].index(key) + 1} — {label}, adapted vs base "
                  "(seed 0), primary span: full-sample point estimate and 95 % night-level paired cluster bootstrap "
                  "interval (2,000 resamples, seed 0). Positive = adaptation better.**\n\n"
                  + md(["Target", "Subject", "b", "Base", "Adapted", "Point", "95 % interval", "Interval",
                        "Median per-night Δ", "Share of nights improved", "Nights"], rows))
    ss = t["bootstrap_seed_sensitivity"]
    rows = []
    for tgt in ("temperature", "humidity"):
        for s in SUBJECTS:
            cells = []
            for bb in BUDGETS:
                r0 = pick(bt, subject_id=s, target=tgt, budget_nights=bb, metric="mae")["interval"]
                rs = [pick(ss, subject_id=s, target=tgt, budget_nights=bb, metric="mae", seed=k)["interval"]
                      for k in ("1", "2")]
                short = {"above_zero": "+", "below_zero": "−", "includes_zero": "0"}
                cells.append(" / ".join(short[x] for x in (r0, *rs)))
            rows.append([tgt, s, *cells])
    b["seed_sens"] = ("**Table P6-4 — Interval side of ΔMAE for seeds 0 / 1 / 2 (+ = entirely above zero, − = "
                      "entirely below, 0 = includes zero). Seed 0 is primary; seeds 1 and 2 are sensitivity, never "
                      "pooled.**\n\n" + md(["Target", "Subject", *[f"b = {x}" for x in BUDGETS]], rows))
    dr = t["drift_sensitivity"]
    rows = []
    for tgt in ("temperature", "humidity"):
        for s in SUBJECTS:
            for bb in BUDGETS:
                cells = []
                for st in STARTS:
                    r = pick(dr, start_night=st, subject_id=s, target=tgt, budget_nights=bb)
                    cells.append("excluded" if r["status"] != "evaluated"
                                 else f"{float(r['G_pct']):+.1f} % ({r['seeds_improved']}/3)")
                rows.append([tgt, s, bb, *cells])
    nn = {s: "/".join(pick(dr, start_night=st, subject_id=s, target="temperature", budget_nights="0")["n_nights"]
                      for st in STARTS) for s in SUBJECTS}
    b["drift"] = ("**Table P6-5 — Post-hoc drift sensitivity: adaptation gain G on the span of nights ≥ s (seed mean; "
                  "in brackets the seeds with G > 0). s = 16 is the frozen primary span. Nights per span "
                  "(s = 12/14/16/18/21): " + "; ".join(f"{s} {v}" for s, v in nn.items()) + ".**\n\n"
                  + md(["Target", "Subject", "b", *[f"s = {x}" for x in STARTS]], rows))
    sp = t["level_spans"]
    rows = []
    for tgt in ("temperature", "humidity"):
        for s in SUBJECTS:
            prim = pick(sp, subject_id=s, target=tgt, span="primary")["mean"]
            cells = [sgn(pick(sp, subject_id=s, target=tgt, span=f"adaptation_b{x}")["minus_primary_mean"])
                     for x in BUDGETS]
            fut = [sgn(pick(sp, subject_id=s, target=tgt, span=f"future_from_{x}")["minus_primary_mean"])
                   for x in ("12", "21")]
            rows.append([tgt, s, f3(prim), sgn(pick(sp, subject_id=s, target=tgt, span="training_pool")
                                               ["minus_primary_mean"]), *cells, *fut])
    b["level"] = ("**Table P6-6 — Post-hoc descriptive: span means minus the primary-span mean (targets only; no "
                  "model).**\n\n" + md(["Target", "Subject", "Primary mean", "Training pool", *[f"Adapt. b = {x}"
                                                                                               for x in BUDGETS],
                                        "Nights ≥ 12", "Nights ≥ 21"], rows))
    cons = t["level_consistency"]
    rows = [[r["target"], r["subject_id"], r["budget_nights"], sgn(r["adaptation_minus_primary"]),
             f3(r["abs_base_bias"]), r["expected_direction"], f"{float(r['p5_G_pct']):+.1f} %",
             r["observed_direction"], "yes" if r["consistent"] == "True" else "no"] for r in cons]
    n_ok = sum(r["consistent"] == "True" for r in cons)
    b["consistency"] = (f"**Table P6-7 — Post-hoc descriptive consistency: expected direction (better if |adaptation "
                        f"mean − primary mean| < |base bias|) vs the P5 G sign ({n_ok}/{len(cons)} consistent).**\n\n"
                        + md(["Target", "Subject", "b", "Adapt. − primary", "\\|bias₀\\|", "Expected", "P5 G",
                              "Observed", "Consistent"], rows))
    dc, db = t["user02_device_context"], t["user02_device_context_bootstrap"]
    rows = []
    for tgt in ("temperature", "humidity"):
        names = list(dict.fromkeys(r["stratum"] for r in dc))
        for name in names:
            mean = [r for r in dc if r["stratum"] == name and r["seed"] == "mean" and r["target"] == tgt]
            if not mean:
                continue
            g = {(r["budget_nights"], r["metric"]): r for r in mean}
            bt_d = [r for r in db if r["stratum"] == name and r["target"] == tgt]
            dm = next((r for r in bt_d if r["quantity"] == "delta_mae_b0_minus_b14"), None)
            b14 = next((r for r in bt_d if r["quantity"] == "bias_b14"), None)
            rows.append([tgt, name, mean[0]["n_nights"], mean[0]["n_windows"], f3(g[("0", "mae")]["value"]),
                         f3(g[("14", "mae")]["value"]), sgn(g[("0", "bias")]["value"]),
                         sgn(g[("14", "bias")]["value"]),
                         f"{sgn(dm['point_estimate'])} [{sgn(dm['ci_lower'])}, {sgn(dm['ci_upper'])}]" if dm else
                         "descriptive only",
                         f"{sgn(b14['point_estimate'])} [{sgn(b14['ci_lower'])}, {sgn(b14['ci_upper'])}]" if b14
                         else "descriptive only"])
    b["device"] = ("**Table P6-8 — User02 primary span by mat, 22482 quality phase and heater context (MAE and bias: "
                   "seed mean; intervals: seed 0, night-cluster bootstrap, only for strata with ≥ 10 nights).**\n\n"
                   + md(["Target", "Stratum", "Nights", "Windows", "MAE b = 0", "MAE b = 14", "Bias b = 0",
                         "Bias b = 14", "ΔMAE b0 − b14 [95 %]", "Bias b = 14 [95 %]"], rows))
    return b


def main() -> int:
    names = ("bootstrap", "bootstrap_seed_sensitivity", "drift_sensitivity", "level_trajectory", "level_spans",
             "level_consistency", "user02_device_context", "user02_device_context_bootstrap")
    t = {n: read(n) for n in names}
    export_csvs(t)
    draw_figures(figure_data(t))
    b = blocks(t)
    rep = paths.PROJECT_ROOT / "docs" / "P6_ROBUSTNESS_STATISTICAL_ANALYSIS_REPORT.md"
    text = rep.read_text(encoding="utf-8").replace("\r\n", "\n")
    found = {m.group("name") for m in MARK.finditer(text)}
    if found != set(b):
        raise SystemExit(f"report markers {sorted(found)} != generated blocks {sorted(b)}")
    text = MARK.sub(lambda m: f"<!-- BEGIN GENERATED P6:{m.group('name')} -->\n\n{b[m.group('name')]}\n\n"
                              f"<!-- END GENERATED P6:{m.group('name')} -->", text)
    write_text(rep, text)
    print(f"wrote paper/tables/p6_*.csv, paper/figures/p6_fig*.png and {len(b)} generated report blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
