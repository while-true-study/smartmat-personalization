"""P1 domain-shift EDA: domain slices, descriptors, distribution summaries and distances (descriptive only).

Input is canonical_v1 (src/evaluation/canonical_input.py). Nothing here resamples, interpolates, normalises,
clips, windows, splits, selects features or fits a model. Rows are never removed; invalid targets are left out
of target statistics only, and their prevalence is reported.

Definitions used in the P1 report
  loaded row          all six channels valid and at least one > 0 (occupied mat)
  night               noon-to-noon recording night of the naive local timestamp (derived for EDA only)
  unit                a night within one domain slice; unit-level statistics use per-night medians
  W1                  1-Wasserstein distance of the row-level distributions (exact for integer variables)
  W1/IQR              W1 divided by the pooled IQR, sqrt((IQR_a^2 + IQR_b^2) / 2)
  RSD                 robust standardised difference: (median_b - median_a) / sqrt(((IQR_a/1.349)^2 + (IQR_b/1.349)^2) / 2)
  Cliff's delta       P(b > a) - P(b < a) over all pairs of units (nights); +1 = every night of b above every night of a
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from src.data.sensor_phase import cliffs_delta, int_distribution_shift, robust_std_diff

N_CH = 6
UPPER_BOUND = 4095
DAY_S = 86400

# main domain slices (canonical values; D-019, D-022, D-027), in reporting order
MAIN_SLICES = ("User01/s1", "User01/s2", "User02/22480", "User02/22482/normal", "User02/22482/p1_shift", "User07")
MINOR_SLICES = ("User02/22482/p1_transition",)          # reported, not used in main comparisons
POOLED = ("User01 (pooled)", "User02 (pooled)", "User07 (pooled)", "User02/22482 (all phases)")
WITHIN_PAIRS = (("User01/s1", "User01/s2"), ("User02/22480", "User02/22482/normal"),
                ("User02/22482/normal", "User02/22482/p1_shift"))
POOLED_PAIRS = (("User01 (pooled)", "User07 (pooled)"), ("User01 (pooled)", "User02 (pooled)"),
                ("User07 (pooled)", "User02 (pooled)"))
# firmware movement labels (same vocabulary as the P0 parser; inventory §6)
MOVEMENT_TOKENS = {"UM": "up", "DM": "down", "RM": "right", "LM": "left", "NM": "absent",
                   "위로이동": "up", "아래로이동": "down", "우로이동": "right", "좌로이동": "left", "자리비움": "absent"}


# ---------------------------------------------------------------------------------------------
# Slicing
# ---------------------------------------------------------------------------------------------

def assign_slices(subject: np.ndarray, device: np.ndarray, sensor_phase: np.ndarray,
                  cq_phase: np.ndarray) -> np.ndarray:
    """Main/minor domain slice of each row; '' for rows outside the primary cohort."""
    subject, device = np.asarray(subject, object), np.asarray(device, object)
    sensor_phase, cq_phase = np.asarray(sensor_phase, object), np.asarray(cq_phase, object)
    out = np.full(subject.size, "", dtype=object)
    u01 = subject == "User01"
    out[u01 & (sensor_phase == "s1")] = "User01/s1"
    out[u01 & (sensor_phase == "s2")] = "User01/s2"
    u02 = subject == "User02"
    out[u02 & (device == "22480")] = "User02/22480"
    d82 = u02 & (device == "22482")
    out[d82 & (cq_phase == "normal")] = "User02/22482/normal"
    out[d82 & (cq_phase == "p1_response_shift")] = "User02/22482/p1_shift"
    out[d82 & (cq_phase == "p1_transition")] = "User02/22482/p1_transition"
    out[subject == "User07"] = "User07"
    return out


def pooled_masks(subject: np.ndarray, device: np.ndarray) -> dict[str, np.ndarray]:
    """Secondary pooled groupings (descriptive only; pooled User02 contains two concurrent mats)."""
    subject, device = np.asarray(subject, object), np.asarray(device, object)
    return {"User01 (pooled)": subject == "User01", "User02 (pooled)": subject == "User02",
            "User07 (pooled)": subject == "User07",
            "User02/22482 (all phases)": (subject == "User02") & (device == "22482")}


def night_index(ts: np.ndarray) -> np.ndarray:
    return (np.asarray(ts, np.int64) - DAY_S // 2) // DAY_S


# ---------------------------------------------------------------------------------------------
# Row descriptors
# ---------------------------------------------------------------------------------------------

@dataclass
class PressureDescriptors:
    total: np.ndarray        # pressure_sum
    mean: np.ndarray
    std: np.ndarray          # across the six channels of a row
    active: np.ndarray       # channels > 0
    all_zero: np.ndarray
    upper: np.ndarray        # channels at 4095
    loaded: np.ndarray       # valid and at least one channel > 0
    dominant: np.ndarray     # 0..5, -1 if not loaded


def pressure_descriptors(p: np.ndarray, valid: np.ndarray) -> PressureDescriptors:
    q = np.where(valid[:, None], p, 0).astype(np.int64)
    total = q.sum(axis=1)
    active = (q > 0).sum(axis=1)
    loaded = valid & (active > 0)
    dominant = np.where(loaded, np.argmax(q, axis=1), -1)
    return PressureDescriptors(total=total, mean=total / N_CH, std=q.std(axis=1), active=active,
                               all_zero=valid & (active == 0), upper=(q == UPPER_BOUND).sum(axis=1),
                               loaded=loaded, dominant=dominant)


def channel_shares(p: np.ndarray, loaded: np.ndarray) -> np.ndarray:
    """Per-row channel contribution to the pressure sum (loaded rows only; NaN elsewhere)."""
    q = p.astype(np.float64)
    tot = q.sum(axis=1)
    out = np.full(q.shape, np.nan)
    out[loaded] = q[loaded] / tot[loaded, None]
    return out


# ---------------------------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------------------------

def summarize(x: np.ndarray) -> dict:
    x = np.asarray(x, np.float64)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"n": 0}
    q05, q25, q50, q75, q95 = np.percentile(x, [5, 25, 50, 75, 95])
    return {"n": int(x.size), "mean": round(float(x.mean()), 4), "std": round(float(x.std()), 4),
            "median": float(q50), "q25": float(q25), "q75": float(q75), "iqr": float(q75 - q25),
            "p05": float(q05), "p95": float(q95), "min": float(x.min()), "max": float(x.max()),
            "zero_ratio": round(float((x == 0).mean()), 5)}


def value_distribution(x: np.ndarray, top: int = 5) -> dict:
    """Unique values and the most frequent ones with their shares (integer targets)."""
    x = np.asarray(x)
    x = x[np.isfinite(x)] if x.dtype.kind == "f" else x
    if x.size == 0:
        return {"n_unique": 0, "top_values": ""}
    vals, cnt = np.unique(x, return_counts=True)
    order = np.argsort(-cnt, kind="stable")[:top]
    return {"n_unique": int(vals.size),
            "top_values": "; ".join(f"{vals[i]:g}:{cnt[i] / x.size:.3f}" for i in order)}


def unit_stat(values: np.ndarray, units: np.ndarray, fn=np.median) -> tuple[np.ndarray, np.ndarray]:
    """Per-unit statistic (default median) over the given rows; returns (unit ids, values)."""
    values, units = np.asarray(values, np.float64), np.asarray(units)
    ok = np.isfinite(values)
    values, units = values[ok], units[ok]
    if values.size == 0:
        return np.array([], units.dtype), np.array([])
    order = np.argsort(units, kind="stable")
    u, start = np.unique(units[order], return_index=True)
    parts = np.split(values[order], start[1:])
    return u, np.array([fn(p) for p in parts], np.float64)


def iqr(x: np.ndarray) -> float:
    return float(np.percentile(x, 75) - np.percentile(x, 25)) if len(x) else float("nan")


# ---------------------------------------------------------------------------------------------
# Distances between two domains
# ---------------------------------------------------------------------------------------------

def distance(a: np.ndarray, b: np.ndarray, a_units: np.ndarray, b_units: np.ndarray) -> dict:
    """Row-level distribution distance and unit-level (night) effect sizes for one variable.

    a, b: row values (finite rows only are used); a_units, b_units: unit id of each row.
    """
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    fa, fb = np.isfinite(a), np.isfinite(b)
    a_units, b_units = np.asarray(a_units)[fa], np.asarray(b_units)[fb]
    a, b = a[fa], b[fb]
    out: dict = {"rows_a": int(a.size), "rows_b": int(b.size)}
    if a.size == 0 or b.size == 0:
        return out
    integer = bool(np.all(a == np.round(a)) and np.all(b == np.round(b)))
    if integer:
        sh = int_distribution_shift(a.astype(np.int64), b.astype(np.int64))
    else:
        grid = np.linspace(0, 1, 1001)
        qa, qb = np.quantile(a, grid), np.quantile(b, grid)
        allv = np.sort(np.concatenate([a, b]))
        ks = np.max(np.abs(np.searchsorted(np.sort(a), allv, "right") / a.size - np.searchsorted(np.sort(b), allv, "right") / b.size))
        sh = {"wasserstein": round(float(np.mean(np.abs(qa - qb))), 4), "ks": round(float(ks), 4)}
    pooled = float(np.sqrt((iqr(a) ** 2 + iqr(b) ** 2) / 2))
    ua, va = unit_stat(a, a_units)
    ub, vb = unit_stat(b, b_units)
    out.update({"w1": sh["wasserstein"], "ks": sh["ks"],
                "w1_over_pooled_iqr": round(sh["wasserstein"] / pooled, 4) if pooled > 0 else None,
                "median_a": float(np.median(a)), "median_b": float(np.median(b)),
                "rsd_rows": robust_std_diff(a, b),
                "units_a": int(ua.size), "units_b": int(ub.size),
                "unit_median_a": float(np.median(va)) if va.size else None,
                "unit_median_b": float(np.median(vb)) if vb.size else None,
                "cliffs_delta_units": cliffs_delta(va, vb) if va.size and vb.size else None,
                "rsd_units": robust_std_diff(va, vb) if va.size > 1 and vb.size > 1 else None})
    return out


# ---------------------------------------------------------------------------------------------
# Time of night, events, relationships
# ---------------------------------------------------------------------------------------------

def hour_of_day(ts: np.ndarray) -> np.ndarray:
    """Clock hour of the naive local timestamp (no timezone conversion; timezone_status local_unspecified)."""
    return (np.asarray(ts, np.int64) % DAY_S) // 3600


def hours_since_session_start(ts: np.ndarray, session: np.ndarray) -> np.ndarray:
    """Hours since the first row of the row's canonical session (sessions are D-024 labels)."""
    ts, session = np.asarray(ts, np.int64), np.asarray(session)
    _, inv = np.unique(session, return_inverse=True)
    start = np.full(inv.max() + 1 if inv.size else 0, np.iinfo(np.int64).max, np.int64)
    np.minimum.at(start, inv, ts)
    return (ts - start[inv]) / 3600.0


def parse_event(text: str) -> tuple[str, tuple[str, ...]]:
    """(movement label or '', control codes) of one canonical event_raw string.

    The last token is a movement label if it is in the firmware vocabulary; every other token is a control code
    (the part before ':' for 'EVENT:NAME'-style tokens is kept whole). Nothing about heater state is inferred.
    """
    tokens = str(text).split()
    move = ""
    if tokens and tokens[-1] in MOVEMENT_TOKENS:
        move = MOVEMENT_TOKENS[tokens[-1]]
        tokens = tokens[:-1]
    return move, tuple(t for t in tokens if t)


def event_vocabulary(events: Sequence[str], counts: Sequence[int]) -> dict[str, Counter]:
    """Occurrence counts of movement labels and control codes over unique event strings with counts."""
    mv, ctl = Counter(), Counter()
    for e, n in zip(events, counts):
        m, cs = parse_event(e)
        mv[m or "(none)"] += n
        for c in cs:
            ctl[c] += n
    return {"movement": mv, "control": ctl}


def event_trajectory(ts: np.ndarray, y: np.ndarray, valid: np.ndarray, stream: np.ndarray, event_rows: np.ndarray,
                     offsets_s: Sequence[int], tol_s: int = 30) -> dict[int, np.ndarray]:
    """For each offset: y(t_event + offset) - y(t_event) per event, using the nearest valid row of the same
    stream within tol_s (NaN if none). Event-conditioned only: no state between events is reconstructed.
    ts must be sorted within each stream; rows of different streams never mix."""
    out = {o: np.full(event_rows.size, np.nan) for o in offsets_s}
    order = np.lexsort((ts, stream))
    ts_o, y_o, v_o, s_o = ts[order], y[order], valid[order], stream[order]
    pos = np.empty(order.size, np.int64)
    pos[order] = np.arange(order.size)
    for k, r in enumerate(event_rows):
        i = pos[r]
        if not v_o[i]:
            continue
        s = s_o[i]
        lo, hi = np.searchsorted(s_o, s, "left"), np.searchsorted(s_o, s, "right")
        tt, yy, vv = ts_o[lo:hi], y_o[lo:hi], v_o[lo:hi]
        for o in offsets_s:
            j = np.searchsorted(tt, ts_o[i] + o)
            cand = [c for c in (j - 1, j) if 0 <= c < tt.size and abs(tt[c] - (ts_o[i] + o)) <= tol_s and vv[c]]
            if cand:
                c = min(cand, key=lambda c: abs(tt[c] - (ts_o[i] + o)))
                out[o][k] = yy[c] - y_o[i]
    return out


def average_ranks(x: np.ndarray) -> np.ndarray:
    vals, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    ends = np.cumsum(cnt)
    starts = ends - cnt
    return ((starts + ends - 1) / 2.0)[inv]


def spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 3:
        return None
    rx, ry = average_ranks(x), average_ranks(y)
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return None
    return round(float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy)), 4)


def binned_trend(x: np.ndarray, y: np.ndarray, n_bins: int = 10) -> list[dict]:
    """Median y per quantile bin of x (bin edges from the x distribution of the same domain)."""
    x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size == 0:
        return []
    edges = np.unique(np.quantile(x, np.linspace(0, 1, n_bins + 1)))
    idx = np.clip(np.searchsorted(edges, x, "right") - 1, 0, max(edges.size - 2, 0))
    out = []
    for b in range(max(edges.size - 1, 1)):
        m = idx == b
        if m.any():
            out.append({"bin": b, "x_low": float(edges[b]), "x_high": float(edges[min(b + 1, edges.size - 1)]),
                        "n": int(m.sum()), "x_median": float(np.median(x[m])), "y_median": float(np.median(y[m]))})
    return out
