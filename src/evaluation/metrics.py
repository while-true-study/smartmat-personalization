"""Protocol v1.0 metrics (D-041) and the inner-selection criterion (D-040).

Metrics are computed per target in original units (°C, %RH); temperature and humidity are never combined into one
endpoint. The selection criterion is unit-free and used for model selection only.
Bias = mean(y_pred - y_true) (positive = over-estimation).
"""
from __future__ import annotations

import numpy as np

TARGETS = ("temperature", "humidity")


def mae(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(p, np.float64) - np.asarray(y, np.float64))))


def rmse(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(p, np.float64) - np.asarray(y, np.float64)) ** 2)))


def bias(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.asarray(p, np.float64) - np.asarray(y, np.float64)))


def target_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, dict[str, float]]:
    """y, p: (n, 2) = (temperature, humidity) in original units."""
    y, p = np.asarray(y), np.asarray(p)
    if y.shape != p.shape or y.ndim != 2 or y.shape[1] != 2 or y.shape[0] == 0:
        raise ValueError("expected matching non-empty (n, 2) arrays")
    return {t: {"mae": mae(y[:, i], p[:, i]), "rmse": rmse(y[:, i], p[:, i]), "bias": bias(y[:, i], p[:, i])}
            for i, t in enumerate(TARGETS)}


def selection_criterion(y: np.ndarray, p: np.ndarray, train_sd: np.ndarray) -> float:
    """(MAE_T / sd_T + MAE_H / sd_H) / 2 with sd from the inner training partition (D-040)."""
    sd = np.asarray(train_sd, np.float64)
    if sd.shape != (2,) or np.any(sd <= 0):
        raise ValueError("train_sd must be two positive standard deviations")
    y, p = np.asarray(y), np.asarray(p)
    return float((mae(y[:, 0], p[:, 0]) / sd[0] + mae(y[:, 1], p[:, 1]) / sd[1]) / 2)


def unweighted_subject_mean(values_by_subject: dict[str, float]) -> float:
    """Primary aggregation: every held-out subject has weight 1/3, whatever its window count (D-041)."""
    if len(values_by_subject) != 3:
        raise ValueError("protocol v1.0 aggregates exactly three held-out subjects")
    return float(np.mean(list(values_by_subject.values())))


def round_half_up(x: float) -> int:
    """Deterministic rounding for the final epoch count: 7.5 -> 8, 6.5 -> 7 (no banker's rounding)."""
    return int(np.floor(x + 0.5))
