"""P0 analysis A7 — temporal gap distribution and session-boundary sensitivity. Read-only on raw data.

For each primary subject/device timeline (User01, User02/22480, User02/22482, User07) this compares
  Timeline A  raw parsed rows in time order
  Timeline B  audit-only view without the identical upload-chunk copies identified by A5
              (src/data/duplicates.upload_copy_mask); nothing else is dropped
and reports step/gap distributions, upload-chunk-aligned gaps, gap context and how candidate
session thresholds change the session structure. No session definition is fixed, no session ID is
created and nothing is written back to data/ (src/data/temporal.py).

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/temporal/:
  gap_summary.csv                 step statistics per group and timeline (+ reference groups)
  gap_distribution.csv            counts per gap bucket
  gap_ecdf.csv                    ECDF of steps on a log grid
  large_gaps.csv                  every gap > 60 s in Timeline B with its context
  user02_22482_gap_patterns.csv   22482 gaps of 25 min-12 h with upload-chunk alignment
  threshold_sensitivity.csv       candidate thresholds x timeline x known-gap variant
  session_candidate_summary.csv   per candidate session (Timeline B; selected thresholds)
  figures/*.png                   QA figures (gap ECDF, sessions and median duration vs threshold)
  temporal_run_meta.json

Usage:
    python scripts/audit_temporal_gaps.py
"""
from __future__ import annotations

import gc
import platform
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.duplicates import (  # noqa: E402
    overlapping_file_pairs, repeated_block_members, row_keys, subject_device_groups, upload_copy_mask,
)
from src.data.io_guard import open_for_write, write_csv, write_json  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.provenance import SourceData, load_sources  # noqa: E402
from src.data.temporal import (  # noqa: E402
    THRESHOLDS_MIN, bucket_counts, build_timeline, candidate_sessions, chance_alignment_rate, chunk_alignment,
    ecdf_points, files_with_multiple_sessions, gap_context, recording_nights, session_rows, session_stats,
    step_summary, steps,
)

PRIMARY = [("User01", "unknown"), ("User02", "22480"), ("User02", "22482"), ("User07", "unknown")]
LABELS = {("User01", "unknown"): "User01", ("User02", "22480"): "User02/22480",
          ("User02", "22482"): "User02/22482", ("User07", "unknown"): "User07"}
SESSION_TABLE_THRESHOLDS_MIN = (5, 30, 60, 120)
BRIDGE_MAX_CHUNKS = 3            # variant: chunk-aligned gaps of 1-3 chunks treated as missing interval
ECDF_GRID = sorted({int(x) for x in np.round(np.logspace(0, np.log10(2 * 86400), 80))})
_EPOCH = datetime(1970, 1, 1)
# dataviz reference palette, categorical slots 1-4 in fixed order (validated: adjacent CVD 9.1, normal 22.9)
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"


def iso(sec) -> str:
    return (_EPOCH + timedelta(seconds=int(sec))).isoformat(sep=" ")


def columns(rows: list[dict], first: list[str]) -> list[str]:
    cols = list(first)
    for r in rows:
        cols += [k for k in r if k not in cols]
    return cols


def analyse_group(src: SourceData, label: str, primary: bool, out: dict, minute_resolution: bool = False) -> None:
    keys = row_keys(src)
    pairs = overlapping_file_pairs(src, keys)
    if minute_resolution:
        # identical rows within one minute are expected in legacy exports; nothing is treated as a copy
        copies = members = np.zeros(src.n, bool)
    else:
        copies = upload_copy_mask(src, keys, pairs)
        members = repeated_block_members(src, keys, pairs)
    tls = {"A_raw": build_timeline(src, "A_raw"), "B_audit_view": build_timeline(src, "B_audit_view", copies)}
    for name, tl in tls.items():
        dt = steps(tl)
        ca = chunk_alignment(dt)
        long = (dt >= 1500) & (dt <= 43200)
        near = {m: (np.abs(dt - m * 60) <= 300) for m in (30, 60, 90)}
        out["summary"].append({
            "group": label, "role": "primary" if primary else "reference", "timeline": name,
            "rows": tl.n, "rows_excluded_as_upload_copies": int(copies.sum()) if name == "B_audit_view" else 0,
            "recording_nights": recording_nights(tl.ts), "calendar_dates": int(np.unique(tl.ts // 86400).size),
            **step_summary(dt),
            "gaps_25min_12h": int(long.sum()), "chunk_aligned_25min_12h": int((ca["aligned"] & long).sum()),
            "chunk_aligned_share": round(float((ca["aligned"] & long).sum() / long.sum()), 4) if long.any() else None,
            "chance_alignment_rate": round(chance_alignment_rate(), 4),
            **{f"gaps_near_{m}min": int(v.sum()) for m, v in near.items()},
            **{f"aligned_near_{m}min": int((v & ca["aligned"]).sum()) for m, v in near.items()},
        })
        out["dist"] += [{"group": label, "timeline": name, **b} for b in bucket_counts(dt)]
        out["ecdf"] += [{"group": label, "timeline": name, **e} for e in ecdf_points(dt, ECDF_GRID)]
        if not primary:
            continue
        nights = recording_nights(tl.ts)
        bridge = ca["aligned"] & (ca["n_chunks"] <= BRIDGE_MAX_CHUNKS)
        for variant, br in (("plain", None), ("bridge_chunk_aligned_1to3", bridge)):
            for m in THRESHOLDS_MIN:
                sess = candidate_sessions(tl, m * 60, br)
                rows = session_rows(src, tl, sess)
                out["sens"].append({"group": label, "timeline": name, "variant": variant, "threshold_min": m,
                                    **session_stats(rows, nights),
                                    "files_with_multiple_sessions": files_with_multiple_sessions(src, tl, sess),
                                    "recording_nights": nights})
                if name == "B_audit_view" and m in SESSION_TABLE_THRESHOLDS_MIN:
                    for r in rows:
                        r["start_ts"], r["end_ts"] = iso(r["start_ts"]), iso(r["end_ts"])
                        out["sessions"].append({"group": label, "variant": variant, "threshold_min": m, **r})
        if name == "B_audit_view":
            for g in gap_context(src, tl, dt, 60, members):
                g["group"] = label
                g["ts_before"], g["ts_after"] = iso(g["ts_before"]), iso(g["ts_after"])
                out["gaps"].append(g)


def make_figures(out_dir: Path, ecdf: list[dict], sens: list[dict]) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    names = [LABELS[g] for g in PRIMARY]
    made = []

    def style(ax, title, xlabel, ylabel):
        ax.set_facecolor(SURFACE)
        ax.set_title(title, loc="left", color=INK, fontsize=11)
        ax.set_xlabel(xlabel, color=INK2, fontsize=9)
        ax.set_ylabel(ylabel, color=INK2, fontsize=9)
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.tick_params(colors=INK2, labelsize=8)
        for s in ax.spines.values():
            s.set_color(GRID)

    def label_ends(fig, ax, items, min_px=18):
        """Direct labels at line ends, nudged apart vertically (display space) so they never collide."""
        fig.canvas.draw()
        pts = sorted(((ax.transData.transform((x, y))[1], x, y, t) for x, y, t in items), key=lambda p: p[0])
        placed = []
        for py, x, y, t in pts:
            py_adj = max(py, placed[-1] + min_px) if placed else py
            placed.append(py_adj)
            dy = (py_adj - py) * 72.0 / fig.dpi
            ax.annotate(t, (x, y), xytext=(6, dy), textcoords="offset points", va="center", fontsize=8, color=INK2,
                        arrowprops={"arrowstyle": "-", "color": GRID, "linewidth": 0.6} if dy > 1 else None)

    # 1. ECDF of gaps longer than 5 s (log x), Timeline B
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150, facecolor=SURFACE)
    for name, color in zip(names, SERIES_COLORS):
        pts = [(e["x_s"], e["ecdf"]) for e in ecdf if e["group"] == name and e["timeline"] == "B_audit_view"]
        x = np.array([p[0] for p in pts], float)
        y = np.array([p[1] for p in pts], float)
        base = np.interp(5, x, y)
        sel = x >= 6
        yy = (y[sel] - base) / (1 - base)
        ax.plot(x[sel] / 60, yy, color=color, linewidth=2, label=name)
    ax.set_xscale("log")
    style(ax, "Gaps longer than 5 s: share at or below x (Timeline B)", "gap length (minutes, log scale)",
          "cumulative share of gaps > 5 s")
    for m in (30, 60, 90):
        ax.axvline(m, color=INK2, linewidth=0.8, linestyle=":")
        ax.annotate(f"{m} min", (m, 0.45), xytext=(3, 0), textcoords="offset points", fontsize=7, color=INK2,
                    rotation=90, va="bottom")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    p = out_dir / "figures" / "gap_ecdf.png"
    with open_for_write(p, "wb") as fh:
        fig.savefig(fh, format="png", facecolor=SURFACE)
    plt.close(fig)
    made.append(p.name)

    # 2/3. sessions per night and median duration vs threshold (Timeline B, plain)
    for metric, title, ylabel, fname, log_y, legend_loc in (
            ("sessions_per_recording_night", "Candidate sessions per recording night vs gap threshold (Timeline B)",
             "sessions per recording night (log scale)", "threshold_sessions.png", True, "upper right"),
            ("median_duration_h", "Median candidate-session duration vs gap threshold (Timeline B)",
             "median duration (hours)", "threshold_median_duration.png", False, "lower right")):
        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150, facecolor=SURFACE)
        ends = []
        for name, color in zip(names, SERIES_COLORS):
            rows = [r for r in sens if r["group"] == name and r["timeline"] == "B_audit_view" and r["variant"] == "plain"]
            x = [r["threshold_min"] for r in rows]
            y = [r[metric] for r in rows]
            ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=4, label=name)
            ends.append((x[-1], y[-1], name))
        ax.set_xscale("log")
        ax.set_xticks(THRESHOLDS_MIN)
        ax.set_xticklabels([str(m) for m in THRESHOLDS_MIN])
        if log_y:
            ax.set_yscale("log")
            ax.set_yticks([1, 1.5, 2, 3, 5, 10, 16])
            ax.set_yticklabels(["1", "1.5", "2", "3", "5", "10", "16"])
            ax.minorticks_off()
        else:
            ax.set_ylim(bottom=0)
        ax.set_xlim(0.8, 260)
        style(ax, title, "gap threshold (minutes, log scale)", ylabel)
        ax.legend(frameon=False, fontsize=8, loc=legend_loc)
        label_ends(fig, ax, ends)
        fig.tight_layout()
        p = out_dir / "figures" / fname
        with open_for_write(p, "wb") as fh:
            fig.savefig(fh, format="png", facecolor=SURFACE)
        plt.close(fig)
        made.append(p.name)
    return made


def main() -> int:
    t_start = time.time()
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2

    groups = subject_device_groups(manifest)
    out = {"summary": [], "dist": [], "ecdf": [], "gaps": [], "sens": [], "sessions": []}
    order = PRIMARY + sorted(k for k in groups if k not in PRIMARY)
    for key in order:
        g = groups[key]
        primary = key in PRIMARY
        label = LABELS.get(key, f"{key[0]}/{key[1]}")
        minute_res = g["families"] == {"legacy_csv_ymd_hm"}
        if minute_res:
            label += " (minute resolution)"
        loaded = load_sources(root, manifest, g["sources"])
        src = SourceData.concat([loaded[s] for s in sorted(loaded)], "+".join(sorted(loaded)), key[0], key[1])
        analyse_group(src, label, primary, out, minute_res)
        del loaded, src
        gc.collect()
        print(f"  {label:<34} done")

    out_dir = paths.p0_output_dir("temporal")
    write_csv(out_dir / "gap_summary.csv", out["summary"], columns(out["summary"], ["group", "role", "timeline"]))
    write_csv(out_dir / "gap_distribution.csv", out["dist"], ["group", "timeline", "bucket", "lo_s", "hi_s", "count", "share", "total_hours"])
    write_csv(out_dir / "gap_ecdf.csv", out["ecdf"], ["group", "timeline", "x_s", "ecdf"])
    write_csv(out_dir / "large_gaps.csv", out["gaps"], columns(out["gaps"], ["group", "ts_before", "ts_after", "gap_s"]))
    patt = [g for g in out["gaps"] if g["group"] == "User02/22482" and 1500 <= g["gap_s"] <= 43200]
    write_csv(out_dir / "user02_22482_gap_patterns.csv", patt, columns(patt, ["group", "ts_before", "ts_after", "gap_s"]))
    write_csv(out_dir / "threshold_sensitivity.csv", out["sens"], columns(out["sens"], ["group", "timeline", "variant", "threshold_min"]))
    write_csv(out_dir / "session_candidate_summary.csv", out["sessions"],
              columns(out["sessions"], ["group", "variant", "threshold_min", "candidate"]))
    figs = make_figures(out_dir, out["ecdf"], out["sens"])
    write_json(out_dir / "temporal_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"], "manifest_sha256": sha256_file(mpath),
        "raw_integrity": {k: len(v) for k, v in integrity.items()},
        "parameters": {"thresholds_min": THRESHOLDS_MIN, "session_table_thresholds_min": SESSION_TABLE_THRESHOLDS_MIN,
                       "chunk_s": 1800, "chunk_tolerance_s": 10, "bridge_max_chunks": BRIDGE_MAX_CHUNKS,
                       "large_gap_s": 60, "timeline_B": "A5 upload_copy_mask (blocks >= 10 identical rows)"},
        "figures": figs, "python": platform.python_version(), "numpy": np.__version__,
        "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"A7 done in {time.time() - t_start:.0f} s -> {out_dir.relative_to(paths.PROJECT_ROOT)}  figures={figs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
