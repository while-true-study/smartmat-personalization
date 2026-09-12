"""Temperature / humidity target-quality audit (P0 A8). Synthetic values and log text only — no raw data."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from src.data.duplicates import overlapping_file_pairs, row_keys, timestamp_conflicts, upload_copy_mask
from src.data.provenance import SourceData
from src.data.raw_parser import parse_text
from src.data.target_quality import (
    channel_states, chunk_positions, classify_zero_runs, constant_runs, flagged_runs, jump_candidates, jump_summary,
    neighbour_valid,
    policy_impact, policy_masks, row_patterns, run_summary, session_ids, spike_candidates, target_summary,
    valid_steps,
)
from src.data.temporal import build_timeline

T0 = datetime(2026, 8, 1, 22, 0, 0)


def arr(*v):
    return np.array(v, dtype=float)


def src_of(files: dict[str, list[str]], device="22480") -> SourceData:
    parsed = [(n, parse_text("\n".join(lines), year_hint=2026)[1]) for n, lines in files.items()]
    return SourceData.from_rows(f"User02_{device}", "User02", device, parsed)


def line(i, temp=28, humid=50, event=" LM", step=3):
    t = T0 + timedelta(seconds=step * i)
    return f"{t:%m-%d %H:%M:%S},{i * 37 % 4000 + 1},{i % 7},0,{i % 11},5,9,{temp},{humid},{event}"


def test_zero_sentinel_is_detected_jointly_and_kept_apart_from_single_zeros():
    t = arr(28, 0, 29, 0, 30)
    h = arr(50, 0, 51, 52, 0)
    ts, hs = channel_states(t, "temp"), channel_states(h, "humid")
    p = row_patterns(ts, hs)
    assert p["joint_zero"].tolist() == [False, True, False, False, False]
    assert p["temp_zero_only"].tolist() == [False, False, False, True, False]
    assert p["humid_zero_only"].tolist() == [False, False, False, False, True]
    assert ts["valid"].tolist() == [True, False, True, False, True]


def test_extreme_glitch_is_detected_but_values_are_untouched():
    t = arr(29, -254, 256, 30)
    h = arr(60, 0, 152, 61)
    ts, hs = channel_states(t, "temp"), channel_states(h, "humid")
    assert ts["extreme_low"].tolist() == [False, True, False, False]
    assert ts["extreme_high"].tolist() == [False, False, True, False]
    assert hs["extreme_high"].tolist() == [False, False, True, False]
    assert t.tolist() == [29, -254, 256, 30]                        # raw values unchanged
    assert row_patterns(ts, hs)["extreme_with_other_zero"].tolist() == [False, True, False, False]


def test_nan_and_missing_are_separate_states():
    x = arr(28, np.nan, np.inf, 30)
    miss = np.array([False, True, False, False])
    st = channel_states(x, "temp", miss)
    assert st["missing"].tolist() == [False, True, False, False]
    assert st["non_finite"].tolist() == [False, False, True, False]
    assert st["valid"].tolist() == [True, False, False, True]


def test_jumps_skip_invalid_rows_and_separate_long_gaps():
    ts = np.array([0, 3, 6, 9, 9 + 7200, 9 + 7203])
    t = arr(28, 0, 28, 29, 34, 34)                                   # sentinel in the middle; +5 after a 2 h gap
    st = channel_states(t, "temp")
    vs = valid_steps(ts, t, st["valid"])
    assert vs.dx.tolist() == [0, 1, 5, 0] and vs.dt.tolist() == [6, 3, 7200, 3]
    rows = {r["dt_class"]: r for r in jump_summary(vs, "temp")}
    assert rows[">30 min"]["max_abs"] == 5 and rows["<=5 s"]["max_abs"] == 1
    assert not jump_candidates(vs, t.size, 3).any()                  # the 5-degree change is after a gap, not a jump


def test_abrupt_jump_and_spike_candidates():
    ts = np.arange(0, 30, 3)
    t = arr(28, 28, 28, 36, 28, 28, 28, 33, 33, 33)                 # spike at 3; step change at 7
    st = channel_states(t, "temp")
    vs = valid_steps(ts, t, st["valid"])
    assert np.flatnonzero(jump_candidates(vs, t.size, 3)).tolist() == [3, 4, 7]
    assert np.flatnonzero(spike_candidates(vs, t.size, 3)).tolist() == [3]


def test_constant_runs_break_on_value_change_and_long_gap():
    ts = np.array([0, 3600, 7200, 7203, 7203 + 4000, 7203 + 4003])
    t = arr(29, 29, 29, 30, 30, 30)
    runs = constant_runs(ts, t, np.ones(t.size, bool), break_s=1800)
    # every gap here except 7200 -> 7203 exceeds 1800 s, so runs break there as well as at the value change
    assert [(a, b, v) for a, b, v in runs] == [(0, 0, 29), (1, 1, 29), (2, 2, 29), (3, 3, 30), (4, 5, 30)]
    runs2 = constant_runs(ts, t, np.ones(t.size, bool), break_s=5000)
    assert [(a, b) for a, b, _ in runs2] == [(0, 2), (3, 5)]
    assert run_summary(ts, runs2)["max_run_h"] == 2.0


def test_same_second_target_conflict_is_detected_and_preserved():
    rows = [line(i) for i in range(20)]
    rows.insert(6, line(5, temp=0, humid=0, event="AHON LM"))       # same second, sentinel values, control event
    src = src_of({"d.txt": rows})
    keys = row_keys(src)
    conf = timestamp_conflicts(src, keys)
    assert len(conf) == 1 and conf[0]["kind"] == "target_conflict" and conf[0]["involves_th_sentinel"]
    copies = upload_copy_mask(src, keys, overlapping_file_pairs(src, keys))
    tl = build_timeline(src, "B", copies)
    assert tl.n == 21                                                # both observations stay in the timeline


def test_chunk_position_marks_chunk_start_sentinel():
    lines = ['{', ' "2026-08-01_22-30-00": {', '  "csvData": "timestamp,P1,P2,P3,P4,P5,P6,temp,humid,event',
             line(0, temp=0, humid=0), *[line(i) for i in range(1, 6)], '"', ' },',
             ' "2026-08-01_23-00-00": {', '  "csvData": "timestamp,P1,P2,P3,P4,P5,P6,temp,humid,event',
             line(6, temp=0, humid=0), *[line(i) for i in range(7, 10)], '"', ' }', '}']
    src = src_of({"d.txt": lines})
    pos, size = chunk_positions(src)
    zero = (src.values[:, 6] == 0) & (src.values[:, 7] == 0)
    assert pos[zero].tolist() == [0, 0] and size[zero].tolist() == [6, 4]


def test_zero_runs_separate_start_sentinels_from_dropouts():
    ts = np.arange(0, 60, 3)
    jz = np.zeros(ts.size, bool)
    jz[[0, 7, 8, 9, 15]] = True                                     # start row, a 3-row dropout, a single dropout
    start_like = np.zeros(ts.size, bool)
    start_like[0] = True
    runs = flagged_runs(ts, jz)
    assert runs == [(0, 0), (7, 9), (15, 15)]
    assert classify_zero_runs(runs, start_like) == ["start_sentinel", "dropout_run", "dropout_run"]


def test_neighbour_context_and_policy_impact():
    ts = np.arange(0, 30, 3)
    t = arr(28, 0, 28, 28, -254, 28, 28, 40, 28, 28)
    h = arr(50, 0, 50, 50, 0, 50, 50, 50, 50, 50)
    tst, hst = channel_states(t, "temp"), channel_states(h, "humid")
    ctx = neighbour_valid(ts, t, tst["valid"], np.array([1]))
    assert ctx["prev_value"][0] == 28 and ctx["next_value"][0] == 28 and ctx["next_dt_s"][0] == 3
    jt = jump_candidates(valid_steps(ts, t, tst["valid"]), t.size, 3)
    jh = jump_candidates(valid_steps(ts, h, hst["valid"]), h.size, 10)
    masks = policy_masks(tst, hst, jt, jh)
    sid = session_ids(t.size, [(0, 4), (5, 9)])
    imp = {r["policy"]: r for r in policy_impact(masks, sid, 2)}
    assert imp["A_joint_zero_sentinel"]["rows_any_invalid"] == 1 and imp["A_joint_zero_sentinel"]["sessions_affected"] == 1
    assert imp["B_zero_plus_extreme_glitch"]["rows_any_invalid"] == 2      # the -254 row and its humidity 0
    assert imp["B_zero_plus_extreme_glitch"]["humid_invalid"] == 2
    assert imp["C_B_plus_abrupt_jump_candidates"]["temp_invalid"] == 4      # + jump into 40 and back out
    assert imp["C_B_plus_abrupt_jump_candidates"]["sessions_affected"] == 2


def test_summaries_are_per_device():
    a = src_of({"a.txt": [line(i, temp=29) for i in range(30)]}, device="22480")
    b = src_of({"b.txt": [line(i, temp=31 + i % 3, humid=70) for i in range(30)]}, device="22482")
    sa, sb = target_summary(a, np.arange(a.n)), target_summary(b, np.arange(b.n))
    assert sa["temp_unique_values"] == 1 and sa["temp_most_frequent_ratio"] == 1.0
    assert sb["temp_unique_values"] == 3 and sb["humid_median"] == 70
    assert sa["rows_both_valid_pct"] == sb["rows_both_valid_pct"] == 100.0
