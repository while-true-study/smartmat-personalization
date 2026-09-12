"""Sensor phase / change-point audit (P0 analysis A10). Read-only and descriptive.

Summarises pressure, target, sampling and activity statistics per time unit (candidate session,
recording night, calendar day), ranks abrupt changes between consecutive units, and quantifies
pre/post distribution shift with effect sizes (no p-values). Nothing here modifies, clips,
normalises, rescales, resamples or removes values; a sensor phase is a provenance label only.

Conventions
  loaded row      all six channels present and at least one > 0 (the mat is occupied); per-channel
                  statistics, the pressure sum and the active-channel count use loaded rows only
  4095            candidate upper bound of the 12-bit range; "upper-bound accumulation consistent with
                  clipping/saturation", never asserted as saturation
  split k         the boundary between unit k-1 and unit k of a time-ordered unit series
  d_w(k)          (median of the w units after k - median of the w units before k) / noise scale, with the
                  noise scale estimated robustly from adjacent-unit differences (a step is one outlier among
                  them, so it barely inflates the scale)
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

N_CH = 6
UPPER_BOUND = 4095
DAY_S = 86400
WINDOWS = (1, 3, 7, 14)
CORE_METRICS = ("pressure_sum_median", "pressure_sum_p95", "rows_4095_ratio", "active_channels_mean")
MOVES = ("up", "down", "left", "right", "absent")          # firmware movement labels (codes 1..5)
STEP_SHARES = (0, 1, 2, 3, 4, 5)                            # exact step lengths reported as shares


# ---------------------------------------------------------------------------------------------
# Time units and phase labels
# ---------------------------------------------------------------------------------------------

def night_index(ts: np.ndarray) -> np.ndarray:
    """Noon-to-noon recording night (the night 22:00-06:00 belongs to the evening's date)."""
    return (np.asarray(ts) - DAY_S // 2) // DAY_S


def day_index(ts: np.ndarray) -> np.ndarray:
    return np.asarray(ts) // DAY_S


def contiguous_units(labels: np.ndarray) -> list[tuple[int, int, int]]:
    """(label, first, last) for runs of equal labels in a time-ordered label array."""
    labels = np.asarray(labels)
    if labels.size == 0:
        return []
    cut = np.flatnonzero(labels[1:] != labels[:-1]) + 1
    starts = np.concatenate([[0], cut])
    ends = np.concatenate([cut - 1, [labels.size - 1]])
    return [(int(labels[a]), int(a), int(b)) for a, b in zip(starts, ends)]


def assign_phase(ts: np.ndarray, boundaries: Sequence[tuple[int, int]], names: Sequence[str]) -> np.ndarray:
    """Phase label per row from boundary intervals (last_ts_before, first_ts_after), in time order.

    A row at or before `last_ts_before` of boundary i belongs to phase i; at or after `first_ts_after`
    to phase i+1. A row strictly inside a boundary interval gets '' (undetermined). Labels only.
    """
    if len(names) != len(boundaries) + 1:
        raise ValueError("need one more phase name than boundaries")
    ts = np.asarray(ts)
    out = np.full(ts.size, names[0], dtype=object)
    for i, (last_before, first_after) in enumerate(boundaries):
        if first_after <= last_before:
            raise ValueError("boundary interval must have first_after > last_before")
        out[ts >= first_after] = names[i + 1]
        out[(ts > last_before) & (ts < first_after)] = ""
    return out


# ---------------------------------------------------------------------------------------------
# Per-unit summary
# ---------------------------------------------------------------------------------------------

def _q(x: np.ndarray, q: float) -> float | None:
    return float(np.percentile(x, q)) if x.size else None


def step_regime(ts: np.ndarray, max_step_s: int = 60) -> dict:
    """Sampling regime from within-recording steps (0 < gap <= max_step_s kept; 0 s = same-second rows)."""
    dt = np.diff(np.asarray(ts))
    dt = dt[(dt >= 0) & (dt <= max_step_s)]
    out: dict = {"steps": int(dt.size)}
    if dt.size == 0:
        return out
    pos = dt[dt > 0]
    out["median_step_s"] = float(np.median(pos)) if pos.size else 0.0
    for s in STEP_SHARES:
        out[f"share_step_{s}s"] = round(float((dt == s).mean()), 5)
    out["share_step_6_60s"] = round(float((dt > 5).mean()), 5)
    out["step_p05_s"], out["step_p95_s"] = _q(pos, 5), _q(pos, 95)
    return out


def summarize_rows(ts: np.ndarray, p: np.ndarray, present: np.ndarray, temp: np.ndarray | None = None,
                   humid: np.ndarray | None = None, t_valid: np.ndarray | None = None,
                   h_valid: np.ndarray | None = None, move: np.ndarray | None = None) -> dict:
    """Statistics of one unit (rows in time order). p: n x 6 float (NaN where absent)."""
    n = int(ts.size)
    out: dict = {"start_ts": int(ts[0]), "end_ts": int(ts[-1]), "duration_h": round((int(ts[-1]) - int(ts[0])) / 3600, 4),
                 "rows": n, "start_hour": round((int(ts[0]) % DAY_S) / 3600, 2),
                 "end_hour": round((int(ts[-1]) % DAY_S) / 3600, 2)}
    full = present.all(axis=1)
    v = np.nan_to_num(p)
    pos = v > 0
    loaded = full & pos.any(axis=1)
    at_b = (v == UPPER_BOUND)
    n_b = at_b.sum(axis=1)
    out.update({"loaded_rows": int(loaded.sum()), "all_zero_ratio": round(float((full & ~pos.any(axis=1)).mean()), 5),
                "rows_4095_ratio": round(float((n_b > 0).mean()), 6), "rows_multi_4095_ratio": round(float((n_b > 1).mean()), 6)})
    q = v[loaded]
    if q.shape[0]:
        tot = q.sum(axis=1)
        act = (q > 0).sum(axis=1)
        out.update({"pressure_sum_median": float(np.median(tot)), "pressure_sum_p95": float(np.percentile(tot, 95)),
                    "active_channels_mean": round(float(act.mean()), 4), "active_channels_median": float(np.median(act))})
        for i in range(N_CH):
            c = q[:, i]
            out[f"p{i + 1}_median"] = float(np.median(c))
            out[f"p{i + 1}_p95"] = float(np.percentile(c, 95))
            out[f"p{i + 1}_zero_ratio"] = round(float((c == 0).mean()), 5)
            out[f"p{i + 1}_4095_ratio"] = round(float((c == UPPER_BOUND).mean()), 6)
    for name, x, ok in (("temp", temp, t_valid), ("humid", humid, h_valid)):
        if x is not None and ok is not None and ok.any():
            xv = x[ok]
            out[f"{name}_median"] = float(np.median(xv))
            out[f"{name}_iqr"] = float(np.percentile(xv, 75) - np.percentile(xv, 25))
            out[f"{name}_valid_share"] = round(float(ok.mean()), 5)
    out.update({f"sampling_{k}": val for k, val in step_regime(ts).items()})
    if move is not None:
        lab = move > 0
        out["movement_label_share"] = round(float(lab.mean()), 5)
        for j, m in enumerate(MOVES, 1):
            out[f"move_{m}_share"] = round(float((move[lab] == j).mean()), 5) if lab.any() else None
    out.update(activity_proxy(ts, v, loaded))
    return out


def activity_proxy(ts: np.ndarray, v: np.ndarray, loaded: np.ndarray, max_dt_s: int = 5) -> dict:
    """Changes per occupied hour of the dominant channel and of the set of active channels.

    Scale-free proxies of movement: they depend on which channels respond, not on their magnitude,
    but a more sensitive sensor still activates more channels (a limitation, reported as such).
    """
    dt = np.diff(ts)
    ok = (dt <= max_dt_s) & loaded[1:] & loaded[:-1]
    hours = float(dt[ok].sum()) / 3600.0
    if not ok.any() or hours <= 0:
        return {"occupied_hours": 0.0}
    dom = np.argmax(v, axis=1)
    act = v > 0
    sw = (dom[1:] != dom[:-1]) & ok
    chg = (act[1:] != act[:-1]).any(axis=1) & ok
    return {"occupied_hours": round(hours, 4), "dominant_switch_per_h": round(float(sw.sum()) / hours, 2),
            "active_set_change_per_h": round(float(chg.sum()) / hours, 2)}


# ---------------------------------------------------------------------------------------------
# Change-point ranking
# ---------------------------------------------------------------------------------------------

def noise_scale(x: np.ndarray) -> float:
    """Robust unit-to-unit noise: 1.4826 * MAD(adjacent differences) / sqrt(2); NaN if undefined."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 3:
        return float("nan")
    d = np.diff(x)
    s = 1.4826 * float(np.median(np.abs(d - np.median(d)))) / np.sqrt(2)
    if not s > 0:
        s = float(np.std(d)) / np.sqrt(2)
    return s if s > 0 else float("nan")


def split_scores(x: np.ndarray, w: int, scale: float | None = None) -> np.ndarray:
    """d_w(k) for every split k = 1..n-1 (index k; d[0] is NaN). Uses the finite units on each side."""
    x = np.asarray(x, float)
    s = noise_scale(x) if scale is None else scale
    out = np.full(x.size, np.nan)
    if not np.isfinite(s):
        return out
    for k in range(1, x.size):
        a = x[max(0, k - w):k]
        b = x[k:k + w]
        a, b = a[np.isfinite(a)], b[np.isfinite(b)]
        if a.size and b.size:
            out[k] = (np.median(b) - np.median(a)) / s
    return out


def step_vs_linear(x: np.ndarray, k: int, half: int = 14) -> dict:
    """Variance explained around split k by a one-step model vs a straight line (same window).

    A step gives r2_step clearly above r2_linear; a gradual drift gives r2_linear >= r2_step.
    """
    lo = max(0, k - half)
    seg = np.asarray(x[lo:k + half], float)
    t = np.arange(seg.size, dtype=float)
    ok = np.isfinite(seg)
    kk = k - lo
    y, tt = seg[ok], t[ok]
    pre = ok[:kk].sum()
    if y.size < 4 or pre < 2 or y.size - pre < 2:
        return {"r2_step": None, "r2_linear": None, "window_units": int(y.size)}
    sst = float(((y - y.mean()) ** 2).sum())
    if sst == 0:
        return {"r2_step": 0.0, "r2_linear": 0.0, "window_units": int(y.size)}
    a, b = y[:pre], y[pre:]
    sse_step = float(((a - a.mean()) ** 2).sum() + ((b - b.mean()) ** 2).sum())
    coef = np.polyfit(tt, y, 1)
    sse_lin = float(((y - np.polyval(coef, tt)) ** 2).sum())
    return {"r2_step": round(1 - sse_step / sst, 4), "r2_linear": round(1 - sse_lin / sst, 4), "window_units": int(y.size)}


def rank_splits(series: dict[str, np.ndarray], windows: Sequence[int] = WINDOWS) -> dict[tuple[str, int], np.ndarray]:
    """|d_w| ranks (1 = strongest) per (metric, window); NaN scores rank last."""
    ranks = {}
    for name, x in series.items():
        for w in windows:
            d = np.abs(split_scores(x, w))
            d[0] = np.nan
            order = np.argsort(-np.nan_to_num(d, nan=-1.0), kind="stable")
            r = np.empty(d.size)
            r[order] = np.arange(1, d.size + 1)
            ranks[(name, w)] = r
    return ranks


def distinct_peaks(score: np.ndarray, radius: int, top: int = 5) -> list[int]:
    """Indices of the strongest splits (higher score = stronger), keeping only one per event.

    A window of w units sees the same step from every split within w units of it; after taking the
    strongest split, all splits within `radius` of it are suppressed (non-maximum suppression).
    """
    s = np.asarray(score, float)
    order = np.argsort(-np.nan_to_num(s, nan=-np.inf), kind="stable")
    taken: list[int] = []
    for k in order:
        if not np.isfinite(s[k]):
            break
        if all(abs(int(k) - t) > radius for t in taken):
            taken.append(int(k))
            if len(taken) == top:
                break
    return taken


def event_rank(peaks: list[int], k: int, radius: int) -> int | None:
    """1-based position of the first peak within `radius` of split k, or None if no peak is near it."""
    for r, p in enumerate(peaks, 1):
        if abs(p - k) <= radius:
            return r
    return None


def consensus(ranks: dict[tuple[str, int], np.ndarray], metrics: Sequence[str], w: int, top: int = 3) -> dict[str, np.ndarray]:
    """Mean rank across metrics at window w, and how many metrics put a split in their top `top`."""
    m = np.vstack([ranks[(name, w)] for name in metrics])
    return {"mean_rank": m.mean(axis=0), "top_count": (m <= top).sum(axis=0)}


# ---------------------------------------------------------------------------------------------
# Effect sizes
# ---------------------------------------------------------------------------------------------

def int_distribution_shift(a: np.ndarray, b: np.ndarray) -> dict:
    """Exact 1-Wasserstein distance and KS statistic between two integer-valued samples."""
    a = np.asarray(a).astype(np.int64)
    b = np.asarray(b).astype(np.int64)
    if a.size == 0 or b.size == 0:
        return {"wasserstein": None, "ks": None}
    lo, hi = int(min(a.min(), b.min())), int(max(a.max(), b.max()))
    ca = np.cumsum(np.bincount(a - lo, minlength=hi - lo + 1)) / a.size
    cb = np.cumsum(np.bincount(b - lo, minlength=hi - lo + 1)) / b.size
    diff = np.abs(ca - cb)
    return {"wasserstein": round(float(diff[:-1].sum()), 3), "ks": round(float(diff.max()), 4)}


def robust_std_diff(a: np.ndarray, b: np.ndarray) -> float | None:
    """(median b - median a) / pooled robust SD (IQR / 1.349); None when both spreads are 0."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if a.size < 2 or b.size < 2:
        return None
    sa = (np.percentile(a, 75) - np.percentile(a, 25)) / 1.349
    sb = (np.percentile(b, 75) - np.percentile(b, 25)) / 1.349
    s = float(np.sqrt((sa ** 2 + sb ** 2) / 2))
    return round(float((np.median(b) - np.median(a)) / s), 3) if s > 0 else None


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float | None:
    """P(b > a) - P(b < a) over all pairs (unit-level effect size; +1 = every b above every a)."""
    a, b = np.sort(np.asarray(a, float)[np.isfinite(a)]), np.asarray(b, float)
    b = b[np.isfinite(b)]
    if a.size == 0 or b.size == 0:
        return None
    below = np.searchsorted(a, b, side="left")           # a < b_j
    above = a.size - np.searchsorted(a, b, side="right")  # a > b_j
    return round(float((below.sum() - above.sum()) / (a.size * b.size)), 4)


def compare_units(before: Sequence[dict], after: Sequence[dict], metrics: Sequence[str]) -> list[dict]:
    """Unit-level pre/post comparison (the unit, not the row, is the analysis unit)."""
    out = []
    for m in metrics:
        a = np.array([u.get(m) for u in before if u.get(m) is not None], float)
        b = np.array([u.get(m) for u in after if u.get(m) is not None], float)
        row = {"metric": m, "units_before": int(a.size), "units_after": int(b.size)}
        if a.size and b.size:
            ma, mb = float(np.median(a)), float(np.median(b))
            row.update({"median_before": round(ma, 4), "median_after": round(mb, 4), "diff": round(mb - ma, 4),
                        "rel_change": round((mb - ma) / abs(ma), 4) if ma else None,
                        "min_before": round(float(a.min()), 4), "max_before": round(float(a.max()), 4),
                        "min_after": round(float(b.min()), 4), "max_after": round(float(b.max()), 4),
                        "robust_std_diff": robust_std_diff(a, b), "cliffs_delta": cliffs_delta(a, b)})
        out.append(row)
    return out


# ---------------------------------------------------------------------------------------------
# Channel and upper-bound detail
# ---------------------------------------------------------------------------------------------

def channel_profile(p: np.ndarray, present: np.ndarray) -> list[dict]:
    """Per-channel statistics on loaded rows: level, spread, zeros, upper bound, contact and contribution."""
    v = np.nan_to_num(p)
    loaded = present.all(axis=1) & (v > 0).any(axis=1)
    q = v[loaded]
    if q.shape[0] == 0:
        return []
    share = q.sum(axis=0) / q.sum()
    out = []
    for i in range(N_CH):
        c = q[:, i]
        act = c[c > 0]
        out.append({
            "channel": f"p{i + 1}", "loaded_rows": int(c.size), "median": float(np.median(c)),
            "q25": float(np.percentile(c, 25)), "q75": float(np.percentile(c, 75)),
            "iqr": float(np.percentile(c, 75) - np.percentile(c, 25)), "p95": float(np.percentile(c, 95)),
            "zero_ratio": round(float((c == 0).mean()), 5), "active_ratio": round(float((c > 0).mean()), 5),
            "ratio_4095": round(float((c == UPPER_BOUND).mean()), 6),
            "median_when_active": float(np.median(act)) if act.size else None,
            "p95_when_active": float(np.percentile(act, 95)) if act.size else None,
            "mass_share": round(float(share[i]), 4),
        })
    return out


def upper_bound_profile(p: np.ndarray, present: np.ndarray, below: int = 10) -> dict:
    """Simultaneous-channel counts at 4095 and accumulation at the bound vs the values just below it."""
    v = np.nan_to_num(p)
    n_b = (v == UPPER_BOUND).sum(axis=1)
    vals = v[present]
    near = ((vals >= UPPER_BOUND - below) & (vals < UPPER_BOUND)).sum()
    at = int((vals == UPPER_BOUND).sum())
    out = {"rows": int(v.shape[0]), "cells_4095": at, "cells_4085_4094": int(near),
           "accumulation_ratio": round(at / (near / below), 2) if near else None}
    for k in range(0, 4):
        out[f"rows_{k}_channels_4095"] = int((n_b == k).sum())
    out["rows_4plus_channels_4095"] = int((n_b >= 4).sum())
    return out
