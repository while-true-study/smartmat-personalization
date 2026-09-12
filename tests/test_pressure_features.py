"""Protocol v1.0 inputs: fixed scaling, geometry-free feature families, training-only target scaler (synthetic)."""
from __future__ import annotations

import numpy as np
import pytest

from src.features.pressure_features import (ADMISSIBLE_FEATURES, FAMILIES, TargetScaler, build_inputs, contact,
                                            family_features, movement, raw)


def test_raw_scaling_is_fixed_and_keeps_4095():
    p = np.array([[[4095, 0, 0, 0, 0, 0], [2048, 1, 0, 0, 0, 4095]]])
    x = raw(p)
    assert x[0, 0, 0] == 1.0 and x[0, 1, 5] == 1.0 and x.max() == 1.0      # no clipping, no removal
    with pytest.raises(ValueError):
        raw(np.array([[[4096, 0, 0, 0, 0, 0]]]))


def test_contact_features_are_geometry_free_descriptors():
    p = np.array([[[10, 10, 10, 10, 10, 10], [0, 0, 0, 0, 0, 0], [30, 0, 0, 0, 0, 0]]])
    c = contact(p)
    assert c.shape == (1, 3, 11)
    assert c[0, 0, 1] == 1.0 and c[0, 0, 8] == pytest.approx(1.0)       # 6 active, maximal entropy
    assert np.all(c[0, 1] == 0)                                          # empty mat: all zero
    assert c[0, 2, 9] == 1.0 and c[0, 2, 8] == 0.0                       # one channel: max share 1, entropy 0


def test_movement_features_use_only_the_window_and_pad_step_zero():
    p = np.zeros((1, 3, 6), int)
    p[0, 1, 0] = 4095
    p[0, 2, 1] = 4095
    m = movement(p)
    assert np.all(m[0, 0] == 0)                                          # no predecessor inside the window
    assert m[0, 1, 0] == 1.0 and m[0, 2, 0] == -1.0 and m[0, 2, 1] == 1.0
    assert m[0, 1, 9] == 1.0 and m[0, 2, 9] == 1.0                       # dominant channel switched


def test_family_definitions_are_frozen():
    assert set(FAMILIES) == {"RAW", "MOVEMENT", "CONTACT", "RAW+MOVEMENT", "RAW+CONTACT", "RAW+MOVEMENT+CONTACT"}
    assert [len(family_features(f)) for f in ("RAW", "MOVEMENT", "CONTACT")] == [6, 10, 11]
    x, names = build_inputs(np.ones((2, 8, 6), int), "RAW+MOVEMENT+CONTACT")
    assert x.shape == (2, 8, 27) and len(names) == 27 and set(names) <= ADMISSIBLE_FEATURES


def test_target_scaler_records_training_provenance_and_inverts():
    y = np.array([[25.0, 40.0], [27.0, 50.0], [26.0, 45.0]])
    sc = TargetScaler.fit(y, scheme="loso", fold="1", partition="train", subjects=["User07", "User02"])
    assert sc.fit_provenance["subjects"] == ["User02", "User07"] and sc.fit_provenance["partition"] == "train"
    assert np.allclose(sc.inverse(sc.transform(y)), y)                   # metrics return to °C / %RH
    with pytest.raises(ValueError):
        TargetScaler.fit(np.array([[25.0, 40.0], [25.0, 41.0]]), scheme="loso", fold="1", partition="train",
                         subjects=["User02"])
