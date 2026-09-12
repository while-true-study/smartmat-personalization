"""Leakage validation gate L1–L12 (synthetic splits; fail-closed behaviour; D-042)."""
from __future__ import annotations

import csv
import re

import pytest

from src.data import paths
from src.evaluation import splits as S
from src.evaluation.leakage import (LeakageGateError, RunContext, check_calendar, check_inputs, require_pass,
                                    run_gate)
from src.evaluation.protocol import load_protocol, protocol_sha256
from src.features.pressure_features import family_features
from tests.test_splits import build, synthetic

CANON = {"dataset_version": "canonical_v1", "content_sha256": {"primary": "c" * 64}, "files": {"primary": "f" * 64}}
MAN_CANON = {"dataset_version": "canonical_v1", "primary_content_sha256": "c" * 64, "primary_file_sha256": "f" * 64}


@pytest.fixture()
def env(tmp_path):
    sessions, pieces, tables = build(synthetic())
    files = {rel: {"sha256": S.write_split(tmp_path / rel, rows, cols), "rows": len(rows)}
             for rel, (rows, cols) in tables.items()}
    manifest = {"protocol_version": "v1.0", "files": files, "canonical": MAN_CANON,
                "protocol_sha256": protocol_sha256()}
    return tmp_path, manifest, sessions, pieces


def gate(env, ctx=None, canonical=CANON):
    root, manifest, sessions, pieces = env
    return run_gate(root, manifest, load_protocol(), sessions, pieces, ctx, canonical)


def loso_ctx(fold=1, **kw):
    base = dict(scheme="loso", fold=fold, input_features=list(family_features("RAW")),
                fit_records=[{"transform": "target_zscore", "partition": "train", "subjects": ["User02", "User07"]}],
                selection_subjects=["User02", "User07"])
    base.update(kw)
    return RunContext(**base)


def rewrite(root, rel, fn):
    rows = S.read_split(root / rel)
    cols = list(rows[0])
    rows = fn(rows)
    with open(root / rel, "w", encoding="utf-8", newline="") as fh:     # tests only: simulate a hand edit
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def failed(rep):
    return {c.check for c in rep.failures()}


def test_valid_protocol_passes_every_check(env):
    rep = gate(env, loso_ctx())
    assert rep.passed, rep.failures()
    assert {c.rule for c in rep.checks} >= {"L1", "L1/L12", "L2/L4", "L4", "L5", "L6", "L7", "L8", "L9", "L10",
                                            "L3/L11"}
    assert require_pass(rep) is rep


def test_corrupted_split_file_is_detected_and_blocks_training(env):
    root = env[0]
    rewrite(root, S.LOSO_OUTER, lambda rows: rows[:-1])
    rep = gate(env)
    assert "split_files_match_manifest" in failed(rep)
    with pytest.raises(LeakageGateError):
        require_pass(rep)


def test_held_out_subject_in_training_fails_even_with_matching_manifest(env):
    root, manifest, *_ = env

    def leak(rows):
        for r in rows:
            if r["fold"] == "1" and r["subject_id"] == "User01":
                r["partition"] = "train"
                break
        return rows
    rewrite(root, S.LOSO_OUTER, leak)
    manifest["files"][S.LOSO_OUTER]["sha256"] = S.file_sha256_lf(root / S.LOSO_OUTER)   # attacker updates hash
    rep = gate(env)
    assert "outer_loso_three_folds_disjoint" in failed(rep)
    assert "concurrent_devices_same_partition" in failed(rep)


def test_held_out_subject_in_inner_validation_fails(env):
    root, manifest, *_ = env

    def leak(rows):
        extra = dict(rows[0])
        extra.update(subject_id="User01", session_id="User01|unknown|S0001", partition="inner_val")
        return rows + [extra]
    rewrite(root, S.LOSO_INNER, leak)
    manifest["files"][S.LOSO_INNER]["sha256"] = S.file_sha256_lf(root / S.LOSO_INNER)
    assert "inner_validation_subject_level" in failed(gate(env))


def test_user02_devices_split_across_partitions_fails(env):
    root, manifest, *_ = env

    def leak(rows):
        for r in rows:
            if r["subject_id"] == "User02" and r["device_id"] == "22482" and r["budget_nights"] == "3" \
                    and r["night_ordinal"] == "2":
                r["partition"] = "test"
        return rows
    rewrite(root, S.PERSONALIZATION, leak)
    manifest["files"][S.PERSONALIZATION]["sha256"] = S.file_sha256_lf(root / S.PERSONALIZATION)
    rep = gate(env)
    assert {"personalization_chronological", "concurrent_devices_same_partition"} <= failed(rep)


def test_adaptation_after_test_or_missing_buffer_fails(env):
    root, manifest, *_ = env

    def leak(rows):
        for r in rows:
            if r["subject_id"] == "User07" and r["budget_nights"] == "1" and r["night_ordinal"] == "2":
                r["partition"] = "test"                                   # buffer night used as test
        return rows
    rewrite(root, S.PERSONALIZATION, leak)
    manifest["files"][S.PERSONALIZATION]["sha256"] = S.file_sha256_lf(root / S.PERSONALIZATION)
    assert "personalization_chronological" in failed(gate(env))


def test_excluded_or_auxiliary_subject_in_split_fails(env):
    root, manifest, *_ = env

    def leak(rows):
        extra = dict(rows[0])
        extra.update(subject_id="User06", session_id="User06|unknown|S0001", partition="train")
        return rows + [extra]
    rewrite(root, S.LOSO_OUTER, leak)
    manifest["files"][S.LOSO_OUTER]["sha256"] = S.file_sha256_lf(root / S.LOSO_OUTER)
    assert "primary_sources_only" in failed(gate(env))


def test_changed_protocol_file_fails(env):
    env[1]["protocol_sha256"] = "0" * 64
    assert "protocol_file_unchanged" in failed(gate(env))


def test_changed_canonical_data_fails(env):
    changed = dict(CANON, files={"primary": "0" * 64})
    assert "canonical_matches_split_manifest" in failed(gate(env, canonical=changed))
    assert "canonical_matches_split_manifest" in failed(gate(env, canonical=None))


@pytest.mark.parametrize("feature", ["temperature", "humidity", "target_temp_valid", "event_raw", "AHON",
                                     "firmware_movement_label", "heater_state", "subject_id", "device_id",
                                     "source_file", "sensor_phase", "channel_quality_phase", "hour_of_day", "month",
                                     "season", "timestamp", "night_id"])
def test_forbidden_input_fields_are_rejected(env, feature):
    rep = gate(env, loso_ctx(input_features=["raw_p1", feature]))
    assert "inputs_admissible" in failed(rep)
    assert check_inputs(["raw_p1", feature]) is not None


def test_calendar_and_identity_names_are_flagged():
    assert check_calendar(["raw_p1", "hour_of_day"]) and check_calendar(["device_id"])
    assert check_calendar(list(family_features("RAW+MOVEMENT+CONTACT"))) is None


def test_scaler_fitted_on_held_out_or_test_data_fails(env):
    bad = [{"transform": "target_zscore", "partition": "train", "subjects": ["User01", "User02"]}]
    assert "fits_training_partition_only" in failed(gate(env, loso_ctx(fit_records=bad)))
    bad_part = [{"transform": "target_zscore", "partition": "test", "subjects": ["User02"]}]
    assert "fits_training_partition_only" in failed(gate(env, loso_ctx(fit_records=bad_part)))
    no_prov = [{"transform": "target_zscore", "partition": "train"}]
    assert "fits_training_partition_only" in failed(gate(env, loso_ctx(fit_records=no_prov)))
    pers = RunContext(scheme="personalization", subject="User07", input_features=list(family_features("RAW")),
                      fit_records=[{"transform": "target_zscore", "partition": "train", "subjects": ["User07"]}],
                      selection_subjects=["User01"])
    assert "fits_training_partition_only" in failed(gate(env, pers))


def test_model_selection_on_held_out_subject_fails(env):
    assert "selection_excludes_held_out" in failed(gate(env, loso_ctx(selection_subjects=["User01", "User02"])))


def test_window_crossing_partition_fails(env):
    ctx = loso_ctx(window_groups=[(("train", "User02|22480|S0001"), ("train", "User02|22480|S0001")),
                                  (("train", "User02|22480|S0001"), ("test", "User01|unknown|S0001"))])
    assert "windows_inside_partitions" in failed(gate(env, ctx))


def test_gate_fails_closed_on_missing_files_or_errors(env):
    root = env[0]
    (root / S.PERSONALIZATION).unlink()
    rep = gate(env)
    assert not rep.passed and "split_files_readable" in failed(rep)
    with pytest.raises(LeakageGateError):
        require_pass(rep)
    empty = type(rep)("v1.0")
    assert not empty.passed                                               # no checks ran -> not passed
    with pytest.raises(LeakageGateError):
        require_pass(empty)


def test_p2_code_reads_canonical_only():
    files = ["splits.py", "p2_protocol.py", "leakage.py", "windowing.py", "protocol.py"]
    code = [paths.PROJECT_ROOT / "src" / "evaluation" / f for f in files]
    code += [paths.PROJECT_ROOT / "src" / "features" / "pressure_features.py"]
    code += [paths.PROJECT_ROOT / "scripts" / f for f in ("build_p2_splits.py", "validate_p2_protocol.py",
                                                          "audit_p2_window_feasibility.py")]
    for p in code:
        text = p.read_text(encoding="utf-8")
        raw_access = r"raw_parser|src\.data\.provenance|src\.data\.manifest|io_guard\.read_bytes|" \
                     r"import[^\n]*\bread_bytes\b|raw_root|raw_package_root"
        assert not re.search(raw_access, text), p
        assert "auxiliary.parquet" not in text, p
