"""P3 strict LOSO baseline under frozen protocol v1.0 (docs/EXPERIMENT_PROTOCOL.md §4–§12; D-031, D-040, D-041).

Order enforced by the code:
1. training-mean baseline per outer fold;
2. RAW-TCN inner search: 3 folds x 16 configurations x 2 inner splits (seed 0), early stopping on inner validation;
3. per-fold selection frozen to `outputs/runs/p3/selection/fold<k>.json` and, for all folds, to the committed
   `configs/experiments/v1.0/p3_selected_configs.yaml` (selected config, final epochs, outer scaler statistics);
4. only then final outer models (3 folds x seeds 0/1/2, fixed epochs, whole outer training pool), each followed by
   the single outer-test evaluation of that model.
Every run calls the leakage gate first (fail closed) and writes config.yaml, run_meta.json, leakage_check.json,
metrics, history and status.json. A run counts as complete only if status.json says so AND every listed artifact
still has its recorded SHA-256. P3 trains the RAW family only.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np
import pyarrow as pa
import yaml

from src.data import paths
from src.data.io_guard import open_for_write, write_csv, write_json, write_parquet, write_text
from src.evaluation import splits as S
from src.evaluation.canonical_input import verify_canonical
from src.evaluation.leakage import GateReport, RunContext, require_pass, run_gate
from src.evaluation.metrics import TARGETS, round_half_up, target_metrics, unweighted_subject_mean
from src.evaluation.p2_protocol import canonical_structure, load_manifest, split_root
from src.evaluation.protocol import PROTOCOL_VERSION, load_protocol, protocol_sha256
from src.features.pressure_features import RAW_FEATURES, TargetScaler, family_features

P3_FAMILY = "RAW"
INNER_SPLITS = ("A", "B")
FREEZE_TAG = "p2-protocol-freeze"


class P3Error(RuntimeError):
    pass


class SelectionNotFrozenError(P3Error):
    """Raised when an outer-test step is attempted before every fold's selection is frozen."""


def assert_p3_family(family: str) -> tuple[str, ...]:
    if family != P3_FAMILY:
        raise P3Error(f"P3 trains the RAW family only (got {family!r}); other families are P4")
    feats = family_features(family)
    if tuple(feats) != RAW_FEATURES:
        raise P3Error("RAW feature list differs from the frozen definition")
    return feats


# ---------------------------------------------------------------------------------------------------------- paths

def run_root() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "runs" / "p3"


def metrics_dir() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "metrics" / "p3"


def selected_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / PROTOCOL_VERSION / "p3_selected_configs.yaml"


def training_mean_dir(fold: int) -> Path:
    return run_root() / "training_mean" / f"fold{fold}"


def inner_dir(fold: int, inner: str, k: int) -> Path:
    return run_root() / "inner" / f"fold{fold}_{inner}_cfg{k:02d}"


def selection_path(fold: int) -> Path:
    return run_root() / "selection" / f"fold{fold}.json"


def final_dir(fold: int, seed: int) -> Path:
    return run_root() / "final" / f"fold{fold}_seed{seed}"


# ------------------------------------------------------------------------------------------------- run status

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run_status(d: Path) -> str:
    """'complete' only if status.json says so and every recorded artifact still matches its SHA-256."""
    st = d / "status.json"
    if not st.exists():
        return "absent"
    try:
        rec = json.loads(st.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "incomplete"
    if rec.get("status") != "complete" or not rec.get("files"):
        return rec.get("status", "incomplete") if rec.get("status") in ("running", "failed") else "incomplete"
    for name, sha in rec["files"].items():
        p = d / name
        if not p.exists() or sha256_file(p) != sha:
            return "incomplete"
    return "complete"


def _status(d: Path) -> dict:
    try:
        return json.loads((d / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def begin_run(d: Path, run_id: str) -> int:
    prev = _status(d)
    attempt = int(prev.get("attempt", 0)) + 1
    history = prev.get("history", [])
    if prev:
        history.append({k: prev.get(k) for k in ("attempt", "status", "started_at", "error")})
    write_json(d / "status.json", {"run_id": run_id, "status": "running", "attempt": attempt,
                                   "started_at": now(), "history": history})
    return attempt


def complete_run(d: Path, files: list[str]) -> None:
    rec = _status(d)
    rec.update(status="complete", finished_at=now(), files={f: sha256_file(d / f) for f in files})
    write_json(d / "status.json", rec)


def fail_run(d: Path, exc: BaseException) -> None:
    rec = _status(d)
    rec.update(status="failed", finished_at=now(), error=f"{type(exc).__name__}: {exc}",
               traceback=traceback.format_exc())
    write_json(d / "status.json", rec)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RunLog:
    def __init__(self, d: Path, echo: bool = True):
        self.path, self.echo = d / "train.log", echo

    def __call__(self, msg: str) -> None:
        with open_for_write(self.path, "a") as fh:
            fh.write(f"{now()} {msg}\n")
        if self.echo:
            print(msg, flush=True)


# -------------------------------------------------------------------------------------------------- provenance

def git_state() -> dict:
    run = lambda *a: subprocess.run(["git", *a], cwd=paths.PROJECT_ROOT, capture_output=True, text=True,  # noqa: E731
                                    encoding="utf-8")
    head = run("rev-parse", "HEAD").stdout.strip() or None
    dirty = bool(run("status", "--porcelain", "--untracked-files=no").stdout.strip())
    tag = run("rev-list", "-n", "1", FREEZE_TAG).stdout.strip() or None
    return {"git_commit": head, "git_dirty_tracked_files": dirty, "p2_tag": FREEZE_TAG, "p2_tag_commit": tag}


def frozen_inputs(verified: dict | None = None) -> dict:
    verified = verify_canonical() if verified is None else verified
    man = load_manifest()
    return {"protocol_version": PROTOCOL_VERSION, "protocol_sha256": protocol_sha256(),
            "split_sha256": {k: v["sha256"] for k, v in man["files"].items()},
            "split_manifest_protocol_sha256": man["protocol_sha256"],
            "canonical_dataset_version": verified["dataset_version"],
            "canonical_primary_content_sha256": verified["content_sha256"]["primary"],
            "canonical_primary_file_sha256": verified["files"]["primary"]}


# ------------------------------------------------------------------------------------------------ gate + data

class P3Session:
    """Per-process cache of canonical rows, fold windows and the canonical split structure for the gate."""

    def __init__(self, echo: bool = True):
        self.echo = echo
        self._rows = None
        self._folds: dict[int, object] = {}
        self._structure = None

    def rows(self):
        if self._rows is None:
            from src.training.loso_data import load_rows
            self._rows = load_rows()
        return self._rows

    def fold(self, fold: int):
        if fold not in self._folds:
            from src.training.loso_data import fold_data
            self._folds[fold] = fold_data(self.rows(), fold)
        return self._folds[fold]

    def gate(self, d: Path, ctx: RunContext) -> tuple[GateReport, dict]:
        """Run the frozen P2 gate for this run (canonical re-verified every time); write the report; fail closed."""
        if self._structure is None:
            self._structure = canonical_structure()
        verified = verify_canonical()
        rep = run_gate(split_root(), load_manifest(), load_protocol(), *self._structure, ctx, verified)
        write_json(d / "leakage_check.json", {"checked_at": now(), "context": {
            "scheme": ctx.scheme, "fold": ctx.fold, "input_features": ctx.input_features,
            "fit_records": ctx.fit_records, "selection_subjects": ctx.selection_subjects,
            "n_window_group_pairs": len(ctx.window_groups)}, **rep.to_dict()})
        require_pass(rep)
        return rep, verified


def _meta(d: Path, run_id: str, kind: str, fold: int, held_out: str, seed: int | None, config: dict | None,
          verified: dict, extra: dict) -> dict:
    from src.training.trainer import environment
    meta = {"run_id": run_id, "kind": kind, "fold": fold, "held_out_subject": held_out, "seed": seed,
            "family": P3_FAMILY, "config": config, **frozen_inputs(verified), **git_state(), **environment(),
            "started_at": now(), **extra}
    write_json(d / "run_meta.json", meta)
    return meta


def _finish_meta(d: Path, **extra) -> None:
    meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
    meta.update(finished_at=now(), **extra)
    write_json(d / "run_meta.json", meta)


def _run_id(name: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{name}"


# ------------------------------------------------------------------------------------------ predictions / metrics

PRED_SCHEMA = pa.schema([
    ("run_id", pa.string()), ("model", pa.string()), ("fold", pa.int8()), ("seed", pa.int16()),
    ("subject_id", pa.string()), ("device_id", pa.string()), ("session_id", pa.string()),
    ("sensor_phase", pa.string()), ("channel_quality_phase", pa.string()), ("night_id", pa.string()),
    ("window_start", pa.timestamp("s")), ("window_end", pa.timestamp("s")), ("target_timestamp", pa.timestamp("s")),
    ("target", pa.string()), ("y_true", pa.float64()), ("y_pred", pa.float64())])


def write_predictions(path: Path, run_id: str, model: str, fold: int, seed: int, prov: dict, mask: np.ndarray,
                      y_true: np.ndarray, y_pred: np.ndarray) -> None:
    n = int(mask.sum())
    cols = {}
    for c in ("subject_id", "device_id", "session_id", "sensor_phase", "channel_quality_phase", "night_id"):
        cols[c] = np.tile(prov[c][mask].astype(str), 2)
    for c in ("window_start", "window_end", "target_timestamp"):
        cols[c] = np.tile(prov[c][mask].astype("datetime64[s]"), 2)
    table = pa.table({
        "run_id": pa.array([run_id] * 2 * n), "model": pa.array([model] * 2 * n),
        "fold": pa.array(np.full(2 * n, fold, np.int8)), "seed": pa.array(np.full(2 * n, seed, np.int16)),
        **{c: pa.array(cols[c]) for c in ("subject_id", "device_id", "session_id", "sensor_phase",
                                          "channel_quality_phase", "night_id")},
        **{c: pa.array(cols[c], pa.timestamp("s")) for c in ("window_start", "window_end", "target_timestamp")},
        "target": pa.array(np.repeat(np.array(TARGETS), n)),
        "y_true": pa.array(np.concatenate([y_true[:, 0], y_true[:, 1]])),
        "y_pred": pa.array(np.concatenate([y_pred[:, 0], y_pred[:, 1]]))}, schema=PRED_SCHEMA)
    write_parquet(path, [table], PRED_SCHEMA)


def write_metrics(path: Path, run_id: str, fold: int, subject: str, y: np.ndarray, p: np.ndarray) -> dict:
    m = target_metrics(y, p)
    rows = [{"run_id": run_id, "fold": fold, "subject_id": subject, "target": t, "metric": k, "value": v,
             "n_windows": int(y.shape[0])} for t, d in m.items() for k, v in d.items()]
    write_csv(path, rows, ["run_id", "fold", "subject_id", "target", "metric", "value", "n_windows"])
    return m


def log_outer_access(fold: int, seed: int | None, model: str, run_id: str, selection_sha: str | None) -> None:
    with open_for_write(run_root() / "outer_test_access.jsonl", "a") as fh:
        fh.write(json.dumps({"at": now(), "fold": fold, "seed": seed, "model": model, "run_id": run_id,
                             "selection_sha256": selection_sha}) + "\n")


# ------------------------------------------------------------------------------------------- training-mean baseline

def training_mean(y_train: np.ndarray) -> np.ndarray:
    """Per-target mean over the labelled windows of the outer training pool (deterministic)."""
    y = np.asarray(y_train, np.float64)
    if y.ndim != 2 or y.shape[1] != 2 or y.shape[0] == 0 or not np.all(np.isfinite(y)):
        raise P3Error("training targets must be a finite, non-empty (n, 2) array")
    return y.mean(axis=0)


def training_mean_predict(mean: np.ndarray, n: int) -> np.ndarray:
    return np.tile(np.asarray(mean, np.float64), (n, 1))


def run_training_mean(sess: P3Session, fold: int, force_log: Callable[[str], None] | None = None) -> str:
    d = training_mean_dir(fold)
    if run_status(d) == "complete":
        return "skipped (complete)"
    run_id = _run_id(f"p3-training-mean-fold{fold}")
    begin_run(d, run_id)
    log = force_log or RunLog(d, sess.echo)
    try:
        fd = sess.fold(fold)
        tr = fd.labelled & (fd.partition == "train")
        te = fd.labelled & (fd.partition == "test")
        plan = {"transform": "training_mean", "partition": "train", "subjects": fd.train_subjects}
        # The gate needs a declared window input schema; P3 windows carry RAW inputs, which this baseline ignores.
        ctx = RunContext("loso", fold=fold, input_features=list(RAW_FEATURES), fit_records=[plan],
                         selection_subjects=[], window_groups=fd.window_groups(tr | te))
        _, verified = sess.gate(d, ctx)
        _meta(d, run_id, "training_mean", fold, fd.held_out, None, None, verified,
              {"inputs_used": [], "train_subjects": fd.train_subjects, "n_train_windows": int(tr.sum()),
               "n_test_windows": int(te.sum())})
        mean = training_mean(fd.targets[tr])
        write_text(d / "config.yaml", yaml.safe_dump({"model": "training_mean", "fold": fold,
                                                      "held_out_subject": fd.held_out,
                                                      "train_subjects": fd.train_subjects,
                                                      "train_mean": {"temperature": float(mean[0]),
                                                                     "humidity": float(mean[1])}},
                                                     sort_keys=False))
        log_outer_access(fold, None, "training_mean", run_id, None)
        pred = training_mean_predict(mean, int(te.sum()))
        m = write_metrics(d / "metrics.csv", run_id, fold, fd.held_out, fd.targets[te], pred)
        write_predictions(d / "predictions.parquet", run_id, "training_mean", fold, -1, fd.prov, te,
                          fd.targets[te], pred)
        _finish_meta(d, train_mean=mean.tolist(), outer_test_metrics=m)
        log(f"fold {fold} training-mean: {json.dumps(m)}")
        complete_run(d, ["config.yaml", "run_meta.json", "leakage_check.json", "metrics.csv", "predictions.parquet"])
        return "complete"
    except BaseException as exc:
        fail_run(d, exc)
        raise


# ---------------------------------------------------------------------------------------------------- inner search

def inner_subjects(fd, inner: str) -> tuple[str, str]:
    tr = sorted(set(fd.prov["subject_id"][fd.inner[inner] == "inner_train"]))
    va = sorted(set(fd.prov["subject_id"][fd.inner[inner] == "inner_val"]))
    if len(tr) != 1 or len(va) != 1 or tr == va or fd.held_out in tr + va:
        raise P3Error(f"fold {fd.fold} inner {inner}: not a two-subject split of the training pool")
    return tr[0], va[0]


def run_inner(sess: P3Session, fold: int, inner: str, k: int) -> str:
    import torch
    from src.training.trainer import config_grid, train_tcn

    d = inner_dir(fold, inner, k)
    if run_status(d) == "complete":
        return "skipped (complete)"
    feats = assert_p3_family(P3_FAMILY)
    cfg = config_grid(load_protocol())[k]
    seed = int(load_protocol()["models"]["selection"]["seed_for_selection"])
    run_id = _run_id(f"p3-inner-fold{fold}{inner}-cfg{k:02d}")
    begin_run(d, run_id)
    log = RunLog(d, sess.echo)
    try:
        fd = sess.fold(fold)
        train_subj, val_subj = inner_subjects(fd, inner)
        tr = fd.labelled & (fd.inner[inner] == "inner_train")
        va = fd.labelled & (fd.inner[inner] == "inner_val")
        plan = {"transform": "target_zscore", "partition": "inner_train", "subjects": [train_subj]}
        ctx = RunContext("loso", fold=fold, input_features=list(feats), fit_records=[plan],
                         selection_subjects=[val_subj], window_groups=fd.window_groups(tr | va, inner))
        _, verified = sess.gate(d, ctx)
        scaler = TargetScaler.fit(fd.targets[tr], scheme="loso", fold=str(fold), partition="inner_train",
                                  subjects=[train_subj])
        if scaler.fit_provenance["subjects"] != plan["subjects"]:
            raise P3Error("scaler provenance differs from the gated plan")
        _meta(d, run_id, "inner", fold, fd.held_out, seed, cfg.as_dict(), verified,
              {"inner_split": inner, "config_index": k, "inner_train_subject": train_subj,
               "inner_val_subject": val_subj, "n_train_windows": int(tr.sum()), "n_val_windows": int(va.sum()),
               "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance}})
        write_text(d / "config.yaml", yaml.safe_dump({"family": P3_FAMILY, "config_index": k, **cfg.as_dict(),
                                                      "seed": seed, "fold": fold, "inner_split": inner},
                                                     sort_keys=False))
        res = train_tcn(cfg, fd.pressure[tr], fd.targets[tr], scaler, seed, pressure_va=fd.pressure[va],
                        y_va=fd.targets[va], log=log)
        write_csv(d / "history.csv", res.history, list(res.history[0]))
        with open_for_write(d / "best_model.pt", "wb") as fh:
            torch.save(res.model.state_dict(), fh)
        best = res.history[res.best_epoch - 1]
        write_json(d / "result.json", {"fold": fold, "inner_split": inner, "config_index": k,
                                       "best_epoch": res.best_epoch, "best_criterion": res.best_score,
                                       "val_mae_temperature": best["val_mae_temperature"],
                                       "val_mae_humidity": best["val_mae_humidity"],
                                       "epochs_run": res.epochs_run, "seconds": round(res.seconds, 1)})
        _finish_meta(d, best_epoch=res.best_epoch, best_criterion=res.best_score, epochs_run=res.epochs_run)
        complete_run(d, ["config.yaml", "run_meta.json", "leakage_check.json", "history.csv", "best_model.pt",
                         "result.json"])
        return "complete"
    except BaseException as exc:
        fail_run(d, exc)
        raise


# ------------------------------------------------------------------------------------------------------- selection

def select_config(scores: list[tuple[float, float]]) -> int:
    """Index of the lowest mean inner score; ties -> first in declared grid order."""
    means = [(a + b) / 2 for a, b in scores]
    return int(min(range(len(means)), key=lambda i: (means[i], i)))


def final_epochs(best_a: int, best_b: int) -> int:
    return round_half_up((best_a + best_b) / 2)


def select_fold(sess: P3Session, fold: int) -> dict:
    """Freeze fold's selection from its 32 complete inner runs. Immutable once written."""
    from src.training.trainer import config_grid

    grid = config_grid(load_protocol())
    res = {}
    for inner in INNER_SPLITS:
        for k in range(len(grid)):
            d = inner_dir(fold, inner, k)
            if run_status(d) != "complete":
                raise P3Error(f"fold {fold}: inner run {d.name} is not complete; selection refused")
            res[(inner, k)] = json.loads((d / "result.json").read_text(encoding="utf-8"))
    scores = [(res[("A", k)]["best_criterion"], res[("B", k)]["best_criterion"]) for k in range(len(grid))]
    k_sel = select_config(scores)
    ea, eb = res[("A", k_sel)]["best_epoch"], res[("B", k_sel)]["best_epoch"]
    fd = sess.fold(fold)
    tr = fd.labelled & (fd.partition == "train")
    d = run_root() / "selection" / f"fold{fold}_gate"
    plan = {"transform": "target_zscore", "partition": "train", "subjects": fd.train_subjects}
    ctx = RunContext("loso", fold=fold, input_features=list(RAW_FEATURES), fit_records=[plan],
                     selection_subjects=list(fd.train_subjects), window_groups=fd.window_groups(tr))
    _, verified = sess.gate(d, ctx)
    scaler = TargetScaler.fit(fd.targets[tr], scheme="loso", fold=str(fold), partition="train",
                              subjects=fd.train_subjects)
    inner_meta = {}
    for inner in INNER_SPLITS:
        tr_s, va_s = inner_subjects(fd, inner)
        inner_meta[inner] = {"train_subject": tr_s, "val_subject": va_s,
                             "criterion": res[(inner, k_sel)]["best_criterion"],
                             "best_epoch": res[(inner, k_sel)]["best_epoch"]}
    sel = {
        "fold": fold, "held_out_subject": fd.held_out, "train_subjects": fd.train_subjects, "family": P3_FAMILY,
        "selection_seed": int(load_protocol()["models"]["selection"]["seed_for_selection"]),
        "criterion": "mean over inner A/B of (MAE_T/sd_T + MAE_H/sd_H)/2 (sd from inner_train)",
        "grid": [{"config_index": k, **grid[k].as_dict(),
                  "inner_A_criterion": scores[k][0], "inner_B_criterion": scores[k][1],
                  "mean_criterion": (scores[k][0] + scores[k][1]) / 2,
                  "inner_A_best_epoch": res[("A", k)]["best_epoch"],
                  "inner_B_best_epoch": res[("B", k)]["best_epoch"]} for k in range(len(grid))],
        "selected_index": k_sel, "selected_config": grid[k_sel].as_dict(), "inner": inner_meta,
        "selection_score": (scores[k_sel][0] + scores[k_sel][1]) / 2,
        "final_epochs": final_epochs(ea, eb), "final_epochs_rule": "round_half_up(mean(inner A, inner B best epoch))",
        "outer_target_scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(),
                                "n": scaler.fit_provenance["n"], "subjects": fd.train_subjects},
        "final_seeds": [int(s) for s in load_protocol()["models"]["seeds"]],
        **frozen_inputs(verified), **git_state(),
    }
    p = selection_path(fold)
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
        keep = {k: v for k, v in old.items() if k not in ("git_commit", "git_dirty_tracked_files", "frozen_at")}
        new = {k: v for k, v in sel.items() if k not in ("git_commit", "git_dirty_tracked_files")}
        if keep != new:
            raise P3Error(f"selection for fold {fold} already frozen with different content; refusing to change it")
        return old
    sel["frozen_at"] = now()
    write_json(p, sel)
    return sel


def export_selection() -> dict:
    """Write the committed resolved config for the final runs (all three folds must be frozen)."""
    folds = {}
    for fold in sorted(int(k) for k in load_protocol()["loso"]["outer_folds"]):
        p = selection_path(fold)
        if not p.exists():
            raise SelectionNotFrozenError(f"fold {fold} selection is not frozen")
        s = json.loads(p.read_text(encoding="utf-8"))
        folds[fold] = {"held_out_subject": s["held_out_subject"], "train_subjects": s["train_subjects"],
                       "selected_index": s["selected_index"], "config": s["selected_config"],
                       "final_epochs": s["final_epochs"],
                       "inner_best_epochs": {k: v["best_epoch"] for k, v in s["inner"].items()},
                       "inner_criteria": {k: v["criterion"] for k, v in s["inner"].items()},
                       "selection_score": s["selection_score"],
                       "outer_target_scaler": {"mean": s["outer_target_scaler"]["mean"],
                                               "std": s["outer_target_scaler"]["std"],
                                               "n": s["outer_target_scaler"]["n"]},
                       "selection_sha256": S.file_sha256_lf(p)}
    doc = {"description": "P3 frozen RAW-TCN selection (protocol v1.0; generated by scripts/run_p3_loso_baseline.py "
                          "export-selection before any outer-test TCN evaluation)",
           "protocol_version": PROTOCOL_VERSION, "protocol_sha256": protocol_sha256(),
           "split_sha256": {k: v["sha256"] for k, v in load_manifest()["files"].items()},
           "family": P3_FAMILY, "final_seeds": [int(s) for s in load_protocol()["models"]["seeds"]],
           "folds": folds}
    p = selected_yaml()
    text = yaml.safe_dump(doc, sort_keys=False)
    if p.exists() and p.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
        raise P3Error("committed selection file exists with different content; refusing to change it")
    write_text(p, text)
    return doc


def frozen_selection() -> dict:
    """The committed selection; every fold present; consistent with outputs/ selection files when those exist."""
    p = selected_yaml()
    if not p.exists():
        raise SelectionNotFrozenError("configs/experiments/v1.0/p3_selected_configs.yaml does not exist")
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    folds = {int(k): v for k, v in doc["folds"].items()}
    want = sorted(int(k) for k in load_protocol()["loso"]["outer_folds"])
    if sorted(folds) != want:
        raise SelectionNotFrozenError(f"selection covers folds {sorted(folds)}, need {want}")
    if doc["protocol_sha256"] != protocol_sha256():
        raise P3Error("protocol file changed after the selection was frozen")
    for f, rec in folds.items():
        sp = selection_path(f)
        if sp.exists() and S.file_sha256_lf(sp) != rec["selection_sha256"]:
            raise P3Error(f"fold {f}: outputs selection file differs from the committed selection")
    doc["folds"] = folds
    return doc


# ------------------------------------------------------------------------------------------------ final outer runs

def run_final(sess: P3Session, fold: int, seed: int) -> str:
    import torch
    from src.training.trainer import TCNConfig, predict_z, train_tcn

    d = final_dir(fold, seed)
    if run_status(d) == "complete":
        return "skipped (complete)"
    sel_doc = frozen_selection()                       # raises before any outer-test step if not frozen
    sel = sel_doc["folds"][fold]
    if seed not in sel_doc["final_seeds"]:
        raise P3Error(f"seed {seed} is not a declared final seed")
    feats = assert_p3_family(sel_doc["family"])
    cfg = TCNConfig(**sel["config"])
    run_id = _run_id(f"p3-final-fold{fold}-seed{seed}")
    begin_run(d, run_id)
    log = RunLog(d, sess.echo)
    try:
        fd = sess.fold(fold)
        if fd.held_out != sel["held_out_subject"]:
            raise P3Error("held-out subject differs from the frozen selection")
        tr = fd.labelled & (fd.partition == "train")
        te = fd.labelled & (fd.partition == "test")
        plan = {"transform": "target_zscore", "partition": "train", "subjects": fd.train_subjects}
        ctx = RunContext("loso", fold=fold, input_features=list(feats), fit_records=[plan], selection_subjects=[],
                         window_groups=fd.window_groups(tr | te))
        _, verified = sess.gate(d, ctx)
        scaler = TargetScaler.fit(fd.targets[tr], scheme="loso", fold=str(fold), partition="train",
                                  subjects=fd.train_subjects)
        if not (np.allclose(scaler.mean, sel["outer_target_scaler"]["mean"], rtol=0, atol=1e-9)
                and np.allclose(scaler.std, sel["outer_target_scaler"]["std"], rtol=0, atol=1e-9)):
            raise P3Error("outer scaler statistics differ from the frozen selection")
        _meta(d, run_id, "final", fold, fd.held_out, seed, cfg.as_dict(), verified,
              {"selected_index": sel["selected_index"], "final_epochs": sel["final_epochs"],
               "selection_sha256": sel["selection_sha256"], "train_subjects": fd.train_subjects,
               "n_train_windows": int(tr.sum()), "n_test_windows": int(te.sum()),
               "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance}})
        write_text(d / "config.yaml", yaml.safe_dump({"family": P3_FAMILY, "fold": fold, "seed": seed,
                                                      "selected_index": sel["selected_index"], **cfg.as_dict(),
                                                      "epochs": sel["final_epochs"]}, sort_keys=False))
        res = train_tcn(cfg, fd.pressure[tr], fd.targets[tr], scaler, seed, epochs=sel["final_epochs"], log=log)
        write_csv(d / "history.csv", res.history, list(res.history[0]))
        with open_for_write(d / "model.pt", "wb") as fh:
            torch.save(res.model.state_dict(), fh)
        # the single outer-test look for this model
        log_outer_access(fold, seed, "tcn_raw", run_id, sel["selection_sha256"])
        from src.training.trainer import device, to_tensor
        pred = scaler.inverse(predict_z(res.model, to_tensor(fd.pressure[te], device())))
        m = write_metrics(d / "metrics.csv", run_id, fold, fd.held_out, fd.targets[te], pred)
        write_predictions(d / "predictions.parquet", run_id, "tcn_raw", fold, seed, fd.prov, te, fd.targets[te], pred)
        _finish_meta(d, epochs_run=res.epochs_run, train_seconds=round(res.seconds, 1), outer_test_metrics=m)
        log(f"fold {fold} seed {seed}: {json.dumps(m)}")
        complete_run(d, ["config.yaml", "run_meta.json", "leakage_check.json", "history.csv", "model.pt",
                         "metrics.csv", "predictions.parquet"])
        return "complete"
    except BaseException as exc:
        fail_run(d, exc)
        raise


# ------------------------------------------------------------------------------------------------------ aggregation

def read_predictions(path: Path) -> dict[str, np.ndarray]:
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    return {c: t[c].to_numpy(zero_copy_only=False) for c in t.column_names}


def _pairs(pr: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    """Long predictions -> (y, p) of shape (n, 2) and per-window provenance (temperature rows define order)."""
    t = pr["target"] == "temperature"
    h = pr["target"] == "humidity"
    if t.sum() != h.sum():
        raise P3Error("unpaired prediction rows")
    y = np.stack([pr["y_true"][t], pr["y_true"][h]], 1)
    p = np.stack([pr["y_pred"][t], pr["y_pred"][h]], 1)
    prov = {k: v[t] for k, v in pr.items() if k not in ("target", "y_true", "y_pred")}
    return y, p, prov


def strata_rows(model: str, fold: int, seed, subject: str, y, p, prov) -> list[dict]:
    out = []

    def add(kind, name, mask):
        if mask.sum() == 0:
            return
        m = target_metrics(y[mask], p[mask])
        for t, dd in m.items():
            for k, v in dd.items():
                out.append({"model": model, "fold": fold, "seed": seed, "subject_id": subject, "stratum_type": kind,
                            "stratum": name, "target": t, "metric": k, "value": v, "n_windows": int(mask.sum())})
    add("overall", "all", np.ones(len(y), bool))
    for kind, col in (("device", "device_id"), ("sensor_phase", "sensor_phase"),
                      ("channel_quality_phase", "channel_quality_phase")):
        vals = sorted(set(prov[col]))
        if len(vals) > 1 or (kind == "device" and subject == "User02"):
            for v in vals:
                add(kind, v, prov[col] == v)
    if subject == "User02":
        for v in sorted(set(prov["channel_quality_phase"][prov["device_id"] == "22482"])):
            add("device_x_channel_quality_phase", f"22482/{v}",
                (prov["device_id"] == "22482") & (prov["channel_quality_phase"] == v))
    # per-night error distribution (declared secondary): quantiles of per-night MAE
    nights = prov["night_id"]
    uniq, inv = np.unique(nights, return_inverse=True)
    for i, t in enumerate(TARGETS):
        err = np.abs(p[:, i] - y[:, i])
        per_night = np.bincount(inv, weights=err) / np.bincount(inv)
        for q, name in ((25, "p25"), (50, "median"), (75, "p75")):
            out.append({"model": model, "fold": fold, "seed": seed, "subject_id": subject,
                        "stratum_type": "per_night_mae", "stratum": f"{name} of {len(uniq)} nights", "target": t,
                        "metric": "mae", "value": float(np.percentile(per_night, q)), "n_windows": int(len(y))})
    return out


def _seed_mean(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in keys), []).append(r)
    out = []
    for key, rs in groups.items():
        v = np.array([r["value"] for r in rs])
        out.append({**dict(zip(keys, key)), "seed": "mean", "value": float(v.mean()),
                    "seed_sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0, "seed_min": float(v.min()),
                    "seed_max": float(v.max()), "n_seeds": len(v), "n_windows": rs[0]["n_windows"]})
    return out


def aggregate() -> dict[str, list[dict]]:
    """All P3 tables from complete runs only (fails if anything is missing or incomplete).

    Seeds are aggregated by averaging their metrics (never by averaging predictions: no ensemble is declared).
    """
    cfg = load_protocol()
    folds = {int(k): v for k, v in cfg["loso"]["outer_folds"].items()}
    seeds = [int(s) for s in cfg["models"]["seeds"]]
    sel_doc = frozen_selection()
    tables: dict[str, list[dict]] = {}
    tm, strata, by_seed, cache = [], [], [], {}
    for f, held in folds.items():
        d = training_mean_dir(f)
        if run_status(d) != "complete":
            raise P3Error(f"training-mean fold {f} incomplete")
        meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
        y, p, prov = cache[("training_mean", f)] = _pairs(read_predictions(d / "predictions.parquet"))
        m = target_metrics(y, p)
        tm.append({"fold": f, "held_out_subject": held, "train_subjects": "+".join(meta["train_subjects"]),
                   "train_n_windows": meta["n_train_windows"], "test_n_windows": meta["n_test_windows"],
                   "train_mean_temp": meta["train_mean"][0], "train_mean_humidity": meta["train_mean"][1],
                   "MAE_T": m["temperature"]["mae"], "RMSE_T": m["temperature"]["rmse"],
                   "bias_T": m["temperature"]["bias"], "MAE_H": m["humidity"]["mae"],
                   "RMSE_H": m["humidity"]["rmse"], "bias_H": m["humidity"]["bias"]})
        strata += strata_rows("training_mean", f, "", held, y, p, prov)
        for s in seeds:
            d = final_dir(f, s)
            if run_status(d) != "complete":
                raise P3Error(f"final fold {f} seed {s} incomplete")
            y, p, prov = cache[("tcn_raw", f, s)] = _pairs(read_predictions(d / "predictions.parquet"))
            m = target_metrics(y, p)
            for t in TARGETS:
                by_seed.append({"fold": f, "held_out_subject": held, "seed": s, "target": t,
                                "mae": m[t]["mae"], "rmse": m[t]["rmse"], "bias": m[t]["bias"],
                                "n_windows": int(len(y)), "final_epochs": sel_doc["folds"][f]["final_epochs"]})
            strata += strata_rows("tcn_raw", f, s, held, y, p, prov)
    tables["training_mean_by_fold"] = tm
    tables["tcn_outer_by_seed"] = by_seed
    by_fold = []
    for f, held in folds.items():
        for t in TARGETS:
            for metric in ("mae", "rmse", "bias"):
                v = np.array([r[metric] for r in by_seed if r["fold"] == f and r["target"] == t])
                by_fold.append({"fold": f, "held_out_subject": held, "target": t, "metric": metric,
                                "seed_mean": float(v.mean()), "seed_sd": float(v.std(ddof=1)),
                                "seed_min": float(v.min()), "seed_max": float(v.max()), "n_seeds": len(v)})
    tables["tcn_outer_by_fold"] = by_fold
    col = {"mae": "MAE", "rmse": "RMSE", "bias": "bias"}
    summary = []
    for t in TARGETS:
        suffix = "T" if t == "temperature" else "H"
        for metric in ("mae", "rmse", "bias"):
            tm_vals = {r["held_out_subject"]: r[f"{col[metric]}_{suffix}"] for r in tm}
            tcn_vals = {r["held_out_subject"]: r["seed_mean"] for r in by_fold
                        if r["target"] == t and r["metric"] == metric}
            for model, vals in (("training_mean", tm_vals), ("tcn_raw", tcn_vals)):
                summary.append({"model": model, "target": t, "metric": metric,
                                **{s: vals[s] for s in folds.values()},
                                "unweighted_subject_mean": unweighted_subject_mean(vals)})
    tables["tcn_outer_summary"] = summary
    pooled = []                                            # window-weighted pooled metric (secondary)
    groups = [("training_mean", "", [cache[("training_mean", f)] for f in folds])]
    groups += [("tcn_raw", s, [cache[("tcn_raw", f, s)] for f in folds]) for s in seeds]
    for model, seed, parts in groups:
        yy = np.concatenate([q[0] for q in parts])
        pp = np.concatenate([q[1] for q in parts])
        m = target_metrics(yy, pp)
        for t in TARGETS:
            for k, v in m[t].items():
                pooled.append({"model": model, "seed": seed, "target": t, "metric": k, "value": v,
                               "n_windows": int(len(yy))})
    tables["secondary_window_weighted_pooled"] = pooled
    tcn_strata = [r for r in strata if r["model"] == "tcn_raw"]
    tables["secondary_strata"] = strata + [
        {"model": "tcn_raw", **r} for r in _seed_mean(tcn_strata, ("fold", "subject_id", "stratum_type", "stratum",
                                                                   "target", "metric"))]
    inner_rows, sel_rows = [], []
    for f in folds:
        if not selection_path(f).exists():
            raise P3Error(f"selection file of fold {f} missing")
        s = json.loads(selection_path(f).read_text(encoding="utf-8"))
        for g in s["grid"]:
            inner_rows.append({"fold": f, "held_out_subject": s["held_out_subject"], **g,
                               "selected": int(g["config_index"] == s["selected_index"])})
        sel_rows.append({"fold": f, "held_out_subject": s["held_out_subject"], "selected_index": s["selected_index"],
                         **s["selected_config"], "inner_A_criterion": s["inner"]["A"]["criterion"],
                         "inner_A_best_epoch": s["inner"]["A"]["best_epoch"],
                         "inner_B_criterion": s["inner"]["B"]["criterion"],
                         "inner_B_best_epoch": s["inner"]["B"]["best_epoch"],
                         "selection_score": s["selection_score"], "final_epochs": s["final_epochs"]})
    tables["tcn_inner_search"] = inner_rows
    tables["tcn_selected_configs"] = sel_rows
    return tables


def run_index() -> list[dict]:
    rows = []
    for kind in ("training_mean", "inner", "final"):
        base = run_root() / kind
        for d in (sorted(base.glob("*")) if base.exists() else []):
            st = _status(d)
            rows.append({"kind": kind, "run": d.name, "status": run_status(d), "attempt": st.get("attempt"),
                         "previous_attempts": len(st.get("history", [])), "run_id": st.get("run_id"),
                         "started_at": st.get("started_at"), "finished_at": st.get("finished_at")})
    return rows


def outer_access_counts() -> dict[str, int]:
    p = run_root() / "outer_test_access.jsonl"
    counts: dict[str, int] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            key = f"{r['model']}|fold{r['fold']}|seed{r['seed']}"
            counts[key] = counts.get(key, 0) + 1
    return counts
