"""P10 parts R and M on synthetic data (D-064; docs/P10_LEVEL_BASELINE_HISTORY_PLAN.md §3–§4)."""
from __future__ import annotations

import numpy as np
import pytest

from src.evaluation import p10_level_baselines as LB


def test_config_matches_code_and_frozen_protocol():
    doc = LB.load_config()
    assert doc["reproduction"]["tolerance_abs"] == LB.TOL_ABS and doc["reproduction"]["tolerance_rel"] == 0.0
    assert doc["user03"] == "not_used"


def test_tolerance_is_absolute_1e9_and_nan_fails():
    assert LB.within_tol(1.0 + 0.9e-9, 1.0)[0]
    assert LB.within_tol(2.0, 2.0) == (True, 0.0)
    assert not LB.within_tol(1.0 + 1.1e-9, 1.0)[0]
    assert not LB.within_tol(float("nan"), 1.0)[0]
    assert not LB.within_tol(1e6 + 1e-3, 1e6)[0]            # no relative tolerance


def test_constants_mean_and_median_use_fit_windows_only():
    y_fit = np.array([[20.0, 30.0], [21.0, 31.0], [25.0, 50.0], [22.0, 33.0]])
    c = LB.constants(y_fit)
    assert np.allclose(c["mean"], [22.0, 36.0])
    assert np.array_equal(c["median"], [21.5, 32.0])         # even count: mean of the two middle values
    y_eval = np.array([[100.0, 100.0]])                      # evaluation targets never enter the constants
    assert np.array_equal(LB.constants(y_fit)["median"], c["median"])
    assert LB.point_metrics(y_eval, np.tile(c["median"], (1, 1)))["temperature"]["bias"] == pytest.approx(21.5 - 100)
    with pytest.raises(LB.P10Error):
        LB.constants(np.zeros((0, 2)))
    with pytest.raises(LB.P10Error):
        LB.constants(np.array([[np.nan, 1.0]]))


def _long(prov_t: dict, prov_h: dict, y: np.ndarray, p: np.ndarray) -> dict:
    n = y.shape[0]
    out = {k: np.concatenate([np.asarray(prov_t[k]), np.asarray(prov_h[k])]) for k in prov_t}
    out["target"] = np.array(["temperature"] * n + ["humidity"] * n)
    out["y_true"] = np.concatenate([y[:, 0], y[:, 1]])
    out["y_pred"] = np.concatenate([p[:, 0], p[:, 1]])
    return out


def test_strict_pairs_verifies_the_target_pairing():
    prov = {"device_id": np.array(["a", "b"]), "window_start": np.array([0, 20], "datetime64[s]")}
    y, p = np.array([[1.0, 2.0], [3.0, 4.0]]), np.array([[1.5, 2.5], [3.5, 4.5]])
    yy, pp, pv = LB.strict_pairs(_long(prov, prov, y, p))
    assert np.array_equal(yy, y) and np.array_equal(pp, p)
    swapped = {"device_id": np.array(["b", "a"]), "window_start": prov["window_start"]}
    with pytest.raises(LB.P10Error):
        LB.strict_pairs(_long(prov, swapped, y, p))


def test_keys_equal_names_the_first_differing_field():
    a = {k: np.array(["x", "y"]) for k in LB.KEY_FIELDS}
    b = {k: v.copy() for k, v in a.items()}
    assert LB.keys_equal(a, b) == (True, "ok")
    b["session_id"] = np.array(["x", "z"])
    assert LB.keys_equal(a, b) == (False, "session_id")
    ints = {k: np.array([1, 2]) for k in LB.KEY_FIELDS}
    dts = {k: np.array([1, 2], "datetime64[s]") for k in LB.KEY_FIELDS}
    assert LB.keys_equal(ints, dts)[0]                        # timestamps compared as epoch seconds


def test_point_counts_are_plain_point_estimates():
    assert LB.count_le([(1.0, 1.0), (0.9, 1.0), (1.1, 1.0)]) == 2


def test_failed_reproduction_writes_only_the_check_table(tmp_path):
    LB.set_output_root(tmp_path)
    try:
        chk = LB.Checks()
        chk.num("loso", "x", 1.0, 1.1)
        assert not chk.passed
        prov = {"reproduction_passed": chk.passed}
        out = LB.write_tables({"reproduction_check": chk.rows, "loso_metrics": [{"a": 1}]}, prov)
        assert (out / "p10_reproduction_check.csv").exists()
        assert not (out / "p10_loso_metrics.csv").exists()
    finally:
        LB.set_output_root(None)
