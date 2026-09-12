"""Pressure channel quality and consistency audit (P0 analysis A9). Read-only and descriptive.

Pressure values are never clipped, normalised, imputed or removed here. Absent channels stay NaN
(never filled with 0). 4095 is treated as a *candidate* boundary value of the 12-bit range, not as a
confirmed saturation code. Constant values are described, not declared as failures.

Constant-run categories (per channel, runs of identical consecutive values):
  zero_all_zero         channel 0 while every channel is 0 throughout (empty-mat candidate)
  zero_others_active    channel 0 while some other channel is loaded (unused / unloaded channel)
  nonzero_others_change channel constant and non-zero while other channels change (one-channel constant)
  nonzero_all_constant  the whole non-zero frame is identical throughout (frame freeze candidate)
"""
from __future__ import annotations

import numpy as np

from src.data.provenance import MISSING, SourceData
from src.data.target_quality import constant_runs, flagged_runs

N_CH = 6
ADC_BOUNDARY_CANDIDATE = 4095
RUN_BREAK_S = 60                                  # a constant run ends at a gap > 60 s
RUN_MIN_S = (60, 300, 1800, 3600)                 # reporting thresholds: >= 1 min, 5 min, 30 min, 1 h
EXTREME_STEP = 3000                               # descriptive: a near full-range change within one step
RUN_CATEGORIES = ("zero_all_zero", "zero_others_active", "nonzero_others_change", "nonzero_all_constant")


def pressure_matrix(src: SourceData, rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(values n x 6 as float with NaN where absent, present mask n x 6)."""
    raw = src.values[rows, :N_CH]
    present = raw != MISSING
    p = raw.astype(np.float64)
    p[~present] = np.nan
    return p, present


def channel_stats(ts: np.ndarray, x: np.ndarray, present: np.ndarray, max_step_s: int = 5) -> dict:
    v = x[present]
    out = {"rows": int(x.size), "present_rows": int(present.sum()), "missing_rows": int((~present).sum())}
    if v.size == 0:
        return out
    ok = present[1:] & present[:-1] & (np.diff(ts) <= max_step_s)
    same = x[1:][ok] == x[:-1][ok]
    mx = v.max()
    out.update({
        "min": float(v.min()), "p01": round(float(np.percentile(v, 1)), 2), "median": float(np.median(v)),
        "mean": round(float(v.mean()), 2), "p99": round(float(np.percentile(v, 99)), 2), "max": float(mx),
        "zero_count": int((v == 0).sum()), "zero_ratio": round(float((v == 0).mean()), 5),
        "unique_values": int(np.unique(v).size),
        "constant_step_ratio": round(float(same.mean()), 5) if same.size else None,
        "constant_nonzero_step_ratio": round(float(same[x[1:][ok] > 0].mean()), 5) if (x[1:][ok] > 0).any() else None,
        "at_4095_count": int((v == ADC_BOUNDARY_CANDIDATE).sum()),
        "at_channel_max_count": int((v == mx).sum()),
        "out_of_range_count": int(((v < 0) | (v > ADC_BOUNDARY_CANDIDATE) | (v != np.round(v))).sum()),
    })
    return out


def boundary_summary(ts: np.ndarray, x: np.ndarray, present: np.ndarray, value: float,
                     session_id: np.ndarray | None = None, max_step_s: int = 6) -> dict:
    flag = present & (x == value)
    runs = flagged_runs(ts, flag, max_step_s)
    lens = [b - a + 1 for a, b in runs]
    dur = [int(ts[b] - ts[a]) for a, b in runs]
    return {
        "value": value, "count": int(flag.sum()),
        "ratio": round(float(flag.sum() / max(1, present.sum())), 6),
        "runs": len(runs), "longest_run_rows": max(lens) if lens else 0, "longest_run_s": max(dur) if dur else 0,
        "affected_sessions": int(np.unique(session_id[flag]).size) if session_id is not None and flag.any() else 0,
        "affected_dates": int(np.unique(ts[flag] // 86400).size) if flag.any() else 0,
    }


def frame_flags(p: np.ndarray, present: np.ndarray) -> dict[str, np.ndarray]:
    full = present.all(axis=1)
    loaded = np.nan_to_num(p) > 0
    all_zero = full & ~loaded.any(axis=1)
    changed = np.ones(p.shape[0], bool)             # frame differs from the previous row
    if p.shape[0] > 1:
        changed[1:] = ~(np.nan_to_num(p[1:], nan=-1) == np.nan_to_num(p[:-1], nan=-1)).all(axis=1)
    return {"all_zero": all_zero, "active_channels": loaded.sum(axis=1), "frame_changed": changed,
            "schema_complete": full}


def classify_channel_runs(ts: np.ndarray, p: np.ndarray, present: np.ndarray, ch: int, frames: dict,
                          break_s: int = RUN_BREAK_S, min_s: int = RUN_MIN_S[0]) -> list[dict]:
    """Constant runs of one channel lasting >= min_s, with their cross-channel category."""
    runs = constant_runs(ts, p[:, ch], present[:, ch], break_s)
    cz = np.concatenate([[0], np.cumsum(frames["all_zero"])])
    cc = np.concatenate([[0], np.cumsum(frames["frame_changed"])])
    out = []
    for a, b, v in runs:
        dur = int(ts[b] - ts[a])
        if dur < min_s:
            continue
        n = b - a + 1
        if v == 0:
            cat = "zero_all_zero" if cz[b + 1] - cz[a] == n else "zero_others_active"
        else:
            cat = "nonzero_all_constant" if cc[b + 1] - cc[a + 1] == 0 else "nonzero_others_change"
        out.append({"channel": f"p{ch + 1}", "first": a, "last": b, "value": v, "rows": n, "duration_s": dur,
                    "category": cat})
    return out


def run_table(runs: list[dict], total_hours: float) -> list[dict]:
    out = []
    for cat in RUN_CATEGORIES:
        for m in RUN_MIN_S:
            sel = [r for r in runs if r["category"] == cat and r["duration_s"] >= m]
            h = sum(r["duration_s"] for r in sel) / 3600.0
            at_b = [r for r in sel if r["value"] == ADC_BOUNDARY_CANDIDATE]
            out.append({"category": cat, "min_duration_s": m, "runs": len(sel), "hours": round(h, 3),
                        "share_of_recorded_time": round(h / total_hours, 5) if total_hours else None,
                        "runs_at_4095": len(at_b), "hours_at_4095": round(sum(r["duration_s"] for r in at_b) / 3600.0, 3)})
    return out


def cross_channel(p: np.ndarray, present: np.ndarray, frames: dict) -> dict:
    """Correlations, contribution shares and dominance on rows where the mat is loaded."""
    sel = frames["schema_complete"] & ~frames["all_zero"]
    q = p[sel]
    out: dict = {"loaded_rows": int(sel.sum())}
    if q.shape[0] < 3:
        return out
    tot = q.sum(axis=1)
    share = q.sum(axis=0) / tot.sum()
    dom = np.bincount(np.argmax(q, axis=1), minlength=N_CH) / q.shape[0]
    with np.errstate(invalid="ignore"):
        corr = np.corrcoef(q, rowvar=False)
    for i in range(N_CH):
        out[f"p{i + 1}_mass_share"] = round(float(share[i]), 4)
        out[f"p{i + 1}_dominant_share"] = round(float(dom[i]), 4)
        out[f"p{i + 1}_active_share"] = round(float((q[:, i] > 0).mean()), 4)
    for i in range(N_CH):
        for j in range(i + 1, N_CH):
            out[f"corr_p{i + 1}_p{j + 1}"] = None if np.isnan(corr[i, j]) else round(float(corr[i, j]), 3)
    ac = frames["active_channels"][sel]
    out.update({"pressure_sum_median": float(np.median(tot)), "pressure_sum_p95": round(float(np.percentile(tot, 95)), 1),
                "active_channels_mean": round(float(ac.mean()), 3),
                **{f"active_channels_eq_{k}": round(float((ac == k).mean()), 4) for k in range(1, N_CH + 1)}})
    return out


def delta_stats(ts: np.ndarray, p: np.ndarray, present: np.ndarray, max_dt_s: int = 5) -> list[dict]:
    """|delta| between consecutive rows within max_dt_s, per channel and for the pressure sum."""
    out = []
    ok_t = np.diff(ts) <= max_dt_s
    series = [(f"p{i + 1}", p[:, i], present[:, i]) for i in range(N_CH)]
    full = present.all(axis=1)
    series.append(("pressure_sum", np.nan_to_num(p).sum(axis=1), full))
    for name, x, pr in series:
        ok = ok_t & pr[1:] & pr[:-1]
        d = np.diff(x)
        a = np.abs(d[ok])
        row = {"series": name, "steps": int(a.size)}
        if a.size:
            row.update({"median_abs": float(np.median(a)), "p99_abs": round(float(np.percentile(a, 99)), 1),
                        "p999_abs": round(float(np.percentile(a, 99.9)), 1), "max_abs": float(a.max()),
                        "n_abs_ge_3000": int((a >= EXTREME_STEP).sum())})
            if name != "pressure_sum":
                # isolated extreme spike: >= EXTREME_STEP in and back out, opposite sign, both within max_dt_s
                ins = ok[:-1] & ok[1:] & (np.abs(d[:-1]) >= EXTREME_STEP) & (np.abs(d[1:]) >= EXTREME_STEP) & \
                    (np.sign(d[:-1]) == -np.sign(d[1:]))
                row["isolated_extreme_spikes"] = int(ins.sum())
        out.append(row)
    return out


def schema_by_file(src: SourceData) -> list[dict]:
    out = []
    code = src.schema_code if src.schema_code is not None else np.zeros(src.n, np.int8)
    present = src.values[:, :N_CH] != MISSING
    for f in range(len(src.files)):
        idx = np.flatnonzero(src.file_idx == f)
        if idx.size == 0:
            continue
        c = np.bincount(code[idx].astype(np.int64), minlength=3)
        out.append({"file": src.files[f], "rows": int(idx.size), "rows_p6": int(c[0]), "rows_device_column": int(c[1]),
                    "rows_nonstandard": int(c[2]), "rows_missing_channel": int((~present[idx].all(axis=1)).sum()),
                    "mixed_schema": bool((c > 0).sum() > 1), "first_ts": int(src.ts[idx].min())})
    return out


def pressure_policy_masks(p: np.ndarray, present: np.ndarray, schema_code: np.ndarray,
                          heuristic_rows: np.ndarray) -> dict[str, np.ndarray]:
    """Hypothetical unusable-row masks. Nothing is removed."""
    schema_invalid = ~present.all(axis=1) | (schema_code == 2)
    v = np.nan_to_num(p)
    impossible = (present & ((v < 0) | (v > ADC_BOUNDARY_CANDIDATE) | (v != np.round(v)))).any(axis=1)
    a = schema_invalid
    b = a | impossible
    return {"A_schema_invalid": a, "B_A_plus_impossible_encoding": b, "C_B_plus_stuck_heuristic": b | heuristic_rows}


def row_policy_impact(masks: dict[str, np.ndarray], session_id: np.ndarray, n_sessions: int) -> list[dict]:
    n = session_id.size
    return [{"policy": k, "rows": n, "rows_affected": int(m.sum()),
             "pct_affected": round(100 * float(m.mean()), 5) if n else None,
             "sessions_affected": int(np.unique(session_id[m]).size), "sessions_total": n_sessions}
            for k, m in masks.items()]


def flag_schema() -> list[dict]:
    """Candidate pressure-quality flag columns for the canonical interim dataset (proposal only)."""
    return [
        {"column": "pressure_schema", "type": "category", "definition": "p6 | p6_with_device_column | nonstandard (raw line layout)"},
        {"column": "pressure_channels_present", "type": "int", "definition": "number of pressure channels in the raw row (absent channels are never filled)"},
        {"column": "pressure_all_zero", "type": "bool", "definition": "every present channel == 0"},
        {"column": "pressure_boundary_4095_channels", "type": "int", "definition": "number of channels equal to 4095 (candidate boundary value; not asserted as saturation)"},
        {"column": "pressure_impossible_encoding", "type": "bool", "definition": "any present channel < 0, > 4095 or non-integer"},
        {"column": "pressure_frame_constant_run_s", "type": "int", "definition": "length of the identical non-zero frame run the row belongs to (context, not validity)"},
        {"column": "pressure_same_second_group", "type": "int", "definition": "shared with the target flags: same-second observation group id or -1"},
        {"column": "source_period", "type": "category", "definition": "provider-documented collection period (e.g. User01 phase, before/after the 2026-01-25 sensor change); a label, not a correction"},
    ]
