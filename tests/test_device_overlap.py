"""Same-subject dual-device overlap analysis (P0 A2). Synthetic fixtures only — no raw data."""
from __future__ import annotations

import numpy as np
import pytest

from src.data.device_overlap import (
    alignment_sensitivity, analysis_view, coverage_mask, diff_summary, evaluation_group, event_coincidence, event_lag_scan,
    group_by_subject, lagged_correlation, nearest, occupancy_table, overlap_summary, pair_rows,
    pressure_features, validate_identity,
)
from src.data.provenance import CHANNELS, SourceData
from src.data.subject_mapping import resolve_source

T0 = 1_780_000_000  # arbitrary synthetic epoch second


def stream(source_id, subject, device, ts, p=None, th=(25, 50), files=None, absent=None):
    ts = np.asarray(ts, dtype=np.int64)
    n = ts.size
    vals = np.zeros((n, len(CHANNELS)), dtype=np.int16)
    if p is not None:
        vals[:, :6] = p
    vals[:, 6], vals[:, 7] = th
    fidx = np.zeros(n, np.int32) if files is None else np.asarray(files, np.int32)
    fw = None if absent is None else np.asarray(absent, np.int8)
    return SourceData(source_id, subject, device, [f"f{i}" for i in range(int(fidx.max()) + 1 if n else 1)],
                      ts, vals, fidx, fw)


# --- identity ---------------------------------------------------------------------------------

def test_same_subject_dual_device_grouping():
    s80 = resolve_source("user02/mat_22480/sm22480_0719.txt")
    s82 = resolve_source("user02/mat_22482/sm22482_0719.txt")
    a = stream("user02_mat_22480", s80.subject_id, s80.device_id, [T0])
    b = stream("user02_mat_22482", s82.subject_id, s82.device_id, [T0])
    assert evaluation_group(a) == evaluation_group(b) == "User02"
    assert group_by_subject([a, b]) == {"User02": ["user02_mat_22480", "user02_mat_22482"]}


@pytest.mark.parametrize("subject,device", [("22480", "22480"), ("User07", "22482"), ("User99", "unknown")])
def test_device_id_confusion_is_rejected(subject, device):
    with pytest.raises(ValueError):
        validate_identity(stream("s", subject, device, [T0]))


# --- coverage and overlap -------------------------------------------------------------------------

def test_temporal_overlap_hours():
    a = np.arange(T0, T0 + 7200, 3)                  # 00:00-02:00
    b = np.arange(T0 + 3600, T0 + 10800, 3)          # 01:00-03:00
    n = 10800
    ma, mb = coverage_mask(a, T0, n, 60), coverage_mask(b, T0, n, 60)
    s = overlap_summary(ma, mb)
    assert s["hours_both"] == pytest.approx(1.0, abs=1e-3)
    assert s["hours_only_a"] == pytest.approx(1.0, abs=1e-3) and s["hours_only_b"] == pytest.approx(1.0, abs=1e-3)
    assert s["ratio_both_of_union"] == pytest.approx(1 / 3, abs=1e-3)
    assert s["n_only_a_periods_ge_30min"] == 1


def test_gaps_longer_than_max_gap_are_not_covered():
    ts = np.array([T0, T0 + 3, T0 + 3 + 3600])       # one-hour hole
    m = coverage_mask(ts, T0, 3610, 60)
    assert m.sum() == 3 + 60 + 1                    # 3 s, then 60 s capped, then the last row's second


def test_non_overlapping_devices():
    a = np.arange(T0, T0 + 3600, 3)
    b = np.arange(T0 + 7200, T0 + 10800, 3)
    ma, mb = coverage_mask(a, T0, 10800, 60), coverage_mask(b, T0, 10800, 60)
    s = overlap_summary(ma, mb)
    assert s["hours_both"] == 0 and s["ratio_both_of_union"] == 0
    joint = (ma & mb)[a - T0]
    assert alignment_sensitivity(a, b, joint)["n_rows"] == 0
    ia, jb = pair_rows(a, b, tol_s=3, rows_a=joint)
    assert ia.size == jb.size == 0


# --- nearest-timestamp pairing ---------------------------------------------------------------------

def test_nearest_timestamp_matching_sensitivity():
    b = np.arange(T0, T0 + 600, 6)
    a = b + 3                                        # every a row is 3 s from the nearest b row
    j, d = nearest(b, a)
    assert np.all(np.abs(d) == 3)
    s = alignment_sensitivity(a, b)
    assert s["share_within_0s"] == 0 and s["share_within_1s"] == 0 and s["share_within_3s"] == 1.0
    s_exact = alignment_sensitivity(b.copy(), b)
    assert s_exact["share_within_0s"] == 1.0


# --- signal relationship ----------------------------------------------------------------------------

def test_lagged_correlation_finds_the_delay():
    rng = np.random.default_rng(0)
    ts = np.arange(T0, T0 + 3 * 3000, 3)
    x = rng.normal(size=ts.size)
    ts_b = ts + 6                                     # b observes the same signal 6 s later
    prof = {r["lag_s"]: r for r in lagged_correlation(ts, x, ts_b, x.copy(), range(-12, 13), tol_s=1)}
    peak = max(r["pearson"] or -1 for r in prof.values())
    plateau = [lag for lag, r in prof.items() if (r["pearson"] or -1) >= peak - 1e-9]
    # with 3 s sampling and a ±1 s pairing tolerance, lag resolution is ±1 s around the true delay
    assert 6 in plateau and set(plateau) <= {5, 6, 7} and peak == pytest.approx(1.0)
    assert abs(prof[0]["pearson"]) < 0.1


def test_event_coincidence_exceeds_control_for_synchronous_events():
    rng = np.random.default_rng(1)
    ts = np.arange(T0, T0 + 3 * 60000, 3)
    ev = rng.random(ts.size) < 0.01
    all_rows = np.ones(ts.size, bool)
    r = event_coincidence(ts, ev, ts, ev, window_s=3, rows_a=all_rows)
    assert r["observed_share"] == 1.0 and r["control_share"] < 0.2 and r["lift"] > 5


def test_event_lag_scan_recovers_a_clock_offset():
    rng = np.random.default_rng(2)
    ts = np.arange(T0, T0 + 3 * 20000, 3)
    ev = rng.random(ts.size) < 0.02
    ts_b = ts + 600                                  # device b's clock runs 10 min ahead
    cov_b = coverage_mask(ts_b, T0, int(ts_b.max() - T0) + 1, 60)
    scan = event_lag_scan(ts, ev, ts_b, ev, range(-1200, 1201, 5), 3, cov_b, T0)
    best = max(scan, key=lambda r: r["share"] or 0)
    assert best["lag_s"] == 600 and best["share"] == 1.0
    assert np.median([r["share"] for r in scan if r["share"] is not None]) < 0.2


# --- occupancy ----------------------------------------------------------------------------------------

def test_occupancy_sensitivity_table():
    a = np.array([1, 1, 0, 0, 1, 0, 1, 0], bool)
    b = np.array([1, 0, 1, 0, 1, 0, 1, 0], bool)
    t = occupancy_table(a, b)
    assert (t["both"], t["only_a"], t["only_b"], t["neither"]) == (3 / 8, 1 / 8, 1 / 8, 3 / 8)
    assert occupancy_table(a, a)["kappa"] == pytest.approx(1.0)
    psum = pressure_features(analysis_view(stream("s", "User02", "22480", np.arange(T0, T0 + 12, 3),
                                                  p=np.array([[0] * 6, [5, 0, 0, 0, 0, 0], [100] * 6, [0] * 6])),
                                           "22480"))["pressure_sum"]
    assert [(psum > thr).sum() for thr in (0, 50, 1000)] == [2, 1, 0]   # threshold dependence is explicit


# --- analysis view -----------------------------------------------------------------------------------

def test_analysis_view_counts_repeated_and_conflicting_rows():
    ts = [T0 + 6, T0, T0 + 3, T0 + 3, T0 + 6]         # file 0: 6, 0, 3 | file 1: 3 (repeat), 6 (conflict)
    p = np.zeros((5, 6), np.int16)
    p[4, 0] = 99                                     # same timestamp as row 0, different values
    v = analysis_view(stream("s", "User02", "22482", ts, p=p, files=[0, 0, 0, 1, 1]), "22482")
    assert v.n_raw == 5 and v.n_exact_duplicates == 1 and v.n_conflicting_ts == 1
    assert list(v.ts - T0) == [0, 3, 6] and v.p[2, 0] == 0   # first row in file order kept


def test_diff_summary_reports_bias():
    x = np.array([27, 28, 29, 30], float)
    s = diff_summary(x, x + 2)
    assert s["median_diff"] == -2 and s["mean_diff_bias"] == -2 and s["mae"] == 2 and s["pearson"] == pytest.approx(1)
