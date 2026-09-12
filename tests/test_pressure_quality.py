"""Pressure channel quality audit (P0 A9). Synthetic arrays and log text only — no raw data."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from src.data.duplicates import subject_device_groups
from src.data.pressure_quality import (
    boundary_summary, channel_stats, classify_channel_runs, cross_channel, delta_stats, frame_flags,
    pressure_matrix, pressure_policy_masks, row_policy_impact, schema_by_file,
)
from src.data.provenance import CHANNELS, MISSING, SourceData
from src.data.raw_parser import parse_text
from src.data.temporal import build_timeline, steps

T0 = 1_780_000_000


def make_src(p: np.ndarray, ts=None, files=None, schema=None, device="22480") -> SourceData:
    n = p.shape[0]
    vals = np.zeros((n, len(CHANNELS)), np.int16)
    vals[:, :6] = p
    vals[:, 6], vals[:, 7] = 28, 50
    ts = np.arange(T0, T0 + 3 * n, 3) if ts is None else np.asarray(ts, np.int64)
    fidx = np.zeros(n, np.int32) if files is None else np.asarray(files, np.int32)
    code = np.zeros(n, np.int8) if schema is None else np.asarray(schema, np.int8)
    return SourceData("s", "User02", device, [f"f{i}" for i in range(int(fidx.max()) + 1)], ts, vals, fidx,
                      schema_code=code)


def manifest_row(source_id, subject, device="unknown", family="md_hms_json", role="primary_candidate"):
    return {"is_sensor_data": "True", "source_id": source_id, "subject_id": subject, "device_id": device,
            "format_family": family, "dataset_role": role}


def test_excluded_source_is_filtered_from_analysis_groups():
    rows = [manifest_row("user06_auxiliary", "User06", family="plain_ymd_hms", role="excluded_invalid"),
            manifest_row("user03_legacy", "User03", family="legacy_csv_ymd_hm", role="auxiliary"),
            manifest_row("user07", "User07")]
    all_groups = subject_device_groups(rows)
    eligible = subject_device_groups(rows, eligible_only=True)
    assert ("User06", "unknown") in all_groups                 # historical audits still see delivered data
    assert ("User06", "unknown") not in eligible and ("User03", "unknown") in eligible and ("User07", "unknown") in eligible


def test_zero_frames_and_boundary_values():
    p = np.array([[0] * 6, [0] * 6, [4095, 10, 0, 0, 0, 0], [4095, 12, 0, 0, 0, 0], [100, 0, 0, 0, 0, 0]], float)
    src = make_src(p)
    P, pres = pressure_matrix(src, np.arange(src.n))
    fr = frame_flags(P, pres)
    assert fr["all_zero"].tolist() == [True, True, False, False, False]
    b = boundary_summary(src.ts, P[:, 0], pres[:, 0], 4095, session_id=np.zeros(src.n, int))
    assert (b["count"], b["runs"], b["longest_run_rows"], b["affected_sessions"]) == (2, 1, 2, 1)
    st = channel_stats(src.ts, P[:, 0], pres[:, 0])
    assert st["at_4095_count"] == 2 and st["zero_count"] == 2 and st["out_of_range_count"] == 0


def test_missing_channel_is_not_filled_and_is_schema_invalid():
    p = np.array([[10, 20, 30, 40, 50, 60], [10, 20, 30, 40, 50, MISSING]], float)
    src = make_src(p, schema=[0, 2])
    P, pres = pressure_matrix(src, np.arange(src.n))
    assert np.isnan(P[1, 5]) and not pres[1, 5]                 # never 0
    st = channel_stats(src.ts, P[:, 5], pres[:, 5])
    assert st["missing_rows"] == 1 and st["present_rows"] == 1
    m = pressure_policy_masks(P, pres, src.schema_code, np.zeros(src.n, bool))
    assert m["A_schema_invalid"].tolist() == [False, True]


def test_five_vs_six_channel_schema_through_parser():
    six = [f"08-01 22:00:{i:02d},1,2,3,4,5,6,28,50, LM" for i in range(0, 30, 3)]
    five = ["08-01 22:01:00,1,2,3,4,5,28,50, LM"]                # a 5-value layout cannot be mapped to P1..P6
    rows6 = parse_text("\n".join(six), year_hint=2026)[1]
    rows5 = parse_text("\n".join(five), year_hint=2026)[1]
    src = SourceData.from_rows("s", "User02", "22480", [("six.txt", rows6), ("mixed.txt", rows6[:2] + rows5)])
    sch = {r["file"]: r for r in schema_by_file(src)}
    assert sch["six.txt"]["rows_nonstandard"] == 0 and not sch["six.txt"]["mixed_schema"]
    assert sch["mixed.txt"]["rows_nonstandard"] == 1 and sch["mixed.txt"]["mixed_schema"]
    assert sch["mixed.txt"]["rows_missing_channel"] == 1           # values are not forced into P1..P6
    odd = np.flatnonzero(src.schema_code == 2)[0]
    assert np.all(src.values[odd] == MISSING)                        # temperature is never read as P6


def test_constant_run_categories():
    n = 60                                                       # 3 min at 3 s
    blocks = []
    blocks.append(np.zeros((n, 6)))                              # empty mat
    b = np.zeros((n, 6)); b[:, 1] = np.arange(n) % 5 + 100      # P1 zero while P2 active
    blocks.append(b)
    c = np.zeros((n, 6)); c[:, 0] = 777; c[:, 2] = np.arange(n) + 1   # P1 stuck non-zero, P3 changing
    blocks.append(c)
    d = np.tile([500, 400, 300, 200, 100, 50], (n, 1))           # whole frame identical
    blocks.append(d)
    p = np.vstack(blocks)
    ts = np.arange(T0, T0 + 3 * p.shape[0], 3)
    ts[n:] += 1000                                               # gaps separate the blocks
    ts[2 * n:] += 1000
    ts[3 * n:] += 1000
    src = make_src(p, ts=ts)
    P, pres = pressure_matrix(src, np.arange(src.n))
    fr = frame_flags(P, pres)
    cats = {(r["channel"], r["first"] // n): r["category"] for r in classify_channel_runs(src.ts, P, pres, 0, fr)}
    assert cats[("p1", 0)] == "zero_all_zero"
    assert cats[("p1", 1)] == "zero_others_active"
    assert cats[("p1", 2)] == "nonzero_others_change"
    assert cats[("p1", 3)] == "nonzero_all_constant"


def test_cross_channel_scale_summary():
    p = np.array([[100, 300, 0, 0, 0, 0]] * 10 + [[0] * 6] * 5, float)
    src = make_src(p)
    P, pres = pressure_matrix(src, np.arange(src.n))
    cc = cross_channel(P, pres, frame_flags(P, pres))
    assert cc["loaded_rows"] == 10 and cc["p2_mass_share"] == 0.75 and cc["p2_dominant_share"] == 1.0
    assert cc["active_channels_eq_2"] == 1.0 and cc["pressure_sum_median"] == 400


def test_delta_stats_find_isolated_extreme_spike():
    p = np.array([[100] * 6] * 5 + [[4095, 100, 100, 100, 100, 100]] + [[100] * 6] * 5, float)
    src = make_src(p)
    P, pres = pressure_matrix(src, np.arange(src.n))
    d = {r["series"]: r for r in delta_stats(src.ts, P, pres)}
    assert d["p1"]["isolated_extreme_spikes"] == 1 and d["p1"]["n_abs_ge_3000"] == 2 and d["p2"]["max_abs"] == 0


def test_same_second_observations_are_preserved_and_policy_impact():
    p = np.array([[10] * 6, [11] * 6, [12] * 6, [13] * 6], float)
    ts = [T0, T0 + 3, T0 + 3, T0 + 6]                              # two observations in one second
    src = make_src(p, ts=ts)
    tl = build_timeline(src, "B")
    assert tl.n == 4 and (steps(tl) == 0).sum() == 1
    P, pres = pressure_matrix(src, tl.rows)
    heur = np.array([False, False, True, False])
    imp = {r["policy"]: r for r in row_policy_impact(
        pressure_policy_masks(P, pres, src.schema_code[tl.rows], heur), np.array([0, 0, 1, 1]), 2)}
    assert imp["A_schema_invalid"]["rows_affected"] == 0
    assert imp["C_B_plus_stuck_heuristic"]["rows_affected"] == 1 and imp["C_B_plus_stuck_heuristic"]["sessions_affected"] == 1
