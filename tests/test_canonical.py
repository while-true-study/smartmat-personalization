"""Canonical interim dataset v1 (P0 closure). Synthetic log text for the build logic; the checks against the
real build read only the local, git-ignored Parquet files and committed manifests (skipped if not built)."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from src.data import paths
from src.data.canonical import (
    build_stream, constant_frame_run_s, content_hash, extract_file, pressure_quality, redact_events, sessions,
    target_quality,
)
from src.data.duplicates import overlapping_file_pairs, row_keys, upload_copy_map, upload_copy_mask
from src.data.io_guard import write_parquet
from src.data.provenance import SourceData
from src.data.raw_parser import parse_text

CFG = paths.load_config("canonical_v1.yaml")
T0 = datetime(2026, 8, 1, 22, 0, 0)


def lines(start: datetime, n: int, step: int = 3, p=(10, 20, 30, 40, 50, 60), t=28, h=50, ev="LM"):
    out = []
    for i in range(n):
        ts = start + timedelta(seconds=step * i)
        vals = [x + i % 7 for x in p]
        out.append(f"{ts:%m-%d %H:%M:%S},{','.join(map(str, vals))},{t},{h}, {ev}")
    return out


def chunk(name: str, text_lines: list[str], source_id="user02_mat_22482", device="22482"):
    rows = parse_text("\n".join(text_lines), year_hint=2026)[1]
    return extract_file(f"rf_{name}", f"user02/mat_{device}/{name}.txt", source_id, rows, device)


def test_exact_upload_copies_are_removed_with_provenance():
    a = lines(T0, 30)
    b = a[18:] + lines(T0 + timedelta(seconds=90), 20)                  # 12 repeated rows, then new rows
    res = build_stream([chunk("f1", a), chunk("f2", b)], "User02", "22482", "primary_candidate", False, CFG)
    st = res.stats
    assert st["rows_raw"] == 62 and st["rows_copies_removed"] == 12 and st["rows_canonical"] == 50 and st["reconciles"]
    prov = res.provenance.to_pydict()
    assert sum(not x for x in prov["is_canonical"]) == 12 and sum(prov["is_canonical"]) == 12
    tab = res.table.to_pydict()
    assert sum(1 for c in tab["duplicate_count"] if c == 2) == 12
    kept_ids = set(tab["canonical_row_id"])
    assert set(prov["canonical_row_id"]) <= kept_ids                  # every copy points to a kept row


def test_copy_map_matches_the_audit_copy_mask():
    a = lines(T0, 30)
    b = a[18:] + lines(T0 + timedelta(seconds=90), 20)
    rows_a, rows_b = parse_text("\n".join(a), 2026)[1], parse_text("\n".join(b), 2026)[1]
    src = SourceData.from_rows("s", "User02", "22482", [("f1", rows_a), ("f2", rows_b)])
    keys = row_keys(src)
    pairs = overlapping_file_pairs(src, keys)
    orig = upload_copy_map(src, keys, pairs)
    assert np.array_equal(orig >= 0, upload_copy_mask(src, keys, pairs))
    assert np.array_equal(keys.full[orig >= 0], keys.full[orig[orig >= 0]])


def test_same_second_different_values_are_kept():
    a = lines(T0, 10)
    a.insert(5, a[4].replace(",28,50,", ",29,50,"))                      # same second, different temperature
    res = build_stream([chunk("f1", a)], "User02", "22482", "primary_candidate", False, CFG)
    tab = res.table.to_pydict()
    assert res.stats["rows_copies_removed"] == 0 and len(tab["timestamp"]) == 11
    groups = [g for g in tab["same_timestamp_group_id"] if g is not None]
    assert len(groups) == 2 and len(set(groups)) == 1
    assert sorted(o for o, g in zip(tab["within_timestamp_order"], tab["same_timestamp_group_id"]) if g) == [0, 1]


def test_invalid_targets_are_flagged_not_deleted():
    t = np.array([28, 0, -254, 256, 0, 27], np.int16)
    h = np.array([50, 0, 0, 152, 40, 0], np.int16)
    t_ok, h_ok, flag = target_quality(t, h, CFG["targets"]["temp_band"], CFG["targets"]["humid_band"])
    assert flag.tolist() == ["ok", "zero_sentinel", "extreme_glitch", "extreme_glitch", "zero_value", "zero_value"]
    assert t_ok.tolist() == [True, False, False, False, False, True]
    assert h_ok.tolist() == [True, False, False, False, True, False]
    a = lines(T0, 5)
    a[2] = a[2].replace(",28,50,", ",0,0,")
    res = build_stream([chunk("f1", a)], "User02", "22482", "primary_candidate", False, CFG)
    tab = res.table.to_pydict()
    assert len(tab["timestamp"]) == 5 and tab["temperature"][2] == 0 and tab["target_quality_flag"][2] == "zero_sentinel"


def test_4095_is_kept_and_only_counted():
    v = np.array([[4095, 0, 0, 0, 0, 0, 28, 50], [4095, 4095, 1, 1, 1, 1, 28, 50], [0] * 6 + [28, 50]], np.int16)
    q = pressure_quality(v, np.zeros(3, np.int8), 0, 4095)
    assert q["valid"].tolist() == [True, True, True] and q["upper"].tolist() == [1, 2, 0]
    assert q["flag"].tolist() == ["upper_bound", "upper_bound", "ok"] and q["all_zero"].tolist() == [False, False, True]
    a = lines(T0, 3, p=(4095, 20, 30, 40, 50, 60))                      # P1 = 4095, 4096, 4097 in the raw text
    tab = build_stream([chunk("f1", a)], "User02", "22482", "primary_candidate", False, CFG).table.to_pydict()
    assert tab["P1"] == [4095, 4096, 4097]                               # raw values kept, never clipped
    assert tab["pressure_valid"] == [True, False, False]
    assert tab["pressure_quality_flag"] == ["upper_bound", "invalid_encoding", "invalid_encoding"]


def test_constant_frame_run_is_context_only():
    ts = np.array([0, 3, 6, 9, 12, 100, 103], np.int64)
    v = np.array([[5, 0, 0, 0, 0, 0, 28, 50]] * 3 + [[0] * 6 + [28, 50]] + [[5, 0, 0, 0, 0, 0, 28, 50]] * 3, np.int16)
    assert constant_frame_run_s(ts, v).tolist() == [6, 6, 6, 0, 0, 3, 3]   # gap > 60 s ends a run; zeros are 0


def test_missing_channel_is_never_filled():
    v = np.array([[1, 2, 3, 4, 5, -32768, 28, 50]], np.int16)
    q = pressure_quality(v, np.zeros(1, np.int8), 0, 4095)
    assert not q["valid"][0] and q["flag"][0] == "missing_channel"


def test_session_rule_and_22482_chunk_bridge():
    ts = np.array([0, 3, 6, 6 + 1805, 6 + 1805 + 3, 6 + 1805 + 3 + 1805], np.int64)
    fidx = np.array([0, 0, 0, 1, 1, 1])                                  # file boundary before the first long gap only
    s = sessions(ts, fidx, "22482", CFG["session"])
    assert s["index"].tolist() == [0, 0, 0, 0, 0, 1] and s["bridged"].tolist() == [False, False, False, True, False, False]
    assert sessions(ts, fidx, "22480", CFG["session"])["index"].tolist() == [0, 0, 0, 1, 1, 2]   # other devices: no bridge
    s2 = sessions(ts, np.zeros(6, int), "22482", CFG["session"])                                 # no file boundary: no bridge
    assert s2["index"].tolist() == [0, 0, 0, 1, 1, 2]
    again = sessions(ts, fidx, "22482", CFG["session"])
    assert all(np.array_equal(again[k], s[k]) for k in s)                                        # deterministic


def test_legacy_minute_rows_keep_their_resolution_and_raw_text():
    rows = parse_text("2025-10-06 21:33,0,0,5,0,0,0,26,40, x\n2025-10-06 21:33,0,0,6,0,0,0,26,40, x", 2025)[1]
    c = extract_file("rf_leg", "user03_legacy/x.csv", "user03_legacy", rows, "unknown")
    tab = build_stream([c], "User03", "unknown", "auxiliary", True, CFG).table.to_pydict()
    assert tab["timestamp_resolution"] == ["minute", "minute"] and tab["timestamp_raw"] == ["2025-10-06 21:33"] * 2
    assert tab["timezone_status"] == ["local_unspecified"] * 2 and tab["pressure_schema"] == ["legacy_csv_fsr"] * 2
    assert tab["sensor_phase"] == ["not_applicable"] * 2 and tab["dataset_role"] == ["auxiliary"] * 2


def test_phase_labels_follow_the_frozen_boundaries():
    before = lines(datetime(2026, 1, 25, 8, 7, 20), 3)
    after = lines(datetime(2026, 1, 25, 17, 31, 21), 3)
    c = chunk("u1", before + after, source_id="user01_phase_c", device="unknown")
    tab = build_stream([c], "User01", "unknown", "primary_candidate", False, CFG).table.to_pydict()
    assert tab["sensor_phase"] == ["s1"] * 3 + ["s2"] * 3 and set(tab["channel_quality_phase"]) == {"normal"}
    d = chunk("d2", lines(datetime(2026, 8, 19, 8, 56, 4), 3) + lines(datetime(2026, 8, 20, 21, 37, 33), 2))
    tab = build_stream([d], "User02", "22482", "primary_candidate", False, CFG).table.to_pydict()
    assert tab["channel_quality_phase"] == ["normal"] * 3 + ["p1_response_shift"] * 2
    assert tab["channel_quality_flag"] == ["none"] * 3 + ["p1"] * 2


def test_event_redaction():
    out, flag = redact_events(["SCHATIDS 1234567890", "LM", "AHON 1234"], 8)
    assert out == ["SCHATIDS <redacted>", "LM", "AHON 1234"] and flag.tolist() == [True, False, False]


def test_build_is_reproducible(tmp_path):
    def build():
        a = lines(T0, 30)
        b = a[18:] + lines(T0 + timedelta(seconds=90), 20)
        return build_stream([chunk("f1", a), chunk("f2", b)], "User02", "22482", "primary_candidate", False, CFG)
    r1, r2 = build(), build()
    assert content_hash([r1.table]) == content_hash([r2.table])
    assert content_hash([r1.provenance]) == content_hash([r2.provenance])
    p1 = write_parquet(tmp_path / "a.parquet", [r1.table], r1.table.schema)
    p2 = write_parquet(tmp_path / "b.parquet", [r2.table], r2.table.schema)
    assert p1.read_bytes() == p2.read_bytes()


# ---- checks against the real build (local; skipped when canonical_v1 has not been built) ----------------------

OUT = paths.repo_path(CFG["output_dir"])
MAN = paths.repo_path(CFG["manifest_dir"])
built = (OUT / "primary.parquet").exists() and (MAN / "canonical_v1_summary.csv").exists()
need_build = pytest.mark.skipif(not built, reason="canonical_v1 not built locally")


def _values(name: str, dataset: str = "primary") -> set:
    col = pq.read_table(OUT / f"{dataset}.parquet", columns=[name]).column(0)
    return set(pc.unique(pc.cast(col, pa.string())).to_pylist())


@need_build
def test_real_build_excludes_invalid_quarantined_and_auxiliary_from_primary():
    prim, aux = _values("source_id"), _values("source_id", "auxiliary")
    assert _values("dataset_role") == {"primary_candidate"} and _values("dataset_role", "auxiliary") == {"auxiliary"}
    assert prim == {"user01_phase_a", "user01_phase_b", "user01_phase_c", "user02_mat_22480", "user02_mat_22482", "user07"}
    assert aux == {"user02_legacy_csv", "user03_legacy"}
    for bad in ("user06_auxiliary", "user02_mat_22480_prefix_mismatch"):
        assert bad not in prim | aux


@need_build
def test_real_build_keeps_user02_devices_as_separate_streams():
    t = pq.read_table(OUT / "primary.parquet", columns=["subject_id", "device_id", "session_id"],
                      filters=[("subject_id", "=", "User02")])
    dev = pc.cast(t["device_id"], pa.string())
    assert set(pc.unique(dev).to_pylist()) == {"22480", "22482"}
    sid = pc.cast(t["session_id"], pa.string())
    for d in ("22480", "22482"):                                          # sessions never mix the two mats
        assert pc.all(pc.starts_with(pc.filter(sid, pc.equal(dev, d)), f"User02|{d}|")).as_py()


@need_build
def test_real_build_phase_boundaries_and_reconciliation():
    rows = list(csv.DictReader(io.StringIO((MAN / "canonical_v1_manifest.csv").read_text(encoding="utf-8"))))
    by = {(r["source_id"], r["sensor_phase"], r["channel_quality_phase"]): r for r in rows}
    assert by[("user01_phase_c", "s1", "normal")]["last_timestamp"] == "2026-01-25 08:07:26"
    assert by[("user01_phase_c", "s2", "normal")]["first_timestamp"] == "2026-01-25 17:31:21"
    assert by[("user02_mat_22482", "not_applicable", "p1_transition")]["first_timestamp"] == "2026-08-19 19:58:23"
    assert by[("user02_mat_22482", "not_applicable", "p1_response_shift")]["first_timestamp"] == "2026-08-20 21:37:33"
    for r in rows:
        if r["status"] == "included":
            assert int(r["rows_raw"]) - int(r["rows_copies_removed"]) == int(r["rows_canonical"])
    summ = list(csv.DictReader(io.StringIO((MAN / "canonical_v1_summary.csv").read_text(encoding="utf-8"))))
    raw = {r["subject_id"] + "|" + r["device_id"]: r for r in summ if r["dataset_file"] in ("primary", "auxiliary")}
    assert sum(int(r["rows_canonical"]) for r in raw.values() if r["dataset_file"] == "primary") == \
        pq.ParquetFile(OUT / "primary.parquet").metadata.num_rows


@need_build
def test_real_build_preserves_upper_bound_values():
    t = pq.read_table(OUT / "primary.parquet", columns=["P1", "P2", "P3", "P4", "P5", "P6", "pressure_upper_bound_channels"],
                      filters=[("subject_id", "=", "User01")])
    cells = sum(int(pc.sum(pc.equal(t[c], 4095)).as_py() or 0) for c in ("P1", "P2", "P3", "P4", "P5", "P6"))
    assert cells == 275_601 == pc.sum(t["pressure_upper_bound_channels"]).as_py()   # A9: every 4095 cell kept
