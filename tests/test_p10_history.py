"""P10 part H on synthetic data: history windows, availability, features, gate helpers and models (D-064;
docs/P10_LEVEL_BASELINE_HISTORY_PLAN.md §5–§6)."""
from __future__ import annotations

import numpy as np
import pytest

from src.evaluation import leakage as L
from src.evaluation import p10_history as H
from src.training.loso_data import Rows


def make_rows(ts, session, pressure=None, subject="UserX", phase="s1", seed=0) -> Rows:
    ts = np.asarray(ts, np.int64)
    n = ts.size
    rng = np.random.default_rng(seed)
    p = rng.integers(0, 4096, size=(n, 6)).astype(np.int16) if pressure is None else np.asarray(pressure, np.int16)
    s = lambda v: np.array([v] * n)  # noqa: E731
    return Rows(s(subject), s("dev"), np.asarray(session).astype(str), s(phase), s("normal"), ts, p,
                rng.normal(25, 1, size=(n, 2)), np.ones(n, bool), np.ones(n, bool))


BASE = 1_700_000_000


def test_history_spec_alignment_and_feature_names():
    for h in H.HISTORIES:
        spec = H.history_spec(h)
        assert spec.n_steps == h // 5 and spec.stride_s == 20 and spec.max_gap_s == 5
    with pytest.raises(H.P10HistoryError):
        H.history_spec(310)                        # 40 - 310 is not a multiple of the stride
    names = H.feature_names(900)
    assert len(names) == 42 and names[0] == "h900_p1_mean" and names[-1] == "h900_p6_abs_change_sum"
    assert H.check_feature_names(list(names)) is None
    assert H.check_feature_names(["h900_p1_mean", "h900_temp_mean"]) is not None
    assert H.check_feature_names(["raw_p1"]) is not None      # new features are never declared as RAW (and vice versa)


def test_summary_features_hand_computed():
    steps = np.zeros((1, 3, 6), np.int16)
    steps[0, :, 0] = [0, 4095, 819]
    x = np.array([0.0, 1.0, 0.2])
    f = H.summary_features(steps).reshape(6, 7)
    assert np.allclose(f[0], [x.mean(), x.std(), 0.0, 1.0, 0.2, 0.2, 1.0 + 0.8])
    assert np.allclose(f[1:], 0.0)
    with pytest.raises(ValueError):
        H.summary_features(np.full((1, 3, 6), 4096))


def test_availability_reasons_session_start_and_gap():
    # session A: rows every 3 s up to 1,197 s, a 13-s gap, rows again from 1,210 s; session B starts later
    t1 = np.arange(0, 1200, 3)
    t2 = np.arange(1210, 1810, 3)
    t3 = np.arange(5000, 5400, 3)
    ts = BASE + np.concatenate([t1, t2, t3])
    sess = ["A"] * (t1.size + t2.size) + ["B"] * t3.size
    rows = make_rows(ts, sess)
    sh = H.build_subject(rows, "UserX", histories=(40, 300, 900))
    assert all(c["passed"] for c in sh.checks), [c for c in sh.checks if not c["passed"]]
    assert sh.available[40].all()
    seg_start = np.where(sh.t_end <= BASE + 1200, BASE + 0, np.where(sh.t_end <= BASE + 5000, BASE + 1210, BASE + 5000))
    for h in (300, 900):
        want = sh.t_end - h >= seg_start
        assert np.array_equal(sh.available[h], want)
        miss = ~want
        exp_reason = np.where(seg_start == BASE + 1210, "gap_gt_5s", "session_start")
        assert np.array_equal(sh.reason[h][miss], exp_reason[miss])
        assert (sh.reason[h][want] == "").all()
    # session B spans 400 s: no 900-s history anywhere, some 300-s ones
    in_b = sh.prov["session_id"] == "B"
    assert not sh.available[900][in_b].any() and sh.available[300][in_b].any()
    assert np.array_equal(sh.common, sh.labelled & sh.available[40] & sh.available[300] & sh.available[900])


def test_features_equal_manual_bin_extraction_and_ignore_future_rows():
    rng = np.random.default_rng(1)
    t = np.cumsum(rng.integers(1, 6, size=600))    # irregular sampling, every gap 1..5 s
    ts = BASE + t
    rows = make_rows(ts, ["A"] * ts.size, seed=2)
    sh = H.build_subject(rows, "UserX", histories=(40, 300))
    assert all(c["passed"] for c in sh.checks)
    k = int(np.flatnonzero(sh.common)[-1])
    t_end = int(sh.t_end[k])
    for h in (40, 300):
        steps = []
        for b in range(h // 5):
            lo, hi = t_end - h + 5 * b, t_end - h + 5 * (b + 1)
            in_bin = np.flatnonzero((ts >= lo) & (ts < hi))
            steps.append(rows.pressure[in_bin[-1]])
        manual = H.summary_features(np.array(steps)[None])
        row = int(np.flatnonzero(np.flatnonzero(sh.common) == k)[0])
        assert np.allclose(sh.features[h][row], manual[0])
    # rows at or after t_end must not change the features of that endpoint
    p2 = rows.pressure.copy()
    p2[ts >= t_end] = 0
    sh2 = H.build_subject(make_rows(ts, ["A"] * ts.size, pressure=p2), "UserX", histories=(40, 300))
    row = int(np.flatnonzero(np.flatnonzero(sh.common) == k)[0])
    for h in (40, 300):
        assert np.array_equal(sh.features[h][row], sh2.features[h][row])


def test_same_second_ties_use_the_last_row_in_canonical_order():
    ts = BASE + np.repeat(np.arange(0, 60, 2), 2)          # every timestamp twice
    p = np.zeros((ts.size, 6), np.int16)
    p[1::2, 0] = 4095                                     # the second row of each pair
    sh = H.build_subject(make_rows(ts, ["A"] * ts.size, pressure=p), "UserX", histories=(40,))
    f = sh.features[40].reshape(-1, 6, 7)
    assert np.allclose(f[:, 0, 0], 1.0)                   # every step took the later tied row


def test_histories_never_cross_sessions_or_phases():
    t = np.arange(0, 1700, 3)
    ts = BASE + t
    sess = np.where(t < 900, "A", "B")                    # contiguous in time, different sessions (B < 900 s)
    sh = H.build_subject(make_rows(ts, sess), "UserX", histories=(40, 300, 900))
    assert all(c["passed"] for c in sh.checks)
    b = sh.prov["session_id"] == "B"
    assert not sh.available[900][b].any()
    assert (sh.reason[900][b] == "session_start").all()


def test_subject_roles_and_fit_provenance_checks():
    outer = [{"fold": "1", "subject_id": s, "partition": "test" if s == "U1" else "train", "held_out_subject": "U1",
              "session_id": f"{s}|x"} for s in ("U1", "U2", "U3")]
    inner = [{"fold": "1", "inner_split": "A", "subject_id": "U2", "partition": "inner_train"},
             {"fold": "1", "inner_split": "A", "subject_id": "U3", "partition": "inner_val"},
             {"fold": "1", "inner_split": "B", "subject_id": "U3", "partition": "inner_train"},
             {"fold": "1", "inner_split": "B", "subject_id": "U2", "partition": "inner_val"}]
    roles = H.subject_roles(1, outer, inner)
    assert roles["held_out"] == "U1" and roles["train"] == ["U2", "U3"] and roles["inner"]["A"] == ("U2", "U3")
    good = L.RunContext("loso", fold=1, fit_records=[{"transform": "feature_standardizer", "partition": "train",
                                                      "subjects": ["U2", "U3"]}], selection_subjects=["U2", "U3"])
    assert L.check_fits(good, outer, []) is None and L.check_selection(good, outer, []) is None
    bad = L.RunContext("loso", fold=1, fit_records=[{"transform": "training_mean_common", "partition": "train",
                                                     "subjects": ["U1", "U2"]}], selection_subjects=["U1"])
    assert L.check_fits(bad, outer, []) is not None and L.check_selection(bad, outer, []) is not None


def test_models_fit_on_training_data_only_and_are_deterministic():
    rng = np.random.default_rng(3)
    x = rng.normal(size=(3000, 42))
    y = np.stack([x[:, 0] * 2 + 25 + rng.normal(size=3000), -x[:, 1] + 40 + rng.normal(size=3000)], 1)
    x_te = rng.normal(size=(200, 42))
    for fam in H.FAMILIES:
        cfg = H.grid(fam)[0]
        p1, prov = H.fit_predict(fam, cfg, x[:2000], y[:2000], x_te, fold=1, partition="train", subjects=["U2"])
        p2, _ = H.fit_predict(fam, cfg, x[:2000], y[:2000], x_te, fold=1, partition="train", subjects=["U2"])
        assert np.array_equal(p1, p2)
        assert all(r["partition"] == "train" and r["subjects"] == ["U2"] for r in prov)
        # the test inputs never influence the fit: predicting a superset gives the same values on the shared rows
        p3, _ = H.fit_predict(fam, cfg, x[:2000], y[:2000], np.concatenate([x_te, x[2000:] * 50]), fold=1,
                              partition="train", subjects=["U2"])
        assert np.allclose(p3[:200], p1, rtol=0, atol=1e-10)


def test_bootstrap_orientation_and_interpretation_rules():
    rng = np.random.default_rng(4)
    nights = np.repeat([f"n{i:02d}" for i in range(12)], 50)
    y = np.stack([rng.normal(25, 1, nights.size), rng.normal(40, 5, nights.size)], 1)
    good, bad = y + 0.1, y + 3.0
    rows = H.bootstrap_rows(1, "UserX", y, {"bad": bad, "good": good}, nights, [("bad", "good", "x")])
    for r in rows:
        assert r["point_estimate"] > 0 and r["interval"] == "above_zero"     # second predictor better
    metrics, boot = [], []
    for f in H.FAMILIES:
        for h in H.HISTORIES:
            for t in ("temperature", "humidity"):
                metrics.append({"subject_id": "User02", "target": t, "predictor": f, "history_s": h, "mae": 1.0,
                                "R": 0.9, "r_within": 0.2, "r_within_mat": 0.05})
                boot.append({"subject_id": "User02", "target": t, "first": "training_mean_common",
                             "second": f"{f}_h{h}", "interval": "above_zero"})
                if h != 40:
                    boot.append({"subject_id": "User02", "target": t, "first": f"{f}_h40", "second": f"{f}_h{h}",
                                 "interval": "includes_zero"})
    out = H.interpretation_rows(metrics, boot)
    assert all(r["H_a_beats_training_mean_common"] for r in out)
    assert not any(r["H_c_variation_beyond_level"] for r in out)          # User02 needs the night x mat rule too
    assert all(r["H_b_longer_history_lower_error"] in ("", False) for r in out)


def test_future_step_detection():
    assert H.has_future_step(np.array([[1, 2, 39]]), np.array([40])) is False
    assert H.has_future_step(np.array([[1, 2, 40]]), np.array([40])) is True


def _three_subjects():
    t = np.arange(0, 2400, 3)
    subjects = {}
    for i, s in enumerate(("U1", "U2", "U3")):
        rows = make_rows(BASE + i * 10_000 + t, [f"{s}|dev|S0001"] * t.size, subject=s, seed=i)
        subjects[s] = H.build_subject(rows, s)
    return subjects


class _FakeFold:
    """Frozen-fold stand-in built from the same synthetic endpoints."""

    def __init__(self, subjects):
        keys = ("subject_id", "device_id", "session_id", "window_start", "target_timestamp")
        self.prov = {k: np.concatenate([sh.prov[k] for sh in subjects.values()]) for k in keys}
        self.labelled = np.concatenate([sh.labelled for sh in subjects.values()])
        self.targets = np.concatenate([sh.targets for sh in subjects.values()])


def test_addendum_gate_passes_and_fails_closed():
    subjects = _three_subjects()
    outer = [{"fold": "1", "subject_id": s, "partition": "test" if s == "U1" else "train", "held_out_subject": "U1",
              "session_id": f"{s}|dev|S0001"} for s in subjects]
    inner = [{"fold": "1", "inner_split": "A", "subject_id": "U2", "partition": "inner_train"},
             {"fold": "1", "inner_split": "A", "subject_id": "U3", "partition": "inner_val"},
             {"fold": "1", "inner_split": "B", "subject_id": "U3", "partition": "inner_train"},
             {"fold": "1", "inner_split": "B", "subject_id": "U2", "partition": "inner_val"}]
    roles = H.subject_roles(1, outer, inner)
    fd = _FakeFold(subjects)
    fits = [{"transform": "feature_standardizer", "partition": "train", "subjects": ["U2", "U3"]}]
    rep = H.addendum_gate(1, roles, subjects, fd, fits, outer, [])
    assert rep["passed"], [c for c in rep["checks"] if not c["passed"]]
    leaky = fits + [{"transform": "training_mean_common", "partition": "train", "subjects": ["U1", "U2"]}]
    assert not H.addendum_gate(1, roles, subjects, fd, leaky, outer, [])["passed"]
    fd.targets = fd.targets + 1.0                       # endpoints no longer equal the frozen fold windows
    assert not H.addendum_gate(1, roles, subjects, fd, fits, outer, [])["passed"]
    subjects["U2"].checks.append({"check": "h900_no_step_row_at_or_after_endpoint", "passed": False, "detail": "x"})
    assert not H.addendum_gate(1, roles, subjects, _FakeFold(subjects), fits, outer, [])["passed"]
