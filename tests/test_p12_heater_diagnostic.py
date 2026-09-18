"""P12 heater-context diagnostic on synthetic data: the frozen look-up, isolation of mats and subjects, source-only
constants, the UNKNOWN rule, eta squared and determinism (D-067; docs/P12_HEATER_DIAGNOSTIC_PLAN.md)."""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from src.evaluation import p6_robustness as P6
from src.evaluation import p8_posthoc as P8
from src.evaluation import p12_heater_diagnostic as P12

T0 = 1_700_000_000


def ev(*pairs):
    return (np.array([p[0] for p in pairs], np.int64), np.array([p[1] for p in pairs], dtype=object))


def states(subjects, devices, ts, events):
    return P12.context_states(np.array(subjects), np.array(devices), np.array(ts, np.int64), events).tolist()


def test_definition_is_the_frozen_d047_one():
    doc = P12.load_config()
    assert tuple(doc["heater_context"]["codes"]) == P6.HEATER_CODES == ("AHON", "AHOF")
    assert doc["heater_context"]["lookback_s"] == P6.HEATER_WINDOW_S == 3600
    assert "P6.heater_context(" in inspect.getsource(P12.context_states)     # reused, not re-implemented


def test_future_event_is_never_used_and_same_second_counts_as_past():
    events = {"U": {"m": ev((T0 + 100, "AHON"))}}
    assert states(["U"] * 3, ["m"] * 3, [T0 + 99, T0 + 100, T0 + 101], events) == ["UNKNOWN", "ON", "ON"]


def test_event_older_than_60_min_is_unknown_and_latest_code_wins():
    events = {"U": {"m": ev((T0, "AHON"), (T0 + 600, "AHOF"))}}
    got = states(["U"] * 4, ["m"] * 4, [T0 + 300, T0 + 600 + 3600, T0 + 600 + 3601, T0 + 900], events)
    assert got == ["ON", "OFF", "UNKNOWN", "OFF"]


def test_events_of_the_other_mat_are_ignored_user02_mats_stay_separate():
    events = {"User02": {"22480": ev((T0, "AHON")), "22482": ev((T0 + 10, "AHOF"))}}
    got = states(["User02"] * 3, ["22480", "22482", "22482"], [T0 + 50, T0 + 50, T0 + 5], events)
    assert got == ["ON", "OFF", "UNKNOWN"]                  # 22482 at T0+5 does not see the 22480 AHON at T0


def test_events_of_another_subject_with_the_same_device_id_are_ignored():
    events = {"User01": {"unknown": ev((T0, "AHON"))}, "User07": {"unknown": ev()}}
    assert states(["User01", "User07"], ["unknown", "unknown"], [T0 + 60, T0 + 60], events) == ["ON", "UNKNOWN"]
    with pytest.raises(P12.P12Error):
        states(["User03"], ["unknown"], [T0], events)       # a subject without its own event table fails closed


def test_last_event_time_agrees_with_the_frozen_lookup():
    events = {"m": ev((T0, "AHON"), (T0 + 5000, "AHOF"))}
    ts = np.array([T0 - 1, T0 + 10, T0 + 3601, T0 + 5000], np.int64)
    got = P12.last_event_time(np.array(["m"] * 4), ts, events)
    assert got.tolist() == [-1, T0, -1, T0 + 5000]
    lab = P6.heater_context(np.array(["m"] * 4), ts, events)
    assert np.array_equal(got >= 0, lab != "no_AHON_AHOF_60min")


def fake_fold():
    subj = np.array(["User01"] * 3 + ["User02"] * 3 + ["User07"] * 2)
    return SimpleNamespace(fold=1, held_out="User01", train_subjects=["User02", "User07"],
                           prov={"subject_id": subj}, partition=np.where(subj == "User01", "test", "train"))


def test_constants_refuse_the_held_out_subject():
    fd = fake_fold()
    P12.assert_source_only(fd, fd.partition == "train")
    with pytest.raises(P12.P12Error):
        P12.assert_source_only(fd, np.ones(8, bool))                         # held-out windows in the fit
    with pytest.raises(P12.P12Error):
        P12.assert_source_only(fd, fd.prov["subject_id"] == "User02")        # not the whole source pool
    with pytest.raises(P12.P12Error):
        P12.assert_source_only(fd, np.zeros(8, bool))


def test_unknown_and_empty_source_states_fall_back_to_the_source_overall_mean():
    y = np.array([[20.0, 40.0], [22.0, 44.0], [30.0, 60.0], [32.0, 64.0]])
    c = P12.conditioned_constants(y, np.array(["ON", "ON", "UNKNOWN", "UNKNOWN"]))
    assert c["mean_ON"].tolist() == [21.0, 42.0] and c["overall_mean"].tolist() == [26.0, 52.0]
    assert c["fallback"] == ["OFF"] and c["mean_OFF"].tolist() == [26.0, 52.0]
    pred = P12.predict_conditioned(np.array(["ON", "OFF", "UNKNOWN"]), c)
    assert pred.tolist() == [[21.0, 42.0], [26.0, 52.0], [26.0, 52.0]]
    with pytest.raises(P12.P12Error):
        P12.predict_conditioned(np.array(["MAYBE"]), c)


def test_eta_squared_sanity():
    g = np.array(["ON"] * 4 + ["OFF"] * 4)
    assert P12.eta_squared(np.array([1.0] * 4 + [3.0] * 4), g) == pytest.approx(1.0)
    assert P12.eta_squared(np.array([1.0, 3.0] * 4), g) == pytest.approx(0.0)
    y = np.array([0.0, 2.0, 0.0, 2.0, 2.0, 4.0, 2.0, 4.0])                   # between 8, total 16
    assert P12.eta_squared(y, g) == pytest.approx(0.5)
    assert np.isnan(P12.eta_squared(y, np.array(["ON"] * 8)))                # one state only
    assert [P12.eta_label(v) for v in (0.01, 0.06, 0.14, float("nan"))] == ["small", "medium", "large", "undefined"]
    assert [P12.case_of(*p) for p in ((0.01, 0.01), (0.2, 0.01), (0.2, 0.07), (0.01, 0.07))] == ["A", "B", "C", "C"]


def test_night_centring_removes_a_pure_night_level_association():
    nights = np.repeat(np.array(["n1", "n2", "n3", "n4"]), 50)
    state = np.where(np.isin(nights, ["n1", "n2"]), "ON", "OFF")             # context constant within a night
    rng = np.random.default_rng(0)
    y = np.where(state == "ON", 30.0, 20.0) + rng.normal(0, 0.5, nights.size)
    assert P12.eta_squared(y, state) > 0.9
    assert P12.eta_squared(P12.centre(y, nights), state) < 1e-20
    mats = np.tile(np.array(["a", "b"]), nights.size // 2)
    yc = P12.centre(y + np.where(mats == "a", 5.0, 0.0), nights, mats)
    for n in ("n1", "n3"):
        for m in ("a", "b"):
            assert abs(yc[(nights == n) & (mats == m)].mean()) < 1e-12


def test_eta_interval_is_deterministic_and_contains_the_point_estimate():
    rng = np.random.default_rng(1)
    nights = np.repeat(np.arange(30).astype(str), 40)
    state = rng.choice(["ON", "OFF", "UNKNOWN"], nights.size)
    y = rng.normal(25, 1, nights.size) + (state == "ON") * 0.8
    a, b = P12.eta_with_interval(y, state, nights), P12.eta_with_interval(y, state, nights)
    assert a == b and a["n_nights"] == 30 and a["n_states"] == 3
    assert a["ci_lower"] <= a["eta_squared"] <= a["ci_upper"]
    assert a["eta_squared"] == pytest.approx(P12.eta_squared(y, state))


def test_common_endpoint_keys_must_match_exactly():
    dev, ws = np.array(["m", "m", "m"]), np.array([T0, T0 + 20, T0 + 40], np.int64)
    y = np.arange(6.0).reshape(3, 2)
    keys = P8.window_keys(dev, ws)
    assert P12.common_keys_equal({"device_id": dev, "window_start": ws}, y, keys, y)
    assert not P12.common_keys_equal({"device_id": dev, "window_start": ws[::-1]}, y, keys, y)     # order matters
    assert not P12.common_keys_equal({"device_id": dev[:2], "window_start": ws[:2]}, y[:2], keys, y)
    assert not P12.common_keys_equal({"device_id": dev, "window_start": ws}, y + 1e-6, keys, y)    # targets differ


def test_no_model_no_trainer_and_own_output_root_only():
    src = inspect.getsource(P12)
    for token in ("train_tcn", "TCNConfig", "HistGradientBoosting", "Ridge(", "fit_predict", ".fit("):
        assert token not in src, token
    assert P12.output_root().as_posix().endswith("outputs/p12_heater_diagnostic")
    assert "outputs/p11_common_pool_tcn" in P12.PROTECTED_TREES and "outputs/runs/p10" in P12.PROTECTED_TREES


def test_design_freeze_refuses_a_changed_plan(tmp_path, monkeypatch):
    P12.set_output_root(tmp_path)
    try:
        first = P12.freeze_design()
        assert P12.freeze_design()["plan_sha256_lf"] == first["plan_sha256_lf"]          # idempotent
        monkeypatch.setattr(P12, "design_hashes", lambda: {**first, "plan_sha256_lf": "0" * 64})
        with pytest.raises(P12.P12Error):
            P12.freeze_design()
    finally:
        P12.set_output_root(None)
