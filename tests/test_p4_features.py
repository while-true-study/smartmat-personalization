"""P4 feature construction (D-039 formulas, synthetic data only): MOVEMENT, CONTACT, family combinations, no leakage."""
from __future__ import annotations

import numpy as np
import pytest
import torch

from src.evaluation.leakage import check_calendar, check_inputs
from src.evaluation.protocol import load_protocol
from src.features.pressure_features import (CONTACT_FEATURES, MOVEMENT_FEATURES, RAW_FEATURES, build_inputs, contact,
                                            family_features, movement, raw)
from src.training.trainer import input_array, to_tensor

D = 4095.0
DIMS = {"RAW": 6, "MOVEMENT": 10, "CONTACT": 11, "RAW+MOVEMENT": 16, "RAW+CONTACT": 17, "RAW+MOVEMENT+CONTACT": 27}


def movement_window() -> np.ndarray:
    return np.array([[[100, 0, 0, 0, 0, 0],       # dominant 0
                      [100, 300, 0, 0, 0, 0],     # dominant 1 -> switch
                      [0, 0, 0, 0, 0, 0],         # empty frame: no dominant -> switch
                      [50, 50, 0, 0, 0, 0],       # tie -> lowest index 0 -> switch
                      [50, 50, 0, 0, 0, 0],       # same -> no switch
                      [60, 60, 0, 0, 0, 0],       # tie again, dominant 0 -> no switch
                      [60, 61, 0, 0, 0, 0],       # dominant 1 -> switch
                      [4095, 4095, 4095, 4095, 4095, 4095]]])   # 4095 kept; dominant 0 -> switch


# ------------------------------------------------------------------------------------------------------ MOVEMENT

def test_movement_step_zero_is_zero_even_with_pressure():
    m = movement(movement_window())
    assert m.shape == (1, 8, 10)
    assert np.all(m[0, 0] == 0.0)


def test_movement_channel_deltas_and_mean_abs_delta():
    p = movement_window()
    m = movement(p)
    assert np.allclose(m[0, 1, :6], [0, 300 / D, 0, 0, 0, 0])
    assert np.allclose(m[0, 2, :6], [-100 / D, -300 / D, 0, 0, 0, 0])
    assert m[0, 1, 6] == pytest.approx(300 / D / 6)
    assert m[0, 2, 6] == pytest.approx(400 / D / 6)
    assert np.allclose(m[0, 1:, :6], np.diff(p[0].astype(float), axis=0) / D)


def test_movement_sum_and_active_deltas():
    m = movement(movement_window())
    assert m[0, 1, 7] == pytest.approx(300 / (6 * D))          # sum 100 -> 400
    assert m[0, 2, 7] == pytest.approx(-400 / (6 * D))         # sum 400 -> 0
    assert m[0, 1, 8] == pytest.approx(1 / 6)                  # active 1 -> 2
    assert m[0, 2, 8] == pytest.approx(-2 / 6)                 # active 2 -> 0
    assert m[0, 7, 8] == pytest.approx(4 / 6)                  # active 2 -> 6


def test_movement_dominant_switch_ties_and_empty_frames():
    m = movement(movement_window())
    assert m[0, :, 9].tolist() == [0, 1, 1, 1, 0, 0, 1, 1]


def test_movement_uses_only_its_own_window():
    p = np.random.default_rng(0).integers(0, 4096, (5, 8, 6))
    alone = movement(p[2:3])
    assert np.array_equal(movement(p)[2:3], alone)           # no dependence on neighbouring windows


# ------------------------------------------------------------------------------------------------------- CONTACT

def test_contact_sum_active_shares_entropy_max_and_spread():
    c = contact(np.array([[[4095, 0, 0, 0, 0, 4095]]]))[0, 0]
    assert c.shape == (11,)
    assert c[0] == pytest.approx(1 / 3)                          # sum / (6 * 4095)
    assert c[1] == pytest.approx(2 / 6)                          # active channels / 6
    assert np.allclose(c[2:8], [0.5, 0, 0, 0, 0, 0.5])           # shares
    assert c[8] == pytest.approx(np.log(2) / np.log(6))          # normalised entropy
    assert c[9] == pytest.approx(0.5)                            # max share
    assert c[10] == pytest.approx(np.sqrt(2 / 9))                # population std / 4095


def test_contact_zero_frame_is_all_zero():
    c = contact(np.zeros((1, 2, 6), int))
    assert np.all(c == 0.0) and np.all(np.isfinite(c))


def test_contact_share_sum_entropy_and_max_share_bounds():
    p = np.random.default_rng(1).integers(0, 4096, (400, 8, 6))
    p[:5] = 0                                                    # some empty windows
    p[5:10, :, 1:] = 0                                           # single-channel frames
    p[5:10, :, 0] = np.maximum(p[5:10, :, 0], 1)
    c = contact(p)
    nonzero = p.sum(axis=-1) > 0
    assert np.allclose(c[..., 2:8].sum(axis=-1)[nonzero], 1.0)
    assert np.all(c[..., 2:8].sum(axis=-1)[~nonzero] == 0.0)
    assert np.all((c[..., 8] >= 0) & (c[..., 8] <= 1 + 1e-12))
    assert np.all((c[..., 9][nonzero] >= 1 / 6 - 1e-12) & (c[..., 9][nonzero] <= 1))
    assert np.allclose(c[5:10, :, 8], 0.0) and np.allclose(c[5:10, :, 9], 1.0)
    assert np.allclose(contact(np.full((1, 1, 6), 7))[0, 0, 8], 1.0)            # uniform -> maximal entropy
    assert set(np.round(c[..., 1] * 6).astype(int).ravel()) <= set(range(7))
    assert np.allclose(c[..., 10], p.std(axis=-1) / D)


# --------------------------------------------------------------------------------------------------- combinations

@pytest.mark.parametrize("family", list(DIMS))
def test_family_dimensions_and_deterministic_column_order(family):
    p = np.random.default_rng(2).integers(0, 4096, (6, 8, 6))
    x, names = build_inputs(p, family)
    assert x.shape == (6, 8, DIMS[family]) and len(names) == DIMS[family] == len(set(names))
    parts = {"raw": RAW_FEATURES, "movement": MOVEMENT_FEATURES, "contact": CONTACT_FEATURES}
    assert names == tuple(f for part in load_protocol()["inputs"]["families"][family] for f in parts[part])
    blocks = {"raw": raw(p), "movement": movement(p), "contact": contact(p)}
    assert np.array_equal(x, np.concatenate([blocks[part] for part in load_protocol()["inputs"]["families"][family]],
                                            axis=-1))
    x2, names2 = build_inputs(p, family)
    assert np.array_equal(x, x2) and names == names2


def test_movement_and_contact_families_contain_no_raw_inputs():
    for fam in ("MOVEMENT", "CONTACT"):
        assert not set(family_features(fam)) & set(RAW_FEATURES)
    assert not set(family_features("MOVEMENT")) & set(CONTACT_FEATURES)
    assert not set(family_features("CONTACT")) & set(MOVEMENT_FEATURES)
    assert family_features("RAW+CONTACT")[:6] == RAW_FEATURES and len(family_features("RAW+CONTACT")) == 17
    assert len(family_features("RAW+MOVEMENT+CONTACT")) == 27


@pytest.mark.parametrize("family", list(DIMS))
def test_chunked_input_array_equals_whole_array_features(family):
    p = np.random.default_rng(3).integers(0, 4096, (50, 8, 6)).astype(np.int16)
    whole = build_inputs(p, family)[0].astype(np.float32)
    assert np.array_equal(input_array(p, family, chunk=7), whole)
    assert input_array(p, family).dtype == np.float32


def test_raw_input_tensor_is_bitwise_the_p3_formula():
    p = np.random.default_rng(4).integers(0, 4096, (300, 8, 6)).astype(np.int16)
    p[0] = 4095
    old = torch.as_tensor(raw(p), dtype=torch.float32).permute(0, 2, 1).contiguous()     # P3 to_tensor
    new = to_tensor(p, torch.device("cpu"))
    assert new.dtype == torch.float32 and torch.equal(old, new)
    assert torch.equal(to_tensor(p, torch.device("cpu"), "RAW"), old)


# -------------------------------------------------------------------------------------------------- no leakage

@pytest.mark.parametrize("family", list(DIMS))
def test_family_inputs_exclude_targets_ids_calendar_phase_and_events(family):
    names = list(family_features(family))
    assert check_inputs(names) is None and check_calendar(names) is None
    assert not set(names) & set(load_protocol()["inputs"]["forbidden_fields"])
    for bad in ("temperature", "humidity", "target_temp_valid", "subject_id", "device_id", "session_id",
                "timestamp", "night_id", "hour_of_day", "month", "sensor_phase", "channel_quality_phase",
                "event_raw", "heater_state", "firmware_movement_label"):
        assert check_inputs(names + [bad]) is not None or check_calendar(names + [bad]) is not None, bad
