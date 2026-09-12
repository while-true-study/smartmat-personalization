"""Protocol v1.0 windowing rule (synthetic rows only; D-032)."""
from __future__ import annotations

import numpy as np
import pytest

from src.evaluation.protocol import load_protocol, window_spec
from src.evaluation.windowing import (WindowingError, WindowSpec, build_windows, continuity_segments, group_key,
                                      labelled, validate_windows)

SPEC = WindowSpec(duration_s=40, bin_s=5, stride_s=20, max_gap_s=5)


def run(ts, groups=None):
    ts = np.asarray(ts, np.int64)
    g = np.zeros(ts.size, np.int64) if groups is None else np.asarray(groups)
    return ts, g, build_windows(ts, g, SPEC)


def test_protocol_window_parameters_are_frozen():
    w = load_protocol()["window"]
    spec = window_spec()
    assert (spec.duration_s, spec.bin_s, spec.stride_s, spec.max_gap_s, spec.n_steps) == (40, 5, 20, 5, 8)
    assert (w["duration_s"], w["n_steps"], w["stride_s"], w["max_gap_s"]) == (40, 8, 20, 5)
    assert window_spec(20).stride_s == 10 and window_spec(30).n_steps == 6


def test_fixed_shape_last_observation_per_bin_without_interpolation():
    ts, g, w = run(np.arange(1000, 1100, 3))                      # regular 3-s rows, 100 s
    assert w.step_rows.shape[1] == 8 and len(w) == 4              # t0 = 1000, 1020, 1040, 1060
    for i in range(len(w)):
        for k, r in enumerate(w.step_rows[i]):
            in_bin = np.flatnonzero((ts >= w.t0[i] + 5 * k) & (ts < w.t0[i] + 5 * k + 5))
            assert r == in_bin[-1]                                  # an observed row: the last one in the bin
    assert np.all(w.target_row == w.step_rows[:, -1])


def test_every_bin_is_observed_when_gaps_are_at_most_5_s():
    rng = np.random.default_rng(0)
    ts = 5000 + np.cumsum(rng.integers(1, 6, 400))                # gaps 1..5 s
    _, _, w = run(ts)
    st = ts[w.step_rows]
    bins = w.t0[:, None] + 5 * np.arange(8)[None, :]
    assert len(w) > 0 and np.all((st >= bins) & (st < bins + 5))


def test_gap_above_max_rejects_window_across_it():
    ts = np.r_[np.arange(0, 60, 3), np.arange(66, 130, 3)]       # one 9-s gap at 57 -> 66
    _, _, w = run(ts)
    seg = continuity_segments(ts, np.zeros(ts.size), 5)
    assert seg.max() == 1
    for i in range(len(w)):
        assert np.unique(seg[w.step_rows[i]]).size == 1           # never spans the gap
    assert not np.any((w.t0 < 57) & (w.t0 + 40 > 66))


def test_session_and_phase_boundaries_are_never_crossed():
    ts = np.arange(0, 240, 3)
    session = np.where(ts < 120, "S1", "S2")                       # no time gap at the boundary
    phase = np.where(ts < 60, "s1", "s2")
    g = group_key(session, phase)
    _, _, w = run(ts, g)
    assert len(w) > 0
    for i in range(len(w)):
        assert np.unique(session[w.step_rows[i]]).size == 1 and np.unique(phase[w.step_rows[i]]).size == 1


def test_validate_rejects_windows_crossing_boundaries_or_gaps():
    ts = np.arange(0, 120, 3)
    g = np.where(ts < 60, 0, 1)
    _, _, w = run(ts, np.zeros(ts.size, np.int64))                 # windows built WITHOUT the boundary ...
    with pytest.raises(WindowingError):
        validate_windows(ts, g, w, SPEC)                           # ... are rejected once the boundary is known
    gap_ts = ts.copy()
    gap_ts[20:] += 7
    with pytest.raises(WindowingError):
        validate_windows(gap_ts, np.zeros(ts.size, np.int64), w, SPEC)


def test_same_second_ties_use_last_row_in_canonical_order():
    ts = np.array([0, 3, 3, 6, 9, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42])
    _, _, w = run(ts)
    assert w.step_rows[0, 0] == 2                                  # bin [0,5): rows 0,1,2 -> row 2 (second at t=3)
    assert w.step_rows[0, 1] == 5                                  # bin [5,10): rows 3,4,5 -> row 5 (second at t=9)


def test_unordered_or_non_contiguous_groups_are_refused():
    with pytest.raises(WindowingError):
        continuity_segments(np.array([0, 3, 1]), np.zeros(3), 5)
    with pytest.raises(WindowingError):
        continuity_segments(np.array([0, 3, 6]), np.array([0, 1, 0]), 5)


def test_invalid_target_at_window_end_gives_no_label():
    ts = np.arange(0, 100, 3)
    _, _, w = run(ts)
    temp_ok = np.ones(ts.size, bool)
    temp_ok[w.target_row[0]] = False                               # zero sentinel at the first window's end
    lab = labelled(w, temp_ok, np.ones(ts.size, bool))
    assert not lab[0] and lab[1:].all()


def test_short_segments_give_no_window_and_spec_is_guarded():
    _, _, w = run(np.arange(0, 33, 3))                             # span 30 s < 35 s
    assert len(w) == 0
    with pytest.raises(WindowingError):
        WindowSpec(duration_s=40, bin_s=4, stride_s=20, max_gap_s=5)
