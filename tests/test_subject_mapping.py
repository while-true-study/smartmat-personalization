"""Subject/device mapping invariants (docs/DATA_POLICY.md, configs/subject_mapping.yaml)."""
from __future__ import annotations

import re

import pytest

from src.data import paths
from src.data.manifest import read_manifest
from src.data.subject_mapping import (
    UNKNOWN_DEVICE_VALUES, analysis_source_ids, device_subject_map, excluded_sources, mapping_config, resolve_file,
    resolve_source, sources, subject_for_device, subject_ids,
)

USER02_DEVICES = {"22480", "22482"}


# --- User02 devices ------------------------------------------------------------------------

@pytest.mark.parametrize("device", ["22480", "22482", 22480, 22482])
def test_user02_devices_map_to_user02(device):
    assert subject_for_device(device) == "User02"


def test_user02_devices_share_one_subject():
    assert {subject_for_device(d) for d in USER02_DEVICES} == {"User02"}


def test_device_ids_are_never_subject_ids():
    for dev in device_subject_map():
        assert dev not in subject_ids()
        assert not any(dev in s for s in subject_ids())
    for s in subject_ids():
        assert re.fullmatch(r"User\d{2}", s), s


@pytest.mark.parametrize("relpath", [
    "user02/mat_22480/sm22480_0719.txt",
    "user02/mat_22482/sm22482_0910.txt",
    "user02\\mat_22482\\sm22482_0719.txt",                  # Windows separators
    "user02/mat_22480/_prefix_mismatch/sm22482_0824.txt",   # quarantined, still User02
])
def test_user02_mat_files_resolve_to_user02(relpath):
    prov = resolve_file(relpath)
    assert prov.subject_id == "User02"
    if prov.device_id == "unresolved":
        assert set(prov.source.device_id_candidates) <= USER02_DEVICES
        assert "device_prefix_mismatch" in prov.flags
    else:
        assert prov.device_id in USER02_DEVICES


def test_prefix_mismatch_is_flagged_not_reassigned():
    prov = resolve_file("user02/mat_22480/_prefix_mismatch/sm22482_0825.txt")
    assert prov.device_id == "unresolved"
    assert prov.device_id_filename == "22482"
    assert prov.source.dataset_role == "quarantined"


def test_unknown_device_is_rejected():
    with pytest.raises(KeyError):
        subject_for_device("99999")


def test_unmapped_path_is_rejected():
    with pytest.raises(KeyError):
        resolve_source("user99/some_file.txt")


# --- configuration integrity ---------------------------------------------------------------

def test_sources_reference_known_subjects_and_devices():
    dev_map = device_subject_map()
    for s in sources():
        assert s.subject_id in subject_ids(), s
        if s.device_id not in UNKNOWN_DEVICE_VALUES:
            assert dev_map[s.device_id] == s.subject_id, s
        for cand in s.device_id_candidates:
            assert dev_map[cand] == s.subject_id, s


def test_source_subdirs_are_unique():
    subdirs = [s.raw_subdir for s in sources()]
    assert len(subdirs) == len(set(subdirs))


def test_dataset_roles_match_policy():
    role = {s.source_id: s.dataset_role for s in sources()}
    assert role["user01_phase_a"] == role["user01_phase_b"] == role["user01_phase_c"] == "primary_candidate"
    assert role["user02_mat_22480"] == role["user02_mat_22482"] == "primary_candidate"
    assert role["user07"] == "primary_candidate"
    assert role["user02_legacy_csv"] == "auxiliary"
    assert role["user03_legacy"] == "auxiliary"
    assert role["user06_auxiliary"] == "excluded_invalid"          # D-017 (provider-confirmed invalid source)
    assert role["user01_metadata"] == "restricted_metadata"


def test_user06_source_is_excluded_but_subject_is_kept_and_not_merged():
    s06 = resolve_source("user06_auxiliary/1003_log.txt")
    s03 = resolve_source("user03_legacy/user3_20251006_log.csv")
    assert "User06" in subject_ids() and "User03" in subject_ids()
    assert s06.subject_id == "User06" and s03.subject_id == "User03"     # never merged
    assert s06.quality_status == "invalid" and not s06.analysis_eligible
    assert s06.exclusion_reason == "provider_confirmed_setting_issue" and s06.exclusion_decision == "D-017"
    assert s03.analysis_eligible and s03.dataset_role == "auxiliary"


def test_analysis_sources_and_exclusion_list():
    eligible = analysis_source_ids()
    assert "user06_auxiliary" not in eligible
    assert "user02_mat_22480_prefix_mismatch" not in eligible and "user01_metadata" not in eligible
    assert {"user01_phase_a", "user02_mat_22480", "user02_mat_22482", "user07", "user03_legacy"} <= eligible
    excluded = {e["source_id"]: e for e in excluded_sources()}
    assert excluded["user06_auxiliary"]["exclusion_reason"] == "provider_confirmed_setting_issue"
    assert excluded["user06_auxiliary"]["exclusion_confirmed_by"] == "data_provider"


def test_user02_legacy_is_same_subject_as_new_user02():
    assert resolve_source("user02/legacy_csv/x.csv").subject_id == "User02"


# --- against the real raw tree / manifest (skipped if unavailable) --------------------------

@pytest.mark.skipif(not paths.raw_root().is_dir(), reason="raw data not present")
def test_every_raw_file_resolves():
    root = paths.raw_root()
    for p in root.rglob("*"):
        if p.is_file():
            resolve_file(p.relative_to(root).as_posix())


@pytest.mark.skipif(not paths.manifest_path().exists(), reason="manifest not built")
def test_manifest_user02_device_rows():
    rows = read_manifest(paths.manifest_path())
    assert {r["subject_id"] for r in rows} <= subject_ids()
    dev_rows = [r for r in rows if r["device_id"] in USER02_DEVICES or r["device_id_filename"] in USER02_DEVICES]
    assert dev_rows, "expected User02 mat files in the manifest"
    assert {r["subject_id"] for r in dev_rows} == {"User02"}
    assert not any(r["subject_id"] in USER02_DEVICES for r in rows)
    assert {r["device_id"] for r in rows if r["source_relpath"].startswith("user02/mat_")} <= USER02_DEVICES | {"unresolved"}


def test_config_version_present():
    assert mapping_config()["version"] >= 1
