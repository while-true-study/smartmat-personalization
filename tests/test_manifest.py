"""Duplicate-collection detection and manifest provenance structure."""
from __future__ import annotations

import hashlib
import re

import pytest

from src.data import paths
from src.data.manifest import (
    MANIFEST_COLUMNS, assign_duplicate_groups, compare_manifests, file_id_for, find_duplicate_groups,
    read_manifest, sha256_file,
)
from src.data.raw_parser import parse_text


def _rec(rel, sha):
    return {"source_relpath": rel, "sha256": sha, "flags": "", "byte_duplicate_group": ""}


def test_byte_identical_files_are_detected(tmp_path):
    a, b, c = tmp_path / "a.txt", tmp_path / "b.txt", tmp_path / "c.txt"
    a.write_bytes(b"07-19 19:54:06,0,0,1,0,0,0,28,52, LM\r\n")
    b.write_bytes(b"07-19 19:54:06,0,0,1,0,0,0,28,52, LM\r\n")
    c.write_bytes(b"07-19 19:54:09,0,0,1,0,0,0,28,52, LM\r\n")
    records = [_rec(p.name, sha256_file(p)) for p in (a, b, c)]
    groups = find_duplicate_groups(records)
    assert list(groups.values()) == [["a.txt", "b.txt"]]
    assign_duplicate_groups(records)
    assert records[0]["byte_duplicate_group"] == records[1]["byte_duplicate_group"] != ""
    assert "byte_duplicate" in records[0]["flags"] and records[2]["flags"] == ""


def test_same_rows_in_different_wrappers_have_same_content_fingerprint():
    plain = "07-19 19:54:06,0,0,1229,355,80,1371,28,52, LM\r\n07-19 19:54:08,0,0,1321,0,0,1735,28,52,AHON LM\r\n"
    wrapped = (
        '{\n  "2026-07-19_20-24-04": {\n'
        '    "csvData": "timestamp,P1,P2,P3,P4,P5,P6,temp,humid,event\n'
        "07-19 19:54:06,0,0,1229,355,80,1371,28,52, LM\n"
        "07-19 19:54:08,0,0,1321,0,0,1735,28,52,AHON LM\n"
        '"\n  }\n}\n'
    )
    _, rows_plain, *_ = parse_text(plain, year_hint=2026)
    _, rows_wrapped, *_ = parse_text(wrapped)
    fp = lambda rows: hashlib.sha256("\n".join(repr(r.fingerprint()) for r in rows).encode()).hexdigest()  # noqa: E731
    assert len(rows_plain) == len(rows_wrapped) == 2
    assert fp(rows_plain) == fp(rows_wrapped)


def test_row_overlap_between_files_is_measurable():
    day1 = "08-21 23:00:00,1,2,3,4,5,6,28,50, LM\n08-21 23:00:03,1,2,3,4,5,6,28,50, LM\n"
    day2 = "08-21 23:00:03,1,2,3,4,5,6,28,50, LM\n08-22 01:00:00,0,0,0,0,0,0,28,50, NM\n"
    _, r1, *_ = parse_text(day1, year_hint=2026)
    _, r2, *_ = parse_text(day2, year_hint=2026)
    shared = {r.fingerprint() for r in r1} & {r.fingerprint() for r in r2}
    assert len(shared) == 1


def test_compare_manifests_detects_changes():
    old = [_rec("a", "1"), _rec("b", "2"), _rec("c", "3")]
    new = [_rec("a", "1"), _rec("b", "X"), _rec("d", "4")]
    assert compare_manifests(old, new) == {"modified": ["b"], "removed": ["c"], "added": ["d"]}


def test_file_id_is_stable_and_path_based():
    assert file_id_for("user07/0403.txt") == file_id_for("user07/0403.txt")
    assert file_id_for("user07/0403.txt") != file_id_for("user07/0404.txt")


@pytest.mark.skipif(not paths.manifest_path().exists(), reason="manifest not built")
def test_manifest_structure():
    rows = read_manifest(paths.manifest_path())
    assert rows and list(rows[0].keys()) == MANIFEST_COLUMNS
    assert len({r["file_id"] for r in rows}) == len(rows)
    assert len({r["source_relpath"] for r in rows}) == len(rows)
    for r in rows:
        assert re.fullmatch(r"[0-9a-f]{64}", r["sha256"])
        assert r["subject_id"] and r["source_id"] and r["dataset_role"]
    # the duplicate-group column exists and is consistent with the checksums
    dup = find_duplicate_groups(rows)
    flagged = {r["source_relpath"] for r in rows if r["byte_duplicate_group"]}
    assert flagged == {p for group in dup.values() for p in group}
