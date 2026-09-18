"""P13 manuscript revision: figure night-selection rule and the P11/P12 export (cross-checks, numbering)."""
from __future__ import annotations

import numpy as np
import pytest

from src.paper import p13_figures as F
from src.paper import p13_revision as E


# ------------------------------------------------------------------------------------------------ Figure S5 rule

def test_longest_run_needs_20_s_steps_within_one_session():
    starts = np.array([0, 20, 40, 100, 120, 140, 160], np.int64)
    sess = np.array(["a"] * 7)
    assert F.longest_run_seconds(starts, sess) == 60 + F.WINDOW_S           # 100..160 plus one window
    assert F.longest_run_seconds(starts, np.array(["a", "a", "a", "a", "b", "b", "b"])) == 40 + F.WINDOW_S
    assert F.longest_run_seconds(np.zeros(0, np.int64), np.zeros(0, str)) == 0


def test_select_night_takes_the_earliest_night_meeting_the_rule_on_every_mat():
    h = 3600
    runs = {(16, "a"): 5 * h, (16, "b"): 1 * h, (17, "a"): 4 * h, (17, "b"): 4 * h, (18, "a"): 9 * h, (18, "b"): 9 * h}
    assert F.select_night(runs, ("a", "b")) == (17, "all_mats_meet_rule")
    assert F.select_night(runs, ("a",)) == (16, "all_mats_meet_rule")


def test_select_night_fallbacks_are_deterministic():
    h = 3600
    runs = {(16, "a"): 1 * h, (16, "b"): 5 * h, (20, "a"): 4 * h, (20, "b"): 1 * h}
    assert F.select_night(runs, ("a", "b")) == (20, "only_a_meets_rule")
    runs = {(16, "a"): 2 * h, (17, "a"): 3 * h, (18, "a"): 3 * h}
    assert F.select_night(runs, ("a",)) == (17, "no_night_meets_rule_longest_run")      # ties: the earlier night


def test_figure_data_carry_no_calendar_date():
    for name in ("p13_figure_target_distribution",):       # the Figure S5 data were withdrawn in P14 (D-070)
        text = (E.TABLES / f"{name}.csv").read_text(encoding="utf-8")
        assert not E.DATE.search(text), name
        assert "night_id" not in text.splitlines()[0]


# ------------------------------------------------------------------------------------------------ export

def _tables(delta: float = 0.0) -> dict[str, list[dict]]:
    cmp_, hm, sm, p12 = [], [], [], []
    for s in E.SUBJECTS:
        for tg in E.TARGETS:
            base = {"subject": s, "target": tg, "n_windows": "10", "n_nights": "2"}
            for m, val in (("mean_common", 1.0), ("median_common", 1.5), ("tcn_full_40s_seed_mean", 2.0),
                           ("tcn_common_40s_seed_mean", 2.5), ("hgb_40s", 3.0), ("hgb_300s", 3.5), ("hgb_900s", 4.0)):
                cmp_.append({**base, "model": m, "MAE": str(val)})
            h = {"subject_id": s, "target": tg, "n_windows": "10"}
            hm += [{**h, "predictor": "training_mean_common", "history_s": "", "seed": "", "mae": str(1.0 + delta)},
                   {**h, "predictor": "training_median_common", "history_s": "", "seed": "", "mae": "1.5"},
                   {**h, "predictor": "raw_tcn", "history_s": "40", "seed": "mean", "mae": "2.0"},
                   *[{**h, "predictor": "hgb", "history_s": k, "seed": "", "mae": str(v)}
                     for k, v in (("40", 3.0), ("300", 3.5), ("900", 4.0))]]
            sm.append({"subject": s, "target": tg, "MAE": "2.5"})
            p12 += [{"subject_id": s, "target": tg, "predictor": "source_mean", "mae": "1.0"},
                    {"subject_id": s, "target": tg, "predictor": "source_median", "mae": "1.5"}]
    return {"p11_common_pool_model_comparison": cmp_, "p10_history_metrics": hm,
            "p11_common_pool_tcn_seed_mean": sm, "p12_heater_constant_metrics_common": p12}


def test_cross_check_passes_on_agreeing_tables_and_stops_on_a_disagreement():
    assert E.cross_check(_tables()) == 60
    with pytest.raises(E.P13ExportError):
        E.cross_check(_tables(delta=1e-6))


def test_supplementary_numbering_continues_s1_s34_without_gaps():
    ids = [int(sid[1:]) for sid, _, _ in E.SUPPLEMENT]
    assert ids == list(range(35, 45))
    stems = [stem for _, _, files in E.SUPPLEMENT for stem, _ in files]
    assert len(stems) == len(set(stems))
    assert all(stem.startswith(f"TableS{sid[1:]}") for sid, _, files in E.SUPPLEMENT for stem, _ in files)
