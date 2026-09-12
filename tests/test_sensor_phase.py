"""User01 sensor phase / change-point audit (P0 A10). Synthetic series and arrays only — no raw data."""
from __future__ import annotations

import numpy as np
import pytest

from src.data.sensor_phase import (
    assign_phase, channel_profile, cliffs_delta, contiguous_units, distinct_peaks, event_rank,
    int_distribution_shift, rank_splits, split_scores, step_regime, step_vs_linear, summarize_rows,
    upper_bound_profile,
)

T0 = 1_780_000_000
RNG = np.random.default_rng(20260913)


def unit_series(kind: str, n: int = 60, k: int = 30, noise: float = 250.0) -> np.ndarray:
    base = {"step": np.where(np.arange(n) < k, 6000.0, 3000.0),
            "drift": np.linspace(6000.0, 3000.0, n),
            "flat": np.full(n, 4500.0)}[kind]
    return base + RNG.normal(0, noise, n)


def frame(n: int, p3: float = 1000.0, others: float = 300.0) -> tuple[np.ndarray, np.ndarray]:
    p = np.full((n, 6), others) + RNG.integers(0, 50, (n, 6))
    p[:, 2] = p3 + RNG.integers(0, 50, n)
    return p.astype(float), np.ones((n, 6), bool)


def test_abrupt_scale_change_is_found_at_the_step():
    x = unit_series("step")
    peaks = distinct_peaks(np.abs(split_scores(x, 3)), 3)
    assert abs(peaks[0] - 30) <= 1
    fit = step_vs_linear(x, 30)
    assert fit["r2_step"] > fit["r2_linear"] + 0.1
    assert abs(split_scores(x, 1)[30]) > 8                       # visible between two adjacent units


def test_gradual_drift_is_not_an_abrupt_step():
    x = unit_series("drift")
    fit = step_vs_linear(x, 30)
    assert fit["r2_linear"] >= fit["r2_step"]
    assert np.nanmax(np.abs(split_scores(x, 1))) < 5              # no single adjacent jump stands out
    step = unit_series("step")
    assert np.nanmax(np.abs(split_scores(step, 1))) > 2 * np.nanmax(np.abs(split_scores(x, 1)))


def test_no_change_control():
    x = unit_series("flat")
    assert np.nanmax(np.abs(split_scores(x, 3))) < 6
    assert abs(cliffs_delta(x[:30], x[30:])) < 0.35
    fit = step_vs_linear(x, 30)
    assert fit["r2_step"] < 0.3


def test_consensus_ranks_and_event_matching():
    ranks = rank_splits({"a": unit_series("step"), "b": unit_series("step")}, windows=(3,))
    assert min(ranks[("a", 3)][29:32]) == 1
    # 9 at split 2 suppresses its neighbours 8 and 5; 7 at split 5 suppresses 1 at split 4
    assert distinct_peaks(np.array([np.nan, 5, 9, 8, 1, 7]), radius=1, top=3) == [2, 5]
    assert event_rank([2, 5], k=4, radius=1) == 2 and event_rank([2], k=5, radius=1) is None


def test_channel_specific_change():
    a_p, a_m = frame(2000, p3=2000.0)
    b_p, b_m = frame(2000, p3=1000.0)                              # only P3 halves
    pa = {r["channel"]: r for r in channel_profile(a_p, a_m)}
    pb = {r["channel"]: r for r in channel_profile(b_p, b_m)}
    assert 0.45 < pb["p3"]["median"] / pa["p3"]["median"] < 0.55
    for ch in ("p1", "p2", "p4", "p5", "p6"):
        assert 0.9 < pb[ch]["median"] / pa[ch]["median"] < 1.1
    assert pb["p3"]["mass_share"] < pa["p3"]["mass_share"]


def test_saturation_ratio_change():
    ts = np.arange(T0, T0 + 3 * 1000, 3)
    pre, m = frame(1000, p3=3000.0)
    pre[::5, 2] = 4095                                            # 20 % of rows at the upper bound
    post, _ = frame(1000, p3=1500.0)
    s_pre, s_post = summarize_rows(ts, pre, m), summarize_rows(ts, post, m)
    assert s_pre["rows_4095_ratio"] == pytest.approx(0.2) and s_post["rows_4095_ratio"] == 0
    assert s_pre["p3_4095_ratio"] == pytest.approx(0.2)
    ub = upper_bound_profile(pre, m)
    assert ub["rows_1_channels_4095"] == 200 and ub["cells_4095"] == 200 and ub["accumulation_ratio"] is None
    pre[1::5, 0] = 4095
    pre[1::5, 1] = 4095
    assert upper_bound_profile(pre, m)["rows_2_channels_4095"] == 200


def test_phase_boundary_assignment():
    ts = np.array([T0, T0 + 3, T0 + 6, T0 + 30_000, T0 + 30_003])
    lab = assign_phase(ts, [(T0 + 6, T0 + 30_000)], ("s1", "s2"))
    assert lab.tolist() == ["s1", "s1", "s1", "s2", "s2"]
    inside = assign_phase(np.array([T0, T0 + 100, T0 + 200]), [(T0, T0 + 200)], ("s1", "s2"))
    assert inside.tolist() == ["s1", "", "s2"]                    # inside the gap: undetermined, never guessed
    with pytest.raises(ValueError):
        assign_phase(ts, [(T0, T0 + 10)], ("s1",))
    with pytest.raises(ValueError):
        assign_phase(ts, [(T0 + 10, T0)], ("s1", "s2"))


def test_sampling_regime_change():
    two = np.arange(T0, T0 + 2 * 500, 2)
    three = np.arange(two[-1] + 3, two[-1] + 3 + 3 * 500, 3)
    days = contiguous_units(np.r_[np.zeros(two.size, int), np.ones(three.size, int)])
    ts = np.r_[two, three]
    regs = [step_regime(ts[a:b + 1]) for _, a, b in days]
    assert [r["median_step_s"] for r in regs] == [2.0, 3.0]
    assert regs[0]["share_step_2s"] == 1.0 and regs[1]["share_step_3s"] == 1.0


def test_same_second_observations_are_preserved():
    ts = np.array([T0, T0 + 3, T0 + 3, T0 + 6])                   # two observations in one second
    p, m = frame(4)
    s = summarize_rows(ts, p, m)
    assert s["rows"] == 4 and s["sampling_steps"] == 3 and s["sampling_share_step_0s"] == pytest.approx(1 / 3, abs=1e-4)
    assert assign_phase(ts, [(T0 + 3, T0 + 6)], ("s1", "s2")).tolist() == ["s1", "s1", "s1", "s2"]


def test_effect_sizes():
    assert int_distribution_shift(np.array([0, 0, 1, 1]), np.array([1, 1, 2, 2])) == {"wasserstein": 1.0, "ks": 0.5}
    assert cliffs_delta(np.array([1, 2, 3]), np.array([4, 5])) == 1.0
    assert cliffs_delta(np.array([1, 2]), np.array([1, 2])) == 0.0
