"""P1 domain-shift EDA (synthetic arrays only; no canonical or raw data needed)."""
from __future__ import annotations

import re

import numpy as np
import pytest

from src.data import paths
from src.data.raw_parser import MOVEMENT_TOKENS as PARSER_MOVEMENT_TOKENS
from src.evaluation.canonical_input import RAW_ACCESS_TOKENS, CanonicalInputError, assert_canonical_path, canonical_dir
from src.evaluation.domain_shift import (
    MAIN_SLICES, MOVEMENT_TOKENS, assign_slices, binned_trend, distance, event_trajectory, event_vocabulary,
    hour_of_day, hours_since_session_start, parse_event, pooled_masks, pressure_descriptors, spearman, summarize,
    unit_stat,
)

P1_CODE = [paths.PROJECT_ROOT / "src" / "evaluation" / f for f in ("domain_shift.py", "p1_eda.py", "p1_figures.py",
                                                                     "canonical_input.py")]
P1_CODE.append(paths.PROJECT_ROOT / "scripts" / "run_p1_domain_eda.py")


def test_domain_slices_follow_canonical_phases():
    subj = np.array(["User01", "User01", "User02", "User02", "User02", "User02", "User07", "User06", "User03"], object)
    dev = np.array(["unknown", "unknown", "22480", "22482", "22482", "22482", "unknown", "unknown", "unknown"], object)
    sp = np.array(["s1", "s2", "not_applicable", "not_applicable", "not_applicable", "not_applicable",
                   "not_applicable", "not_applicable", "not_applicable"], object)
    cq = np.array(["normal", "normal", "normal", "normal", "p1_response_shift", "p1_transition", "normal", "normal", "normal"], object)
    out = assign_slices(subj, dev, sp, cq).tolist()
    assert out == ["User01/s1", "User01/s2", "User02/22480", "User02/22482/normal", "User02/22482/p1_shift",
                   "User02/22482/p1_transition", "User07", "", ""]              # User06 / auxiliary never sliced
    assert set(out[:5] + out[6:7]) == set(MAIN_SLICES)


def test_pooled_masks_keep_devices_of_one_subject_together():
    subj = np.array(["User02", "User02", "User01"], object)
    dev = np.array(["22480", "22482", "unknown"], object)
    m = pooled_masks(subj, dev)
    assert m["User02 (pooled)"].tolist() == [True, True, False] and m["User02/22482 (all phases)"].tolist() == [False, True, False]


def test_pressure_descriptors_and_upper_bound():
    p = np.array([[0] * 6, [4095, 0, 0, 0, 0, 0], [10, 20, 30, 0, 0, 0], [5, 5, 5, 5, 5, 5]])
    d = pressure_descriptors(p, np.array([True, True, True, False]))
    assert d.total.tolist() == [0, 4095, 60, 0] and d.active.tolist() == [0, 1, 3, 0]
    assert d.all_zero.tolist() == [True, False, False, False] and d.loaded.tolist() == [False, True, True, False]
    assert d.upper.tolist() == [0, 1, 0, 0] and d.dominant.tolist() == [-1, 0, 2, -1]


def test_distribution_summary_and_invalid_target_exclusion():
    temp = np.array([25, 26, 0, 27, 28], float)
    valid = np.array([True, True, False, True, True])
    s = summarize(temp[valid])
    assert s["n"] == 4 and s["min"] == 25 and s["median"] == 26.5 and s["zero_ratio"] == 0.0


def test_distance_is_consistent_and_symmetric():
    rng = np.random.default_rng(1)
    a = rng.integers(0, 50, 2000)
    b = a + 10
    ua, ub = np.repeat(np.arange(20), 100), np.repeat(np.arange(20), 100)
    ab, ba = distance(a, b, ua, ub), distance(b, a, ub, ua)
    assert ab["w1"] == pytest.approx(10.0) and ab["w1"] == ba["w1"] and ab["ks"] == ba["ks"]
    assert ab["cliffs_delta_units"] == -ba["cliffs_delta_units"] and ab["cliffs_delta_units"] > 0.9
    same = distance(a, a, ua, ua)
    assert same["w1"] == 0 and same["ks"] == 0 and same["cliffs_delta_units"] == 0


def test_unit_stat_uses_one_value_per_unit():
    u, v = unit_stat(np.array([1, 2, 3, 10, 20]), np.array([7, 7, 7, 9, 9]))
    assert u.tolist() == [7, 9] and v.tolist() == [2.0, 15.0]


def test_time_of_night_grouping_without_timezone_conversion():
    ts = np.array([0, 3600 * 23 + 59, 86400 + 3600 * 2])                 # naive local seconds
    assert hour_of_day(ts).tolist() == [0, 23, 2]
    rel = hours_since_session_start(np.array([100, 100 + 7200, 50, 50 + 1800]), np.array([1, 1, 2, 2]))
    assert rel.tolist() == [0.0, 2.0, 0.0, 0.5]


def test_control_event_parsing():
    assert parse_event("AHON LM") == ("left", ("AHON",))
    assert parse_event("EVENT:FORCED_OFF 자리비움") == ("absent", ("EVENT:FORCED_OFF",))
    assert parse_event("BHSDOWN") == ("", ("BHSDOWN",)) and parse_event("") == ("", ())
    voc = event_vocabulary(["AHON LM", "LM", "BHSDOWN NM"], [2, 10, 3])
    assert voc["control"] == {"AHON": 2, "BHSDOWN": 3} and voc["movement"]["left"] == 12
    assert MOVEMENT_TOKENS == PARSER_MOVEMENT_TOKENS                   # same vocabulary as the P0 parser


def test_event_trajectory_is_event_conditioned_only():
    ts = np.arange(0, 7200, 60)
    y = np.where(ts < 3600, 20.0, 21.0)
    ok = np.ones(ts.size, bool)
    stream = np.zeros(ts.size, int)
    ev = np.array([np.searchsorted(ts, 3000)])
    tr = event_trajectory(ts, y, ok, stream, ev, (-600, 600, 1800), tol_s=30)
    assert tr[-600][0] == 0 and tr[600][0] == 1 and tr[1800][0] == 1
    ok2 = ok.copy()
    ok2[(ts > 3000) & (ts < 5500)] = False                                 # no valid row near +10/+30 min: stays NaN
    tr2 = event_trajectory(ts, y, ok2, stream, ev, (600, 1800), tol_s=30)
    assert np.isnan(tr2[600][0]) and np.isnan(tr2[1800][0])


def test_spearman_and_binned_trend():
    x = np.arange(100, dtype=float)
    assert spearman(x, 2 * x + 1) == 1.0 and spearman(x, -x) == -1.0 and spearman(x, np.ones(100)) is None
    bins = binned_trend(x, x, 4)
    assert len(bins) == 4 and bins[0]["y_median"] < bins[-1]["y_median"]


def test_canonical_only_input_guard():
    with pytest.raises(CanonicalInputError):
        assert_canonical_path(paths.PROJECT_ROOT / paths.path_config()["raw_root"] / "x.txt")
    with pytest.raises(CanonicalInputError):
        assert_canonical_path(paths.PROJECT_ROOT / "outputs" / "x.parquet")
    assert assert_canonical_path(canonical_dir() / "primary.parquet").name == "primary.parquet"


def test_p1_code_has_no_raw_access():
    offenders = []
    for p in P1_CODE:
        text = p.read_text(encoding="utf-8")
        body = text if p.name != "canonical_input.py" else text.split("RAW_ACCESS_TOKENS = (", 1)[0]
        for tok in RAW_ACCESS_TOKENS:
            if re.search(rf"\b{tok}\b", body):
                offenders.append(f"{p.name}: {tok}")
        if "raw_parser" in text or "src.data.provenance" in text or "src.data.manifest" in text:
            offenders.append(f"{p.name}: imports a raw-reading module")
    assert not offenders, offenders
