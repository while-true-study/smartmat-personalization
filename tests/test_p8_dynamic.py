"""P8 final dynamic-signal diagnostic, protocol v1.2 (synthetic data only; no study data, no model result)."""
from __future__ import annotations

import csv
import dataclasses
import re

import numpy as np
import pytest

from src.evaluation import p5_personalization as P5
from src.evaluation import p8_dynamic as D
from tests.test_p8_posthoc import SUBJECTS, world  # noqa: F401  (module fixture reused)

RNG = np.random.default_rng(11)


def nights_of(n_nights: int, per: int) -> np.ndarray:
    return np.repeat([f"n{i:03d}" for i in range(n_nights)], per)


# ------------------------------------------------------------------------------------------ 1.-6. pure metrics

def test_identity_R2_equals_1_plus_Q2_minus_2rQ():
    for _ in range(20):
        y = RNG.normal(25, 2, 400)
        p = 0.3 * y + RNG.normal(0, RNG.uniform(0.1, 3), 400) + RNG.normal(0, 5)
        st = D.signal_stats(y, p, nights_of(20, 20))
        assert st["identity_gap"] <= 1e-12
        assert st["R"] ** 2 == pytest.approx(1 + st["Q"] ** 2 - 2 * st["r_pooled"] * st["Q"], abs=1e-12)
        assert st["oracle_affine"] == pytest.approx(np.sqrt(1 - st["r_pooled"] ** 2))


def test_constant_predictor_has_Q_zero_R_one_and_undefined_correlations():
    y = RNG.normal(25, 2, 300)
    st = D.signal_stats(y, np.full(300, 23.7), nights_of(10, 30))
    assert st["constant"] and st["Q"] == 0.0 and st["R"] == pytest.approx(1.0, abs=1e-12)
    assert all(np.isnan(st[k]) for k in ("r_pooled", "r_within", "r_within_mat", "oracle_affine"))


def test_a_constant_offset_changes_no_scale_or_correlation_statistic():
    y = RNG.normal(40, 8, 600)
    nights = nights_of(30, 20)
    p = 0.5 * y + RNG.normal(0, 4, 600)
    a, b = D.signal_stats(y, p, nights), D.signal_stats(y, p - 17.25, nights)
    for k in ("R", "Q", "r_pooled", "r_within", "r_within_mat", "oracle_affine"):
        assert b[k] == pytest.approx(a[k], abs=1e-12), k
    assert b["bias"] != pytest.approx(a["bias"])


def test_night_centring_removes_a_pure_between_night_level_shift():
    nights = nights_of(25, 40)
    y = RNG.normal(30, 2, nights.size)
    p = 0.4 * y + RNG.normal(0, 1, nights.size)
    shift = np.repeat(RNG.normal(0, 10, 25), 40)
    a, b = D.signal_stats(y, p, nights), D.signal_stats(y, p + shift, nights)
    assert b["r_within"] == pytest.approx(a["r_within"], abs=1e-12)
    assert b["r_within_mat"] == pytest.approx(a["r_within_mat"], abs=1e-12)
    assert abs(b["r_pooled"] - a["r_pooled"]) > 0.05                       # the pooled correlation does change


def test_within_night_tracking_gives_a_positive_within_night_correlation():
    nights = nights_of(30, 50)
    level = np.repeat(RNG.normal(0, 5, 30), 50)
    signal = RNG.normal(0, 1, nights.size)
    y = 25 + level + signal
    p = 24 + np.repeat(RNG.normal(0, 5, 30), 50) + signal + RNG.normal(0, 0.5, nights.size)  # levels unrelated
    st = D.signal_stats(y, p, nights)
    assert st["r_within"] > 0.8 and st["r_within"] > st["r_pooled"]


def test_a_between_night_only_relationship_gives_pooled_but_no_within_night_correlation():
    nights = nights_of(40, 50)
    level = np.repeat(RNG.normal(0, 3, 40), 50)
    y = 25 + level + RNG.normal(0, 1, nights.size)
    p = 25 + level + RNG.normal(0, 1, nights.size)                           # independent within-night noise
    st = D.signal_stats(y, p, nights)
    assert st["r_pooled"] > 0.8 and abs(st["r_within"]) < 0.1


def test_mat_centring_removes_between_mat_levels_inside_a_night():
    nights = nights_of(20, 60)
    mats = np.tile(np.repeat(["22480", "22482"], 30), 20)
    offset = np.where(mats == "22482", 4.0, 0.0)
    y = 25 + offset + RNG.normal(0, 1, nights.size)
    p = 25 + offset + RNG.normal(0, 1, nights.size)                          # only the mat level is shared
    st = D.signal_stats(y, p, nights, mats)
    assert st["r_within"] > 0.7 and abs(st["r_within_mat"]) < 0.1


def test_per_night_correlations_report_exclusions_instead_of_dropping_nights():
    nights = np.concatenate([nights_of(5, 20), np.repeat(["short"], 5), np.repeat(["flat"], 20)])
    y = np.concatenate([RNG.normal(25, 1, 100), RNG.normal(25, 1, 5), np.full(20, 25.0)])
    p = y + RNG.normal(0, 1, y.size)
    s = D.per_night_summary(y, p, nights)
    assert (s["n_nights_eligible"], s["n_nights_too_few_windows"], s["n_nights_zero_target_sd"],
            s["n_nights_total"]) == (5, 1, 1, 7)


# ------------------------------------------------------------------------------------------ bootstrap exactness

def test_resampled_correlations_equal_the_window_level_values_of_the_resampled_data():
    nights = nights_of(12, 30)
    mats = np.tile(np.repeat(["a", "b"], 15), 12)
    y = RNG.normal(25, 2, nights.size) + np.repeat(RNG.normal(0, 2, 12), 30)
    p = 0.5 * y + RNG.normal(0, 1, nights.size)
    m = D.night_moments(y, p, nights, mats)
    counts = np.zeros((1, 12))
    counts[0, 0], counts[0, 3], counts[0, 7], counts[0, 11] = 1, 2, 1, 3   # night 3 drawn twice, night 11 thrice
    w = D.weighted_corrs(counts, m)
    keep = np.concatenate([np.flatnonzero(nights == m.night[i]) for i in range(12) for _ in range(int(counts[0, i]))])
    # duplicated nights need distinct ids for the direct computation, as each draw is its own cluster
    dup = np.concatenate([np.full(int((nights == m.night[i]).sum()), f"{i}_{k}") for i in range(12)
                          for k in range(int(counts[0, i]))])
    direct = D.signal_stats(y[keep], p[keep], dup, mats[keep])
    for k in D.STATS:
        assert w[k][0] == pytest.approx(direct[k], abs=1e-12), k


# ------------------------------------------------------------------------------ 7.-9. affine fit (if triggered)

def test_affine_fit_is_ordinary_least_squares_and_degenerates_to_the_adaptation_mean():
    p = RNG.normal(0, 1, 200)
    y = 2.5 * p + 7 + RNG.normal(0, 0.1, 200)
    a, c, deg = D.affine_fit(y, p)
    slope, icept = np.polyfit(p, y, 1)
    assert (a, c) == pytest.approx((slope, icept)) and not deg
    a, c, deg = D.affine_fit(y, np.full(200, 3.0))
    assert deg and a == 0.0 and c == pytest.approx(y.mean())


def test_affine_fit_uses_no_test_label_and_only_the_adaptation_nights(world):  # noqa: F811
    rows, pers = world["rows"], world["pers"]
    for subject in SUBJECTS:
        for b in (1, 3, 7, 14):
            sw = P5.subject_windows(rows, subject, b, pers)
            ad = sw.mask("adaptation")
            base = {s: sw.targets[ad] * 0.5 + RNG.normal(0, 1, sw.targets[ad].shape) for s in (0, 1, 2)}
            later = (rows.subject == subject) & (rows.ts >= sw.row_ts["buffer"][0])
            moved = dataclasses.replace(rows, targets=rows.targets + np.where(later[:, None], 9.0, 0.0))
            sw2 = P5.subject_windows(moved, subject, b, pers)
            f1, f2 = D.affine_fits(sw, base), D.affine_fits(sw2, base)
            assert f1["fits"] == f2["fits"]                                  # test labels change nothing
            assert f1["fit_windows"] == int(ad.sum())
            assert set(sw.prov["night_ordinal"][ad]) <= set(range(1, b + 1))
            if subject == "User02":
                assert f1["fit_mats"] == ["22480", "22482"]                  # pooled over both mats


def test_triggered_affine_comparator_runs_gated_on_adaptation_windows(world, tmp_path):  # noqa: F811
    D.set_output_root(tmp_path / "dyn_affine")
    try:
        offset_rows = list(csv.DictReader(open(world["outs"][0] / "p8_by_seed.csv", encoding="utf-8")))
        ds = D.load_subject("User02", offset_rows, offset_rows)
        recs = D.run_affine(world["sess"], ds)
        assert {r["budget_nights"] for r in recs} == {1, 3, 7, 14} and all(r["fit_mats"] == "22480;22482"
                                                                            for r in recs)
        for b in (1, 3, 7, 14):
            d = D.run_root() / "affine" / "User02" / f"b{b:02d}"
            assert (d / "leakage_check.json").exists() and (d / "affine_checks.json").exists()
        a, c = recs[0]["slope_a"], recs[0]["intercept_c"]
        f = ds.preds[("F", recs[0]["budget_nights"], recs[0]["seed"])][:, 0]
        assert np.allclose(f, a * ds.preds[("C", 0, recs[0]["seed"])][:, 0] + c)
        assert len(D.affine_mae_bootstrap(ds)) == 4 * 3 * 3 * 2
    finally:
        D.set_output_root(None)


# ------------------------------------------------------------------------- 10.-11. end to end, determinism, privacy

@pytest.fixture(scope="module")
def dynamic_runs(world, tmp_path_factory):  # noqa: F811
    offset_rows = list(csv.DictReader(open(world["outs"][0] / "p8_by_seed.csv", encoding="utf-8")))
    outs = []
    for k in (1, 2):
        D.set_output_root(tmp_path_factory.mktemp(f"dyn{k}"))
        tables, prov = D.analyse(offset_rows=offset_rows, run_affine_if_triggered=False)
        outs.append((D.write_tables(tables, prov), tables, prov))
    D.set_output_root(None)
    return outs


def test_diagnostic_checks_hold_on_the_synthetic_matrix(dynamic_runs):
    _, tables, prov = dynamic_runs[0]
    assert prov["checks"]["d_equals_c_max_abs_diff"] <= D.IDENTITY_TOL
    assert prov["checks"]["identity_max_gap"] <= D.IDENTITY_TOL
    assert prov["checks"]["constant_rows_R_Q"] == [(1.0, 0.0)]
    const = [r for r in tables["by_seed"] if r["condition"] in "AB"]
    assert const and all(np.isnan(r["r_pooled"]) and r["Q"] == 0.0 for r in const)
    assert {r["condition"] for r in tables["cases"]} == {"C", "E", "S"}
    assert {(r["condition"], r["budget_nights"]) for r in tables["headlines"]} == {("C", 0), ("E", 14), ("S", 14)}
    assert prov["design"]["plan_sha256_lf"] == D.design_hashes()["plan_sha256_lf"]
    assert all(r["status"] == D.STATUS for r in tables["by_seed"])


def test_deterministic_rerun_reproduces_every_table(dynamic_runs):
    a, b = dynamic_runs[0][0], dynamic_runs[1][0]
    files = sorted(a.glob("p8_dynamic_*.csv"))
    assert files
    for f in files:
        assert f.read_bytes() == (b / f.name).read_bytes(), f.name


def test_outputs_contain_anonymous_ids_only(dynamic_runs):
    date = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b|\b(19|20)\d{6}-\d{6}\b")
    for f in sorted(dynamic_runs[0][0].glob("p8_dynamic_*.csv")):
        text = f.read_text(encoding="utf-8")
        assert not date.search(text) and "night_id" not in text.splitlines()[0] and "\\" not in text, f.name
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r.get("subject_id"):
                assert r["subject_id"] in SUBJECTS


def test_trigger_rule_needs_two_subjects_and_two_seeds():
    base = dict(condition="C", target="temperature")
    rows = [dict(base, subject_id="User01", oracle_affine=0.85, oracle_affine_seeds_at_most_0_90=2),
            dict(base, subject_id="User02", oracle_affine=0.88, oracle_affine_seeds_at_most_0_90=1),
            dict(base, subject_id="User07", oracle_affine=0.99, oracle_affine_seeds_at_most_0_90=0)]
    rows += [dict(r, target="humidity", oracle_affine=0.8, oracle_affine_seeds_at_most_0_90=3) for r in rows[:2]]
    t = D.trigger(rows)
    assert not t["per_target"]["temperature"]["fires"]                       # one isolated seed does not count
    assert t["per_target"]["humidity"]["fires"] and t["fired"]


def test_correlation_classes_follow_the_preregistered_thresholds():
    assert D.r_class(0.25, "above_zero") == "positive"
    assert D.r_class(0.05, "above_zero") == "small"
    assert D.r_class(0.25, "includes_zero") == "zero"
    assert D.r_class(-0.3, "below_zero") == "negative"
    assert D.r_class(float("nan"), "undefined") == "na"


def test_config_refuses_drift(tmp_path, monkeypatch):
    import yaml
    doc = D.load_config()
    bad = dict(doc, definitions=dict(doc["definitions"], oracle_headroom_at_most=0.8))
    (tmp_path / "c.yaml").write_text(yaml.safe_dump(bad))
    monkeypatch.setattr(D, "config_yaml", lambda: tmp_path / "c.yaml")
    with pytest.raises(D.P8DynamicError):
        D.load_config()
