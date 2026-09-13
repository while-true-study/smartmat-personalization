"""P3 strict LOSO pipeline (synthetic data only; no study data, no model result)."""
from __future__ import annotations

import json

import numpy as np
import pytest
import torch

from src.evaluation import metrics as M
from src.evaluation import p3_loso as P
from src.evaluation import splits as S
from src.evaluation.leakage import LeakageGateError, RunContext, run_gate
from src.evaluation.protocol import load_protocol, protocol_sha256
from src.features.pressure_features import RAW_FEATURES, TargetScaler
from src.models.tcn import TCN, to_channels_first
from src.training import trainer as T
from src.training.loso_data import Rows, fold_data
from tests.test_splits import build, synthetic


# ------------------------------------------------------------------------------------------------ model

def test_tcn_shapes_and_residual_projection():
    m = TCN(6, 32, 3, 0.1)
    x = torch.rand(5, 8, 6)
    assert m(to_channels_first(x)).shape == (5, 2)
    assert isinstance(m.blocks[0].residual, torch.nn.Conv1d) and m.blocks[0].residual.in_channels == 6
    assert isinstance(m.blocks[1].residual, torch.nn.Identity)
    assert [b.main[0].conv.dilation[0] for b in m.blocks] == [1, 2, 4]
    assert m.receptive_field() >= 8 and TCN(6, 32, 2).receptive_field() == 15


def test_tcn_is_causal():
    torch.manual_seed(0)
    m = TCN(6, 16, 3, 0.0).eval()
    x = torch.rand(2, 6, 8)
    y = x.clone()
    y[:, :, 5:] += 1.0                                     # change only the future of step 4
    with torch.no_grad():
        hx, hy = m.blocks(x), m.blocks(y)
    assert torch.allclose(hx[:, :, :5], hy[:, :, :5]) and not torch.allclose(hx[:, :, 5:], hy[:, :, 5:])


# ------------------------------------------------------------------------------------------- scaling/metrics

def test_training_mean_baseline_and_metrics():
    y_tr = np.array([[20.0, 40.0], [22.0, 60.0]])
    mean = P.training_mean(y_tr)
    assert mean.tolist() == [21.0, 50.0]
    y_te = np.array([[23.0, 45.0], [19.0, 55.0]])
    pred = P.training_mean_predict(mean, 2)
    m = M.target_metrics(y_te, pred)
    assert m["temperature"]["mae"] == 2.0 and m["humidity"]["mae"] == 5.0
    assert m["temperature"]["rmse"] == 2.0 and m["temperature"]["bias"] == 0.0
    assert M.bias(np.array([1.0]), np.array([3.0])) == 2.0                 # pred - true
    with pytest.raises(P.P3Error):
        P.training_mean(np.array([[np.nan, 1.0]]))


def test_selection_criterion_is_unit_free():
    y = np.array([[20.0, 40.0], [22.0, 60.0]])
    p = y + np.array([1.0, 10.0])
    assert M.selection_criterion(y, p, np.array([1.0, 10.0])) == pytest.approx(1.0)
    assert M.unweighted_subject_mean({"User01": 1.0, "User02": 2.0, "User07": 6.0}) == 3.0
    with pytest.raises(ValueError):
        M.unweighted_subject_mean({"User02/22480": 1.0, "User02/22482": 2.0, "User01": 1, "User07": 1})


def test_target_scaler_inverse_and_training_only_provenance():
    y = np.array([[20.0, 40.0], [24.0, 60.0], [22.0, 50.0]])
    sc = TargetScaler.fit(y, scheme="loso", fold="1", partition="inner_train", subjects=["User02"])
    assert np.allclose(sc.inverse(sc.transform(y)), y)
    assert sc.fit_provenance == {"transform": "target_zscore", "scheme": "loso", "fold": "1",
                                 "partition": "inner_train", "subjects": ["User02"], "nights": None, "n": 3}


# ----------------------------------------------------------------------------------------- grid / selection

def test_config_grid_is_the_frozen_16_in_declared_order():
    grid = T.config_grid(load_protocol())
    assert len(grid) == 16
    assert (grid[0].channels, grid[0].kernel_size, grid[0].dropout, grid[0].lr) == (32, 2, 0.1, 0.001)
    assert (grid[1].lr, grid[2].dropout, grid[4].kernel_size, grid[8].channels) == (0.0003, 0.3, 3, 64)
    assert {(g.weight_decay, g.batch_size, g.max_epochs, g.early_stopping_patience) for g in grid} == \
        {(0.0001, 256, 50, 5)}


def test_selection_tie_breaks_in_grid_order():
    scores = [(0.5, 0.7), (0.4, 0.6), (0.6, 0.4), (0.9, 0.1)]   # means 0.6, 0.5, 0.5, 0.5
    assert P.select_config(scores) == 1


def test_best_epoch_and_final_epoch_rules():
    assert T.best_epoch_of([5, 4, 3, 3.5, 3, 4, 4, 4, 4, 9], patience=5, max_epochs=50) == (3, 8)
    assert T.best_epoch_of([1.0] * 3, patience=5, max_epochs=50) == (1, 3)
    assert T.best_epoch_of(list(np.linspace(1, 0, 60)), patience=5, max_epochs=50) == (50, 50)
    assert P.final_epochs(7, 8) == 8 and P.final_epochs(6, 7) == 7 and P.final_epochs(10, 10) == 10
    assert M.round_half_up(2.5) == 3 and M.round_half_up(3.5) == 4                # not banker's rounding


def test_p3_trains_raw_only_with_frozen_seeds():
    assert P.assert_p3_family("RAW") == RAW_FEATURES
    for fam in ("MOVEMENT", "CONTACT", "RAW+MOVEMENT", "RAW+CONTACT", "RAW+MOVEMENT+CONTACT"):
        with pytest.raises(P.P3Error):
            P.assert_p3_family(fam)
    assert load_protocol()["models"]["seeds"] == [0, 1, 2]
    assert load_protocol()["models"]["selection"]["seed_for_selection"] == 0


# ------------------------------------------------------------------------------------------------ fold data

def synthetic_rows():
    arr = synthetic()
    order = np.lexsort((arr["ts"], np.char.add(arr["subject"].astype(str), arr["device"].astype(str))))
    arr = {k: v[order] for k, v in arr.items()}
    n = arr["ts"].size
    rng = np.random.default_rng(0)
    rows = Rows(arr["subject"].astype(str), arr["device"].astype(str), arr["session"].astype(str),
                arr["sp"].astype(str), arr["cq"].astype(str), arr["ts"].astype(np.int64),
                rng.integers(0, 4096, (n, 6)).astype(np.int16), rng.normal(25, 2, (n, 2)),
                np.ones(n, bool), np.ones(n, bool))
    return arr, rows


@pytest.fixture()
def synth(tmp_path):
    arr, rows = synthetic_rows()
    _, _, tables = build(arr)
    for rel, (r, cols) in tables.items():
        S.write_split(tmp_path / rel, r, cols)
    return rows, tmp_path


def test_fold_assignment_follows_committed_split_files(synth):
    rows, split_dir = synth
    for fold, held in {1: "User01", 2: "User02", 3: "User07"}.items():
        fd = fold_data(rows, fold, split_dir)
        assert fd.held_out == held
        assert set(fd.prov["subject_id"][fd.partition == "test"]) == {held}
        assert held not in set(fd.prov["subject_id"][fd.partition == "train"])
        for inner in ("A", "B"):
            assert np.all(fd.inner[inner][fd.partition == "test"] == "")
            assert held not in set(fd.prov["subject_id"][fd.inner[inner] != ""])
    fd2 = fold_data(rows, 2, split_dir)
    test_dev = set(fd2.prov["device_id"][fd2.partition == "test"])
    assert test_dev == {"22480", "22482"}                                    # both User02 mats held out together


def test_fold_windows_keep_4095_and_boundaries(synth):
    rows, split_dir = synth
    rows.pressure[:50] = 4095
    fd = fold_data(rows, 1, split_dir)
    assert fd.pressure.max() == 4095 and fd.pressure.shape[1:] == (8, 6)
    for first, last in fd.window_groups(np.ones(len(fd.labelled), bool)):
        assert first == last


def test_labelled_requires_both_targets(synth):
    rows, split_dir = synth
    rows.temp_ok[:] = True
    fd_all = fold_data(rows, 3, split_dir)
    rows.humid_ok[::2] = False
    fd = fold_data(rows, 3, split_dir)
    assert fd.labelled.sum() < fd_all.labelled.sum()


# ------------------------------------------------------------------------------------------- run bookkeeping

def test_incomplete_run_is_not_treated_as_complete(tmp_path):
    d = tmp_path / "run"
    assert P.run_status(d) == "absent"
    P.begin_run(d, "r1")
    assert P.run_status(d) == "running"
    (d / "a.txt").write_text("x")
    P.complete_run(d, ["a.txt"])
    assert P.run_status(d) == "complete"
    (d / "a.txt").write_text("changed")                                      # artifact edited after completion
    assert P.run_status(d) == "incomplete"
    (d / "a.txt").unlink()
    assert P.run_status(d) == "incomplete"
    d.mkdir(exist_ok=True)
    assert P.run_status(tmp_path / "empty_dir_only") == "absent"


def test_resume_counts_attempts_and_keeps_history(tmp_path):
    d = tmp_path / "run"
    P.begin_run(d, "r1")
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        P.fail_run(d, exc)
    assert P.run_status(d) == "failed"
    assert P.begin_run(d, "r2") == 2
    st = json.loads((d / "status.json").read_text())
    assert st["history"][0]["status"] == "failed" and "boom" in st["history"][0]["error"]


def test_prediction_provenance_is_complete(tmp_path):
    prov = {"subject_id": np.array(["User02", "User02"]), "device_id": np.array(["22480", "22482"]),
            "session_id": np.array(["User02|22480|S0001", "User02|22482|S0001"]),
            "sensor_phase": np.array(["not_applicable"] * 2), "channel_quality_phase": np.array(["normal"] * 2),
            "night_id": np.array(["2026-07-19"] * 2), "window_start": np.array([1_780_000_000, 1_780_000_020]),
            "window_end": np.array([1_780_000_040, 1_780_000_060]),
            "target_timestamp": np.array([1_780_000_038, 1_780_000_058])}
    y, p = np.array([[29.0, 50.0], [32.0, 66.0]]), np.array([[28.0, 55.0], [30.0, 60.0]])
    P.write_predictions(tmp_path / "pred.parquet", "rid", "tcn_raw", 2, 1, prov, np.ones(2, bool), y, p)
    pr = P.read_predictions(tmp_path / "pred.parquet")
    want = {"run_id", "model", "fold", "seed", "subject_id", "device_id", "session_id", "sensor_phase",
            "channel_quality_phase", "night_id", "window_start", "window_end", "target_timestamp", "target",
            "y_true", "y_pred"}
    assert set(pr) == want and len(pr["y_true"]) == 4
    y2, p2, prov2 = P._pairs(pr)
    assert np.array_equal(y2, y) and np.array_equal(p2, p) and list(prov2["device_id"]) == ["22480", "22482"]
    rows = P.strata_rows("tcn_raw", 2, 1, "User02", y, p, prov)
    assert {r["stratum"] for r in rows if r["stratum_type"] == "device"} == {"22480", "22482"}


def test_run_metadata_has_required_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "load_manifest", lambda: {"files": {"f.csv": {"sha256": "s" * 64}},
                                                     "protocol_sha256": protocol_sha256()})
    verified = {"dataset_version": "canonical_v1", "content_sha256": {"primary": "c" * 64},
                "files": {"primary": "f" * 64}}
    meta = P._meta(tmp_path, "rid", "final", 1, "User01", 0, {"channels": 32}, verified, {})
    for k in ("run_id", "protocol_version", "git_commit", "git_dirty_tracked_files", "p2_tag", "p2_tag_commit",
              "canonical_primary_content_sha256", "split_sha256", "protocol_sha256", "seed", "fold",
              "held_out_subject", "config", "python", "torch", "cuda_version", "device", "started_at",
              "deterministic_algorithms"):
        assert k in meta, k
    assert json.loads((tmp_path / "run_meta.json").read_text())["run_id"] == "rid"


# --------------------------------------------------------------------------------- gate / one look at test

class FakeSession(P.P3Session):
    def __init__(self, fd, gate_exc=None):
        super().__init__(echo=False)
        self._fd, self._gate_exc, self.gated = fd, gate_exc, 0

    def fold(self, fold):
        return self._fd

    def gate(self, d, ctx):
        self.gated += 1
        if self._gate_exc:
            raise self._gate_exc
        return None, {"dataset_version": "canonical_v1", "content_sha256": {"primary": "c" * 64},
                      "files": {"primary": "f" * 64}}


def test_leakage_gate_runs_before_the_trainer_and_fails_closed(synth, tmp_path, monkeypatch):
    rows, split_dir = synth
    fd = fold_data(rows, 1, split_dir)
    monkeypatch.setattr(P, "run_root", lambda: tmp_path / "runs")
    calls = []
    monkeypatch.setattr(T, "train_tcn", lambda *a, **k: calls.append(1))
    sess = FakeSession(fd, LeakageGateError("blocked"))
    with pytest.raises(LeakageGateError):
        P.run_inner(sess, 1, "A", 0)
    assert sess.gated == 1 and calls == []
    d = P.inner_dir(1, "A", 0)
    assert P.run_status(d) == "failed" and not (d / "best_model.pt").exists()


def test_inner_context_passes_gate_and_held_out_selection_fails(synth):
    rows, split_dir = synth
    arr, _ = synthetic_rows()
    sessions, pieces, _ = build(arr)
    fd = fold_data(rows, 1, split_dir)
    man = {"protocol_version": "v1.0", "protocol_sha256": protocol_sha256(),
           "files": {rel: {"sha256": S.file_sha256_lf(split_dir / rel)} for rel in S.SPLIT_FILES},
           "canonical": {"dataset_version": "canonical_v1", "primary_content_sha256": "c" * 64,
                         "primary_file_sha256": "f" * 64}}
    canon = {"dataset_version": "canonical_v1", "content_sha256": {"primary": "c" * 64},
             "files": {"primary": "f" * 64}}
    tr = fd.labelled & (fd.inner["A"] == "inner_train")
    ok = RunContext("loso", fold=1, input_features=list(RAW_FEATURES),
                    fit_records=[{"transform": "target_zscore", "partition": "inner_train", "subjects": ["User02"]}],
                    selection_subjects=["User07"], window_groups=fd.window_groups(tr, "A"))
    rep = run_gate(split_dir, man, load_protocol(), sessions, pieces, ok, canon)
    assert rep.passed, rep.failures()
    bad = RunContext("loso", fold=1, input_features=list(RAW_FEATURES), fit_records=ok.fit_records,
                     selection_subjects=["User01"], window_groups=ok.window_groups)
    assert not run_gate(split_dir, man, load_protocol(), sessions, pieces, bad, canon).passed


def test_outer_test_cannot_run_before_selection_is_frozen(synth, tmp_path, monkeypatch):
    rows, split_dir = synth
    fd = fold_data(rows, 1, split_dir)
    monkeypatch.setattr(P, "run_root", lambda: tmp_path / "runs")
    monkeypatch.setattr(P, "selected_yaml", lambda: tmp_path / "missing.yaml")
    sess = FakeSession(fd)
    with pytest.raises(P.SelectionNotFrozenError):
        P.run_final(sess, 1, 0)
    assert sess.gated == 0 and not (tmp_path / "runs").exists()               # nothing touched, no test access
    with pytest.raises(P.P3Error):
        P.select_fold(sess, 1)                                                # inner runs incomplete -> refused


def test_lean_structure_equals_p2_structure_and_keys_are_equivalent():
    from src.evaluation.windowing import build_windows, group_key
    from src.evaluation.protocol import window_spec
    from src.training.loso_data import coded_key, structure_records
    arr = synthetic(cross_noon_night=3)
    order = np.lexsort((arr["ts"], np.char.add(arr["subject"].astype(str), arr["device"].astype(str))))
    arr = {k: v[order] for k, v in arr.items()}
    n = arr["ts"].size
    rows = Rows(arr["subject"].astype(str), arr["device"].astype(str), arr["session"].astype(str),
                arr["sp"].astype(str), arr["cq"].astype(str), arr["ts"].astype(np.int64),
                np.zeros((n, 6), np.int16), np.zeros((n, 2)), np.ones(n, bool), np.ones(n, bool))
    sessions, pieces = structure_records(rows)
    p2_sessions = S.session_records(rows.ts, rows.subject, rows.device, rows.session, rows.sensor_phase,
                                    rows.cq_phase)
    p2_pieces = S.piece_records(rows.ts, rows.subject, rows.device, rows.session, rows.sensor_phase, rows.cq_phase,
                                rows.night)
    assert sessions == p2_sessions and pieces == p2_pieces
    labels = (rows.subject, rows.device, rows.session, rows.sensor_phase)
    w_new = build_windows(rows.ts, coded_key(*labels), window_spec())
    w_old = build_windows(rows.ts, group_key(*labels), window_spec())
    assert np.array_equal(w_new.step_rows, w_old.step_rows) and np.array_equal(w_new.t0, w_old.t0)
