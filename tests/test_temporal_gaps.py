"""Temporal gap and session-boundary analysis (P0 A7). Synthetic log text only — no raw data."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from src.data.duplicates import overlapping_file_pairs, row_keys, upload_copy_mask
from src.data.provenance import SourceData
from src.data.raw_parser import parse_text
from src.data.temporal import (
    bucket_counts, build_timeline, candidate_sessions, chance_alignment_rate, chunk_alignment, gap_context,
    session_rows, session_stats, step_summary, steps,
)

T0 = datetime(2026, 8, 1, 22, 0, 0)


def row(t: datetime, k: int, p0=None, event=" LM") -> str:
    p0 = (k * 37) % 4000 + 1 if p0 is None else p0
    return f"{t:%m-%d %H:%M:%S},{p0},{k % 7},0,{k % 11},5,9,28,50,{event}"


def rows_at(offsets_s, start=T0, first_k=0):
    return [row(start + timedelta(seconds=int(s)), first_k + k) for k, s in enumerate(offsets_s)]


def src_of(files: dict[str, list[str]]) -> SourceData:
    parsed = [(n, parse_text("\n".join(lines), year_hint=2026)[1]) for n, lines in files.items()]
    return SourceData.from_rows("User02_22482", "User02", "22482", parsed)


def n_sessions(src, minutes, exclude=None, bridge=None):
    tl = build_timeline(src, "t", exclude)
    return len(candidate_sessions(tl, minutes * 60, bridge))


def test_normal_sampling_and_jitter_stay_in_the_sampling_class():
    rng = np.random.default_rng(0)
    offs = np.cumsum(rng.choice([2, 3, 3, 3, 4], size=500))   # jittered ~3 s sampling
    src = src_of({"f.txt": rows_at(offs)})
    s = step_summary(steps(build_timeline(src, "t")))
    assert s["median_s"] == 3 and s["share_sampling"] == 1.0
    assert n_sessions(src, 1) == 1


def test_short_missing_interval_is_bucketed_but_not_a_break():
    offs = list(range(0, 300, 3)) + [300 + 12] + list(range(315, 600, 3))
    src = src_of({"f.txt": rows_at(offs)})
    dt = steps(build_timeline(src, "t"))
    b = {x["bucket"]: x["count"] for x in bucket_counts(dt)}
    assert b["5-15 s"] == 1 and step_summary(dt)["n_short_missing"] == 1
    assert n_sessions(src, 1) == 1


def test_long_gap_splits_below_its_length_only():
    offs = list(range(0, 600, 3)) + list(range(600 + 3 * 3600, 600 + 3 * 3600 + 600, 3))
    src = src_of({"f.txt": rows_at(offs)})
    assert [n_sessions(src, m) for m in (1, 60, 120, 240)] == [2, 2, 2, 1]


def test_midnight_crossing_keeps_one_session():
    start = datetime(2026, 8, 1, 23, 50, 0)
    src = src_of({"f.txt": rows_at(range(0, 1200, 3), start=start)})
    tl = build_timeline(src, "t")
    sess = session_rows(src, tl, candidate_sessions(tl, 300))
    assert len(sess) == 1 and sess[0]["crosses_midnight"] and sess[0]["calendar_dates"] == 2


def test_file_boundary_without_and_with_session_break():
    a = rows_at(range(0, 600, 3))
    b_cont = rows_at(range(603, 1200, 3), first_k=200)            # next file 3 s later: same recording
    src = src_of({"d1.txt": a, "d2.txt": b_cont})
    tl = build_timeline(src, "t")
    sess = session_rows(src, tl, candidate_sessions(tl, 60))
    assert len(sess) == 1 and sess[0]["files"] == 2
    b_gap = rows_at(range(600 + 5 * 3600, 600 + 5 * 3600 + 600, 3), first_k=200)
    src2 = src_of({"d1.txt": a, "d2.txt": b_gap})
    ctx = gap_context(src2, build_timeline(src2, "t"), steps(build_timeline(src2, "t")), 60)
    assert n_sessions(src2, 120) == 2 and len(ctx) == 1 and ctx[0]["file_boundary"]


def test_duplicated_chunk_does_not_contaminate_gap_statistics():
    a = rows_at(range(0, 900, 3))
    b = rows_at(range(600, 1500, 3), first_k=200)                  # head of b repeats the last 100 rows of a
    src = src_of({"d1.txt": a, "d2.txt": b})
    keys = row_keys(src)
    mask = upload_copy_mask(src, keys, overlapping_file_pairs(src, keys))
    assert mask.sum() == 100 and np.all(src.file_idx[mask] == 1)   # only the later copy is marked
    dt_raw = steps(build_timeline(src, "A"))
    dt_view = steps(build_timeline(src, "B", mask))
    assert (dt_raw == 0).sum() == 100 and (dt_view == 0).sum() == 0
    assert n_sessions(src, 1) == n_sessions(src, 1, exclude=mask) == 1


def test_threshold_sensitivity_counts_sessions():
    offs, t = [], 0
    for gap in (90, 600, 3000, 3 * 3600):                          # 1.5 min, 10 min, 50 min, 3 h
        offs += list(range(t, t + 300, 3))
        t = offs[-1] + gap
    offs += list(range(t, t + 300, 3))
    src = src_of({"f.txt": rows_at(offs)})
    assert [n_sessions(src, m) for m in (1, 5, 30, 60, 120, 240)] == [5, 4, 3, 2, 2, 1]
    tl = build_timeline(src, "t")
    st = session_stats(session_rows(src, tl, candidate_sessions(tl, 60 * 60)), n_nights=1)
    assert st["sessions"] == 2 and st["sessions_per_recording_night"] == 2


def test_same_second_observations_are_preserved():
    lines = rows_at(range(0, 60, 3))
    lines.insert(5, row(T0 + timedelta(seconds=12), 999, p0=7))  # second reading in the same second
    src = src_of({"f.txt": lines})
    keys = row_keys(src)
    mask = upload_copy_mask(src, keys, overlapping_file_pairs(src, keys))
    tl = build_timeline(src, "B", mask)
    assert tl.n == 21 and (steps(tl) == 0).sum() == 1 and step_summary(steps(tl))["n_same_second"] == 1


def test_chunk_aligned_gaps_and_bridging():
    dt = np.array([3, 1804, 3606, 2000, 5404, 90])
    ca = chunk_alignment(dt)
    assert ca["aligned"].tolist() == [False, True, True, False, True, False]
    assert ca["n_chunks"][[1, 2, 4]].tolist() == [1, 2, 3]
    assert 0 < chance_alignment_rate() < 0.02
    offs = list(range(0, 300, 3)) + list(range(300 + 1804, 300 + 1804 + 300, 3))
    src = src_of({"f.txt": rows_at(offs)})
    tl = build_timeline(src, "t")
    bridge = chunk_alignment(steps(tl))["aligned"]
    assert n_sessions(src, 10) == 2 and n_sessions(src, 10, bridge=bridge) == 1
