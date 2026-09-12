"""P0 analysis A10 — User01 sensor phase / change-point audit. Read-only on raw data.

Tests whether the documented pressure-sensor replacement of User01 (2026-01-25) is a clear acquisition-
domain boundary: where the change happens, how abrupt it is, which channels change, whether it also shows
in behaviour, targets or sampling, and whether a `sensor_phase` provenance label is justified. User01 only,
on the A5/A7 audit timeline (identical upload-chunk copies excluded in memory); candidate sessions
(proposed D-015) and recording nights are analysis units. Nothing is modified, clipped, normalised,
rescaled, resampled or removed.

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/user01_phase/:
  session_pressure_summary.csv     one row per session / recording night / calendar day
  change_point_candidates.csv      strongest splits per metric and window, consensus ranking, documented boundary
  boundary_window_comparison.csv   unit-level pre/post comparison for ±1/3/7/14 units and whole periods (+ placebo)
  distribution_shift.csv           row-level Wasserstein / KS / robust differences for the same windows
  channel_pre_post_summary.csv     per-channel profile pre vs post
  saturation_summary.csv           4095 detail: channels, runs, simultaneous channels, timing around the boundary
  sampling_regime.csv              sampling interval regime per day and its change dates
  phase_assignment.csv             candidate sensor_phase labels (provenance only)
  figures/*.png                    QA figures
  user01_phase_run_meta.json
"""
from __future__ import annotations

import platform
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.duplicates import overlapping_file_pairs, row_keys, subject_device_groups, upload_copy_mask  # noqa: E402
from src.data.io_guard import open_for_write, write_csv, write_json  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.pressure_quality import boundary_summary, pressure_matrix  # noqa: E402
from src.data.provenance import SourceData, code_text, load_sources  # noqa: E402
from src.data.raw_parser import split_event  # noqa: E402
from src.data.sensor_phase import (  # noqa: E402
    CORE_METRICS, MOVES, N_CH, UPPER_BOUND, WINDOWS, assign_phase, channel_profile, compare_units, consensus,
    contiguous_units, day_index, distinct_peaks, event_rank, int_distribution_shift, night_index, rank_splits, robust_std_diff, split_scores,
    step_regime, step_vs_linear, summarize_rows, upper_bound_profile,
)
from src.data.subject_mapping import resolve_source  # noqa: E402
from src.data.target_quality import channel_states, channel_values, session_ids  # noqa: E402
from src.data.temporal import build_timeline, candidate_sessions, chunk_alignment, steps  # noqa: E402

KEY = ("User01", "unknown")
DOCUMENTED = datetime(2026, 1, 25)                  # provider note: pressure-sensor replacement
OTHER_EVENTS = {"2025-11-18": "heating season start (metadata; year inferred)", "2025-12-17": "log format change"}
PHASE_NAMES = ("s1", "s2")                          # candidate User01 sensor_phase labels (provenance only)
_EPOCH = datetime(1970, 1, 1)
RANK_METRICS = CORE_METRICS + tuple(f"p{i}_median" for i in range(1, 7)) + tuple(f"p{i}_p95" for i in range(1, 7)) + (
    "all_zero_ratio", "duration_h", "temp_median", "humid_median", "sampling_median_step_s", "sampling_share_step_2s",
    "sampling_share_step_3s", "dominant_switch_per_h", "active_set_change_per_h")
COMPARE_METRICS = RANK_METRICS + ("active_channels_median", "rows_multi_4095_ratio", "start_hour",
                                  "end_hour", "temp_iqr", "humid_iqr", "movement_label_share",
                                  *(f"move_{m}_share" for m in MOVES), *(f"p{i}_zero_ratio" for i in range(1, 7)),
                                  *(f"p{i}_4095_ratio" for i in range(1, 7)))
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"


def sec(d: datetime) -> int:
    return int((d - _EPOCH).total_seconds())


def iso(s) -> str:
    return (_EPOCH + timedelta(seconds=int(s))).isoformat(sep=" ")


def date_of(s) -> str:
    return (_EPOCH + timedelta(seconds=int(s))).date().isoformat()


def columns(rows: list[dict], first: list[str]) -> list[str]:
    cols = list(first)
    for r in rows:
        cols += [k for k in r if k not in cols]
    return cols


def movement_codes(src: SourceData, rows: np.ndarray) -> np.ndarray:
    """Firmware movement label per row: 0 none, 1..5 = MOVES (up, down, left, right, absent)."""
    codes = src.event_code[rows]
    uniq, inv = np.unique(codes, return_inverse=True)
    lut = np.zeros(uniq.size, np.int8)
    for i, c in enumerate(uniq):
        mv = split_event(code_text(int(c)) or "")[0]
        lut[i] = MOVES.index(mv) + 1 if mv in MOVES else 0
    return lut[inv]


def main() -> int:
    t_start = time.time()
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2
    groups = subject_device_groups(manifest, eligible_only=True)          # D-017: User06 never loaded
    g = groups[KEY]
    loaded = load_sources(root, manifest, g["sources"])
    src = SourceData.concat([loaded[s] for s in sorted(loaded)], "+".join(sorted(loaded)), *KEY)
    keys = row_keys(src)
    tl = build_timeline(src, "B", upload_copy_mask(src, keys, overlapping_file_pairs(src, keys)))
    rows, ts = tl.rows, tl.ts
    P, pres = pressure_matrix(src, rows)
    temp, t_miss = channel_values(src, rows, "temp")
    humid, h_miss = channel_values(src, rows, "humid")
    t_ok, h_ok = channel_states(temp, "temp", t_miss)["valid"], channel_states(humid, "humid", h_miss)["valid"]
    move = movement_codes(src, rows)
    source_of_file = np.array([resolve_source(f).source_id for f in src.files])
    src_id = source_of_file[src.file_idx[rows]]
    file_of_row = src.file_idx[rows]

    # ---- documented boundary: the recording gap that contains midday of the documented date -------------
    i_after = int(np.searchsorted(ts, sec(DOCUMENTED + timedelta(hours=12))))
    last_before, first_after = int(ts[i_after - 1]), int(ts[i_after])
    phase = assign_phase(ts, [(last_before, first_after)], PHASE_NAMES)
    pre_rows, post_rows = phase == PHASE_NAMES[0], phase == PHASE_NAMES[1]

    # ---- units ----------------------------------------------------------------------------------------
    ca = chunk_alignment(steps(tl))
    sessions = candidate_sessions(tl, 1800, ca["aligned"] & (ca["n_chunks"] <= 3))     # proposed D-015; label only
    unit_spans = {"session": [(k, a, b) for k, (a, b) in enumerate(sessions)],
                  "night": contiguous_units(night_index(ts)), "day": contiguous_units(day_index(ts))}
    units: dict[str, list[dict]] = {}
    for utype, spans in unit_spans.items():
        lst = []
        for j, (lab, a, b) in enumerate(spans):
            sl = slice(a, b + 1)
            ph = set(phase[sl].tolist())
            u = {"unit_type": utype, "unit": j,
                 "label": date_of(ts[a]) if utype != "night" else date_of(lab * 86400 + 43200),
                 "sensor_phase": ph.pop() if len(ph) == 1 else "mixed",
                 "source_phase": "+".join(sorted(set(src_id[sl].tolist()))),
                 "first_file": src.files[int(file_of_row[a])],
                 "gap_before_h": round((int(ts[a]) - lst[-1]["end_ts"]) / 3600, 2) if lst else None,
                 "first": a, "last": b}
            u.update(summarize_rows(ts[sl], P[sl], pres[sl], temp[sl], humid[sl], t_ok[sl], h_ok[sl], move[sl]))
            lst.append(u)
        units[utype] = lst
    out_units = [{k: (iso(v) if k in ("start_ts", "end_ts") else v) for k, v in u.items() if k not in ("first", "last")}
                 for utype in units for u in units[utype]]

    def split_index(utype: str) -> int:
        return next(j for j, u in enumerate(units[utype]) if u["start_ts"] >= first_after)

    # ---- change-point ranking -------------------------------------------------------------------------
    cp_rows = []
    regimes = [(u["label"], u.get("sampling_median_step_s")) for u in units["day"]]
    regime_changes = [regimes[i][0] for i in range(1, len(regimes)) if regimes[i][1] != regimes[i - 1][1]]
    other_events: set[str] = set(OTHER_EVENTS) | set(regime_changes)   # documented events and sampling-regime changes

    def split_row(utype, us, kind, metric, w, rank, k, kb, score, **extra):
        return {"unit_type": utype, "kind": kind, "metric": metric, "window": w, "rank": rank,
                "split_first_unit_after": us[k]["label"], "split_start_after": iso(us[k]["start_ts"]),
                "gap_h": round((us[k]["start_ts"] - us[k - 1]["end_ts"]) / 3600, 2), "score": score,
                "is_documented_boundary": bool(k == kb), "units_from_documented": int(k - kb), **extra}

    for utype in ("session", "night", "day"):
        us = units[utype]
        series = {m: np.array([np.nan if u.get(m) is None else u[m] for u in us], float) for m in RANK_METRICS}
        ranks = rank_splits(series)
        kb = split_index(utype)
        for w in WINDOWS:
            # consensus over the core metrics: mean |d_w| rank, one candidate per event (suppression radius w)
            cons = consensus(ranks, CORE_METRICS, w)
            score = -cons["mean_rank"]
            score[0] = np.nan
            peaks = distinct_peaks(score, w, top=10)
            for r, k in enumerate(peaks, 1):
                cp_rows.append(split_row(utype, us, "consensus_core", "+".join(CORE_METRICS), w, r, k, kb,
                                         round(float(cons["mean_rank"][k]), 2), top3_metrics=int(cons["top_count"][k])))
            near = min(w, 2)                        # a peak this close to the documented split is the same event
            cp_rows.append(split_row(utype, us, "documented_boundary_consensus", "+".join(CORE_METRICS), w,
                                     event_rank(peaks, kb, near), kb, kb, round(float(cons["mean_rank"][kb]), 2),
                                     top3_metrics=int(cons["top_count"][kb])))
            if utype == "night" and w in (3, 7):
                other_events.update(us[k]["label"] for k in peaks[:3] if abs(k - kb) > w)
            for m, x in series.items():
                d = split_scores(x, w)
                peaks = distinct_peaks(np.abs(d), w, top=5)
                for r, k in enumerate(peaks, 1):
                    cp_rows.append(split_row(utype, us, "per_metric_top", m, w, r, k, kb, round(float(d[k]), 3),
                                             **(step_vs_linear(x, k) if w == 7 else {})))
                far = np.abs(d.copy())
                far[max(0, kb - w):kb + w + 1] = np.nan
                k_far = int(np.nanargmax(far)) if np.isfinite(far).any() else None
                cp_rows.append(split_row(utype, us, "documented_boundary_metric", m, w, event_rank(peaks, kb, near), kb, kb,
                                         None if not np.isfinite(d[kb]) else round(float(d[kb]), 3),
                                         raw_rank=int(ranks[(m, w)][kb]),
                                         max_abs_score_elsewhere=None if k_far is None else round(float(far[k_far]), 3),
                                         elsewhere_split=None if k_far is None else us[k_far]["label"],
                                         **(step_vs_linear(x, kb) if w == 7 else {})))

    # ---- windows around the boundary ------------------------------------------------------------------
    win_rows, dist_rows = [], []
    clock = (ts % 86400) / 3600.0
    core_night = (clock >= 0) & (clock < 5)
    v_all = np.nan_to_num(P)
    full = pres.all(axis=1)
    loaded_row = full & (v_all > 0).any(axis=1)

    def row_mask(us: list[dict]) -> np.ndarray:
        m = np.zeros(ts.size, bool)
        for u in us:
            m[u["first"]:u["last"] + 1] = True
        return m

    def dist(tag: str, utype: str, a_m: np.ndarray, b_m: np.ndarray) -> None:
        ma, mb = a_m & loaded_row, b_m & loaded_row
        variables = [("pressure_sum", v_all.sum(axis=1)), ("active_channels", (v_all > 0).sum(axis=1))]
        variables += [(f"p{i + 1}", v_all[:, i]) for i in range(N_CH)]
        for name, x in variables:
            a, b = x[ma], x[mb]
            sh = int_distribution_shift(a, b)
            iqr = max((float(np.percentile(x_, 75) - np.percentile(x_, 25)) for x_ in (a, b) if x_.size), default=0.0)
            dist_rows.append({"window": tag, "unit_type": utype, "variable": name, "rows_before": int(a.size), "rows_after": int(b.size),
                              "median_before": float(np.median(a)) if a.size else None, "median_after": float(np.median(b)) if b.size else None,
                              "p95_before": float(np.percentile(a, 95)) if a.size else None,
                              "p95_after": float(np.percentile(b, 95)) if b.size else None, **sh,
                              "wasserstein_over_max_iqr": round(sh["wasserstein"] / iqr, 3) if sh["wasserstein"] is not None and iqr > 0 else None,
                              "robust_std_diff_rows": robust_std_diff(a, b)})
        a, b = v_all.sum(axis=1)[ma & core_night], v_all.sum(axis=1)[mb & core_night]
        dist_rows.append({"window": tag, "unit_type": utype, "variable": "pressure_sum_00_05h", "rows_before": int(a.size),
                          "rows_after": int(b.size), "median_before": float(np.median(a)) if a.size else None,
                          "median_after": float(np.median(b)) if b.size else None,
                          "p95_before": float(np.percentile(a, 95)) if a.size else None,
                          "p95_after": float(np.percentile(b, 95)) if b.size else None, **int_distribution_shift(a, b),
                          "robust_std_diff_rows": robust_std_diff(a, b)})

    for utype in ("session", "night"):
        us = units[utype]
        kb = split_index(utype)
        pre_u, post_u = us[:kb], us[kb:]
        windows = [(f"pm{n}", pre_u[-n:], post_u[:n]) for n in WINDOWS] + [("all", pre_u, post_u)]
        windows += [("placebo_pre_14v14", pre_u[-28:-14], pre_u[-14:]), ("placebo_post_14v14", post_u[:14], post_u[14:28])]
        for tag, a, b in windows:
            for r in compare_units(a, b, COMPARE_METRICS):
                win_rows.append({"window": tag, "unit_type": utype,
                                 "first_unit_before": a[0]["label"] if a else None, "last_unit_after": b[-1]["label"] if b else None, **r})
            if utype == "night":
                dist(tag, utype, row_mask(a), row_mask(b))
    # the same ±7-night comparison at the other candidate events (documented, sampling, data-driven), for scale
    nights_u = units["night"]
    for ev in sorted(other_events):
        k = next((j for j, u in enumerate(nights_u) if u["label"] >= ev), None)
        if k is None or k < 3 or abs(k - split_index("night")) <= 7:
            continue
        a, b = nights_u[max(0, k - 7):k], nights_u[k:k + 7]
        tag = f"event_{ev}_pm7"
        for r in compare_units(a, b, COMPARE_METRICS):
            win_rows.append({"window": tag, "unit_type": "night", "first_unit_before": a[0]["label"],
                             "last_unit_after": b[-1]["label"], **r})
        dist(tag, "night", row_mask(a), row_mask(b))

    # ---- channel profiles -----------------------------------------------------------------------------
    ch_rows = []
    nights = units["night"]
    kbn = split_index("night")
    prof_sets = {"all": (pre_rows, post_rows), "pm14_nights": (row_mask(nights[kbn - 14:kbn]), row_mask(nights[kbn:kbn + 14]))}
    for tag, (a_m, b_m) in prof_sets.items():
        pa = {r["channel"]: r for r in channel_profile(P[a_m], pres[a_m])}
        pb = {r["channel"]: r for r in channel_profile(P[b_m], pres[b_m])}
        for ch in pa:
            row = {"window": tag, "channel": ch}
            for k in pa[ch]:
                if k != "channel":
                    row[f"{k}_before"], row[f"{k}_after"] = pa[ch][k], pb[ch][k]
            for k in ("median_when_active", "p95_when_active", "p95", "active_ratio", "mass_share"):
                x0, x1 = pa[ch][k], pb[ch][k]
                row[f"{k}_ratio"] = round(x1 / x0, 3) if x0 else None
            ch_rows.append(row)

    # ---- upper bound (4095) ---------------------------------------------------------------------------
    sat_rows = []
    sid = session_ids(ts.size, sessions)
    for name, m in (("before", pre_rows), ("after", post_rows)):
        sess_total = int(np.unique(sid[m]).size)
        for ch in range(N_CH):
            b = boundary_summary(ts[m], P[m, ch], pres[m, ch], float(UPPER_BOUND), sid[m])
            sat_rows.append({"kind": "channel", "period": name, "channel": f"p{ch + 1}", "count": b["count"],
                             "ratio_of_rows": b["ratio"], "runs": b["runs"], "longest_run_rows": b["longest_run_rows"],
                             "longest_run_s": b["longest_run_s"], "sessions_affected": b["affected_sessions"],
                             "sessions_total": sess_total, "dates_affected": b["affected_dates"]})
        sat_rows.append({"kind": "simultaneous", "period": name, **upper_bound_profile(P[m], pres[m])})
    any_b = (v_all == UPPER_BOUND).any(axis=1)
    pre_b = np.flatnonzero(any_b & pre_rows)
    post_b = np.flatnonzero(any_b & post_rows)
    sat_rows.append({"kind": "timing", "period": "before", "detail": "last row with a 4095 channel",
                     "ts": iso(ts[pre_b[-1]]) if pre_b.size else None,
                     "hours_to_boundary": round((last_before - ts[pre_b[-1]]) / 3600, 2) if pre_b.size else None})
    sat_rows.append({"kind": "timing", "period": "after", "detail": "first row with a 4095 channel",
                     "ts": iso(ts[post_b[0]]) if post_b.size else None,
                     "hours_to_boundary": round((ts[post_b[0]] - first_after) / 3600, 2) if post_b.size else None})
    for i in post_b:
        chans = [f"p{c + 1}" for c in range(N_CH) if v_all[i, c] == UPPER_BOUND]
        sat_rows.append({"kind": "post_event", "period": "after", "ts": iso(ts[i]), "channel": "+".join(chans),
                         "detail": f"night {date_of(ts[i] - 43200)}; active channels {int((v_all[i] > 0).sum())}"})
    for h in range(-36, 37):
        t0 = (last_before // 3600 + h) * 3600 if h <= 0 else (first_after // 3600 + h - 1) * 3600
        m = (ts >= t0) & (ts < t0 + 3600)
        if m.any():
            sat_rows.append({"kind": "hourly_near_boundary", "period": phase[np.flatnonzero(m)[0]], "ts": iso(t0),
                             "count": int(m.sum()), "ratio_of_rows": round(float(any_b[m].mean()), 4)})
    for name, ph_name in (("before", PHASE_NAMES[0]), ("after", PHASE_NAMES[1])):
        for key in ["rows_4095_ratio"] + [f"p{c + 1}_4095_ratio" for c in range(N_CH)]:
            sat_rows.append({"kind": "session_ratio_distribution", "period": name, "channel": key,
                             **_session_ratio(units["session"], key, ph_name)})
    # ---- sampling regime ------------------------------------------------------------------------------
    samp_rows = []
    prev = None
    for u in units["day"]:
        reg = u.get("sampling_median_step_s")
        label = None if reg is None else f"{reg:g}s"
        samp_rows.append({"kind": "day", "date": u["label"], "source_phase": u["source_phase"], "sensor_phase": u["sensor_phase"],
                          **{k: u.get(k) for k in u if k.startswith("sampling_")}, "regime": label,
                          "regime_changed": bool(prev is not None and label != prev)})
        prev = label
    for name, m in (("source:" + s, src_id == s) for s in sorted(set(src_id.tolist()))):
        samp_rows.append({"kind": "period", "date": name, **{f"sampling_{k}": v for k, v in _regime(ts, m).items()}})
    for name, m in (("sensor:before", pre_rows), ("sensor:after", post_rows)):
        samp_rows.append({"kind": "period", "date": name, **{f"sampling_{k}": v for k, v in _regime(ts, m).items()}})

    # ---- phase assignment (candidate provenance label) ------------------------------------------------
    ph_rows = []
    for name in PHASE_NAMES:
        m = phase == name
        idx = np.flatnonzero(m)
        ph_rows.append({"sensor_phase": name, "rows": int(m.sum()), "first_ts": iso(ts[idx[0]]), "last_ts": iso(ts[idx[-1]]),
                        "sessions": int(np.unique(sid[m]).size), "nights": int(np.unique(night_index(ts[m])).size),
                        "source_phases": "+".join(sorted(set(src_id[m].tolist()))),
                        "file_at_edge": src.files[int(file_of_row[idx[-1] if name == PHASE_NAMES[0] else idx[0]])]})
    ph_rows.append({"sensor_phase": "(boundary interval)", "rows": int((phase == "").sum()), "first_ts": iso(last_before),
                    "last_ts": iso(first_after), "detail_gap_h": round((first_after - last_before) / 3600, 2)})

    od = paths.p0_output_dir("user01_phase")
    write_csv(od / "session_pressure_summary.csv", out_units,
              columns(out_units, ["unit_type", "unit", "label", "sensor_phase", "source_phase", "first_file", "gap_before_h"]))
    write_csv(od / "change_point_candidates.csv", cp_rows, columns(cp_rows, ["unit_type", "kind", "metric", "window", "rank"]))
    write_csv(od / "boundary_window_comparison.csv", win_rows, columns(win_rows, ["window", "unit_type", "metric"]))
    write_csv(od / "distribution_shift.csv", dist_rows, columns(dist_rows, ["window", "unit_type", "variable"]))
    write_csv(od / "channel_pre_post_summary.csv", ch_rows, columns(ch_rows, ["window", "channel"]))
    write_csv(od / "saturation_summary.csv", sat_rows, columns(sat_rows, ["kind", "period", "channel", "ts", "detail"]))
    write_csv(od / "sampling_regime.csv", samp_rows, columns(samp_rows, ["kind", "date", "source_phase", "sensor_phase", "regime"]))
    write_csv(od / "phase_assignment.csv", ph_rows, columns(ph_rows, ["sensor_phase"]))
    figs = make_figures(od, units, last_before, first_after, P, pres, prof_sets["pm14_nights"])
    write_json(od / "user01_phase_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"], "manifest_sha256": sha256_file(mpath),
        "raw_integrity": {k: len(v) for k, v in integrity.items()}, "sources": sorted(loaded),
        "rows_audit_view": int(ts.size), "documented_boundary_date": DOCUMENTED.date().isoformat(),
        "boundary_interval": [iso(last_before), iso(first_after)], "phase_names": list(PHASE_NAMES),
        "units": {k: len(v) for k, v in units.items()}, "windows": list(WINDOWS), "core_metrics": list(CORE_METRICS),
        "figures": figs, "python": platform.python_version(), "numpy": np.__version__,
        "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"A10 done in {time.time() - t_start:.0f} s -> {od.relative_to(paths.PROJECT_ROOT)}  figures={figs}")
    return 0


def _regime(ts: np.ndarray, m: np.ndarray) -> dict:
    """Sampling regime over the rows of a (possibly non-contiguous) mask, using steps inside it only."""
    idx = np.flatnonzero(m)
    parts = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    dts = np.concatenate([np.diff(ts[p]) for p in parts if p.size > 1] or [np.array([], np.int64)])
    return step_regime(np.concatenate([[0], np.cumsum(dts)]))      # step_regime reads a timestamp series


def _session_ratio(sessions: list[dict], key: str, phase_name: str) -> dict:
    x = np.array([u[key] for u in sessions if u["sensor_phase"] == phase_name and u.get(key) is not None], float)
    if x.size == 0:
        return {"sessions": 0}
    return {"sessions": int(x.size), "sessions_with_4095": int((x > 0).sum()), "session_ratio_median": round(float(np.median(x)), 5),
            "session_ratio_p90": round(float(np.percentile(x, 90)), 5), "session_ratio_max": round(float(x.max()), 5)}


def make_figures(od: Path, units: dict, last_before: int, first_after: int, P: np.ndarray, pres: np.ndarray,
                 local: tuple[np.ndarray, np.ndarray]) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    made = []
    nights = units["night"]
    x = np.array([datetime.fromisoformat(u["label"]) for u in nights])
    bdate = _EPOCH + timedelta(seconds=(last_before + first_after) // 2)

    def style(ax, title, ylabel):
        ax.set_facecolor(SURFACE)
        ax.set_title(title, loc="left", color=INK, fontsize=10)
        ax.set_ylabel(ylabel, color=INK2, fontsize=8)
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.tick_params(colors=INK2, labelsize=7)
        for s in ax.spines.values():
            s.set_color(GRID)

    def segments(vals):
        """Break the line where consecutive nights are more than 2 days apart."""
        seg, cur = [], [0]
        for i in range(1, len(x)):
            if (x[i] - x[i - 1]).days > 2:
                seg.append(cur)
                cur = []
            cur.append(i)
        seg.append(cur)
        return seg

    panels = [("Pressure sum on loaded rows, per recording night", "pressure sum",
               [("pressure_sum_median", "median", SERIES_COLORS[0]), ("pressure_sum_p95", "p95", SERIES_COLORS[1])], 1),
              ("Rows with at least one channel at 4095, per night", "% of rows", [("rows_4095_ratio", None, SERIES_COLORS[0])], 100),
              ("Mean number of active channels on loaded rows, per night", "channels", [("active_channels_mean", None, SERIES_COLORS[0])], 1),
              ("Median sampling step, per night", "seconds", [("sampling_median_step_s", None, SERIES_COLORS[0])], 1)]
    fig, axes = plt.subplots(len(panels), 1, figsize=(9, 9), dpi=150, sharex=True, facecolor=SURFACE)
    for ax, (title, ylab, series, scale) in zip(axes, panels):
        for key, lab, color in series:
            y = np.array([np.nan if u.get(key) is None else u[key] * scale for u in nights], float)
            for s in segments(y):
                ax.plot(x[s], y[s], color=color, linewidth=1.5, marker="o", markersize=2.5,
                        label=lab if (lab and s == segments(y)[0]) else None)
        style(ax, title, ylab)
        ax.axvline(bdate, color=INK, linewidth=1.0, linestyle="--")
        for d in OTHER_EVENTS:
            ax.axvline(datetime.fromisoformat(d), color=INK2, linewidth=0.7, linestyle=":")
        if any(lab for _, lab, _ in series):
            ax.legend(frameon=False, fontsize=7, loc="upper left", bbox_to_anchor=(0.14, 1.0))   # empty Sep-Oct span
    axes[0].annotate("2026-01-25 documented sensor change", (bdate, 1), xycoords=("data", "axes fraction"),
                     xytext=(4, -10), textcoords="offset points", fontsize=7, color=INK)
    for d, t in OTHER_EVENTS.items():
        axes[0].annotate(t.split(" (")[0], (datetime.fromisoformat(d), 1), xycoords=("data", "axes fraction"),
                         xytext=(-4, -10), textcoords="offset points", fontsize=6, color=INK2, ha="right")
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.tight_layout()
    p = od / "figures" / "user01_night_timeseries.png"
    with open_for_write(p, "wb") as fh:
        fig.savefig(fh, format="png", facecolor=SURFACE)
    plt.close(fig)
    made.append(p.name)

    # channel distributions, ±14 nights around the boundary: ECDF of values when the channel is active
    a_m, b_m = local
    fig, axes = plt.subplots(2, 3, figsize=(9, 5.5), dpi=150, sharex=True, sharey=True, facecolor=SURFACE)
    v = np.nan_to_num(P)
    full = pres.all(axis=1)
    loaded = full & (v > 0).any(axis=1)
    for c, ax in enumerate(axes.ravel()):
        for m, lab, color in ((a_m, "14 nights before", SERIES_COLORS[0]), (b_m, "14 nights after", SERIES_COLORS[1])):
            col = v[m & loaded, c]
            act = np.sort(col[col > 0])
            if act.size:
                ax.plot(act, np.arange(1, act.size + 1) / act.size, color=color, linewidth=1.8,
                        label=f"{lab} (active {100 * act.size / col.size:.0f} %)")
        style(ax, f"P{c + 1}", "cumulative share" if c % 3 == 0 else "")
        ax.axvline(UPPER_BOUND, color=INK2, linewidth=0.7, linestyle=":")
        ax.legend(frameon=False, fontsize=6, loc="lower right")
        if c >= 3:
            ax.set_xlabel("value when active", color=INK2, fontsize=8)
    fig.suptitle("User01 channel values when active: 14 nights before vs after 2026-01-25 (dotted line: 4095)",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout()
    p = od / "figures" / "user01_channel_pre_post.png"
    with open_for_write(p, "wb") as fh:
        fig.savefig(fh, format="png", facecolor=SURFACE)
    plt.close(fig)
    made.append(p.name)
    return made


if __name__ == "__main__":
    raise SystemExit(main())
