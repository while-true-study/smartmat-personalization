"""Single-device channel anomaly audit (P0 A9b). Synthetic arrays only — no raw data."""
from __future__ import annotations

from datetime import datetime

import numpy as np

from src.data.channel_anomaly import best_split, channel_unit_stats, classify_shift, recovery
from src.data.sensor_phase import assign_phase, distinct_peaks, split_scores
from src.data.subject_mapping import channel_quality_spec

RNG = np.random.default_rng(20260913)
EPOCH = datetime(1970, 1, 1)


def sec(s: str) -> int:
    return int((datetime.fromisoformat(s) - EPOCH).total_seconds())


def frame(n: int, p1_active: float, p1_level: float = 800.0) -> tuple[np.ndarray, np.ndarray]:
    p = RNG.integers(200, 1200, (n, 6)).astype(float)
    p[:, 0] = np.where(RNG.random(n) < p1_active, p1_level + RNG.integers(0, 50, n), 0)
    return p, np.ones((n, 6), bool)


def test_channel_unit_stats():
    p = np.array([[100, 0, 0, 0, 0, 300], [0, 0, 0, 0, 0, 0], [50, 0, 0, 0, 0, 50], [np.nan, 5, 5, 5, 5, 5]], float)
    present = ~np.isnan(p)
    s = channel_unit_stats(p, present)
    assert s["loaded_rows"] == 2 and s["all_zero_ratio"] == 0.25          # the row with a missing channel is not loaded
    assert s["p1_active_ratio"] == 1.0 and s["p1_nz_median"] == 75.0 and s["p1_nz_iqr"] == 25.0
    assert s["p6_dominant_ratio"] == 0.5 and s["p1_dominant_ratio"] == 0.5   # tie resolves to the first channel
    assert abs(s["p1_mass_share"] - 150 / 500) < 1e-9


def test_p1_only_drop_is_detected_and_classified():
    nights = [channel_unit_stats(*frame(400, 0.5 if k < 20 else 0.14)) for k in range(40)]
    x = np.array([u["p1_active_ratio"] for u in nights])
    assert distinct_peaks(np.abs(split_scores(x, 3)), 3)[0] in (19, 20, 21)
    others = np.array([u["p3_nz_median"] for u in nights])                  # an unaffected channel: noise only
    assert np.nanmax(np.abs(split_scores(others, 3))) < np.nanmax(np.abs(split_scores(x, 3))) / 3
    c = classify_shift({"p1": -1.0, "p2": 0.1, "p3": -0.3, "p4": 0.2, "p5": 0.0, "p6": -0.5})
    assert c["label"] == "p1_only" and c["shifted_channels"] == "p1"


def test_localized_whole_mat_and_no_shift_labels():
    assert classify_shift({"p1": -1.0, "p6": -0.9, "p2": 0.1, "p3": 0, "p4": 0, "p5": 0})["label"] == "p1_plus_localized"
    whole = {f"p{i}": -0.95 for i in range(1, 7)}
    assert classify_shift(whole)["label"] == "whole_mat_shift"
    assert classify_shift({"p1": -0.2, "p2": -0.9, "p3": 0, "p4": 0, "p5": 0, "p6": 0})["label"] == "p1_not_shifted"
    assert classify_shift({"p6": -1.0, "p1": 0.3}, primary="p6")["label"] == "p6_only"


def test_recovery_states():
    assert recovery([0.5] * 7, [0.14] * 7, [0.14] * 7)["state"] == "persistent"
    assert recovery([0.5] * 7, [0.14] * 7, [0.49] * 7)["state"] == "recovered"
    assert recovery([0.5] * 7, [0.14] * 7, [0.30] * 7)["state"] == "partial_recovery"
    assert recovery([], [0.1], [0.1])["state"] is None


def test_best_split_finds_the_hour_of_onset():
    hourly = np.r_[RNG.normal(1400, 150, 12), RNG.normal(60, 15, 20)]
    bs = best_split(hourly)
    assert bs["k"] == 12 and bs["r2_step"] > 0.9
    drift = np.linspace(1400, 60, 32)
    assert best_split(drift)["r2_step"] < 0.8                            # a line is never a clean single step


def test_channel_quality_phases_from_config():
    bounds, names, chans = channel_quality_spec("22482")
    assert names == ("normal", "p1_transition", "p1_response_shift")
    assert chans == {"normal": "", "p1_transition": "p1", "p1_response_shift": "p1"}
    assert bounds == [(sec("2026-08-19 08:56:10"), sec("2026-08-19 19:58:23")),
                      (sec("2026-08-20 09:58:32"), sec("2026-08-20 21:37:33"))]
    ts = np.array([sec("2026-08-19 08:56:10"), sec("2026-08-20 02:00:00"), sec("2026-08-20 21:37:33"), sec("2026-09-01 00:00:00")])
    assert assign_phase(ts, bounds, names).tolist() == ["normal", "p1_transition", "p1_response_shift", "p1_response_shift"]
    assert channel_quality_spec("22480") == ([], ("normal",), {"normal": ""})
    assert channel_quality_spec("unknown")[1] == ("normal",)
