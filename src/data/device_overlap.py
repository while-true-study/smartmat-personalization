"""Same-subject multi-device overlap analysis (P0 analysis A2). Read-only and descriptive.

Scope: how two devices of one subject (User02: 22480, 22482) record in time, and how their
pressure, occupancy and temperature/humidity relate.

Guarantees:
- Device streams are never merged, resampled, interpolated or written. Cross-device
  comparisons pair *existing* rows by nearest timestamp within a tolerance; no value is created.
- The per-device *analysis view* sorts rows by time and counts identical repeated rows (same
  timestamp and values, e.g. repeated across adjacent daily files) once. This is an in-memory
  view for these statistics only, not the P0 de-duplication policy (OPEN-07).
- Identity comes from configs/subject_mapping.yaml; a device ID is never a subject ID, and all
  devices of one subject share one evaluation group.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from src.data.provenance import MISSING, SourceData
from src.data.subject_mapping import device_subject_map, subject_for_device, subject_ids

DAY_S = 86400


# ---------------------------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------------------------

def validate_identity(stream: SourceData) -> None:
    """Refuse streams whose subject is unknown, is a device ID, or does not own the device."""
    devices = device_subject_map()
    if stream.subject_id in devices:
        raise ValueError(f"{stream.source_id}: device ID {stream.subject_id!r} used as subject_id")
    if stream.subject_id not in subject_ids():
        raise ValueError(f"{stream.source_id}: unknown subject {stream.subject_id!r}")
    for dev in str(stream.device_id).split("|"):
        if dev in devices and subject_for_device(dev) != stream.subject_id:
            raise ValueError(f"{stream.source_id}: device {dev} does not belong to {stream.subject_id}")


def evaluation_group(stream: SourceData) -> str:
    """Grouping key for any split: the subject, never the device (RESEARCH_PROTOCOL L8)."""
    validate_identity(stream)
    return stream.subject_id


def group_by_subject(streams: Iterable[SourceData]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for s in streams:
        groups.setdefault(evaluation_group(s), []).append(s.source_id)
    return groups


# ---------------------------------------------------------------------------------------------
# Analysis view and per-row descriptors
# ---------------------------------------------------------------------------------------------

@dataclass
class DeviceView:
    label: str
    source_id: str
    subject_id: str
    device_id: str
    n_files: int
    ts: np.ndarray           # int64, sorted, unique
    p: np.ndarray            # int16 (n, 6)
    temp: np.ndarray         # int16, MISSING if absent
    humid: np.ndarray        # int16, MISSING if absent
    fw_absent: np.ndarray    # int8: 1 absent (NM), 0 other movement label, -1 no label
    n_raw: int
    n_exact_duplicates: int  # identical rows counted once in the view
    n_conflicting_ts: int    # timestamps with >1 distinct row; first row in file order is kept

    @property
    def n(self) -> int:
        return int(self.ts.size)


def analysis_view(src: SourceData, label: str) -> DeviceView:
    validate_identity(src)
    n = src.n
    fw = src.firmware_absent if src.firmware_absent is not None else np.full(n, -1, np.int8)
    order = np.lexsort(tuple(src.values[:, j] for j in range(src.values.shape[1] - 1, -1, -1)) + (src.ts,))
    ts, vals, orig = src.ts[order], src.values[order], order
    same = np.zeros(n, bool)
    if n > 1:
        same[1:] = (ts[1:] == ts[:-1]) & (vals[1:] == vals[:-1]).all(axis=1)
    keep = ~same
    ts_k, orig_k = ts[keep], orig[keep]
    o2 = np.lexsort((orig_k, ts_k))                     # within a timestamp: earliest in file order first
    ts_k, orig_k = ts_k[o2], orig_k[o2]
    first = np.ones(ts_k.size, bool)
    if ts_k.size > 1:
        first[1:] = ts_k[1:] != ts_k[:-1]
    conflicting = int(np.unique(ts_k[~first]).size)
    sel = orig_k[first]
    return DeviceView(
        label=label, source_id=src.source_id, subject_id=src.subject_id, device_id=src.device_id,
        n_files=len(src.files), ts=src.ts[sel], p=src.values[sel, :6], temp=src.values[sel, 6],
        humid=src.values[sel, 7], fw_absent=fw[sel], n_raw=n, n_exact_duplicates=int(same.sum()),
        n_conflicting_ts=conflicting,
    )


def pressure_features(view: DeviceView, max_step_s: int = 5) -> dict[str, np.ndarray]:
    """Device-independent per-row summaries of P1–P6 (no cross-device combination)."""
    p = view.p.astype(np.float64)
    p[view.p == MISSING] = np.nan
    psum = p.sum(axis=1)
    change = np.full(view.n, np.nan)
    if view.n > 1:
        step = np.diff(view.ts)
        d = np.abs(np.diff(p, axis=0)).sum(axis=1)
        change[1:] = np.where(step <= max_step_s, d, np.nan)
    return {
        "pressure_sum": psum,
        "pressure_mean": psum / 6.0,
        "pressure_std": p.std(axis=1),
        "active_channels": (p > 0).sum(axis=1).astype(np.float64),
        "change_magnitude": change,
    }


def th_valid(view: DeviceView) -> np.ndarray:
    """Descriptive plausibility mask (excludes sentinel zeros and glitches); not a cleaning rule (OPEN-09)."""
    t, h = view.temp.astype(np.int32), view.humid.astype(np.int32)
    return (t > 0) & (t < 60) & (h > 0) & (h <= 100)


# ---------------------------------------------------------------------------------------------
# Temporal coverage (per-second grid over the analysis span)
# ---------------------------------------------------------------------------------------------

def coverage_mask(ts: np.ndarray, t0: int, n_sec: int, max_gap_s: int) -> np.ndarray:
    """Second s is covered if a row at t <= s < t + min(step to next row, max_gap_s) exists."""
    if ts.size == 0:
        return np.zeros(n_sec, bool)
    start = ts - t0
    step = np.diff(ts, append=ts[-1] + 1)
    end = np.minimum(start + np.minimum(step, max_gap_s), n_sec)
    diff = np.bincount(start, minlength=n_sec + 1)[: n_sec + 1] - np.bincount(end, minlength=n_sec + 1)[: n_sec + 1]
    return np.cumsum(diff[:n_sec]) > 0


def runs(mask: np.ndarray) -> np.ndarray:
    """(start, end) index pairs of True runs; end exclusive."""
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return np.stack([np.flatnonzero(d == 1), np.flatnonzero(d == -1)], axis=1)


def lookup(mask: np.ndarray, t0: int, t: np.ndarray) -> np.ndarray:
    idx = t - t0
    ok = (idx >= 0) & (idx < mask.size)
    out = np.zeros(t.size, bool)
    out[ok] = mask[idx[ok]]
    return out


def overlap_summary(mask_a: np.ndarray, mask_b: np.ndarray, min_run_s: int = 1800) -> dict:
    both, a, b = mask_a & mask_b, mask_a, mask_b
    union = a | b
    ra, rb = runs(a & ~b), runs(b & ~a)
    h = lambda m: float(m.sum()) / 3600.0  # noqa: E731
    return {
        "hours_a": h(a), "hours_b": h(b), "hours_both": h(both),
        "hours_only_a": h(a & ~b), "hours_only_b": h(b & ~a), "hours_union": h(union),
        "ratio_both_of_union": float(both.sum() / union.sum()) if union.any() else None,
        "ratio_both_of_a": float(both.sum() / a.sum()) if a.any() else None,
        "ratio_both_of_b": float(both.sum() / b.sum()) if b.any() else None,
        "n_only_a_periods_ge_30min": int(((ra[:, 1] - ra[:, 0]) >= min_run_s).sum()) if ra.size else 0,
        "n_only_b_periods_ge_30min": int(((rb[:, 1] - rb[:, 0]) >= min_run_s).sum()) if rb.size else 0,
    }


def interval_stats(ts: np.ndarray) -> dict:
    dt = np.diff(ts)
    out = {"n_steps": int(dt.size)}
    if dt.size:
        for q in (5, 25, 50, 75, 95, 99):
            out[f"dt_p{q:02d}_s"] = float(np.percentile(dt, q))
        for lo, hi, name in ((0, 1, "le1"), (2, 2, "2"), (3, 3, "3"), (4, 4, "4"), (5, 10, "5_10"),
                             (11, 60, "11_60"), (61, 600, "61_600"), (601, 10**12, "gt600")):
            out[f"share_dt_{name}_s"] = float(((dt >= lo) & (dt <= hi)).mean())
        for g in (10, 60, 300, 1800, 7200):
            sel = dt > g
            out[f"n_gaps_gt_{g}s"] = int(sel.sum())
        out["gap_hours_gt_60s"] = float(dt[dt > 60].sum() / 3600.0)
        out["max_gap_h"] = float(dt.max() / 3600.0)
    return out


# ---------------------------------------------------------------------------------------------
# Nearest-timestamp pairing (no interpolation)
# ---------------------------------------------------------------------------------------------

def nearest(ts_b: np.ndarray, targets: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Index of the nearest row of ts_b (sorted) for each target, and signed delta ts_b[j] - target."""
    if ts_b.size == 0:
        return np.full(targets.size, -1, np.int64), np.full(targets.size, np.inf)
    idx = np.searchsorted(ts_b, targets)
    lo, hi = np.clip(idx - 1, 0, ts_b.size - 1), np.clip(idx, 0, ts_b.size - 1)
    j = np.where(np.abs(ts_b[hi] - targets) < np.abs(targets - ts_b[lo]), hi, lo)
    return j, (ts_b[j] - targets).astype(np.float64)


def pair_rows(ts_a: np.ndarray, ts_b: np.ndarray, tol_s: float, lag_s: int = 0,
              rows_a: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Pairs (i, j) with |ts_b[j] - (ts_a[i] + lag)| <= tol. A row of b may pair with several rows of a."""
    ia = np.arange(ts_a.size) if rows_a is None else np.flatnonzero(rows_a)
    j, d = nearest(ts_b, ts_a[ia] + lag_s)
    ok = (j >= 0) & (np.abs(d) <= tol_s)
    return ia[ok], j[ok]


def alignment_sensitivity(ts_a: np.ndarray, ts_b: np.ndarray, rows_a: np.ndarray | None = None,
                          tolerances: Sequence[float] = (0, 1, 3)) -> dict:
    ia = np.arange(ts_a.size) if rows_a is None else np.flatnonzero(rows_a)
    _, d = nearest(ts_b, ts_a[ia])
    ad = np.abs(d)
    out = {"n_rows": int(ia.size)}
    for t in tolerances:
        out[f"share_within_{t:g}s"] = float((ad <= t).mean()) if ia.size else None
    if ia.size:
        for q in (50, 90, 99):
            out[f"abs_delta_p{q}_s"] = float(np.percentile(ad, q))
    return out


# ---------------------------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------------------------

def _rankdata(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    bounds = np.flatnonzero(np.concatenate([[True], xs[1:] != xs[:-1], [True]]))
    avg = (bounds[:-1] + bounds[1:] - 1) / 2.0 + 1.0
    ranks = np.empty(x.size)
    ranks[order] = np.repeat(avg, np.diff(bounds))
    return ranks


def pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return None
    x, y = x[m], y[m]
    sx, sy = x.std(), y.std()
    if sx == 0 or sy == 0:
        return None
    return float(((x - x.mean()) * (y - y.mean())).mean() / (sx * sy))


def spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return None
    return pearson(_rankdata(x[m]), _rankdata(y[m]))


def lagged_correlation(ts_a, xa, ts_b, xb, lags: Iterable[int], tol_s: float = 1.0,
                       rows_a: np.ndarray | None = None,
                       gate_a: np.ndarray | None = None, gate_b: np.ndarray | None = None) -> list[dict]:
    """Correlation of xa(t) with xb(t + lag) over nearest-timestamp pairs; optional gating per side."""
    out = []
    for lag in lags:
        ia, jb = pair_rows(ts_a, ts_b, tol_s, lag, rows_a)
        if gate_a is not None:
            keep = gate_a[ia] & gate_b[jb]
            ia, jb = ia[keep], jb[keep]
        out.append({"lag_s": int(lag), "n_pairs": int(ia.size),
                    "pearson": pearson(xa[ia], xb[jb]), "spearman": spearman(xa[ia], xb[jb])})
    return out


def occupancy_table(active_a: np.ndarray, active_b: np.ndarray) -> dict:
    n = active_a.size
    if n == 0:
        return {"n_pairs": 0}
    both = float((active_a & active_b).mean())
    oa, ob = float((active_a & ~active_b).mean()), float((~active_a & active_b).mean())
    nei = 1.0 - both - oa - ob
    pa, pb = both + oa, both + ob
    pe = pa * pb + (1 - pa) * (1 - pb)
    return {
        "n_pairs": int(n), "both": both, "only_a": oa, "only_b": ob, "neither": nei,
        "agreement": both + nei, "kappa": (both + nei - pe) / (1 - pe) if pe < 1 else None,
        "p_b_given_a": both / pa if pa else None, "p_a_given_b": both / pb if pb else None,
    }


def event_coincidence(ts_a, ev_a, ts_b, ev_b, window_s: int, rows_a: np.ndarray,
                      control_shift_s: int = DAY_S, cov_b=None, t0: int = 0) -> dict:
    """Share of a-events with a b-event within ±window, observed vs b shifted by ±control_shift."""
    tb = ts_b[ev_b]

    def hit_share(times):
        if times.size == 0 or tb.size == 0:
            return None, 0
        j, d = nearest(tb, times)
        return float((np.abs(d) <= window_s).mean()), int(times.size)

    ta = ts_a[ev_a & rows_a]
    obs, n_obs = hit_share(ta)
    ctrl = []
    for sh in (control_shift_s, -control_shift_s):
        shifted = ts_a[ev_a] + sh
        if cov_b is not None:
            shifted = shifted[lookup(cov_b, t0, shifted)]
        s, n = hit_share(shifted)
        if s is not None:
            ctrl.append((s, n))
    ctrl_share = (sum(s * n for s, n in ctrl) / sum(n for _, n in ctrl)) if ctrl else None
    return {"window_s": window_s, "n_events_a": n_obs, "observed_share": obs,
            "control_share": ctrl_share, "n_control_events": sum(n for _, n in ctrl),
            "lift": (obs / ctrl_share) if obs is not None and ctrl_share else None}


def event_lag_scan(ts_a, ev_a, ts_b, ev_b, lags: Iterable[int], window_s: int,
                   cov_b: np.ndarray, t0: int) -> list[dict]:
    """Share of a-events with a b-event within ±window at t + lag, for many lags.

    Only a-events whose shifted time falls inside b's coverage count, so the share is not
    diluted by periods where b did not record. A clock offset between devices would show up
    as a peak at a non-zero lag.
    """
    ta, tb = ts_a[ev_a], ts_b[ev_b]
    out = []
    for lag in lags:
        t = ta + lag
        t = t[lookup(cov_b, t0, t)]
        if t.size == 0 or tb.size == 0:
            out.append({"lag_s": int(lag), "n_events": 0, "share": None})
            continue
        _, d = nearest(tb, t)
        out.append({"lag_s": int(lag), "n_events": int(t.size), "share": float((np.abs(d) <= window_s).mean())})
    return out


def diff_summary(x: np.ndarray, y: np.ndarray) -> dict:
    """x - y statistics over paired finite values."""
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if x.size == 0:
        return {"n_pairs": 0}
    d = x - y
    return {
        "n_pairs": int(d.size), "median_diff": float(np.median(d)), "mean_diff_bias": float(d.mean()),
        "mae": float(np.abs(d).mean()), "p05_diff": float(np.percentile(d, 5)),
        "p95_diff": float(np.percentile(d, 95)), "pearson": pearson(x, y), "spearman": spearman(x, y),
        "median_a": float(np.median(x)), "median_b": float(np.median(y)),
    }


def quantiles(x: np.ndarray, qs: Sequence[float] = (0, 1, 5, 25, 50, 75, 95, 99, 100)) -> dict:
    x = x[np.isfinite(x)]
    return {f"p{q:g}": (float(np.percentile(x, q)) if x.size else None) for q in qs}
