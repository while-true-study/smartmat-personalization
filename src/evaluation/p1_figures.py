"""P1 figures (research-facing candidates, not frozen paper figures). Encoding: colour = subject, line style =
domain slice within the subject; sequential single hue for magnitudes."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from src.data.io_guard import open_for_write
from src.evaluation.domain_shift import MAIN_SLICES, MINOR_SLICES

C = {"User01": "#2a78d6", "User02": "#eb6834", "User07": "#1baf7a"}
GRAY, INK, INK2, GRID, SURFACE = "#9a9892", "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
LS = {"User01/s1": "-", "User01/s2": "--", "User02/22480": "-", "User02/22482/normal": "--",
      "User02/22482/p1_shift": ":", "User07": "-", "User02/22482/p1_transition": "-"}
_EPOCH = datetime(1970, 1, 1)


def color(slice_name: str) -> str:
    return GRAY if slice_name in MINOR_SLICES else C[slice_name.split("/")[0].split(" ")[0]]


def _style(ax, title, xlabel="", ylabel=""):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.set_xlabel(xlabel, fontsize=8, color=INK2)
    ax.set_ylabel(ylabel, fontsize=8, color=INK2)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.tick_params(colors=INK2, labelsize=7)
    for s in ax.spines.values():
        s.set_color(GRID)


def _save(fig, path: Path) -> str:
    with open_for_write(path, "wb") as fh:
        fig.savefig(fh, format="png", facecolor=SURFACE)
    return path.name


def make_all(res: dict, out: Path) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    D, masks = res["data"], res["masks"]
    made = []

    # Figure 1 — coverage timeline: subject x device x phase x season
    rows = list(MAIN_SLICES) + list(MINOR_SLICES)
    fig, ax = plt.subplots(figsize=(11, 3.8), dpi=150, facecolor=SURFACE)
    bands = [("2025-08-01", "2025-09-01", "summer"), ("2025-09-01", "2025-12-01", "autumn"), ("2025-12-01", "2026-03-01", "winter"),
             ("2026-03-01", "2026-06-01", "spring"), ("2026-06-01", "2026-09-01", "summer"), ("2026-09-01", "2026-10-01", "autumn")]
    for i, (a, b, lab) in enumerate(bands):
        a, b = datetime.fromisoformat(a), datetime.fromisoformat(b)
        ax.axvspan(a, b, color=GRID if i % 2 == 0 else SURFACE, alpha=0.6, zorder=0)
        ax.text(a + (b - a) / 2, len(rows) - 0.35, lab, ha="center", va="bottom", fontsize=7, color=INK2)
    for y, name in enumerate(rows[::-1]):
        nights = np.unique(D.night[masks[name]])
        ax.broken_barh([(mdates.date2num(_EPOCH + timedelta(days=int(n), hours=12)), 1.0) for n in nights],
                       (y - 0.32, 0.64), facecolors=color(name), edgecolor=SURFACE, linewidth=0.3)
    for d, lab in (("2026-01-25T12:00", "User01 sensor change (D-019)"), ("2026-08-20T12:00", "22482 P1 shift (D-022)")):
        ax.axvline(datetime.fromisoformat(d), color=INK, linestyle="--", linewidth=0.8)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows[::-1], fontsize=8)
    ax.set_ylim(-0.6, len(rows) - 0.1)
    ax.set_xlim(datetime(2025, 8, 1), datetime(2026, 10, 1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    _style(ax, "Recorded nights per domain slice — subject, device, phase and season change together (dashed: frozen phase boundaries)")
    fig.tight_layout()
    made.append(_save(fig, out / "fig1_coverage_timeline.png"))
    plt.close(fig)

    # Figure 2 — pressure descriptors by domain slice
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150, facecolor=SURFACE, gridspec_kw={"width_ratios": [1.3, 1]})
    q = np.linspace(0, 1, 201)
    for name in MAIN_SLICES:
        m = masks[name] & D.pd.loaded
        a1.plot(np.quantile(D.pd.total[m], q), q, color=color(name), linestyle=LS[name], linewidth=1.8, label=name)
    a1.set_xlim(0, 12000)
    a1.legend(frameon=False, fontsize=7, loc="lower right")
    _style(a1, "Pressure sum on loaded rows (ECDF)", "pressure sum (raw units)", "cumulative share")
    share = np.array([[np.mean(D.pd.active[masks[n] & D.pvalid] == k) for k in range(7)] for n in MAIN_SLICES])
    im = a2.imshow(share, cmap="Blues", vmin=0, vmax=0.5, aspect="auto")
    for i in range(share.shape[0]):
        for j in range(7):
            a2.text(j, i, f"{share[i, j]:.2f}", ha="center", va="center", fontsize=6.5,
                    color="white" if share[i, j] > 0.3 else INK)
    a2.set_xticks(range(7))
    a2.set_yticks(range(len(MAIN_SLICES)))
    a2.set_yticklabels(MAIN_SLICES, fontsize=7)
    _style(a2, "Share of rows by number of active channels", "active channels (0 = empty mat)")
    a2.grid(False)
    fig.colorbar(im, ax=a2, fraction=0.04)
    fig.tight_layout()
    made.append(_save(fig, out / "fig2_pressure_by_domain.png"))
    plt.close(fig)

    # Figure 3 — targets by domain slice (row quantiles and night medians)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150, facecolor=SURFACE)
    rng = np.random.default_rng(0)
    for ax, (var, x, ok, unit) in zip(axes, (("temperature", D.temp, D.t_ok, "°C"), ("humidity", D.humid, D.h_ok, "%RH"))):
        for i, name in enumerate(MAIN_SLICES):
            v = masks[name] & ok
            p05, q25, q50, q75, p95 = np.percentile(x[v], [5, 25, 50, 75, 95])
            ax.plot([p05, p95], [i, i], color=color(name), linewidth=1.2)
            ax.add_patch(plt.Rectangle((q25, i - 0.25), max(q75 - q25, 0.15), 0.5, facecolor=color(name), alpha=0.35,
                                       edgecolor=color(name)))
            ax.plot([q50, q50], [i - 0.3, i + 0.3], color=INK, linewidth=1.5)
            nights = np.unique(D.night[v])
            med = np.array([np.median(x[v & (D.night == n)]) for n in nights])
            ax.scatter(med, i + 0.38 + rng.uniform(-0.05, 0.05, med.size), s=5, color=color(name), alpha=0.6)
        ax.set_yticks(range(len(MAIN_SLICES)))
        ax.set_yticklabels(MAIN_SLICES if var == "temperature" else [], fontsize=7)
        ax.invert_yaxis()
        _style(ax, f"{var.capitalize()}: p05–p95, IQR box, median; dots = night medians", unit)
    fig.tight_layout()
    made.append(_save(fig, out / "fig3_targets_by_domain.png"))
    plt.close(fig)

    # Figure 4 — within-subject/device shift vs between-subject-associated shift
    dist = res["domain_distance_matrix"]
    pairs = [("User01/s1", "User01/s2"), ("User02/22480", "User02/22482/normal"), ("User02/22482/normal", "User02/22482/p1_shift"),
             ("User01/s2", "User07"), ("User02/22480", "User07"), ("User02/22482/normal", "User07"), ("User01/s1", "User07"),
             ("User01 (pooled)", "User07 (pooled)"), ("User01 (pooled)", "User02 (pooled)"), ("User07 (pooled)", "User02 (pooled)")]
    kinds = ["within"] * 3 + ["between (slices)"] * 4 + ["between (pooled)"] * 3
    variables = ["pressure_sum", "active_channel_count", "temperature", "humidity"]
    look = {(r["domain_a"], r["domain_b"], r["variable"]): r for r in dist}
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=150, facecolor=SURFACE)
    for ax, key, vmax, title in ((axes[0], "cliffs_delta_units", 1.0, "|Cliff's δ| between night medians"),
                                 (axes[1], "w1_over_pooled_iqr", 2.5, "Row-level W1 / pooled IQR")):
        mat = np.array([[abs(float(look[(a, b, v)][key] or 0)) for v in variables] for a, b in pairs])
        ax.imshow(np.minimum(mat, vmax), cmap="Blues", vmin=0, vmax=vmax, aspect="auto")
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if mat[i, j] > 0.6 * vmax else INK)
        ax.set_xticks(range(len(variables)))
        ax.set_xticklabels(["pressure sum", "active ch.", "temperature", "humidity"], fontsize=7)
        ax.set_yticks(range(len(pairs)))
        ax.set_yticklabels([f"[{k}] {a} ↔ {b}" for (a, b), k in zip(pairs, kinds)] if ax is axes[0] else [], fontsize=6.5)
        for yline in (2.5, 6.5):
            ax.axhline(yline, color=INK, linewidth=0.8)
        _style(ax, title)
        ax.grid(False)
    fig.suptitle("Within-subject/device shifts are as large as between-subject-associated shifts (subject, period and device confounded)",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout()
    made.append(_save(fig, out / "fig4_within_vs_between_shift.png"))
    plt.close(fig)

    # Figure 5 — month and time-of-night target shift
    temporal = [r for r in res["monthly_distribution"] if r["period_type"] == "month"]
    months = sorted({r["period"] for r in temporal})
    ton = [r for r in res["time_of_night_summary"] if r["bin_type"] == "hour_of_day"]
    hours = [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), dpi=150, facecolor=SURFACE)
    for col, (var, unit) in enumerate((("temperature", "°C"), ("humidity", "%RH"))):
        ax = axes[0, col]
        for name in MAIN_SLICES:
            pts = [(months.index(r["period"]), r[f"{var}_median"]) for r in temporal if r["slice"] == name and r[f"{var}_median"] is not None]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color(name), linestyle=LS[name], marker="o", markersize=3,
                    linewidth=1.6, label=name)
        ax.set_xticks(range(len(months)))
        ax.set_xticklabels([m[2:] for m in months], fontsize=6.5, rotation=45)
        _style(ax, f"Monthly median {var} by slice", "month", unit)
        ax = axes[1, col]
        for name in MAIN_SLICES:
            pts = {r["bin"]: r[f"{var}_dev_from_night_median"] for r in ton if r["slice"] == name and r["share_of_slice_rows"] >= 0.02}
            xs = [i for i, h in enumerate(hours) if h in pts and pts[h] is not None]
            ax.plot(xs, [pts[hours[i]] for i in xs], color=color(name), linestyle=LS[name], marker="o", markersize=3, linewidth=1.6)
        ax.set_xticks(range(len(hours)))
        ax.set_xticklabels([f"{h:02d}" for h in hours], fontsize=6.5)
        _style(ax, f"{var.capitalize()} − night median, by clock hour", "clock hour (naive local time; hours with ≥ 2 % of rows)", unit)
    axes[0, 0].legend(frameon=False, fontsize=6.5, loc="best")
    fig.tight_layout()
    made.append(_save(fig, out / "fig5_month_and_time_of_night.png"))
    plt.close(fig)

    # Figure 6 — pressure–target relationship by slice (binned medians)
    rel = [r for r in res["pressure_target_relation"] if r["kind"] == "binned" and r["x"] == "pressure_sum"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150, facecolor=SURFACE)
    for ax, (var, unit) in zip(axes, (("temperature", "°C"), ("humidity", "%RH"))):
        for name in MAIN_SLICES:
            pts = [(r["x_median"], r["y_median"]) for r in rel if r["slice"] == name and r["y"] == var]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color(name), linestyle=LS[name], marker="o", markersize=3,
                    linewidth=1.6, label=name)
        _style(ax, f"Median {var} per pressure-sum decile (within slice)", "pressure sum, decile median", unit)
    axes[0].legend(frameon=False, fontsize=6.5, loc="best")
    fig.tight_layout()
    made.append(_save(fig, out / "fig6_pressure_target_relation.png"))
    plt.close(fig)
    return made
