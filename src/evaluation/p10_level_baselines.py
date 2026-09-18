"""P10 parts R and M: reproduction check of the frozen level baselines and neural metrics, and median baselines
(protocol v1.4 addendum; D-064; docs/P10_LEVEL_BASELINE_HISTORY_PLAN.md §3–§4).

Post hoc and exploratory. Nothing here trains or re-infers a model and no frozen artifact is written:
- R: the strict-LOSO fold windows and the RQ2 windows are rebuilt from canonical_v1 and the frozen splits; the frozen
  training-mean, RAW-TCN (P3), base / fine-tuning (P5) and scratch-control (P8) predictions are paired window by
  window with them; MAE, RMSE, bias, constants and window/night counts must equal the frozen full-precision tables
  (absolute tolerance 1e-9, relative 0; exact equality for keys, targets and counts). A failure stops P10.
- M: source-training median (labelled outer-training windows) and adaptation-target median (labelled adaptation
  windows of the budget; User02 pooled over both mats), evaluated next to the means. Constants are deterministic:
  one value, no seed repetition. The constant-vs-neural counts are point-estimate comparisons only.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from src.data import paths
from src.data.io_guard import open_for_write, write_csv, write_json
from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P5
from src.evaluation import p8_posthoc as P8
from src.evaluation import splits as S
from src.evaluation.leakage import RunContext
from src.evaluation.metrics import TARGETS, bias, mae, rmse
from src.evaluation.p3_loso import now, read_predictions, run_status, sha256_file
from src.evaluation.protocol import load_protocol, protocol_sha256
from src.features.pressure_features import RAW_FEATURES

VERSION = "v1.4"
DECISION = "D-064"
TOL_ABS = 1e-9
TOL_REL = 0.0
KEY_FIELDS = ("subject_id", "device_id", "session_id", "sensor_phase", "channel_quality_phase", "night_id",
              "window_start", "window_end", "target_timestamp")


class P10Error(RuntimeError):
    pass


# --------------------------------------------------------------------------------------------------- design / paths

def plan_doc() -> Path:
    return paths.PROJECT_ROOT / "docs" / "P10_LEVEL_BASELINE_HISTORY_PLAN.md"


def config_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / VERSION / "p10_level_baseline_history.yaml"


def load_config() -> dict:
    """The v1.4 addendum, checked against the frozen v1.0 protocol and the fixed tolerance (refuses any drift)."""
    doc = yaml.safe_load(config_yaml().read_text(encoding="utf-8"))
    problems = []
    if doc.get("protocol_version") != VERSION or doc.get("decision") != DECISION:
        problems.append("addendum version/decision")
    if doc["base_protocol"]["sha256"] != protocol_sha256():
        problems.append("v1.0 protocol file differs from the hash the addendum builds on")
    rp = doc["reproduction"]
    if float(rp["tolerance_abs"]) != TOL_ABS or float(rp["tolerance_rel"]) != TOL_REL:
        problems.append("reproduction tolerance differs from the plan")
    if doc["subjects"] != sorted(P5.subject_folds()) or doc["seeds_neural"] != P5.seeds():
        problems.append("subjects/seeds differ from v1.0")
    mb = doc["median_baselines"]
    if mb["budgets_nights"] != [b for b in P5.budgets() if b > 0] or \
            mb["primary_test_from_ordinal"] != int(load_protocol()["personalization"]["primary_test_from_ordinal"]):
        problems.append("budgets/primary span differ from v1.0")
    if mb["statistic"] != "numpy_median" or mb["user02"] != "pooled_over_mats":
        problems.append("median definition differs from the plan")
    if problems:
        raise P10Error("v1.4 addendum check failed: " + "; ".join(problems))
    return doc


def design_hashes() -> dict:
    return {"addendum_version": VERSION, "decision": DECISION, "plan_sha256_lf": S.file_sha256_lf(plan_doc()),
            "config_sha256_lf": S.file_sha256_lf(config_yaml()), "base_protocol_sha256": protocol_sha256()}


_OUTPUT_ROOT: Path | None = None


def set_output_root(root: Path | None) -> None:
    global _OUTPUT_ROOT
    _OUTPUT_ROOT = None if root is None else Path(root)


def output_root() -> Path:
    return _OUTPUT_ROOT if _OUTPUT_ROOT is not None else paths.PROJECT_ROOT / "outputs"


def run_root() -> Path:
    return output_root() / "runs" / "p10" / "level_baselines"


def metrics_dir() -> Path:
    return output_root() / "metrics" / "p10"


def tables_dir() -> Path:
    return paths.PROJECT_ROOT / "paper" / "tables"


def read_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def log_test_access(analysis: str, scope: str) -> None:
    with open_for_write(run_root() / "test_access.jsonl", "a") as fh:
        fh.write(json.dumps({"at": now(), "analysis": analysis, "scope": scope, **design_hashes()}) + "\n")


# ------------------------------------------------------------------------------------------------ pure helpers

def within_tol(got: float, want: float, tol_abs: float = TOL_ABS) -> tuple[bool, float]:
    """|got − want| <= tol_abs (relative tolerance 0). NaN never passes."""
    d = abs(float(got) - float(want))
    return bool(np.isfinite(d) and d <= tol_abs), d


@dataclass
class Checks:
    """Collects every reproduction comparison; `passed` only if all pass."""
    rows: list[dict] = field(default_factory=list)

    def num(self, scope: str, quantity: str, got, want, **ctx) -> None:
        ok, d = within_tol(got, want)
        self.rows.append({"scope": scope, **ctx, "quantity": quantity, "kind": "float", "recomputed": float(got),
                          "frozen": float(want), "abs_diff": d, "tolerance_abs": TOL_ABS, "passed": ok})

    def exact(self, scope: str, quantity: str, ok: bool, got="", want="", **ctx) -> None:
        self.rows.append({"scope": scope, **ctx, "quantity": quantity, "kind": "exact", "recomputed": got,
                          "frozen": want, "abs_diff": "", "tolerance_abs": 0, "passed": bool(ok)})

    @property
    def passed(self) -> bool:
        return bool(self.rows) and all(r["passed"] for r in self.rows)

    def failures(self) -> list[dict]:
        return [r for r in self.rows if not r["passed"]]


def constants(y_fit: np.ndarray) -> dict[str, np.ndarray]:
    """Per-target mean and median over the fitting windows (numpy.median: mean of the two middle values if even)."""
    y = np.asarray(y_fit, np.float64)
    if y.ndim != 2 or y.shape[1] != 2 or y.shape[0] == 0 or not np.all(np.isfinite(y)):
        raise P10Error("fitting targets must be a finite, non-empty (n, 2) array")
    return {"mean": y.mean(axis=0), "median": np.median(y, axis=0)}


def point_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, dict[str, float]]:
    y, p = np.asarray(y, np.float64), np.asarray(p, np.float64)
    if y.shape != p.shape or y.ndim != 2 or y.shape[1] != 2 or y.shape[0] == 0:
        raise ValueError("expected matching non-empty (n, 2) arrays")
    return {t: {"mae": mae(y[:, i], p[:, i]), "rmse": rmse(y[:, i], p[:, i]), "bias": bias(y[:, i], p[:, i])}
            for i, t in enumerate(TARGETS)}


def _as_str(a) -> np.ndarray:
    a = np.asarray(a)
    if np.issubdtype(a.dtype, np.datetime64):
        return a.astype("datetime64[s]").astype(np.int64).astype(str)
    if np.issubdtype(a.dtype, np.integer):
        return a.astype(np.int64).astype(str)
    return a.astype(str)


def strict_pairs(pr: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    """Long predictions -> (y, p) (n, 2) and provenance, requiring that temperature row i and humidity row i carry
    identical provenance (the pairing of the two targets is verified, not assumed)."""
    t, h = pr["target"] == "temperature", pr["target"] == "humidity"
    if t.sum() != h.sum() or t.sum() + h.sum() != pr["target"].size:
        raise P10Error("prediction rows are not an exact temperature/humidity pairing")
    for k, v in pr.items():
        if k in ("target", "y_true", "y_pred"):
            continue
        if not np.array_equal(_as_str(v[t]), _as_str(v[h])):
            raise P10Error(f"temperature and humidity rows differ in {k}")
    y = np.stack([pr["y_true"][t], pr["y_true"][h]], 1).astype(np.float64)
    p = np.stack([pr["y_pred"][t], pr["y_pred"][h]], 1).astype(np.float64)
    return y, p, {k: v[t] for k, v in pr.items() if k not in ("target", "y_true", "y_pred")}


def keys_equal(prov_frozen: dict, prov_new: dict, mask: np.ndarray | None = None,
               fields: tuple[str, ...] = KEY_FIELDS) -> tuple[bool, str]:
    """Window-by-window equality of the provenance keys (in order)."""
    for f in fields:
        a = _as_str(prov_frozen[f])
        b = _as_str(prov_new[f] if mask is None else np.asarray(prov_new[f])[mask])
        if a.shape != b.shape or not np.array_equal(a, b):
            return False, f
    return True, "ok"


def count_le(pairs: list[tuple[float, float]]) -> int:
    """Number of cells with constant MAE <= neural seed-mean MAE (point estimates; no interval)."""
    return int(sum(1 for c, n in pairs if c <= n))


# ------------------------------------------------------------------------------------------------ strict LOSO

def loso_part(sess, checks: Checks, tables: dict) -> dict:
    """R1–R5 and the strict-LOSO medians. Returns per-fold constants {fold: {"mean", "median", ...}}."""
    tm_tab = {int(r["fold"]): r for r in read_csv(tables_dir() / "p3_training_mean_by_fold.csv")}
    tcn_tab = {(int(r["fold"]), int(r["seed"]), r["target"]): r
               for r in read_csv(tables_dir() / "p3_tcn_outer_by_seed.csv")}
    summ = {(r["model"], r["target"], r["metric"]): r for r in read_csv(tables_dir() / "p3_primary_summary.csv")}
    out, seedmeans = {}, {}
    for fold, held in sorted({int(k): v for k, v in load_protocol()["loso"]["outer_folds"].items()}.items()):
        fd = sess.fold(fold)
        tr = fd.labelled & (fd.partition == "train")
        te = fd.labelled & (fd.partition == "test")
        ctx = dict(fold=fold, subject_id=held)
        d = run_root() / "loso" / f"fold{fold}"
        fits = [{"transform": "training_mean", "partition": "train", "subjects": fd.train_subjects},
                {"transform": "training_median", "partition": "train", "subjects": fd.train_subjects}]
        sess.gate(d, RunContext("loso", fold=fold, input_features=list(RAW_FEATURES), fit_records=fits,
                                selection_subjects=[], window_groups=fd.window_groups(tr | te)))
        run = P3.training_mean_dir(fold)
        if run_status(run) != "complete":
            raise P10Error(f"P3 training-mean fold {fold} is not verifiably complete")
        meta = json.loads((run / "run_meta.json").read_text(encoding="utf-8"))
        tab = tm_tab[fold]
        checks.exact("loso", "held_out_subject", tab["held_out_subject"] == held == meta["held_out_subject"],
                     held, tab["held_out_subject"], **ctx)
        checks.exact("loso", "n_train_windows", int(tr.sum()) == int(tab["train_n_windows"]) == meta["n_train_windows"],
                     int(tr.sum()), tab["train_n_windows"], **ctx)
        checks.exact("loso", "n_test_windows", int(te.sum()) == int(tab["test_n_windows"]) == meta["n_test_windows"],
                     int(te.sum()), tab["test_n_windows"], **ctx)
        c = constants(fd.targets[tr])
        for i, t in enumerate(TARGETS):
            col = "train_mean_temp" if t == "temperature" else "train_mean_humidity"
            checks.num("loso", "training_mean", c["mean"][i], meta["train_mean"][i], target=t, **ctx)
            checks.num("loso", "training_mean_table", c["mean"][i], float(tab[col]), target=t, **ctx)
        y_te = fd.targets[te]
        prov_te = {k: v[te] for k, v in fd.prov.items()}
        y_f, p_f, pv_f = strict_pairs(read_predictions(run / "predictions.parquet"))
        ok, bad = keys_equal(pv_f, prov_te)
        checks.exact("loso", "training_mean_prediction_keys", ok, bad, "ok", **ctx)
        checks.exact("loso", "training_mean_y_true", bool(np.array_equal(y_f, y_te)), **ctx)
        checks.exact("loso", "training_mean_prediction_is_constant",
                     bool(np.array_equal(p_f, np.tile(np.asarray(meta["train_mean"]), (len(p_f), 1)))), **ctx)
        suffix = {"temperature": "T", "humidity": "H"}
        m_mean = point_metrics(y_te, np.tile(c["mean"], (len(y_te), 1)))
        m_med = point_metrics(y_te, np.tile(c["median"], (len(y_te), 1)))
        for t in TARGETS:
            for k, col in (("mae", "MAE"), ("rmse", "RMSE"), ("bias", "bias")):
                checks.num("loso", f"training_mean_{k}", m_mean[t][k], float(tab[f"{col}_{suffix[t]}"]), target=t,
                           **ctx)
                checks.num("loso", f"training_mean_{k}_summary", m_mean[t][k], float(summ[("training_mean", t, k)][held]),
                           target=t, **ctx)
        n_nights = int(np.unique(prov_te["night_id"].astype(str)).size)
        n_train_nights = int(np.unique(fd.prov["night_id"][tr].astype(str)).size)
        files = {"p3_training_mean": sha256_file(run / "predictions.parquet")}
        for t_i, t in enumerate(TARGETS):
            for label, cc, mm in (("training_mean", c["mean"], m_mean), ("training_median", c["median"], m_med)):
                tables["loso_constants"].append({"fold": fold, "subject_id": held, "statistic": label, "target": t,
                                                 "value": float(cc[t_i]), "n_train_windows": int(tr.sum()),
                                                 "n_train_nights": n_train_nights,
                                                 "train_subjects": "+".join(fd.train_subjects)})
                tables["loso_metrics"].append({"subject_id": held, "fold": fold, "target": t, "predictor": label,
                                               "seed": "", **mm[t], "n_windows": int(te.sum()),
                                               "n_nights": n_nights, "source": "recomputed"})
        per_seed = {t: {k: [] for k in ("mae", "rmse", "bias")} for t in TARGETS}
        for s in P5.seeds():
            rd = P3.final_dir(fold, s)
            if run_status(rd) != "complete":
                raise P10Error(f"P3 final fold {fold} seed {s} is not verifiably complete")
            ys, ps, pvs = strict_pairs(read_predictions(rd / "predictions.parquet"))
            ok, bad = keys_equal(pvs, prov_te)
            checks.exact("loso", "raw_tcn_prediction_keys", ok, bad, "ok", seed=s, **ctx)
            checks.exact("loso", "raw_tcn_y_true", bool(np.array_equal(ys, y_te)), seed=s, **ctx)
            files[f"p3_final_seed{s}"] = sha256_file(rd / "predictions.parquet")
            mm = point_metrics(y_te, ps)
            for t in TARGETS:
                for k in ("mae", "rmse", "bias"):
                    checks.num("loso", f"raw_tcn_{k}", mm[t][k], float(tcn_tab[(fold, s, t)][k]), target=t, seed=s,
                               **ctx)
                    per_seed[t][k].append(mm[t][k])
                checks.exact("loso", "raw_tcn_n_windows", int(tcn_tab[(fold, s, t)]["n_windows"]) == int(te.sum()),
                             int(te.sum()), tcn_tab[(fold, s, t)]["n_windows"], target=t, seed=s, **ctx)
                tables["loso_metrics"].append({"subject_id": held, "fold": fold, "target": t, "predictor": "raw_tcn",
                                               "seed": s, **mm[t], "n_windows": int(te.sum()), "n_nights": n_nights,
                                               "source": "frozen_predictions"})
        for t in TARGETS:
            rec = {k: float(np.mean(v)) for k, v in per_seed[t].items()}
            for k in ("mae", "rmse", "bias"):
                checks.num("loso", f"raw_tcn_{k}_seed_mean_summary", rec[k], float(summ[("tcn_raw", t, k)][held]),
                           target=t, **ctx)
            tables["loso_metrics"].append({"subject_id": held, "fold": fold, "target": t, "predictor": "raw_tcn",
                                           "seed": "mean", **rec, "mae_seed_sd": float(np.std(per_seed[t]["mae"],
                                                                                              ddof=1)),
                                           "n_windows": int(te.sum()), "n_nights": n_nights,
                                           "source": "frozen_predictions"})
            seedmeans[(held, t)] = rec
        log_test_access("loso_constants", f"fold{fold}")
        out[fold] = {"held_out": held, "mean": c["mean"], "median": c["median"], "files": files,
                     "train_subjects": fd.train_subjects, "n_train_windows": int(tr.sum()),
                     "n_train_nights": n_train_nights, "m_mean": m_mean, "m_med": m_med}
    for t in TARGETS:
        for k in ("mae", "rmse", "bias"):
            um_tm = float(np.mean([out[f]["m_mean"][t][k] for f in out]))
            um_tcn = float(np.mean([seedmeans[(out[f]["held_out"], t)][k] for f in out]))
            checks.num("loso", f"training_mean_{k}_unweighted_mean", um_tm,
                       float(summ[("training_mean", t, k)]["unweighted_subject_mean"]), target=t)
            checks.num("loso", f"raw_tcn_{k}_unweighted_mean", um_tcn,
                       float(summ[("tcn_raw", t, k)]["unweighted_subject_mean"]), target=t)
    tables["_loso_seedmeans"] = seedmeans
    return out


# ------------------------------------------------------------------------------------------------ personalization

def rq2_part(sess, checks: Checks, tables: dict, loso: dict) -> dict:
    """R6–R11 and the primary-span medians."""
    plan = P5.frozen_plan()
    sel = P5.p3_selection()
    primary_from = int(load_protocol()["personalization"]["primary_test_from_ordinal"])
    counts_tab = {(r["subject_id"], int(r["budget_nights"])): r for r in read_csv(tables_dir() / "p5_budget_counts.csv")}
    p5_tab = {(r["subject_id"], int(r["budget_nights"]), int(r["seed"]), r["target"]): r
              for r in read_csv(tables_dir() / "p5_by_seed.csv") if r["span"] == "primary"}
    p8_rows = read_csv(output_root_frozen_p8() / "p8_by_seed.csv")
    p8 = {(r["subject_id"], r["target"], int(r["budget_nights"]), r["predictor"], r["seed"]): r for r in p8_rows
          if r["eval_scope"] == "all" and r["calibration"] in ("none", "pooled")}
    files = {}
    for subject, fold in sorted(P5.subject_folds().items(), key=lambda kv: kv[1]):
        rec = plan["subjects"][subject]
        if rec["base_selection_sha256"] != sel["folds"][fold]["selection_sha256"]:
            raise P10Error("P3 selection differs from the committed P5 plan")
        ctx = dict(subject_id=subject, fold=fold)
        sw0 = sess.windows(subject, 0)
        te0 = sw0.mask("test")
        prim0 = sw0.primary[te0]
        checks.exact("rq2", "primary_windows_digest", sw0.primary_digest() == rec["primary_test"]["windows_sha256"],
                     **ctx)
        y = sw0.targets[te0][prim0]
        prov = {k: v[te0][prim0] for k, v in sw0.prov.items()}
        keys = P8.window_keys(prov["device_id"], prov["window_start"])
        nights = prov["night_id"].astype(str)
        n_w, n_n = int(y.shape[0]), int(np.unique(nights).size)
        ct0 = counts_tab[(subject, 0)]
        checks.exact("rq2", "primary_test_windows", n_w == int(ct0["primary_test_windows"]), n_w,
                     ct0["primary_test_windows"], **ctx)
        checks.exact("rq2", "primary_test_nights", n_n == int(ct0["primary_test_nights"]), n_n,
                     ct0["primary_test_nights"], **ctx)
        checks.exact("rq2", "primary_night_ordinals_ge_16", bool((prov["night_ordinal"] >= primary_from).all()), **ctx)
        a = loso[fold]
        const_a = {"A": a["mean"], "A_med": a["median"]}
        for label, cvec in const_a.items():
            mm = point_metrics(y, np.tile(cvec, (n_w, 1)))
            for t in TARGETS:
                if label == "A":
                    for k in ("mae", "rmse", "bias"):
                        checks.num("rq2", f"A_{k}", mm[t][k], float(p8[(subject, t, 0, "A", "")][k]), target=t, **ctx)
                tables["rq2_metrics"].append({"subject_id": subject, "target": t, "budget_nights": 0,
                                              "predictor": label, "seed": "", **mm[t], "n_windows": n_w,
                                              "n_nights": n_n, "fit_windows": a["n_train_windows"],
                                              "fit_nights": a["n_train_nights"], "source": "recomputed"})
        preds = {}
        for s in P5.seeds():
            d0 = P5.run_dir(subject, 0, s)
            if run_status(d0) != "complete":
                raise P10Error(f"P5 run {subject} b0 seed {s} not complete")
            files[f"p5/{subject}/b00_seed{s}"] = sha256_file(d0 / "predictions.parquet")
            yy, pp, pv = strict_pairs(read_predictions(d0 / "predictions.parquet"))
            pm = pv["primary_test"].astype(bool)
            idx = P8.align(keys, P8.window_keys(pv["device_id"][pm], pv["window_start"][pm]))
            ok, bad = keys_equal({k: v[pm][idx] for k, v in pv.items()}, prov,
                                 fields=KEY_FIELDS)
            checks.exact("rq2", "C_prediction_keys", ok, bad, "ok", seed=s, **ctx)
            checks.exact("rq2", "C_y_true", bool(np.array_equal(yy[pm][idx], y)), seed=s, **ctx)
            preds[("C", 0, s)] = pp[pm][idx]
        for b in (x for x in P5.budgets() if x > 0):
            ctx_b = dict(budget_nights=b, **ctx)
            nights_b = P5.budget_nights(sess.pers(), subject, b)
            checks.exact("rq2", "adaptation_and_buffer_nights_equal_plan",
                         nights_b["adaptation"] == rec["budgets"][b]["adaptation_nights"]
                         and nights_b["buffer"] == rec["budgets"][b]["buffer_nights"], **ctx_b)
            swb = sess.windows(subject, b)
            ad, te = swb.mask("adaptation"), swb.mask("test")
            primb = te & swb.primary
            d = run_root() / "rq2" / subject / f"b{b:02d}"
            sess.gate(d, RunContext("personalization", subject=subject, budget=b, input_features=list(RAW_FEATURES),
                                    fit_records=[{"transform": "training_mean", "partition": "train",
                                                  "subjects": a["train_subjects"]},
                                                 {"transform": "training_median", "partition": "train",
                                                  "subjects": a["train_subjects"]}],
                                    selection_subjects=[], window_groups=swb.window_groups(ad | te)))
            fw = P8.fit_window_checks(swb, nights_b, ad, b, primary_from)
            for chk in fw:
                checks.exact("rq2", f"fit_windows:{chk['check']}", chk["passed"], chk["detail"], "ok", **ctx_b)
            ct = counts_tab[(subject, b)]
            n_ad = int(ad.sum())
            n_ad_nights = int(np.unique(swb.prov["night_id"][ad].astype(str)).size)
            checks.exact("rq2", "adaptation_windows", n_ad == int(ct["adaptation_windows"]), n_ad,
                         ct["adaptation_windows"], **ctx_b)
            idx = P8.align(keys, P8.window_keys(swb.prov["device_id"][primb], swb.prov["window_start"][primb]))
            checks.exact("rq2", "primary_targets_equal_b0", bool(np.array_equal(swb.targets[primb][idx], y)), **ctx_b)
            cb = constants(swb.targets[ad])
            for i, t in enumerate(TARGETS):
                off = float(p8[(subject, t, b, "B", "")]["offset"])
                checks.num("rq2", "B_adaptation_mean_as_A_plus_offset", cb["mean"][i], a["mean"][i] + off, target=t,
                           **ctx_b)
            for label, cvec in (("B", cb["mean"]), ("B_med", cb["median"])):
                mm = point_metrics(y, np.tile(cvec, (n_w, 1)))
                for i, t in enumerate(TARGETS):
                    if label == "B":
                        for k in ("mae", "rmse", "bias"):
                            checks.num("rq2", f"B_{k}", mm[t][k], float(p8[(subject, t, b, "B", "")][k]), target=t,
                                       **ctx_b)
                        fwn = int(p8[(subject, t, b, "B", "")]["fit_windows"])
                        checks.exact("rq2", "B_fit_windows", fwn == n_ad, n_ad, fwn, target=t, **ctx_b)
                    tables["rq2_constants"].append({"subject_id": subject, "budget_nights": b, "statistic":
                                                    "adaptation_mean" if label == "B" else "adaptation_median",
                                                    "target": t, "value": float(cvec[i]), "n_fit_windows": n_ad,
                                                    "n_fit_nights": n_ad_nights,
                                                    "adaptation_nights_in_split": len(nights_b["adaptation"])})
                    tables["rq2_metrics"].append({"subject_id": subject, "target": t, "budget_nights": b,
                                                  "predictor": label, "seed": "", **mm[t], "n_windows": n_w,
                                                  "n_nights": n_n, "fit_windows": n_ad, "fit_nights": n_ad_nights,
                                                  "source": "recomputed"})
            for s in P5.seeds():
                dd = P5.run_dir(subject, b, s)
                if run_status(dd) != "complete":
                    raise P10Error(f"P5 run {subject} b{b} seed {s} not complete")
                files[f"p5/{subject}/b{b:02d}_seed{s}"] = sha256_file(dd / "predictions.parquet")
                yy, pp, pv = strict_pairs(read_predictions(dd / "predictions.parquet"))
                pm = pv["primary_test"].astype(bool)
                ie = P8.align(keys, P8.window_keys(pv["device_id"][pm], pv["window_start"][pm]))
                ok, bad = keys_equal({k: v[pm][ie] for k, v in pv.items()}, prov,
                                     fields=KEY_FIELDS)
                checks.exact("rq2", "E_prediction_keys", ok, bad, "ok", seed=s, **ctx_b)
                checks.exact("rq2", "E_y_true", bool(np.array_equal(yy[pm][ie], y)), seed=s, **ctx_b)
                preds[("E", b, s)] = pp[pm][ie]
        for s in P5.seeds():
            d = P8.control_dir(subject, s)
            if run_status(d) != "complete":
                raise P10Error(f"P8 control {subject} seed {s} not complete")
            files[f"p8_posthoc/init_control/{subject}/b14_seed{s}"] = sha256_file(d / "predictions.parquet")
            yy, pp, pv = strict_pairs(read_predictions(d / "predictions.parquet"))
            pm = pv["primary_test"].astype(bool)
            i_s = P8.align(keys, P8.window_keys(pv["device_id"][pm], pv["window_start"][pm]))
            ok, bad = keys_equal({k: v[pm][i_s] for k, v in pv.items()}, prov)
            checks.exact("rq2", "S_prediction_keys", ok, bad, "ok", seed=s, **ctx)
            checks.exact("rq2", "S_y_true", bool(np.array_equal(yy[pm][i_s], y)), seed=s, **ctx)
            preds[("S", 14, s)] = pp[pm][i_s]
        for (label, b, s), p in sorted(preds.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
            mm = point_metrics(y, p)
            for t in TARGETS:
                for k in ("mae", "rmse", "bias"):
                    checks.num("rq2", f"{label}_{k}_vs_p8", mm[t][k], float(p8[(subject, t, b, label, str(s))][k]),
                               target=t, budget_nights=b, seed=s, **ctx)
                    if label in ("C", "E"):
                        checks.num("rq2", f"{label}_{k}_vs_p5", mm[t][k], float(p5_tab[(subject, b, s, t)][k]),
                                   target=t, budget_nights=b, seed=s, **ctx)
                tables["rq2_metrics"].append({"subject_id": subject, "target": t, "budget_nights": b,
                                              "predictor": label, "seed": s, **mm[t], "n_windows": n_w,
                                              "n_nights": n_n, "fit_windows": "", "fit_nights": "",
                                              "source": "frozen_predictions"})
        for b in (x for x in P5.budgets() if x > 0):
            for s in P5.seeds():
                for t in TARGETS:
                    r = p8[(subject, t, b, "D", str(s))]
                    tables["rq2_metrics"].append({"subject_id": subject, "target": t, "budget_nights": b,
                                                  "predictor": "D", "seed": s, "mae": float(r["mae"]),
                                                  "rmse": float(r["rmse"]), "bias": float(r["bias"]),
                                                  "n_windows": int(r["n_windows"]), "n_nights": int(r["n_nights"]),
                                                  "fit_windows": r["fit_windows"], "fit_nights": "",
                                                  "source": "reused_p8_by_seed"})
        log_test_access("rq2_constants", subject)
    return files


def output_root_frozen_p8() -> Path:
    """The frozen v1.1 metrics (never P10's own output root)."""
    return paths.PROJECT_ROOT / "outputs" / "metrics" / "p8_posthoc"


# ------------------------------------------------------------------------------------------------ summaries

def seed_mean_rows(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        if r["seed"] in ("", "mean"):
            continue
        groups.setdefault(tuple(r[k] for k in keys), []).append(r)
    out = []
    for key, rs in groups.items():
        rec = dict(zip(keys, key))
        for k in ("mae", "rmse", "bias"):
            v = np.array([float(r[k]) for r in rs])
            rec[k] = float(v.mean())
            if k == "mae":
                rec["mae_seed_sd"] = float(v.std(ddof=1)) if len(v) > 1 else ""
                rec["mae_seed_min"], rec["mae_seed_max"] = float(v.min()), float(v.max())
        rec.update(seed="mean", n_seeds=len(rs), n_windows=rs[0]["n_windows"], n_nights=rs[0]["n_nights"],
                   source=rs[0]["source"])
        out.append(rec)
    return out


def rq2_summary(rows: list[dict]) -> list[dict]:
    const = [dict(r, n_seeds=1) for r in rows if r["seed"] == ""]
    return const + seed_mean_rows(rows, ("subject_id", "target", "budget_nights", "predictor"))


def point_counts(loso_rows: list[dict], rq2_sum: list[dict], interp_rows: list[dict], checks: Checks) -> list[dict]:
    """Descriptive point-estimate counts (plan §4); the frozen 12/24 is re-derived and checked (R11)."""
    lm = {(r["subject_id"], r["target"], r["predictor"], str(r["seed"])): float(r["mae"]) for r in loso_rows}
    sm = {(r["subject_id"], r["target"], int(r["budget_nights"]), r["predictor"]): float(r["mae"]) for r in rq2_sum}
    subjects = sorted({r["subject_id"] for r in rq2_sum})
    defs = []
    cells = [(s, t) for s in subjects for t in TARGETS]
    for const in ("training_mean", "training_median"):
        pairs = [(lm[(s, t, const, "")], lm[(s, t, "raw_tcn", "mean")]) for s, t in cells]
        defs.append({"setting": "strict_loso_all_windows", "comparison": f"{const} MAE <= RAW-TCN seed-mean MAE",
                     "cells": len(pairs), "count": count_le(pairs),
                     "cells_true": ";".join(f"{s}/{t}" for (s, t), p in zip(cells, pairs) if p[0] <= p[1])})
    for const in ("A", "A_med"):
        pairs = [(sm[(s, t, 0, const)], sm[(s, t, 0, "C")]) for s, t in cells]
        defs.append({"setting": "rq2_primary_span", "comparison": f"{const} MAE <= C (base, b = 0) seed-mean MAE",
                     "cells": len(pairs), "count": count_le(pairs),
                     "cells_true": ";".join(f"{s}/{t}" for (s, t), p in zip(cells, pairs) if p[0] <= p[1])})
    cells24 = [(s, t, b) for s in subjects for t in TARGETS for b in (1, 3, 7, 14)]
    for const in ("B", "B_med"):
        pairs = [(sm[(s, t, b, const)], sm[(s, t, b, "E")]) for s, t, b in cells24]
        defs.append({"setting": "rq2_primary_span", "comparison": f"{const} MAE <= E (fine-tuning) seed-mean MAE",
                     "cells": len(pairs), "count": count_le(pairs),
                     "cells_true": ";".join(f"{s}/{t}/b{b}" for (s, t, b), p in zip(cells24, pairs) if p[0] <= p[1])})
        b14 = [(sm[(s, t, 14, const)], sm[(s, t, 14, "E")]) for s in subjects for t in TARGETS]
        defs.append({"setting": "rq2_primary_span_b14", "comparison": f"{const} MAE <= E (fine-tuning) seed-mean MAE",
                     "cells": len(b14), "count": count_le(b14), "cells_true": ""})
    frozen = {(r["subject_id"], r["target"], int(r["budget_nights"])): r for r in interp_rows}
    for s, t, b in cells24:
        fr = frozen[(s, t, b)]
        checks.num("counts", "mae_B_vs_interpretation", sm[(s, t, b, "B")], float(fr["mae_B"]), subject_id=s, target=t,
                   budget_nights=b)
        checks.num("counts", "mae_E_vs_interpretation", sm[(s, t, b, "E")], float(fr["mae_E"]), subject_id=s, target=t,
                   budget_nights=b)
        checks.exact("counts", "case_A_B_le_E_flag", (sm[(s, t, b, "B")] <= sm[(s, t, b, "E")]) ==
                     (fr["case_A_B_le_E"] == "True"), subject_id=s, target=t, budget_nights=b)
    n_frozen = sum(1 for r in interp_rows if r["case_A_B_le_E"] == "True")
    got = [d for d in defs if d["comparison"].startswith("B MAE") and d["setting"] == "rq2_primary_span"][0]["count"]
    checks.exact("counts", "B_le_E_total_equals_frozen", got == n_frozen, got, n_frozen)
    for d in defs:
        d["definition"] = "point estimate: constant MAE <= neural seed-mean MAE; not non-inferiority, equivalence or " \
                          "absence of a difference"
    return defs


# ------------------------------------------------------------------------------------------------------ analysis

def analyse(sess) -> tuple[dict[str, list[dict]], dict]:
    load_config()
    checks = Checks()
    tables: dict[str, list] = {"loso_constants": [], "loso_metrics": [], "rq2_constants": [], "rq2_metrics": []}
    loso = loso_part(sess, checks, tables)
    seedmeans = tables.pop("_loso_seedmeans")
    files = rq2_part(sess, checks, tables, loso)
    tables["rq2_summary"] = rq2_summary(tables["rq2_metrics"])
    tables["point_counts"] = point_counts(tables["loso_metrics"], tables["rq2_summary"],
                                          read_csv(tables_dir() / "p8_interpretation_cases.csv"), checks)
    tables["reproduction_check"] = checks.rows
    frozen_tables = ["p3_training_mean_by_fold.csv", "p3_tcn_outer_by_seed.csv", "p3_primary_summary.csv",
                     "p5_by_seed.csv", "p5_budget_counts.csv", "p8_calibration_by_seed.csv",
                     "p8_interpretation_cases.csv"]
    prov = {"design": design_hashes(), "generated_at": now(), **P3.frozen_inputs(), **P5.p5_git_state(),
            "reproduction_passed": checks.passed, "n_checks": len(checks.rows), "n_failed": len(checks.failures()),
            "max_abs_diff": max((r["abs_diff"] for r in checks.rows if r["kind"] == "float"), default=0.0),
            "tolerance": {"abs": TOL_ABS, "rel": TOL_REL},
            "frozen_tables_sha256": {n: sha256_file(tables_dir() / n) for n in frozen_tables},
            "frozen_p8_by_seed_sha256": sha256_file(output_root_frozen_p8() / "p8_by_seed.csv"),
            "p3_selection_sha256_lf": S.file_sha256_lf(P3.selected_yaml()),
            "p5_plan_sha256_lf": S.file_sha256_lf(P5.plan_yaml()),
            "prediction_files_sha256": {**{f"p3/fold{f}/{k}": v for f, rec in loso.items()
                                           for k, v in rec["files"].items()}, **files},
            "loso_seed_means": {f"{s}|{t}": v for (s, t), v in seedmeans.items()}}
    return tables, prov


def write_tables(tables: dict[str, list[dict]], prov: dict) -> Path:
    """Write the tables. If the reproduction check failed, only the check table and the provenance are written (plan
    §3: a failure stops P10 before any new result is produced)."""
    out = metrics_dir()
    if not prov["reproduction_passed"]:
        tables = {"reproduction_check": tables["reproduction_check"]}
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r)) or ["none"]
        write_csv(out / f"p10_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    write_json(out / "p10_level_baselines_provenance.json", prov)
    return out
