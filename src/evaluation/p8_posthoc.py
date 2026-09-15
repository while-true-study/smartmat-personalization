"""P8 post-hoc validation analyses (protocol v1.1 addendum; D-057; docs/P8_POSTHOC_VALIDATION_PLAN.md).

Post hoc: designed after the P3–P6 results and the P8 manuscript draft were seen. Nothing here replaces a v1.0 primary
result, and no P3–P6 artifact is modified. On the RQ2 windows of each subject (primary span = nights >= 16):
- A. calibration comparators — A training mean (P3 outer training pool), B = A + c_b (= the adaptation-target mean),
  C RAW-TCN base (frozen P3 checkpoint), D = C + c_b, E the frozen P5 full fine-tuning; with
  c_b = mean over the labelled adaptation windows of budget b of (y − f(x)). User02: one offset over both mats
  (primary) and one per mat (post-hoc per-device calibration diagnostic);
- B. residual variation — MAE, RMSE, bias = mean(ŷ − y), target SD, error SD (population SDs, ddof = 0; equal to
  √(RMSE² − bias²) of `p5_personalization.err_sd`) and R = error SD / target SD, a descriptive ratio (not explained
  variance);
- C. initialization control S (b = 14) — the fold's RAW-TCN architecture, randomly initialised, trained on nights
  1–14 with the frozen fine-tuning recipe (only the initialisation differs from E), evaluated on nights >= 16;
plus night-level paired bootstrap comparisons with the frozen P6 settings and the pre-registered case map (§8).
Offsets and the control's training data come only from adaptation windows. Every calibration budget and every control
run passes the v1.0 leakage gate and explicit addendum checks first (fail closed).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

from src.data import paths
from src.data.io_guard import open_for_write, write_csv, write_json, write_text
from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P5
from src.evaluation import p6_robustness as P6
from src.evaluation import splits as S
from src.evaluation.leakage import RunContext
from src.evaluation.metrics import TARGETS, bias, mae, rmse, target_metrics
from src.evaluation.p3_loso import (RunLog, begin_run, complete_run, fail_run, frozen_inputs, now, read_predictions,
                                    run_status, sha256_file)
from src.evaluation.protocol import load_protocol, protocol_sha256
from src.features.pressure_features import RAW_FEATURES

ADDENDUM_VERSION = "v1.1"
LABELS = {"A": "training_mean", "B": "adaptation_target_mean", "C": "raw_tcn_base", "D": "raw_tcn_bias_calibrated",
          "E": "full_fine_tuning", "S": "scratch_initialization_control"}
DETERMINISTIC = ("A", "B")
CALIBRATED = ("B", "D")
USER02, MATS = "User02", ("22480", "22482")
CONTROL_BUDGET = 14
COMPARISONS_ALL = (("D", "E"), ("B", "E"), ("B", "D"))
COMPARISONS_CONTROL = (("S", "E"), ("B", "S"))
IDENTITY_TOL = 1e-9
CONSISTENCY_TOL = 1e-9


class P8Error(RuntimeError):
    pass


class NotEstimable(P8Error):
    """A calibration offset without any labelled adaptation window (reported as not estimable; no fallback)."""


# ---------------------------------------------------------------------------------------------- design / paths

def plan_doc() -> Path:
    return paths.PROJECT_ROOT / "docs" / "P8_POSTHOC_VALIDATION_PLAN.md"


def addendum_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / ADDENDUM_VERSION / "posthoc_validation.yaml"


def load_addendum() -> dict:
    """The v1.1 addendum, checked against the frozen v1.0 protocol it builds on (refuses any drift)."""
    doc = yaml.safe_load(addendum_yaml().read_text(encoding="utf-8"))
    pz = load_protocol()["personalization"]
    problems = []
    if doc.get("protocol_version") != ADDENDUM_VERSION or doc.get("decision") != "D-057":
        problems.append("addendum version/decision")
    if doc["base_protocol"]["sha256"] != protocol_sha256():
        problems.append("v1.0 protocol file differs from the hash the addendum builds on")
    if doc["subjects"] != sorted(P5.subject_folds()) or doc["budgets_nights"] != P5.budgets() or \
            doc["seeds"] != P5.seeds():
        problems.append("subjects/budgets/seeds differ from v1.0")
    if doc["primary_test_from_ordinal"] != int(pz["primary_test_from_ordinal"]):
        problems.append("primary span differs from v1.0")
    cal = doc["calibration"]
    if cal["optimisation"] != "none" or cal["uses_test_labels"] or cal["refit_scaler"] or \
            cal["user02_per_mat_supplement"]["mats"] != list(MATS):
        problems.append("calibration rule differs from the plan")
    ic = doc["initialization_control"]
    if ic["budget_nights"] != CONTROL_BUDGET or ic["init"] != "random" or ic["seeds"] != P5.seeds():
        problems.append("initialization control differs from the plan")
    resamples, seed, level = P6.bootstrap_settings()
    bt = doc["bootstrap"]
    if (bt["resamples"], bt["seed"], bt["level"], bt["primary_model_seed"]) != (resamples, seed, level,
                                                                                 P6.PRIMARY_SEED):
        problems.append("bootstrap settings differ from v1.0 / P6")
    if [tuple(c) for c in doc["comparisons"]["all_budgets"]] != list(COMPARISONS_ALL) or \
            [tuple(c) for c in doc["comparisons"]["budget_14"]] != list(COMPARISONS_CONTROL):
        problems.append("comparisons differ from the plan")
    if problems:
        raise P8Error("v1.1 addendum check failed: " + "; ".join(problems))
    return doc


def design_hashes() -> dict:
    return {"addendum_version": ADDENDUM_VERSION, "decision": "D-057",
            "plan_sha256_lf": S.file_sha256_lf(plan_doc()), "addendum_sha256_lf": S.file_sha256_lf(addendum_yaml()),
            "base_protocol_sha256": protocol_sha256()}


_OUTPUT_ROOT: Path | None = None


def set_output_root(root: Path | None) -> None:
    """Redirect runs and metrics (clean reproduction into a separate directory); None = outputs/."""
    global _OUTPUT_ROOT
    _OUTPUT_ROOT = None if root is None else Path(root)


def output_root() -> Path:
    return _OUTPUT_ROOT if _OUTPUT_ROOT is not None else paths.PROJECT_ROOT / "outputs"


def run_root() -> Path:
    return output_root() / "runs" / "p8_posthoc"


def metrics_dir() -> Path:
    return output_root() / "metrics" / "p8_posthoc"


def control_dir(subject: str, seed: int) -> Path:
    return run_root() / "init_control" / subject / f"b{CONTROL_BUDGET:02d}_seed{seed}"


def calibration_dir(subject: str, budget: int) -> Path:
    return run_root() / "calibration" / subject / f"b{budget:02d}"


def log_test_access(analysis: str, subject: str, budget: int, seed: int | None, run_id: str) -> None:
    with open_for_write(run_root() / "test_access.jsonl", "a") as fh:
        fh.write(json.dumps({"at": now(), "analysis": analysis, "subject": subject, "budget": budget, "seed": seed,
                             "run_id": run_id, **design_hashes()}) + "\n")


# ------------------------------------------------------------------------------------------------ pure helpers

def calibration_offset(y_fit: np.ndarray, p_fit: np.ndarray) -> np.ndarray:
    """c = mean over the fit windows of (y − prediction), per target. No optimisation, no hyperparameter."""
    y, p = np.asarray(y_fit, np.float64), np.asarray(p_fit, np.float64)
    if y.ndim != 2 or y.shape != p.shape or y.shape[1] != 2:
        raise ValueError("expected matching (n, 2) arrays")
    if y.shape[0] == 0:
        raise NotEstimable("no labelled adaptation window")
    if not (np.all(np.isfinite(y)) and np.all(np.isfinite(p))):
        raise P8Error("non-finite adaptation targets or predictions")
    return (y - p).mean(axis=0)


def residual_stats(y: np.ndarray, p: np.ndarray) -> dict[str, dict[str, float]]:
    """Per target: MAE, RMSE, bias = mean(ŷ − y), target SD, error SD (both population SDs) and R."""
    y, p = np.asarray(y, np.float64), np.asarray(p, np.float64)
    if y.shape != p.shape or y.ndim != 2 or y.shape[1] != 2 or y.shape[0] == 0:
        raise ValueError("expected matching non-empty (n, 2) arrays")
    out = {}
    for i, t in enumerate(TARGETS):
        e = p[:, i] - y[:, i]
        tsd, esd = float(np.std(y[:, i])), float(np.std(e))
        out[t] = {"mae": mae(y[:, i], p[:, i]), "rmse": rmse(y[:, i], p[:, i]), "bias": bias(y[:, i], p[:, i]),
                  "target_sd": tsd, "err_sd": esd, "R": esd / tsd if tsd > 0 else float("nan")}
    return out


def night_arrays(y: np.ndarray, p: np.ndarray, nights: np.ndarray) -> dict[str, dict[str, np.ndarray]]:
    """Per target, per night (sorted by night id) window count, MAE, RMSE and bias: the P6 bootstrap input."""
    uniq, inv = np.unique(np.asarray(nights).astype(str), return_inverse=True)
    inv = inv.reshape(-1)
    cnt = np.bincount(inv).astype(np.float64)
    out = {}
    for i, t in enumerate(TARGETS):
        e = np.asarray(p, np.float64)[:, i] - np.asarray(y, np.float64)[:, i]
        out[t] = {"night": uniq, "n": cnt, "mae": np.bincount(inv, weights=np.abs(e)) / cnt,
                  "rmse": np.sqrt(np.bincount(inv, weights=e ** 2) / cnt), "bias": np.bincount(inv, weights=e) / cnt}
    return out


def window_keys(device: np.ndarray, window_start: np.ndarray) -> np.ndarray:
    ws = np.asarray(window_start)
    if np.issubdtype(ws.dtype, np.datetime64):
        ws = ws.astype("datetime64[s]").astype(np.int64)
    return np.char.add(np.char.add(np.asarray(device).astype(str), "|"), ws.astype(np.int64).astype(str))


def align(ref_keys: np.ndarray, keys: np.ndarray) -> np.ndarray:
    """Index i such that keys[i] == ref_keys (identical window sets, no duplicates)."""
    if len(set(ref_keys.tolist())) != ref_keys.size or len(set(keys.tolist())) != keys.size:
        raise P8Error("duplicate window keys")
    if ref_keys.size != keys.size or set(ref_keys.tolist()) != set(keys.tolist()):
        raise P8Error("window sets differ: the primary-span pairing is broken")
    order = np.argsort(keys)
    return order[np.searchsorted(keys[order], ref_keys)]


def fit_window_checks(sw, nights: dict, fit: np.ndarray, budget: int, primary_from: int) -> list[dict]:
    """Addendum checks on the windows an offset or the control is fitted on (fail closed: a raise is a failure)."""
    out = []

    def chk(name: str, fn):
        try:
            problem = fn()
        except Exception as exc:                                              # fail closed
            problem = f"check raised {type(exc).__name__}: {exc}"
        out.append({"check": name, "passed": problem is None, "detail": problem or "ok"})

    nid, ordn = sw.prov["night_id"][fit], sw.prov["night_ordinal"][fit]
    chk("fit_windows_are_labelled_adaptation_windows",
        lambda: None if not (fit & ~sw.mask("adaptation")).any() and (fit.any() or budget == 0)
        else "a fit window is unlabelled or outside the adaptation partition (or no fit window at b > 0)")
    chk("fit_windows_in_the_earliest_b_nights",
        lambda: None if set(nid.tolist()) <= set(nights["adaptation"]) and (ordn.size == 0 or int(ordn.max()) <= budget)
        else f"fit nights {sorted(set(ordn.tolist()))} outside nights 1..{budget}")
    chk("no_fit_window_in_the_buffer_night",
        lambda: None if not (np.isin(nid, nights["buffer"]).any() or (ordn == budget + 1).any())
        else "a fit window lies in the buffer night")
    chk("no_fit_window_in_a_test_or_primary_night",
        lambda: None if not (np.isin(nid, nights["test"] + nights["primary"]).any() or (ordn >= primary_from).any()
                             or (sw.partition[fit] != "adaptation").any())
        else "a fit window lies in a test/primary night")

    def precede():
        if budget == 0:
            return None if not fit.any() else "b = 0 has fit windows"
        later = min(sw.row_ts[p][0] for p in ("buffer", "test") if p in sw.row_ts)
        return None if sw.adapt_row_max_ts is not None and sw.adapt_row_max_ts < later else \
            f"fit rows reach {sw.adapt_row_max_ts}, buffer/test rows start {later}"
    chk("fit_rows_precede_buffer_and_test_rows", precede)
    return out


def _require(checks: list[dict], what: str) -> None:
    if not all(c["passed"] for c in checks):
        raise P8Error(f"{what} checks failed: " + "; ".join(f"{c['check']}: {c['detail']}" for c in checks
                                                            if not c["passed"]))


# ------------------------------------------------------------------------------------------------ frozen inputs

def training_mean_value(fold: int) -> tuple[np.ndarray, list[str]]:
    """The P3 training-mean predictor of the fold (frozen run), with its training subjects."""
    d = P3.training_mean_dir(fold)
    if run_status(d) != "complete":
        raise P8Error(f"P3 training-mean run of fold {fold} is missing or not verifiably complete")
    meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
    return np.asarray(meta["train_mean"], np.float64), sorted(meta["train_subjects"])


def _pairs(path: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    return P3._pairs(read_predictions(path))


def _p5_run(subject: str, budget: int, seed: int) -> Path:
    d = P5.run_dir(subject, budget, seed)
    if run_status(d) != "complete":
        raise P8Error(f"P5 run {subject} b={budget} seed {seed} is missing or not verifiably complete")
    return d


def _p5_primary_metrics(d: Path) -> dict[tuple[str, str], float]:
    return {(r["target"], r["metric"]): float(r["value"]) for r in P5._read_csv(d / "metrics.csv")
            if r["span"] == "primary"}


# ------------------------------------------------------------------------------------------ predictor assembly

@dataclass
class SubjectAnalysis:
    subject: str
    fold: int
    y: np.ndarray                   # (n, 2) primary-span targets, in the order of the b = 0 primary windows
    nights: np.ndarray
    device: np.ndarray
    keys: np.ndarray
    preds: dict = field(default_factory=dict)      # (label, budget, seed | None, calibration) -> (n, 2)
    offsets: dict = field(default_factory=dict)    # (label, budget, seed | None, calibration) -> (2,)
    fit_windows: dict = field(default_factory=dict)  # (budget, calibration) -> labelled adaptation windows used
    not_estimable: list = field(default_factory=list)
    checks: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)


def pred_key(label: str, budget: int, seed: int | None) -> tuple:
    """Primary-comparator key: B/D pooled (User02 over both mats), A/C/E/S uncalibrated."""
    return (label, budget, None if label in DETERMINISTIC else seed, "pooled" if label in CALIBRATED else "none")


def calibration_fits(sw, mean: np.ndarray, base_adapt: dict[int, np.ndarray]) -> dict:
    """Offsets of B (training mean) and D (base seed s) for one budget, from its labelled adaptation windows only.

    `base_adapt[s]` holds the base predictions on exactly those windows (sw.mask('adaptation') order). User02: one
    offset pooled over both mats (primary) and one per mat (diagnostic; a mat without adaptation windows is not
    estimable, with no fallback). B's identity (training mean + c = adaptation-target mean) is checked here.
    """
    ad = sw.mask("adaptation")
    y_ad = sw.targets[ad]
    dev = sw.prov["device_id"][ad].astype(str)
    scopes = [("pooled", np.ones(y_ad.shape[0], bool))]
    if sw.subject == USER02:
        scopes += [(m, dev == m) for m in MATS]
    out = {"offsets": {}, "fit_windows": {}, "identity_gap": {}, "not_estimable": []}
    for s, p in base_adapt.items():
        if p.shape != y_ad.shape:
            raise P8Error("base predictions do not cover exactly the adaptation windows")
    for scope, m in scopes:
        out["fit_windows"][scope] = int(m.sum())
        try:
            c_a = calibration_offset(y_ad[m], np.tile(mean, (int(m.sum()), 1)))
        except NotEstimable:
            out["not_estimable"].append({"subject_id": sw.subject, "budget_nights": sw.budget, "calibration": scope,
                                         "reason": "no labelled adaptation window on this mat"})
            continue
        gap = float(np.max(np.abs((mean + c_a) - y_ad[m].mean(axis=0))))
        out["identity_gap"][scope] = gap
        if gap > IDENTITY_TOL:
            raise P8Error(f"{sw.subject} b={sw.budget} {scope}: training mean + offset != adaptation-target mean "
                          f"({gap:g})")
        out["offsets"][("B", None, scope)] = c_a
        for s, p in base_adapt.items():
            out["offsets"][("D", s, scope)] = calibration_offset(y_ad[m], p[m])
    return out


def analyse_subject(sess, subject: str) -> SubjectAnalysis:
    """Predictors A–E on the primary span of one subject, for every budget and seed (gate + checks first)."""
    from src.training.trainer import device, predict_z, set_determinism, to_tensor
    fold = P5.subject_folds()[subject]
    sel = P5.p3_selection()
    plan = P5.frozen_plan()
    rec = plan["subjects"][subject]
    if rec["base_selection_sha256"] != sel["folds"][fold]["selection_sha256"]:
        raise P8Error("P3 selection differs from the committed P5 plan")
    scaler = P5.base_scaler(fold, sel)
    mean, mean_subjects = training_mean_value(fold)
    if mean_subjects != sorted(sel["folds"][fold]["train_subjects"]):
        raise P8Error(f"fold {fold}: training-mean subjects differ from the base training pool")
    primary_from = int(load_protocol()["personalization"]["primary_test_from_ordinal"])
    fits = [dict(scaler.fit_provenance), {"transform": "training_mean", "partition": "train",
                                          "subjects": mean_subjects}]
    seeds = P5.seeds()

    sw0 = sess.windows(subject, 0)
    te0 = sw0.mask("test")
    keys_te0 = window_keys(sw0.prov["device_id"][te0], sw0.prov["window_start"][te0])
    prim0 = sw0.primary[te0]
    an = SubjectAnalysis(subject, fold, sw0.targets[te0][prim0], sw0.prov["night_id"][te0][prim0].astype(str),
                         sw0.prov["device_id"][te0][prim0].astype(str), keys_te0[prim0])
    if sw0.primary_digest() != rec["primary_test"]["windows_sha256"]:
        raise P8Error(f"{subject}: primary test windows differ from the committed P5 plan")

    models, base = {}, {}
    x0 = to_tensor(sw0.pressure[te0], device())
    for s in seeds:
        model, _, prov = P5.base_model(fold, s, sel)
        if prov["weights_sha256"] != rec["base_checkpoints"][s]["weights_sha256"]:
            raise P8Error(f"{subject} seed {s}: base checkpoint differs from the committed P5 plan")
        set_determinism(s)                                   # as in the P5 base evaluation
        p = scaler.inverse(predict_z(model, x0))
        d0 = _p5_run(subject, 0, s)
        y_ref, p_ref, pv = _pairs(d0 / "predictions.parquet")
        same = bool(np.array_equal(p, p_ref) and np.array_equal(sw0.targets[te0], y_ref)
                    and np.array_equal(keys_te0, window_keys(pv["device_id"], pv["window_start"])))
        an.checks[f"base_seed{s}_reproduces_p5_b0_bitwise"] = same
        if not same:
            raise P8Error(f"{subject} seed {s}: base inference does not reproduce the P5 b = 0 predictions bitwise")
        models[s] = model
        base[s] = p[prim0]
        an.preds[("C", 0, s, "none")] = base[s]
        an.provenance[f"p5/{subject}/b00_seed{s}"] = sha256_file(d0 / "predictions.parquet")
    an.preds[("A", 0, None, "none")] = np.tile(mean, (an.y.shape[0], 1))

    for b in (x for x in P5.budgets() if x > 0):
        nights = P5.budget_nights(sess.pers(), subject, b)
        if nights["adaptation"] != rec["budgets"][b]["adaptation_nights"] or \
                nights["buffer"] != rec["budgets"][b]["buffer_nights"]:
            raise P8Error(f"{subject} b={b}: adaptation/buffer nights differ from the committed P5 plan")
        swb = sess.windows(subject, b)
        ad, te = swb.mask("adaptation"), swb.mask("test")
        primb = te & swb.primary
        d = calibration_dir(subject, b)
        ctx = RunContext("personalization", subject=subject, budget=b, input_features=list(RAW_FEATURES),
                         fit_records=fits, selection_subjects=[], window_groups=swb.window_groups(ad | te))
        sess.gate(d, ctx)
        checks = fit_window_checks(swb, nights, ad, b, primary_from)
        write_json(d / "calibration_checks.json", {"checked_at": now(), "passed": all(c["passed"] for c in checks),
                                                   "checks": checks, **design_hashes()})
        _require(checks, f"{subject} b={b} calibration")
        an.checks[f"b{b:02d}_gate_and_fit_window_checks"] = True

        idx = align(an.keys, window_keys(swb.prov["device_id"][primb], swb.prov["window_start"][primb]))
        if not np.array_equal(swb.targets[primb][idx], an.y):
            raise P8Error(f"{subject} b={b}: primary-span targets differ from b = 0")
        xa = to_tensor(swb.pressure[ad], device())
        p_ad = {}
        for s in seeds:
            set_determinism(s)
            p_ad[s] = scaler.inverse(predict_z(models[s], xa))
        fit = calibration_fits(swb, mean, p_ad)
        an.not_estimable += fit["not_estimable"]
        for scope, n in fit["fit_windows"].items():
            an.fit_windows[(b, scope)] = n
        for scope, gap in fit["identity_gap"].items():
            an.checks[f"b{b:02d}_{scope}_training_mean_plus_offset_equals_adaptation_mean_max_abs"] = gap
        for (label, s, scope), c in fit["offsets"].items():
            an.offsets[(label, b, s, scope)] = c
            an.preds[(label, b, s, scope)] = np.tile(mean + c, (an.y.shape[0], 1)) if label == "B" else base[s] + c
        for s in seeds:
            dd = _p5_run(subject, b, s)
            y_e, p_e, pv = _pairs(dd / "predictions.parquet")
            pm = pv["primary_test"].astype(bool)
            ie = align(an.keys, window_keys(pv["device_id"][pm], pv["window_start"][pm]))
            if not np.array_equal(y_e[pm][ie], an.y):
                raise P8Error(f"{subject} b={b} seed {s}: P5 targets differ from the primary-span targets")
            an.preds[("E", b, s, "none")] = p_e[pm][ie]
            an.provenance[f"p5/{subject}/b{b:02d}_seed{s}"] = sha256_file(dd / "predictions.parquet")
        log_test_access("calibration", subject, b, None, f"p8-calibration-{subject}-b{b:02d}")
    return an


def attach_control(an: SubjectAnalysis) -> None:
    """Add the initialization-control predictions S (b = 14) of the complete control runs."""
    for s in P5.seeds():
        d = control_dir(an.subject, s)
        if run_status(d) != "complete":
            raise P8Error(f"initialization control {an.subject} seed {s} is missing or not verifiably complete")
        y, p, pv = _pairs(d / "predictions.parquet")
        pm = pv["primary_test"].astype(bool)
        i = align(an.keys, window_keys(pv["device_id"][pm], pv["window_start"][pm]))
        if not np.array_equal(y[pm][i], an.y):
            raise P8Error(f"control {an.subject} seed {s}: targets differ from the primary-span targets")
        an.preds[("S", CONTROL_BUDGET, s, "none")] = p[pm][i]
        an.provenance[f"p8_posthoc/init_control/{an.subject}/b14_seed{s}"] = sha256_file(d / "predictions.parquet")


def consistency_with_p5(an: SubjectAnalysis) -> float:
    """Largest |difference| between the metrics of C (b = 0) and E and the frozen P5 primary metrics."""
    worst = 0.0
    for (label, b, s, cal), p in an.preds.items():
        if label not in ("C", "E") or (label == "C" and b != 0):
            continue
        ref = _p5_primary_metrics(_p5_run(an.subject, b, s))
        for t, dd in target_metrics(an.y, p).items():
            worst = max(worst, *(abs(v - ref[(t, k)]) for k, v in dd.items()))
    return worst


# ------------------------------------------------------------------------------------------------------ metrics

def _eval_scopes(an: SubjectAnalysis, calibration: str) -> list[tuple[str, np.ndarray]]:
    everything = np.ones(an.y.shape[0], bool)
    if calibration in MATS:                                  # a per-mat offset is evaluated on its own mat only
        return [(calibration, an.device == calibration)]
    scopes = [("all", everything)]
    if an.subject == USER02:
        scopes += [(m, an.device == m) for m in MATS]
    return scopes


def by_seed_rows(an: SubjectAnalysis) -> list[dict]:
    rows = []
    for (label, b, s, cal), p in sorted(an.preds.items(), key=lambda kv: (kv[0][1], kv[0][0], str(kv[0][3]),
                                                                          -1 if kv[0][2] is None else kv[0][2])):
        for scope, m in _eval_scopes(an, cal):
            if not m.any():
                continue
            st = residual_stats(an.y[m], p[m])
            off = an.offsets.get((label, b, s, cal))
            for i, t in enumerate(TARGETS):
                rows.append({"subject_id": an.subject, "fold": an.fold, "target": t, "budget_nights": b,
                             "predictor": label, "predictor_name": LABELS[label], "seed": "" if s is None else s,
                             "calibration": "per_mat" if cal in MATS else cal, "eval_scope": scope,
                             **st[t], "offset": "" if off is None else float(off[i]),
                             "fit_windows": an.fit_windows.get((b, cal), "") if label in CALIBRATED else "",
                             "n_windows": int(m.sum()), "n_nights": int(np.unique(an.nights[m]).size)})
    return rows


SUMMARY_KEYS = ("subject_id", "fold", "target", "budget_nights", "predictor", "predictor_name", "calibration",
                "eval_scope")


def seed_summary(rows: list[dict]) -> list[dict]:
    """Seed mean (and seed SD/min/max, ddof = 1 as in P5) per subject x target x budget x predictor x scope."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in SUMMARY_KEYS), []).append(r)
    out = []
    for key, rs in groups.items():
        rec = dict(zip(SUMMARY_KEYS, key))
        rec["n_seeds"] = len(rs)
        for m in ("mae", "rmse", "bias", "err_sd", "R"):
            v = np.array([r[m] for r in rs], np.float64)
            rec[m] = float(v.mean())
            if m in ("mae", "R"):
                rec[f"{m}_seed_sd"] = float(v.std(ddof=1)) if len(v) > 1 else ""
                rec[f"{m}_seed_min"] = float(v.min()) if len(v) > 1 else ""
                rec[f"{m}_seed_max"] = float(v.max()) if len(v) > 1 else ""
        rec["target_sd"] = rs[0]["target_sd"]
        offs = [r["offset"] for r in rs if r["offset"] != ""]
        rec["offset_mean"] = float(np.mean(offs)) if offs else ""
        rec.update(fit_windows=rs[0]["fit_windows"], n_windows=rs[0]["n_windows"], n_nights=rs[0]["n_nights"])
        out.append(rec)
    return out


def identity_checks(rows: list[dict]) -> dict[str, float]:
    """Constant predictors have R = 1; a constant offset leaves the error SD unchanged (C vs D)."""
    const = max(abs(r["R"] - 1.0) for r in rows if r["predictor"] in DETERMINISTIC)
    sd = {(r["subject_id"], r["target"], r["seed"], r["eval_scope"]): r["err_sd"] for r in rows
          if r["predictor"] == "C" and r["budget_nights"] == 0}
    shift = max(abs(r["err_sd"] - sd[(r["subject_id"], r["target"], r["seed"], r["eval_scope"])]) for r in rows
                if r["predictor"] == "D")
    if const > IDENTITY_TOL or shift > IDENTITY_TOL:
        raise P8Error(f"identity check failed: |R - 1| {const:g}, error-SD shift {shift:g}")
    return {"constant_predictor_max_abs_R_minus_1": const, "offset_error_sd_max_abs_change": shift}


def loso_rows() -> list[dict]:
    """Strict-LOSO residual variation (Table 2 setting): frozen P3 predictions of the held-out subject."""
    rows = []
    for subject, fold in sorted(P5.subject_folds().items(), key=lambda kv: kv[1]):
        d = P3.training_mean_dir(fold)
        if run_status(d) != "complete":
            raise P8Error(f"P3 training-mean fold {fold} is not complete")
        y, p, pv = _pairs(d / "predictions.parquet")
        keys = window_keys(pv["device_id"], pv["window_start"])
        runs = [("A", None, d, y, p)]
        for s in P5.seeds():
            ds = P3.final_dir(fold, s)
            if run_status(ds) != "complete":
                raise P8Error(f"P3 final fold {fold} seed {s} is not complete")
            ys, ps, pvs = _pairs(ds / "predictions.parquet")
            if not (np.array_equal(ys, y) and np.array_equal(window_keys(pvs["device_id"], pvs["window_start"]),
                                                             keys)):
                raise P8Error(f"fold {fold}: training-mean and RAW-TCN windows differ")
            runs.append(("C", s, ds, ys, ps))
        n_nights = int(np.unique(pv["night_id"].astype(str)).size)
        for label, s, dr, yy, pp in runs:
            st = residual_stats(yy, pp)
            ref = {(r["target"], r["metric"]): float(r["value"]) for r in P5._read_csv(dr / "metrics.csv")}
            worst = max(abs(st[t][k] - ref[(t, k)]) for t in TARGETS for k in ("mae", "rmse", "bias"))
            if worst > CONSISTENCY_TOL:
                raise P8Error(f"fold {fold} {label}: metrics do not reproduce the P3 run ({worst:g})")
            for t in TARGETS:
                rows.append({"setting": "strict_loso", "subject_id": subject, "fold": fold, "target": t,
                             "budget_nights": "", "predictor": label, "predictor_name": "training_mean" if label == "A"
                             else "raw_tcn", "seed": "" if s is None else s, "calibration": "none",
                             "eval_scope": "all", **st[t], "offset": "", "fit_windows": "",
                             "n_windows": int(yy.shape[0]), "n_nights": n_nights})
    return rows


# ------------------------------------------------------------------------------------------------------ bootstrap

def comparator_bootstrap(an: SubjectAnalysis) -> list[dict]:
    """Paired night-level bootstrap of Δ = MAE(first) − MAE(second) (positive = second better), P6 settings.

    One set of resampled nights per subject is shared by every comparison (as in P6). Seed 0 is primary; seeds 1
    and 2 are sensitivity.
    """
    resamples, rng_seed, level = P6.bootstrap_settings()
    arrays = {k: night_arrays(an.y, p, an.nights) for k, p in an.preds.items()
              if k[3] in ("none", "pooled")}
    n = np.unique(an.nights).size
    counts = P6.resample_counts(n, resamples, rng_seed)
    full = np.ones((1, n))
    todo = [(f, s_, b) for b in P6.ADAPT_BUDGETS for f, s_ in COMPARISONS_ALL]
    if any(k[0] == "S" for k in an.preds):
        todo += [(f, s_, CONTROL_BUDGET) for f, s_ in COMPARISONS_CONTROL]
    rows = []
    for first, second, b in todo:
        for seed in P5.seeds():
            fa, sa = arrays[pred_key(first, b, seed)], arrays[pred_key(second, b, seed)]
            for t in TARGETS:
                x, y = fa[t], sa[t]
                P6.pair(x, y)
                boot = P6.paired_effects(counts, x, y)["mae"]
                point = float(P6.paired_effects(full, x, y)["mae"][0])
                lo, hi = P6.interval(boot, level)
                pn = x["mae"] - y["mae"]
                rows.append({"subject_id": an.subject, "target": t, "budget_nights": b, "first": first,
                             "second": second, "seed": seed, "role": "primary" if seed == P6.PRIMARY_SEED
                             else "sensitivity", "n_nights": int(x["night"].size), "n_windows": int(x["n"].sum()),
                             "first_mae": float(P6.weighted(full, x)["mae"][0]),
                             "second_mae": float(P6.weighted(full, y)["mae"][0]), "point_estimate": point,
                             "ci_lower": lo, "ci_upper": hi, "interval": P6.side(lo, hi),
                             "night_median_delta": float(np.median(pn)),
                             "proportion_nights_second_better": float((pn > 0).mean()),
                             "n_resamples": resamples, "rng_seed": rng_seed, "level": level})
    return rows


def p6_reproduction(an: SubjectAnalysis, p6_rows: list[dict]) -> float:
    """Largest |difference| between this module's C-vs-E bootstrap (seed 0) and the frozen P6 ΔMAE table."""
    resamples, rng_seed, level = P6.bootstrap_settings()
    n = np.unique(an.nights).size
    counts = P6.resample_counts(n, resamples, rng_seed)
    full = np.ones((1, n))
    worst = 0.0
    for b in P6.ADAPT_BUDGETS:
        c = night_arrays(an.y, an.preds[("C", 0, P6.PRIMARY_SEED, "none")], an.nights)
        e = night_arrays(an.y, an.preds[("E", b, P6.PRIMARY_SEED, "none")], an.nights)
        for t in TARGETS:
            ref = [r for r in p6_rows if r["subject_id"] == an.subject and r["target"] == t
                   and int(r["budget_nights"]) == b and r["metric"] == "mae" and int(r["seed"]) == P6.PRIMARY_SEED]
            if len(ref) != 1:
                raise P8Error(f"P6 ΔMAE row {an.subject} {t} b={b} not found once")
            lo, hi = P6.interval(P6.paired_effects(counts, c[t], e[t])["mae"], level)
            point = float(P6.paired_effects(full, c[t], e[t])["mae"][0])
            worst = max(worst, abs(lo - float(ref[0]["ci_lower"])), abs(hi - float(ref[0]["ci_upper"])),
                        abs(point - float(ref[0]["point_estimate"])))
    return worst


# ------------------------------------------------------------------------------------------ interpretation map

def interpretation_rows(summary: list[dict], boot: list[dict]) -> list[dict]:
    """The pre-registered case map (plan §8), per subject x target x budget; nothing here is tuned to the results."""
    mean = {(r["subject_id"], r["target"], int(r["budget_nights"]), r["predictor"]): float(r["mae"])
            for r in summary if r["eval_scope"] == "all" and r["calibration"] in ("none", "pooled")}
    side = {(r["subject_id"], r["target"], int(r["budget_nights"]), r["first"], r["second"]): r["interval"]
            for r in boot if r["role"] == "primary"}

    def better(subj, t, b, x, y) -> bool:
        """X better than Y: seed-0 interval of MAE(X) − MAE(Y) below zero and X has the lower seed-mean MAE."""
        if (subj, t, b, x, y) in side:
            below = side[(subj, t, b, x, y)] == "below_zero"
        else:
            below = side[(subj, t, b, y, x)] == "above_zero"
        return below and mean[(subj, t, b, x)] < mean[(subj, t, b, y)]

    out = []
    subjects = sorted({r["subject_id"] for r in summary})
    for subj in subjects:
        for t in TARGETS:
            for b in P6.ADAPT_BUDGETS:
                m = {k: mean[(subj, t, b, k)] for k in ("B", "D", "E")}
                m["A"], m["C"] = mean[(subj, t, 0, "A")], mean[(subj, t, 0, "C")]
                rec = {"subject_id": subj, "target": t, "budget_nights": b,
                       **{f"mae_{k}": m[k] for k in "ABCDE"},
                       "case_A_B_le_E": m["B"] <= m["E"],
                       "E_better_than_B": better(subj, t, b, "E", "B"), "B_better_than_E": better(subj, t, b, "B", "E"),
                       "case_B_D_approx_E": not better(subj, t, b, "D", "E") and not better(subj, t, b, "E", "D"),
                       "case_C_E_better_than_D": better(subj, t, b, "E", "D"),
                       "D_better_than_E": better(subj, t, b, "D", "E"),
                       "B_better_than_D": better(subj, t, b, "B", "D"), "D_better_than_B": better(subj, t, b, "D", "B"),
                       "D_above_C": m["D"] > m["C"], "E_above_C": m["E"] > m["C"]}
                if subj == "User07" and t == "temperature":
                    rec["case_D"] = rec["D_above_C"] and rec["E_above_C"]
                    rec["case_E"] = (not rec["D_above_C"]) and rec["E_above_C"]
                if b == CONTROL_BUDGET and (subj, t, b, "S") in mean:
                    rec["mae_S"] = mean[(subj, t, b, "S")]
                    rec["case_F_S_better_than_B"] = better(subj, t, b, "S", "B")
                    rec["case_G_S_not_better_than_B"] = not rec["case_F_S_better_than_B"]
                    rec["case_H_E_better_than_S"] = better(subj, t, b, "E", "S")
                    rec["case_I_S_approx_or_better_than_E"] = not rec["case_H_E_better_than_S"]
                    rec["S_better_than_E"] = better(subj, t, b, "S", "E")
                out.append(rec)
    return out


# ------------------------------------------------------------------------------------------ initialization control

def control_checks(sw, nights: dict, fit: np.ndarray, primary_from: int) -> list[dict]:
    """Addendum checks of the control's training windows: nights 1–14 only; never night 15 or a primary night."""
    out = fit_window_checks(sw, nights, fit, CONTROL_BUDGET, primary_from)
    ordn = sw.prov["night_ordinal"][fit]
    out.append({"check": "training_windows_only_in_nights_1_to_14",
                "passed": bool(fit.any() and ordn.min() >= 1 and ordn.max() <= CONTROL_BUDGET),
                "detail": "ok" if fit.any() and ordn.max() <= CONTROL_BUDGET else f"ordinals {sorted(set(ordn))}"})
    bad = (ordn == CONTROL_BUDGET + 1) | (ordn >= primary_from)
    out.append({"check": "no_training_window_in_night_15_or_the_primary_span", "passed": not bad.any(),
                "detail": "ok" if not bad.any() else f"{int(bad.sum())} windows"})
    return out


def init_weights_digest(cfg, seed: int) -> str:
    """Digest of the random initialisation train_tcn starts from (same seeding, before any update)."""
    from src.models.tcn import TCN
    from src.training.trainer import set_determinism
    set_determinism(seed)
    return P5.weights_digest(TCN(len(RAW_FEATURES), cfg.channels, cfg.kernel_size, cfg.dropout).state_dict())


def run_init_control(sess, subject: str, seed: int) -> str:
    import torch
    from src.training.trainer import device, environment, predict_z, to_tensor, train_tcn

    d = control_dir(subject, seed)
    if run_status(d) == "complete":
        return "skipped (complete)"
    if seed not in P5.seeds() or subject not in P5.subject_folds():
        raise P8Error(f"{subject} seed {seed} is not a declared control run")
    load_addendum()
    plan = P5.frozen_plan()
    rec = plan["subjects"][subject]
    fold = P5.subject_folds()[subject]
    b = CONTROL_BUDGET
    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_p8-init-control-{subject}-b{b:02d}-seed{seed}"
    begin_run(d, run_id)
    log = RunLog(d, sess.echo)
    try:
        sel = P5.p3_selection()
        if rec["base_selection_sha256"] != sel["folds"][fold]["selection_sha256"]:
            raise P8Error("P3 selection differs from the committed P5 plan")
        nights = P5.budget_nights(sess.pers(), subject, b)
        if nights["adaptation"] != rec["budgets"][b]["adaptation_nights"] or \
                nights["buffer"] != rec["budgets"][b]["buffer_nights"]:
            raise P8Error("adaptation/buffer nights differ from the committed P5 plan")
        sw = sess.windows(subject, b)
        tr, te = sw.mask("adaptation"), sw.mask("test")
        scaler = P5.base_scaler(fold, sel)                 # the base model's target scaler, never refit
        ctx = RunContext("personalization", subject=subject, budget=b, input_features=list(RAW_FEATURES),
                         fit_records=[dict(scaler.fit_provenance)], selection_subjects=[],
                         window_groups=sw.window_groups(tr | te))
        _, verified = sess.gate(d, ctx)
        cfg, epochs = P5.adaptation_config(sel["folds"][fold]["config"])
        primary_from = int(load_protocol()["personalization"]["primary_test_from_ordinal"])
        checks = P5.p5_checks(subject, b, sw, nights, sess.pers(), sel, scaler, cfg, epochs, rec) + \
            control_checks(sw, nights, tr, primary_from)
        init_sha = init_weights_digest(cfg, seed)
        base_shas = {v["weights_sha256"] for v in rec["base_checkpoints"].values()}
        checks.append({"check": "initialisation_is_not_a_pretrained_base", "passed": init_sha not in base_shas,
                       "detail": "ok" if init_sha not in base_shas else "initial weights equal a base checkpoint"})
        write_json(d / "checks.json", {"checked_at": now(), "passed": all(c["passed"] for c in checks),
                                       "checks": checks})
        _require(checks, f"{subject} seed {seed} control")
        meta = {"run_id": run_id, "phase": "P8", "kind": "initialization_control", **design_hashes(),
                "subject": subject, "held_out_subject": subject, "fold": fold, "budget_nights": b, "seed": seed,
                "family": P5.P5_FAMILY, "input_features": list(RAW_FEATURES), "init": "random",
                "init_weights_sha256": init_sha, "architecture": {k: sel["folds"][fold]["config"][k]
                                                                  for k in ("channels", "kernel_size", "dropout")},
                "recipe": "frozen_p5_fine_tuning", "config": cfg.as_dict(), "epochs": epochs, "optimizer": "adamw",
                "adaptation_nights": nights["adaptation"], "buffer_nights": nights["buffer"],
                "primary_test_nights": rec["primary_test"]["nights"], "n_train_windows": int(tr.sum()),
                "n_test_windows": int(te.sum()), "n_primary_test_windows": int((te & sw.primary).sum()),
                "p3_selected_configs_sha256": sel["file_sha256"], "p5_plan_sha256": S.file_sha256_lf(P5.plan_yaml()),
                "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance},
                **frozen_inputs(verified), **P5.p5_git_state(), **environment(), "started_at": now()}
        write_json(d / "run_meta.json", meta)
        write_text(d / "config.yaml", yaml.safe_dump({"subject": subject, "fold": fold, "budget_nights": b,
                                                      "seed": seed, "init": "random", "config": cfg.as_dict(),
                                                      "epochs": epochs}, sort_keys=False))
        res = train_tcn(cfg, sw.pressure[tr], sw.targets[tr], scaler, seed, epochs=epochs, log=log, init_state=None)
        write_csv(d / "history.csv", res.history, list(res.history[0]))
        with open_for_write(d / "model.pt", "wb") as fh:
            torch.save(res.model.state_dict(), fh)
        log_test_access("init_control", subject, b, seed, run_id)          # the single test look of this model
        pred = scaler.inverse(predict_z(res.model, to_tensor(sw.pressure[te], device())))
        y = sw.targets[te]
        sm = P5.span_metrics(y, pred, sw.primary[te], sw.prov["night_id"][te])
        rows = [{"run_id": run_id, "subject_id": subject, "fold": fold, "budget_nights": b, "seed": seed,
                 "span": span, "target": t, "metric": k, "value": v, "n_windows": r["n_windows"],
                 "n_nights": r["n_nights"]}
                for span, r in sm.items() for t, dd in r["metrics"].items() for k, v in dd.items()]
        write_csv(d / "metrics.csv", rows, list(rows[0]))
        P5.write_predictions(d / "predictions.parquet", run_id, "tcn_raw_scratch_init_control", subject, fold, b,
                             seed, sw, te, y, pred)
        meta.update(finished_at=now(), epochs_run=res.epochs_run, train_seconds=round(res.seconds, 1),
                    model_sha256=sha256_file(d / "model.pt"), weights_sha256=P5.weights_digest(res.model.state_dict()),
                    predictions_sha256=sha256_file(d / "predictions.parquet"),
                    primary_metrics=sm["primary"]["metrics"])
        write_json(d / "run_meta.json", meta)
        log(f"{subject} control seed {seed}: primary {json.dumps(sm['primary']['metrics'])}")
        complete_run(d, ["config.yaml", "run_meta.json", "leakage_check.json", "checks.json", "history.csv",
                         "model.pt", "metrics.csv", "predictions.parquet"])
        return "complete"
    except BaseException as exc:
        fail_run(d, exc)
        raise


# ------------------------------------------------------------------------------------------------------ analysis

def analyse(sess, p6_mae_rows: list[dict] | None = None) -> tuple[dict[str, list[dict]], dict]:
    """All tables of the addendum plus provenance (control runs must be complete)."""
    load_addendum()
    tables = {"by_seed": [], "not_estimable": [], "bootstrap": []}
    prov = {"design": design_hashes(), "checks": {}, "inputs_sha256": {}}
    for subject in sorted(P5.subject_folds(), key=P5.subject_folds().get):
        an = analyse_subject(sess, subject)
        attach_control(an)
        tables["by_seed"] += by_seed_rows(an)
        tables["not_estimable"] += an.not_estimable
        tables["bootstrap"] += comparator_bootstrap(an)
        prov["checks"][subject] = {**an.checks, "p5_metrics_max_abs_diff": consistency_with_p5(an),
                                   **({"p6_bootstrap_max_abs_diff": p6_reproduction(an, p6_mae_rows)}
                                      if p6_mae_rows is not None else {}),
                                   "fit_windows": {f"b{b:02d}_{c}": n for (b, c), n in sorted(an.fit_windows.items())},
                                   "primary_windows": int(an.y.shape[0]),
                                   "primary_nights": int(np.unique(an.nights).size)}
        prov["inputs_sha256"].update(an.provenance)
        if prov["checks"][subject]["p5_metrics_max_abs_diff"] > CONSISTENCY_TOL:
            raise P8Error(f"{subject}: C/E metrics do not reproduce the frozen P5 metrics")
        if p6_mae_rows is not None and prov["checks"][subject]["p6_bootstrap_max_abs_diff"] > CONSISTENCY_TOL:
            raise P8Error(f"{subject}: C-vs-E bootstrap does not reproduce the frozen P6 table")
    prov["identities"] = identity_checks(tables["by_seed"])
    tables["summary"] = seed_summary(tables["by_seed"])
    tables["loso"] = loso_rows()
    tables["loso_summary"] = seed_summary(tables["loso"])
    tables["interpretation"] = interpretation_rows(tables["summary"], tables["bootstrap"])
    control = []
    for subject in sorted(P5.subject_folds(), key=P5.subject_folds().get):
        for s in P5.seeds():
            meta = json.loads((control_dir(subject, s) / "run_meta.json").read_text(encoding="utf-8"))
            control.append({"subject_id": subject, "seed": s, "run_id": meta["run_id"],
                            "init_weights_sha256": meta["init_weights_sha256"],
                            "weights_sha256": meta["weights_sha256"], "n_train_windows": meta["n_train_windows"],
                            "epochs_run": meta["epochs_run"]})
    prov["init_control_runs"] = control
    return tables, prov


def write_tables(tables: dict[str, list[dict]], prov: dict) -> Path:
    out = metrics_dir()
    empty = {"not_estimable": ["subject_id", "budget_nights", "calibration", "reason"]}
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r)) or empty.get(name, ["none"])
        write_csv(out / f"p8_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    write_json(out / "p8_posthoc_provenance.json", prov)
    return out
