"""P4 feature-family comparison under frozen protocol v1.0 (RQ3; docs/EXPERIMENT_PROTOCOL.md §8–§11; D-039–D-041,
D-043, D-044).

Families trained here: MOVEMENT, CONTACT, RAW+MOVEMENT, RAW+CONTACT, RAW+MOVEMENT+CONTACT. RAW is not re-run: the RAW
TCN and the training-mean predictor frozen at `p3-loso-baseline` are imported from the committed P3 tables as the
reference rows.

Order enforced by the code, per family:
1. inner search: 3 folds x 16 configurations x 2 inner splits (seed 0), early stopping on inner validation;
2. per-fold selection frozen to `outputs/runs/p4/<family>/selection/fold<k>.json`, then all 15 family x fold
   selections to `configs/experiments/v1.0/p4_selected_configs.yaml`;
3. only once that file is committed (tracked and unmodified): final models (3 folds x seeds 0/1/2, fixed epochs, whole
   outer training pool), each followed by the single outer-test evaluation of that model;
4. aggregation against the frozen P3 reference.
Run bookkeeping, provenance, the leakage-gate session, prediction and metric writers, strata, the selection rule and
the final-epoch rule are P3's (`src/evaluation/p3_loso.py`), imported unchanged. Only the input family changes.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

from src.data import paths
from src.data.io_guard import open_for_write, write_csv, write_json, write_text
from src.evaluation import splits as S
from src.evaluation.leakage import RunContext, check_calendar, check_inputs
from src.evaluation.metrics import TARGETS, target_metrics, unweighted_subject_mean
from src.evaluation.p2_protocol import load_manifest
from src.evaluation.p3_loso import (INNER_SPLITS, P3Session, RunLog, _pairs, _seed_mean, _status, begin_run,
                                    complete_run, fail_run, final_epochs, frozen_inputs, git_state, inner_subjects,
                                    now, read_predictions, run_status, select_config, strata_rows, write_metrics,
                                    write_predictions)
from src.evaluation.protocol import PROTOCOL_VERSION, load_protocol, protocol_sha256
from src.features.pressure_features import (ADMISSIBLE_FEATURES, FAMILIES, FAMILY_PARTS, TargetScaler,
                                            family_features)

REFERENCE_FAMILY = "RAW"
P4_FAMILIES = ("MOVEMENT", "CONTACT", "RAW+MOVEMENT", "RAW+CONTACT", "RAW+MOVEMENT+CONTACT")
ALL_FAMILIES = (REFERENCE_FAMILY, *P4_FAMILIES)
FAMILY_DIMS = {"RAW": 6, "MOVEMENT": 10, "CONTACT": 11, "RAW+MOVEMENT": 16, "RAW+CONTACT": 17,
               "RAW+MOVEMENT+CONTACT": 27}
TRAINING_MEAN = "training_mean"
P3_TAG = "p3-loso-baseline"
P3_REFERENCE_FILES = ("paper/tables/p3_tcn_outer_by_seed.csv", "paper/tables/p3_training_mean_by_fold.csv",
                      "paper/tables/p3_primary_summary.csv", "paper/tables/p3_secondary_strata.csv",
                      "paper/tables/p3_selected_configs.csv", "configs/experiments/v1.0/p3_selected_configs.yaml")
# Pre-declared comparisons (D-044). Delta = metric(first) - metric(second): negative = the first is better.
EFFECTS = (("A", "MOVEMENT added to RAW", "RAW+MOVEMENT", "RAW"),
           ("B", "CONTACT added to RAW", "RAW+CONTACT", "RAW"),
           ("C", "MOVEMENT+CONTACT added to RAW", "RAW+MOVEMENT+CONTACT", "RAW"),
           ("D", "CONTACT added to RAW+MOVEMENT", "RAW+MOVEMENT+CONTACT", "RAW+MOVEMENT"),
           ("E", "MOVEMENT added to RAW+CONTACT", "RAW+MOVEMENT+CONTACT", "RAW+CONTACT"))
STANDALONE = (("S1", "MOVEMENT alone vs RAW", "MOVEMENT", "RAW"),
              ("S2", "CONTACT alone vs RAW", "CONTACT", "RAW"))
PRIMARY_METRICS = ("mae", "rmse")


class P4Error(RuntimeError):
    pass


class SelectionNotFrozenError(P4Error):
    """Raised when an outer-test step is attempted before the P4 selection file is committed."""


def family_slug(family: str) -> str:
    return family.lower().replace("+", "_")


def model_label(family: str) -> str:
    return f"tcn_{family_slug(family)}"


# ------------------------------------------------------------------------------------------------ family guard

def assert_family_inputs(family: str) -> tuple[str, ...]:
    """The declared inputs of `family`, checked against protocol.yaml and the frozen definitions (fail closed)."""
    if family not in FAMILY_DIMS:
        raise P4Error(f"unknown feature family {family!r}")
    protocol = load_protocol()["inputs"]
    if protocol["families"].get(family) != list(FAMILIES[family]):
        raise P4Error(f"{family}: composition differs from protocol.yaml")
    feats = family_features(family)
    if len(feats) != FAMILY_DIMS[family] or len(set(feats)) != len(feats):
        raise P4Error(f"{family}: {len(feats)} inputs, expected {FAMILY_DIMS[family]} distinct inputs")
    expected = tuple(f for part in protocol["families"][family] for f in FAMILY_PARTS[part])
    if feats != expected:
        raise P4Error(f"{family}: input order differs from the declared part order")
    for part, names in FAMILY_PARTS.items():
        present = [f for f in feats if f in names]
        if part in FAMILIES[family] and tuple(present) != names:
            raise P4Error(f"{family}: {part} inputs incomplete")
        if part not in FAMILIES[family] and present:
            raise P4Error(f"{family}: contains {part} inputs {present}")
    if not set(feats) <= ADMISSIBLE_FEATURES or set(feats) & set(protocol["forbidden_fields"]):
        raise P4Error(f"{family}: inadmissible input")
    problem = check_inputs(list(feats)) or check_calendar(list(feats))
    if problem:
        raise P4Error(f"{family}: {problem}")
    return feats


def assert_p4_family(family: str) -> tuple[str, ...]:
    if family not in P4_FAMILIES:
        raise P4Error(f"P4 trains {', '.join(P4_FAMILIES)} (got {family!r}); RAW is the frozen P3 reference")
    return assert_family_inputs(family)


# ---------------------------------------------------------------------------------------------------------- paths

def run_root() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "runs" / "p4"


def metrics_dir() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "metrics" / "p4"


def selected_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / PROTOCOL_VERSION / "p4_selected_configs.yaml"


def family_root(family: str) -> Path:
    return run_root() / family_slug(family)


def inner_dir(family: str, fold: int, inner: str, k: int) -> Path:
    return family_root(family) / "inner" / f"fold{fold}_{inner}_cfg{k:02d}"


def selection_path(family: str, fold: int) -> Path:
    return family_root(family) / "selection" / f"fold{fold}.json"


def final_dir(family: str, fold: int, seed: int) -> Path:
    return family_root(family) / "final" / f"fold{fold}_seed{seed}"


# -------------------------------------------------------------------------------------------------- provenance

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=paths.PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")


def p4_git_state() -> dict:
    return {**git_state(), "p3_tag": P3_TAG, "p3_tag_commit": _git("rev-list", "-n", "1", P3_TAG).stdout.strip()
            or None}


def _run_id(name: str) -> str:
    return f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{name}"


def _meta(d: Path, run_id: str, kind: str, family: str, fold: int, held_out: str, seed: int | None,
          config: dict | None, verified: dict, extra: dict) -> dict:
    from src.training.trainer import environment, set_determinism
    if seed is not None:
        set_determinism(seed)          # record the flags train_tcn runs with (P3 report §14 note); it re-seeds anyway
    feats = family_features(family)
    meta = {"run_id": run_id, "phase": "P4", "kind": kind, "fold": fold, "held_out_subject": held_out, "seed": seed,
            "family": family, "input_features": list(feats), "n_inputs": len(feats), "config": config,
            **frozen_inputs(verified), **p4_git_state(), **environment(), "started_at": now(), **extra}
    write_json(d / "run_meta.json", meta)
    return meta


def _finish_meta(d: Path, **extra) -> None:
    meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
    meta.update(finished_at=now(), **extra)
    write_json(d / "run_meta.json", meta)


def log_outer_access(family: str, fold: int, seed: int, run_id: str, selection_sha: str, commit: str) -> None:
    with open_for_write(run_root() / "outer_test_access.jsonl", "a") as fh:
        fh.write(json.dumps({"at": now(), "family": family, "fold": fold, "seed": seed, "model": model_label(family),
                             "run_id": run_id, "selection_sha256": selection_sha,
                             "selection_commit": commit}) + "\n")


def _check_family_tensor(fd, family: str, feats: tuple[str, ...]) -> None:
    """The input array the trainer builds for this family has exactly the declared width."""
    from src.training.trainer import input_array
    x = input_array(fd.pressure[:2], family)
    if x.shape[-1] != len(feats):
        raise P4Error(f"{family}: input array has {x.shape[-1]} features, declared {len(feats)}")


# ---------------------------------------------------------------------------------------------------- inner search

def run_inner(sess: P3Session, family: str, fold: int, inner: str, k: int) -> str:
    import torch
    from src.training.trainer import config_grid, train_tcn

    d = inner_dir(family, fold, inner, k)
    if run_status(d) == "complete":
        return "skipped (complete)"
    feats = assert_p4_family(family)
    cfg = config_grid(load_protocol())[k]
    seed = int(load_protocol()["models"]["selection"]["seed_for_selection"])
    run_id = _run_id(f"p4-{family_slug(family)}-inner-fold{fold}{inner}-cfg{k:02d}")
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
        _check_family_tensor(fd, family, feats)
        scaler = TargetScaler.fit(fd.targets[tr], scheme="loso", fold=str(fold), partition="inner_train",
                                  subjects=[train_subj])
        if scaler.fit_provenance["subjects"] != plan["subjects"]:
            raise P4Error("scaler provenance differs from the gated plan")
        _meta(d, run_id, "inner", family, fold, fd.held_out, seed, cfg.as_dict(), verified,
              {"inner_split": inner, "config_index": k, "inner_train_subject": train_subj,
               "inner_val_subject": val_subj, "n_train_windows": int(tr.sum()), "n_val_windows": int(va.sum()),
               "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance}})
        write_text(d / "config.yaml", yaml.safe_dump({"family": family, "input_features": list(feats),
                                                      "config_index": k, **cfg.as_dict(), "seed": seed, "fold": fold,
                                                      "inner_split": inner}, sort_keys=False))
        res = train_tcn(cfg, fd.pressure[tr], fd.targets[tr], scaler, seed, pressure_va=fd.pressure[va],
                        y_va=fd.targets[va], log=log, family=family)
        write_csv(d / "history.csv", res.history, list(res.history[0]))
        with open_for_write(d / "best_model.pt", "wb") as fh:
            torch.save(res.model.state_dict(), fh)
        best = res.history[res.best_epoch - 1]
        write_json(d / "result.json", {"family": family, "fold": fold, "inner_split": inner, "config_index": k,
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

def scaler_digest(stats: dict) -> str:
    """SHA-256 of the outer target-scaler statistics and their fit provenance (canonical JSON)."""
    keys = ("mean", "std", "n", "subjects", "partition", "fold")
    return hashlib.sha256(json.dumps({k: stats[k] for k in keys}, sort_keys=True).encode()).hexdigest()


def p3_outer_scaler(fold: int) -> dict:
    """The outer target-scaler statistics frozen by P3 for this fold (same outer training pool for every family)."""
    doc = yaml.safe_load((paths.PROJECT_ROOT / P3_REFERENCE_FILES[-1]).read_text(encoding="utf-8"))
    return {int(k): v for k, v in doc["folds"].items()}[fold]["outer_target_scaler"]


def select_fold(sess: P3Session, family: str, fold: int) -> dict:
    """Freeze the family x fold selection from its 32 complete inner runs. Immutable once written."""
    from src.training.trainer import config_grid

    feats = assert_p4_family(family)
    grid = config_grid(load_protocol())
    res = {}
    for inner in INNER_SPLITS:
        for k in range(len(grid)):
            d = inner_dir(family, fold, inner, k)
            if run_status(d) != "complete":
                raise P4Error(f"{family} fold {fold}: inner run {d.name} is not complete; selection refused")
            res[(inner, k)] = json.loads((d / "result.json").read_text(encoding="utf-8"))
            if res[(inner, k)].get("family") != family:
                raise P4Error(f"{d}: result belongs to another family")
    scores = [(res[("A", k)]["best_criterion"], res[("B", k)]["best_criterion"]) for k in range(len(grid))]
    k_sel = select_config(scores)
    ea, eb = res[("A", k_sel)]["best_epoch"], res[("B", k_sel)]["best_epoch"]
    fd = sess.fold(fold)
    tr = fd.labelled & (fd.partition == "train")
    d = family_root(family) / "selection" / f"fold{fold}_gate"
    plan = {"transform": "target_zscore", "partition": "train", "subjects": fd.train_subjects}
    ctx = RunContext("loso", fold=fold, input_features=list(feats), fit_records=[plan],
                     selection_subjects=list(fd.train_subjects), window_groups=fd.window_groups(tr))
    _, verified = sess.gate(d, ctx)
    scaler = TargetScaler.fit(fd.targets[tr], scheme="loso", fold=str(fold), partition="train",
                              subjects=fd.train_subjects)
    ref = p3_outer_scaler(fold)
    if not (np.allclose(scaler.mean, ref["mean"], rtol=0, atol=1e-9)
            and np.allclose(scaler.std, ref["std"], rtol=0, atol=1e-9) and scaler.fit_provenance["n"] == ref["n"]):
        raise P4Error(f"fold {fold}: outer target scaler differs from the frozen P3 scaler of the same pool")
    stats = {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), "n": scaler.fit_provenance["n"],
             "subjects": fd.train_subjects, "partition": "train", "fold": str(fold)}
    inner_meta = {}
    for inner in INNER_SPLITS:
        tr_s, va_s = inner_subjects(fd, inner)
        inner_meta[inner] = {"train_subject": tr_s, "val_subject": va_s,
                             "criterion": res[(inner, k_sel)]["best_criterion"],
                             "best_epoch": res[(inner, k_sel)]["best_epoch"]}
    sel = {
        "family": family, "input_features": list(feats), "n_inputs": len(feats),
        "fold": fold, "held_out_subject": fd.held_out, "train_subjects": fd.train_subjects,
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
        "outer_target_scaler": {**stats, "sha256": scaler_digest(stats), "equals_p3_frozen_scaler": True},
        "final_seeds": [int(s) for s in load_protocol()["models"]["seeds"]],
        **frozen_inputs(verified), **p4_git_state(),
    }
    p = selection_path(family, fold)
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
        drop = ("git_commit", "git_dirty_tracked_files", "frozen_at")
        if {k: v for k, v in old.items() if k not in drop} != {k: v for k, v in sel.items() if k not in drop}:
            raise P4Error(f"{family} fold {fold}: selection already frozen with different content; refusing")
        return old
    sel["frozen_at"] = now()
    write_json(p, sel)
    return sel


def export_selection() -> dict:
    """Write the committed P4 selection (all 15 family x fold selections must be frozen)."""
    folds_cfg = sorted(int(k) for k in load_protocol()["loso"]["outer_folds"])
    families = {}
    for fam in P4_FAMILIES:
        feats = assert_p4_family(fam)
        folds = {}
        for fold in folds_cfg:
            p = selection_path(fam, fold)
            if not p.exists():
                raise SelectionNotFrozenError(f"{fam} fold {fold} selection is not frozen")
            s = json.loads(p.read_text(encoding="utf-8"))
            folds[fold] = {"held_out_subject": s["held_out_subject"], "train_subjects": s["train_subjects"],
                           "selected_index": s["selected_index"], "config": s["selected_config"],
                           "inner_criteria": {k: v["criterion"] for k, v in s["inner"].items()},
                           "selection_score": s["selection_score"],
                           "inner_best_epochs": {k: v["best_epoch"] for k, v in s["inner"].items()},
                           "final_epochs": s["final_epochs"],
                           "outer_target_scaler": {k: s["outer_target_scaler"][k]
                                                   for k in ("mean", "std", "n", "subjects", "sha256")},
                           "selection_sha256": S.file_sha256_lf(p)}
        families[fam] = {"input_features": list(feats), "n_inputs": len(feats), "folds": folds}
    p3_yaml = paths.PROJECT_ROOT / P3_REFERENCE_FILES[-1]
    doc = {"description": "P4 frozen feature-family TCN selections (protocol v1.0; generated by "
                          "scripts/run_p4_feature_ablation.py export-selection from inner validation only, before any "
                          "P4 outer-test evaluation)",
           "protocol_version": PROTOCOL_VERSION, "protocol_sha256": protocol_sha256(),
           "split_sha256": {k: v["sha256"] for k, v in load_manifest()["files"].items()},
           "selection_seed": int(load_protocol()["models"]["selection"]["seed_for_selection"]),
           "criterion": "mean over inner A/B of (MAE_T/sd_T + MAE_H/sd_H)/2 (sd from inner_train); ties -> grid order",
           "final_epochs_rule": "round_half_up(mean(inner A, inner B best epoch))",
           "final_seeds": [int(s) for s in load_protocol()["models"]["seeds"]],
           "reference": {"family": REFERENCE_FAMILY, "p3_tag": P3_TAG,
                         "p3_selected_configs_sha256": S.file_sha256_lf(p3_yaml)},
           "families": families}
    p = selected_yaml()
    text = yaml.safe_dump(doc, sort_keys=False)
    if p.exists() and p.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
        raise P4Error("committed P4 selection file exists with different content; refusing to change it")
    write_text(p, text)
    return doc


def selection_commit() -> str:
    """Commit holding the selection file; refuses unless the file is tracked and unmodified (commit-before-test)."""
    try:
        rel = selected_yaml().relative_to(paths.PROJECT_ROOT).as_posix()
    except ValueError:
        raise SelectionNotFrozenError(f"{selected_yaml()} is outside the repository") from None
    if not selected_yaml().exists() or _git("ls-files", "--error-unmatch", rel).returncode != 0:
        raise SelectionNotFrozenError(f"{rel} is not committed")
    if _git("diff", "--quiet", "HEAD", "--", rel).returncode != 0:
        raise SelectionNotFrozenError(f"{rel} differs from its committed version")
    return _git("log", "-n", "1", "--format=%H", "--", rel).stdout.strip()


def frozen_selection() -> dict:
    """The committed P4 selection: every family and fold present, consistent with the frozen protocol and splits."""
    p = selected_yaml()
    if not p.exists():
        raise SelectionNotFrozenError(f"{p.name} does not exist")
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    want = sorted(int(k) for k in load_protocol()["loso"]["outer_folds"])
    if sorted(doc["families"]) != sorted(P4_FAMILIES):
        raise SelectionNotFrozenError(f"selection covers {sorted(doc['families'])}, need {sorted(P4_FAMILIES)}")
    if doc["protocol_sha256"] != protocol_sha256():
        raise P4Error("protocol file changed after the selection was frozen")
    if doc["split_sha256"] != {k: v["sha256"] for k, v in load_manifest()["files"].items()}:
        raise P4Error("split files changed after the selection was frozen")
    for fam, rec in doc["families"].items():
        rec["folds"] = {int(k): v for k, v in rec["folds"].items()}
        if sorted(rec["folds"]) != want:
            raise SelectionNotFrozenError(f"{fam}: selection covers folds {sorted(rec['folds'])}, need {want}")
        if rec["input_features"] != list(assert_p4_family(fam)):
            raise P4Error(f"{fam}: frozen input list differs from the family definition")
        for f, s in rec["folds"].items():
            sp = selection_path(fam, f)
            if sp.exists() and S.file_sha256_lf(sp) != s["selection_sha256"]:
                raise P4Error(f"{fam} fold {f}: outputs selection file differs from the committed selection")
    return doc


# ------------------------------------------------------------------------------------------------ final outer runs

def run_final(sess: P3Session, family: str, fold: int, seed: int) -> str:
    import torch
    from src.training.trainer import TCNConfig, device, predict_z, to_tensor, train_tcn

    d = final_dir(family, fold, seed)
    if run_status(d) == "complete":
        return "skipped (complete)"
    feats = assert_p4_family(family)
    doc = frozen_selection()                      # raises before any outer-test step if not frozen
    commit = selection_commit()                   # ... or not committed
    sel = doc["families"][family]["folds"][fold]
    if seed not in doc["final_seeds"]:
        raise P4Error(f"seed {seed} is not a declared final seed")
    cfg = TCNConfig(**sel["config"])
    run_id = _run_id(f"p4-{family_slug(family)}-final-fold{fold}-seed{seed}")
    begin_run(d, run_id)
    log = RunLog(d, sess.echo)
    try:
        fd = sess.fold(fold)
        if fd.held_out != sel["held_out_subject"]:
            raise P4Error("held-out subject differs from the frozen selection")
        tr = fd.labelled & (fd.partition == "train")
        te = fd.labelled & (fd.partition == "test")
        plan = {"transform": "target_zscore", "partition": "train", "subjects": fd.train_subjects}
        ctx = RunContext("loso", fold=fold, input_features=list(feats), fit_records=[plan], selection_subjects=[],
                         window_groups=fd.window_groups(tr | te))
        _, verified = sess.gate(d, ctx)
        _check_family_tensor(fd, family, feats)
        scaler = TargetScaler.fit(fd.targets[tr], scheme="loso", fold=str(fold), partition="train",
                                  subjects=fd.train_subjects)
        if not (np.allclose(scaler.mean, sel["outer_target_scaler"]["mean"], rtol=0, atol=1e-9)
                and np.allclose(scaler.std, sel["outer_target_scaler"]["std"], rtol=0, atol=1e-9)):
            raise P4Error("outer scaler statistics differ from the frozen selection")
        _meta(d, run_id, "final", family, fold, fd.held_out, seed, cfg.as_dict(), verified,
              {"selected_index": sel["selected_index"], "final_epochs": sel["final_epochs"],
               "selection_sha256": sel["selection_sha256"], "selection_file_sha256": S.file_sha256_lf(selected_yaml()),
               "selection_commit": commit, "train_subjects": fd.train_subjects,
               "n_train_windows": int(tr.sum()), "n_test_windows": int(te.sum()),
               "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance}})
        write_text(d / "config.yaml", yaml.safe_dump({"family": family, "input_features": list(feats), "fold": fold,
                                                      "seed": seed, "selected_index": sel["selected_index"],
                                                      **cfg.as_dict(), "epochs": sel["final_epochs"]},
                                                     sort_keys=False))
        res = train_tcn(cfg, fd.pressure[tr], fd.targets[tr], scaler, seed, epochs=sel["final_epochs"], log=log,
                        family=family)
        write_csv(d / "history.csv", res.history, list(res.history[0]))
        with open_for_write(d / "model.pt", "wb") as fh:
            torch.save(res.model.state_dict(), fh)
        # the single outer-test look for this model
        log_outer_access(family, fold, seed, run_id, sel["selection_sha256"], commit)
        pred = scaler.inverse(predict_z(res.model, to_tensor(fd.pressure[te], device(), family)))
        m = write_metrics(d / "metrics.csv", run_id, fold, fd.held_out, fd.targets[te], pred)
        write_predictions(d / "predictions.parquet", run_id, model_label(family), fold, seed, fd.prov, te,
                          fd.targets[te], pred)
        _finish_meta(d, epochs_run=res.epochs_run, train_seconds=round(res.seconds, 1), outer_test_metrics=m)
        log(f"{family} fold {fold} seed {seed}: {json.dumps(m)}")
        complete_run(d, ["config.yaml", "run_meta.json", "leakage_check.json", "history.csv", "model.pt",
                         "metrics.csv", "predictions.parquet"])
        return "complete"
    except BaseException as exc:
        fail_run(d, exc)
        raise


# --------------------------------------------------------------------------------------------- frozen P3 reference

def _read_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def p3_reference_unchanged() -> None:
    """The committed P3 reference files are byte-identical to `p3-loso-baseline`."""
    for rel in P3_REFERENCE_FILES:
        if not (paths.PROJECT_ROOT / rel).exists():
            raise P4Error(f"frozen P3 reference {rel} is missing")
        r = _git("diff", "--quiet", P3_TAG, "--", rel)
        if r.returncode != 0:
            raise P4Error(f"{rel} differs from {P3_TAG} (or the tag is missing)")


def p3_reference(root: Path | None = None, verify_tag: bool = True, include_selection: bool = True) -> dict:
    """RAW-TCN per-seed results, training-mean results, strata and selections as frozen by P3 (committed files only).

    RAW seed means are recomputed from the per-seed table and must equal the committed P3 summary (1e-12).
    include_selection=False skips the selection table (absent from a public-release reproduction; D-050).
    """
    root = paths.PROJECT_ROOT if root is None else root
    if verify_tag:
        p3_reference_unchanged()
    t = lambda name: _read_csv(root / "paper" / "tables" / name)  # noqa: E731
    outer = []
    for r in t("p3_tcn_outer_by_seed.csv"):
        outer.append({"family": REFERENCE_FAMILY, "fold": int(r["fold"]), "held_out_subject": r["held_out_subject"],
                      "seed": int(r["seed"]), "target": r["target"], "mae": float(r["mae"]), "rmse": float(r["rmse"]),
                      "bias": float(r["bias"]), "n_windows": int(r["n_windows"]),
                      "final_epochs": int(r["final_epochs"]), "source": "p3_frozen"})
    tm = []
    for r in t("p3_training_mean_by_fold.csv"):
        for tgt, suf in (("temperature", "T"), ("humidity", "H")):
            tm.append({"fold": int(r["fold"]), "held_out_subject": r["held_out_subject"], "target": tgt,
                       "mae": float(r[f"MAE_{suf}"]), "rmse": float(r[f"RMSE_{suf}"]), "bias": float(r[f"bias_{suf}"]),
                       "n_windows": int(r["test_n_windows"])})
    summary = t("p3_primary_summary.csv")
    subjects = [r["held_out_subject"] for r in t("p3_training_mean_by_fold.csv")]
    for tgt in TARGETS:
        for metric in ("mae", "rmse", "bias"):
            vals = {s: float(np.mean([r[metric] for r in outer if r["held_out_subject"] == s and r["target"] == tgt]))
                    for s in subjects}
            row = next(r for r in summary if r["model"] == "tcn_raw" and r["target"] == tgt and r["metric"] == metric)
            got = [vals[s] for s in subjects] + [unweighted_subject_mean(vals)]
            want = [float(row[s]) for s in subjects] + [float(row["unweighted_subject_mean"])]
            if not np.allclose(got, want, rtol=0, atol=1e-12):
                raise P4Error(f"P3 per-seed table does not reproduce the P3 summary ({tgt} {metric})")
    strata = []
    for r in t("p3_secondary_strata.csv"):
        strata.append({"model": REFERENCE_FAMILY if r["model"] == "tcn_raw" else TRAINING_MEAN,
                       "fold": int(r["fold"]), "seed": "mean" if r["model"] == "tcn_raw" else "",
                       "subject_id": r["subject_id"], "stratum_type": r["stratum_type"], "stratum": r["stratum"],
                       "target": r["target"], "metric": r["metric"], "value": float(r["value"]),
                       "seed_sd": float(r["seed_sd"]) if r["seed_sd"] else "", "n_windows": int(r["n_windows"]),
                       "source": "p3_frozen"})
    sel = [{**r, "family": REFERENCE_FAMILY, "n_inputs": FAMILY_DIMS[REFERENCE_FAMILY], "source": "p3_frozen"}
           for r in t("p3_selected_configs.csv")] if include_selection else []
    files = {rel: S.file_sha256_lf(root / rel) for rel in P3_REFERENCE_FILES} if include_selection else {}
    return {"outer": outer, "training_mean": tm, "strata": strata, "selected": sel, "files_sha256": files}


# ------------------------------------------------------------------------------------------------------ analysis

def err_sd(rmse: float, bias: float) -> float:
    """SD of the signed error: RMSE^2 = bias^2 + SD^2 (descriptive split of the error into offset and variation)."""
    return float(np.sqrt(max(rmse ** 2 - bias ** 2, 0.0)))


def _by_fold(outer: list[dict]) -> list[dict]:
    out = []
    keys = sorted({(r["family"], r["fold"], r["held_out_subject"]) for r in outer},
                  key=lambda k: (ALL_FAMILIES.index(k[0]), k[1]))
    for fam, f, held in keys:
        for t in TARGETS:
            rs = [r for r in outer if r["family"] == fam and r["fold"] == f and r["target"] == t]
            for metric in ("mae", "rmse", "bias", "err_sd"):
                v = np.array([r[metric] for r in rs])
                out.append({"family": fam, "fold": f, "held_out_subject": held, "target": t, "metric": metric,
                            "seed_mean": float(v.mean()), "seed_sd": float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                            "seed_min": float(v.min()), "seed_max": float(v.max()), "n_seeds": len(v)})
    return out


def _lookup(by_fold: list[dict], tm: list[dict]) -> dict[tuple, float]:
    """(model, subject, target, metric) -> seed mean (training-mean: its deterministic value)."""
    sm = {(r["family"], r["held_out_subject"], r["target"], r["metric"]): r["seed_mean"] for r in by_fold}
    for r in tm:
        for metric in ("mae", "rmse", "bias"):
            sm[(TRAINING_MEAN, r["held_out_subject"], r["target"], metric)] = r[metric]
        sm[(TRAINING_MEAN, r["held_out_subject"], r["target"], "err_sd")] = err_sd(r["rmse"], r["bias"])
    return sm


def _compare(sm: dict, a: str, b: str, subjects: list[str], extra: dict) -> list[dict]:
    rows = []
    for t in TARGETS:
        for metric in PRIMARY_METRICS:
            d = {s: sm[(a, s, t, metric)] - sm[(b, s, t, metric)] for s in subjects}
            mean_b = unweighted_subject_mean({s: sm[(b, s, t, metric)] for s in subjects})
            delta = unweighted_subject_mean(d)
            rows.append({**extra, "first": a, "second": b, "target": t, "metric": metric,
                         **{f"delta_{s}": d[s] for s in subjects}, "delta_unweighted_mean": delta,
                         "relative_delta_unweighted_mean": delta / mean_b,
                         "improved_subjects": int(sum(v < 0 for v in d.values())),
                         "worse_subjects": int(sum(v > 0 for v in d.values())), "n_subjects": len(subjects)})
    return rows


def build_tables(outer: list[dict], tm: list[dict], subjects: list[str]) -> dict[str, list[dict]]:
    """All P4 comparison tables from per-seed outer results (RAW + P4 families) and the training-mean results."""
    outer = [{**r, "err_sd": err_sd(r["rmse"], r["bias"])} for r in outer]
    fams = [f for f in ALL_FAMILIES if any(r["family"] == f for r in outer)]
    if fams != list(ALL_FAMILIES):
        raise P4Error(f"families present {fams}, need {list(ALL_FAMILIES)}")
    for fam in ALL_FAMILIES:
        for s in subjects:
            n = len([r for r in outer if r["family"] == fam and r["held_out_subject"] == s])
            if n != 3 * len(TARGETS):
                raise P4Error(f"{fam} {s}: {n} per-seed rows, need 3 seeds x 2 targets")
    by_fold = _by_fold(outer)
    sm = _lookup(by_fold, tm)
    tables: dict[str, list[dict]] = {"outer_by_seed": outer, "outer_by_fold": by_fold}
    summary = []
    for t in TARGETS:
        for metric in ("mae", "rmse", "bias", "err_sd"):
            means = {m: unweighted_subject_mean({s: sm[(m, s, t, metric)] for s in subjects})
                     for m in (TRAINING_MEAN, *ALL_FAMILIES)}
            order = sorted(ALL_FAMILIES, key=lambda f: means[f])
            for m in (TRAINING_MEAN, *ALL_FAMILIES):
                summary.append({"model": m, "target": t, "metric": metric,
                                **{s: sm[(m, s, t, metric)] for s in subjects},
                                "unweighted_subject_mean": means[m],
                                "rank_among_tcn_families": (order.index(m) + 1
                                                            if m != TRAINING_MEAN and metric in PRIMARY_METRICS
                                                            else "")})
    tables["family_summary"] = summary
    vs_raw = []
    for fam in P4_FAMILIES:
        kind = "standalone representation" if "RAW" not in fam else "features added to RAW"
        vs_raw += _compare(sm, fam, REFERENCE_FAMILY, subjects, {"family": fam, "comparison_type": kind})
    tables["vs_raw"] = vs_raw
    vs_tm = []
    for fam in ALL_FAMILIES:
        for row in _compare(sm, fam, TRAINING_MEAN, subjects, {"family": fam}):
            for s in subjects:
                tm_v = sm[(TRAINING_MEAN, s, row["target"], row["metric"])]
                seeds = [r[row["metric"]] for r in outer if r["family"] == fam and r["held_out_subject"] == s
                         and r["target"] == row["target"]]
                row[f"seeds_better_{s}"] = int(sum(v < tm_v for v in seeds))
            row["all_seeds_same_side"] = all(row[f"seeds_better_{s}"] in (0, 3) for s in subjects)
            vs_tm.append(row)
    tables["vs_training_mean"] = vs_tm
    tables["incremental_effects"] = [r for eid, label, a, b in EFFECTS
                                     for r in _compare(sm, a, b, subjects, {"effect": eid, "label": label})]
    paired, consistency = [], []
    for eid, label, a, b in EFFECTS + STANDALONE:
        for t in TARGETS:
            for metric in PRIMARY_METRICS:
                ds = []
                for s in subjects:
                    for seed in (0, 1, 2):
                        va = next(r[metric] for r in outer if r["family"] == a and r["held_out_subject"] == s
                                  and r["target"] == t and r["seed"] == seed)
                        vb = next(r[metric] for r in outer if r["family"] == b and r["held_out_subject"] == s
                                  and r["target"] == t and r["seed"] == seed)
                        ds.append((s, seed, va - vb))
                        paired.append({"effect": eid, "label": label, "first": a, "second": b, "target": t,
                                       "metric": metric, "subject_id": s, "seed": seed, "first_value": va,
                                       "second_value": vb, "delta": va - vb})
                v = np.array([x[2] for x in ds])
                consistency.append({"effect": eid, "label": label, "first": a, "second": b, "target": t,
                                    "metric": metric, "improved_fold_seeds": int((v < 0).sum()),
                                    "n_fold_seeds": len(v), "mean_delta": float(v.mean()),
                                    "min_delta": float(v.min()), "max_delta": float(v.max()),
                                    **{f"improved_seeds_{s}": int(sum(x[2] < 0 for x in ds if x[0] == s))
                                       for s in subjects},
                                    "direction_consistent_all_9": bool((v < 0).all() or (v > 0).all())})
    tables["seed_paired_deltas"] = paired
    tables["seed_consistency"] = consistency
    offset = []
    for m in (TRAINING_MEAN, *ALL_FAMILIES):
        for s in subjects:
            for t in TARGETS:
                mae_v, b, e = sm[(m, s, t, "mae")], sm[(m, s, t, "bias")], sm[(m, s, t, "err_sd")]
                ref = (sm[(REFERENCE_FAMILY, s, t, "mae")], sm[(REFERENCE_FAMILY, s, t, "bias")],
                       sm[(REFERENCE_FAMILY, s, t, "err_sd")])
                offset.append({"model": m, "subject_id": s, "target": t, "mae": mae_v, "bias": b,
                               "abs_bias": abs(b), "abs_bias_over_mae": abs(b) / mae_v, "err_sd": e,
                               "delta_mae_vs_raw": mae_v - ref[0], "delta_abs_bias_vs_raw": abs(b) - abs(ref[1]),
                               "delta_err_sd_vs_raw": e - ref[2]})
    tables["bias_offset"] = offset
    return tables


def aggregate(include_selection: bool = True, p3_root: Path | None = None) -> dict[str, list[dict]]:
    """All P4 tables from complete final runs and the frozen P3 reference (fails if anything is missing).

    Public-release reproduction (D-050): include_selection=False leaves out the inner-search, selection and
    reference-provenance tables (no inner-search record); p3_root points at the reproduced P3 tables (no tag check).
    """
    cfg = load_protocol()
    folds = {int(k): v for k, v in cfg["loso"]["outer_folds"].items()}
    seeds = [int(s) for s in cfg["models"]["seeds"]]
    ref = p3_reference() if p3_root is None else p3_reference(p3_root, verify_tag=False,
                                                                 include_selection=include_selection)
    doc = frozen_selection()
    outer, strata, pooled_parts = list(ref["outer"]), [], {}
    for fam in P4_FAMILIES:
        for f, held in folds.items():
            for s in seeds:
                d = final_dir(fam, f, s)
                if run_status(d) != "complete":
                    raise P4Error(f"{fam} final fold {f} seed {s} incomplete")
                y, p, prov = _pairs(read_predictions(d / "predictions.parquet"))
                m = target_metrics(y, p)
                logged = {(r["target"], r["metric"]): float(r["value"]) for r in _read_csv(d / "metrics.csv")}
                if any(logged[(t, k)] != v for t in TARGETS for k, v in m[t].items()):
                    raise P4Error(f"{d}: predictions do not reproduce metrics.csv")
                for t in TARGETS:
                    outer.append({"family": fam, "fold": f, "held_out_subject": held, "seed": s, "target": t,
                                  "mae": m[t]["mae"], "rmse": m[t]["rmse"], "bias": m[t]["bias"],
                                  "n_windows": int(len(y)),
                                  "final_epochs": doc["families"][fam]["folds"][f]["final_epochs"], "source": "p4"})
                strata += [{**r, "model": fam, "source": "p4"} for r in strata_rows(fam, f, s, held, y, p, prov)]
                pooled_parts.setdefault((fam, s), []).append((y, p))
    n_ref = {(r["held_out_subject"]): r["n_windows"] for r in ref["training_mean"]}
    for r in outer:
        if r["n_windows"] != n_ref[r["held_out_subject"]]:
            raise P4Error(f"{r['family']} {r['held_out_subject']}: {r['n_windows']} test windows, P3 had "
                          f"{n_ref[r['held_out_subject']]}")
    tables = build_tables(outer, ref["training_mean"], list(folds.values()))
    tables["training_mean_reference"] = ref["training_mean"]
    means = _seed_mean([r for r in strata], ("model", "fold", "subject_id", "stratum_type", "stratum", "target",
                                             "metric"))
    tables["secondary_strata"] = ref["strata"] + strata + [{**r, "source": "p4"} for r in means]
    pooled = []
    for (fam, s), parts in pooled_parts.items():
        yy, pp = np.concatenate([q[0] for q in parts]), np.concatenate([q[1] for q in parts])
        for t, dd in target_metrics(yy, pp).items():
            for k, v in dd.items():
                pooled.append({"family": fam, "seed": s, "target": t, "metric": k, "value": v, "n_windows": len(yy)})
    tables["secondary_window_weighted_pooled"] = pooled
    if not include_selection:
        return tables
    inner_rows = []
    sel_rows = list(ref["selected"])
    for fam in P4_FAMILIES:
        for f in folds:
            s = json.loads(selection_path(fam, f).read_text(encoding="utf-8"))
            for g in s["grid"]:
                inner_rows.append({"family": fam, "fold": f, "held_out_subject": s["held_out_subject"], **g,
                                   "selected": int(g["config_index"] == s["selected_index"])})
            sel_rows.append({"fold": f, "held_out_subject": s["held_out_subject"],
                             "selected_index": s["selected_index"], **s["selected_config"],
                             "inner_A_criterion": s["inner"]["A"]["criterion"],
                             "inner_A_best_epoch": s["inner"]["A"]["best_epoch"],
                             "inner_B_criterion": s["inner"]["B"]["criterion"],
                             "inner_B_best_epoch": s["inner"]["B"]["best_epoch"],
                             "selection_score": s["selection_score"], "final_epochs": s["final_epochs"],
                             "family": fam, "n_inputs": s["n_inputs"], "source": "p4"})
    tables["inner_search"] = inner_rows
    tables["selected_configs"] = sel_rows
    tables["reference_provenance"] = [{"file": k, "sha256_lf": v, "p3_tag": P3_TAG}
                                      for k, v in ref["files_sha256"].items()]
    return tables


# ----------------------------------------------------------------------------------------------------- bookkeeping

def run_index() -> list[dict]:
    rows = []
    for fam in P4_FAMILIES:
        for kind in ("inner", "final"):
            base = family_root(fam) / kind
            for d in (sorted(base.glob("*")) if base.exists() else []):
                st = _status(d)
                rows.append({"family": fam, "kind": kind, "run": d.name, "status": run_status(d),
                             "attempt": st.get("attempt"), "previous_attempts": len(st.get("history", [])),
                             "run_id": st.get("run_id"), "started_at": st.get("started_at"),
                             "finished_at": st.get("finished_at")})
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


def write_tables(tables: dict[str, list[dict]]) -> Path:
    out = metrics_dir()
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r))
        write_csv(out / f"p4_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    idx = run_index()
    write_csv(out / "p4_run_index.csv", idx, list(idx[0]))
    write_json(out / "p4_outer_test_access_counts.json", outer_access_counts())
    return out
