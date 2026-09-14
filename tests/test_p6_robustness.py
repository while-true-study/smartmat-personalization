"""P6 robustness analysis (synthetic data only; no study data, no model result)."""
from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from src.evaluation import p6_robustness as P6
from src.evaluation.metrics import TARGETS

SUBJECTS = ("User01", "User02", "User07")


def make_rows(n_nights: int = 30, delta: float = 0.0, noise: float = 0.3, seed_values: dict | None = None,
              first_primary: int = 16) -> list[dict]:
    """Per-night rows for every subject x budget x seed x target; adapted MAE = base MAE - delta (+ seed noise)."""
    rng = np.random.default_rng(7)
    rows = []
    for subject in SUBJECTS:
        base = {t: rng.uniform(1, 5, n_nights) for t in TARGETS}
        n_w = rng.integers(50, 400, n_nights)
        for b in (0, 1, 3, 7, 14):
            for s in (0, 1, 2):
                for t in TARGETS:
                    for k in range(n_nights):
                        ordinal = k + 1
                        if b > 0 and ordinal < b + 2:
                            continue                                    # the budget's test nights only
                        mae = base[t][k] - (delta if b > 0 else 0.0)
                        if seed_values and s in seed_values:
                            mae = seed_values[s]
                        rows.append({"subject_id": subject, "budget_nights": b, "seed": s,
                                     "night_id": f"2026-01-{k + 1:02d}" if k < 31 else f"2026-02-{k - 30:02d}",
                                     "night_ordinal": ordinal, "primary_test": int(ordinal >= first_primary),
                                     "target": t, "mae": float(mae), "rmse": float(mae * 1.2),
                                     "bias": float(mae * (0.8 if subject != "User02" else -0.8)),
                                     "n_windows": int(n_w[k])})
    return rows


def boot(rows, **kw):
    return {(r["subject_id"], r["target"], r["budget_nights"], r["metric"]): r
            for r in P6.bootstrap_rows(rows, **kw)}


# ---------------------------------------------------------------------------------------------- bootstrap core

def test_protocol_bootstrap_settings_are_the_frozen_ones():
    assert P6.bootstrap_settings() == (2000, 0, 0.95)


def test_identical_base_and_adapted_give_a_zero_interval():
    out = boot(make_rows(delta=0.0))
    for r in out.values():
        assert r["point_estimate"] == 0.0 and r["ci_lower"] == 0.0 and r["ci_upper"] == 0.0
        assert r["interval"] == "includes_zero" and r["proportion_nights_improved"] == 0.0


def test_constantly_better_or_worse_adaptation_gives_one_sided_intervals():
    better = boot(make_rows(delta=0.4))
    worse = boot(make_rows(delta=-0.4))
    for k, r in better.items():
        if k[3] == "mae":
            assert r["ci_lower"] > 0 and r["interval"] == "above_zero"
            assert r["point_estimate"] == pytest.approx(0.4) and r["proportion_nights_improved"] == 1.0
    for k, r in worse.items():
        if k[3] == "mae":
            assert r["ci_upper"] < 0 and r["interval"] == "below_zero"


def test_broken_night_pairing_fails():
    rows = make_rows()
    drop = next(r for r in rows if r["subject_id"] == "User07" and r["budget_nights"] == 3 and r["seed"] == 0
                and r["primary_test"] == 1)
    rows.remove(drop)
    with pytest.raises(P6.P6Error):
        P6.bootstrap_rows(rows)
    rows = make_rows()
    r = next(r for r in rows if r["subject_id"] == "User01" and r["budget_nights"] == 7 and r["seed"] == 0
             and r["primary_test"] == 1)
    r["n_windows"] += 1                                                   # a different window set on one night
    with pytest.raises(P6.P6Error):
        P6.bootstrap_rows(rows)


def test_subjects_targets_budgets_and_non_primary_nights_are_not_mixed():
    rows = make_rows(delta=0.2)
    ref = boot(rows)
    noisy = copy.deepcopy(rows)
    for r in noisy:
        if r["primary_test"] == 0:
            r["mae"] = r["rmse"] = r["bias"] = 999.0                       # non-primary nights must not enter
    assert boot(noisy) == ref
    one = [r for r in rows if r["subject_id"] == "User02"]
    got = boot(one)
    assert all(got[k] == ref[k] for k in got)                              # other subjects do not affect User02
    swapped = [dict(r, mae=r["mae"] + (5 if r["target"] == "humidity" else 0)) for r in rows]
    t_only = {k: v for k, v in boot(swapped).items() if k[1] == "temperature"}
    assert all(t_only[k] == ref[k] for k in t_only)                        # humidity does not leak into temperature


def test_primary_bootstrap_uses_seed_zero_only():
    rows = make_rows(delta=0.2)
    ref = boot(rows)
    crazy = make_rows(delta=0.2, seed_values={1: 50.0, 2: -3.0})
    got = boot(crazy)
    assert got == ref and {r["seed"] for r in got.values()} == {0}
    sens = P6.bootstrap_rows(crazy, seeds=(1, 2))
    assert {r["seed"] for r in sens} == {1, 2}


def test_bootstrap_is_reproducible_and_uses_exactly_2000_resamples():
    rows = make_rows(delta=0.1)
    a, b = P6.bootstrap_rows(rows), P6.bootstrap_rows(rows)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert {r["n_resamples"] for r in a} == {2000} and {r["rng_seed"] for r in a} == {0}
    c = P6.resample_counts(15, 2000, 0)
    assert c.shape == (2000, 15) and np.all(c.sum(1) == 15)
    assert np.array_equal(c, P6.resample_counts(15, 2000, 0))


def test_cluster_statistic_equals_the_window_level_metric():
    rng = np.random.default_rng(3)
    nights = [rng.normal(1.0, 2.0, int(rng.integers(5, 40))) for _ in range(12)]      # signed window errors
    arr = {"n": np.array([len(e) for e in nights], float), "mae": np.array([np.abs(e).mean() for e in nights]),
           "rmse": np.array([np.sqrt((e ** 2).mean()) for e in nights]), "bias": np.array([e.mean() for e in nights])}
    counts = np.array([[2, 0, 1, 1, 0, 3, 1, 0, 1, 1, 2, 0]], float)
    w = P6.weighted(counts, arr)
    pooled = np.concatenate([e for e, c in zip(nights, counts[0]) for _ in range(int(c))])
    assert w["mae"][0] == pytest.approx(np.abs(pooled).mean())
    assert w["rmse"][0] == pytest.approx(np.sqrt((pooled ** 2).mean()))
    assert w["bias"][0] == pytest.approx(pooled.mean())


def test_point_estimate_equals_the_full_sample_difference():
    rows = make_rows(delta=0.3)
    r = boot(rows)[("User07", "humidity", 14, "mae")]
    base = P6.night_arrays(rows, "User07", 0, 0, "humidity")
    adapted = P6.night_arrays(rows, "User07", 14, 0, "humidity")
    full = np.ones((1, base["night"].size))
    assert r["point_estimate"] == pytest.approx(P6.weighted(full, base)["mae"][0] - P6.weighted(full, adapted)["mae"][0])


# ------------------------------------------------------------------------------------------ post-hoc analyses

def test_drift_grid_excludes_spans_overlapping_adaptation_or_buffer_nights():
    out = P6.drift_rows(make_rows(delta=0.2))
    ex = {(r["start_night"], r["budget_nights"]) for r in out if r["status"].startswith("excluded")}
    assert ex == {(12, 14), (14, 14)}
    ev = [r for r in out if r["status"] == "evaluated" and r["budget_nights"] > 0]
    assert {r["start_night"] for r in ev} == set(P6.DRIFT_STARTS)
    r = next(r for r in ev if r["start_night"] == 21 and r["subject_id"] == "User02" and r["budget_nights"] == 3)
    assert r["n_nights"] == 10 and r["direction"] == "better" and r["seeds_improved"] == 3


def test_rolling_mean_is_centred_and_truncated():
    v = np.arange(10, dtype=float)
    r = P6.rolling_centred(v, 7)
    assert r[5] == pytest.approx(v[2:9].mean()) and r[0] == pytest.approx(v[0:4].mean())
    assert r[-1] == pytest.approx(v[6:10].mean())


def test_heater_context_uses_the_latest_event_within_60_minutes_on_the_same_device():
    events = {"22482": (np.array([1000, 5000]), np.array(["AHON", "AHOF"], dtype=object)),
              "22480": (np.array([4000]), np.array(["AHON"], dtype=object))}
    dev = np.array(["22482", "22482", "22482", "22482", "22480", "22480"])
    ts = np.array([900, 1500, 4700, 5100, 4100, 8000])
    got = P6.heater_context(dev, ts, events)
    assert list(got) == ["no_AHON_AHOF_60min", "after_AHON_60min", "no_AHON_AHOF_60min", "after_AHOF_60min",
                         "after_AHON_60min", "no_AHON_AHOF_60min"]


def test_stratum_bootstrap_point_is_the_full_sample_value():
    rng = np.random.default_rng(1)
    nights = np.repeat(np.arange(12).astype(str), 20)
    e0 = rng.normal(-2, 1, nights.size)
    e14 = rng.normal(-0.5, 1, nights.size)
    res = P6.stratum_bootstrap(e0, e14, nights, 2000, 0, 0.95)
    assert res["delta_mae_b0_minus_b14"]["point"] == pytest.approx(np.abs(e0).mean() - np.abs(e14).mean())
    assert res["bias_b0"]["interval"] == "below_zero"
    assert res["bias_b14"]["point"] == pytest.approx(e14.mean())


def test_mismatch_consistency_rule():
    spans = [{"subject_id": "User07", "target": "temperature", "span": f"adaptation_b{b}",
              "minus_primary_mean": -2.2} for b in P6.ADAPT_BUDGETS]
    out = P6.mismatch_consistency(spans, {("User07", "temperature"): 1.1},
                                  {("User07", "temperature", b): -20.0 for b in P6.ADAPT_BUDGETS})
    assert all(r["expected_direction"] == "worse" and r["consistent"] for r in out)
