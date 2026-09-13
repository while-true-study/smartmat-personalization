"""P4 feature-family pipeline (synthetic data only; no study data, no model result)."""
from __future__ import annotations

import copy
import json

import numpy as np
import pytest
import torch

from src.evaluation import p3_loso as P3
from src.evaluation import p4_ablation as P4
from src.evaluation import splits as S
from src.evaluation.leakage import LeakageGateError, RunContext, run_gate
from src.evaluation.protocol import load_protocol, protocol_sha256
from src.features.pressure_features import TargetScaler, family_features
from src.training import trainer as T
from src.training.loso_data import fold_data
from tests.test_p3_loso import FakeSession, synth, synthetic_rows  # noqa: F401  (fixture)
from tests.test_splits import build

DIMS = {"MOVEMENT": 10, "CONTACT": 11, "RAW+MOVEMENT": 16, "RAW+CONTACT": 17, "RAW+MOVEMENT+CONTACT": 27}
FROZEN_GRID = T.config_grid


class PassingSession(FakeSession):
    """Gate stub that passes and writes a report, so a synthetic run can complete (the real gate is tested above)."""

    def gate(self, d, ctx):
        out = super().gate(d, ctx)
        (d / "leakage_check.json").write_text(json.dumps({"stub": True, "input_features": ctx.input_features}))
        return out


def tiny_grid(_protocol):
    """16 configurations of the frozen grid, cut to 2 epochs / patience 1 so synthetic training stays fast."""
    return [T.TCNConfig(g.channels, g.kernel_size, g.dropout, g.lr, g.weight_decay, g.batch_size, 2, 1)
            for g in FROZEN_GRID(load_protocol())]


# ------------------------------------------------------------------------------------------------ family guard

def test_p4_trains_exactly_the_five_declared_families():
    assert P4.P4_FAMILIES == ("MOVEMENT", "CONTACT", "RAW+MOVEMENT", "RAW+CONTACT", "RAW+MOVEMENT+CONTACT")
    for fam, n in DIMS.items():
        assert len(P4.assert_p4_family(fam)) == n
    with pytest.raises(P4.P4Error):
        P4.assert_p4_family("RAW")                          # frozen P3 reference, never re-run in P4
    with pytest.raises(P4.P4Error):
        P4.assert_p4_family("RAW+POSITION")
    assert set(P4.ALL_FAMILIES) == set(load_protocol()["inputs"]["families"])


def test_family_guard_fails_closed_on_a_changed_protocol_composition(monkeypatch):
    bad = copy.deepcopy(load_protocol())
    bad["inputs"]["families"]["CONTACT"] = ["raw", "contact"]
    monkeypatch.setattr(P4, "load_protocol", lambda: bad)
    with pytest.raises(P4.P4Error):
        P4.assert_family_inputs("CONTACT")


def test_trainer_builds_a_tcn_with_the_family_input_width():
    p = np.random.default_rng(0).integers(0, 4096, (600, 8, 6)).astype(np.int16)
    y = np.stack([25 + p[:, -1, 0] / 4095, 40 + p[:, -1, 1] / 409.5], 1)
    sc = TargetScaler.fit(y[:400], scheme="synthetic", fold="0", partition="train", subjects=["s"])
    cfg = T.TCNConfig(8, 2, 0.1, 1e-3, 1e-4, 256, 2, 5)
    for fam, n in DIMS.items():
        r = T.train_tcn(cfg, p[:400], y[:400], sc, 0, epochs=2, log=lambda m: None, family=fam)
        assert r.model.blocks[0].main[0].conv.in_channels == n
        out = T.predict_z(r.model, T.to_tensor(p[400:], T.device(), fam))
        assert out.shape == (200, 2) and np.all(np.isfinite(out))


def test_raw_training_path_is_unchanged_by_the_family_argument():
    p = np.random.default_rng(1).integers(0, 4096, (700, 8, 6)).astype(np.int16)
    y = np.stack([25 + p[:, -1, 2] / 4095, 40 + p[:, -1, 3] / 409.5], 1)
    sc = TargetScaler.fit(y[:500], scheme="synthetic", fold="0", partition="train", subjects=["s"])
    cfg = T.TCNConfig(16, 3, 0.1, 1e-3, 1e-4, 256, 3, 5)
    a = T.train_tcn(cfg, p[:500], y[:500], sc, 0, pressure_va=p[500:], y_va=y[500:], log=lambda m: None)
    b = T.train_tcn(cfg, p[:500], y[:500], sc, 0, pressure_va=p[500:], y_va=y[500:], log=lambda m: None,
                    family="RAW")
    assert a.history == b.history and a.best_epoch == b.best_epoch
    assert all(torch.equal(a.model.state_dict()[k], b.model.state_dict()[k]) for k in a.model.state_dict())


# ------------------------------------------------------------------------------------------------ leakage gate

def _gate_inputs(split_dir):
    arr, _ = synthetic_rows()
    sessions, pieces, _ = build(arr)
    man = {"protocol_version": "v1.0", "protocol_sha256": protocol_sha256(),
           "files": {rel: {"sha256": S.file_sha256_lf(split_dir / rel)} for rel in S.SPLIT_FILES},
           "canonical": {"dataset_version": "canonical_v1", "primary_content_sha256": "c" * 64,
                         "primary_file_sha256": "f" * 64}}
    canon = {"dataset_version": "canonical_v1", "content_sha256": {"primary": "c" * 64},
             "files": {"primary": "f" * 64}}
    return sessions, pieces, man, canon


@pytest.mark.parametrize("family", list(DIMS))
def test_family_inner_context_passes_gate_and_forbidden_inputs_fail(synth, family):  # noqa: F811
    rows, split_dir = synth
    sessions, pieces, man, canon = _gate_inputs(split_dir)
    fd = fold_data(rows, 2, split_dir)
    tr = fd.labelled & (fd.inner["B"] == "inner_train")
    feats = list(P4.assert_p4_family(family))
    ok = RunContext("loso", fold=2, input_features=feats,
                    fit_records=[{"transform": "target_zscore", "partition": "inner_train", "subjects": ["User07"]}],
                    selection_subjects=["User01"], window_groups=fd.window_groups(tr, "B"))
    rep = run_gate(split_dir, man, load_protocol(), sessions, pieces, ok, canon)
    assert rep.passed, rep.failures()
    for extra in ("humidity", "device_id", "night_id", "channel_quality_phase", "control_event"):
        bad = RunContext("loso", fold=2, input_features=feats + [extra], fit_records=ok.fit_records,
                         selection_subjects=ok.selection_subjects, window_groups=ok.window_groups)
        assert not run_gate(split_dir, man, load_protocol(), sessions, pieces, bad, canon).passed, extra


def test_gate_runs_before_the_trainer_and_fails_closed(synth, tmp_path, monkeypatch):  # noqa: F811
    rows, split_dir = synth
    fd = fold_data(rows, 1, split_dir)
    monkeypatch.setattr(P4, "run_root", lambda: tmp_path / "runs")
    calls = []
    monkeypatch.setattr(T, "train_tcn", lambda *a, **k: calls.append(1))
    sess = FakeSession(fd, LeakageGateError("blocked"))
    with pytest.raises(LeakageGateError):
        P4.run_inner(sess, "CONTACT", 1, "A", 0)
    d = P4.inner_dir("CONTACT", 1, "A", 0)
    assert sess.gated == 1 and calls == [] and P4.run_status(d) == "failed" and not (d / "best_model.pt").exists()
    with pytest.raises(P4.P4Error):
        P4.run_inner(sess, "RAW", 1, "A", 0)               # RAW is refused before any gate or run directory
    assert sess.gated == 1 and not P4.inner_dir("RAW", 1, "A", 0).exists()


# --------------------------------------------------------------------------------- runs, selection, one look

def test_inner_run_records_family_and_run_identity(synth, tmp_path, monkeypatch):  # noqa: F811
    rows, split_dir = synth
    fd = fold_data(rows, 3, split_dir)
    monkeypatch.setattr(P4, "run_root", lambda: tmp_path / "runs")
    monkeypatch.setattr(T, "config_grid", tiny_grid)
    sess = PassingSession(fd)
    assert P4.run_inner(sess, "RAW+MOVEMENT+CONTACT", 3, "B", 5) == "complete"
    d = P4.inner_dir("RAW+MOVEMENT+CONTACT", 3, "B", 5)
    assert d.parts[-3:] == ("raw_movement_contact", "inner", "fold3_B_cfg05") and P4.run_status(d) == "complete"
    meta = json.loads((d / "run_meta.json").read_text())
    assert meta["family"] == "RAW+MOVEMENT+CONTACT" and meta["n_inputs"] == 27 and meta["seed"] == 0
    assert meta["deterministic_algorithms"] is True and meta["p3_tag"] == "p3-loso-baseline"
    assert meta["inner_val_subject"] not in (fd.held_out, meta["inner_train_subject"])
    state = torch.load(d / "best_model.pt")
    assert state["blocks.0.main.0.conv.weight"].shape[1] == 27
    assert P4.run_inner(sess, "RAW+MOVEMENT+CONTACT", 3, "B", 5) == "skipped (complete)"
    (d / "result.json").write_text("{}")                   # edited artifact -> not complete any more
    assert P4.run_status(d) == "incomplete"


def test_raw_through_the_p4_runner_equals_the_p3_runner(synth, tmp_path, monkeypatch):  # noqa: F811
    """Regression: the family-aware runner reproduces P3's RAW inner run bitwise (synthetic data)."""
    rows, split_dir = synth
    fd = fold_data(rows, 1, split_dir)
    monkeypatch.setattr(P3, "run_root", lambda: tmp_path / "p3")
    monkeypatch.setattr(P4, "run_root", lambda: tmp_path / "p4")
    monkeypatch.setattr(T, "config_grid", tiny_grid)
    monkeypatch.setattr(P4, "P4_FAMILIES", P4.P4_FAMILIES + ("RAW",))
    assert P3.run_inner(PassingSession(fd), 1, "A", 3) == "complete"
    assert P4.run_inner(PassingSession(fd), "RAW", 1, "A", 3) == "complete"
    d3, d4 = P3.inner_dir(1, "A", 3), P4.inner_dir("RAW", 1, "A", 3)
    r3, r4 = (json.loads((d / "result.json").read_text()) for d in (d3, d4))
    assert (r3["best_epoch"], r3["best_criterion"]) == (r4["best_epoch"], r4["best_criterion"])
    assert (d3 / "history.csv").read_text() == (d4 / "history.csv").read_text()
    s3, s4 = torch.load(d3 / "best_model.pt"), torch.load(d4 / "best_model.pt")
    assert all(torch.equal(s3[k], s4[k]) for k in s3)


def test_final_run_refuses_before_the_selection_is_committed(synth, tmp_path, monkeypatch):  # noqa: F811
    rows, split_dir = synth
    fd = fold_data(rows, 1, split_dir)
    monkeypatch.setattr(P4, "run_root", lambda: tmp_path / "runs")
    monkeypatch.setattr(P4, "selected_yaml", lambda: tmp_path / "missing.yaml")
    sess = FakeSession(fd)
    with pytest.raises(P4.SelectionNotFrozenError):
        P4.run_final(sess, "MOVEMENT", 1, 0)
    assert sess.gated == 0 and not (tmp_path / "runs").exists()           # nothing touched, no test access
    (tmp_path / "missing.yaml").write_text("x")                            # present but outside git
    monkeypatch.setattr(P4, "frozen_selection", lambda: {"families": {}})
    with pytest.raises(P4.SelectionNotFrozenError):
        P4.run_final(sess, "MOVEMENT", 1, 0)
    assert sess.gated == 0 and not (tmp_path / "runs").exists()
    with pytest.raises(P4.P4Error):
        P4.select_fold(sess, "MOVEMENT", 1)                                # inner runs incomplete -> refused


def test_selection_is_immutable_and_export_refuses_changes(synth, tmp_path, monkeypatch):  # noqa: F811
    rows, split_dir = synth
    fd = fold_data(rows, 1, split_dir)
    monkeypatch.setattr(P4, "run_root", lambda: tmp_path / "runs")
    monkeypatch.setattr(P4, "selected_yaml", lambda: tmp_path / "p4_selected_configs.yaml")
    monkeypatch.setattr(T, "config_grid", tiny_grid)
    tr = fd.labelled & (fd.partition == "train")
    sc = TargetScaler.fit(fd.targets[tr], scheme="loso", fold="1", partition="train", subjects=fd.train_subjects)
    monkeypatch.setattr(P4, "p3_outer_scaler", lambda f: {"mean": sc.mean.tolist(), "std": sc.std.tolist(),
                                                         "n": sc.fit_provenance["n"]})
    sess = FakeSession(fd)
    for inner in ("A", "B"):
        for k in range(16):
            d = P4.inner_dir("CONTACT", 1, inner, k)
            P4.begin_run(d, "r")
            (d / "result.json").write_text(json.dumps({"family": "CONTACT", "best_criterion": 1.0 + (k == 7) * -0.5,
                                                       "best_epoch": 3 if inner == "A" else 4}))
            P4.complete_run(d, ["result.json"])
    s = P4.select_fold(sess, "CONTACT", 1)
    assert s["selected_index"] == 7 and s["final_epochs"] == 4                 # half-up of 3.5
    assert s["outer_target_scaler"]["sha256"] == P4.scaler_digest(s["outer_target_scaler"])
    assert P4.select_fold(sess, "CONTACT", 1)["frozen_at"] == s["frozen_at"]   # unchanged on re-run
    with pytest.raises(P4.SelectionNotFrozenError):
        P4.export_selection()                                                  # other families not frozen
    monkeypatch.setattr(P4, "p3_outer_scaler", lambda f: {"mean": [0.0, 0.0], "std": [1.0, 1.0], "n": 1})
    P4.selection_path("CONTACT", 1).unlink()
    with pytest.raises(P4.P4Error):
        P4.select_fold(sess, "CONTACT", 1)                   # outer scaler must equal P3's for the same pool


# ------------------------------------------------------------------------------------------------------ analysis

SUBJ = ["User01", "User02", "User07"]


def fake_outer(values: dict[str, list[float]]) -> list[dict]:
    """Per family: subject MAEs; seeds get +-0.1 around it; RMSE = MAE + 1, bias = MAE / 2 (temperature only moves)."""
    out = []
    for fam, maes in values.items():
        for f, (s, m) in enumerate(zip(SUBJ, maes), start=1):
            for seed, eps in zip((0, 1, 2), (-0.1, 0.0, 0.1)):
                for t in ("temperature", "humidity"):
                    v = m + eps if t == "temperature" else 10.0
                    out.append({"family": fam, "fold": f, "held_out_subject": s, "seed": seed, "target": t,
                                "mae": v, "rmse": v + 1, "bias": v / 2, "n_windows": 100, "final_epochs": 3,
                                "source": "x"})
    return out


def fake_tm() -> list[dict]:
    return [{"fold": f, "held_out_subject": s, "target": t, "mae": 2.0 if t == "temperature" else 10.0,
             "rmse": 3.0 if t == "temperature" else 11.0, "bias": 1.0, "n_windows": 100}
            for f, s in enumerate(SUBJ, start=1) for t in ("temperature", "humidity")]


def test_comparison_tables_arithmetic():
    vals = {"RAW": [3.0, 5.0, 2.0], "MOVEMENT": [4.0, 6.0, 3.0], "CONTACT": [3.0, 5.0, 2.0],
            "RAW+MOVEMENT": [2.5, 5.5, 1.5], "RAW+CONTACT": [2.9, 4.0, 2.05], "RAW+MOVEMENT+CONTACT": [2.0, 5.0, 1.0]}
    t = P4.build_tables(fake_outer(vals), fake_tm(), SUBJ)
    a = next(r for r in t["incremental_effects"] if r["effect"] == "A" and r["target"] == "temperature"
             and r["metric"] == "mae")
    assert [a[f"delta_{s}"] for s in SUBJ] == pytest.approx([-0.5, 0.5, -0.5])
    assert a["improved_subjects"] == 2 and a["worse_subjects"] == 1
    assert a["delta_unweighted_mean"] == pytest.approx(-0.5 / 3)
    d = next(r for r in t["incremental_effects"] if r["effect"] == "D" and r["target"] == "temperature"
             and r["metric"] == "mae")
    assert [d[f"delta_{s}"] for s in SUBJ] == pytest.approx([-0.5, -0.5, -0.5]) and d["improved_subjects"] == 3
    h = next(r for r in t["vs_raw"] if r["family"] == "CONTACT" and r["target"] == "humidity" and r["metric"] == "mae")
    assert h["improved_subjects"] == 0 and h["worse_subjects"] == 0 and h["comparison_type"].startswith("standalone")
    tm = next(r for r in t["vs_training_mean"] if r["family"] == "RAW+MOVEMENT+CONTACT"
              and r["target"] == "temperature" and r["metric"] == "mae")
    assert [tm[f"delta_{s}"] for s in SUBJ] == pytest.approx([0.0, 3.0, -1.0]) and tm["improved_subjects"] == 1
    assert [tm[f"seeds_better_{s}"] for s in SUBJ] == [1, 0, 3] and tm["all_seeds_same_side"] is False
    sc = next(r for r in t["seed_consistency"] if r["effect"] == "B" and r["target"] == "temperature"
              and r["metric"] == "mae")
    assert sc["improved_fold_seeds"] == 6 and sc["n_fold_seeds"] == 9
    assert sc["min_delta"] == pytest.approx(-1.0) and sc["max_delta"] == pytest.approx(0.05)
    assert [sc[f"improved_seeds_{s}"] for s in SUBJ] == [3, 3, 0]
    summ = {r["model"]: r for r in t["family_summary"] if r["target"] == "temperature" and r["metric"] == "mae"}
    assert summ["RAW+MOVEMENT+CONTACT"]["rank_among_tcn_families"] == 1 and summ["MOVEMENT"][
        "rank_among_tcn_families"] == 6 and summ["training_mean"]["rank_among_tcn_families"] == ""
    off = next(r for r in t["bias_offset"] if r["model"] == "RAW" and r["subject_id"] == "User01"
               and r["target"] == "temperature")
    assert off["abs_bias_over_mae"] == pytest.approx(0.5)
    assert off["err_sd"] == pytest.approx(np.mean([np.sqrt((v + 1) ** 2 - (v / 2) ** 2) for v in (2.9, 3.0, 3.1)]))


def test_build_tables_refuses_missing_family_or_seed():
    vals = {f: [1.0, 1.0, 1.0] for f in P4.ALL_FAMILIES}
    rows = fake_outer(vals)
    with pytest.raises(P4.P4Error):
        P4.build_tables([r for r in rows if r["family"] != "CONTACT"], fake_tm(), SUBJ)
    with pytest.raises(P4.P4Error):
        P4.build_tables([r for r in rows if not (r["family"] == "RAW" and r["seed"] == 2)], fake_tm(), SUBJ)


def test_error_decomposition_is_exact():
    assert P4.err_sd(5.0, 3.0) == pytest.approx(4.0) and P4.err_sd(2.0, -2.0) == 0.0


def test_aggregate_end_to_end_on_synthetic_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(P4, "run_root", lambda: tmp_path / "runs")
    monkeypatch.setattr(P4, "metrics_dir", lambda: tmp_path / "metrics")
    rng = np.random.default_rng(5)
    n = 24
    folds = {1: "User01", 2: "User02", 3: "User07"}

    def prov(subject):
        dev = np.array(["22480", "22482"] * (n // 2)) if subject == "User02" else np.array(["unknown"] * n)
        cq = np.where(dev == "22482", np.array(["normal", "p1_response_shift", "p1_transition"] * (n // 3)), "normal")
        sp = np.array(["s1", "s2"] * (n // 2)) if subject == "User01" else np.array(["not_applicable"] * n)
        t0 = 1_780_000_000 + np.arange(n) * 20
        return {"subject_id": np.array([subject] * n), "device_id": dev, "session_id": np.array([f"{subject}|x|S1"] * n),
                "sensor_phase": sp, "channel_quality_phase": cq, "night_id": np.array(["2026-07-19", "2026-07-20"] * (n // 2)),
                "window_start": t0, "window_end": t0 + 40, "target_timestamp": t0 + 38}

    truth = {s: np.stack([rng.normal(27, 1, n), rng.normal(45, 5, n)], 1) for s in folds.values()}
    raw_rows, tm_rows = [], []
    for f, s in folds.items():
        y = truth[s]
        for t_i, t in enumerate(("temperature", "humidity")):
            tm_rows.append({"fold": f, "held_out_subject": s, "target": t, "mae": 2.0, "rmse": 2.5, "bias": 1.0,
                            "n_windows": n})
            for seed in (0, 1, 2):
                raw_rows.append({"family": "RAW", "fold": f, "held_out_subject": s, "seed": seed, "target": t,
                                 "mae": 1.0 + seed / 10, "rmse": 1.5, "bias": 0.5, "n_windows": n, "final_epochs": 3,
                                 "source": "p3_frozen"})
        for fam in P4.P4_FAMILIES:
            for seed in (0, 1, 2):
                d = P4.final_dir(fam, f, seed)
                P4.begin_run(d, "r")
                p = y + rng.normal(0, 1, y.shape)
                P3.write_metrics(d / "metrics.csv", "r", f, s, y, p)
                P3.write_predictions(d / "predictions.parquet", "r", P4.model_label(fam), f, seed, prov(s),
                                     np.ones(n, bool), y, p)
                P4.complete_run(d, ["metrics.csv", "predictions.parquet"])
            sp = P4.selection_path(fam, f)
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps({"held_out_subject": s, "selected_index": 0, "grid": [{"config_index": 0}],
                                      "selected_config": {"channels": 32}, "selection_score": 1.0, "final_epochs": 3,
                                      "n_inputs": len(family_features(fam)),
                                      "inner": {"A": {"criterion": 1.0, "best_epoch": 3},
                                                "B": {"criterion": 1.0, "best_epoch": 3}}}))
    monkeypatch.setattr(P4, "p3_reference", lambda: {"outer": raw_rows, "training_mean": tm_rows, "strata": [],
                                                     "selected": [], "files_sha256": {"x": "y"}})
    monkeypatch.setattr(P4, "frozen_selection", lambda: {"families": {
        fam: {"folds": {f: {"final_epochs": 3} for f in folds}} for fam in P4.P4_FAMILIES}})
    t = P4.aggregate()
    assert len([r for r in t["outer_by_seed"] if r["source"] == "p4"]) == 5 * 3 * 3 * 2
    assert {r["model"] for r in t["family_summary"]} == {"training_mean", *P4.ALL_FAMILIES}
    kinds = {(r["subject_id"], r["stratum_type"]) for r in t["secondary_strata"] if r.get("seed") == "mean"}
    assert {("User01", "sensor_phase"), ("User02", "device"), ("User02", "device_x_channel_quality_phase")} <= kinds
    assert len(t["seed_consistency"]) == 7 * 2 * 2 and len(t["incremental_effects"]) == 5 * 2 * 2
    out = P4.write_tables(t)
    for name in ("inner_search", "selected_configs", "outer_by_seed", "outer_by_fold", "family_summary", "vs_raw",
                 "vs_training_mean", "incremental_effects", "secondary_strata", "seed_consistency"):
        assert (out / f"p4_{name}.csv").exists(), name


def test_p3_reference_files_are_unchanged_since_the_p3_tag():
    if P4._git("rev-parse", "-q", "--verify", f"refs/tags/{P4.P3_TAG}").returncode != 0:
        pytest.skip("p3-loso-baseline tag not available in this checkout")
    P4.p3_reference_unchanged()


def test_frozen_p3_reference_reproduces_the_committed_p3_summary():
    ref = P4.p3_reference(verify_tag=False)
    assert {r["family"] for r in ref["outer"]} == {"RAW"} and len(ref["outer"]) == 18
    assert {(r["seed"]) for r in ref["outer"]} == {0, 1, 2} and len(ref["training_mean"]) == 6
    assert {r["model"] for r in ref["strata"]} == {"RAW", "training_mean"}
    assert set(ref["files_sha256"]) == set(P4.P3_REFERENCE_FILES)
