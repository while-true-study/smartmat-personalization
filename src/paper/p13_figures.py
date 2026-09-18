"""P13 manuscript revision: Figure 6 (target distributions) and Figure S5 (one example night per subject).

Descriptive plots of recorded data; neither introduces a metric, a model or a test.
- `extract_figure_data()` reads the canonical dataset through the frozen strict leave-one-subject-out windows
  (`loso_data.fold_data`) and the committed personalization split, and writes small figure-data tables to
  paper/tables/ (p13_figure_*.csv). No calendar date, night id or clock time is written: nights are ordinals and time
  is relative to the first plotted window of the night.
- `render_all()` draws the figures from those tables only (and the frozen source-training means of
  `p10_loso_constants`), in the style of the P8 figures (src/paper/manuscript_figures.py).

Night selection for Figure S5 (fixed before any figure was drawn; no model output is used):
  for each subject, the earliest night of the primary test span (night ordinal >= 16, `primary_test` = 1 in the
  personalization split) whose longest run of consecutive labelled 40-s windows (same session, window starts 20 s
  apart, i.e. an unbroken 5-s-binned segment) lasts at least 4 h. User02: the earliest such night on which both mats
  meet the rule; if none, the earliest night on which mat 22480 meets it; if no night meets the rule, the night with
  the longest run. The branch taken is recorded in p13_figure_night_selection.csv.

P14 (D-070): Figure S5 is withdrawn from the submission candidate. Its night-level series and heater-event timing are
never written to paper/tables/ again: `extract_figure_data()` exports only the Figure 6 table unless an explicit
private (git-ignored) directory is given for the example nights, and `render_all()` draws only Figure 6 unless asked.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.data import paths
from src.data.io_guard import write_csv
from src.paper import manuscript_figures as MF
from src.paper import sources as S

TABLES = paths.PROJECT_ROOT / "paper" / "tables"
FIGURES_DIR = paths.PROJECT_ROOT / "paper" / "manuscript" / "revision_p13" / "figures"
SUBJECTS = ("User01", "User02", "User07")
TARGETS = ("temperature", "humidity")
MATS_USER02 = ("22480", "22482")
MIN_RUN_S = 4 * 3600
STEP_S = 20
WINDOW_S = 40
QUANTILES = (("p05", 0.05), ("p25", 0.25), ("p50", 0.50), ("p75", 0.75), ("p95", 0.95))
FIGURES = {"figure6_target_distributions": "Figure 6", "figureS5_example_nights": "Figure S5"}


# ------------------------------------------------------------------------------------------------ figure data

def _seconds(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x)
    if np.issubdtype(x.dtype, np.datetime64):
        return x.astype("datetime64[s]").astype(np.int64)
    return x.astype(np.int64)


def longest_run_seconds(starts: np.ndarray, sessions: np.ndarray) -> int:
    """Longest duration covered by consecutive windows whose starts are STEP_S apart within one session (starts
    sorted). A single window covers WINDOW_S."""
    if starts.size == 0:
        return 0
    best, first = 0, 0
    for i in range(1, starts.size + 1):
        if i == starts.size or starts[i] - starts[i - 1] != STEP_S or sessions[i] != sessions[i - 1]:
            best = max(best, int(starts[i - 1] - starts[first]) + WINDOW_S)
            first = i
    return best


def select_night(runs: dict[tuple[int, str], int], mats: tuple[str, ...]) -> tuple[int, str]:
    """(night ordinal, branch) by the rule in the module docstring. `runs`: (ordinal, mat) -> longest run (s)."""
    ordinals = sorted({o for o, _ in runs})
    ok = lambda o, m: runs.get((o, m), 0) >= MIN_RUN_S  # noqa: E731
    for o in ordinals:
        if all(ok(o, m) for m in mats):
            return o, "all_mats_meet_rule"
    if len(mats) > 1:
        for o in ordinals:
            if ok(o, mats[0]):
                return o, f"only_{mats[0]}_meets_rule"
    o = max(ordinals, key=lambda k: (max(runs.get((k, m), 0) for m in mats), -k))
    return o, "no_night_meets_rule_longest_run"


def extract_figure_data(out_dir: Path = TABLES, example_nights_dir: Path | None = None) -> dict[str, int]:
    from src.evaluation import p6_robustness as P6
    from src.evaluation.p3_loso import P3Session
    from src.evaluation.p5_personalization import personalization_split
    from src.evaluation.protocol import load_protocol

    sess = P3Session(echo=False)
    pers = [r for r in personalization_split() if r["budget_nights"] == "0"]
    folds = {int(k): v for k, v in load_protocol()["loso"]["outer_folds"].items()}
    dist, series, events_out, selection = [], [], [], []
    for fold, held in sorted(folds.items()):
        fd = sess.fold(fold)
        m = (fd.partition == "test") & fd.labelled & (fd.prov["subject_id"] == held)
        y = fd.targets[m]
        dev = fd.prov["device_id"][m].astype(str)
        night = fd.prov["night_id"][m].astype(str)
        sess_id = fd.prov["session_id"][m].astype(str)
        start = _seconds(fd.prov["window_start"][m])
        press = fd.pressure[m].astype(np.float64).sum(axis=2).mean(axis=1) / (6 * 4095.0)
        mats = MATS_USER02 if held == "User02" else tuple(sorted(np.unique(dev)))
        # ---- Figure 6: distribution summaries per subject (User02 per mat)
        for mat in mats:
            k = dev == mat
            for i, tg in enumerate(TARGETS):
                v = y[k, i]
                dist.append({"subject_id": held, "mat": mat if held == "User02" else "all", "target": tg,
                             "n_windows": int(k.sum()), "n_nights": int(np.unique(night[k]).size),
                             "mean": float(v.mean()),
                             **{name: float(q) for (name, _), q in zip(QUANTILES, np.quantile(v, [q for _, q in
                                                                                                   QUANTILES]))}})
        if example_nights_dir is None:
            continue
        # ---- Figure S5 (withdrawn in P14; private directory only): night selection by the fixed rule
        ordinal = {r["night_id"]: int(r["night_ordinal"]) for r in pers if r["subject_id"] == held}
        primary = {r["night_id"] for r in pers if r["subject_id"] == held and r["primary_test"] == "1"}
        runs: dict[tuple[int, str], int] = {}
        for n in sorted(set(night) & primary, key=ordinal.get):
            for mat in mats:
                k = (night == n) & (dev == mat)
                order = np.argsort(start[k], kind="stable")
                runs[(ordinal[n], mat)] = longest_run_seconds(start[k][order], sess_id[k][order])
        chosen, branch = select_night(runs, mats)
        night_of = {v: k for k, v in ordinal.items()}[chosen]
        k_night = night == night_of
        t0 = int(start[k_night].min())
        t1 = int(start[k_night].max()) + WINDOW_S
        ev = P6.heater_events(held)
        for mat in mats:
            k = k_night & (dev == mat)
            order = np.argsort(start[k], kind="stable")
            for j in np.flatnonzero(k)[order]:
                series.append({"subject_id": held, "mat": mat if held == "User02" else "all",
                               "night_ordinal": chosen, "t_rel_h": (int(start[j]) + WINDOW_S - t0) / 3600.0,
                               "session_index": int(np.searchsorted(np.unique(sess_id[k]), sess_id[j])),
                               "pressure_total_fraction": float(press[j]), "temperature": float(y[j, 0]),
                               "humidity": float(y[j, 1])})
            ets, codes = ev.get(mat, (np.zeros(0, np.int64), np.zeros(0, dtype=object)))
            for t, c in zip(ets, codes):
                if t0 <= int(t) <= t1:
                    events_out.append({"subject_id": held, "mat": mat if held == "User02" else "all",
                                       "night_ordinal": chosen, "t_rel_h": (int(t) - t0) / 3600.0, "code": str(c)})
            selection.append({"subject_id": held, "mat": mat if held == "User02" else "all", "night_ordinal": chosen,
                              "branch": branch, "longest_run_h": runs.get((chosen, mat), 0) / 3600.0,
                              "n_windows_plotted": int(k.sum()),
                              "n_primary_nights_checked": len({o for o, _ in runs}),
                              "rule": "earliest primary-span night (ordinal >= 16) with a run of consecutive labelled "
                                      "40-s windows of at least 4 h; User02: on both mats"})
    write_csv(out_dir / "p13_figure_target_distribution.csv", dist, list(dist[0]))
    if example_nights_dir is not None:
        if Path(example_nights_dir).resolve().is_relative_to((paths.PROJECT_ROOT / "paper").resolve()):
            raise ValueError("Figure S5 data may not be written under paper/ (withdrawn from release; D-070)")
        write_csv(example_nights_dir / "p13_figure_night_series.csv", series, list(series[0]))
        write_csv(example_nights_dir / "p13_figure_night_events.csv", events_out,
                  ["subject_id", "mat", "night_ordinal", "t_rel_h", "code"])
        write_csv(example_nights_dir / "p13_figure_night_selection.csv", selection, list(selection[0]))
    return {"distribution_rows": len(dist), "series_rows": len(series), "event_rows": len(events_out),
            "selected": len(selection)}


# ------------------------------------------------------------------------------------------------ rendering

def _source_mean(subject: str, target: str) -> float:
    return float(S.cell("p10_loso_constants", "value", subject_id=subject, statistic="training_mean", target=target))


def figure6(out_dir: Path) -> Path:
    plt = MF._plt()
    rows = S.rows("p13_figure_target_distribution")
    cats = [("User01", "all"), ("User02", "22480"), ("User02", "22482"), ("User07", "all")]
    labels = ["User01", "User02\nmat 22480", "User02\nmat 22482", "User07"]
    fig, axes = plt.subplots(1, 2, figsize=(MF.FULL_WIDTH, 3.0))
    for ax, tg, panel in zip(axes, TARGETS, "ab"):
        stats = []
        for s, mat in cats:
            r = next(x for x in rows if x["subject_id"] == s and x["mat"] == mat and x["target"] == tg)
            stats.append({"med": float(r["p50"]), "q1": float(r["p25"]), "q3": float(r["p75"]),
                          "whislo": float(r["p05"]), "whishi": float(r["p95"]), "fliers": [], "label": ""})
        bp = ax.bxp(stats, positions=range(len(cats)), widths=0.55, patch_artist=True, showfliers=False,
                    medianprops={"color": MF.INK, "lw": 1.0}, whiskerprops={"color": MF.MUTED, "lw": 0.8},
                    capprops={"color": MF.MUTED, "lw": 0.8}, boxprops={"lw": 0.7, "edgecolor": MF.INK})
        for patch, (s, mat) in zip(bp["boxes"], cats):
            patch.set_facecolor(MF.COLORS[mat if s == "User02" else s])
            patch.set_alpha(0.55)
        for i, (s, _) in enumerate(cats):
            ax.plot([i - 0.36, i + 0.36], [_source_mean(s, tg)] * 2, color=MF.INK, lw=1.1, ls=(0, (2, 1.2)),
                    label="source-training mean" if i == 0 else None)
        ax.set_xticks(range(len(cats)), labels)
        ax.set_ylabel(f"{tg.capitalize()} ({MF.UNIT[tg]})")
        ax.set_title(f"({panel}) {tg}", loc="left")
        ax.grid(axis="y", color=MF.GRID, lw=0.6)
        ax.set_axisbelow(True)
    axes[0].legend(loc="upper left", frameon=False, handlelength=2.2)
    fig.tight_layout(w_pad=2.0)
    return MF._save(fig, out_dir, "figure6_target_distributions")


def figureS5(out_dir: Path) -> Path:
    plt = MF._plt()
    series = S.rows("p13_figure_night_series")
    events = S.rows("p13_figure_night_events")
    fig, axes = plt.subplots(3, 3, figsize=(MF.FULL_WIDTH, 5.6), sharex="col")
    quantities = (("pressure_total_fraction", "Total pressure\n(fraction of full scale)"),
                  ("temperature", "Temperature (°C)"), ("humidity", "Humidity (%RH)"))
    for col, subject in enumerate(SUBJECTS):
        mats = MATS_USER02 if subject == "User02" else ("all",)
        ordinal = next(r["night_ordinal"] for r in series if r["subject_id"] == subject)
        for row, (q, ylabel) in enumerate(quantities):
            ax = axes[row, col]
            for mat in mats:
                pts = [r for r in series if r["subject_id"] == subject and r["mat"] == mat]
                t = np.array([float(r["t_rel_h"]) for r in pts])
                v = np.array([float(r[q]) for r in pts])
                sess = np.array([int(r["session_index"]) for r in pts])
                brk = np.flatnonzero((np.diff(t) * 3600.0 > STEP_S + 1e-6) | (np.diff(sess) != 0)) + 1
                t, v = np.insert(t, brk, np.nan), np.insert(v, brk, np.nan)
                color = MF.COLORS[mat] if subject == "User02" else MF.COLORS[subject]
                ax.plot(t, v, color=color, lw=0.6, label=f"mat {mat}" if subject == "User02" and row == 0 else None)
            if q == "temperature":
                ymax = ax.get_ylim()[1]
                for e in (x for x in events if x["subject_id"] == subject):
                    on = e["code"] == "AHON"
                    color = MF.COLORS[e["mat"]] if subject == "User02" else MF.INK
                    ax.plot(float(e["t_rel_h"]), ymax, marker="v" if on else "^", ms=3.4, ls="none",
                            markeredgecolor=color, markerfacecolor=color if on else "white", markeredgewidth=0.7,
                            clip_on=False, zorder=5)
            ax.grid(color=MF.GRID, lw=0.5)
            ax.set_axisbelow(True)
            if col == 0:
                ax.set_ylabel(ylabel)
            if row == 0:
                ax.set_title(f"{subject}, night {ordinal}", loc="left")
            if row == 2:
                ax.set_xlabel("Hours since first window")
        if subject == "User02":
            axes[0, col].legend(loc="upper right", frameon=False, fontsize=6.5)
    handles = [plt.Line2D([], [], marker="v", ls="none", color=MF.INK, ms=3.4, label="heater-on code"),
               plt.Line2D([], [], marker="^", ls="none", markeredgecolor=MF.INK, markerfacecolor="white", ms=3.4,
                          markeredgewidth=0.7, label="heater-off code")]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.03, 1, 1), h_pad=0.6, w_pad=1.2)
    return MF._save(fig, out_dir, "figureS5_example_nights")


def render_all(out_dir: Path = FIGURES_DIR, include_example_nights: bool = False) -> list[Path]:
    """Figure 6 only; Figure S5 (withdrawn in P14) only on explicit request and never into paper/."""
    if include_example_nights and Path(out_dir).resolve().is_relative_to((paths.PROJECT_ROOT / "paper").resolve()):
        raise ValueError("Figure S5 may not be drawn under paper/ (withdrawn from release; D-070)")
    return [figure6(out_dir)] + ([figureS5(out_dir)] if include_example_nights else [])
