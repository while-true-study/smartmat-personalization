"""P0 analysis A9 — pressure channel quality and consistency audit. Read-only on raw data.

Uses only analysis-eligible sources (D-017: the provider-confirmed invalid User06 source, quarantined and
restricted sources are excluded). Main groups: User01, User02/22480, User02/22482, User07 on the A5/A7
audit timeline; auxiliary legacy sources are reported for reference only. Pressure values are never
clipped, normalised, imputed or removed (src/data/pressure_quality.py).

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/pressure_quality/:
  pressure_channel_summary.csv, pressure_boundary_summary.csv, constant_run_summary.csv,
  constant_channel_runs.csv, frame_constant_runs.csv, pressure_cross_channel.csv,
  pressure_distribution_by_period.csv, pressure_delta_summary.csv, pressure_schema_summary.csv,
  pressure_schema_by_source.csv, pressure_policy_impact.csv, pressure_flag_schema.csv,
  excluded_sources.csv, pressure_quality_run_meta.json
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
from src.data.duplicates import overlapping_file_pairs, row_keys, subject_device_groups, upload_copy_mask  # noqa: E402
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.pressure_quality import (  # noqa: E402
    ADC_BOUNDARY_CANDIDATE, N_CH, RUN_MIN_S, boundary_summary, channel_stats, classify_channel_runs, cross_channel,
    delta_stats, flag_schema, frame_flags, pressure_matrix, pressure_policy_masks, row_policy_impact, run_table,
    schema_by_file,
)
from src.data.provenance import SourceData, load_sources  # noqa: E402
from src.data.subject_mapping import excluded_sources, resolve_source  # noqa: E402
from src.data.target_quality import flagged_runs, session_ids  # noqa: E402
from src.data.temporal import build_timeline, candidate_sessions, chunk_alignment, steps  # noqa: E402

PRIMARY = [("User01", "unknown"), ("User02", "22480"), ("User02", "22482"), ("User07", "unknown")]
LABELS = {("User01", "unknown"): "User01", ("User02", "22480"): "User02/22480",
          ("User02", "22482"): "User02/22482", ("User07", "unknown"): "User07"}
KNOWN_EVENTS = {"User01": {"2025-11-18": "heating season start (metadata, year inferred)",
                           "2025-12-17": "log format change", "2026-01-25": "pressure sensor change (provider note)"}}
STUCK_ONE_CHANNEL_S, STUCK_FRAME_S = 1800, 300      # Policy C heuristic only (never frozen)
_EPOCH = datetime(1970, 1, 1)


def iso(sec) -> str:
    return (_EPOCH + timedelta(seconds=int(sec))).isoformat(sep=" ")


def day(sec) -> str:
    return (_EPOCH + timedelta(seconds=int(sec))).date().isoformat()


def week_start(sec) -> str:
    d = (_EPOCH + timedelta(seconds=int(sec))).date()
    return (d - timedelta(days=d.weekday())).isoformat()


def columns(rows: list[dict], first: list[str]) -> list[str]:
    cols = list(first)
    for r in rows:
        cols += [k for k in r if k not in cols]
    return cols


def period_metrics(p: np.ndarray, frames: dict, sel: np.ndarray) -> dict:
    loaded = sel & frames["schema_complete"] & ~frames["all_zero"]
    q = p[loaded]
    out = {"rows": int(sel.sum()), "loaded_share": round(float(loaded.sum() / max(1, sel.sum())), 4)}
    if q.shape[0] == 0:
        return out
    tot = q.sum(axis=1)
    out.update({"pressure_sum_median": float(np.median(tot)), "pressure_sum_p95": round(float(np.percentile(tot, 95)), 1),
                "active_channels_mean": round(float(frames["active_channels"][loaded].mean()), 3)})
    share = q.sum(axis=0) / tot.sum()
    for i in range(N_CH):
        c = q[:, i]
        out[f"p{i + 1}_p95"] = round(float(np.percentile(c, 95)), 1)
        out[f"p{i + 1}_median_when_active"] = float(np.median(c[c > 0])) if (c > 0).any() else None
        out[f"p{i + 1}_active_share"] = round(float((c > 0).mean()), 4)
        out[f"p{i + 1}_mass_share"] = round(float(share[i]), 4)
        out[f"p{i + 1}_at_4095"] = int((c == ADC_BOUNDARY_CANDIDATE).sum())
    return out


def analyse(src: SourceData, label: str, primary: bool, minute_res: bool, out: dict) -> None:
    keys = row_keys(src)
    copies = np.zeros(src.n, bool) if minute_res else upload_copy_mask(src, keys, overlapping_file_pairs(src, keys))
    tl = build_timeline(src, "B", copies)
    rows, ts = tl.rows, tl.ts
    P, pres = pressure_matrix(src, rows)
    fr = frame_flags(P, pres)
    source_of_file = [resolve_source(f).source_id for f in src.files]
    src_id = np.array([source_of_file[i] for i in src.file_idx[rows]])
    if primary:
        ca = chunk_alignment(steps(tl))
        sess = candidate_sessions(tl, 1800, ca["aligned"] & (ca["n_chunks"] <= 3))    # proposed D-015; label only
    else:
        sess = [(0, tl.n - 1)] if tl.n else []
    sid = session_ids(tl.n, sess)
    role = "primary" if primary else "reference_auxiliary"

    # 1. channel statistics: overall and per source (phase)
    for scope, sel in [("overall", np.ones(tl.n, bool))] + [(s, src_id == s) for s in sorted(set(src_id.tolist()))]:
        if scope != "overall" and len(set(src_id.tolist())) == 1:
            continue
        idx = np.flatnonzero(sel)
        for ch in range(N_CH):
            out["channels"].append({"group": label, "role": role, "scope": scope, "channel": f"p{ch + 1}",
                                    **channel_stats(ts[idx], P[idx, ch], pres[idx, ch])})
    # 2. boundary values (minute-resolution legacy rows share a timestamp: runs chain across 60 s steps)
    run_step = 60 if minute_res else 6
    for ch in range(N_CH):
        v = P[pres[:, ch], ch]
        vals, cnt = np.unique(v[(v > 0) & (v < ADC_BOUNDARY_CANDIDATE)], return_counts=True)
        mode = float(vals[np.argmax(cnt)]) if vals.size else np.nan
        for kind, value in (("zero", 0.0), ("4095_candidate", float(ADC_BOUNDARY_CANDIDATE)),
                            ("channel_max", float(v.max()) if v.size else np.nan), ("top_interior_value", mode)):
            out["boundary"].append({"group": label, "role": role, "channel": f"p{ch + 1}", "kind": kind,
                                    **boundary_summary(ts, P[:, ch], pres[:, ch], value, sid if primary else None,
                                                       max_step_s=run_step)})
    # 3. cross-channel consistency (overall and per source/phase)
    for scope, sel in [("overall", np.ones(tl.n, bool))] + [(s, src_id == s) for s in sorted(set(src_id.tolist()))]:
        if scope != "overall" and len(set(src_id.tolist())) == 1:
            continue
        out["cross"].append({"group": label, "role": role, "scope": scope,
                             **cross_channel(P[sel], pres[sel], {k: v[sel] for k, v in fr.items()})})
    # 4. scale by period
    days = np.array([day(t) for t in ts])
    months = np.array([d[:7] for d in days])
    weeks = np.array([week_start(t) for t in ts])
    events = KNOWN_EVENTS.get(label, {})
    splits = [("source", src_id), ("month", months), ("week", weeks), ("day", days)]
    if label == "User01":
        # baseline evidence for A10 only: sides of the daytime recording gap on the documented change date
        noon = int((datetime(2026, 1, 25, 12) - _EPOCH).total_seconds())
        splits.append(("sensor_change_side", np.where(ts < noon, "before_2026-01-25_daytime_gap", "after_2026-01-25_daytime_gap")))
    for ptype, lab in splits:
        for per in sorted(set(lab.tolist())):
            sel = lab == per
            ev = ""
            if ptype in ("week", "day"):
                d0, span = datetime.fromisoformat(per).date(), 7 if ptype == "week" else 1
                ev = "; ".join(f"{d}: {t}" for d, t in events.items() if 0 <= (datetime.fromisoformat(d).date() - d0).days < span)
            out["period"].append({"group": label, "role": role, "period_type": ptype, "period": per,
                                  "known_event": ev, **period_metrics(P, fr, sel)})
    if minute_res or not primary:
        out["summary"].append({"group": label, "role": role, "rows": tl.n, "all_zero_rows": int(fr["all_zero"].sum()),
                               "all_zero_share": round(float(fr["all_zero"].mean()), 4),
                               "rows_with_missing_channel": int((~fr["schema_complete"]).sum()),
                               "rows_any_4095": int((np.nan_to_num(P) == ADC_BOUNDARY_CANDIDATE).any(axis=1).sum()),
                               "note": "reference only; time-based runs/deltas not computed"})
        return

    # 5. constant runs per channel and frame freezes
    recorded_h = sum(float(ts[b] - ts[a]) for a, b in sess) / 3600.0
    heuristic = np.zeros(tl.n, bool)
    for ch in range(N_CH):
        runs = classify_channel_runs(ts, P, pres, ch, fr)
        for r in run_table(runs, recorded_h):
            out["run_summary"].append({"group": label, "channel": f"p{ch + 1}", **r})
        for r in runs:
            if r["duration_s"] >= 1800:
                out["runs"].append({"group": label, "channel": r["channel"], "category": r["category"],
                                    "value": r["value"], "start": iso(ts[r["first"]]), "end": iso(ts[r["last"]]),
                                    "duration_min": round(r["duration_s"] / 60, 1), "rows": r["rows"],
                                    "source_relpath": src.files[int(src.file_idx[rows[r["first"]]])]})
            if r["category"] == "nonzero_others_change" and r["duration_s"] >= STUCK_ONE_CHANNEL_S:
                heuristic[r["first"]:r["last"] + 1] = True
    frame_runs = [(max(a - 1, 0), b) for a, b in flagged_runs(ts, ~fr["frame_changed"] & ~fr["all_zero"], 60)]
    at_bound = (np.nan_to_num(P) == ADC_BOUNDARY_CANDIDATE).any(axis=1)
    for m in RUN_MIN_S:
        sel = [(a, b) for a, b in frame_runs if ts[b] - ts[a] >= m]
        wb = [(a, b) for a, b in sel if at_bound[b]]
        out["frame_runs"].append({"group": label, "min_duration_s": m, "runs": len(sel),
                                  "hours": round(sum(ts[b] - ts[a] for a, b in sel) / 3600, 3),
                                  "runs_with_4095_channel": len(wb),
                                  "hours_with_4095_channel": round(sum(ts[b] - ts[a] for a, b in wb) / 3600, 3),
                                  "median_active_channels": float(np.median([fr["active_channels"][b] for a, b in sel])) if sel else None})
    for a, b in frame_runs:
        if ts[b] - ts[a] >= STUCK_FRAME_S:
            heuristic[a:b + 1] = True
    # 6. deltas within normal sampling
    for r in delta_stats(ts, P, pres):
        out["delta"].append({"group": label, **r})
    # 7. policies (simulation)
    masks = pressure_policy_masks(P, pres, src.schema_code[rows] if src.schema_code is not None else np.zeros(tl.n, np.int8), heuristic)
    for r in row_policy_impact(masks, sid, len(sess)):
        out["policy"].append({"group": label, **r})
    out["summary"].append({"group": label, "role": role, "rows": tl.n, "candidate_sessions": len(sess),
                           "recorded_hours": round(recorded_h, 1), "all_zero_rows": int(fr["all_zero"].sum()),
                           "all_zero_share": round(float(fr["all_zero"].mean()), 4),
                           "rows_with_missing_channel": int((~fr["schema_complete"]).sum()),
                           "rows_any_4095": int(at_bound.sum()), "heuristic_stuck_rows": int(heuristic.sum()),
                           "heuristic_rows_with_4095_channel": int((heuristic & at_bound).sum())})


def main() -> int:
    t_start = time.time()
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2
    groups = subject_device_groups(manifest, eligible_only=True)
    assert not any(s == "User06" for s, _ in groups), "User06 source must be excluded (D-017)"
    out = {k: [] for k in ("channels", "boundary", "cross", "period", "summary", "run_summary", "runs",
                           "frame_runs", "delta", "policy", "schema", "schema_src")}
    for key in PRIMARY + sorted(k for k in groups if k not in PRIMARY):
        g = groups[key]
        minute_res = g["families"] == {"legacy_csv_ymd_hm"}
        label = LABELS.get(key, f"{key[0]}/{key[1]}") + (" (minute resolution)" if minute_res else "")
        loaded = load_sources(root, manifest, g["sources"])
        for sid_, s in sorted(loaded.items()):
            files = schema_by_file(s)
            for f in files:
                out["schema"].append({"group": label, "source_id": sid_, **{k: (day(v) if k == "first_ts" else v) for k, v in f.items()}})
            dev_files = [f for f in files if f["rows_device_column"] > 0]
            out["schema_src"].append({
                "group": label, "source_id": sid_, "expected_channels": N_CH, "files": len(files),
                "rows": sum(f["rows"] for f in files), "rows_p6": sum(f["rows_p6"] for f in files),
                "rows_device_column": sum(f["rows_device_column"] for f in files),
                "rows_nonstandard": sum(f["rows_nonstandard"] for f in files),
                "rows_missing_channel": sum(f["rows_missing_channel"] for f in files),
                "files_with_schema_change": sum(f["mixed_schema"] for f in files),
                "first_device_column_date": day(min(f["first_ts"] for f in dev_files)) if dev_files else "",
                "format_family": resolve_source(s.files[0]).format_family if s.files else "",
            })
        src = SourceData.concat([loaded[s] for s in sorted(loaded)], "+".join(sorted(loaded)), key[0], key[1])
        analyse(src, label, key in PRIMARY, minute_res, out)
        del loaded, src
        gc.collect()
        print(f"  {label:<34} done")

    for pol in dict.fromkeys(r["policy"] for r in out["policy"]):
        rs = [r for r in out["policy"] if r["policy"] == pol]
        tot = {k: sum(r[k] for r in rs) for k in ("rows", "rows_affected", "sessions_affected", "sessions_total")}
        tot["pct_affected"] = round(100 * tot["rows_affected"] / tot["rows"], 5)
        out["policy"].append({"group": "TOTAL_primary", "policy": pol, **tot})

    od = paths.p0_output_dir("pressure_quality")
    write_csv(od / "pressure_channel_summary.csv", out["channels"], columns(out["channels"], ["group", "role", "scope", "channel"]))
    write_csv(od / "pressure_boundary_summary.csv", out["boundary"], columns(out["boundary"], ["group", "role", "channel", "kind"]))
    write_csv(od / "constant_run_summary.csv", out["run_summary"], columns(out["run_summary"], ["group", "channel", "category"]))
    write_csv(od / "constant_channel_runs.csv", out["runs"], columns(out["runs"], ["group", "channel", "category"]))
    write_csv(od / "frame_constant_runs.csv", out["frame_runs"], columns(out["frame_runs"], ["group", "min_duration_s"]))
    write_csv(od / "pressure_cross_channel.csv", out["cross"], columns(out["cross"], ["group", "role", "scope"]))
    write_csv(od / "pressure_distribution_by_period.csv", out["period"], columns(out["period"], ["group", "role", "period_type", "period", "known_event"]))
    write_csv(od / "pressure_delta_summary.csv", out["delta"], columns(out["delta"], ["group", "series"]))
    write_csv(od / "pressure_schema_summary.csv", out["schema"], columns(out["schema"], ["group", "source_id", "file"]))
    write_csv(od / "pressure_schema_by_source.csv", out["schema_src"], columns(out["schema_src"], ["group", "source_id"]))
    write_csv(od / "pressure_policy_impact.csv", out["policy"], columns(out["policy"], ["group", "policy"]))
    write_csv(od / "pressure_group_summary.csv", out["summary"], columns(out["summary"], ["group", "role"]))
    write_csv(od / "pressure_flag_schema.csv", flag_schema(), ["column", "type", "definition"])
    write_csv(od / "excluded_sources.csv", excluded_sources(), columns(excluded_sources(), ["source_id"]))
    write_json(od / "pressure_quality_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"], "manifest_sha256": sha256_file(mpath),
        "raw_integrity": {k: len(v) for k, v in integrity.items()},
        "groups": sorted(f"{s}|{d}" for s, d in groups), "excluded_sources": [e["source_id"] for e in excluded_sources()],
        "parameters": {"boundary_candidate": ADC_BOUNDARY_CANDIDATE, "run_break_s": 60, "run_min_s": RUN_MIN_S,
                       "policy_c_one_channel_s": STUCK_ONE_CHANNEL_S, "policy_c_frame_s": STUCK_FRAME_S,
                       "context_sessions": "proposed D-015 (label only)"},
        "python": platform.python_version(), "numpy": np.__version__, "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"A9 done in {time.time() - t_start:.0f} s -> {od.relative_to(paths.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
