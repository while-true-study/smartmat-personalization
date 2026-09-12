"""Protocol v1.0 split construction (synthetic sessions; D-030, D-031, D-037, D-042)."""
from __future__ import annotations

import re

import numpy as np
import pytest

from src.data import paths
from src.evaluation import splits as S
from src.evaluation.protocol import load_protocol, night_id

COHORT = ["User01", "User02", "User07"]
FOLDS = {1: "User01", 2: "User02", 3: "User07"}
BUDGETS, BUFFER, PRIMARY_FROM = [0, 1, 3, 7, 14], 1, 16
DAY0 = int(np.datetime64("2026-01-01T00:00:00", "s").astype(np.int64))


def synthetic(n_nights: int = 18, cross_noon_night: int | None = None):
    """Three subjects; User02 records on two concurrent mats; User01 has s1/s2; 22482 has quality phases."""
    cols = {k: [] for k in ("ts", "subject", "device", "session", "sp", "cq")}
    streams = [("User01", "unknown"), ("User02", "22480"), ("User02", "22482"), ("User07", "unknown")]
    for subj, dev in streams:
        for n in range(n_nights):
            start = DAY0 + n * 86400 + 22 * 3600 + (300 if dev == "22482" else 0)
            end = start + 600
            if cross_noon_night is not None and n == cross_noon_night and subj == "User07":
                start, end = DAY0 + (n + 1) * 86400 + 11 * 3600, DAY0 + (n + 1) * 86400 + 13 * 3600
            t = np.arange(start, end, 3)
            sp = ("s1" if n < 9 else "s2") if subj == "User01" else "not_applicable"
            cq = ("normal" if n < 6 else "p1_transition" if n == 6 else "p1_response_shift") if dev == "22482" \
                else "normal"
            cols["ts"].append(t)
            for k, v in (("subject", subj), ("device", dev), ("session", f"{subj}|{dev}|S{n + 1:04d}"),
                         ("sp", sp), ("cq", cq)):
                cols[k].append(np.full(t.size, v, dtype=object))
    arr = {k: np.concatenate(v) for k, v in cols.items()}
    arr["night"] = night_id(arr["ts"])
    return arr


def build(arr):
    sessions = S.session_records(arr["ts"], arr["subject"], arr["device"], arr["session"], arr["sp"], arr["cq"])
    pieces = S.piece_records(arr["ts"], arr["subject"], arr["device"], arr["session"], arr["sp"], arr["cq"],
                             arr["night"])
    return sessions, pieces, {
        S.LOSO_OUTER: (S.loso_outer(sessions, FOLDS, COHORT, "v1.0"), S.OUTER_COLUMNS),
        S.LOSO_INNER: (S.loso_inner(sessions, FOLDS, COHORT, "v1.0"), S.INNER_COLUMNS),
        S.PERSONALIZATION: (S.personalization(pieces, BUDGETS, BUFFER, PRIMARY_FROM, "v1.0"), S.PERS_COLUMNS),
    }


def test_protocol_split_parameters_are_frozen():
    cfg = load_protocol()
    assert {int(k): v for k, v in cfg["loso"]["outer_folds"].items()} == FOLDS
    pz = cfg["personalization"]
    assert (pz["budgets_nights"], pz["buffer_nights"], pz["primary_test_from_ordinal"]) == (BUDGETS, BUFFER, 16)
    assert cfg["data"]["subjects"] == COHORT and cfg["grouping"]["night_offset_hours"] == 12


def test_exactly_three_outer_folds_with_whole_subjects_held_out():
    _, _, t = build(synthetic())
    outer = t[S.LOSO_OUTER][0]
    assert sorted({r["fold"] for r in outer}) == [1, 2, 3]
    for f, held in FOLDS.items():
        rows = [r for r in outer if r["fold"] == f]
        assert {r["subject_id"] for r in rows if r["partition"] == "test"} == {held}
        assert held not in {r["subject_id"] for r in rows if r["partition"] == "train"}
    held02 = [r for r in outer if r["fold"] == 2 and r["subject_id"] == "User02"]
    assert {r["device_id"] for r in held02} == {"22480", "22482"} and {r["partition"] for r in held02} == {"test"}


def test_nested_validation_is_subject_level_and_excludes_the_held_out_subject():
    _, _, t = build(synthetic())
    inner = t[S.LOSO_INNER][0]
    for f, held in FOLDS.items():
        rows = [r for r in inner if r["fold"] == f]
        assert held not in {r["subject_id"] for r in rows}
        for name in ("A", "B"):
            tr = {r["subject_id"] for r in rows if r["inner_split"] == name and r["partition"] == "inner_train"}
            va = {r["subject_id"] for r in rows if r["inner_split"] == name and r["partition"] == "inner_val"}
            assert len(tr) == len(va) == 1 and not tr & va
    f1 = [r for r in inner if r["fold"] == 1 and r["inner_split"] == "A"]
    assert {r["subject_id"] for r in f1 if r["partition"] == "inner_train"} == {"User02"}   # prompt example


def test_chronological_budgets_buffer_and_common_test_span():
    _, _, t = build(synthetic())
    pers = t[S.PERSONALIZATION][0]
    for subj in COHORT:
        for b in BUDGETS:
            rows = [r for r in pers if r["subject_id"] == subj and r["budget_nights"] == b]
            parts = {r["night_ordinal"]: r["partition"] for r in rows}
            assert sorted(parts) == list(range(1, 19))                     # nights ordered chronologically
            if b:
                assert [k for k, p in parts.items() if p == "adaptation"] == list(range(1, b + 1))
                assert [k for k, p in parts.items() if p == "buffer"] == [b + 1]
                adapt_end = max(r["end_timestamp"] for r in rows if r["partition"] == "adaptation")
                test_start = min(r["start_timestamp"] for r in rows if r["partition"] == "test")
                assert adapt_end < test_start                               # no future row in adaptation
            assert {r["night_ordinal"] for r in rows if r["primary_test"]} == set(range(16, 19))


def test_user02_devices_share_the_partition_of_each_night():
    _, _, t = build(synthetic())
    pers = [r for r in t[S.PERSONALIZATION][0] if r["subject_id"] == "User02"]
    by_night = {}
    for r in pers:
        by_night.setdefault((r["budget_nights"], r["night_id"]), set()).add((r["device_id"], r["partition"]))
    for devs in by_night.values():
        assert {d for d, _ in devs} == {"22480", "22482"} and len({p for _, p in devs}) == 1


def test_session_crossing_noon_is_cut_into_night_pieces():
    arr = synthetic(cross_noon_night=3)
    sessions, pieces, _ = build(arr)
    sid = "User07|unknown|S0004"
    assert len([p for p in pieces if p["session_id"] == sid]) == 2
    assert len([s for s in sessions if s["session_id"] == sid]) == 1


def test_split_files_are_deterministic_with_stable_sha(tmp_path):
    arr = synthetic()
    h1 = {rel: S.write_split(tmp_path / "a" / rel, rows, cols) for rel, (rows, cols) in build(arr)[2].items()}
    perm = np.random.default_rng(1).permutation(arr["ts"].size)
    shuffled = {k: v[perm] for k, v in arr.items()}                         # input order must not matter
    h2 = {rel: S.write_split(tmp_path / "b" / rel, rows, cols) for rel, (rows, cols) in build(shuffled)[2].items()}
    assert h1 == h2
    for rel in h1:
        assert (tmp_path / "a" / rel).read_bytes() == (tmp_path / "b" / rel).read_bytes()
        assert S.file_sha256_lf(tmp_path / "a" / rel) == h1[rel]
    crlf = tmp_path / "crlf.csv"
    crlf.write_bytes((tmp_path / "a" / S.LOSO_OUTER).read_bytes().replace(b"\n", b"\r\n"))
    assert S.file_sha256_lf(crlf) == h1[S.LOSO_OUTER]                       # checkout line endings do not matter


def test_multi_phase_session_is_refused():
    arr = synthetic()
    arr["sp"] = arr["sp"].copy()
    arr["sp"][0] = "s2"                                                      # one row of S0001 in another phase
    with pytest.raises(S.SplitError):
        build(arr)


def test_committed_split_files_match_their_manifest():
    import json
    root = paths.PROJECT_ROOT / load_protocol()["artifacts"]["split_dir"]
    man = json.loads((root / "v1.0_manifest.json").read_text(encoding="utf-8"))
    assert man["protocol_version"] == "v1.0" and man["canonical"]["dataset_version"] == "canonical_v1"
    for rel in S.SPLIT_FILES:
        assert S.file_sha256_lf(root / rel) == man["files"][rel]["sha256"]
        rows = S.read_split(root / rel)
        assert len(rows) == man["files"][rel]["rows"]
        assert {r["subject_id"] for r in rows} <= set(COHORT)                # no User03/User06/auxiliary


def test_experiment_protocol_is_frozen_without_open_items():
    text = (paths.PROJECT_ROOT / "docs" / "EXPERIMENT_PROTOCOL.md").read_text(encoding="utf-8")
    assert "Status: FROZEN — protocol version v1.0" in text
    for word in ("TBD", "PLACEHOLDER", "to be decided", "나중에 결정"):
        assert word not in text
    headings = re.findall(r"^## (\d+)\. ", text, flags=re.M)
    assert [int(h) for h in headings] == list(range(15))
