"""Protocol v1.0 windowing (docs/EXPERIMENT_PROTOCOL.md §7, D-032).

Deterministic time binning of observed rows. No value is interpolated, resampled, averaged or filled:
- rows are ordered by (group, timestamp, within_timestamp_order), as in canonical_v1;
- a continuity segment is a run of rows of one group with every inter-row gap <= max_gap_s;
- a window [t0, t0 + duration_s) lies inside one segment and is cut into n_steps bins of bin_s seconds;
- each step is the LAST observed row of its bin (ties within a second: the last row in canonical order);
- the target row is the row of the last step (window end); no row after it is used.

Because every gap inside a segment is <= max_gap_s and bin_s == max_gap_s, every bin of a window with
seg_start <= t0 and t0 + duration_s - bin_s <= seg_end holds at least one row, and no row of another segment can
fall inside the window (the next segment starts more than max_gap_s after seg_end).

`group` must already encode every boundary a window may not cross (subject, device, session, sensor phase,
channel-quality phase, split partition and, for RQ2, the night). `group_key` builds it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class WindowingError(ValueError):
    pass


@dataclass(frozen=True)
class WindowSpec:
    duration_s: int = 40
    bin_s: int = 5
    stride_s: int = 20
    max_gap_s: int = 5

    def __post_init__(self):
        if self.duration_s % self.bin_s:
            raise WindowingError("duration_s must be a multiple of bin_s")
        if self.bin_s != self.max_gap_s:
            raise WindowingError("bin_s must equal max_gap_s (guarantees an observed row in every bin)")
        if self.stride_s <= 0:
            raise WindowingError("stride_s must be positive")

    @property
    def n_steps(self) -> int:
        return self.duration_s // self.bin_s

    @property
    def min_span_s(self) -> int:
        """Smallest segment span (last - first timestamp) that holds one window."""
        return self.duration_s - self.bin_s


@dataclass
class Windows:
    group: np.ndarray        # (n,) group code of each window
    t0: np.ndarray           # (n,) window start (naive local seconds)
    step_rows: np.ndarray    # (n, n_steps) row index of the observation used at each step
    target_row: np.ndarray   # (n,) row index of the target (= last step)
    segment: np.ndarray      # (n,) continuity segment of each window

    def __len__(self) -> int:
        return int(self.t0.size)


def group_key(*labels: np.ndarray) -> np.ndarray:
    """Integer code for the combination of boundary labels (equal labels -> equal code)."""
    if not labels:
        raise WindowingError("at least one boundary label is needed")
    stacked = np.stack([np.asarray(x).astype(str) for x in labels], axis=1)
    _, code = np.unique(stacked, axis=0, return_inverse=True)
    return code.reshape(-1).astype(np.int64)


def check_order(ts: np.ndarray, group: np.ndarray) -> None:
    """Rows must be contiguous per group and time-ordered inside it."""
    ts, group = np.asarray(ts), np.asarray(group)
    change = np.flatnonzero(group[1:] != group[:-1]) + 1
    if np.unique(group[np.r_[0, change]]).size != change.size + 1:
        raise WindowingError("rows of a group are not contiguous")
    same = group[1:] == group[:-1]
    if np.any(np.diff(ts)[same] < 0):
        raise WindowingError("rows are not time-ordered inside a group")


def continuity_segments(ts: np.ndarray, group: np.ndarray, max_gap_s: int) -> np.ndarray:
    """Segment id per row: a new segment at every group change or inter-row gap > max_gap_s."""
    ts, group = np.asarray(ts, np.int64), np.asarray(group)
    check_order(ts, group)
    if ts.size == 0:
        return np.zeros(0, np.int64)
    new = np.r_[True, (group[1:] != group[:-1]) | (np.diff(ts) > max_gap_s)]
    return np.cumsum(new) - 1


def build_windows(ts: np.ndarray, group: np.ndarray, spec: WindowSpec) -> Windows:
    ts, group = np.asarray(ts, np.int64), np.asarray(group)
    seg = continuity_segments(ts, group, spec.max_gap_s)
    n_seg = int(seg[-1]) + 1 if seg.size else 0
    first = np.searchsorted(seg, np.arange(n_seg), side="left")
    last = np.searchsorted(seg, np.arange(n_seg), side="right") - 1
    t0s, segs = [], []
    for s in range(n_seg):
        start, end = ts[first[s]], ts[last[s]]
        if end - start < spec.min_span_s:
            continue
        k = np.arange((end - spec.min_span_s - start) // spec.stride_s + 1, dtype=np.int64)
        t0s.append(start + k * spec.stride_s)
        segs.append(np.full(k.size, s, np.int64))
    if not t0s:
        e = np.zeros(0, np.int64)
        return Windows(e, e, np.zeros((0, spec.n_steps), np.int64), e, e)
    t0 = np.concatenate(t0s)
    wseg = np.concatenate(segs)
    # last row with ts < bin end inside the window's own segment: (segment, ts) is globally sorted
    base = np.int64(1) << 34
    if ts.min() < 0 or ts.max() >= base:
        raise WindowingError("timestamps out of the supported range")
    key = seg * base + ts
    bin_end = t0[:, None] + spec.bin_s * np.arange(1, spec.n_steps + 1)[None, :]
    rows = np.searchsorted(key, wseg[:, None] * base + bin_end, side="left") - 1
    w = Windows(group[rows[:, 0]], t0, rows, rows[:, -1], wseg)
    validate_windows(ts, group, w, spec)
    return w


def validate_windows(ts: np.ndarray, group: np.ndarray, w: Windows, spec: WindowSpec) -> None:
    """Every window is inside one group and one gap-free run, each step inside its own bin, target = last step."""
    ts, group = np.asarray(ts, np.int64), np.asarray(group)
    if len(w) == 0:
        return
    rows = w.step_rows
    bin_start = w.t0[:, None] + spec.bin_s * np.arange(spec.n_steps)[None, :]
    st = ts[rows]
    if np.any(st < bin_start) or np.any(st >= bin_start + spec.bin_s):
        raise WindowingError("a step row lies outside its bin (empty bin or wrong row)")
    if np.any(np.diff(rows, axis=1) <= 0):
        raise WindowingError("step rows are not strictly increasing")
    if np.any(group[rows] != w.group[:, None]):
        raise WindowingError("a window crosses a group boundary (session/phase/partition)")
    if np.any(w.target_row != rows[:, -1]):
        raise WindowingError("target row is not the last step")
    # every consecutive row pair between the first and the last step: same group, gap <= max_gap_s
    gap_ok = np.r_[True, (group[1:] == group[:-1]) & (np.diff(ts) <= spec.max_gap_s)]
    bad = np.cumsum(~gap_ok)
    if np.any(bad[rows[:, -1]] != bad[rows[:, 0]]):
        raise WindowingError("a window spans an inter-row gap > max_gap_s or a group change")


def labelled(w: Windows, temp_valid: np.ndarray, humid_valid: np.ndarray) -> np.ndarray:
    """Windows that carry a label: both targets valid at the target row (D-025 flags; nothing repaired)."""
    return np.asarray(temp_valid, bool)[w.target_row] & np.asarray(humid_valid, bool)[w.target_row]
