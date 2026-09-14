"""Manuscript Figures 1-4 and S1-S4 (P8), drawn only from the frozen figure-data tables.

- Figure 1 is a design schematic without data (paper/manuscript/FIGURE1_SCHEMATIC.md).
- Figures 2-4 and S1-S4 re-draw the committed report figures from `p5_figure_data` / `p6_figure_data` with the same
  encodings and palette (scripts/export_p5_tables.py, scripts/export_p6_tables.py), without report titles, at print
  size. Axis limits are matplotlib's automatic limits of the plotted data; nothing is cropped or rescaled.
- No calendar date: the x axes use budgets, start nights or night ordinals.
"""
from __future__ import annotations

from pathlib import Path

from src.data.io_guard import open_for_write
from src.paper import sources as S
from src.paper.manuscript_tables import GENERATED

SUBJECTS = ("User01", "User02", "User07")
BUDGETS = ("0", "1", "3", "7", "14")
ADAPT_BUDGETS = ("1", "3", "7", "14")
STARTS = ("12", "14", "16", "18", "21")
UNIT = {"temperature": "°C", "humidity": "%RH"}
# categorical palette of the report figures (validated default palette); the cohort mean is drawn in primary ink
COLORS = {"User01": "#2a78d6", "User02": "#eb6834", "User07": "#1baf7a", "unweighted_mean": "#0b0b0b",
          "22480": "#4a3aa7", "22482": "#e87ba4"}
MARKERS = {"User01": "o", "User02": "s", "User07": "^", "unweighted_mean": "D", "22480": "o", "22482": "s"}
INK, MUTED, GRID, BAND = "#0b0b0b", "#6f6d67", "#e1e0d9", "#f0efec"
# Figure 1 roles (schematic only; not subject colours)
ROLE = {"train": "#c9c7bf", "held_out": "#e3a52b", "adapt": "#6b54c4", "unused": "#eeede8", "test": "#e3a52b"}
DPI = 300
FULL_WIDTH = 6.8          # inches, full text width
SINGLE_WIDTH = 4.6

FIGURES = {
    "figure1_study_design": "Figure 1",
    "figure2_temperature_personalization": "Figure 2",
    "figure3_humidity_personalization": "Figure 3",
    "figure4_night_robustness": "Figure 4",
    "figureS1_abs_bias": "Figure S1",
    "figureS2_start_span_sensitivity": "Figure S2",
    "figureS3_level_trajectory": "Figure S3",
    "figureS4_user02_mats": "Figure S4",
}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8.5,
        "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7.5, "axes.edgecolor": MUTED,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "axes.spines.top": False,
        "axes.spines.right": False, "figure.facecolor": "white", "axes.facecolor": "white",
        "svg.hashsalt": "p8", "path.simplify": False})
    return plt


QA: dict[str, list[tuple[str, str]]] = {}         # text overlaps found while rendering, per figure


def _save(fig, out_dir: Path, stem: str) -> Path:
    QA[stem] = text_overlaps(fig)
    path = out_dir / f"{stem}.png"
    with open_for_write(path, "wb") as fh:
        fig.savefig(fh, format="png", dpi=DPI, metadata={"Software": None}, bbox_inches="tight", pad_inches=0.03)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return path


def _p5(figure: str, panel: str) -> list[dict[str, str]]:
    return S.rows("p5_figure_data", figure=figure, panel=panel)


def _p6(figure: str, **kw: str) -> list[dict[str, str]]:
    return S.rows("p6_figure_data", figure=figure, **kw)


# --- Figure 1 ------------------------------------------------------------------------------------------------------

def figure1(out_dir: Path) -> Path:
    plt = _plt()
    from matplotlib.patches import FancyBboxPatch, Rectangle

    fig, ax = plt.subplots(figsize=(FULL_WIDTH, 5.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 66)
    ax.axis("off")

    def box(x, y, w, h, text, fc="white", size=6.5, weight="normal"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.8", fc=fc, ec=INK,
                                    lw=0.7))
        t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, weight=weight, color=INK,
                    linespacing=1.3)
        _fit(fig, ax, t, w - 1.0, h - 0.3)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8, shrinkA=0, shrinkB=0))

    def title(x, y, text):
        ax.text(x, y, text, ha="left", va="bottom", fontsize=7.5, weight="bold", color=INK)

    # (a) data preparation
    title(1, 62.4, "(a) Data preparation")
    a = [(1, "Smart-mat logs:\n6 pressure channels,\ntemperature, humidity"),
         (26, "Audited canonical\ndataset (checksums,\nflags, sessions)"),
         (51, "Splits defined first,\nthen 40-s windows\n(8 steps × 6 channels)"),
         (76, "3 subjects,\n4 mat streams\n(1 subject, 2 mats)")]
    for x, t in a:
        box(x, 52.4, 22, 8.6, t)
    for (x, _), (nx, _) in zip(a, a[1:]):
        arrow(x + 22.4, 56.7, nx - 0.5, 56.7)

    # (b) strict leave-one-subject-out
    title(1, 47.4, "(b) Strict leave-one-subject-out")
    for k in range(3):
        y = 40.4 - k * 6.4
        ax.text(1, y + 2.2, f"Fold {k + 1}", ha="left", va="center", fontsize=6.5, color=INK)
        for j, name in enumerate("ABC"):
            held = j == k
            box(7.8 + j * 11.0, y, 10.3, 4.6, f"Subject {name}\n{'held out' if held else 'training'}",
                fc=ROLE["held_out" if held else "train"], size=6.2, weight="bold" if held else "normal")
    note = ax.text(1, 18.2, "Model selection: two swapped\ninner splits of the two\ntraining subjects only. "
                            "Held-out\nsubject evaluated once.",
                   ha="left", va="center", fontsize=6.2, color=INK, linespacing=1.35)
    _fit(fig, ax, note, 26.5, 9.0)
    box(28.2, 14.6, 16.4, 7.2, "Base model\nper fold and seed\n(RAW-TCN)")
    arrow(36.4, 27.4, 36.4, 22.3)
    arrow(45.0, 18.2, 49.0, 18.2)
    ax.text(49.3, 18.2, "(c)", ha="left", va="center", fontsize=6.5, color=MUTED)

    # (c) chronological personalization
    title(51, 47.4, "(c) Chronological personalization of the held-out subject")
    ax.text(51, 44.6, "Base model from (b), all parameters fine-tuned on nights 1…b (10 epochs)",
            ha="left", va="center", fontsize=6.2, color=MUTED)
    n_show, x0, cw = 22, 58.6, 1.55
    for i, b in enumerate((0, 1, 3, 7, 14)):
        y = 39.6 - i * 4.1
        ax.text(57.4, y + 1.3, f"b = {b}", ha="right", va="center", fontsize=6.5, color=INK)
        for n in range(1, n_show + 1):
            if n <= b:
                fc, hatch = ROLE["adapt"], None
            elif b and n == b + 1:
                fc, hatch = "white", "//////"
            elif n >= 16:
                fc, hatch = ROLE["test"], None
            else:
                fc, hatch = ROLE["unused"], None
            ax.add_patch(Rectangle((x0 + (n - 1) * cw, y), cw * 0.84, 2.6, fc=fc, ec=MUTED if hatch else "none",
                                   lw=0.4, hatch=hatch))
        ax.text(x0 + n_show * cw + 0.5, y + 1.3, "…", ha="left", va="center", fontsize=7, color=INK)
    for n in (1, 5, 10, 16, 20):
        ax.text(x0 + (n - 1) * cw + cw * 0.42, 22.6, str(n), ha="center", va="top", fontsize=6, color=MUTED)
    ax.text(x0 + (n_show / 2) * cw, 20.2, "Night ordinal (primary test span identical for every b)", ha="center",
            va="top", fontsize=6.2, color=MUTED)
    legend = [("adapt", None, "adaptation nights 1…b"), ("buffer", "//////", "buffer night b + 1 (unused)"),
              ("unused", None, "not in primary test span"), ("test", None, "primary test span (nights ≥ 16)")]
    for j, (key, hatch, label) in enumerate(legend):
        lx, ly = 53 + (j % 2) * 23.5, 14.6 - (j // 2) * 3.0
        ax.add_patch(Rectangle((lx, ly), 1.8, 1.8, fc="white" if key == "buffer" else ROLE[key],
                               ec=MUTED if hatch else "none", lw=0.4, hatch=hatch))
        ax.text(lx + 2.5, ly + 0.9, label, ha="left", va="center", fontsize=6.2, color=INK)

    # (d) evaluation and reproduction
    title(1, 7.6, "(d) Evaluation and reproduction")
    box(1, 0.6, 47.5, 6.0, "Per-subject MAE, RMSE and bias on the primary span;\n"
                           "night-level paired bootstrap of ΔMAE (base − adapted)")
    box(51.5, 0.6, 47.5, 6.0, "Selected models, predictions and result tables\n"
                              "reproduced from the de-identified release candidate")
    return _save(fig, out_dir, "figure1_study_design")

def _fit(fig, ax, text, width: float, height: float, minimum: float = 6.0) -> None:
    """Shrink a text until it fits a width x height box given in data units (no label may overflow its box)."""
    renderer = fig.canvas.get_renderer()
    (x0, y0), (x1, y1) = ax.transData.transform([(0, 0), (width, height)])
    while text.get_fontsize() > minimum:
        bb = text.get_window_extent(renderer)
        if bb.width <= x1 - x0 and bb.height <= y1 - y0:
            return
        text.set_fontsize(text.get_fontsize() - 0.1)
    raise ValueError(f"text does not fit its box: {text.get_text()!r}")


def text_overlaps(fig) -> list[tuple[str, str]]:
    """Pairs of visible, non-empty texts whose rendered extents intersect (formatting QA)."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    hidden = set()
    for ax in fig.axes:                              # tick labels outside the view limits are not drawn
        for axis, (lo, hi) in ((ax.xaxis, sorted(ax.get_xlim())), (ax.yaxis, sorted(ax.get_ylim()))):
            for tick in axis.get_major_ticks():
                if not lo - 1e-9 <= tick.get_loc() <= hi + 1e-9:
                    hidden.update((id(tick.label1), id(tick.label2)))
    texts, seen = [], set()
    from matplotlib.text import Text
    for t in fig.findobj(match=Text):
        if id(t) in seen or id(t) in hidden or not t.get_visible() or not t.get_text().strip():
            continue
        seen.add(id(t))
        texts.append(t)
    boxes = [(t.get_text(), t.get_window_extent(renderer)) for t in texts]
    out = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (a, ba), (b, bb) = boxes[i], boxes[j]
            if ba.overlaps(bb) and ba.width > 0 and bb.width > 0:
                out.append((a, b))
    return out


# --- Figures 2, 3, S1, S4: MAE-type curves over the adaptation budget ------------------------------------------------

def _budget_curves(ax, figure: str, panel: str, ylabel: str) -> None:
    rows = _p5(figure, panel)
    xs = list(range(len(BUDGETS)))
    series = list(dict.fromkeys(r["series"] for r in rows))
    ends = []
    for s in series:
        pts = sorted((r for r in rows if r["series"] == s), key=lambda r: BUDGETS.index(r["budget_nights"]))
        y = [float(r["value"]) for r in pts]
        mean = s == "unweighted_mean"
        ax.plot(xs, y, color=COLORS[s], lw=1.6, ls="--" if mean else "-", marker=MARKERS[s], ms=4.5,
                label="Unweighted mean (3 subjects)" if mean else s, zorder=3)
        if not mean:
            ax.vlines(xs, [float(r["seed_min"]) for r in pts], [float(r["seed_max"]) for r in pts],
                      color=COLORS[s], lw=0.9, alpha=0.7, zorder=2)
        ends.append([y[-1], "mean" if mean else s])
    lo, hi = ax.get_ylim()
    for y_lab, name in spread_labels(ends, 0.065 * (hi - lo)):
        ax.annotate(name, (xs[-1], y_lab), xytext=(6, 0), textcoords="offset points", va="center", fontsize=7,
                    color=INK)
    ax.set_xticks(xs, BUDGETS)
    ax.set_xlim(-0.3, len(xs) - 0.25)
    ax.set_xlabel("Adaptation budget b (nights; b = 0: base model)")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color=GRID, lw=0.5)


def spread_labels(ends: list[list], gap: float) -> list[tuple[float, str]]:
    """Place end labels at least `gap` apart, each cluster centred on the mean of its members' line ends."""
    items = sorted((float(y), str(n)) for y, n in ends)
    clusters = [[it] for it in items]
    while True:
        pos = []
        for c in clusters:
            centre = sum(y for y, _ in c) / len(c)
            first = centre - gap * (len(c) - 1) / 2
            pos.append([first + gap * k for k in range(len(c))])
        merged = False
        for i in range(len(clusters) - 1):
            if pos[i + 1][0] - pos[i][-1] < gap - 1e-12:
                clusters[i:i + 2] = [clusters[i] + clusters[i + 1]]
                merged = True
                break
        if not merged:
            return [(y, name) for c, ys in zip(clusters, pos) for (_, name), y in zip(c, ys)]


def _legend_below(fig, axes, ncol: int, y: float = -0.02) -> None:
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, y), ncol=ncol, frameon=False)


def figure_personalization(out_dir: Path, target: str) -> Path:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(SINGLE_WIDTH, 3.0))
    fig_id = "P5-1" if target == "temperature" else "P5-2"
    _budget_curves(ax, fig_id, target, f"{target.capitalize()} MAE ({UNIT[target]})")
    fig.tight_layout()
    _legend_below(fig, [ax], 4, y=0.0)
    stem = "figure2_temperature_personalization" if target == "temperature" else "figure3_humidity_personalization"
    return _save(fig, out_dir, stem)


def figure_s1(out_dir: Path) -> Path:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.9))
    for ax, (tag, t) in zip(axes, (("(a)", "temperature"), ("(b)", "humidity"))):
        _budget_curves(ax, "P5-3", t, f"{t.capitalize()} |bias| ({UNIT[t]})")
        ax.set_title(f"{tag} {t.capitalize()}", loc="left")
    fig.tight_layout()
    _legend_below(fig, axes, 4, y=0.0)
    return _save(fig, out_dir, "figureS1_abs_bias")


def figure_s4(out_dir: Path) -> Path:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.9))
    for ax, (tag, t) in zip(axes, (("(a)", "temperature"), ("(b)", "humidity"))):
        _budget_curves(ax, "P5-4", t, f"User02 {t} MAE ({UNIT[t]})")
        ax.set_title(f"{tag} {t.capitalize()}", loc="left")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.tight_layout()
    fig.legend(handles, [f"mat {x}" for x in labels], loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2,
               frameon=False)
    return _save(fig, out_dir, "figureS4_user02_mats")


# --- Figure 4: night-level bootstrap ---------------------------------------------------------------------------------

def figure4(out_dir: Path) -> Path:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(FULL_WIDTH, 2.9))
    for ax, (tag, fig_id, t) in zip(axes, (("(a)", "P6-1", "temperature"), ("(b)", "P6-2", "humidity"))):
        ax.axhline(0, color=INK, lw=0.8, zorder=1)
        for i, s in enumerate(SUBJECTS):
            pts = sorted(_p6(fig_id, series=s), key=lambda r: ADAPT_BUDGETS.index(r["x"]))
            xs = [ADAPT_BUDGETS.index(r["x"]) + (i - 1) * 0.2 for r in pts]
            y = [float(r["value"]) for r in pts]
            lo = [float(r["value"]) - float(r["lower"]) for r in pts]
            hi = [float(r["upper"]) - float(r["value"]) for r in pts]
            ax.errorbar(xs, y, yerr=[lo, hi], fmt=MARKERS[s], color=COLORS[s], ms=4.5, lw=1.2, capsize=2.5,
                        label=s, zorder=3)
        ax.set_xticks(range(len(ADAPT_BUDGETS)), ADAPT_BUDGETS)
        ax.set_xlabel("Adaptation budget b (nights)")
        ax.set_ylabel(f"ΔMAE = base − adapted ({UNIT[t]})")
        ax.set_title(f"{tag} {t.capitalize()}", loc="left")
        ax.grid(axis="y", color=GRID, lw=0.5)
    fig.tight_layout()
    _legend_below(fig, axes, 3, y=0.0)
    return _save(fig, out_dir, "figure4_night_robustness")


# --- Figure S2: start-span sensitivity -------------------------------------------------------------------------------

def figure_s2(out_dir: Path) -> Path:
    plt = _plt()
    fig, axes = plt.subplots(2, 4, figsize=(FULL_WIDTH, 4.2), sharex=True)
    for row, (tag, t) in enumerate((("(a)", "temperature"), ("(b)", "humidity"))):
        for col, b in enumerate(ADAPT_BUDGETS):
            ax = axes[row][col]
            ax.axhline(0, color=INK, lw=0.8, zorder=1)
            ax.axvline(16, color=MUTED, lw=0.8, ls=":", zorder=1)
            for s in SUBJECTS:
                pts = sorted(_p6("P6-3", panel=f"{t}|b={b}", series=s), key=lambda r: int(r["x"]))
                xs = [int(r["x"]) for r in pts]
                ax.plot(xs, [float(r["value"]) for r in pts], color=COLORS[s], marker=MARKERS[s], lw=1.3, ms=3.5,
                        label=s, zorder=3)
                ax.vlines(xs, [float(r["lower"]) for r in pts], [float(r["upper"]) for r in pts], color=COLORS[s],
                          lw=0.8, alpha=0.7, zorder=2)
            ax.set_title(f"{tag} {t.capitalize()}, b = {b}" if col == 0 else f"b = {b}", loc="left", fontsize=7.5)
            ax.set_xticks([int(x) for x in STARTS])
            ax.tick_params(labelsize=6.5)
            ax.grid(axis="y", color=GRID, lw=0.5)
            if row == 1:
                ax.set_xlabel("Start night of test span", fontsize=7)
        axes[row][0].set_ylabel("Adaptation gain G (%)", fontsize=7)
    fig.tight_layout()
    _legend_below(fig, axes[0], 3, y=0.0)
    return _save(fig, out_dir, "figureS2_start_span_sensitivity")


# --- Figure S3: level trajectories -----------------------------------------------------------------------------------

def figure_s3(out_dir: Path) -> Path:
    plt = _plt()
    panels = (("(a)", "User07", "temperature"), ("(b)", "User01", "humidity"), ("(c)", "User02", "temperature"))
    fig, axes = plt.subplots(1, 3, figsize=(FULL_WIDTH, 2.6))
    for ax, (tag, s, t) in zip(axes, panels):
        key = f"{s}|{t}"
        nights = sorted(_p6("P6-4", panel=key, series="night_mean"), key=lambda r: int(r["x"]))
        roll = sorted(_p6("P6-4", panel=key, series="rolling_mean_7"), key=lambda r: int(r["x"]))
        ax.axvspan(0.5, 14.5, color=BAND, zorder=0, label="adaptation nights (b ≤ 14)")
        ax.axvline(15.5, color=MUTED, lw=0.8, ls=":", zorder=1, label="primary test from night 16")
        ax.scatter([int(r["x"]) for r in nights], [float(r["value"]) for r in nights], s=4, color=MUTED, zorder=2,
                   label="night mean")
        ax.plot([int(r["x"]) for r in roll], [float(r["value"]) for r in roll], color=COLORS[s], lw=1.4, zorder=3,
                label="rolling mean (7 nights)")
        for series, ls, lab in (("primary_mean", "--", "primary-span mean"),
                                ("training_pool_mean", "-.", "base training-pool mean")):
            v = float(S.select("p6_figure_data", figure="P6-4", panel=key, series=series)["value"])
            ax.axhline(v, color=INK, lw=0.8, ls=ls, zorder=2, label=lab)
        ax.set_title(f"{tag} {s}, {t}", loc="left", fontsize=7.5)
        ax.set_xlabel("Night ordinal", fontsize=7)
        ax.set_ylabel(f"{t.capitalize()} ({UNIT[t]})", fontsize=7)
        ax.tick_params(labelsize=6.5)
        ax.grid(axis="y", color=GRID, lw=0.5)
    fig.tight_layout()
    from matplotlib.lines import Line2D
    handles, labels = axes[0].get_legend_handles_labels()
    k = labels.index("rolling mean (7 nights)")
    handles[k] = Line2D([], [], color=MUTED, lw=1.4)
    labels[k] = "rolling mean (7 nights; subject colour)"
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=3, frameon=False)
    return _save(fig, out_dir, "figureS3_level_trajectory")


def render_all(out_dir: Path = GENERATED / "figures") -> list[Path]:
    return [figure1(out_dir),
            figure_personalization(out_dir, "temperature"),
            figure_personalization(out_dir, "humidity"),
            figure4(out_dir),
            figure_s1(out_dir),
            figure_s2(out_dir),
            figure_s3(out_dir),
            figure_s4(out_dir)]
