"""Temporal gap structure and session-boundary sensitivity (P0 analysis A7). Read-only, descriptive.

Nothing here fixes a session definition, creates session IDs, removes rows, resamples or
interpolates. Candidate thresholds are evaluated side by side; the choice is a documented decision.

Terminology (a step is the time difference between consecutive rows of one subject/device timeline):
  same_second          0 s    (several observations logged in one second; kept)
  sampling             1-5 s  (nominal ~3 s sampling and its jitter)
  short_missing        6-15 s (a few samples missing)
  short_interruption   15 s-5 min
  medium_interruption  5-30 min
  long_interruption    30 min-2 h
  break                > 2 h  (typically the daytime pause between nights)
These classes are descriptive labels, not session rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from src.data.provenance import SourceData, code_text

DAY_S = 86400
UPLOAD_CHUNK_S = 1800
STEP_CLASSES = ((0, 0, "same_second"), (1, 5, "sampling"), (6, 15, "short_missing"),
                (16, 300, "short_interruption"), (301, 1800, "medium_interruption"),
                (1801, 7200, "long_interruption"), (7201, 10**12, "break"))
GAP_BUCKETS = ((0, 0, "0 s"), (1, 5, "<=5 s"), (6, 15, "5-15 s"), (16, 30, "15-30 s"), (31, 60, "30 s-1 min"),
               (61, 300, "1-5 min"), (301, 900, "5-15 min"), (901, 1800, "15-30 min"), (1801, 3600, "30-60 min"),
               (3601, 7200, "1-2 h"), (7201, 21600, "2-6 h"), (21601, 43200, "6-12 h"), (43201, 10**12, ">12 h"))
THRESHOLDS_MIN = (1, 2, 5, 10, 15, 30, 45, 60, 90, 120)


# ---------------------------------------------------------------------------------------------
# Timelines
# ---------------------------------------------------------------------------------------------

@dataclass
class Timeline:
    """Rows of one subject/device in time order (stable: file order within one second)."""
    label: str
    rows: np.ndarray   # indices into the SourceData
    ts: np.ndarray

    @property
    def n(self) -> int:
        return int(self.rows.size)


def build_timeline(src: SourceData, label: str, exclude: np.ndarray | None = None) -> Timeline:
    keep = np.arange(src.n) if exclude is None else np.flatnonzero(~exclude)
    order = keep[np.argsort(src.ts[keep], kind="stable")]
    return Timeline(label=label, rows=order, ts=src.ts[order])


def steps(tl: Timeline) -> np.ndarray:
    return np.diff(tl.ts)


def step_summary(dt: np.ndarray) -> dict:
    out = {"n_steps": int(dt.size)}
    if dt.size:
        pos = dt[dt > 0]
        out.update({"min_s": int(dt.min()), "median_s": float(np.median(dt)), "p90_s": float(np.percentile(dt, 90)),
                    "p95_s": float(np.percentile(dt, 95)), "p99_s": float(np.percentile(dt, 99)),
                    "max_s": int(dt.max()), "median_positive_s": float(np.median(pos)) if pos.size else None})
        for lo, hi, name in STEP_CLASSES:
            sel = (dt >= lo) & (dt <= hi)
            out[f"n_{name}"] = int(sel.sum())
            out[f"share_{name}"] = round(float(sel.mean()), 6)
    return out


def bucket_counts(dt: np.ndarray, buckets=GAP_BUCKETS) -> list[dict]:
    out = []
    for lo, hi, name in buckets:
        sel = (dt >= lo) & (dt <= hi)
        out.append({"bucket": name, "lo_s": lo, "hi_s": hi, "count": int(sel.sum()),
                    "share": round(float(sel.mean()), 8) if dt.size else None,
                    "total_hours": round(float(dt[sel].sum()) / 3600, 3)})
    return out


def ecdf_points(dt: np.ndarray, grid_s: Sequence[int]) -> list[dict]:
    """Share of steps <= x for a grid of x (for plots and tables)."""
    s = np.sort(dt)
    return [{"x_s": int(x), "ecdf": round(float(np.searchsorted(s, x, "right") / s.size), 8) if s.size else None}
            for x in grid_s]


# ---------------------------------------------------------------------------------------------
# Upload-chunk alignment
# ---------------------------------------------------------------------------------------------

def chunk_alignment(dt: np.ndarray, tol_s: int = 10, chunk_s: int = UPLOAD_CHUNK_S, min_s: int = 1500) -> dict:
    """Whether a gap equals n x chunk + a few seconds (n >= 1): the signature of lost upload chunks."""
    dt = np.asarray(dt)
    n = np.floor((dt + chunk_s / 2) / chunk_s).astype(np.int64)
    resid = dt - n * chunk_s
    aligned = (dt >= min_s) & (n >= 1) & (resid >= -tol_s) & (resid <= tol_s)
    return {"n_chunks": n, "residual_s": resid, "aligned": aligned}


def chance_alignment_rate(tol_s: int = 10, chunk_s: int = UPLOAD_CHUNK_S) -> float:
    """Share of uniformly placed gaps expected to look chunk-aligned by coincidence."""
    return (2 * tol_s + 1) / chunk_s


# ---------------------------------------------------------------------------------------------
# Candidate sessions (descriptive; never final)
# ---------------------------------------------------------------------------------------------

def split_points(dt: np.ndarray, threshold_s: int, bridge: np.ndarray | None = None) -> np.ndarray:
    """Indices i where a new candidate session starts at row i+1 (step dt[i] > threshold, unless bridged)."""
    brk = dt > threshold_s
    if bridge is not None:
        brk &= ~bridge
    return np.flatnonzero(brk)


def candidate_sessions(tl: Timeline, threshold_s: int, bridge: np.ndarray | None = None) -> list[tuple[int, int]]:
    """(first, last) positions in the timeline of each candidate session."""
    if tl.n == 0:
        return []
    cuts = split_points(steps(tl), threshold_s, bridge)
    starts = np.concatenate([[0], cuts + 1])
    ends = np.concatenate([cuts, [tl.n - 1]])
    return list(zip(starts.tolist(), ends.tolist()))


def _noon_hours(sec: np.ndarray) -> np.ndarray:
    """Clock time as hours since 12:00 (keeps a night 20:00-06:00 contiguous: 8..18)."""
    return ((sec % DAY_S) / 3600.0 - 12.0) % 24.0


def _clock(noon_h: float) -> float:
    return round((noon_h + 12.0) % 24.0, 2)


def session_rows(src: SourceData, tl: Timeline, sessions: list[tuple[int, int]]) -> list[dict]:
    out = []
    for k, (a, b) in enumerate(sessions):
        t0, t1 = int(tl.ts[a]), int(tl.ts[b])
        rows = tl.rows[a:b + 1]
        mid = t0 + (t1 - t0) / 2
        out.append({
            "candidate": k, "start_ts": t0, "end_ts": t1, "duration_h": round((t1 - t0) / 3600, 4),
            "rows": int(b - a + 1), "start_hour": round((t0 % DAY_S) / 3600, 2), "end_hour": round((t1 % DAY_S) / 3600, 2),
            "midpoint_hour": round((mid % DAY_S) / 3600, 2),
            "crosses_midnight": bool(t0 // DAY_S != t1 // DAY_S),
            "calendar_dates": int(t1 // DAY_S - t0 // DAY_S + 1),
            "files": int(np.unique(src.file_idx[rows]).size),
        })
    return out


def session_stats(rows: list[dict], n_nights: int) -> dict:
    if not rows:
        return {"sessions": 0}
    d = np.array([r["duration_h"] for r in rows])
    n = np.array([r["rows"] for r in rows])
    starts = np.array([r["start_ts"] for r in rows])
    ends = np.array([r["end_ts"] for r in rows])
    sh, eh = _noon_hours(starts), _noon_hours(ends)
    return {
        "sessions": len(rows), "median_duration_h": round(float(np.median(d)), 3), "mean_duration_h": round(float(d.mean()), 3),
        "p10_duration_h": round(float(np.percentile(d, 10)), 3), "p90_duration_h": round(float(np.percentile(d, 90)), 3),
        "min_duration_h": round(float(d.min()), 4), "max_duration_h": round(float(d.max()), 3),
        "median_rows": float(np.median(n)), "sessions_per_recording_night": round(len(rows) / n_nights, 3) if n_nights else None,
        "sessions_lt_10min": int((d < 1 / 6).sum()), "sessions_gt_16h": int((d > 16).sum()),
        "crossing_midnight": int(sum(r["crosses_midnight"] for r in rows)),
        "spanning_multiple_files": int(sum(r["files"] > 1 for r in rows)),
        "start_hour_p10": _clock(float(np.percentile(sh, 10))), "start_hour_p50": _clock(float(np.median(sh))),
        "start_hour_p90": _clock(float(np.percentile(sh, 90))), "end_hour_p10": _clock(float(np.percentile(eh, 10))),
        "end_hour_p50": _clock(float(np.median(eh))), "end_hour_p90": _clock(float(np.percentile(eh, 90))),
    }


def recording_nights(ts: np.ndarray) -> int:
    """Noon-to-noon nights with data (a night is not assumed to be a session)."""
    return int(np.unique((ts - DAY_S // 2) // DAY_S).size)


def files_with_multiple_sessions(src: SourceData, tl: Timeline, sessions: list[tuple[int, int]]) -> int:
    sid = np.empty(tl.n, np.int64)
    for k, (a, b) in enumerate(sessions):
        sid[a:b + 1] = k
    f = src.file_idx[tl.rows]
    pairs = np.unique(np.stack([f, sid], axis=1), axis=0)
    _, per_file = np.unique(pairs[:, 0], return_counts=True)
    return int((per_file > 1).sum())


# ---------------------------------------------------------------------------------------------
# Gap context
# ---------------------------------------------------------------------------------------------

def _side(src: SourceData, rows: np.ndarray) -> dict:
    v = src.values[rows].astype(np.int64)
    p = v[:, :6].sum(axis=1)
    t, h = v[:, 6], v[:, 7]
    ok = (t > 0) & (h > 0)
    fw = src.firmware_absent[rows] if src.firmware_absent is not None else np.full(rows.size, -1)
    return {"pressure_sum_mean": round(float(p.mean()), 1), "share_nonzero_pressure": round(float((p > 0).mean()), 3),
            "share_nm_label": round(float((fw == 1).mean()), 3),
            "temp": float(np.median(t[ok])) if ok.any() else None, "humid": float(np.median(h[ok])) if ok.any() else None}


def gap_context(src: SourceData, tl: Timeline, dt: np.ndarray, min_gap_s: int, near_block: np.ndarray | None = None,
                context_rows: int = 5) -> list[dict]:
    """One record per step longer than min_gap_s, describing both sides of the gap."""
    out = []
    ca = chunk_alignment(dt)
    for i in np.flatnonzero(dt > min_gap_s):
        rb, ra = tl.rows[i], tl.rows[i + 1]
        before = tl.rows[max(0, i - context_rows + 1):i + 1]
        after = tl.rows[i + 1:i + 1 + context_rows]
        sb, sa = _side(src, before), _side(src, after)
        ev = src.event_code
        out.append({
            "ts_before": int(tl.ts[i]), "ts_after": int(tl.ts[i + 1]), "gap_s": int(dt[i]),
            "hour_before": round((int(tl.ts[i]) % DAY_S) / 3600, 2), "hour_after": round((int(tl.ts[i + 1]) % DAY_S) / 3600, 2),
            "crosses_midnight": bool(tl.ts[i] // DAY_S != tl.ts[i + 1] // DAY_S),
            "file_before": src.files[int(src.file_idx[rb])], "file_after": src.files[int(src.file_idx[ra])],
            "file_boundary": bool(src.file_idx[rb] != src.file_idx[ra]),
            "adjacent_to_repeated_block": bool(near_block is not None and (near_block[rb] or near_block[ra])),
            "chunk_aligned": bool(ca["aligned"][i]), "n_chunks": int(ca["n_chunks"][i]),
            "chunk_residual_s": int(ca["residual_s"][i]),
            "event_before": (code_text(int(ev[rb])) or "") if ev is not None else "",
            "event_after": (code_text(int(ev[ra])) or "") if ev is not None else "",
            **{f"before_{k}": v for k, v in sb.items()}, **{f"after_{k}": v for k, v in sa.items()},
        })
    return out
