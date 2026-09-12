"""P0 analysis A8 — temperature / humidity target-quality audit. Read-only on raw data.

Per subject/device timeline (the A5/A7 audit view without identical upload-chunk copies), this
labels candidate target states (zero, extreme, jumps, constant runs, same-second conflicts), describes
where they occur, and simulates how hypothetical validity policies would change the usable rows.
No value is replaced, clipped, interpolated, smoothed or deleted (src/data/target_quality.py).

Candidate sessions used as context labels follow the *proposed* D-015 rule (> 30 min, 1-3 lost
upload chunks bridged); they are not a frozen session definition.

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/target_quality/:
  target_quality_summary.csv, suspicious_value_patterns.csv, suspicious_target_rows.csv,
  target_context_summary.csv, target_jump_summary.csv, constant_run_summary.csv,
  session_target_summary.csv, same_second_target_conflicts.csv, target_policy_impact.csv,
  target_distribution_by_device.csv, target_daily_medians.csv, user02_device_th_bias.csv,
  quality_flag_schema.csv, target_quality_run_meta.json
"""
from __future__ import annotations

import gc
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.device_overlap import diff_summary, pair_rows  # noqa: E402
from src.data.duplicates import (  # noqa: E402
    overlapping_file_pairs, repeated_block_members, row_keys, subject_device_groups, timestamp_conflicts,
    upload_copy_mask,
)
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.provenance import SourceData, code_text, load_sources  # noqa: E402
from src.data.target_quality import (  # noqa: E402
    CANDIDATE_BAND, JUMP_THRESHOLDS, POLICY_C_JUMP, binned_std, channel_states, channel_values, chunk_positions,
    classify_zero_runs, constant_runs, file_positions, flag_schema, flagged_runs, has_control, jump_candidates,
    jump_summary, neighbour_valid,
    policy_impact, policy_masks, row_patterns, run_summary, session_ids, spike_candidates, target_summary,
    valid_steps,
)
from src.data.temporal import build_timeline, candidate_sessions, chunk_alignment, steps  # noqa: E402

PRIMARY = [("User01", "unknown"), ("User02", "22480"), ("User02", "22482"), ("User07", "unknown")]
LABELS = {("User01", "unknown"): "User01", ("User02", "22480"): "User02/22480",
          ("User02", "22482"): "User02/22482", ("User07", "unknown"): "User07"}
SESSION_THRESHOLD_S, BRIDGE_MAX_CHUNKS = 1800, 3           # proposed D-015, used as a context label only
_EPOCH = datetime(1970, 1, 1)


def iso(sec) -> str:
    return (_EPOCH + timedelta(seconds=int(sec))).isoformat(sep=" ")


def day(sec) -> str:
    return (_EPOCH + timedelta(seconds=int(sec))).date().isoformat()


def columns(rows: list[dict], first: list[str]) -> list[str]:
    cols = list(first)
    for r in rows:
        cols += [k for k in r if k not in cols]
    return cols


def pattern_label(t: float, h: float, t_st: str, h_st: str) -> str:
    if t == 0 and h == 0:
        return "joint_zero (T=0, H=0)"
    return f"{t_st}/{h_st} (T={t:g}, H={h:g})"


def analyse(src: SourceData, label: str, primary: bool, minute_res: bool, out: dict, keep_for_bias: dict) -> None:
    keys = row_keys(src)
    pairs = overlapping_file_pairs(src, keys)
    if minute_res:
        copies = members = np.zeros(src.n, bool)
    else:
        copies = upload_copy_mask(src, keys, pairs)
        members = repeated_block_members(src, keys, pairs)
    tl = build_timeline(src, "B", copies)
    rows, ts = tl.rows, tl.ts
    n = tl.n

    summ = {"group": label, "role": "primary" if primary else "reference",
            "timestamp_resolution": "minute" if minute_res else "second", **target_summary(src, rows)}
    x = {}
    st = {}
    for ch in ("temp", "humid"):
        x[ch], miss = channel_values(src, rows, ch)
        st[ch] = channel_states(x[ch], ch, miss)
    pat = row_patterns(st["temp"], st["humid"])

    # candidate sessions (context label only)
    dt = steps(tl)
    ca = chunk_alignment(dt)
    sess = candidate_sessions(tl, SESSION_THRESHOLD_S, ca["aligned"] & (ca["n_chunks"] <= BRIDGE_MAX_CHUNKS))
    sid = session_ids(n, sess)
    sess_first = np.zeros(n, bool)
    sess_last = np.zeros(n, bool)
    for a, b in sess:
        sess_first[a], sess_last[b] = True, True

    # context arrays in timeline order
    cpos_all, csize_all = chunk_positions(src)
    ffirst_all, flast_all = file_positions(src)
    cpos, csize = cpos_all[rows], csize_all[rows]
    gap_before = np.concatenate([[-1], dt])
    same_sec = np.zeros(n, bool)
    if n > 1:
        eq = ts[1:] == ts[:-1]
        same_sec[1:] |= eq
        same_sec[:-1] |= eq
    control = has_control(src, rows)
    control_near = control.copy()
    control_near[1:] |= control[:-1]
    control_near[:-1] |= control[1:]

    suspicious = np.zeros(n, bool)
    for ch in ("temp", "humid"):
        suspicious |= ~st[ch]["valid"]
    susp_pos = np.flatnonzero(suspicious)
    nb = {ch: neighbour_valid(ts, x[ch], st[ch]["valid"], susp_pos) for ch in ("temp", "humid")}

    def ch_state(ch, p):
        for k in ("missing", "non_finite", "zero", "extreme_low", "extreme_high"):
            if st[ch][k][p]:
                return k
        return "valid"

    cat_of = {}
    for k, p in enumerate(susp_pos):
        r = rows[p]
        tst, hst = ch_state("temp", p), ch_state("humid", p)
        cat = pattern_label(x["temp"][p], x["humid"][p], tst, hst)
        cat_of[p] = cat
        chunk_key = src.chunk_keys[int(src.chunk_idx[r])] if src.chunk_idx is not None and src.chunk_idx[r] >= 0 else ""
        out["rows"].append({
            "group": label, "pattern": cat, "ts": iso(ts[p]), "temp": x["temp"][p], "humid": x["humid"][p],
            "temp_state": tst, "humid_state": hst, "source_relpath": src.files[int(src.file_idx[r])],
            "source_line_no": int(src.line_no[r]) if src.line_no is not None else -1, "chunk_key": chunk_key,
            "chunk_position": int(cpos[p]), "chunk_rows": int(csize[p]), "file_first_row": bool(ffirst_all[r]),
            "file_last_row": bool(flast_all[r]), "session_first_row": bool(sess_first[p]), "session_last_row": bool(sess_last[p]),
            "gap_before_s": int(gap_before[p]), "same_second": bool(same_sec[p]), "control_event": bool(control[p]),
            "control_within_1_row": bool(control_near[p]), "in_repeated_block": bool(members[r]),
            "event": code_text(int(src.event_code[r])) if src.event_code is not None else "",
            "prev_valid_temp": nb["temp"]["prev_value"][k], "next_valid_temp": nb["temp"]["next_value"][k],
            "prev_valid_humid": nb["humid"]["prev_value"][k], "next_valid_humid": nb["humid"]["next_value"][k],
            "prev_valid_dt_s": nb["temp"]["prev_dt_s"][k], "next_valid_dt_s": nb["temp"]["next_dt_s"][k],
        })

    # pattern table and context shares
    by_cat: dict[str, list[int]] = {}
    for p, c in cat_of.items():
        by_cat.setdefault(c, []).append(p)
    for c, plist in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
        p = np.array(plist)
        r = rows[p]
        files = sorted({src.files[int(f)] for f in src.file_idx[r]})
        with_chunk = cpos[p] >= 0
        out["patterns"].append({
            "group": label, "pattern": c, "count": int(p.size), "pct_of_rows": round(100 * p.size / n, 5),
            "first_ts": iso(ts[p].min()), "last_ts": iso(ts[p].max()),
            "affected_dates": int(np.unique(ts[p] // 86400).size), "affected_files": len(files),
            "files_example": " | ".join(files[:4]) + (" | ..." if len(files) > 4 else ""),
        })
        out["context"].append({
            "group": label, "pattern": c, "count": int(p.size),
            "with_chunk_info": int(with_chunk.sum()),
            "share_chunk_first_row": round(float((cpos[p][with_chunk] == 0).mean()), 4) if with_chunk.any() else None,
            "share_chunk_first_3_rows": round(float((cpos[p][with_chunk] <= 2).mean()), 4) if with_chunk.any() else None,
            "share_file_first_row": round(float(ffirst_all[r].mean()), 4),
            "share_session_first_row": round(float(sess_first[p].mean()), 4),
            "share_session_last_row": round(float(sess_last[p].mean()), 4),
            "share_after_gap_gt_60s": round(float((gap_before[p] > 60).mean()), 4),
            "share_same_second": round(float(same_sec[p].mean()), 4),
            "share_control_event_row": round(float(control[p].mean()), 4),
            "share_control_within_1_row": round(float(control_near[p].mean()), 4),
            "share_in_repeated_block": round(float(members[r].mean()), 4),
        })
    # inverse view: how often is the first row of an upload chunk a joint zero?
    first_rows = cpos == 0
    summ["chunk_first_rows"] = int(first_rows.sum())
    summ["chunk_first_rows_joint_zero_pct"] = round(100 * float(pat["joint_zero"][first_rows].mean()), 3) if first_rows.any() else None
    summ["other_rows_joint_zero_pct"] = round(100 * float(pat["joint_zero"][~first_rows].mean()), 4) if (~first_rows).any() else None
    # joint-zero runs: short runs at a session/chunk start vs. multi-row dropout runs elsewhere
    zruns = flagged_runs(ts, pat["joint_zero"])
    zcls = classify_zero_runs(zruns, sess_first | (cpos == 0) | ffirst_all[rows])
    zlen = np.array([b - a + 1 for a, b in zruns]) if zruns else np.array([], int)
    for cls in ("start_sentinel", "dropout_run"):
        sel = np.array([c == cls for c in zcls], bool)
        summ[f"zero_runs_{cls}"] = int(sel.sum())
        summ[f"zero_rows_{cls}"] = int(zlen[sel].sum()) if sel.any() else 0
    summ["zero_run_len_max"] = int(zlen.max()) if zlen.size else 0
    summ["zero_run_len_p50"] = float(np.median(zlen)) if zlen.size else None
    drop_dates = Counter()
    for (a, b), c in zip(zruns, zcls):
        if c == "dropout_run":
            drop_dates[day(ts[a])] += b - a + 1
            out["zero_runs"].append({"group": label, "start": iso(ts[a]), "end": iso(ts[b]), "rows": b - a + 1,
                                     "duration_s": int(ts[b] - ts[a]), "source_relpath": src.files[int(src.file_idx[rows[a]])],
                                     "session_first": bool(sess_first[a]), "chunk_position": int(cpos[a])})
    summ["zero_dropout_top_dates"] = "; ".join(f"{d}={v}" for d, v in drop_dates.most_common(5))
    zpos = np.flatnonzero(pat["joint_zero"])
    if zpos.size > 1:
        zint = np.diff(ts[zpos])
        near = np.abs(zint - 1800 * np.round(zint / 1800)) <= 60
        summ["joint_zero_intervals_near_n_x_30min_pct"] = round(100 * float((near & (zint >= 1740)).mean()), 2)
        summ["joint_zero_interval_median_s"] = float(np.median(zint))
    summ["control_event_rows"] = int(control.sum())
    rec_h = sum(float(ts[b] - ts[a]) for a, b in sess) / 3600.0
    summ["control_events_per_recorded_hour"] = round(float(control.sum()) / rec_h, 3) if rec_h else None
    top = Counter((code_text(int(src.event_code[r])) or "").split()[0] for r in rows[control]) if src.event_code is not None else Counter()
    summ["top_control_tokens"] = "; ".join(f"{k}={v}" for k, v in top.most_common(5))
    summ["candidate_sessions"] = len(sess)

    if primary:
        # jumps, spikes, runs, variance
        jumps = {}
        for ch in ("temp", "humid"):
            vs = valid_steps(ts, x[ch], st[ch]["valid"])
            for r in jump_summary(vs, ch):
                out["jumps"].append({"group": label, "channel": ch, **r})
            jumps[ch] = jump_candidates(vs, n, POLICY_C_JUMP[ch])
            for thr in JUMP_THRESHOLDS[ch]:
                summ[f"{ch}_spikes_ge_{thr}"] = int(spike_candidates(vs, n, thr).sum())
            runs = constant_runs(ts, x[ch], st[ch]["valid"])
            bstd = binned_std(ts, x[ch], st[ch]["valid"], 1800)
            dstd = binned_std(ts, x[ch], st[ch]["valid"], 86400)
            sstd = [float(np.std(x[ch][a:b + 1][st[ch]["valid"][a:b + 1]])) for a, b in sess
                    if st[ch]["valid"][a:b + 1].sum() >= 10]
            longest = max(runs, key=lambda r: ts[r[1]] - ts[r[0]]) if runs else None
            # during long constant runs of one channel, does the other channel of the same sensor still move?
            other = "humid" if ch == "temp" else "temp"
            long_runs = [(a, b) for a, b, _ in runs if ts[b] - ts[a] >= 3 * 3600]
            other_range = [float(np.ptp(x[other][a:b + 1][st[other]["valid"][a:b + 1]]))
                           for a, b in long_runs if st[other]["valid"][a:b + 1].any()]
            out["runs"].append({
                "group": label, "channel": ch, **run_summary(ts, runs),
                "longest_run_value": longest[2] if longest else None,
                "longest_run_start": iso(ts[longest[0]]) if longest else "",
                "bins_30min": int(bstd.size), "bins_30min_zero_std_pct": round(100 * float((bstd == 0).mean()), 2) if bstd.size else None,
                "bins_30min_median_std": round(float(np.median(bstd)), 3) if bstd.size else None,
                "daily_median_std": round(float(np.median(dstd)), 3) if dstd.size else None,
                "runs_ge_3h_other_channel_median_range": float(np.median(other_range)) if other_range else None,
                "runs_ge_3h_other_channel_range_ge_2": int(sum(r >= 2 for r in other_range)),
                "sessions_with_10_valid": len(sstd),
                "session_median_std": round(float(np.median(sstd)), 3) if sstd else None,
                "sessions_zero_std": int(sum(s == 0 for s in sstd)),
            })
        # per-session table
        for k, (a, b) in enumerate(sess):
            vt, vh = st["temp"]["valid"][a:b + 1], st["humid"]["valid"][a:b + 1]
            t_s, h_s = x["temp"][a:b + 1][vt], x["humid"][a:b + 1][vh]
            out["sessions"].append({
                "group": label, "candidate_session": k, "start": iso(ts[a]), "end": iso(ts[b]),
                "duration_h": round((ts[b] - ts[a]) / 3600, 3), "rows": int(b - a + 1),
                "temp_invalid_rows": int((~vt).sum()), "humid_invalid_rows": int((~vh).sum()),
                "temp_median": float(np.median(t_s)) if t_s.size else None, "temp_min": float(t_s.min()) if t_s.size else None,
                "temp_max": float(t_s.max()) if t_s.size else None, "temp_std": round(float(t_s.std()), 3) if t_s.size else None,
                "temp_unique": int(np.unique(t_s).size), "temp_share_28_30": round(float(((t_s >= 28) & (t_s <= 30)).mean()), 4) if t_s.size else None,
                "humid_median": float(np.median(h_s)) if h_s.size else None, "humid_min": float(h_s.min()) if h_s.size else None,
                "humid_max": float(h_s.max()) if h_s.size else None, "humid_std": round(float(h_s.std()), 3) if h_s.size else None,
                "humid_unique": int(np.unique(h_s).size),
            })
        # policies
        masks = policy_masks(st["temp"], st["humid"], jumps["temp"], jumps["humid"])
        for r in policy_impact(masks, sid, len(sess)):
            out["policy"].append({"group": label, **r})
        # distribution on policy-B-valid values
        okb = {ch: ~masks["B_zero_plus_extreme_glitch"][ch] for ch in ("temp", "humid")}
        months = np.array([day(t)[:7] for t in ts])
        for scope in ["overall"] + sorted(set(months.tolist())):
            sel = np.ones(n, bool) if scope == "overall" else months == scope
            row = {"group": label, "scope": scope, "rows": int(sel.sum())}
            for ch in ("temp", "humid"):
                v = x[ch][sel & okb[ch]]
                if v.size:
                    row.update({f"{ch}_min": float(v.min()), f"{ch}_p25": float(np.percentile(v, 25)),
                                f"{ch}_median": float(np.median(v)), f"{ch}_p75": float(np.percentile(v, 75)),
                                f"{ch}_max": float(v.max()), f"{ch}_iqr": float(np.percentile(v, 75) - np.percentile(v, 25))})
            if scope == "overall":
                for ch in ("temp", "humid"):
                    sm = [float(np.median(x[ch][a:b + 1][okb[ch][a:b + 1]])) for a, b in sess if okb[ch][a:b + 1].any()]
                    row.update({f"{ch}_session_median_p10": float(np.percentile(sm, 10)), f"{ch}_session_median_p50": float(np.median(sm)),
                                f"{ch}_session_median_p90": float(np.percentile(sm, 90))})
                if label == "User02/22480":
                    vt = x["temp"][okb["temp"]]
                    summ["temp_share_28_30"] = round(float(((vt >= 28) & (vt <= 30)).mean()), 4)
            out["dist"].append(row)
        days = ts // 86400
        for d in np.unique(days):
            sel = days == d
            out["daily"].append({"group": label, "date": day(d * 86400), "rows": int(sel.sum()),
                                 "temp_median": float(np.median(x["temp"][sel & okb["temp"]])) if (sel & okb["temp"]).any() else None,
                                 "humid_median": float(np.median(x["humid"][sel & okb["humid"]])) if (sel & okb["humid"]).any() else None,
                                 "temp_std": round(float(np.std(x["temp"][sel & okb["temp"]])), 3) if (sel & okb["temp"]).any() else None})
        # same-second conflicts (A5 function on all rows of the group)
        conf = timestamp_conflicts(src, keys)
        kinds = Counter()
        for c in conf:
            if c["kind"] == "sensor_conflict":
                kinds["pressure_only"] += 1
                continue
            tdiff, hdiff = c["temp_diff"] > 0, c["humid_diff"] > 0
            cls = "temp_and_humid" if tdiff and hdiff else ("temp_only" if tdiff else "humid_only")
            kinds[cls] += 1
            kinds["with_sentinel"] += int(c["involves_th_sentinel"])
            kinds["with_control_event"] += int(c["involves_control_event"])
            kinds["also_pressure_differs"] += int(c["max_pressure_diff"] > 0)
            sel = np.flatnonzero(src.ts == c["ts"])
            vals = sorted({(int(src.values[i, 6]), int(src.values[i, 7])) for i in sel})
            evs = sorted({code_text(int(src.event_code[i])) or "" for i in sel}) if src.event_code is not None else []
            out["conflicts"].append({"group": label, "ts": iso(c["ts"]), "class": cls, "temp_diff": c["temp_diff"],
                                     "humid_diff": c["humid_diff"], "max_pressure_diff": c["max_pressure_diff"],
                                     "involves_sentinel": c["involves_th_sentinel"], "involves_control_event": c["involves_control_event"],
                                     "origin": c["origin"], "adjacent_lines": c["adjacent_lines"],
                                     "th_values": " / ".join(f"({t},{h})" for t, h in vals), "events": " | ".join(evs),
                                     "files": c["files"]})
        for k in ("pressure_only", "temp_only", "humid_only", "temp_and_humid", "with_sentinel",
                  "with_control_event", "also_pressure_differs"):
            summ[f"same_second_{k}"] = kinds.get(k, 0)
        if label.startswith("User02/"):
            keep_for_bias[label] = (ts.copy(), x["temp"].copy(), x["humid"].copy(), okb["temp"].copy(), okb["humid"].copy())
    out["summary"].append(summ)


def main() -> int:
    t_start = time.time()
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2
    groups = subject_device_groups(manifest)
    out = {k: [] for k in ("summary", "patterns", "rows", "context", "jumps", "runs", "sessions", "conflicts",
                           "policy", "dist", "daily", "zero_runs")}
    keep: dict = {}
    for key in PRIMARY + sorted(k for k in groups if k not in PRIMARY):
        g = groups[key]
        minute_res = g["families"] == {"legacy_csv_ymd_hm"}
        label = LABELS.get(key, f"{key[0]}/{key[1]}") + (" (minute resolution)" if minute_res else "")
        loaded = load_sources(root, manifest, g["sources"])
        src = SourceData.concat([loaded[s] for s in sorted(loaded)], "+".join(sorted(loaded)), key[0], key[1])
        analyse(src, label, key in PRIMARY, minute_res, out, keep)
        del loaded, src
        gc.collect()
        print(f"  {label:<34} done")

    # policy totals over the primary groups
    for pol in dict.fromkeys(r["policy"] for r in out["policy"]):
        rs = [r for r in out["policy"] if r["policy"] == pol]
        tot = {k: sum(r[k] for r in rs) for k in ("rows", "temp_invalid", "humid_invalid", "rows_any_invalid",
                                                   "usable_temp_rows", "usable_humid_rows", "usable_both_rows",
                                                   "sessions_affected", "sessions_total")}
        tot["pct_rows_any_invalid"] = round(100 * tot["rows_any_invalid"] / tot["rows"], 4)
        out["policy"].append({"group": "TOTAL_primary", "policy": pol, **tot})

    # User02 device T/H relation (reproduces A2 on the audit view; paired within +-1 s)
    bias = []
    if {"User02/22480", "User02/22482"} <= set(keep):
        ta, xa_t, xa_h, oa_t, oa_h = keep["User02/22480"]
        tb, xb_t, xb_h, ob_t, ob_h = keep["User02/22482"]
        ia, jb = pair_rows(ta, tb, 1)
        for ch, xa, xb, oa, ob in (("temp", xa_t, xb_t, oa_t, ob_t), ("humid", xa_h, xb_h, oa_h, ob_h)):
            ok = oa[ia] & ob[jb]
            bias.append({"channel": ch, "comparison": "22480 - 22482 (pairs within 1 s, policy-B-valid)",
                         **diff_summary(xa[ia[ok]], xb[jb[ok]])})

    od = paths.p0_output_dir("target_quality")
    write_csv(od / "target_quality_summary.csv", out["summary"], columns(out["summary"], ["group", "role"]))
    write_csv(od / "suspicious_value_patterns.csv", out["patterns"], columns(out["patterns"], ["group", "pattern"]))
    write_csv(od / "suspicious_target_rows.csv", out["rows"], columns(out["rows"], ["group", "pattern", "ts"]))
    write_csv(od / "target_context_summary.csv", out["context"], columns(out["context"], ["group", "pattern"]))
    write_csv(od / "target_jump_summary.csv", out["jumps"], columns(out["jumps"], ["group", "channel", "dt_class"]))
    write_csv(od / "constant_run_summary.csv", out["runs"], columns(out["runs"], ["group", "channel"]))
    write_csv(od / "session_target_summary.csv", out["sessions"], columns(out["sessions"], ["group", "candidate_session"]))
    write_csv(od / "same_second_target_conflicts.csv", out["conflicts"], columns(out["conflicts"], ["group", "ts", "class"]))
    write_csv(od / "target_policy_impact.csv", out["policy"], columns(out["policy"], ["group", "policy"]))
    write_csv(od / "target_distribution_by_device.csv", out["dist"], columns(out["dist"], ["group", "scope"]))
    write_csv(od / "target_daily_medians.csv", out["daily"], columns(out["daily"], ["group", "date"]))
    write_csv(od / "user02_device_th_bias.csv", bias, columns(bias, ["channel", "comparison"]))
    write_csv(od / "zero_dropout_runs.csv", out["zero_runs"], columns(out["zero_runs"], ["group", "start", "end", "rows"]))
    write_csv(od / "quality_flag_schema.csv", flag_schema(), ["column", "type", "values", "purpose"])
    write_json(od / "target_quality_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"], "manifest_sha256": sha256_file(mpath),
        "raw_integrity": {k: len(v) for k, v in integrity.items()},
        "parameters": {"candidate_band": CANDIDATE_BAND, "jump_thresholds": JUMP_THRESHOLDS,
                       "policy_c_jump": POLICY_C_JUMP, "jump_max_dt_s": 5, "constant_run_break_s": 1800,
                       "context_sessions": "proposed D-015 (> 30 min, 1-3 lost chunks bridged); label only",
                       "timeline": "A5 upload_copy_mask view (A7 timeline B); minute-resolution groups unmodified"},
        "python": platform.python_version(), "numpy": np.__version__, "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"A8 done in {time.time() - t_start:.0f} s -> {od.relative_to(paths.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
