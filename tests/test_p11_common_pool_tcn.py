"""P11 common-pool RAW-TCN on synthetic data: masks, pools, the unchanged epoch rule, pairs and the interpretation map
(D-066; docs/P11_COMMON_POOL_TCN_PLAN.md)."""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from src.evaluation import p3_loso as P3
from src.evaluation import p11_common_pool_tcn as P11


def fake_fold(held="User01"):
    subj = np.array(["User01"] * 4 + ["User02"] * 5 + ["User07"] * 3)
    part = np.where(subj == held, "test", "train")
    inner = {"A": np.where(subj == "User02", "inner_train", np.where(subj == "User07", "inner_val", "")),
             "B": np.where(subj == "User07", "inner_train", np.where(subj == "User02", "inner_val", ""))}
    labelled = np.ones(subj.size, bool)
    labelled[[1, 5]] = False
    return SimpleNamespace(prov={"subject_id": subj}, partition=part, inner=inner, labelled=labelled, held_out=held,
                           train_subjects=["User02", "User07"])


def fake_subjects():
    return {"User01": SimpleNamespace(common=np.array([True, False, True, False])),
            "User02": SimpleNamespace(common=np.array([False, False, True, True, True])),
            "User07": SimpleNamespace(common=np.array([True, False, True]))}


def test_common_mask_scatters_each_subject_in_order():
    fd = fake_fold()
    cm = P11.common_mask(fd, fake_subjects())
    assert cm.tolist() == [True, False, True, False, False, False, True, True, True, True, False, True]


def test_common_mask_rejects_misaligned_missing_or_unlabelled():
    fd = fake_fold()
    bad = fake_subjects()
    bad["User02"] = SimpleNamespace(common=np.array([True, True]))
    with pytest.raises(P11.P11Error):
        P11.common_mask(fd, bad)
    missing = fake_subjects()
    del missing["User07"]
    with pytest.raises(P11.P11Error):
        P11.common_mask(fd, missing)
    unlabelled = fake_subjects()
    unlabelled["User01"] = SimpleNamespace(common=np.array([True, True, False, False]))   # window 1 is not labelled
    with pytest.raises(P11.P11Error):
        P11.common_mask(fd, unlabelled)


def test_pools_keep_the_held_out_subject_out_of_every_fit_and_selection_pool():
    fd = fake_fold()
    pl = P11.pools(fd, P11.common_mask(fd, fake_subjects()))
    held = fd.prov["subject_id"] == "User01"
    for name, mask in pl.items():
        if name.startswith("test"):
            assert mask.any() and not np.any(mask & ~held)
        else:
            assert not np.any(mask & held), name
    assert pl["train"].sum() == 5 and pl["train_full"].sum() == 7 and pl["test"].sum() == 2
    assert set(fd.prov["subject_id"][pl["inner_train_A"]]) == {"User02"}
    assert set(fd.prov["subject_id"][pl["inner_val_A"]]) == {"User07"}
    assert np.array_equal(pl["inner_train_A"], pl["inner_val_B"])          # A and B are the swapped pair
    assert not np.any(pl["train"] & ~pl["train_full"])                     # the common pool is a subset of the full pool


def test_pools_fail_closed_when_the_held_out_subject_is_in_an_inner_split():
    fd = fake_fold()
    fd.inner["A"] = np.where(fd.prov["subject_id"] == "User01", "inner_train", fd.inner["A"])
    with pytest.raises(P11.P11Error):
        P11.pools(fd, P11.common_mask(fd, fake_subjects()))


def test_epoch_rule_is_the_frozen_v1_0_function_not_a_new_rule():
    src = inspect.getsource(P11.freeze_epochs)
    assert "P3.final_epochs(" in src
    assert P3.final_epochs(4, 5) == 5 and P3.final_epochs(1, 8) == 5 and P3.final_epochs(2, 3) == 3
    assert P3.final_epochs(2, 2) == 2 and P3.final_epochs(1, 2) == 2


def test_no_search_no_grid_and_frozen_configuration_only():
    src = inspect.getsource(P11)
    assert "config_grid" not in src and "select_config" not in src      # nothing is searched or reselected
    assert "P3.frozen_selection()" in inspect.getsource(P11.frozen_config)
    assert "HistGradientBoosting" not in src and "fit_predict" not in src   # HGB is read, never refitted


def test_config_matches_frozen_rules_and_outputs_stay_in_their_own_root():
    doc = P11.load_config()
    assert doc["model"]["grid_search"] == "none" and doc["final"]["seeds"] == [0, 1, 2]
    assert doc["epochs"]["final_rule"].startswith("round_half_up(mean(")
    root = P11.output_root().as_posix()
    assert root.endswith("outputs/p11_common_pool_tcn")
    for tree in P11.PROTECTED_TREES:
        assert not root.endswith(tree) and tree not in P11.final_dir(1, 0).as_posix()


def test_final_run_refuses_before_the_epoch_count_is_frozen(tmp_path):
    P11.set_output_root(tmp_path)
    try:
        with pytest.raises(P11.P11Error, match="not frozen"):
            P11.run_final(None, 1, 0, {})
        assert not (tmp_path / "test_access.jsonl").exists()
    finally:
        P11.set_output_root(None)


def test_comparison_pairs_are_the_preregistered_ones():
    pairs = P11.comparison_pairs([0, 1, 2])
    assert ("training_mean_common", "raw_tcn_common_seed0", "level_baseline_vs_common_pool_tcn") in pairs
    assert ("training_median_common", "raw_tcn_common_seed2", "level_baseline_vs_common_pool_tcn") in pairs
    assert ("raw_tcn_common_seed1", "hgb_h40", "same_pool_same_history_two_pipelines") in pairs
    assert ("raw_tcn_full_seed0", "raw_tcn_common_seed0", "training_pool_restriction") in pairs
    assert [p for p in pairs if p[2] == "longer_history"] == [("hgb_h40", "hgb_h300", "longer_history"),
                                                              ("hgb_h40", "hgb_h900", "longer_history")]
    assert len(pairs) == 3 * 4 + 2


def test_interpretation_cases_follow_the_plan():
    assert [P11.case_of(n) for n in (0, 1, 2, 3)] == ["A", "B", "C", "C"]
    subjects = ["User01", "User02", "User07"]
    boot = []
    for t in ("temperature", "humidity"):
        for s, (lo_mean, lo_med) in zip(subjects, [(0.1, 0.2), (0.1, -0.1), (-0.3, -0.2)]):
            for first, lo in (("training_mean_common", lo_mean), ("training_median_common", lo_med)):
                boot.append({"subject_id": s, "target": t, "first": first, "second": "raw_tcn_common_seed0",
                             "point_estimate": lo + 0.05, "ci_lower": lo, "ci_upper": lo + 0.1})
    rows = P11.interpretation(boot, subjects)
    per = {(r["target"], r["subject_id"]): r for r in rows}
    assert per[("temperature", "User01")]["exceeds_level_baselines"] is True
    assert per[("temperature", "User02")]["exceeds_level_baselines"] is False      # must beat the median as well
    assert per[("temperature", "ALL")]["case"] == "B" and per[("humidity", "ALL")]["exceeds_level_baselines"] == 1
