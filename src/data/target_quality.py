"""Temperature / humidity target-quality audit (P0 analysis A8). Read-only and descriptive.

Nothing here replaces, clips, interpolates, smooths or deletes a target value. Every state below
is a *candidate* label used to measure structure; ranges and jump sizes are descriptive parameters,
not validity rules (OPEN-09).

Per-channel states (temperature and humidity separately):
  missing        channel absent in the row
  non_finite     NaN / inf (cannot occur in the integer raw logs; handled for completeness)
  zero           value == 0
  extreme_low    value below the candidate plausibility band
  extreme_high   value above the candidate plausibility band
  valid          none of the above
Row-level candidate patterns: joint zero (T = 0 and H = 0), abrupt jumps between consecutive valid
observations, isolated spikes, constant runs, and same-second conflicts (via src/data/duplicates.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from src.data.provenance import MISSING, SourceData, code_text
from src.data.duplicates import CONTROL_TOKENS

CANDIDATE_BAND = {"temp": (-10.0, 60.0), "humid": (0.0, 100.0)}   # descriptive, not a rule
JUMP_THRESHOLDS = {"temp": (2, 3, 5, 10), "humid": (5, 10, 20, 40)}
POLICY_C_JUMP = {"temp": 3, "humid": 10}                           # sensitivity only
DT_CLASSES = ((0, 5, "<=5 s"), (6, 60, "6-60 s"), (61, 1800, "1-30 min"), (1801, 10**12, ">30 min"))
RUN_BREAK_S = 1800


# ---------------------------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------------------------

def channel_values(src: SourceData, rows: np.ndarray, channel: str) -> tuple[np.ndarray, np.ndarray]:
    """Float values (NaN where missing) and the missing mask for 'temp' or 'humid'."""
    j = 6 if channel == "temp" else 7
    raw = src.values[rows, j]
    missing = raw == MISSING
    x = raw.astype(np.float64)
    x[missing] = np.nan
    return x, missing


def channel_states(x: np.ndarray, channel: str, missing: np.ndarray | None = None) -> dict[str, np.ndarray]:
    lo, hi = CANDIDATE_BAND[channel]
    miss = np.zeros(x.size, bool) if missing is None else missing.copy()
    non_finite = ~np.isfinite(x) & ~miss
    finite = np.isfinite(x)
    zero = finite & (x == 0)
    ext_lo = finite & (x < lo) & ~zero
    ext_hi = finite & (x > hi)
    valid = finite & ~zero & ~ext_lo & ~ext_hi
    return {"missing": miss, "non_finite": non_finite, "zero": zero, "extreme_low": ext_lo,
            "extreme_high": ext_hi, "valid": valid}


def row_patterns(t_states: dict, h_states: dict) -> dict[str, np.ndarray]:
    jz = t_states["zero"] & h_states["zero"]
    ext = t_states["extreme_low"] | t_states["extreme_high"] | h_states["extreme_low"] | h_states["extreme_high"]
    return {
        "joint_zero": jz,
        "temp_zero_only": t_states["zero"] & ~h_states["zero"],
        "humid_zero_only": h_states["zero"] & ~t_states["zero"],
        "extreme_any": ext,
        "extreme_with_other_zero": ext & (t_states["zero"] | h_states["zero"]),
    }


# ---------------------------------------------------------------------------------------------
# Jumps, spikes, constant runs
# ---------------------------------------------------------------------------------------------

@dataclass
class ValidSteps:
    idx: np.ndarray    # positions (in the analysed order) of the later observation of each step
    prev: np.ndarray   # positions of the earlier observation
    dt: np.ndarray
    dx: np.ndarray


def valid_steps(ts: np.ndarray, x: np.ndarray, valid: np.ndarray) -> ValidSteps:
    """Steps between consecutive *valid* observations (invalid rows are skipped, never filled)."""
    pos = np.flatnonzero(valid)
    if pos.size < 2:
        e = np.array([], np.int64)
        return ValidSteps(e, e, e, np.array([], float))
    return ValidSteps(pos[1:], pos[:-1], np.diff(ts[pos]), np.diff(x[pos]))


def jump_summary(vs: ValidSteps, channel: str) -> list[dict]:
    out = []
    for lo, hi, name in DT_CLASSES:
        sel = (vs.dt >= lo) & (vs.dt <= hi)
        a = np.abs(vs.dx[sel])
        row = {"dt_class": name, "n_steps": int(sel.sum())}
        if a.size:
            row.update({"median_abs": float(np.median(a)), "p95_abs": float(np.percentile(a, 95)),
                        "p99_abs": float(np.percentile(a, 99)), "p999_abs": float(np.percentile(a, 99.9)),
                        "max_abs": float(a.max()), "share_nonzero": round(float((a > 0).mean()), 6)})
            for thr in JUMP_THRESHOLDS[channel]:
                row[f"n_abs_ge_{thr}"] = int((a >= thr).sum())
        out.append(row)
    return out


def jump_candidates(vs: ValidSteps, n: int, threshold: float, max_dt: int = 5) -> np.ndarray:
    """Positions whose value differs from the previous valid observation by >= threshold within max_dt s."""
    mask = np.zeros(n, bool)
    sel = (vs.dt <= max_dt) & (np.abs(vs.dx) >= threshold)
    mask[vs.idx[sel]] = True
    return mask


def spike_candidates(vs: ValidSteps, n: int, threshold: float, max_dt: int = 5) -> np.ndarray:
    """Isolated spikes: a jump in and a jump back out (opposite sign), both within max_dt s."""
    mask = np.zeros(n, bool)
    if vs.idx.size < 2:
        return mask
    a_in, a_out = vs.dx[:-1], vs.dx[1:]
    ok = ((vs.dt[:-1] <= max_dt) & (vs.dt[1:] <= max_dt) & (np.abs(a_in) >= threshold)
          & (np.abs(a_out) >= threshold) & (np.sign(a_in) == -np.sign(a_out)))
    mask[vs.idx[:-1][ok]] = True
    return mask


def constant_runs(ts: np.ndarray, x: np.ndarray, valid: np.ndarray, break_s: int = RUN_BREAK_S) -> list[tuple[int, int, float]]:
    """Runs of identical consecutive valid values; a run also ends at a gap > break_s. (first_pos, last_pos, value)."""
    pos = np.flatnonzero(valid)
    if pos.size == 0:
        return []
    v, t = x[pos], ts[pos]
    new = np.ones(pos.size, bool)
    new[1:] = (v[1:] != v[:-1]) | (np.diff(t) > break_s)
    starts = np.flatnonzero(new)
    ends = np.concatenate([starts[1:] - 1, [pos.size - 1]])
    return [(int(pos[s]), int(pos[e]), float(v[s])) for s, e in zip(starts, ends)]


def flagged_runs(ts: np.ndarray, flag: np.ndarray, max_step_s: int = 6) -> list[tuple[int, int]]:
    """Consecutive flagged positions (e.g. joint-zero rows) whose steps are <= max_step_s: (first_pos, last_pos)."""
    pos = np.flatnonzero(flag)
    if pos.size == 0:
        return []
    brk = np.ones(pos.size, bool)
    brk[1:] = (np.diff(pos) != 1) | (np.diff(ts[pos]) > max_step_s)
    starts = np.flatnonzero(brk)
    ends = np.concatenate([starts[1:] - 1, [pos.size - 1]])
    return [(int(pos[s]), int(pos[e])) for s, e in zip(starts, ends)]


def classify_zero_runs(runs: list[tuple[int, int]], start_like: np.ndarray, max_start_len: int = 2) -> list[str]:
    """'start_sentinel' if a short run begins at a session/chunk start, otherwise 'dropout_run'."""
    return ["start_sentinel" if start_like[a] and (b - a + 1) <= max_start_len else "dropout_run" for a, b in runs]


def run_summary(ts: np.ndarray, runs: list[tuple[int, int, float]]) -> dict:
    if not runs:
        return {"n_runs": 0}
    dur = np.array([ts[b] - ts[a] for a, b, _ in runs], float) / 3600.0
    total = dur.sum()
    return {"n_runs": len(runs), "median_run_h": round(float(np.median(dur)), 4),
            "p99_run_h": round(float(np.percentile(dur, 99)), 3), "max_run_h": round(float(dur.max()), 3),
            "runs_ge_1h": int((dur >= 1).sum()), "runs_ge_3h": int((dur >= 3).sum()), "runs_ge_6h": int((dur >= 6).sum()),
            "share_time_in_runs_ge_1h": round(float(dur[dur >= 1].sum() / total), 4) if total else None,
            "share_time_in_runs_ge_3h": round(float(dur[dur >= 3].sum() / total), 4) if total else None}


def value_concentration(x: np.ndarray, valid: np.ndarray) -> dict:
    v = x[valid]
    if v.size == 0:
        return {"n_valid": 0}
    u, c = np.unique(v, return_counts=True)
    mode = u[np.argmax(c)]
    return {"n_valid": int(v.size), "unique_values": int(u.size), "most_frequent_value": float(mode),
            "most_frequent_ratio": round(float(c.max() / v.size), 4),
            "share_within_mode_pm1": round(float((np.abs(v - mode) <= 1).mean()), 4),
            "min": float(v.min()), "p25": float(np.percentile(v, 25)), "median": float(np.median(v)),
            "p75": float(np.percentile(v, 75)), "max": float(v.max()),
            "iqr": float(np.percentile(v, 75) - np.percentile(v, 25)), "std": round(float(v.std()), 3)}


def binned_std(ts: np.ndarray, x: np.ndarray, valid: np.ndarray, bin_s: int, min_obs: int = 10) -> np.ndarray:
    """Standard deviation of valid values per time bin (a descriptive statistic; values are not resampled)."""
    t, v = ts[valid], x[valid]
    if t.size == 0:
        return np.array([])
    b = t // bin_s
    order = np.argsort(b, kind="stable")
    b, v = b[order], v[order]
    _, start, count = np.unique(b, return_index=True, return_counts=True)
    out = [float(np.std(v[s:s + c])) for s, c in zip(start, count) if c >= min_obs]
    return np.array(out)


# ---------------------------------------------------------------------------------------------
# Context of suspicious rows
# ---------------------------------------------------------------------------------------------

def chunk_positions(src: SourceData) -> tuple[np.ndarray, np.ndarray]:
    """For every row (source order): index within its upload chunk and the chunk's row count (-1 if no chunk)."""
    pos = np.full(src.n, -1, np.int64)
    size = np.full(src.n, -1, np.int64)
    if src.chunk_idx is None:
        return pos, size
    has = np.flatnonzero(src.chunk_idx >= 0)
    if has.size == 0:
        return pos, size
    ci = src.chunk_idx[has]
    order = np.lexsort((has, ci))
    ci_s, rows_s = ci[order], has[order]
    first = np.concatenate([[True], ci_s[1:] != ci_s[:-1]])
    grp_start = np.maximum.accumulate(np.where(first, np.arange(ci_s.size), 0))
    pos[rows_s] = np.arange(ci_s.size) - grp_start
    _, inv, cnt = np.unique(ci_s, return_inverse=True, return_counts=True)
    size[rows_s] = cnt[inv]
    return pos, size


def file_positions(src: SourceData) -> tuple[np.ndarray, np.ndarray]:
    """Whether each row is the first / last data row of its file (source order)."""
    first = np.zeros(src.n, bool)
    last = np.zeros(src.n, bool)
    if src.n:
        f = src.file_idx
        first[0] = True
        first[1:] = f[1:] != f[:-1]
        last[-1] = True
        last[:-1] = f[:-1] != f[1:]
    return first, last


def has_control(src: SourceData, rows: np.ndarray) -> np.ndarray:
    if src.event_code is None:
        return np.zeros(rows.size, bool)
    cache: dict[int, bool] = {}
    out = np.zeros(rows.size, bool)
    for k, r in enumerate(rows):
        code = int(src.event_code[r])
        if code not in cache:
            text = code_text(code) or ""
            cache[code] = any(t in text for t in CONTROL_TOKENS)
        out[k] = cache[code]
    return out


def neighbour_valid(ts: np.ndarray, x: np.ndarray, valid: np.ndarray, at: np.ndarray) -> dict[str, np.ndarray]:
    """Previous / next valid value and elapsed seconds for positions `at` (positions in the analysed order)."""
    vpos = np.flatnonzero(valid)
    out = {k: np.full(at.size, np.nan) for k in ("prev_value", "prev_dt_s", "next_value", "next_dt_s")}
    if vpos.size == 0:
        return out
    i_next = np.searchsorted(vpos, at, side="right")
    i_prev = np.searchsorted(vpos, at, side="left") - 1
    okp, okn = i_prev >= 0, i_next < vpos.size
    out["prev_value"][okp] = x[vpos[i_prev[okp]]]
    out["prev_dt_s"][okp] = ts[at[okp]] - ts[vpos[i_prev[okp]]]
    out["next_value"][okn] = x[vpos[i_next[okn]]]
    out["next_dt_s"][okn] = ts[vpos[i_next[okn]]] - ts[at[okn]]
    return out


# ---------------------------------------------------------------------------------------------
# Hypothetical policies (row counts only)
# ---------------------------------------------------------------------------------------------

def policy_masks(t_states: dict, h_states: dict, jumps_t: np.ndarray, jumps_h: np.ndarray) -> dict[str, dict[str, np.ndarray]]:
    """Per policy: which rows would have an invalid temperature / humidity target. Nothing is changed."""
    jz = t_states["zero"] & h_states["zero"]
    ext_t = t_states["extreme_low"] | t_states["extreme_high"]
    ext_h = h_states["extreme_low"] | h_states["extreme_high"]
    # a zero that accompanies an extreme value in the other channel is part of the same glitch row
    glitch_zero_t = t_states["zero"] & ext_h
    glitch_zero_h = h_states["zero"] & ext_t
    a_t, a_h = jz.copy(), jz.copy()
    b_t = a_t | ext_t | glitch_zero_t | t_states["missing"] | t_states["non_finite"]
    b_h = a_h | ext_h | glitch_zero_h | h_states["missing"] | h_states["non_finite"]
    return {
        "A_joint_zero_sentinel": {"temp": a_t, "humid": a_h},
        "B_zero_plus_extreme_glitch": {"temp": b_t, "humid": b_h},
        "C_B_plus_abrupt_jump_candidates": {"temp": b_t | jumps_t, "humid": b_h | jumps_h},
    }


def policy_impact(masks: dict, session_id: np.ndarray, n_sessions: int) -> list[dict]:
    out = []
    n = session_id.size
    for name, m in masks.items():
        any_bad = m["temp"] | m["humid"]
        out.append({"policy": name, "rows": n, "temp_invalid": int(m["temp"].sum()),
                    "humid_invalid": int(m["humid"].sum()), "rows_any_invalid": int(any_bad.sum()),
                    "pct_rows_any_invalid": round(100 * float(any_bad.mean()), 4) if n else None,
                    "usable_temp_rows": int(n - m["temp"].sum()), "usable_humid_rows": int(n - m["humid"].sum()),
                    "usable_both_rows": int(n - any_bad.sum()),
                    "sessions_affected": int(np.unique(session_id[any_bad]).size), "sessions_total": n_sessions})
    return out


def flag_schema() -> list[dict]:
    """Candidate quality-flag columns for the canonical interim dataset (proposal; nothing is written)."""
    return [
        {"column": "target_temp_state", "type": "category", "values": "valid|missing|non_finite|zero|extreme_low|extreme_high",
         "purpose": "cause-preserving state of the temperature value"},
        {"column": "target_humid_state", "type": "category", "values": "valid|missing|non_finite|zero|extreme_low|extreme_high",
         "purpose": "cause-preserving state of the humidity value"},
        {"column": "target_zero_sentinel", "type": "bool", "values": "T == 0 and H == 0",
         "purpose": "known joint-zero pattern"},
        {"column": "target_extreme_glitch", "type": "bool", "values": "value outside candidate band, or zero paired with it",
         "purpose": "known device glitch pattern; raw value kept"},
        {"column": "target_chunk_position", "type": "int", "values": ">= 0 or -1",
         "purpose": "row index within its upload chunk (context of sentinels)"},
        {"column": "target_temp_jump_abs / target_humid_jump_abs", "type": "float", "values": "|delta| to previous valid obs",
         "purpose": "raw magnitude; the jump threshold is applied later, not stored as a decision"},
        {"column": "target_prev_valid_dt_s", "type": "int", "values": "seconds", "purpose": "separates jumps after gaps from 3-s jumps"},
        {"column": "target_spike_candidate", "type": "bool", "values": "in-and-out jump within 5 s",
         "purpose": "candidate only; parameterised"},
        {"column": "target_temp_run_h / target_humid_run_h", "type": "float", "values": "hours",
         "purpose": "length of the constant run the row belongs to"},
        {"column": "target_same_second_group", "type": "int", "values": "group id or -1",
         "purpose": "same-second observations with different values; keeps order and provenance"},
        {"column": "source_relpath, source_line_no, source_chunk_key", "type": "provenance", "values": "",
         "purpose": "unique row identity back to raw"},
    ]


def target_summary(src: SourceData, rows: np.ndarray) -> dict:
    """State counts and value concentration for one subject/device group (rows in analysed order)."""
    out: dict = {"rows": int(rows.size)}
    states = {}
    for ch in ("temp", "humid"):
        x, miss = channel_values(src, rows, ch)
        st = channel_states(x, ch, miss)
        states[ch] = st
        for k, m in st.items():
            out[f"{ch}_{k}"] = int(m.sum())
        out[f"{ch}_valid_pct"] = round(100 * float(st["valid"].mean()), 4) if rows.size else None
        out.update({f"{ch}_{k}": v for k, v in value_concentration(x, st["valid"]).items()})
    for k, m in row_patterns(states["temp"], states["humid"]).items():
        out[f"rows_{k}"] = int(m.sum())
    both = states["temp"]["valid"] & states["humid"]["valid"]
    out["rows_both_valid"] = int(both.sum())
    out["rows_both_valid_pct"] = round(100 * float(both.mean()), 4) if rows.size else None
    return out


def session_ids(n: int, sessions: Sequence[tuple[int, int]]) -> np.ndarray:
    sid = np.full(n, -1, np.int64)
    for k, (a, b) in enumerate(sessions):
        sid[a:b + 1] = k
    return sid
