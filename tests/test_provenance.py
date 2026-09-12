"""Cross-source provenance detection (P0 A1). Synthetic fixtures only — no raw data."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from src.data.provenance import (
    CHANNELS, MISSING, Thresholds, SourceData, by_date, common_channels, compare, file_correspondence,
    is_suspicious, pair_scope,
)
from src.data.raw_parser import parse_text
from src.data.subject_mapping import resolve_source

START = datetime(2026, 1, 1, 22, 0, 0)
EPOCH = datetime(1970, 1, 1)


def synth(seed: int, n: int = 600, absent: int = 100, step_s: int = 3, start: datetime = START,
          files: int = 1) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Random occupied recording preceded by an empty-mat period; T/H vary slowly."""
    rng = np.random.default_rng(seed)
    t0 = int((start - EPOCH).total_seconds())
    ts = t0 + step_s * np.arange(n, dtype=np.int64)
    vals = np.zeros((n, len(CHANNELS)), dtype=np.int16)
    vals[absent:, :6] = rng.integers(0, 4096, size=(n - absent, 6))
    vals[:, 6] = 25 + (np.arange(n) // 200)
    vals[:, 7] = 42 + (np.arange(n) // 300)
    fidx = (np.arange(n) * files // n).astype(np.int32)
    return ts, vals, fidx


def src(sid, subject, ts, vals, fidx, device="unknown"):
    n_files = int(fidx.max()) + 1 if fidx.size else 0
    return SourceData(sid, subject, device, [f"{sid}/f{i}.txt" for i in range(n_files)], ts, vals, fidx)


def modes(a, b):
    return {m: compare(a, b, m) for m in ("A_exact_ts_values", "B_minute_ts_values", "C_value_sequence")}


def test_exact_duplicate_is_detected_in_all_modes():
    ts, v, f = synth(1)
    a, b = src("sa", "UserA", ts, v, f), src("sb", "UserB", ts.copy(), v.copy(), f.copy())
    for m, res in modes(a, b).items():
        assert res.ratio_a == pytest.approx(1.0) and res.ratio_b == pytest.approx(1.0), m
        assert is_suspicious("cross_subject", res), m
    res = compare(a, b, "A_exact_ts_values")
    assert res.longest_ordered_run == 500           # every informative row, in order
    assert res.offset_s_min == res.offset_s_max == 0


def test_partial_duplicate_is_detected_and_quantified():
    ts, v, f = synth(1)
    ts2, v2, f2 = synth(2)
    v2[300:450] = v[200:350]                         # copy a 150-row block of A into B
    ts2[300:450] = ts[200:350]
    a, b = src("sa", "UserA", ts, v, f), src("sb", "UserB", ts2, v2, f2)
    res = compare(a, b, "A_exact_ts_values")
    assert res.informative_matched_a == 150 and res.informative_matched_b == 150
    assert res.matched_a == 150 + 100                # + the shared empty-mat rows (same clock, same T/H)
    assert res.ratio_a == pytest.approx(250 / 600)
    assert res.longest_ordered_run == 150
    assert is_suspicious("cross_subject", res)
    assert compare(a, b, "C_value_sequence").longest_ordered_run == 150 - 5 + 1


def test_minute_resolution_export_is_detected_by_mode_b_and_c():
    ts, v, f = synth(3)
    minute_ts = (ts // 60) * 60                      # export that dropped seconds
    a, b = src("parent", "UserA", ts, v, f), src("export", "UserB", minute_ts, v.copy(), f.copy())
    r = modes(a, b)
    # exact timestamps: only occupied rows that happened at :00 match (1 in 20 at a 3 s interval)
    assert r["A_exact_ts_values"].informative_matched_b == 500 // 20
    assert r["B_minute_ts_values"].ratio_a == pytest.approx(1.0)
    assert r["B_minute_ts_values"].ratio_b == pytest.approx(1.0)
    assert r["C_value_sequence"].ratio_a == pytest.approx(1.0)
    c = r["C_value_sequence"]
    assert -59 <= c.offset_s_min <= c.offset_s_max <= 0   # export timestamp = parent floored to minute


def test_ordered_run_survives_repeated_rows_within_a_minute():
    ts, v, f = synth(10, absent=0)
    v[1::2] = v[0::2]                                # static body: every value pair repeats
    a = src("parent", "UserA", ts, v, f)
    b = src("export", "UserB", (ts // 60) * 60, v.copy(), f.copy())
    assert compare(a, b, "B_minute_ts_values").longest_ordered_run == 600


def test_minute_resolution_export_detected_through_parser():
    rng = np.random.default_rng(4)
    parent, export = [], ["TS(YYYY-MM-DD HH:MM),FSR1(A0),FSR2(A1),FSR3(A2),FSR4(A3),FSR5(A4),FSR6(A5),Temp(℃),Hum(%),Event"]
    for i in range(300):
        t = START + timedelta(seconds=3 * i)
        p = ",".join(str(x) for x in rng.integers(1, 4096, 6))
        parent.append(f"{t:%Y-%m-%d %H:%M:%S},{p},26,40, 좌로이동")
        export.append(f"{t:%Y-%m-%d} {t.hour}:{t:%M},{p},26,40, 좌로이동")
    _, rows_p, *_ = parse_text("\n".join(parent))
    _, rows_e, *_ = parse_text("\n".join(export))
    a = SourceData.from_rows("parent", "UserA", "unknown", [("p.txt", rows_p)])
    b = SourceData.from_rows("export", "UserB", "unknown", [("e.csv", rows_e)])
    assert compare(a, b, "B_minute_ts_values").ratio_b == pytest.approx(1.0)
    assert compare(a, b, "A_exact_ts_values").ratio_b < 0.1


def test_independent_sources_do_not_match():
    ts, v, f = synth(5)
    ts2, v2, f2 = synth(6)                           # same clock, same empty-mat rows, same T/H
    stuck = np.array([4095, 0, 0, 0, 0, 0, 25, 42], dtype=np.int16)
    v[150:170], v2[400:420] = stuck, stuck           # identical constant pattern at different times
    a, b = src("sa", "UserA", ts, v, f), src("sb", "UserB", ts2, v2, f2)
    r = modes(a, b)
    assert r["B_minute_ts_values"].matched_a > 0     # empty-mat rows coincide ...
    for m, res in r.items():
        assert res.informative_matched_a == 0 and res.informative_matched_b == 0, m   # ... but carry no evidence
        assert not is_suspicious("cross_subject", res), m
    assert r["C_value_sequence"].matched_a == 0      # constant k-grams are excluded


def test_same_subject_devices_are_not_cross_subject_conflicts():
    s22480 = resolve_source("user02/mat_22480/sm22480_0719.txt")
    s22482 = resolve_source("user02/mat_22482/sm22482_0719.txt")
    assert pair_scope(s22480.subject_id, s22482.subject_id) == "same_subject"
    ts, v, f = synth(7)
    a = src("user02_mat_22480", s22480.subject_id, ts, v, f, device="22480")
    b = src("user02_mat_22482", s22482.subject_id, ts.copy(), v.copy(), f.copy(), device="22482")
    res = compare(a, b, "A_exact_ts_values")
    assert res.ratio_a == pytest.approx(1.0)          # overlap is measured ...
    assert not is_suspicious(pair_scope(a.subject_id, b.subject_id), res)   # ... but never a cross-subject flag
    assert a.subject_id == b.subject_id == "User02" and {a.device_id, b.device_id} == {"22480", "22482"}


def test_only_common_channels_are_compared():
    ts, v, f = synth(8)
    v_missing = v.copy()
    v_missing[:, 5] = MISSING                        # source without P6
    a, b = src("sa", "UserA", ts, v, f), src("sb", "UserB", ts.copy(), v_missing, f.copy())
    assert "p6" not in common_channels(a, b)
    res = compare(a, b, "A_exact_ts_values")
    assert "p6" not in res.channels and res.ratio_a == pytest.approx(1.0)


def test_by_date_and_file_correspondence():
    ts, v, f = synth(9, n=2400, absent=0, files=2, start=datetime(2026, 1, 1, 23, 0))  # crosses midnight
    keep = slice(50, 2350)                           # export cropped at both ends
    a = src("parent", "UserA", ts, v, f)
    b = src("export", "UserB", (ts[keep] // 60) * 60, v[keep].copy(), np.zeros(2300, np.int32))
    res = compare(a, b, "B_minute_ts_values")
    days = by_date(a, b, res)
    assert [d["date"] for d in days] == ["2026-01-01", "2026-01-02"]
    assert sum(d["matched_rows_a"] for d in days) == res.matched_a == 2300
    corr = file_correspondence(a, b, res)
    assert [c["file_b"] for c in corr] == ["export/f0.txt", "export/f0.txt"]
    first = corr[0]
    assert first["a_unmatched_leading"] == 50 and first["a_unmatched_interior"] == 0


def test_thresholds_are_explicit():
    th = Thresholds()
    assert th.min_informative_matches > 1 and th.min_ordered_run > 1


def test_non_integer_values_are_rejected():
    from src.data.raw_parser import DataRow
    row = DataRow(1, "x", "ymd_hms", START, "explicit", ",", 8, "p6_t_h", None,
                  (1.5, 0, 0, 0, 0, 0), 25, 40, "", None, None, None, True)
    with pytest.raises(ValueError):
        SourceData.from_rows("s", "UserA", "unknown", [("f", [row])])
