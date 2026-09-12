"""Single-device channel anomaly audit (P0 analysis A9b: User02 / 22482 P1). Read-only and descriptive.

Per-unit channel statistics, a classification of which channels shift at a boundary, a recovery check and a
best single split for fine-grained (e.g. hourly) series. Change-point ranking and effect sizes are reused from
src/data/sensor_phase.py. Nothing is removed, corrected, imputed, clipped or normalised; a channel-quality phase
is a provenance label only.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

N_CH = 6
SHIFT_DELTA = 0.8          # |Cliff's delta| treated as a large unit-level shift (descriptive, not a test)


def channel_unit_stats(p: np.ndarray, present: np.ndarray) -> dict:
    """Channel statistics of one unit on loaded rows (all channels present, at least one > 0)."""
    v = np.nan_to_num(p)
    full = present.all(axis=1)
    pos = v > 0
    loaded = full & pos.any(axis=1)
    out: dict = {"rows": int(v.shape[0]), "loaded_rows": int(loaded.sum()),
                 "all_zero_ratio": round(float((full & ~pos.any(axis=1)).mean()), 5) if v.shape[0] else None}
    q = v[loaded]
    if q.shape[0] == 0:
        return out
    tot = q.sum(axis=1)
    dom = np.bincount(np.argmax(q, axis=1), minlength=N_CH) / q.shape[0]
    share = q.sum(axis=0) / tot.sum()
    out.update({"pressure_sum_median": float(np.median(tot)), "pressure_sum_p95": float(np.percentile(tot, 95)),
                "active_channels_mean": round(float((q > 0).sum(axis=1).mean()), 4)})
    for i in range(N_CH):
        c = q[:, i]
        nz = c[c > 0]
        k = f"p{i + 1}"
        out[f"{k}_active_ratio"] = round(float((c > 0).mean()), 5)
        out[f"{k}_zero_ratio"] = round(float((c == 0).mean()), 5)
        out[f"{k}_nz_median"] = float(np.median(nz)) if nz.size else None
        out[f"{k}_nz_iqr"] = float(np.percentile(nz, 75) - np.percentile(nz, 25)) if nz.size else None
        out[f"{k}_p95"] = float(np.percentile(c, 95))
        out[f"{k}_mass_share"] = round(float(share[i]), 5)
        out[f"{k}_dominant_ratio"] = round(float(dom[i]), 5)
    return out


def classify_shift(deltas: dict[str, float | None], primary: str = "p1", threshold: float = SHIFT_DELTA) -> dict:
    """Which channels shift at a boundary, from unit-level effect sizes per channel (e.g. Cliff's delta of the
    active ratio or the non-zero median). Labels: p1_not_shifted, p1_only, p1_plus_localized, whole_mat_shift."""
    shifted = {ch: d is not None and abs(d) >= threshold for ch, d in deltas.items()}
    others = [ch for ch, s in shifted.items() if s and ch != primary]
    if not shifted.get(primary):
        label = f"{primary}_not_shifted"
    elif not others:
        label = f"{primary}_only"
    elif len(others) >= 4 and len({np.sign(deltas[ch]) for ch in others + [primary]}) == 1:
        label = "whole_mat_shift"
    else:
        label = f"{primary}_plus_localized"
    return {"label": label, "shifted_channels": ";".join(ch for ch, s in shifted.items() if s)}


def recovery(pre: Sequence[float], post_early: Sequence[float], post_late: Sequence[float]) -> dict:
    """How far the late post period returns toward the pre level: 0 = stays shifted, 1 = fully back."""
    a, b, c = (np.nanmedian(np.asarray(x, float)) if len(x) else np.nan for x in (pre, post_early, post_late))
    gap = a - b
    frac = float((c - b) / gap) if np.isfinite(gap) and gap != 0 and np.isfinite(c) else None
    state = None if frac is None else ("recovered" if frac >= 0.8 else "partial_recovery" if frac >= 0.3 else "persistent")
    return {"pre_median": None if not np.isfinite(a) else float(a), "post_early_median": None if not np.isfinite(b) else float(b),
            "post_late_median": None if not np.isfinite(c) else float(c),
            "recovered_fraction": None if frac is None else round(frac, 3), "state": state}


def best_split(x: np.ndarray, min_seg: int = 3) -> dict:
    """Single split minimising the within-segment squared error (one-step fit); index k starts segment 2."""
    x = np.asarray(x, float)
    ok = np.flatnonzero(np.isfinite(x))
    y = x[ok]
    if y.size < 2 * min_seg:
        return {"k": None}
    cs, cs2 = np.cumsum(y), np.cumsum(y ** 2)
    n = y.size
    best, bk = np.inf, None
    for k in range(min_seg, n - min_seg + 1):
        s1, s2 = cs[k - 1], cs[-1] - cs[k - 1]
        q1, q2 = cs2[k - 1], cs2[-1] - cs2[k - 1]
        sse = (q1 - s1 ** 2 / k) + (q2 - s2 ** 2 / (n - k))
        if sse < best:
            best, bk = sse, k
    sst = float(((y - y.mean()) ** 2).sum())
    return {"k": int(ok[bk]), "before_mean": float(y[:bk].mean()), "after_mean": float(y[bk:].mean()),
            "r2_step": round(1 - best / sst, 4) if sst > 0 else None}
