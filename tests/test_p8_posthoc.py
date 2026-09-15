"""P8 post-hoc validation analyses, protocol v1.1 addendum (synthetic data only; no study data, no model result)."""
from __future__ import annotations

import copy
import dataclasses
import json
import re

import numpy as np
import pytest
import yaml

from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P5
from src.evaluation import p6_robustness as P6
from src.evaluation import p8_posthoc as P8
from src.evaluation import splits as S
from src.evaluation.leakage import LeakageGateError
from src.training import trainer as T
from tests.test_p3_loso import synthetic_rows
from tests.test_p5_personalization import TRAIN, SynthSession, fake_base
from tests.test_splits import build

SUBJECTS = ("User01", "User02", "User07")
LOSO_ROWS = P8.loso_rows                     # the world fixture replaces P8.loso_rows while it is active


def synthetic_split(tmp):
    arr, rows = synthetic_rows()
    _, _, tables = build(arr)
    for rel, (r, cols) in tables.items():
        S.write_split(tmp / "splits" / rel, r, cols)
    return rows, S.read_split(tmp / "splits" / S.PERSONALIZATION)


def pool_mean(rows, fold):
    return rows.targets[np.isin(rows.subject, TRAIN[fold])].mean(axis=0)


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """Synthetic P3 bases, the full P5 matrix, the control runs and the analysis, run twice (two output roots)."""
    tmp = tmp_path_factory.mktemp("p8")
    with pytest.MonkeyPatch.context() as mp:
        rows, pers = synthetic_split(tmp)
        fake_base(tmp, mp, rows)
        sess = SynthSession(rows, pers)
        plan = P5.build_plan(sess)
        (tmp / "plan.yaml").write_text(yaml.safe_dump(plan, sort_keys=False))
        mp.setattr(P5, "plan_yaml", lambda: tmp / "plan.yaml")
        mp.setattr(P5, "frozen_plan", lambda: plan)
        mp.setattr(P5, "plan_commit", lambda: "x")
        mp.setattr(P8, "training_mean_value", lambda fold: (pool_mean(rows, fold), sorted(TRAIN[fold])))
        mp.setattr(P8, "loso_rows", lambda: [])
        for subject in SUBJECTS:
            for b in P5.budgets():
                for s in P5.seeds():
                    assert P5.run_personalization(sess, subject, b, s) == "complete"
        captured = []
        orig = T.train_tcn

        def spy(cfg, pressure_tr, y_tr, scaler, seed, **kw):
            captured.append({"pressure": pressure_tr.copy(), "y": y_tr.copy(), "seed": seed,
                             "init_state": kw.get("init_state"), "epochs": kw.get("epochs"), "lr": cfg.lr})
            return orig(cfg, pressure_tr, y_tr, scaler, seed, **kw)
        mp.setattr(T, "train_tcn", spy)
        outs, provs, tabs = [], [], []
        for k in (1, 2):
            P8.set_output_root(tmp / f"out{k}")
            run_sess = sess if k == 1 else SynthSession(rows, pers)
            for subject in SUBJECTS:
                for s in P5.seeds():
                    assert P8.run_init_control(run_sess, subject, s) == "complete"
            tables, prov = P8.analyse(run_sess)
            outs.append(P8.write_tables(tables, prov))
            provs.append(prov)
            tabs.append(tables)
        P8.set_output_root(tmp / "out1")
        analyses = {s: P8.analyse_subject(sess, s) for s in SUBJECTS}
        for s in SUBJECTS:
            P8.attach_control(analyses[s])
        yield {"rows": rows, "pers": pers, "sess": sess, "plan": plan, "captured": captured, "outs": outs,
               "provs": provs, "tables": tabs, "an": analyses, "tmp": tmp}
    P8.set_output_root(None)


# ------------------------------------------------------------------------------------------------ 1. identity

def test_training_mean_plus_offset_equals_the_adaptation_target_mean(world):
    rows, pers = world["rows"], world["pers"]
    for subject, fold in (("User01", 1), ("User02", 2), ("User07", 3)):
        mean = pool_mean(rows, fold)
        for b in (1, 3, 7, 14):
            sw = P5.subject_windows(rows, subject, b, pers)
            ad = sw.mask("adaptation")
            fit = P8.calibration_fits(sw, mean, {})
            c = fit["offsets"][("B", None, "pooled")]
            assert np.allclose(mean + c, sw.targets[ad].mean(axis=0), rtol=0, atol=1e-12)
            assert fit["identity_gap"]["pooled"] <= P8.IDENTITY_TOL
    for subject, checks in world["provs"][0]["checks"].items():
        gaps = [v for k, v in checks.items() if k.endswith("equals_adaptation_mean_max_abs")]
        assert gaps and max(gaps) <= P8.IDENTITY_TOL
    an = world["an"]["User07"]
    b_pred = an.preds[("B", 7, None, "pooled")]
    assert np.all(b_pred == b_pred[0])                                          # a constant predictor


def test_offset_is_the_mean_residual_with_no_optimisation():
    y = np.array([[1.0, 10.0], [3.0, 14.0]])
    p = np.array([[0.0, 11.0], [1.0, 11.0]])
    assert np.allclose(P8.calibration_offset(y, p), [1.5, 1.0])
    with pytest.raises(P8.NotEstimable):
        P8.calibration_offset(np.zeros((0, 2)), np.zeros((0, 2)))


# ------------------------------------------------------------------------------------ 2./3. only adaptation data

def test_no_test_row_enters_the_calibration(world):
    rows, pers = world["rows"], world["pers"]
    for subject, fold in (("User01", 1), ("User02", 2), ("User07", 3)):
        mean = pool_mean(rows, fold)
        for b in (1, 3, 7, 14):
            sw = P5.subject_windows(rows, subject, b, pers)
            later = (rows.subject == subject) & (rows.ts >= sw.row_ts["buffer"][0])   # buffer + every test row
            moved = dataclasses.replace(rows, targets=rows.targets + np.where(later[:, None], 7.5, 0.0))
            sw2 = P5.subject_windows(moved, subject, b, pers)
            assert not np.array_equal(sw.targets[sw.mask("test")], sw2.targets[sw2.mask("test")])
            base = {s: np.full(sw.targets[sw.mask("adaptation")].shape, 20.0 + s) for s in (0, 1, 2)}
            f1, f2 = P8.calibration_fits(sw, mean, base), P8.calibration_fits(sw2, mean, base)
            assert f1["offsets"].keys() == f2["offsets"].keys()
            assert all(np.array_equal(f1["offsets"][k], f2["offsets"][k]) for k in f1["offsets"])
            early = (rows.subject == subject) & (rows.ts <= sw.adapt_row_max_ts)
            shifted = dataclasses.replace(rows, targets=rows.targets + np.where(early[:, None], 7.5, 0.0))
            f3 = P8.calibration_fits(P5.subject_windows(shifted, subject, b, pers), mean, base)
            assert np.allclose(f3["offsets"][("B", None, "pooled")] - f1["offsets"][("B", None, "pooled")], 7.5)


def test_calibration_uses_only_the_preceding_adaptation_nights(world):
    rows, pers = world["rows"], world["pers"]
    for b in (1, 3, 7, 14):
        sw = P5.subject_windows(rows, "User07", b, pers)
        nights = P5.budget_nights(pers, "User07", b)
        ad = sw.mask("adaptation")
        good = P8.fit_window_checks(sw, nights, ad, b, 16)
        assert all(c["passed"] for c in good), good
        assert set(sw.prov["night_ordinal"][ad]) <= set(range(1, b + 1))
        assert sw.adapt_row_max_ts < sw.row_ts["buffer"][0]
        failed = lambda m: {c["check"] for c in P8.fit_window_checks(sw, nights, m, b, 16)  # noqa: E731
                            if not c["passed"]}
        buf = sw.labelled & (sw.partition == "buffer")
        assert "no_fit_window_in_the_buffer_night" in failed(ad | (buf & (np.cumsum(buf) == 1)))
        tst = sw.mask("test", True)
        assert "no_fit_window_in_a_test_or_primary_night" in failed(ad | (tst & (np.cumsum(tst) == 1)))
        assert P8.calibration_fits(sw, pool_mean(rows, 3), {})["fit_windows"]["pooled"] == int(ad.sum())
    for subject in SUBJECTS:
        for b in (1, 3, 7, 14):
            rep = json.loads((P8.calibration_dir(subject, b) / "calibration_checks.json").read_text())
            assert rep["passed"] and rep["plan_sha256_lf"] == P8.design_hashes()["plan_sha256_lf"]
            assert (P8.calibration_dir(subject, b) / "leakage_check.json").exists()


# ------------------------------------------------------------------------------------------ 4./5. User02 mats

def test_user02_pooled_calibration_pools_both_mats(world):
    rows, pers = world["rows"], world["pers"]
    sw = P5.subject_windows(rows, "User02", 3, pers)
    ad = sw.mask("adaptation")
    dev = sw.prov["device_id"][ad]
    assert set(dev) == {"22480", "22482"}
    mean = pool_mean(rows, 2)
    fit = P8.calibration_fits(sw, mean, {})
    assert fit["fit_windows"]["pooled"] == fit["fit_windows"]["22480"] + fit["fit_windows"]["22482"] == ad.sum()
    assert np.allclose(fit["offsets"][("B", None, "pooled")], sw.targets[ad].mean(0) - mean)
    an = world["an"]["User02"]
    for s in (0, 1, 2):
        d = an.preds[("D", 3, s, "pooled")] - an.preds[("C", 0, s, "none")]
        assert np.allclose(d, d[0], rtol=0, atol=1e-9)                        # one offset for both mats
    b = an.preds[("B", 3, None, "pooled")]
    assert np.array_equal(b[an.device == "22480"][0], b[an.device == "22482"][0])


def test_user02_per_mat_calibration_never_mixes_mats(world):
    rows, pers = world["rows"], world["pers"]
    sw = P5.subject_windows(rows, "User02", 7, pers)
    ad = sw.mask("adaptation")
    dev = sw.prov["device_id"][ad]
    mean = pool_mean(rows, 2)
    fit = P8.calibration_fits(sw, mean, {})
    for m in P8.MATS:
        assert np.allclose(fit["offsets"][("B", None, m)], sw.targets[ad][dev == m].mean(0) - mean)
    other = (rows.subject == "User02") & (rows.device == "22482")
    moved = dataclasses.replace(rows, targets=rows.targets + np.where(other[:, None], 9.0, 0.0))
    fit2 = P8.calibration_fits(P5.subject_windows(moved, "User02", 7, pers), mean, {})
    assert np.array_equal(fit2["offsets"][("B", None, "22480")], fit["offsets"][("B", None, "22480")])
    assert not np.array_equal(fit2["offsets"][("B", None, "22482")], fit["offsets"][("B", None, "22482")])
    one_mat = dataclasses.replace(sw, prov={**sw.prov, "device_id": np.full(sw.prov["device_id"].shape, "22480")})
    fit3 = P8.calibration_fits(one_mat, mean, {})
    assert ("B", None, "22482") not in fit3["offsets"]
    assert fit3["not_estimable"] == [{"subject_id": "User02", "budget_nights": 7, "calibration": "22482",
                                      "reason": "no labelled adaptation window on this mat"}]
    rows_out = [r for r in world["tables"][0]["by_seed"] if r["calibration"] == "per_mat"]
    an = world["an"]["User02"]
    assert rows_out and {r["eval_scope"] for r in rows_out} == set(P8.MATS)
    for r in rows_out:
        assert r["n_windows"] == int((an.device == r["eval_scope"]).sum())
    assert not any(r["calibration"] == "per_mat" for r in world["tables"][0]["by_seed"] if r["subject_id"] != "User02")


# ------------------------------------------------------------------------------------ 6./7. residual variation

def test_a_constant_predictor_has_R_equal_to_one():
    rng = np.random.default_rng(3)
    y = rng.normal([25, 45], [2, 6], (500, 2))
    st = P8.residual_stats(y, np.tile([27.0, 40.0], (500, 1)))
    for t in st:
        assert st[t]["R"] == pytest.approx(1.0, abs=1e-12)
        assert st[t]["target_sd"] == pytest.approx(np.std(y[:, 0 if t == "temperature" else 1]))


def test_a_constant_offset_leaves_the_error_sd_unchanged():
    rng = np.random.default_rng(4)
    y = rng.normal([25, 45], [2, 6], (400, 2))
    p = y + rng.normal([1, -3], [0.5, 2], (400, 2))
    a, b = P8.residual_stats(y, p), P8.residual_stats(y, p + np.array([-2.7, 11.0]))
    for t in a:
        assert b[t]["err_sd"] == pytest.approx(a[t]["err_sd"], abs=1e-12)
        assert b[t]["R"] == pytest.approx(a[t]["R"], abs=1e-12)
        assert b[t]["bias"] != pytest.approx(a[t]["bias"])
        assert a[t]["err_sd"] == pytest.approx(P5.err_sd(a[t]["rmse"], a[t]["bias"]), abs=1e-9)   # same convention
    ident = world_free_identities()
    assert ident["constant_predictor_max_abs_R_minus_1"] <= P8.IDENTITY_TOL


def world_free_identities():
    rows = []
    for label, s, esd, r in (("A", "", 2.0, 1.0), ("B", "", 2.0, 1.0), ("C", 0, 1.5, 0.75), ("D", 0, 1.5, 0.75)):
        rows.append({"subject_id": "User01", "target": "temperature", "predictor": label, "seed": s,
                     "budget_nights": 0 if label in "AC" else 3, "eval_scope": "all", "err_sd": esd, "R": r})
    return P8.identity_checks(rows)


def test_identities_hold_in_the_synthetic_analysis(world):
    ident = world["provs"][0]["identities"]
    assert ident["constant_predictor_max_abs_R_minus_1"] <= P8.IDENTITY_TOL
    assert ident["offset_error_sd_max_abs_change"] <= P8.IDENTITY_TOL


# ---------------------------------------------------------------------------- 8./9. initialization control data

def control_calls(world):
    return [c for c in world["captured"] if c["init_state"] is None]


def test_scratch_training_never_sees_nights_16_or_later(world):
    rows, pers = world["rows"], world["pers"]
    calls = control_calls(world)
    assert len(calls) == 2 * 3 * 3                                              # two output roots x 3 subjects x 3 seeds
    for subject in SUBJECTS:
        sw = P5.subject_windows(rows, subject, 14, pers)
        tr = sw.mask("adaptation")
        mine = [c for c in calls if c["pressure"].shape == sw.pressure[tr].shape
                and np.array_equal(c["pressure"], sw.pressure[tr]) and np.array_equal(c["y"], sw.targets[tr])]
        assert len(mine) == 6
        assert sw.prov["night_ordinal"][tr].max() <= 14 and not (sw.prov["night_ordinal"][tr] >= 16).any()
        assert all(c["epochs"] == 10 and c["lr"] == pytest.approx(1e-4) for c in mine)   # the frozen recipe
        nights = P5.budget_nights(pers, subject, 14)
        prim = sw.mask("test", True)
        bad = P8.control_checks(sw, nights, tr | (prim & (np.cumsum(prim) == 1)), 16)
        assert "no_training_window_in_night_15_or_the_primary_span" in {c["check"] for c in bad if not c["passed"]}
    for subject in SUBJECTS:
        for s in P5.seeds():
            d = P8.control_dir(subject, s)
            meta = json.loads((d / "run_meta.json").read_text())
            assert meta["init"] == "random" and meta["adaptation_nights"] == \
                world["plan"]["subjects"][subject]["budgets"][14]["adaptation_nights"]
            assert meta["init_weights_sha256"] not in {v["weights_sha256"] for v in
                                                       world["plan"]["subjects"][subject]["base_checkpoints"].values()}
            assert json.loads((d / "checks.json").read_text())["passed"]
            pr = P3.read_predictions(d / "predictions.parquet")
            assert pr["night_ordinal"].min() >= 16


def test_night_15_is_excluded_from_training_and_evaluation(world):
    rows, pers = world["rows"], world["pers"]
    for subject in SUBJECTS:
        sw = P5.subject_windows(rows, subject, 14, pers)
        nights = P5.budget_nights(pers, subject, 14)
        assert [P5.budget_nights(pers, subject, 14)["ordinal"][n] for n in nights["buffer"]] == [15]
        buf = sw.labelled & (sw.partition == "buffer")
        assert buf.any() and set(sw.prov["night_ordinal"][buf]) == {15}
        tr = sw.mask("adaptation")
        assert not (tr & buf).any()
        trained = [c for c in control_calls(world) if np.array_equal(c["y"], sw.targets[tr])]
        assert len(trained) == 6 and all(c["pressure"].shape[0] == int(tr.sum()) for c in trained)
        failed = {c["check"] for c in P8.control_checks(sw, nights, tr | (buf & (np.cumsum(buf) == 1)), 16)
                  if not c["passed"]}
        assert {"no_fit_window_in_the_buffer_night", "no_training_window_in_night_15_or_the_primary_span"} <= failed
        assert not np.isin(sw.prov["night_ordinal"][tr], [15]).any()
        for s in P5.seeds():
            pr = P3.read_predictions(P8.control_dir(subject, s) / "predictions.parquet")
            assert 15 not in set(pr["night_ordinal"].tolist())


def test_control_gate_failure_stops_before_any_training(world, tmp_path, monkeypatch):
    monkeypatch.setattr(P5, "frozen_plan", lambda: world["plan"])
    P8.set_output_root(tmp_path / "gated")
    calls = []
    monkeypatch.setattr(T, "train_tcn", lambda *a, **k: calls.append(1))
    try:
        sess = SynthSession(world["rows"], world["pers"], LeakageGateError("blocked"))
        with pytest.raises(LeakageGateError):
            P8.run_init_control(sess, "User01", 0)
        d = P8.control_dir("User01", 0)
        assert calls == [] and P8.run_status(d) == "failed" and not (d / "predictions.parquet").exists()
        assert not (P8.run_root() / "test_access.jsonl").exists()
    finally:
        P8.set_output_root(world["tmp"] / "out1")


# -------------------------------------------------------------------------------------- 10./11. outputs

DATE = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b|\b(19|20)\d{6}-\d{6}\b")


def test_outputs_contain_anonymous_ids_only(world):
    out = world["outs"][0]
    files = sorted(out.glob("p8_*.csv"))
    assert {f.name for f in files} >= {"p8_by_seed.csv", "p8_summary.csv", "p8_bootstrap.csv",
                                       "p8_interpretation.csv", "p8_not_estimable.csv"}
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert not DATE.search(text), f.name
        assert "\\" not in text and ":/" not in text and "night_id" not in text.splitlines()[0]
        with open(f, encoding="utf-8", newline="") as fh:
            import csv
            for r in csv.DictReader(fh):
                if r.get("subject_id"):
                    assert r["subject_id"] in SUBJECTS
                if r.get("eval_scope") not in (None, "all"):
                    assert r["eval_scope"] in P8.MATS


def test_deterministic_rerun_reproduces_every_table(world):
    a, b = world["outs"]
    for f in sorted(a.glob("p8_*.csv")):
        assert f.read_bytes() == (b / f.name).read_bytes(), f.name
    for subject in SUBJECTS:
        for s in P5.seeds():
            ra, rb = (P3.read_predictions(o.parent.parent / "runs" / "p8_posthoc" / "init_control" / subject
                                          / f"b14_seed{s}" / "predictions.parquet") for o in (a, b))
            assert np.array_equal(ra["y_pred"], rb["y_pred"])


# ------------------------------------------------------------------------------------------ analysis logic

def test_e_and_c_reproduce_the_frozen_p5_metrics(world):
    for subject, c in world["provs"][0]["checks"].items():
        assert c["p5_metrics_max_abs_diff"] <= P8.CONSISTENCY_TOL
        assert all(c[f"base_seed{s}_reproduces_p5_b0_bitwise"] for s in P5.seeds())


def test_bootstrap_sign_convention_and_shared_nights():
    rng = np.random.default_rng(0)
    y = rng.normal(25, 1, (300, 2))
    nights = np.repeat([f"n{i:02d}" for i in range(30)], 10)
    an = P8.SubjectAnalysis("User07", 3, y, nights, np.full(300, "d"), np.arange(300).astype(str))
    for b in (1, 3, 7, 14):
        an.preds[P8.pred_key("B", b, 0)] = y + 1.0                            # B worse than D and E everywhere
        for s in (0, 1, 2):
            an.preds[P8.pred_key("D", b, s)] = y + rng.normal(0, 0.2, y.shape)
            an.preds[P8.pred_key("E", b, s)] = y + rng.normal(0, 0.2, y.shape)
    rows = P8.comparator_bootstrap(an)
    be = [r for r in rows if r["first"] == "B" and r["second"] == "E" and r["role"] == "primary"]
    assert be and all(r["interval"] == "above_zero" and r["point_estimate"] > 0 for r in be)
    assert {r["n_resamples"] for r in rows} == {2000} and {r["seed"] for r in rows} == {0, 1, 2}
    assert not any(r["first"] == "S" or r["second"] == "S" for r in rows)       # no control, no S comparison


def test_interpretation_map_follows_the_preregistered_rule():
    summary, boot = [], []
    vals = {"A": 3.0, "C": 2.0, "B": 1.0, "D": 1.2, "E": 1.1, "S": 1.5}
    for t in ("temperature", "humidity"):
        for label in "AC":
            summary.append({"subject_id": "User07", "target": t, "budget_nights": 0, "predictor": label,
                            "eval_scope": "all", "calibration": "none", "mae": vals[label]})
        for b in (1, 3, 7, 14):
            for label in "BDES" if b == 14 else "BDE":
                summary.append({"subject_id": "User07", "target": t, "budget_nights": b, "predictor": label,
                                "eval_scope": "all", "calibration": "pooled" if label in "BD" else "none",
                                "mae": vals[label]})
            for first, second, side in (("D", "E", "includes_zero"), ("B", "E", "includes_zero"),
                                        ("B", "D", "below_zero")) + ((("S", "E", "above_zero"),
                                                                     ("B", "S", "below_zero")) if b == 14 else ()):
                boot.append({"subject_id": "User07", "target": t, "budget_nights": b, "first": first,
                             "second": second, "role": "primary", "interval": side})
    rows = P8.interpretation_rows(summary, boot)
    r = next(x for x in rows if x["target"] == "temperature" and x["budget_nights"] == 14)
    assert r["case_A_B_le_E"] and r["case_B_D_approx_E"] and not r["case_C_E_better_than_D"]
    assert r["B_better_than_D"] and not r["case_F_S_better_than_B"] and r["case_G_S_not_better_than_B"]
    assert r["case_H_E_better_than_S"] and not r["case_I_S_approx_or_better_than_E"]
    assert r["case_D"] is False and r["case_E"] is False                        # D and E below C: neither case
    lower_ci_but_higher_mean = copy.deepcopy(boot)
    for x in lower_ci_but_higher_mean:
        if x["first"] == "S":
            x["interval"] = "below_zero"                                        # S − E below zero, but S mean > E
    r2 = next(x for x in P8.interpretation_rows(summary, lower_ci_but_higher_mean)
              if x["target"] == "humidity" and x["budget_nights"] == 14)
    assert not r2["S_better_than_E"] and not r2["case_H_E_better_than_S"]


def test_addendum_refuses_drift_from_v1(tmp_path, monkeypatch):
    doc = P8.load_addendum()
    assert doc["base_protocol"]["sha256"] == P5.protocol_sha256()
    bad = copy.deepcopy(doc)
    bad["initialization_control"]["budget_nights"] = 7
    (tmp_path / "a.yaml").write_text(yaml.safe_dump(bad))
    monkeypatch.setattr(P8, "addendum_yaml", lambda: tmp_path / "a.yaml")
    with pytest.raises(P8.P8Error):
        P8.load_addendum()
    bad = copy.deepcopy(doc)
    bad["base_protocol"]["sha256"] = "0" * 64
    (tmp_path / "a.yaml").write_text(yaml.safe_dump(bad))
    with pytest.raises(P8.P8Error):
        P8.load_addendum()


def test_loso_residual_variation_reads_the_frozen_p3_predictions(tmp_path, monkeypatch):
    rng = np.random.default_rng(5)
    n = 60
    prov = {"subject_id": np.full(n, "User07"), "device_id": np.full(n, "d"), "session_id": np.full(n, "s"),
            "sensor_phase": np.full(n, "s1"), "channel_quality_phase": np.full(n, "normal"),
            "night_id": np.repeat(["n1", "n2", "n3"], 20), "window_start": np.arange(n) * 60,
            "window_end": np.arange(n) * 60 + 60, "target_timestamp": np.arange(n) * 60 + 59}
    y = rng.normal([25, 45], [1, 4], (n, 2))
    mask = np.ones(n, bool)

    def make(d, model, seed, p):
        P3.begin_run(d, "r")
        P3.write_predictions(d / "predictions.parquet", "r", model, 1, seed, prov, mask, y, p)
        P3.write_metrics(d / "metrics.csv", "r", 1, "User07", y, p)
        P3.complete_run(d, ["predictions.parquet", "metrics.csv"])
    for fold in (1, 2, 3):
        make(tmp_path / f"tm{fold}", "training_mean", -1, np.tile([26.0, 40.0], (n, 1)))
        for s in (0, 1, 2):
            make(tmp_path / f"f{fold}_{s}", "tcn", s, y + rng.normal(0.5, 0.3, y.shape))
    monkeypatch.setattr(P3, "training_mean_dir", lambda fold: tmp_path / f"tm{fold}")
    monkeypatch.setattr(P3, "final_dir", lambda fold, s: tmp_path / f"f{fold}_{s}")
    rows = LOSO_ROWS()
    assert len(rows) == 3 * 4 * 2
    tm = [r for r in rows if r["predictor"] == "A"]
    assert all(r["R"] == pytest.approx(1.0, abs=1e-12) and r["n_nights"] == 3 for r in tm)
    assert all(r["R"] < 1 for r in rows if r["predictor"] == "C")
    summary = P8.seed_summary(rows)
    assert {r["n_seeds"] for r in summary if r["predictor"] == "C"} == {3}


def test_p6_bootstrap_helpers_are_reused_unchanged():
    assert P6.bootstrap_settings() == (2000, 0, 0.95)
    assert P8.COMPARISONS_ALL == (("D", "E"), ("B", "E"), ("B", "D"))
    assert P8.COMPARISONS_CONTROL == (("S", "E"), ("B", "S"))
