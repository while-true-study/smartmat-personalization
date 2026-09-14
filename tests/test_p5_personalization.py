"""P5 chronological personalization (synthetic data only; no study data, no model result)."""
from __future__ import annotations

import copy
import json

import numpy as np
import pytest
import torch
import yaml

from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P
from src.evaluation import splits as S
from src.evaluation.leakage import LeakageGateError
from src.evaluation.protocol import load_protocol
from src.features.pressure_features import TargetScaler
from src.models.tcn import TCN
from src.training import trainer as T
from tests.test_p3_loso import synthetic_rows
from tests.test_splits import build

TRAIN = {1: ["User02", "User07"], 2: ["User01", "User07"], 3: ["User01", "User02"]}
BASE_CFG = {"channels": 8, "kernel_size": 2, "dropout": 0.1, "lr": 0.001, "weight_decay": 0.0001, "batch_size": 256,
            "max_epochs": 50, "early_stopping_patience": 5}


@pytest.fixture()
def synth(tmp_path):
    arr, rows = synthetic_rows()
    _, _, tables = build(arr)
    for rel, (r, cols) in tables.items():
        S.write_split(tmp_path / "splits" / rel, r, cols)
    pers = S.read_split(tmp_path / "splits" / S.PERSONALIZATION)
    return rows, pers


class SynthSession(P.P5Session):
    """Synthetic rows/split; the gate passes and writes a report (the real gate is tested in test_leakage.py)."""

    def __init__(self, rows, pers, gate_exc=None):
        super().__init__(echo=False)
        self._rows, self._pers, self.gate_exc, self.gated = rows, pers, gate_exc, 0

    def gate(self, d, ctx):
        self.gated += 1
        if self.gate_exc:
            raise self.gate_exc
        d.mkdir(parents=True, exist_ok=True)
        (d / "leakage_check.json").write_text(json.dumps({"stub": True, "scheme": ctx.scheme}))
        return None, {"dataset_version": "canonical_v1", "content_sha256": {"primary": "c" * 64},
                      "files": {"primary": "f" * 64}}


# ------------------------------------------------------------------------------------------------- windows / split

def test_windows_stay_inside_partition_night_session_and_phase(synth):
    rows, pers = synth
    for subject in ("User01", "User02", "User07"):
        for b in load_protocol()["personalization"]["budgets_nights"]:
            sw = P.subject_windows(rows, subject, b, pers)
            nights = P.budget_nights(pers, subject, b)
            assert np.array_equal(sw.first_labels, sw.last_labels)
            assert all(nights["partition"][n] == p for n, p in zip(sw.prov["night_id"], sw.partition))
            adapt = sw.mask("adaptation")
            assert set(sw.prov["night_ordinal"][adapt]) <= set(range(1, b + 1))
            assert not np.isin(sw.prov["night_id"][adapt | sw.mask("test")], nights["buffer"]).any()
            assert (b == 0) == (not adapt.any())


def test_primary_test_windows_are_identical_for_every_budget(synth):
    rows, pers = synth
    for subject in ("User01", "User02", "User07"):
        digests = {P.subject_windows(rows, subject, b, pers).primary_digest() for b in (0, 1, 3, 7, 14)}
        assert len(digests) == 1
        sw = P.subject_windows(rows, subject, 14, pers)
        assert set(sw.prov["night_ordinal"][sw.mask("test", True)]) == {16, 17, 18}


def test_adaptation_rows_precede_buffer_and_test_rows(synth):
    rows, pers = synth
    for b in (1, 3, 7, 14):
        sw = P.subject_windows(rows, "User07", b, pers)
        assert sw.adapt_row_max_ts < sw.row_ts["buffer"][0] <= sw.row_ts["buffer"][1] < sw.row_ts["test"][0]


def test_both_user02_mats_share_every_nights_partition(synth):
    rows, pers = synth
    for b in (1, 3, 7, 14):
        sw = P.subject_windows(rows, "User02", b, pers)
        for n in np.unique(sw.prov["night_id"]):
            assert len(set(sw.partition[sw.prov["night_id"] == n])) == 1
        assert set(sw.prov["device_id"][sw.mask("adaptation")]) == {"22480", "22482"}


def test_split_night_in_two_partitions_is_refused(synth):
    rows, pers = synth
    bad = copy.deepcopy(pers)
    r = next(x for x in bad if x["subject_id"] == "User02" and x["budget_nights"] == "3" and x["device_id"] == "22482"
             and x["night_ordinal"] == "2")
    r["partition"] = "test"
    with pytest.raises(P.P5Error):
        P.budget_nights(bad, "User02", 3)


# ---------------------------------------------------------------------------------------------- frozen recipe

def test_adaptation_recipe_is_the_frozen_one(monkeypatch):
    cfg, epochs = P.adaptation_config(BASE_CFG)
    assert (cfg.lr, cfg.weight_decay, cfg.batch_size, epochs) == (pytest.approx(1e-4), 1e-4, 256, 10)
    assert (cfg.channels, cfg.kernel_size, cfg.dropout) == (8, 2, 0.1)
    bad = copy.deepcopy(load_protocol())
    bad["personalization"]["fine_tuning"]["epochs"] = 20
    monkeypatch.setattr(P, "load_protocol", lambda: bad)
    with pytest.raises(P.P5Error):
        P.adaptation_config(BASE_CFG)


def test_fine_tuning_starts_from_the_base_weights_and_is_deterministic():
    rng = np.random.default_rng(0)
    p = rng.integers(0, 4096, (300, 8, 6)).astype(np.int16)
    y = np.stack([25 + p[:, -1, 0] / 4095, 40 + p[:, -1, 1] / 409.5], 1)
    sc = TargetScaler(np.array([25.5, 45.0]), np.array([0.3, 3.0]), {"subjects": ["x"]})
    torch.manual_seed(1)
    base = {k: v.clone() for k, v in TCN(6, 8, 2, 0.1).state_dict().items()}
    frozen = T.TCNConfig(8, 2, 0.1, 0.0, 1e-4, 256, 1, 5)                  # lr 0 -> AdamW leaves weights as they are
    r0 = T.train_tcn(frozen, p, y, sc, 0, epochs=1, log=lambda m: None, init_state=base)
    assert all(torch.equal(r0.model.state_dict()[k].cpu(), base[k]) for k in base)
    cfg, _ = P.adaptation_config(BASE_CFG)
    a = T.train_tcn(cfg, p, y, sc, 1, epochs=10, log=lambda m: None, init_state=base)
    b = T.train_tcn(cfg, p, y, sc, 1, epochs=10, log=lambda m: None, init_state=base)
    assert a.epochs_run == 10 and a.best_epoch is None                       # no early stopping, no validation
    assert all(torch.equal(a.model.state_dict()[k], b.model.state_dict()[k]) for k in base)
    assert not all(torch.equal(a.model.state_dict()[k].cpu(), base[k]) for k in base)


# ------------------------------------------------------------------------------------------- end-to-end (synthetic)

def fake_base(tmp_path, monkeypatch, rows):
    """Synthetic P3 selection + base checkpoints for the three folds (seeds 0/1/2)."""
    sel = {"folds": {}, "file_sha256": "p" * 64}
    for fold, train in TRAIN.items():
        m = np.isin(rows.subject, train)
        mean, std = rows.targets[m].mean(0), rows.targets[m].std(0)
        sel["folds"][fold] = {"train_subjects": train, "config": BASE_CFG, "selected_index": 0, "final_epochs": 1,
                              "selection_sha256": f"s{fold}" * 8,
                              "outer_target_scaler": {"mean": mean.tolist(), "std": std.tolist(), "n": int(m.sum())}}
        for seed in (0, 1, 2):
            d = tmp_path / "p3" / f"fold{fold}_seed{seed}"
            P3.begin_run(d, f"r{fold}{seed}")
            torch.manual_seed(10 * fold + seed)
            torch.save(TCN(6, 8, 2, 0.1).state_dict(), d / "model.pt")
            (d / "run_meta.json").write_text(json.dumps({
                "run_id": f"r{fold}{seed}", "selection_sha256": f"s{fold}" * 8, "git_commit": "c" * 40,
                "scaler": {"mean": mean.tolist(), "std": std.tolist(), "transform": "target_zscore",
                           "scheme": "loso", "fold": str(fold), "partition": "train", "subjects": sorted(train),
                           "nights": None, "n": int(m.sum())}}))
            P3.complete_run(d, ["model.pt", "run_meta.json"])
    monkeypatch.setattr(P, "p3_selection", lambda: sel)
    monkeypatch.setattr(P, "base_run_dir", lambda fold, seed: tmp_path / "p3" / f"fold{fold}_seed{seed}")
    monkeypatch.setattr(P, "run_root", lambda: tmp_path / "p5")
    return sel


def test_personalization_runs_end_to_end_without_refitting_the_scaler(synth, tmp_path, monkeypatch):
    rows, pers = synth
    fake_base(tmp_path, monkeypatch, rows)
    sess = SynthSession(rows, pers)
    plan = P.build_plan(sess)
    (tmp_path / "plan.yaml").write_text(yaml.safe_dump(plan, sort_keys=False))
    monkeypatch.setattr(P, "plan_yaml", lambda: tmp_path / "plan.yaml")
    monkeypatch.setattr(P, "frozen_plan", lambda: plan)
    monkeypatch.setattr(P, "plan_commit", lambda: "plan" + "0" * 36)
    monkeypatch.setattr(TargetScaler, "fit", classmethod(lambda cls, *a, **k: pytest.fail("scaler refit")))
    assert P.run_personalization(sess, "User07", 0, 1) == "complete"
    assert P.run_personalization(sess, "User07", 3, 1) == "complete"
    d0, d3 = P.run_dir("User07", 0, 1), P.run_dir("User07", 3, 1)
    m0, m3 = (json.loads((d / "run_meta.json").read_text()) for d in (d0, d3))
    assert m0["kind"] == "base_eval" and not (d0 / "model.pt").exists() and m0["epochs_run"] == 0
    assert m3["kind"] == "adaptation" and m3["epochs_run"] == 10
    assert m3["adaptation_config"]["lr"] == pytest.approx(1e-4) and m3["adaptation_nights"] == \
        plan["subjects"]["User07"]["budgets"][3]["adaptation_nights"]
    assert m3["base_checkpoint"]["weights_sha256"] == plan["subjects"]["User07"]["base_checkpoints"][1]["weights_sha256"]
    assert m3["weights_sha256"] != m3["base_checkpoint"]["weights_sha256"]
    for k in ("git_commit", "protocol_sha256", "split_sha256", "canonical_primary_content_sha256", "plan_commit",
              "p3_selected_configs_sha256", "buffer_nights", "primary_test_nights", "seed", "base_lr", "scaler",
              "predictions_sha256", "model_sha256", "deterministic_algorithms"):
        assert k in m3, k
    assert all(c["passed"] for c in json.loads((d3 / "p5_checks.json").read_text())["checks"])
    pr = P3.read_predictions(d3 / "predictions.parquet")
    assert set(pr["subject_id"]) == {"User07"} and pr["primary_test"].any() and not np.isin(
        pr["night_ordinal"], [1, 2, 3, 4]).any()                               # no adaptation or buffer night scored
    assert P.test_access_counts() == {"User07|b0|seed1": 1, "User07|b3|seed1": 1}
    assert P.run_personalization(sess, "User07", 3, 1) == "skipped (complete)"
    assert P.test_access_counts()["User07|b3|seed1"] == 1


def test_run_refuses_before_the_plan_is_committed(synth, tmp_path, monkeypatch):
    rows, pers = synth
    monkeypatch.setattr(P, "run_root", lambda: tmp_path / "p5")
    monkeypatch.setattr(P, "plan_yaml", lambda: tmp_path / "missing.yaml")
    sess = SynthSession(rows, pers)
    with pytest.raises(P.PlanNotFrozenError):
        P.run_personalization(sess, "User01", 1, 0)
    assert sess.gated == 0 and not (tmp_path / "p5").exists()
    (tmp_path / "missing.yaml").write_text("x")
    monkeypatch.setattr(P, "frozen_plan", lambda: {})
    with pytest.raises(P.PlanNotFrozenError):
        P.run_personalization(sess, "User01", 1, 0)                          # present but not committed
    assert sess.gated == 0 and not (tmp_path / "p5").exists()


def test_gate_failure_stops_the_run_before_any_training(synth, tmp_path, monkeypatch):
    rows, pers = synth
    fake_base(tmp_path, monkeypatch, rows)
    plan = P.build_plan(SynthSession(rows, pers))
    monkeypatch.setattr(P, "frozen_plan", lambda: plan)
    monkeypatch.setattr(P, "plan_commit", lambda: "x")
    calls = []
    monkeypatch.setattr(T, "train_tcn", lambda *a, **k: calls.append(1))
    sess = SynthSession(rows, pers, LeakageGateError("blocked"))
    with pytest.raises(LeakageGateError):
        P.run_personalization(sess, "User01", 7, 2)
    d = P.run_dir("User01", 7, 2)
    assert calls == [] and P.run_status(d) == "failed" and not (d / "predictions.parquet").exists()
    assert P.test_access_counts() == {}


def test_p5_checks_fail_closed_on_refit_scaler_and_changed_plan(synth, tmp_path, monkeypatch):
    rows, pers = synth
    sel = fake_base(tmp_path, monkeypatch, rows)
    sess = SynthSession(rows, pers)
    plan = P.build_plan(sess)
    sw = sess.windows("User02", 7)
    nights = P.budget_nights(pers, "User02", 7)
    cfg, ep = P.adaptation_config(BASE_CFG)
    ok = P.base_scaler(2, sel)
    good = P.p5_checks("User02", 7, sw, nights, pers, sel, ok, cfg, ep, plan["subjects"]["User02"])
    assert all(c["passed"] for c in good) and len(good) == 10
    refit = TargetScaler(ok.mean + 0.5, ok.std, dict(ok.fit_provenance))
    bad = P.p5_checks("User02", 7, sw, nights, pers, sel, refit, cfg, ep, plan["subjects"]["User02"])
    assert [c["check"] for c in bad if not c["passed"]] == ["scaler_not_refit_on_target_data"]
    leaky = TargetScaler(ok.mean, ok.std, {**ok.fit_provenance, "subjects": ["User01", "User02", "User07"]})
    assert not next(c for c in P.p5_checks("User02", 7, sw, nights, pers, sel, leaky, cfg, ep,
                                           plan["subjects"]["User02"])
                    if c["check"] == "scaler_fit_on_outer_training_subjects_only")["passed"]
    longer = T.TCNConfig(**{**cfg.as_dict(), "lr": 1e-3})
    assert not next(c for c in P.p5_checks("User02", 7, sw, nights, pers, sel, ok, longer, ep,
                                           plan["subjects"]["User02"])
                    if c["check"] == "no_test_based_selection_recipe_frozen")["passed"]


def test_full_matrix_and_aggregation_on_synthetic_data(synth, tmp_path, monkeypatch):
    rows, pers = synth
    fake_base(tmp_path, monkeypatch, rows)
    sess = SynthSession(rows, pers)
    plan = P.build_plan(sess)
    (tmp_path / "plan.yaml").write_text(yaml.safe_dump(plan, sort_keys=False))
    monkeypatch.setattr(P, "plan_yaml", lambda: tmp_path / "plan.yaml")
    monkeypatch.setattr(P, "frozen_plan", lambda: plan)
    monkeypatch.setattr(P, "plan_commit", lambda: "x")
    monkeypatch.setattr(P, "metrics_dir", lambda: tmp_path / "metrics")
    for subject in ("User01", "User02", "User07"):
        for b in (0, 1, 3, 7, 14):
            for s in (0, 1, 2):
                assert P.run_personalization(sess, subject, b, s) == "complete"
    t = P.aggregate()
    assert len(t["by_seed"]) == 3 * 5 * 3 * 2 * 2
    assert {r["n_nights"] for r in t["by_seed"] if r["span"] == "primary"} == {3}
    g = [r for r in t["adaptation_gain"] if r["budget_nights"] == 0]
    assert all(r["G_pct"] == 0.0 for r in g)
    kinds = {(r["subject_id"], r["stratum"]) for r in t["strata"] if r["seed"] == "mean"}
    assert {("User02", "22480"), ("User02", "22482"), ("User01", "s2")} <= kinds    # synthetic s1 ends before night 16
    assert ("User01", "s1") not in kinds
    assert {r["budget_nights"] for r in t["budget_counts"]} == {0, 1, 3, 7, 14}
    assert all(v == 1 for v in P.test_access_counts().values()) and len(P.test_access_counts()) == 45
    out = P.write_tables(t)
    for name in ("by_seed", "primary_summary", "adaptation_gain", "per_night", "strata", "budget_counts"):
        assert (out / f"p5_{name}.csv").exists()


# ------------------------------------------------------------------------------------------------------ analysis

def test_adaptation_gain_is_signed_and_never_clipped(monkeypatch):
    rows = []
    for subject, (e0, eb) in {"User01": (2.0, 3.0), "User02": (5.0, 1.0), "User07": (2.0, 2.0)}.items():
        for b in (0, 1, 3, 7, 14):
            for s in (0, 1, 2):
                v = e0 if b == 0 else eb
                for t in ("temperature", "humidity"):
                    rows.append({"subject_id": subject, "fold": 1, "budget_nights": b, "seed": s, "span": "primary",
                                 "target": t, "mae": v, "rmse": v + 1, "bias": -v if subject == "User02" else v / 2,
                                 "err_sd": 1.0, "n_windows": 10, "n_nights": 2})
    g = P.gain_rows(rows, P.seed_summary(rows, "primary"))
    u1 = next(r for r in g if r["subject_id"] == "User01" and r["budget_nights"] == 7 and r["target"] == "humidity")
    assert u1["G_pct"] == pytest.approx(-50.0) and u1["delta_E"] == pytest.approx(-1.0)
    assert u1["C_b"] == pytest.approx(1.0 - 1.5) and u1["seeds_improved"] == 0
    u2 = next(r for r in g if r["subject_id"] == "User02" and r["budget_nights"] == 14 and r["target"] == "temperature")
    assert u2["G_pct"] == pytest.approx(80.0) and u2["C_b"] == pytest.approx(4.0) and u2["seeds_improved"] == 3
    c = next(r for r in g if r["subject_id"] == "unweighted_mean" and r["budget_nights"] == 1
             and r["target"] == "temperature")
    assert c["E0_mae"] == pytest.approx(3.0) and c["Eb_mae"] == pytest.approx(2.0)
    assert c["G_pct"] == pytest.approx(100 / 3) and c["subjects_improved"] == 1
    assert c["abs_bias_0"] == pytest.approx((1.0 + 5.0 + 1.0) / 3)          # |bias| averaged, not signed bias
    z = next(r for r in g if r["subject_id"] == "User07" and r["budget_nights"] == 0 and r["target"] == "humidity")
    assert z["G_pct"] == 0.0 and z["delta_E"] == 0.0
