"""Cross-file duplicate and overlap analysis (P0 A5). Synthetic log text only — no raw data."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from src.data.duplicates import (
    cross_device_equality, duplicate_counts, file_boundaries, file_ranges, metadata_only_differences,
    overlapping_file_pairs, policy_impact, repeated_chunk_keys, repeated_sequences, row_keys, timestamp_conflicts,
    within_file_repeated_blocks,
)
from src.data.provenance import SourceData
from src.data.raw_parser import parse_text

START = datetime(2026, 8, 1, 22, 0, 0)


def line(i, p0=None, temp=28, humid=50, event=" LM", step=3):
    t = START + timedelta(seconds=step * i)
    p0 = (i * 37) % 4000 + 1 if p0 is None else p0
    return f"{t:%m-%d %H:%M:%S},{p0},{i % 7},0,{i % 11},5,9,{temp},{humid},{event}"


def source(files: dict[str, list[str]], subject="User02", device="22480") -> SourceData:
    parsed = [(name, parse_text("\n".join(lines), year_hint=2026)[1]) for name, lines in files.items()]
    return SourceData.from_rows(f"{subject}_{device}", subject, device, parsed)


def analyse(src):
    k = row_keys(src)
    pairs = overlapping_file_pairs(src, k)
    return k, duplicate_counts(src, k), pairs, repeated_sequences(src, k, pairs)


def test_repeated_upload_block_is_an_exact_cross_file_duplicate():
    a = [line(i) for i in range(100)]
    b = [line(i) for i in range(60, 150)]            # last 40 rows of A are repeated at the head of B
    src = source({"d1.txt": a, "d2.txt": b})
    k, c, pairs, seqs = analyse(src)
    assert c["raw_rows"] == 190 and c["exact_duplicate_rows"] == 40
    assert c["exact_duplicates_across_files"] == 40 and c["exact_duplicates_within_file"] == 0
    assert c["conflicting_timestamps"] == 0
    assert pairs[0]["relation"] == "duplicate_block" and pairs[0]["overlapping_timestamps"] == 40
    s = seqs[0]
    assert s["matched_rows"] == 40 and s["at_end_of_a"] and s["at_start_of_b"] and s["identical_incl_event"]
    assert s["a_line_start"] == 61 and s["b_line_start"] == 1   # original row positions are kept


def test_partial_overlap_with_conflicting_values():
    a = [line(i) for i in range(100)]
    b = [line(i) for i in range(80, 90)] + [line(i, p0=4095) for i in range(90, 100)] + [line(i) for i in range(100, 120)]
    src = source({"d1.txt": a, "d2.txt": b})
    k, c, pairs, seqs = analyse(src)
    p = pairs[0]
    assert p["relation"] == "partial_duplicate"
    assert p["shared_sensor_target_rows"] == 10 and p["conflicting_timestamps_between_files"] == 10
    assert c["conflicting_timestamps"] == 10
    conf = timestamp_conflicts(src, k)
    assert len(conf) == 10 and {r["kind"] for r in conf} == {"sensor_conflict"}
    assert all(not r["same_file"] and r["origin"] == "between_files" for r in conf)
    assert all(r["max_pressure_diff"] > 0 for r in conf)
    assert seqs[0]["matched_rows"] == 10


def test_same_timestamp_same_values_different_event_is_metadata_only():
    rows = [line(i) for i in range(20)]
    rows.insert(6, line(5, event="AHON LM"))         # same second and values as row 5, extra control text
    src = source({"d1.txt": rows})
    k, c, _, _ = analyse(src)
    assert c["metadata_only_extra_rows"] == 1 and c["conflicting_timestamps"] == 0 and c["exact_duplicate_rows"] == 0
    assert metadata_only_differences(src, k)[0]["count"] == 1
    pol = {p["policy"]: p for p in policy_impact(c, minute_resolution=False)}
    assert pol["B_same_timestamp_same_values"]["status"] == "requires_decision_metadata"


def test_same_timestamp_conflicting_target_is_flagged_with_context():
    rows = [line(i) for i in range(20)]
    rows.insert(4, line(3, temp=0, humid=0, event="AHON LM"))   # chunk-start style sentinel + control event
    src = source({"d1.txt": rows})
    k, c, _, _ = analyse(src)
    conf = timestamp_conflicts(src, k)
    assert c["conflicting_timestamps"] == 1 and len(conf) == 1
    r = conf[0]
    assert r["kind"] == "target_conflict" and r["involves_th_sentinel"] and r["involves_control_event"]
    assert r["same_file"] and r["origin"] == "within_file" and r["adjacent_lines"]


def test_within_file_conflict_copied_with_its_chunk_is_not_a_between_file_conflict():
    rows = [line(i) for i in range(30)]
    rows.insert(21, line(20, p0=7, event="AHON LM"))  # same-second double log inside file 1
    copy = rows[15:]                                  # upload chunk repeated at the head of file 2
    src = source({"d1.txt": rows, "d2.txt": copy})
    conf = timestamp_conflicts(src, row_keys(src))
    assert len(conf) == 1 and conf[0]["origin"] == "within_file" and not conf[0]["same_file"]
    assert conf[0]["adjacent_lines"]


def test_upload_chunk_repeated_inside_one_file():
    rows = [line(i) for i in range(100)] + [line(i) for i in range(40, 70)] + [line(i) for i in range(100, 120)]
    src = source({"d1.txt": rows})
    k = row_keys(src)
    c = duplicate_counts(src, k)
    assert c["exact_duplicates_within_file"] == 30 and c["exact_duplicates_within_file_adjacent"] == 0
    blocks = within_file_repeated_blocks(src, k)
    assert len(blocks) == 1 and blocks[0]["matched_rows"] == 30
    assert blocks[0]["a_line_start"] == 101 and blocks[0]["b_line_start"] == 41


def test_non_overlapping_files_have_no_pairs_and_a_gap_boundary():
    a = [line(i) for i in range(50)]
    b = [line(i) for i in range(2000, 2050)]         # starts ~1.6 h after A ends
    src = source({"d1.txt": a, "d2.txt": b})
    k, c, pairs, seqs = analyse(src)
    assert pairs == [] and seqs == [] and c["exact_duplicate_rows"] == 0
    bnd = file_boundaries(src, pairs)
    assert bnd[0]["boundary_kind"] == "gap" and bnd[0]["gap_bin"] == "1800-7200s"
    fr = file_ranges(src)
    assert [f["rows"] for f in fr] == [50, 50]


def test_overlap_without_shared_rows_is_time_overlap_only():
    a = [line(i) for i in range(100)]
    b = [line(i, p0=3999 - i) for i in range(50, 60)]  # same clock, different values -> not a copy
    src = source({"d1.txt": a, "d2.txt": b})
    k, c, pairs, _ = analyse(src)
    assert pairs[0]["relation"] == "time_overlap_only" and pairs[0]["shared_sensor_target_rows"] == 0
    assert pairs[0]["overlapping_timestamps"] == 10 and c["conflicting_timestamps"] == 10


def test_cross_device_records_are_not_dedup_candidates():
    rows = [line(i) for i in range(30)]
    a = source({"a.txt": rows}, device="22480")
    b = source({"b.txt": rows}, device="22482")
    ka, kb = row_keys(a), row_keys(b)
    assert duplicate_counts(a, ka)["exact_duplicate_rows"] == 0   # each device is its own dedup group
    assert duplicate_counts(b, kb)["exact_duplicate_rows"] == 0
    diag = cross_device_equality(a, ka, b, kb)
    assert diag["shared_sensor_target_rows"] == 30 and "not duplicates" in diag["note"]


def test_within_file_adjacent_exact_duplicate_and_policy_counts():
    rows = [line(i) for i in range(10)]
    rows.insert(3, line(2))                          # the same second logged twice, identical content
    src = source({"d1.txt": rows})
    k, c, _, _ = analyse(src)
    assert c["exact_duplicates_within_file"] == 1 and c["exact_duplicates_within_file_adjacent"] == 1
    pol = {p["policy"]: p for p in policy_impact(c, minute_resolution=False)}
    assert pol["raw"]["rows_after"] == 11
    assert pol["A1_exact_duplicates_across_files"]["rows_after"] == 11   # within-file repeat kept
    assert pol["A_all_exact_duplicates"]["rows_after"] == 10
    assert pol["C_one_row_per_timestamp"]["rows_after"] == 10 and pol["C_one_row_per_timestamp"]["status"] == "simulated"
    minute = {p["policy"]: p["status"] for p in policy_impact(c, minute_resolution=True)}
    assert minute["A_all_exact_duplicates"] == "not_applicable_minute_resolution"


def test_repeated_chunk_key_across_files():
    def wrap(key, idx):
        return ['{', f' "{key}": {{', '  "csvData": "timestamp,P1,P2,P3,P4,P5,P6,temp,humid,event',
                *[line(i) for i in idx], '"', ' }', '}']
    src = source({"d1.txt": wrap("2026-08-01_22-30-00", range(0, 10)),
                  "d2.txt": wrap("2026-08-01_22-30-00", range(0, 10))})
    k = row_keys(src)
    rep = repeated_chunk_keys(src, k)
    assert rep == [{"chunk_key": "2026-08-01_22-30-00", "n_files": 2, "files": "d1.txt | d2.txt",
                    "rows_per_copy": "10,10", "relation": "identical"}]
    assert np.all(src.chunk_idx >= 0)
