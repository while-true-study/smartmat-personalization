"""Protocol v1.0 model inputs (docs/EXPERIMENT_PROTOCOL.md §8, D-033, D-038, D-039).

Inputs are computed from the six pressure channels of the window steps only (array shape (n, steps, 6), raw
integers 0–4095). Every transform is a fixed formula; nothing is fitted, so no input statistic can come from a test
partition. Geometry-free: no channel coordinate, centre of pressure or left/right interpretation is used (OPEN-20).

Families (per step k):
- RAW (6):       p_c / 4095
- MOVEMENT (10): d_c = (p_c[k] - p_c[k-1]) / 4095 (6); abs_change = mean_c |d_c|; d_sum = S[k] - S[k-1];
                 d_active = (A[k] - A[k-1]) / 6; dominant_switch = 1 if the dominant channel changed.
                 Step 0 has no predecessor inside the window: all MOVEMENT values are 0 there (declared padding).
- CONTACT (11):  S = sum_c p_c / (6 * 4095); active = A / 6 with A = #{c: p_c > 0}; share_c = p_c / sum_c p_c (6);
                 entropy = -sum_c share_c ln share_c / ln 6; max_share = max_c share_c; spread = std_c(p_c) / 4095.
                 An all-zero frame has shares 0, entropy 0, max_share 0.
Dominant channel = argmax_c p_c (lowest index on ties); none (-1) for an all-zero frame.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

PRESSURE_COLUMNS = ("P1", "P2", "P3", "P4", "P5", "P6")
PRESSURE_DIVISOR = 4095.0

RAW_FEATURES = tuple(f"raw_{c.lower()}" for c in PRESSURE_COLUMNS)
MOVEMENT_FEATURES = tuple(f"d_{c.lower()}" for c in PRESSURE_COLUMNS) + (
    "abs_change", "d_sum", "d_active", "dominant_switch")
CONTACT_FEATURES = ("sum", "active") + tuple(f"share_{c.lower()}" for c in PRESSURE_COLUMNS) + (
    "entropy", "max_share", "spread")
FAMILY_PARTS = {"raw": RAW_FEATURES, "movement": MOVEMENT_FEATURES, "contact": CONTACT_FEATURES}
FAMILIES = {
    "RAW": ("raw",), "MOVEMENT": ("movement",), "CONTACT": ("contact",),
    "RAW+MOVEMENT": ("raw", "movement"), "RAW+CONTACT": ("raw", "contact"),
    "RAW+MOVEMENT+CONTACT": ("raw", "movement", "contact"),
}
ADMISSIBLE_FEATURES = frozenset(RAW_FEATURES + MOVEMENT_FEATURES + CONTACT_FEATURES)


def family_features(family: str) -> tuple[str, ...]:
    return tuple(f for part in FAMILIES[family] for f in FAMILY_PARTS[part])


def _check(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p)
    if p.ndim != 3 or p.shape[-1] != 6:
        raise ValueError("pressure windows must have shape (n, steps, 6)")
    if np.any(p < 0) or np.any(p > PRESSURE_DIVISOR):
        raise ValueError("pressure outside the 12-bit range 0..4095")
    return p.astype(np.float64)


def raw(p: np.ndarray) -> np.ndarray:
    """Fixed physical-range scaling; 4095 becomes 1.0 and is kept (D-033)."""
    return _check(p) / PRESSURE_DIVISOR


def dominant(p: np.ndarray) -> np.ndarray:
    p = np.asarray(p)
    d = np.argmax(p, axis=-1)
    return np.where(p.max(axis=-1) > 0, d, -1)


def contact(p: np.ndarray) -> np.ndarray:
    p = _check(p)
    total = p.sum(axis=-1)
    share = np.divide(p, total[..., None], out=np.zeros_like(p), where=total[..., None] > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ent = -np.where(share > 0, share * np.log(share), 0.0).sum(axis=-1) / np.log(6)
    feats = [total / (6 * PRESSURE_DIVISOR), (p > 0).sum(axis=-1) / 6.0]
    feats += [share[..., c] for c in range(6)]
    feats += [ent, share.max(axis=-1), p.std(axis=-1) / PRESSURE_DIVISOR]
    return np.stack(feats, axis=-1)


def movement(p: np.ndarray) -> np.ndarray:
    p = _check(p)
    n, steps, _ = p.shape
    d = np.zeros_like(p)
    d[:, 1:] = np.diff(p, axis=1) / PRESSURE_DIVISOR
    s = p.sum(axis=-1) / (6 * PRESSURE_DIVISOR)
    a = (p > 0).sum(axis=-1) / 6.0
    dom = dominant(p)
    d_sum, d_act, switch = np.zeros((n, steps)), np.zeros((n, steps)), np.zeros((n, steps))
    d_sum[:, 1:] = np.diff(s, axis=1)
    d_act[:, 1:] = np.diff(a, axis=1)
    switch[:, 1:] = (dom[:, 1:] != dom[:, :-1]).astype(float)
    feats = [d[..., c] for c in range(6)] + [np.abs(d).mean(axis=-1), d_sum, d_act, switch]
    return np.stack(feats, axis=-1)


def build_inputs(p: np.ndarray, family: str) -> tuple[np.ndarray, tuple[str, ...]]:
    """(n, steps, n_features) input tensor and its feature names for a declared family."""
    fn = {"raw": raw, "movement": movement, "contact": contact}
    x = np.concatenate([fn[part](p) for part in FAMILIES[family]], axis=-1)
    return x, family_features(family)


@dataclass
class TargetScaler:
    """z-score per target, fitted on labelled windows of a training partition only (D-034, L3/L11).

    `fit_provenance` records where the statistics came from; the leakage gate checks it against the split.
    """
    mean: np.ndarray
    std: np.ndarray
    fit_provenance: dict = field(default_factory=dict)

    @classmethod
    def fit(cls, y: np.ndarray, *, scheme: str, fold: str, partition: str, subjects: list[str],
            nights: list[str] | None = None) -> "TargetScaler":
        y = np.asarray(y, np.float64)
        if y.ndim != 2 or y.shape[1] != 2 or y.shape[0] < 2:
            raise ValueError("targets must have shape (n >= 2, 2) = (temperature, humidity)")
        std = y.std(axis=0)
        if np.any(std <= 0):
            raise ValueError("a target is constant in the fitting partition")
        prov = {"transform": "target_zscore", "scheme": scheme, "fold": fold, "partition": partition,
                "subjects": sorted(subjects), "nights": sorted(nights) if nights is not None else None,
                "n": int(y.shape[0])}
        return cls(y.mean(axis=0), std, prov)

    def transform(self, y: np.ndarray) -> np.ndarray:
        return (np.asarray(y, np.float64) - self.mean) / self.std

    def inverse(self, z: np.ndarray) -> np.ndarray:
        return np.asarray(z, np.float64) * self.std + self.mean
