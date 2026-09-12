"""Coverage and confounding audit (P0 A11). Synthetic timestamps and manifest rows only — no raw data."""
from __future__ import annotations

from datetime import datetime

import numpy as np

from src.data.coverage import (
    chronological_capacity, check, coverage_summary, dominant_step, eligibility, minutes, month_range,
    monthly_coverage, overlap, quarter_of, season_of,
)
from src.data.duplicates import subject_device_groups
from src.data.sensor_phase import assign_phase
from src.data.subject_mapping import analysis_source_ids, excluded_sources, resolve_source, sensor_phase_spec

EPOCH = datetime(1970, 1, 1)


def sec(s: str) -> int:
    return int((datetime.fromisoformat(s) - EPOCH).total_seconds())


def night(start: str, hours: float, step: int = 3) -> np.ndarray:
    t0 = sec(start)
    return np.arange(t0, t0 + int(hours * 3600), step)


def test_subject_month_coverage():
    ts = np.concatenate([night("2026-01-30 22:00:00", 4), night("2026-02-02 22:00:00", 1)])
    valid = np.ones(ts.size, bool)
    valid[:100] = False
    rows = {r["month"]: r for r in monthly_coverage(ts, valid, month_range("2026-01", "2026-03"))}
    assert rows["2026-01"]["recording_days"] == 2 and rows["2026-01"]["active_recording_hours"] == 4.0   # 30th + 31st
    assert rows["2026-02"]["recording_days"] == 1 and rows["2026-02"]["active_recording_hours"] == 1.0
    assert rows["2026-03"]["recording_days"] == 0 and rows["2026-03"]["valid_target_rows"] == 0
    assert sum(r["valid_target_rows"] for r in rows.values()) == ts.size - 100
    assert month_range("2025-11", "2026-02") == ["2025-11", "2025-12", "2026-01", "2026-02"]


def test_temporal_overlap_on_recorded_days_and_minutes():
    a = np.concatenate([night("2026-07-18 22:00:00", 2), night("2026-07-19 01:00:00", 4)])
    b = night("2026-07-19 03:00:00", 3)                                  # shares 03:00-05:00 on 07-19
    ov = overlap(a, b)
    assert ov["overlap_days"] == 1 and ov["overlap_weeks"] == 1 and ov["overlap_months"] == 1
    assert ov["overlap_recording_hours"] == 2.0 and ov["days_only_a"] == 1 and ov["gap_between_ranges_h"] == 0


def test_no_overlap_subjects():
    a = night("2026-04-01 22:00:00", 8)
    b = night("2026-04-03 19:00:00", 8)
    ov = overlap(a, b)
    assert ov["overlap_days"] == 0 and ov["overlap_recording_hours"] == 0
    assert ov["overlap_weeks"] == 1 and ov["overlap_months"] == 1        # same ISO week and month, no shared day
    assert abs(ov["gap_between_ranges_h"] - (sec("2026-04-03 19:00:00") - sec("2026-04-02 05:59:57")) / 3600) < 0.01


def test_multi_device_same_subject():
    d1 = np.concatenate([night("2026-08-01 22:00:00", 6), night("2026-08-03 22:00:00", 6)])
    d2 = np.concatenate([night("2026-08-01 23:00:00", 6), night("2026-08-05 22:00:00", 6)])
    union = minutes(np.concatenate([d1, d2]))
    assert union.size < minutes(d1).size + minutes(d2).size                      # concurrent hours counted once
    ov = overlap(d1, d2)
    assert ov["overlap_recording_hours"] == 5.0 and ov["days_only_a"] >= 1 and ov["days_only_b"] >= 1
    assert resolve_source("user02/mat_22480/sm22480_0801.txt").subject_id == resolve_source(
        "user02/mat_22482/sm22482_0801.txt").subject_id == "User02"          # two devices, one subject


def test_sensor_phase_subdivision_from_config():
    bounds, names = sensor_phase_spec("User01")
    assert names == ("s1", "s2") and bounds == [(sec("2026-01-25 08:07:26"), sec("2026-01-25 17:31:21"))]
    assert sensor_phase_spec("User07") == ([], ("s1",))
    ts = np.array([sec("2026-01-25 08:07:26"), sec("2026-01-25 17:31:21"), sec("2026-01-26 01:00:00")])
    assert assign_phase(ts, bounds, names).tolist() == ["s1", "s2", "s2"]


def manifest_row(source_id, subject, device, role, family="md_hms_json"):
    return {"is_sensor_data": "True", "source_id": source_id, "subject_id": subject, "device_id": device,
            "format_family": family, "dataset_role": role}


def test_excluded_and_auxiliary_sources_are_separated():
    rows = [manifest_row("user06_auxiliary", "User06", "unknown", "excluded_invalid"),
            manifest_row("user02_mat_22480_prefix_mismatch", "User02", "unresolved", "quarantined"),
            manifest_row("user02_legacy_csv", "User02", "unknown", "auxiliary", "legacy_csv_ymd_hm"),
            manifest_row("user02_mat_22480", "User02", "22480", "primary_candidate"),
            manifest_row("user03_legacy", "User03", "unknown", "auxiliary", "legacy_csv_ymd_hm")]
    groups = subject_device_groups(rows, eligible_only=True)
    assert ("User06", "unknown") not in groups and ("User02", "unresolved") not in groups
    assert groups[("User02", "unknown")]["roles"] == {"auxiliary"}                 # legacy kept apart from the mats
    assert groups[("User02", "22480")]["roles"] == {"primary_candidate"}
    excl = {e["source_id"] for e in excluded_sources()}
    assert {"user06_auxiliary", "user02_mat_22480_prefix_mismatch"} <= excl
    assert "user03_legacy" in analysis_source_ids() and "user06_auxiliary" not in analysis_source_ids()


def test_cohort_eligibility_calculation():
    ok = {"volume": "pass", "targets": "pass"}
    assert eligibility(ok) == "eligible"
    assert eligibility(ok, ["device unknown"]) == "eligible_with_caveat"
    assert eligibility({**ok, "targets": check(0.80, 0.95)}) == "not_eligible"
    assert eligibility({**ok, "targets": check(None, 0.95)}) == "not_eligible"          # unknown never passes
    cap = chronological_capacity(np.arange(20, 36), min_nights=7)
    assert cap["nights"] == 16 and cap["can_split"]
    assert not chronological_capacity(np.arange(10), min_nights=7)["can_split"]


def test_summary_calendar_and_sampling_helpers():
    ts = night("2026-01-10 22:00:00", 2.5)
    valid = np.ones(ts.size, bool)
    s = coverage_summary(ts, valid, valid, valid, raw_rows=ts.size + 5)
    assert s["recording_days"] == 2 and s["usable_recording_days"] == 1          # 120 min on day 1, 30 min on day 2
    assert s["dominant_sampling_interval"] == "3s" and s["raw_rows"] == ts.size + 5
    minute_rows = np.repeat(np.arange(sec("2025-10-06 22:00:00"), sec("2025-10-06 23:00:00"), 60), 25)
    assert dominant_step(minute_rows) == "minute_resolution"
    d = sec("2026-01-10 00:00:00") // 86400
    assert season_of(d) == "2025-winter" and quarter_of(d) == "2026-Q1"
    assert season_of(sec("2026-07-01 00:00:00") // 86400) == "2026-summer"
