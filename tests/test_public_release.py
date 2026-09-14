"""public_release_v1 builder, loader, privacy validator and equivalence gate (synthetic data only)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.data import public_release as R
from src.evaluation import p5_personalization as P5
from src.evaluation import splits as S
from src.evaluation.protocol import PROTOCOL_VERSION, night_id, protocol_sha256
from tests.test_p3_loso import synthetic_rows
from tests.test_splits import build


def synthetic_workspace(tmp_path: Path):
    arr, rows = synthetic_rows()
    rows.temp_ok[::17] = False                                           # some unlabelled windows
    _, _, tables = build(arr)
    split_dir = tmp_path / "splits_private"
    for rel, (r, cols) in tables.items():
        S.write_split(split_dir / rel, r, cols)
    pers = S.read_split(split_dir / S.PERSONALIZATION)
    plan = {"protocol_sha256": "x", "subjects": {}}
    for s in R.ALLOWED_SUBJECTS:
        n0 = P5.budget_nights(pers, s, 0)
        budgets = {}
        for b in (0, 1, 3, 7, 14):
            nb = P5.budget_nights(pers, s, b)
            budgets[b] = {"adaptation_nights": nb["adaptation"], "buffer_nights": nb["buffer"],
                          "later_test_nights": len(nb["test"]), "later_test_first": nb["test"][0],
                          "later_test_last": nb["test"][-1]}
        plan["subjects"][s] = {"primary_test": {"nights": n0["primary"], "windows_sha256":
                                                P5.subject_windows(rows, s, 0, pers).primary_digest()},
                               "base_checkpoints": {0: {"weights_sha256": "w", "p3_run_id": "r-20260913",
                                                        "p3_run_dir": "outputs/runs/p3/final/fold1_seed0"}},
                               "budgets": budgets}
    ev_ts = rows.ts[rows.subject == "User02"]
    events = [("User02", "22482", int(ev_ts[10]), "AHON"), ("User02", "22480", int(ev_ts[50]), "AHOF"),
              ("User02", "22482", int(ev_ts[90]), "BHSDOWN")]
    return rows, split_dir, plan, events


def build_into(tmp_path: Path, name: str = "release"):
    rows, split_dir, plan, events = synthetic_workspace(tmp_path)
    out = tmp_path / name
    out.mkdir(exist_ok=True)
    (out / "README.md").write_text("# test release\n\nRelative time only.\n", encoding="utf-8")
    excluded = [{"source_id": "user06_auxiliary", "subject_id": "User06", "dataset_role": "excluded_invalid",
                 "exclusion_reason": "provider_confirmed_setting_issue", "exclusion_confirmed_by": "data_provider",
                 "exclusion_decision": "D-017"}]
    identity = {"protocol_version": PROTOCOL_VERSION, "protocol_sha256": protocol_sha256(),
                "split_sha256": {rel: S.file_sha256_lf(split_dir / rel) for rel in S.SPLIT_FILES}, "base_tag": "t"}
    manifest, checks = R.build_release(out, rows, split_dir, plan=plan, events=events, reference={"x": 1},
                                       excluded=excluded, budgets=[0, 1, 3, 7, 14], identity=identity,
                                       raw_names=["user01/phase_a/raw_0101.txt", "raw_0101.txt"])
    return out, manifest, checks, rows, split_dir


# ----------------------------------------------------------------------------------------------- time mapping

def test_relative_time_keeps_noon_nights_gaps_and_clock_time():
    ts = np.array([1_780_000_000, 1_780_000_003, 1_780_050_000, 1_780_100_000, 1_780_190_000], np.int64)
    a = R.anchor_of(ts.min())
    assert a % R.DAY_S == 0 and (ts.min() - R.NOON_S - a) // R.DAY_S == 0          # first night is D0001
    keys = R.night_key_ts(ts, a)
    assert keys[0] == "D0001"
    same_private = night_id(ts)[:, None] == night_id(ts)[None, :]
    assert np.array_equal(same_private, keys[:, None] == keys[None, :])            # identical night grouping
    rel = ts - a
    assert np.array_equal(np.diff(rel), np.diff(ts)) and np.array_equal(rel % R.DAY_S, ts % R.DAY_S)
    for r in rel:
        assert R.parse_rel(R.rel_str(r)) == r
    assert R.night_key_date(str(night_id(ts[:1])[0]), a) == "D0001"
    with pytest.raises(R.ReleaseError):
        R.rel_str(-1)


# -------------------------------------------------------------------------------------------------- builder

def test_build_passes_every_gate_and_is_byte_deterministic(tmp_path):
    out1, man1, checks, rows, split_dir = build_into(tmp_path / "a")
    assert all(c["passed"] for c in checks), [c for c in checks if not c["passed"]]
    assert set(man1["artifacts_sha256"]) == set(R.ARTIFACTS)
    out2, man2, _, _, _ = build_into(tmp_path / "b")
    for a in (*R.ARTIFACTS, "manifest.json"):
        assert (out1 / a).read_bytes() == (out2 / a).read_bytes(), a
    first = (out1 / "manifest.json").read_bytes()
    (out1 / "p5_plan_public.yaml").write_text("stale: true\n", encoding="utf-8")
    build_into(tmp_path / "a")                                  # rebuild over a stale file and a stale manifest
    assert (out1 / "manifest.json").read_bytes() == first
    t = pq.read_table(out1 / "windows.parquet")
    assert t.column_names == R.WINDOW_COLUMNS
    assert not any(str(f.type).startswith(("timestamp", "date")) for f in t.schema)
    plan = (out1 / "p5_plan_public.yaml").read_text()
    assert "2026-" not in plan and "p3_run_id" not in plan and "D0001" in plan


def test_public_loader_rebuilds_the_private_model_ready_arrays(tmp_path):
    out, man, _, rows, split_dir = build_into(tmp_path)
    rel = R.PublicRelease(out)
    from src.training.loso_data import fold_data
    for f in (1, 2, 3):
        p, q = fold_data(rows, f, split_dir), rel.fold_data(f)
        assert np.array_equal(p.pressure, q.pressure) and np.array_equal(p.targets, q.targets, equal_nan=True)
        assert np.array_equal(p.labelled, q.labelled) and np.array_equal(p.partition, q.partition)
    pers = S.read_split(split_dir / S.PERSONALIZATION)
    for s in R.ALLOWED_SUBJECTS:
        p, q = P5.subject_windows(rows, s, 7, pers), rel.subject_windows(s, 7)
        assert np.array_equal(p.pressure, q.pressure) and np.array_equal(p.partition, q.partition)
        assert q.primary_digest() == p.primary_digest()                       # via the manifest correspondence
        assert q.public_digest() != p.primary_digest()
    assert set(rel.w.device[rel.w.subject == "User02"]) == {"22480", "22482"}


def test_control_events_keep_heater_codes_only(tmp_path):
    out, *_ = build_into(tmp_path)
    ev = S.read_split(out / "control_events.csv")
    assert [e["code"] for e in ev] == ["AHOF", "AHON"] and all(e["time"].startswith("D") for e in ev)


# ---------------------------------------------------------------------------------------- privacy validator

def failing(out: Path) -> set[str]:
    return {c["check"] for c in R.validate_release(out) if not c["passed"]}


@pytest.mark.parametrize("artifact,inject,check", [
    ("control_events.csv", "User02,22482,5,2026-01-05 22:00:00,AHON\n", "text_scan:control_events.csv"),
    ("schema.json", '{"x": "C:\\\\Users\\\\someone\\\\data"}', "text_scan:schema.json"),
    ("reference_digests.json", '{"id": "chatIDs=0123456789"}', "text_scan:reference_digests.json"),
    ("p5_plan_public.yaml", "note: raw_0101.txt from user01/phase_a\n", "text_scan:p5_plan_public.yaml"),
    ("splits/v1.0_loso/outer_folds.csv", "v1.0,x,1,User06,User06,unknown,s,s1,normal,test,D0001 00:00:00,"
                                         "D0001 00:00:01,1\n", "text_scan:splits/v1.0_loso/outer_folds.csv"),
    ("schema.json", '{"diagnosis": "x"}', "restricted_fields:schema.json"),
])
def test_validator_fails_on_injected_private_content(tmp_path, artifact, inject, check):
    out, *_ = build_into(tmp_path)
    p = out / artifact
    p.write_text(p.read_text(encoding="utf-8") + inject, encoding="utf-8")
    bad = failing(out)
    assert check in bad and "manifest_hashes_match" in bad


def test_validator_fails_on_forbidden_columns_and_unknown_subjects(tmp_path):
    out, *_ = build_into(tmp_path)
    t = pq.read_table(out / "windows.parquet")
    pq.write_table(t.append_column("event_raw", pa.array(["x"] * t.num_rows)), out / "windows.parquet")
    assert "window_columns_frozen_no_restricted_or_date_fields" in failing(out)
    out2, *_ = build_into(tmp_path / "b")
    t = pq.read_table(out2 / "windows.parquet")
    subj = np.where(t["subject_id"].to_numpy(zero_copy_only=False) == "User07", "User06",
                    t["subject_id"].to_numpy(zero_copy_only=False))
    t = t.set_column(t.column_names.index("subject_id"), "subject_id", pa.array(subj))
    pq.write_table(t, out2 / "windows.parquet")
    assert "window_values_allowed_ids_ranges_relative_time" in failing(out2)
    with pytest.raises(R.ReleaseError):
        R.PublicRelease(out2)                                                   # manifest hash mismatch


def test_validator_passes_the_release_readme_and_manifest(tmp_path):
    out, man, *_ = build_into(tmp_path)
    assert failing(out) == set()
    assert json.loads((out / "manifest.json").read_text())["equivalence"]["passed"] is True
