"""P0 analysis A9b — User02 / 22482 P1 channel anomaly audit. Read-only on raw data.

A9 saw 22482's P1 nearly stop responding around 2026-08-20. This audit re-derives the change point without
assuming that date, measures how abrupt and lasting it is, which channels are involved, whether the other mat of
the same subject (22480, a control for concurrent environmental change only) or targets shift at the same time,
how it relates to schema/firmware boundaries and occupancy, and how much data it affects. Nothing is removed,
corrected, imputed, clipped or normalised; a channel-quality phase is a provenance label only.

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/user02_channel_anomaly/:
  unit_channel_summary.csv       22482 and 22480 per night / session / day: channel, sum, occupancy, T/H, sampling, events
  change_point_candidates.csv    distinct candidates per metric and window, P1 consensus, whole-mat consensus
  boundary_window_comparison.csv ±1/3/7 nights and whole periods, recovery, 22480 control at the same split
  channel_shift_classification.csv
  hourly_onset.csv               hourly P1 series around the boundary and the best single split
  schema_firmware_timeline.csv   device column, container, sampling regime, control/event tokens, files
  impact_summary.csv             affected rows / nights / hours and User02 coverage with and without the slice
  figures/channel_anomaly_timeseries.png
  user02_channel_anomaly_run_meta.json
"""
from __future__ import annotations

import platform
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.channel_anomaly import best_split, channel_unit_stats, classify_shift, recovery  # noqa: E402
from src.data.coverage import (  # noqa: E402
    MIN_HOURS, MIN_NIGHTS, MIN_SPLIT_NIGHTS, chronological_capacity, minutes,
)
from src.data.duplicates import overlapping_file_pairs, row_keys, subject_device_groups, upload_copy_mask  # noqa: E402
from src.data.io_guard import open_for_write, write_csv, write_json  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.pressure_quality import pressure_matrix  # noqa: E402
from src.data.provenance import SourceData, code_text, load_sources  # noqa: E402
from src.data.raw_parser import split_event  # noqa: E402
from src.data.subject_mapping import channel_quality_spec  # noqa: E402
from src.data.sensor_phase import (  # noqa: E402
    assign_phase, cliffs_delta, compare_units, consensus, contiguous_units, distinct_peaks, night_index, rank_splits,
    split_scores, step_regime, step_vs_linear,
)
from src.data.target_quality import channel_states, channel_values  # noqa: E402
from src.data.temporal import build_timeline, candidate_sessions, chunk_alignment, steps  # noqa: E402

DEV, CONTROL = ("User02", "22482"), ("User02", "22480")
A9_MARKER = datetime(2026, 8, 20)                       # A9 observation, used only as a reference label
WINDOWS = (1, 3, 7)
P1_METRICS = ("p1_active_ratio", "p1_nz_median", "p1_p95", "p1_mass_share", "p1_dominant_ratio")
MAT_METRICS = ("pressure_sum_median", "active_channels_mean", "all_zero_ratio")
CH_METRICS = tuple(f"p{i}_{m}" for i in range(1, 7) for m in ("active_ratio", "nz_median", "nz_iqr", "p95",
                                                              "mass_share", "dominant_ratio", "zero_ratio"))
CONTEXT = ("pressure_sum_median", "pressure_sum_p95", "pressure_sum_excl_p1_median", "active_channels_mean",
           "active_channels_excl_p1_mean",
           "all_zero_ratio", "duration_h",
           "start_hour", "end_hour", "temp_median", "humid_median", "sampling_median_step_s",
           "device_column_share", "control_event_share", "move_absent_share")
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID, SURFACE, MUTED = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb", "#b8b6ae"
_EPOCH = datetime(1970, 1, 1)


def iso(s) -> str:
    return (_EPOCH + timedelta(seconds=int(s))).isoformat(sep=" ")


def date_of(s) -> str:
    return (_EPOCH + timedelta(seconds=int(s))).date().isoformat()


def columns(rows: list[dict], first: list[str]) -> list[str]:
    cols = list(first)
    for r in rows:
        cols += [k for k in r if k not in cols]
    return cols


def timeline_arrays(src: SourceData) -> dict:
    keys = row_keys(src)
    tl = build_timeline(src, "B", upload_copy_mask(src, keys, overlapping_file_pairs(src, keys)))
    rows = tl.rows
    P, pres = pressure_matrix(src, rows)
    temp, tm = channel_values(src, rows, "temp")
    humid, hm = channel_values(src, rows, "humid")
    codes = src.event_code[rows]
    uniq, inv = np.unique(codes, return_inverse=True)
    move, control = [], []
    for c in uniq:
        mv, ctl = split_event(code_text(int(c)) or "")
        move.append(mv or "")
        control.append(" ".join(t.split(":")[0] for t in (ctl or "").split()))
    ca = chunk_alignment(steps(tl))
    return {"tl": tl, "ts": tl.ts, "P": P, "pres": pres, "temp": temp, "humid": humid,
            "t_ok": channel_states(temp, "temp", tm)["valid"], "h_ok": channel_states(humid, "humid", hm)["valid"],
            "move": np.array(move, dtype=object)[inv], "control": np.array(control, dtype=object)[inv],
            "schema": src.schema_code[rows], "container": np.where(src.chunk_idx[rows] >= 0, "quasi_json", "plain"),
            "file": np.array(src.files, dtype=object)[src.file_idx[rows]],
            "sessions": candidate_sessions(tl, 1800, ca["aligned"] & (ca["n_chunks"] <= 3))}


def units_of(a: dict) -> dict[str, list[dict]]:
    ts = a["ts"]
    spans = {"night": contiguous_units(night_index(ts)), "day": contiguous_units(ts // 86400),
             "session": [(k, s, e) for k, (s, e) in enumerate(a["sessions"])]}
    out = {}
    for utype, sp in spans.items():
        lst = []
        for j, (lab, s, e) in enumerate(sp):
            sl = slice(s, e + 1)
            u = {"unit_type": utype, "unit": j, "label": date_of(lab * 86400 + 43200) if utype == "night" else date_of(ts[s]),
                 "first": s, "last": e, "start_ts": int(ts[s]), "end_ts": int(ts[e]),
                 "duration_h": round((int(ts[e]) - int(ts[s])) / 3600, 3),
                 "start_hour": round((int(ts[s]) % 86400) / 3600, 2), "end_hour": round((int(ts[e]) % 86400) / 3600, 2),
                 "first_file": a["file"][s].split("/")[-1]}
            u.update(channel_unit_stats(a["P"][sl], a["pres"][sl]))
            for name in ("temp", "humid"):
                ok = a[f"{name[0]}_ok"][sl]
                u[f"{name}_median"] = float(np.median(a[name][sl][ok])) if ok.any() else None
            reg = step_regime(ts[sl])
            u["sampling_median_step_s"] = reg.get("median_step_s")
            u["device_column_share"] = round(float((a["schema"][sl] == 1).mean()), 4)
            u["control_event_share"] = round(float((a["control"][sl] != "").mean()), 5)
            u["move_absent_share"] = round(float((a["move"][sl] == "absent").mean()), 5)
            if u.get("active_channels_mean") is not None:          # the mean count is the sum of per-channel shares
                u["active_channels_excl_p1_mean"] = round(u["active_channels_mean"] - u["p1_active_ratio"], 4)
                v = np.nan_to_num(a["P"][sl])
                ld = a["pres"][sl].all(axis=1) & (v > 0).any(axis=1)
                u["pressure_sum_excl_p1_median"] = float(np.median(v[ld][:, 1:].sum(axis=1)))
            lst.append(u)
        out[utype] = lst
    return out


def series(us: list[dict], m: str) -> np.ndarray:
    return np.array([np.nan if u.get(m) is None else u[m] for u in us], float)


def main() -> int:
    t_start = time.time()
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2
    groups = subject_device_groups(manifest, eligible_only=True)
    A, U = {}, {}
    for key in (DEV, CONTROL):
        loaded = load_sources(root, manifest, groups[key]["sources"])
        src = SourceData.concat([loaded[s] for s in sorted(loaded)], "+".join(sorted(loaded)), *key)
        A[key] = timeline_arrays(src)
        U[key] = units_of(A[key])
    a82, a80 = A[DEV], A[CONTROL]
    nights, nights80 = U[DEV]["night"], U[CONTROL]["night"]

    # ---- change points without assuming the A9 date --------------------------------------------------------
    cp = []
    strongest: dict[str, int] = {}
    for utype in ("night", "session", "day"):
        us = U[DEV][utype]
        ser = {m: series(us, m) for m in P1_METRICS + MAT_METRICS + CH_METRICS}
        ranks = rank_splits(ser, WINDOWS)
        for w in WINDOWS:
            for name, metrics in (("consensus_p1", P1_METRICS), ("consensus_whole_mat", MAT_METRICS)):
                cons = consensus(ranks, metrics, w)
                score = -cons["mean_rank"]
                score[0] = np.nan
                peaks = distinct_peaks(score, w, top=5)
                if name == "consensus_p1" and w == 3:
                    strongest[utype] = peaks[0]
                for r, k in enumerate(peaks, 1):
                    cp.append({"unit_type": utype, "kind": name, "metric": "+".join(metrics), "window": w, "rank": r,
                               "split_first_unit_after": us[k]["label"], "split_start_after": iso(us[k]["start_ts"]),
                               "gap_h": round((us[k]["start_ts"] - us[k - 1]["end_ts"]) / 3600, 2),
                               "score_mean_rank": round(float(cons["mean_rank"][k]), 2), "top3_metrics": int(cons["top_count"][k])})
            for m in P1_METRICS + MAT_METRICS + tuple(f"p{i}_{x}" for i in range(2, 7) for x in ("active_ratio", "nz_median")):
                d = split_scores(ser[m], w)
                for r, k in enumerate(distinct_peaks(np.abs(d), w, top=3), 1):
                    cp.append({"unit_type": utype, "kind": "per_metric_top", "metric": m, "window": w, "rank": r,
                               "split_first_unit_after": us[k]["label"], "split_start_after": iso(us[k]["start_ts"]),
                               "gap_h": round((us[k]["start_ts"] - us[k - 1]["end_ts"]) / 3600, 2),
                               "score_d": round(float(d[k]), 3), **(step_vs_linear(ser[m], k, half=10) if w == 3 else {})})

    kb = strongest["night"]                                  # strongest P1 split between recording nights
    b_label = nights[kb]["label"]
    last_normal_ts, first_shift_ts = nights[kb - 1]["end_ts"], nights[kb]["start_ts"]

    # ---- hourly onset around the boundary ------------------------------------------------------------------
    ts = a82["ts"]
    lo, hi = nights[max(0, kb - 2)]["start_ts"], nights[min(len(nights) - 1, kb + 1)]["end_ts"]
    hours = np.arange(lo // 3600, hi // 3600 + 1)
    hr_rows, hr_val = [], []
    for h in hours:
        m = (ts >= h * 3600) & (ts < (h + 1) * 3600)
        if m.sum() < 60:
            continue
        st = channel_unit_stats(a82["P"][m], a82["pres"][m])
        hr_rows.append({"hour": iso(h * 3600), "rows": int(m.sum()), "p1_active_ratio": st.get("p1_active_ratio"),
                        "p1_nz_median": st.get("p1_nz_median"), "p1_p95": st.get("p1_p95"), "p6_active_ratio": st.get("p6_active_ratio"),
                        "pressure_sum_median": st.get("pressure_sum_median"), "active_channels_mean": st.get("active_channels_mean")})
        hr_val.append(st.get("p1_p95", np.nan))
    bs = best_split(np.array(hr_val, float))
    for i, r in enumerate(hr_rows):
        r["segment"] = None if bs["k"] is None else ("before_split" if i < bs["k"] else "after_split")
    hourly_split = hr_rows[bs["k"]]["hour"] if bs["k"] is not None else None

    # ---- windows, recovery, channel classification, control ------------------------------------------------
    win = []
    pre_all, post_all = nights[:kb], nights[kb:]
    metrics_all = tuple(dict.fromkeys(P1_METRICS + CH_METRICS + CONTEXT))
    for tag, a, b in [(f"pm{n}", pre_all[-n:], post_all[:n]) for n in WINDOWS] + [("all", pre_all, post_all)]:
        for r in compare_units(a, b, metrics_all):
            win.append({"device": "22482", "window": tag, **r})
    k80 = next(j for j, u in enumerate(nights80) if u["label"] >= b_label)
    for tag, n in [(f"pm{n}", n) for n in WINDOWS] + [("all", None)]:
        a, b = (nights80[:k80], nights80[k80:]) if n is None else (nights80[max(0, k80 - n):k80], nights80[k80:k80 + n])
        for r in compare_units(a, b, tuple(f"p{i}_active_ratio" for i in range(1, 7)) + CONTEXT):
            win.append({"device": "22480 (control)", "window": tag, **r})
    rec = []
    for m in ("p1_active_ratio", "p1_nz_median", "p1_p95", "p6_active_ratio", "p6_nz_median"):
        x = series(nights, m)
        r = recovery(x[kb - 7:kb], x[kb:kb + 7], x[-7:])
        rec.append({"metric": m, "last_night": nights[-1]["label"], **r,
                    **step_vs_linear(x, kb, half=10)})
    cls = []
    for basis in ("active_ratio", "nz_median", "p95", "mass_share"):
        deltas = {f"p{i}": cliffs_delta(series(pre_all[-7:], f"p{i}_{basis}"), series(post_all[:7], f"p{i}_{basis}"))
                  for i in range(1, 7)}
        c = classify_shift(deltas)
        cls.append({"basis": f"{basis} (Cliff's delta, ±7 nights)", **{f"delta_{k}": v for k, v in deltas.items()}, **c})
    mat = {m: cliffs_delta(series(pre_all[-7:], m), series(post_all[:7], m)) for m in MAT_METRICS}
    cls.append({"basis": "whole mat (Cliff's delta, ±7 nights)", **{f"delta_{k}": v for k, v in mat.items()},
                "label": "", "shifted_channels": ""})

    # ---- a second, separate 22482 change: strongest whole-mat split away from the P1 boundary --------------
    cons_m = consensus(rank_splits({m: series(nights, m) for m in MAT_METRICS}, (7,)), MAT_METRICS, 7)
    sc = -cons_m["mean_rank"]
    sc[0] = np.nan
    ks = next((k for k in distinct_peaks(sc, 7, top=5) if abs(k - kb) > 3), None)
    secondary = None
    if ks is not None:
        secondary = nights[ks]["label"]
        a, b = nights[max(kb, ks - 7):ks], nights[ks:ks + 7]          # pre window after the P1 boundary only
        for r in compare_units(a, b, metrics_all + ("p1_active_ratio",)):
            win.append({"device": "22482", "window": f"secondary_{secondary}_pm7", **r})
        for basis in ("active_ratio", "nz_median", "p95", "mass_share"):
            deltas = {f"p{i}": cliffs_delta(series(a, f"p{i}_{basis}"), series(b, f"p{i}_{basis}")) for i in range(1, 7)}
            cls.append({"basis": f"secondary {secondary}: {basis} (after-P1-boundary nights vs next 7)",
                        **{f"delta_{k}": v for k, v in deltas.items()}, **classify_shift(deltas, primary="p6")})
        cls.append({"basis": f"secondary {secondary}: whole mat", "label": "", "shifted_channels": "",
                    **{f"delta_{m}": cliffs_delta(series(a, m), series(b, m)) for m in MAT_METRICS}})
        k80s = next(j for j, u in enumerate(nights80) if u["label"] >= secondary)
        for r in compare_units(nights80[max(0, k80s - 7):k80s], nights80[k80s:k80s + 7],
                               tuple(f"p{i}_active_ratio" for i in range(1, 7)) + CONTEXT):
            win.append({"device": "22480 (control)", "window": f"secondary_{secondary}_pm7", **r})
    control_cp = []
    ser80 = {m: series(nights80, m) for m in ("pressure_sum_median", "active_channels_mean", "temp_median", "humid_median")
             + tuple(f"p{i}_active_ratio" for i in range(1, 7))}
    for m, x in ser80.items():
        d = split_scores(x, 3)
        peaks = distinct_peaks(np.abs(d), 3, top=5)
        control_cp.append({"unit_type": "night", "kind": "control_22480_at_same_split", "metric": m, "window": 3,
                           "split_first_unit_after": nights80[k80]["label"], "score_d": round(float(d[k80]), 3),
                           "rank": next((r for r, p in enumerate(peaks, 1) if abs(p - k80) <= 1), None),
                           "max_abs_d_series": round(float(np.nanmax(np.abs(d))), 3)})
    for m in ("temp_median", "humid_median"):
        d = split_scores(series(nights, m), 3)
        control_cp.append({"unit_type": "night", "kind": "targets_22482_at_split", "metric": m, "window": 3,
                           "split_first_unit_after": b_label, "score_d": round(float(d[kb]), 3),
                           "max_abs_d_series": round(float(np.nanmax(np.abs(d))), 3)})
    cp += control_cp

    # ---- schema / firmware / event timeline ----------------------------------------------------------------
    tl_rows = []
    dev = ts[a82["schema"] == 1]
    tl_rows.append({"event": "device_id column first row", "ts": iso(dev.min()) if dev.size else None,
                    "days_from_boundary": round((dev.min() - first_shift_ts) / 86400, 2) if dev.size else None})
    for lab in sorted(set(a82["container"].tolist())):
        sel = ts[a82["container"] == lab]
        tl_rows.append({"event": f"container {lab}", "ts": f"{iso(sel.min())} .. {iso(sel.max())}", "days_from_boundary": None})
    regs = [(u["label"], u.get("sampling_median_step_s")) for u in nights]
    changes = [f"{regs[i][0]}: {regs[i - 1][1]} -> {regs[i][1]}" for i in range(1, len(regs)) if regs[i][1] != regs[i - 1][1]]
    tl_rows.append({"event": "sampling regime changes (per night median step)", "ts": "; ".join(changes) or "none",
                    "days_from_boundary": None})
    tok = Counter()
    first_seen, last_seen = {}, {}
    for t, c in zip(ts, a82["control"]):
        for x in str(c).split():
            tok[x] += 1
            first_seen.setdefault(x, t)
            last_seen[x] = t
    for x in sorted(tok):
        tl_rows.append({"event": f"control token {x}", "ts": f"{iso(first_seen[x])} .. {iso(last_seen[x])}", "count": tok[x],
                        "days_from_boundary": round((first_seen[x] - first_shift_ts) / 86400, 2)})
    tl_rows.append({"event": "files at the boundary", "ts": f"{nights[kb - 1]['first_file']} | {nights[kb]['first_file']}",
                    "days_from_boundary": 0})
    tl_rows.append({"event": "A9 reference marker", "ts": A9_MARKER.date().isoformat(),
                    "days_from_boundary": round((int((A9_MARKER - _EPOCH).total_seconds()) - first_shift_ts) / 86400, 2)})

    # ---- impact --------------------------------------------------------------------------------------------
    t80 = a80["ts"]
    aff = ts >= first_shift_ts
    m82, m80 = minutes(ts), minutes(t80)
    union = np.union1d(m82, m80)
    keep = np.union1d(minutes(ts[~aff]), m80)
    keep_ts = np.concatenate([ts[~aff], t80])
    cap = chronological_capacity(night_index(keep_ts), MIN_SPLIT_NIGHTS)
    imp = [{
        "affected_from": iso(first_shift_ts), "affected_to": iso(ts[-1]), "affected_rows": int(aff.sum()),
        "affected_rows_share_22482": round(float(aff.mean()), 4),
        "affected_nights": int(np.unique(night_index(ts[aff])).size), "affected_hours": round(minutes(ts[aff]).size / 60, 2),
        "affected_hours_share_22482": round(minutes(ts[aff]).size / m82.size, 4),
        "affected_hours_share_user02": round(minutes(ts[aff]).size / union.size, 4),
        "control_22480_hours_same_period": round(minutes(t80[t80 >= first_shift_ts]).size / 60, 2),
        "control_22480_nights_same_period": int(np.unique(night_index(t80[t80 >= first_shift_ts])).size),
        "affected_hours_also_covered_by_22480": round(np.intersect1d(minutes(ts[aff]), m80).size / 60, 2),
        "user02_hours_total": round(union.size / 60, 2), "user02_hours_without_affected": round(keep.size / 60, 2),
        "user02_nights_without_affected": int(np.unique(night_index(keep_ts)).size),
        "user02_last_row_without_affected": iso(keep_ts.max()),
        "meets_a11_volume": bool(keep.size / 60 >= MIN_HOURS and np.unique(night_index(keep_ts)).size >= MIN_NIGHTS),
        "meets_a11_chronological": bool(cap["can_split"]),
    }]
    imp[0] = {"kind": "shifted_slice (from first fully shifted night)", **imp[0]}
    # configured channel-quality phases (D-022) applied as labels, and checked against the evidence above
    bounds, names, chans = channel_quality_spec(DEV[1])
    lab = assign_phase(ts, bounds, names) if bounds else np.full(ts.size, names[0], dtype=object)
    evidence = [(int(nights[kb - 2]["end_ts"]), int(nights[kb - 1]["start_ts"])),
                (int(nights[kb - 1]["end_ts"]), int(first_shift_ts))]
    for name in names:
        m = lab == name
        imp.append({"kind": f"configured_phase:{name}", "channel_quality_flag": chans.get(name, ""),
                    "affected_from": iso(ts[m].min()) if m.any() else None, "affected_to": iso(ts[m].max()) if m.any() else None,
                    "affected_rows": int(m.sum()), "affected_rows_share_22482": round(float(m.mean()), 4),
                    "affected_nights": int(np.unique(night_index(ts[m])).size), "affected_hours": round(minutes(ts[m]).size / 60, 2),
                    "affected_hours_share_user02": round(minutes(ts[m]).size / union.size, 4),
                    "config_matches_evidence": bool(bounds == evidence)})
    unlabeled = int((lab == "").sum())
    imp.append({"kind": "configured_phase:rows_inside_boundary_gaps", "affected_rows": unlabeled})

    od = paths.p0_output_dir("user02_channel_anomaly")
    unit_rows = [{"device": dv, **{k: (iso(v) if k.endswith("_ts") else v) for k, v in u.items() if k not in ("first", "last")}}
                 for dv, key in (("22482", DEV), ("22480", CONTROL)) for ut in ("night", "session", "day") for u in U[key][ut]]
    write_csv(od / "unit_channel_summary.csv", unit_rows, columns(unit_rows, ["device", "unit_type", "unit", "label"]))
    write_csv(od / "change_point_candidates.csv", cp, columns(cp, ["unit_type", "kind", "metric", "window", "rank"]))
    rec_rows = [{"device": "22482", "window": "recovery", **r} for r in rec]
    write_csv(od / "boundary_window_comparison.csv", win + rec_rows, columns(win + rec_rows, ["device", "window", "metric"]))
    write_csv(od / "channel_shift_classification.csv", cls, columns(cls, ["basis", "label", "shifted_channels"]))
    write_csv(od / "hourly_onset.csv", hr_rows, columns(hr_rows, ["hour", "segment"]))
    write_csv(od / "schema_firmware_timeline.csv", tl_rows, columns(tl_rows, ["event", "ts", "days_from_boundary"]))
    write_csv(od / "impact_summary.csv", imp, columns(imp, ["kind", "channel_quality_flag"]))
    figs = make_figure(od, nights, nights80, kb, k80)
    write_json(od / "user02_channel_anomaly_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"), "raw_root": paths.path_config()["raw_root"],
        "manifest_sha256": sha256_file(mpath), "raw_integrity": {k: len(v) for k, v in integrity.items()},
        "strongest_split": {u: U[DEV][u][k]["label"] for u, k in strongest.items()},
        "boundary_interval": [iso(last_normal_ts), iso(first_shift_ts)], "hourly_best_split_p1_p95": hourly_split,
        "transition_recording": [iso(nights[kb - 1]["start_ts"]), iso(nights[kb - 1]["end_ts"])],
        "last_fully_normal_row": iso(nights[kb - 2]["end_ts"]), "secondary_whole_mat_split": secondary,
        "hourly_best_split_r2": bs.get("r2_step"), "windows": list(WINDOWS), "p1_metrics": list(P1_METRICS),
        "figures": figs, "python": platform.python_version(), "numpy": np.__version__,
        "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"A9b done in {time.time() - t_start:.0f} s -> {od.relative_to(paths.PROJECT_ROOT)}  strongest={strongest and {u: U[DEV][u][k]['label'] for u, k in strongest.items()}}")
    return 0


def make_figure(od: Path, nights: list[dict], nights80: list[dict], kb: int, k80: int) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    x = [datetime.fromisoformat(u["label"]) for u in nights]
    x80 = [datetime.fromisoformat(u["label"]) for u in nights80]
    bx = datetime.fromisoformat(nights[kb]["label"]) - timedelta(hours=12)
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.5), dpi=150, sharex=True, facecolor=SURFACE)

    def style(ax, title, ylabel):
        ax.set_facecolor(SURFACE)
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.set_ylabel(ylabel, fontsize=8, color=INK2)
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.tick_params(colors=INK2, labelsize=7)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.axvline(bx, color=INK, linestyle="--", linewidth=0.9)

    ax = axes[0]
    for i in range(2, 7):
        ax.plot(x, [u.get(f"p{i}_active_ratio") for u in nights], color=MUTED, linewidth=1, label="P2-P6" if i == 2 else None)
    ax.plot(x, [u.get("p6_active_ratio") for u in nights], color=SERIES_COLORS[1], linewidth=1.6, marker="o", markersize=2.5, label="P6")
    ax.plot(x, [u.get("p1_active_ratio") for u in nights], color=SERIES_COLORS[0], linewidth=2, marker="o", markersize=3, label="P1")
    style(ax, "22482: share of loaded rows where the channel is active, per night", "active share")
    ax.legend(frameon=False, fontsize=7, loc="lower left", ncol=3)
    ax = axes[1]
    ax.plot(x, [u.get("p1_nz_median") for u in nights], color=SERIES_COLORS[0], linewidth=2, marker="o", markersize=3, label="P1 median")
    ax.plot(x, [u.get("p1_p95") for u in nights], color=SERIES_COLORS[1], linewidth=1.6, marker="o", markersize=2.5, label="P1 p95")
    ax.set_yscale("symlog", linthresh=10)
    style(ax, "22482: P1 value when active (median) and P1 p95, per night (symlog)", "value")
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    ax = axes[2]
    ax.plot(x, [u.get("pressure_sum_median") for u in nights], color=SERIES_COLORS[0], linewidth=1.8, marker="o", markersize=2.5, label="22482")
    ax.plot(x80, [u.get("pressure_sum_median") for u in nights80], color=SERIES_COLORS[2], linewidth=1.8, marker="o", markersize=2.5, label="22480 (control)")
    style(ax, "Pressure-sum median on loaded rows, per night", "pressure sum")
    ax.legend(frameon=False, fontsize=7, loc="lower left")
    axes[0].annotate(f"strongest split: first night {nights[kb]['label']}", (bx, 1), xycoords=("data", "axes fraction"),
                     xytext=(4, -10), textcoords="offset points", fontsize=7, color=INK)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    fig.tight_layout()
    p = od / "figures" / "channel_anomaly_timeseries.png"
    with open_for_write(p, "wb") as fh:
        fig.savefig(fh, format="png", facecolor=SURFACE)
    plt.close(fig)
    return [p.name]


if __name__ == "__main__":
    raise SystemExit(main())
