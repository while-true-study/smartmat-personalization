"""P11: the frozen RAW-TCN retrained on the P10 common endpoints (protocol v1.5 addendum; D-066;
docs/P11_COMMON_POOL_TCN_PLAN.md; audit docs/p11_common_pool_tcn_audit.md).

Post hoc and exploratory. The only purpose is to remove the training-pool confound of P10 Part H.
- Input, architecture, hyperparameters, optimizer, seeds, metrics and bootstrap are the frozen v1.0 / v1.4 ones. The TCN
  input stays the 40-s RAW window; no 900-s sequence is ever given to it and nothing is searched.
- Inner-training, inner-validation, outer-training and test windows are restricted to the P10 common endpoints
  (labelled and with 40-, 300- and 900-s gap-free history), computed per subject by `p10_history.build_subject`.
- The epoch count is re-derived on the common pool with the unchanged v1.0 rule `p3_loso.final_epochs` from inner A and
  inner B of the fold's frozen configuration (seed 0); the target scaler is refitted on the common training pool.
- Histogram boosting and the full-pool RAW-TCN are read from the committed P10 / P3 prediction files, never refitted.
- The v1.0 gate runs before every training run and fails closed. P11 writes only under its own output root.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import yaml

from src.data import paths
from src.data.io_guard import open_for_write, write_csv, write_json, write_text
from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P5
from src.evaluation import p8_posthoc as P8
from src.evaluation import p10_history as H
from src.evaluation import p10_level_baselines as LB
from src.evaluation import splits as S
from src.evaluation.leakage import RunContext
from src.evaluation.p3_loso import now, read_predictions, run_status, sha256_file
from src.evaluation.protocol import load_protocol, protocol_sha256
from src.features.pressure_features import TargetScaler

VERSION, DECISION = "v1.5", "D-066"
HGB_HISTORIES = H.HISTORIES
TOLERANCE = 1e-9
PROTECTED_TREES = ("outputs/runs/p3", "outputs/runs/p10", "outputs/metrics/p3", "outputs/metrics/p10", "paper/tables")
METRIC_KEYS = ("mae", "rmse", "bias", "R", "Q", "r_pooled", "r_within", "r_within_mat")


class P11Error(RuntimeError):
    pass


def config_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / VERSION / "p11_common_pool_tcn.yaml"


def plan_doc() -> Path:
    return paths.PROJECT_ROOT / "docs" / "P11_COMMON_POOL_TCN_PLAN.md"


def load_config() -> dict:
    """The v1.5 config must agree with the frozen rules this module reuses (refuses any drift)."""
    doc = yaml.safe_load(config_yaml().read_text(encoding="utf-8"))
    proto = load_protocol()
    problems = []
    if doc["protocol_version"] != VERSION or doc["decision"] != DECISION:
        problems.append("version / decision")
    if list(doc["final"]["seeds"]) != P5.seeds() or int(doc["epochs"]["inner_seed"]) != int(
            proto["models"]["selection"]["seed_for_selection"]):
        problems.append("seeds")
    fixed = proto["models"]["tcn"]["fixed"]
    es = doc["epochs"]["early_stopping"]
    if (es["patience"], es["max_epochs"]) != (fixed["early_stopping_patience"], fixed["max_epochs"]):
        problems.append("early stopping")
    bt = doc["bootstrap"]
    from src.evaluation import p6_robustness as P6
    if (bt["resamples"], bt["seed"], bt["level"]) != P6.bootstrap_settings():
        problems.append("bootstrap settings")
    if doc["model"]["grid_search"] != "none" or doc["model"]["new_hyperparameters"] != "none":
        problems.append("search must stay disabled")
    if sorted(doc["subjects"]) != sorted(P5.subject_folds()):
        problems.append("subjects")
    if problems:
        raise P11Error("v1.5 config differs from the frozen rules: " + "; ".join(problems))
    return doc


def design_hashes() -> dict:
    return {"addendum_version": VERSION, "decision": DECISION, "plan_sha256_lf": S.file_sha256_lf(plan_doc()),
            "config_sha256_lf": S.file_sha256_lf(config_yaml()), "base_protocol_sha256": protocol_sha256(),
            "p10_design": LB.design_hashes()}


_OUTPUT_ROOT: Path | None = None


def set_output_root(root: Path | None) -> None:
    global _OUTPUT_ROOT
    _OUTPUT_ROOT = None if root is None else Path(root)


def output_root() -> Path:
    return _OUTPUT_ROOT if _OUTPUT_ROOT is not None else paths.PROJECT_ROOT / "outputs" / "p11_common_pool_tcn"


def inner_dir(fold: int, inner: str) -> Path:
    return output_root() / "runs" / "inner" / f"fold{fold}_{inner}"


def final_dir(fold: int, seed: int) -> Path:
    return output_root() / "runs" / "final" / f"fold{fold}_seed{seed}"


def selection_path(fold: int) -> Path:
    return output_root() / "runs" / "selection" / f"fold{fold}.json"


# ------------------------------------------------------------------------------------------------ common masks

def common_mask(fd, subjects: dict) -> np.ndarray:
    """The P10 common endpoints of every subject, scattered into the fold's window index space.

    `subjects` maps subject id -> object with `.common` (bool per 40-s endpoint of that subject, in canonical order).
    The caller must have asserted order-exact alignment (`p10_history.frozen_fold_windows_equal`)."""
    mask = np.zeros(fd.labelled.shape[0], bool)
    seen = set()
    for s, sh in subjects.items():
        idx = np.flatnonzero(fd.prov["subject_id"] == s)
        common = np.asarray(sh.common, bool)
        if idx.size != common.size:
            raise P11Error(f"{s}: {common.size} endpoints but {idx.size} fold windows")
        mask[idx[common]] = True
        seen.add(s)
    missing = set(np.unique(fd.prov["subject_id"]).tolist()) - seen
    if missing:
        raise P11Error(f"no common mask for {sorted(missing)}")
    if np.any(mask & ~fd.labelled):
        raise P11Error("a common endpoint is not labelled")
    return mask


def pools(fd, cm: np.ndarray) -> dict[str, np.ndarray]:
    """Train / test / inner masks restricted to the common endpoints; the held-out subject is only ever in `test`."""
    out = {"train": cm & (fd.partition == "train"), "test": cm & (fd.partition == "test"),
           "train_full": fd.labelled & (fd.partition == "train"), "test_full": fd.labelled & (fd.partition == "test")}
    for name in P3.INNER_SPLITS:
        out[f"inner_train_{name}"] = cm & (fd.inner[name] == "inner_train")
        out[f"inner_val_{name}"] = cm & (fd.inner[name] == "inner_val")
    held = fd.prov["subject_id"] == fd.held_out
    for k, m in out.items():
        if k.startswith("test"):
            if np.any(m & ~held):
                raise P11Error(f"{k}: a test window is not from the held-out subject")
        elif np.any(m & held):
            raise P11Error(f"{k}: the held-out subject is in a fitting or selection pool")
    return out


def build_subjects(sess, echo=print) -> dict:
    rows = sess.rows()
    out = {}
    for s in sorted(P5.subject_folds()):
        echo(f"{now()} building common endpoints of {s}")
        out[s] = H.build_subject(rows, s)
        bad = [c for c in out[s].checks if not c["passed"]]
        if bad:
            raise P11Error(f"{s}: P10 history checks failed: {bad[:3]}")
    return out


def aligned_mask(sess, fold: int, subjects: dict):
    fd = sess.fold(fold)
    for s, sh in subjects.items():
        problem = H.frozen_fold_windows_equal(sh, fd)
        if problem:
            raise P11Error(f"fold {fold} {s}: {problem}")
    return fd, common_mask(fd, subjects)


# ------------------------------------------------------------------------------------------------ training runs

def frozen_config(fold: int):
    from src.training.trainer import TCNConfig
    sel_doc = P3.frozen_selection()
    sel = sel_doc["folds"][fold]
    return TCNConfig(**sel["config"]), sel, sel_doc


def _snapshot_environment(seed: int) -> None:
    from src.training.trainer import set_determinism
    set_determinism(seed)             # so that run_meta records the flags train_tcn will use (train_tcn re-seeds)


def run_inner(sess, fold: int, inner: str, subjects: dict) -> str:
    """Inner A or B of the fold's frozen configuration on the common endpoints: yields the best epoch only."""
    import torch
    from src.training.trainer import train_tcn

    d = inner_dir(fold, inner)
    if run_status(d) == "complete":
        return "skipped (complete)"
    feats = P3.assert_p3_family(P3.P3_FAMILY)
    cfg, sel, _ = frozen_config(fold)
    seed = int(load_protocol()["models"]["selection"]["seed_for_selection"])
    run_id = P3._run_id(f"p11-inner-fold{fold}{inner}")
    P3.begin_run(d, run_id)
    log = P3.RunLog(d, sess.echo)
    try:
        fd, cm = aligned_mask(sess, fold, subjects)
        train_subj, val_subj = P3.inner_subjects(fd, inner)
        pl = pools(fd, cm)
        tr, va = pl[f"inner_train_{inner}"], pl[f"inner_val_{inner}"]
        plan = {"transform": "target_zscore", "partition": "inner_train", "subjects": [train_subj]}
        ctx = RunContext("loso", fold=fold, input_features=list(feats), fit_records=[plan],
                         selection_subjects=[val_subj], window_groups=fd.window_groups(tr | va, inner))
        _, verified = sess.gate(d, ctx)
        scaler = TargetScaler.fit(fd.targets[tr], scheme="loso", fold=str(fold), partition="inner_train",
                                  subjects=[train_subj])
        if scaler.fit_provenance["subjects"] != plan["subjects"]:
            raise P11Error("scaler provenance differs from the gated plan")
        if set(np.unique(fd.prov["subject_id"][tr])) != {train_subj} or \
                set(np.unique(fd.prov["subject_id"][va])) != {val_subj}:
            raise P11Error("inner pools are not single-subject")
        _snapshot_environment(seed)
        P3._meta(d, run_id, "p11_inner_common_pool", fold, fd.held_out, seed, cfg.as_dict(), verified,
                 {"inner_split": inner, "selected_index": sel["selected_index"], "inner_train_subject": train_subj,
                  "inner_val_subject": val_subj, "n_train_windows": int(tr.sum()), "n_val_windows": int(va.sum()),
                  "training_pool": "p10_common_endpoints",
                  "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance},
                  **design_hashes()})
        write_text(d / "config.yaml", yaml.safe_dump({"family": P3.P3_FAMILY, "fold": fold, "inner_split": inner,
                                                      "selected_index": sel["selected_index"], **cfg.as_dict(),
                                                      "seed": seed, "training_pool": "p10_common_endpoints"},
                                                     sort_keys=False))
        res = train_tcn(cfg, fd.pressure[tr], fd.targets[tr], scaler, seed, pressure_va=fd.pressure[va],
                        y_va=fd.targets[va], log=log)
        write_csv(d / "history.csv", res.history, list(res.history[0]))
        with open_for_write(d / "best_model.pt", "wb") as fh:
            torch.save(res.model.state_dict(), fh)
        best = res.history[res.best_epoch - 1]
        write_json(d / "result.json", {"fold": fold, "inner_split": inner, "best_epoch": res.best_epoch,
                                       "best_criterion": res.best_score,
                                       "val_mae_temperature": best["val_mae_temperature"],
                                       "val_mae_humidity": best["val_mae_humidity"], "epochs_run": res.epochs_run,
                                       "seconds": round(res.seconds, 1), "n_train_windows": int(tr.sum()),
                                       "n_val_windows": int(va.sum()), "inner_train_subject": train_subj,
                                       "inner_val_subject": val_subj})
        P3._finish_meta(d, best_epoch=res.best_epoch, best_criterion=res.best_score, epochs_run=res.epochs_run)
        P3.complete_run(d, ["config.yaml", "run_meta.json", "leakage_check.json", "history.csv", "best_model.pt",
                            "result.json"])
        return "complete"
    except BaseException as exc:
        P3.fail_run(d, exc)
        raise


def freeze_epochs(fold: int) -> dict:
    """Final epoch count of the fold from its two complete inner runs; immutable once written."""
    p = selection_path(fold)
    res = {}
    for inner in P3.INNER_SPLITS:
        d = inner_dir(fold, inner)
        if run_status(d) != "complete":
            raise P11Error(f"fold {fold} inner {inner} is not complete")
        res[inner] = json.loads((d / "result.json").read_text(encoding="utf-8"))
    _, sel, _ = frozen_config(fold)
    rec = {"fold": fold, "held_out_subject": sel["held_out_subject"], "selected_index": sel["selected_index"],
           "config": sel["config"], "inner_best_epochs": {k: int(v["best_epoch"]) for k, v in res.items()},
           "inner_best_criterion": {k: float(v["best_criterion"]) for k, v in res.items()},
           "final_epochs": P3.final_epochs(int(res["A"]["best_epoch"]), int(res["B"]["best_epoch"])),
           "final_epochs_rule": "round_half_up(mean(inner A, inner B best epoch)) [p3_loso.final_epochs, unchanged]",
           "full_pool_final_epochs": int(sel["final_epochs"]),
           "full_pool_inner_best_epochs": sel.get("inner_best_epochs"), "training_pool": "p10_common_endpoints",
           **design_hashes()}
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
        if any(old[k] != rec[k] for k in ("inner_best_epochs", "final_epochs", "config")):
            raise P11Error(f"fold {fold}: a frozen P11 epoch selection exists and differs")
        return old
    rec["frozen_at"] = now()
    write_json(p, rec)
    return rec


def log_test_access(fold: int, seed: int, run_id: str, epochs: int) -> None:
    with open_for_write(output_root() / "test_access.jsonl", "a") as fh:
        fh.write(json.dumps({"at": now(), "fold": fold, "seed": seed, "model": "tcn_raw_common_pool",
                             "run_id": run_id, "final_epochs": epochs, **design_hashes()}) + "\n")


def run_final(sess, fold: int, seed: int, subjects: dict) -> str:
    import torch
    from src.training.trainer import device, predict_z, to_tensor, train_tcn

    d = final_dir(fold, seed)
    if run_status(d) == "complete":
        return "skipped (complete)"
    if not selection_path(fold).exists():
        raise P11Error(f"fold {fold}: the epoch count is not frozen; no test access before that")
    epochs_rec = json.loads(selection_path(fold).read_text(encoding="utf-8"))
    cfg, sel, sel_doc = frozen_config(fold)
    if seed not in sel_doc["final_seeds"]:
        raise P11Error(f"seed {seed} is not a declared final seed")
    if epochs_rec["config"] != sel["config"]:
        raise P11Error("the frozen configuration changed after the P11 epoch selection")
    feats = P3.assert_p3_family(sel_doc["family"])
    epochs = int(epochs_rec["final_epochs"])
    run_id = P3._run_id(f"p11-final-fold{fold}-seed{seed}")
    P3.begin_run(d, run_id)
    log = P3.RunLog(d, sess.echo)
    try:
        fd, cm = aligned_mask(sess, fold, subjects)
        if fd.held_out != sel["held_out_subject"]:
            raise P11Error("held-out subject differs from the frozen selection")
        pl = pools(fd, cm)
        tr, te = pl["train"], pl["test"]
        plan = {"transform": "target_zscore", "partition": "train", "subjects": fd.train_subjects}
        ctx = RunContext("loso", fold=fold, input_features=list(feats), fit_records=[plan], selection_subjects=[],
                         window_groups=fd.window_groups(tr | te))
        _, verified = sess.gate(d, ctx)
        scaler = TargetScaler.fit(fd.targets[tr], scheme="loso", fold=str(fold), partition="train",
                                  subjects=fd.train_subjects)
        if sorted(np.unique(fd.prov["subject_id"][tr]).tolist()) != sorted(fd.train_subjects):
            raise P11Error("the common training pool does not consist of exactly the source subjects")
        _snapshot_environment(seed)
        P3._meta(d, run_id, "p11_final_common_pool", fold, fd.held_out, seed, cfg.as_dict(), verified,
                 {"selected_index": sel["selected_index"], "final_epochs": epochs,
                  "full_pool_final_epochs": int(sel["final_epochs"]), "train_subjects": fd.train_subjects,
                  "n_train_windows": int(tr.sum()), "n_train_windows_full_pool": int(pl["train_full"].sum()),
                  "n_test_windows": int(te.sum()), "training_pool": "p10_common_endpoints",
                  "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance},
                  **design_hashes()})
        write_text(d / "config.yaml", yaml.safe_dump({"family": P3.P3_FAMILY, "fold": fold, "seed": seed,
                                                      "selected_index": sel["selected_index"], **cfg.as_dict(),
                                                      "epochs": epochs, "training_pool": "p10_common_endpoints"},
                                                     sort_keys=False))
        res = train_tcn(cfg, fd.pressure[tr], fd.targets[tr], scaler, seed, epochs=epochs, log=log)
        write_csv(d / "history.csv", res.history, list(res.history[0]))
        with open_for_write(d / "model.pt", "wb") as fh:
            torch.save(res.model.state_dict(), fh)
        log_test_access(fold, seed, run_id, epochs)                      # the single test look of this model
        pred = scaler.inverse(predict_z(res.model, to_tensor(fd.pressure[te], device())))
        m = P3.write_metrics(d / "metrics.csv", run_id, fold, fd.held_out, fd.targets[te], pred)
        P3.write_predictions(d / "predictions.parquet", run_id, "tcn_raw_common_pool", fold, seed, fd.prov, te,
                             fd.targets[te], pred)
        P3._finish_meta(d, epochs_run=res.epochs_run, train_seconds=round(res.seconds, 1), test_metrics=m,
                        weights_sha256=P5.weights_digest(res.model.state_dict()))
        log(f"fold {fold} seed {seed}: {json.dumps(m)}")
        P3.complete_run(d, ["config.yaml", "run_meta.json", "leakage_check.json", "history.csv", "model.pt",
                            "metrics.csv", "predictions.parquet"])
        return "complete"
    except BaseException as exc:
        P3.fail_run(d, exc)
        raise


# ------------------------------------------------------------------------------------------------ evaluation

def snapshot_protected() -> dict[str, str]:
    """SHA-256 of every existing P3 / P10 output and paper table (to prove P11 changed none of them)."""
    out = {}
    for tree in PROTECTED_TREES:
        root = paths.PROJECT_ROOT / tree
        for p in sorted(root.rglob("*")):
            if p.is_file():
                out[p.relative_to(paths.PROJECT_ROOT).as_posix()] = sha256_file(p)
    return out


def comparison_pairs(seeds: list[int]) -> list[tuple[str, str, str]]:
    out = []
    for s in seeds:
        out += [("training_mean_common", f"raw_tcn_common_seed{s}", "level_baseline_vs_common_pool_tcn"),
                ("training_median_common", f"raw_tcn_common_seed{s}", "level_baseline_vs_common_pool_tcn"),
                (f"raw_tcn_common_seed{s}", "hgb_h40", "same_pool_same_history_two_pipelines"),
                (f"raw_tcn_full_seed{s}", f"raw_tcn_common_seed{s}", "training_pool_restriction")]
    out += [("hgb_h40", f"hgb_h{h}", "longer_history") for h in HGB_HISTORIES[1:]]
    return out


def _read_csv(p: Path) -> list[dict]:
    import csv
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _close(a, b) -> bool:
    a, b = float(a), float(b)
    return (np.isnan(a) and np.isnan(b)) or abs(a - b) <= TOLERANCE


def case_of(n_subjects: int) -> str:
    return "A" if n_subjects == 0 else "B" if n_subjects == 1 else "C"


def interpretation(boot: list[dict], subjects: list[str]) -> list[dict]:
    """Plan §5, applied mechanically: seed-0 intervals against both common-pool constants above zero."""
    side = {(r["subject_id"], r["target"], r["first"], r["second"]): r for r in boot}
    out = []
    for t in H.TARGETS:
        hits = []
        for s in subjects:
            a = side[(s, t, "training_mean_common", "raw_tcn_common_seed0")]
            b = side[(s, t, "training_median_common", "raw_tcn_common_seed0")]
            ok = a["ci_lower"] > 0 and b["ci_lower"] > 0
            hits.append(ok)
            out.append({"target": t, "subject_id": s, "mean_minus_tcn": a["point_estimate"],
                        "mean_ci_lower": a["ci_lower"], "mean_ci_upper": a["ci_upper"],
                        "median_minus_tcn": b["point_estimate"], "median_ci_lower": b["ci_lower"],
                        "median_ci_upper": b["ci_upper"], "exceeds_level_baselines": bool(ok), "case": ""})
        out.append({"target": t, "subject_id": "ALL", "exceeds_level_baselines": int(sum(hits)),
                    "case": case_of(int(sum(hits)))})
    return out


def evaluate(sess, subjects: dict, before: dict[str, str], timings: list[dict], echo=print) -> tuple[dict, dict]:
    seeds = P5.seeds()
    p10_metrics = _read_csv(paths.PROJECT_ROOT / "outputs" / "metrics" / "p10" / "p10_history_metrics.csv")
    p10_boot = _read_csv(paths.PROJECT_ROOT / "outputs" / "metrics" / "p10" / "p10_history_bootstrap.csv")
    p10_prov = json.loads((paths.PROJECT_ROOT / "outputs" / "metrics" / "p10" / "p10_history_provenance.json")
                          .read_text(encoding="utf-8"))
    tables: dict[str, list[dict]] = {"counts": [], "epochs": [], "per_seed": [], "comparison": [], "bootstrap": []}
    val: dict = {"checks": [], "folds": {}}

    def check(name: str, passed: bool, detail: str = "ok") -> None:
        val["checks"].append({"check": name, "passed": bool(passed), "detail": detail})

    all_metrics: list[dict] = []
    for fold, held in sorted({int(k): v for k, v in load_protocol()["loso"]["outer_folds"].items()}.items()):
        fd, cm = aligned_mask(sess, fold, subjects)
        pl = pools(fd, cm)
        tr, te = pl["train"], pl["test"]
        y_te = fd.targets[te]
        prov_te = {k: v[te] for k, v in fd.prov.items()}
        keys_te = P8.window_keys(prov_te["device_id"], prov_te["window_start"])
        nights, mats = prov_te["night_id"].astype(str), prov_te["device_id"].astype(str)
        sel = json.loads(selection_path(fold).read_text(encoding="utf-8"))

        # ---- counts
        n_full, n_common = int(pl["train_full"].sum()), int(tr.sum())
        rec = {"fold": fold, "held_out_subject": held, "source_subjects": "+".join(fd.train_subjects),
               "full_source_endpoints": n_full, "common_source_endpoints": n_common,
               "retention_percent": 100.0 * n_common / n_full, "full_test_endpoints": int(pl["test_full"].sum()),
               "common_test_endpoints": int(te.sum()),
               "test_retention_percent": 100.0 * int(te.sum()) / int(pl["test_full"].sum()),
               "test_nights_common": int(np.unique(nights).size),
               "test_nights_full": int(np.unique(fd.prov["night_id"][pl["test_full"]]).size),
               "source_nights_common": int(np.unique(fd.prov["night_id"][tr].astype(str)
                                                      + "|" + fd.prov["subject_id"][tr].astype(str)).size)}
        for s in fd.train_subjects:
            m = fd.prov["subject_id"] == s
            rec[f"common_{s}"], rec[f"full_{s}"] = int((tr & m).sum()), int((pl["train_full"] & m).sum())
        tables["counts"].append(rec)
        check(f"fold{fold}_common_training_count_equals_p10", n_common == int(p10_prov["folds"][str(fold)]
                                                                               ["n_train_common"]),
              f"{n_common} vs {p10_prov['folds'][str(fold)]['n_train_common']}")
        check(f"fold{fold}_common_test_count_equals_p10", int(te.sum()) == int(p10_prov["folds"][str(fold)]
                                                                               ["n_test_common"]))

        # ---- epoch selection rows
        for inner in P3.INNER_SPLITS:
            r = json.loads((inner_dir(fold, inner) / "result.json").read_text(encoding="utf-8"))
            tables["epochs"].append({
                "fold": fold, "held_out_subject": held, "inner_split": inner,
                "inner_train_subject": r["inner_train_subject"], "inner_val_subject": r["inner_val_subject"],
                "n_inner_train_common": r["n_train_windows"], "n_inner_val_common": r["n_val_windows"],
                "selected_epoch": r["best_epoch"], "epochs_run": r["epochs_run"],
                "validation_metric": r["best_criterion"], "val_mae_temperature": r["val_mae_temperature"],
                "val_mae_humidity": r["val_mae_humidity"], "final_refit_epoch": sel["final_epochs"],
                "selection_rule": sel["final_epochs_rule"],
                "full_pool_inner_best_epoch": (sel.get("full_pool_inner_best_epochs") or {}).get(inner, ""),
                "full_pool_final_epoch": sel["full_pool_final_epochs"], "config": json.dumps(sel["config"],
                                                                                           sort_keys=True)})
            check(f"fold{fold}_{inner}_held_out_not_in_inner", held not in (r["inner_train_subject"],
                                                                           r["inner_val_subject"]))

        preds: dict[str, np.ndarray] = {}
        # ---- committed P10 predictions: key and target equality, HGB read not refitted
        for family in H.FAMILIES:
            for h in H.HISTORIES:
                f = paths.PROJECT_ROOT / "outputs" / "runs" / "p10" / "history" / f"fold{fold}" / f"{family}_h{h}" \
                    / "predictions.parquet"
                ys, ps, pv = LB.strict_pairs(read_predictions(f))
                kk = P8.window_keys(pv["device_id"], pv["window_start"])
                same = bool(np.array_equal(kk, keys_te)) and bool(np.array_equal(ys, y_te))
                check(f"fold{fold}_{family}_h{h}_keys_and_targets_equal_p10", same)
                if not same:
                    raise P11Error(f"fold {fold}: P11 common test endpoints differ from P10 {family} h{h}")
                if family == "hgb":
                    preds[f"hgb_h{h}"] = ps
        if np.unique(keys_te).size != keys_te.size:
            raise P11Error("duplicate endpoint keys")

        # ---- constants on the common source pool
        c = LB.constants(fd.targets[tr])
        preds["training_mean_common"] = np.tile(c["mean"], (y_te.shape[0], 1))
        preds["training_median_common"] = np.tile(c["median"], (y_te.shape[0], 1))

        # ---- TCN: full pool (frozen P3 predictions, key join) and common pool (P11 runs)
        weights = []
        for s in seeds:
            ys, ps, pv = LB.strict_pairs(read_predictions(P3.final_dir(fold, s) / "predictions.parquet"))
            pos = {k: i for i, k in enumerate(P8.window_keys(pv["device_id"], pv["window_start"]).tolist())}
            ii = np.array([pos[k] for k in keys_te.tolist()], np.int64)
            if not np.array_equal(ys[ii], y_te):
                raise P11Error(f"fold {fold} seed {s}: frozen TCN targets differ on the common endpoints")
            preds[f"raw_tcn_full_seed{s}"] = ps[ii]
            d = final_dir(fold, s)
            if run_status(d) != "complete":
                raise P11Error(f"P11 final fold {fold} seed {s} not complete")
            ys, ps, pv = LB.strict_pairs(read_predictions(d / "predictions.parquet"))
            kk = P8.window_keys(pv["device_id"], pv["window_start"])
            if not (np.array_equal(kk, keys_te) and np.array_equal(ys, y_te)):
                raise P11Error(f"fold {fold} seed {s}: P11 predictions are not on the common test endpoints")
            preds[f"raw_tcn_common_seed{s}"] = ps
            meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
            weights.append(meta["weights_sha256"])
            check(f"fold{fold}_seed{s}_scaler_fit_on_source_training_only",
                  sorted(meta["scaler"]["subjects"]) == sorted(fd.train_subjects)
                  and meta["scaler"]["partition"] == "train" and held not in meta["scaler"]["subjects"]
                  and int(meta["scaler"]["n"]) == n_common, json.dumps(meta["scaler"]["subjects"]))
            check(f"fold{fold}_seed{s}_deterministic_flags", bool(meta["deterministic_algorithms"]))
            check(f"fold{fold}_seed{s}_epochs_equal_frozen_selection", int(meta["epochs_run"]) == sel["final_epochs"])
        check(f"fold{fold}_seeds_give_distinct_models", len(set(weights)) == len(seeds))
        check(f"fold{fold}_seeds_give_distinct_predictions",
              not np.array_equal(preds["raw_tcn_common_seed0"], preds["raw_tcn_common_seed1"])
              and not np.array_equal(preds["raw_tcn_common_seed1"], preds["raw_tcn_common_seed2"]))
        check(f"fold{fold}_common_scaler_differs_from_full_pool_scaler", True,
              "refitted on the common pool by construction (run_meta.scaler.n == common count)")

        # ---- metrics
        rows = []
        for label in ("training_mean_common", "training_median_common"):
            rows += H.metric_row(fold, held, label, "", "", y_te, preds[label], nights, mats, train_pool="common",
                                 n_train_windows=n_common)
        for h in HGB_HISTORIES:
            rows += H.metric_row(fold, held, "hgb", h, "", y_te, preds[f"hgb_h{h}"], nights, mats,
                                 train_pool="common", n_train_windows=n_common)
        for s in seeds:
            rows += H.metric_row(fold, held, "raw_tcn_full", H.ENDPOINT_S, s, y_te, preds[f"raw_tcn_full_seed{s}"],
                                 nights, mats, train_pool="full_40s_labelled", n_train_windows=n_full)
            rows += H.metric_row(fold, held, "raw_tcn_common", H.ENDPOINT_S, s, y_te,
                                 preds[f"raw_tcn_common_seed{s}"], nights, mats, train_pool="common",
                                 n_train_windows=n_common, final_epochs=sel["final_epochs"])
        all_metrics += rows

        # ---- regression against the committed P10 tables (values are read, never replaced)
        p10_of = {(r["subject_id"], r["target"], r["predictor"], r["history_s"], r["seed"]): r for r in p10_metrics}
        bad = []
        for r in rows:
            name = {"raw_tcn_full": "raw_tcn"}.get(r["predictor"], r["predictor"])
            if r["predictor"] == "raw_tcn_common":
                continue
            ref = p10_of.get((held, r["target"], name, str(r["history_s"]), str(r["seed"])))
            if ref is None or not all(_close(r[k], ref[k]) for k in ("mae", "rmse", "bias")):
                bad.append((name, r["history_s"], r["seed"], r["target"]))
        check(f"fold{fold}_hgb_constants_and_full_pool_tcn_metrics_equal_p10_tables", not bad, str(bad[:4]))

        # ---- bootstrap (the P10 rule, unchanged)
        brows = H.bootstrap_rows(fold, held, y_te, preds, nights, comparison_pairs(seeds))
        for r in brows:
            seed_tag = [p for p in (r["first"], r["second"]) if "_seed" in p]
            r["seed"] = int(seed_tag[0].rsplit("_seed", 1)[1]) if seed_tag else ""
            r["primary"] = int(r["seed"] in ("", 0))
        tables["bootstrap"] += brows
        ref = {(r["subject_id"], r["target"], r["first"], r["second"]): r for r in p10_boot}
        bad = [(r["first"], r["second"], r["target"]) for r in brows if r["role"] == "longer_history" and not all(
            _close(r[k], ref[(held, r["target"], r["first"], r["second"])][k])
            for k in ("point_estimate", "ci_lower", "ci_upper"))]
        check(f"fold{fold}_hgb_history_bootstrap_equals_p10_table", not bad, str(bad))
        val["folds"][fold] = {"held_out": held, "n_test": int(te.sum()), "n_train_common": n_common,
                              "constants": {k: v.tolist() for k, v in c.items()}, "final_epochs": sel["final_epochs"]}
        echo(f"{now()} fold {fold} evaluated")

    # ---- tables
    tcn = [r for r in all_metrics if r["predictor"] == "raw_tcn_common"]
    rename = {"mae": "MAE", "rmse": "RMSE", "bias": "bias", "R": "R", "Q": "Q", "r_pooled": "r_pooled",
              "r_within": "r_within_night", "r_within_mat": "r_within_night_mat"}
    tables["per_seed"] = [{"fold": r["fold"], "subject": r["subject_id"], "target": r["target"], "seed": r["seed"],
                           **{rename[k]: r[k] for k in METRIC_KEYS}, "target_sd": r["target_sd"],
                           "n_windows": r["n_windows"], "n_nights": r["n_nights"],
                           "n_train_windows": r["n_train_windows"], "final_epochs": r["final_epochs"]} for r in tcn]
    tables["seed_mean"] = []
    for r in H.seed_mean(tcn):
        sds = [x["mae"] for x in tcn if (x["subject_id"], x["target"]) == (r["subject_id"], r["target"])]
        tables["seed_mean"].append({"fold": r["fold"], "subject": r["subject_id"], "target": r["target"],
                                    "n_seeds": len(sds), **{rename[k]: r[k] for k in METRIC_KEYS},
                                    "MAE_seed_min": r["mae_seed_min"], "MAE_seed_max": r["mae_seed_max"],
                                    "MAE_seed_sd": float(np.std(sds, ddof=1)), "n_windows": r["n_windows"],
                                    "n_nights": r["n_nights"], "n_train_windows": r["n_train_windows"]})
    means = {("raw_tcn_common", r["subject_id"], r["target"]): r for r in H.seed_mean(tcn)}
    means.update({("raw_tcn_full", r["subject_id"], r["target"]): r
                  for r in H.seed_mean([x for x in all_metrics if x["predictor"] == "raw_tcn_full"])})
    label = {"training_mean_common": "mean_common", "training_median_common": "median_common",
             "raw_tcn_common": "tcn_common_40s_seed_mean", "raw_tcn_full": "tcn_full_40s_seed_mean"}
    for r in all_metrics:
        if r["predictor"] in ("raw_tcn_common", "raw_tcn_full"):
            continue
        name = label.get(r["predictor"], f"hgb_{r['history_s']}s")
        tables["comparison"].append({"subject": r["subject_id"], "target": r["target"], "model": name,
                                     "train_pool": r["train_pool"], "n_train_windows": r["n_train_windows"],
                                     "MAE": r["mae"], "RMSE": r["rmse"], "bias": r["bias"], "MAE_seed_min": "",
                                     "MAE_seed_max": "", "n_windows": r["n_windows"], "n_nights": r["n_nights"]})
    for (pred, s, t), r in means.items():
        tables["comparison"].append({"subject": s, "target": t, "model": label[pred], "train_pool": r["train_pool"],
                                     "n_train_windows": r["n_train_windows"], "MAE": r["mae"], "RMSE": r["rmse"],
                                     "bias": r["bias"], "MAE_seed_min": r["mae_seed_min"],
                                     "MAE_seed_max": r["mae_seed_max"], "n_windows": r["n_windows"],
                                     "n_nights": r["n_nights"]})
    order = ["mean_common", "median_common", "tcn_common_40s_seed_mean", "tcn_full_40s_seed_mean", "hgb_40s",
             "hgb_300s", "hgb_900s"]
    tables["comparison"].sort(key=lambda r: (r["target"] != "temperature", r["subject"], order.index(r["model"])))
    subjects_sorted = sorted(P5.subject_folds())
    tables["interpretation"] = interpretation([r for r in tables["bootstrap"]], subjects_sorted)
    tables["runs"] = timings

    # ---- leakage / integrity summary
    after = snapshot_protected()
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    check("existing_p3_p10_outputs_and_paper_tables_unchanged", not changed, str(changed[:5]))
    val["n_protected_files"] = len(before)
    val["passed"] = all(c["passed"] for c in val["checks"])
    return tables, val


def write_outputs(tables: dict[str, list[dict]], val: dict, prov: dict) -> Path:
    out = output_root()
    names = {"counts": "common_pool_counts.csv", "epochs": "common_pool_epoch_selection.csv",
             "per_seed": "common_pool_tcn_per_seed.csv", "seed_mean": "common_pool_tcn_seed_mean.csv",
             "comparison": "common_pool_model_comparison.csv", "bootstrap": "common_pool_bootstrap.csv",
             "interpretation": "common_pool_interpretation.csv", "runs": "common_pool_runs.csv"}
    for key, fname in names.items():
        rows = tables.get(key, [])
        cols = list(dict.fromkeys(k for r in rows for k in r)) or ["none"]
        write_csv(out / fname, [{c: r.get(c, "") for c in cols} for r in rows], cols)
    write_json(out / "validation.json", val)
    write_json(out / "provenance.json", prov)
    return out


def run(sess, echo=print) -> tuple[dict, dict, dict]:
    load_config()
    H.load_history_config()
    before = snapshot_protected()
    started = time.time()
    subjects = build_subjects(sess, echo)
    timings = []
    folds = sorted(int(k) for k in load_protocol()["loso"]["outer_folds"])
    for fold in folds:
        for inner in P3.INNER_SPLITS:
            t0 = time.time()
            status = run_inner(sess, fold, inner, subjects)
            timings.append({"kind": "inner", "fold": fold, "inner_split": inner, "seed": 0, "status": status,
                            "wall_seconds": round(time.time() - t0, 1)})
            echo(f"{now()} fold {fold} inner {inner}: {status}")
        rec = freeze_epochs(fold)
        echo(f"{now()} fold {fold}: inner best epochs {rec['inner_best_epochs']} -> final {rec['final_epochs']} "
             f"(full pool: {rec['full_pool_final_epochs']})")
    for fold in folds:
        for seed in P5.seeds():
            t0 = time.time()
            status = run_final(sess, fold, seed, subjects)
            timings.append({"kind": "final", "fold": fold, "inner_split": "", "seed": seed, "status": status,
                            "wall_seconds": round(time.time() - t0, 1)})
            echo(f"{now()} fold {fold} seed {seed}: {status}")
    tables, val = evaluate(sess, subjects, before, timings, echo)
    from src.training.trainer import environment
    prov = {"generated_at": now(), **design_hashes(), **P3.frozen_inputs(), **P5.p5_git_state(),
            "environment": environment(), "n_training_runs": len(timings),
            "total_wall_seconds": round(time.time() - started, 1),
            "prediction_files_sha256": {f"fold{f}_seed{s}": sha256_file(final_dir(f, s) / "predictions.parquet")
                                        for f in folds for s in P5.seeds()},
            "validation_passed": val["passed"]}
    return tables, val, prov
