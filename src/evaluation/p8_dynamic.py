"""P8 final dynamic-signal diagnostic (protocol v1.2 addendum; D-059; docs/P8_DYNAMIC_SIGNAL_PLAN.md).

Second-order post hoc: conceived after the P3–P6 results and the v1.1 post-hoc results were known. It evaluates,
on the existing RQ2 primary-span predictions (nothing retrained), whether the neural predictions co-vary with the
target beyond a level offset:
- R = SD(e)/SD(y), Q = SD(ŷ)/SD(y) (population SDs), with R² = 1 + Q² − 2·r·Q checked for every row;
- r_pooled = corr(ŷ, y); r_within = corr of night-centred ŷ and y concatenated over nights (primary tracking
  diagnostic); r_within_mat = the same centred within night × mat (sensitivity; differs only for User02);
- per-night correlations (supplementary; eligibility fixed in the plan);
- R_oracle_affine = √max(0, 1 − r_pooled²), a retrospective oracle (an affine map fitted on test labels would be
  leakage), never a performance endpoint;
- the P6 night-cluster bootstrap (shared resampled nights per subject) for the correlations;
- the pre-registered case map J1–J8 and the affine-calibration trigger. Only if the trigger fires, the
  adaptation-only affine calibration F (fitted on adaptation windows; gate and fit-window checks first).
Constant predictions have Q = 0, R = 1 and correlations NA (never 0).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from src.data import paths
from src.data.io_guard import open_for_write, write_csv, write_json
from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P5
from src.evaluation import p6_robustness as P6
from src.evaluation import p8_posthoc as P8
from src.evaluation import splits as S
from src.evaluation.leakage import RunContext
from src.evaluation.metrics import TARGETS, bias, mae, rmse
from src.evaluation.p3_loso import now, read_predictions, run_status, sha256_file
from src.evaluation.protocol import load_protocol, protocol_sha256
from src.features.pressure_features import RAW_FEATURES

VERSION = "v1.2"
STATUS = "post_hoc_second_order_diagnostic"
CONST_TOL = 1e-12
IDENTITY_TOL = 1e-9
CONSISTENCY_TOL = 1e-9
MIN_NIGHT_WINDOWS = 10
R_POS_MIN = 0.10
Q_ZERO_BELOW = 0.10
R_ONE_BAND = (0.95, 1.05)
ORACLE_NEAR_ONE = 0.95
ORACLE_HEADROOM = 0.90
CONDITIONS = {"C": (0,), "D": (1, 3, 7, 14), "E": (1, 3, 7, 14), "S": (14,)}
NAMES = {"A": "training_mean", "B": "adaptation_target_mean", "C": "raw_tcn_base", "D": "raw_tcn_bias_calibrated",
         "E": "full_fine_tuning", "S": "scratch_initialization_control", "F": "adaptation_only_affine_calibration"}
STATS = ("r_pooled", "r_within", "r_within_mat")


class P8DynamicError(RuntimeError):
    pass


# ---------------------------------------------------------------------------------------------- design / paths

def plan_doc() -> Path:
    return paths.PROJECT_ROOT / "docs" / "P8_DYNAMIC_SIGNAL_PLAN.md"


def config_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / VERSION / "dynamic_signal_diagnostic.yaml"


def load_config() -> dict:
    """The v1.2 addendum, checked against the frozen v1.0 protocol and the v1.1 addendum it builds on."""
    doc = yaml.safe_load(config_yaml().read_text(encoding="utf-8"))
    problems = []
    if doc.get("protocol_version") != VERSION or doc.get("decision") != "D-059":
        problems.append("addendum version/decision")
    if doc["base_protocol"]["sha256"] != protocol_sha256():
        problems.append("v1.0 protocol file differs from the hash v1.2 builds on")
    prev = doc["previous_addendum"]
    if prev["sha256_lf"] != S.file_sha256_lf(P8.addendum_yaml()) or prev["plan_sha256_lf"] != \
            S.file_sha256_lf(P8.plan_doc()):
        problems.append("v1.1 addendum or plan differs from the hash v1.2 builds on")
    if doc["subjects"] != sorted(P5.subject_folds()) or doc["seeds"] != P5.seeds():
        problems.append("subjects/seeds differ from v1.0")
    if doc["primary_test_from_ordinal"] != int(load_protocol()["personalization"]["primary_test_from_ordinal"]):
        problems.append("primary span differs from v1.0")
    resamples, seed, level = P6.bootstrap_settings()
    bt = doc["bootstrap"]
    if (bt["resamples"], bt["seed"], bt["level"], bt["primary_model_seed"]) != (resamples, seed, level,
                                                                                 P6.PRIMARY_SEED):
        problems.append("bootstrap settings differ from v1.0 / P6")
    d = doc["definitions"]
    if (d["r_positive"]["seed_mean_min"], d["q_zero_below"], tuple(d["r_one_band"]), d["oracle_near_one_from"],
            d["oracle_headroom_at_most"]) != (R_POS_MIN, Q_ZERO_BELOW, R_ONE_BAND, ORACLE_NEAR_ONE, ORACLE_HEADROOM):
        problems.append("operational thresholds differ from the plan")
    if doc["affine_trigger"]["oracle_affine_at_most"] != ORACLE_HEADROOM:
        problems.append("affine trigger differs from the plan")
    if problems:
        raise P8DynamicError("v1.2 addendum check failed: " + "; ".join(problems))
    return doc


def design_hashes() -> dict:
    return {"protocol_version": VERSION, "decision": "D-059", "status": STATUS,
            "plan_sha256_lf": S.file_sha256_lf(plan_doc()), "config_sha256_lf": S.file_sha256_lf(config_yaml()),
            "base_protocol_sha256": protocol_sha256(),
            "v1_1_addendum_sha256_lf": S.file_sha256_lf(P8.addendum_yaml()),
            "v1_1_plan_sha256_lf": S.file_sha256_lf(P8.plan_doc())}


_OUTPUT_ROOT: Path | None = None


def set_output_root(root: Path | None) -> None:
    global _OUTPUT_ROOT
    _OUTPUT_ROOT = None if root is None else Path(root)


def output_root() -> Path:
    return _OUTPUT_ROOT if _OUTPUT_ROOT is not None else paths.PROJECT_ROOT / "outputs"


def run_root() -> Path:
    return output_root() / "runs" / "p8_dynamic"


def metrics_dir() -> Path:
    return output_root() / "metrics" / "p8_dynamic"


def log_test_access(analysis: str, subject: str) -> None:
    with open_for_write(run_root() / "test_access.jsonl", "a") as fh:
        fh.write(json.dumps({"at": now(), "analysis": analysis, "subject": subject, **design_hashes()}) + "\n")


# ------------------------------------------------------------------------------------------------ pure metrics

def is_constant(p: np.ndarray) -> bool:
    p = np.asarray(p, np.float64)
    return bool(np.std(p) <= CONST_TOL * max(1.0, abs(float(np.mean(p)))))


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation with population moments; NA if the first array is constant or the second has no variance."""
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    if is_constant(a) or np.std(b) <= CONST_TOL:
        return float("nan")
    da, db = a - a.mean(), b - b.mean()
    return float((da * db).sum() / np.sqrt((da * da).sum() * (db * db).sum()))


def _centre(x: np.ndarray, groups: np.ndarray) -> np.ndarray:
    uniq, inv = np.unique(np.asarray(groups).astype(str), return_inverse=True)
    inv = inv.reshape(-1)
    means = np.bincount(inv, weights=x) / np.bincount(inv)
    return x - means[inv]


def signal_stats(y: np.ndarray, p: np.ndarray, nights: np.ndarray, mats: np.ndarray | None = None) -> dict:
    """R, Q, pooled / night-centred / night × mat-centred correlations and the oracle ratio for one target."""
    y, p = np.asarray(y, np.float64), np.asarray(p, np.float64)
    nights = np.asarray(nights).astype(str)
    mats = np.zeros(y.size).astype(str) if mats is None else np.asarray(mats).astype(str)
    sd_y = float(np.std(y))
    if sd_y <= CONST_TOL:
        raise P8DynamicError("target without variance")
    e = p - y
    const = is_constant(p)
    out = {"R": float(np.std(e)) / sd_y, "Q": 0.0 if const else float(np.std(p)) / sd_y, "constant": const,
           "mae": mae(y, p), "rmse": rmse(y, p), "bias": bias(y, p), "target_sd": sd_y}
    if const:
        out.update(R=1.0 if abs(out["R"] - 1.0) <= IDENTITY_TOL else out["R"], r_pooled=float("nan"),
                   r_within=float("nan"), r_within_mat=float("nan"), r2_pooled=float("nan"),
                   oracle_affine=float("nan"), identity_gap=abs(out["R"] ** 2 - 1.0))
        return out
    r = _corr(p, y)
    out["r_pooled"] = r
    pc, yc = _centre(p, nights), _centre(y, nights)
    out["r_within"] = _corr(pc, yc)
    key = np.char.add(np.char.add(nights, "|"), mats)
    out["r_within_mat"] = _corr(_centre(p, key), _centre(y, key))
    out["r2_pooled"] = r * r
    out["oracle_affine"] = float(np.sqrt(max(0.0, 1.0 - r * r)))
    out["identity_gap"] = abs(out["R"] ** 2 - (1 + out["Q"] ** 2 - 2 * r * out["Q"]))
    return out


def per_night_summary(y: np.ndarray, p: np.ndarray, nights: np.ndarray) -> dict:
    """Median of the eligible nights' correlations and the exclusion counts (supplementary; plan §3)."""
    nights = np.asarray(nights).astype(str)
    rs, few, zy, zp = [], 0, 0, 0
    for n in np.unique(nights):
        m = nights == n
        if m.sum() < MIN_NIGHT_WINDOWS:
            few += 1
            continue
        if np.std(y[m]) <= CONST_TOL:
            zy += 1
            continue
        if np.std(p[m]) <= CONST_TOL:
            zp += 1
            continue
        rs.append(_corr(p[m], y[m]))
    return {"per_night_r_median": float(np.median(rs)) if rs else float("nan"), "n_nights_eligible": len(rs),
            "n_nights_too_few_windows": few, "n_nights_zero_target_sd": zy, "n_nights_zero_prediction_sd": zp,
            "n_nights_total": int(np.unique(nights).size)}


# ---------------------------------------------------------------------------------- bootstrap from night moments

@dataclass
class NightMoments:
    night: np.ndarray               # sorted night ids
    n: np.ndarray
    mp: np.ndarray
    my: np.ndarray
    sxx: np.ndarray                 # within-night centred sums (pred², target², cross)
    syy: np.ndarray
    sxy: np.ndarray
    sxx_m: np.ndarray               # within night × mat centred sums, added over the mats of a night
    syy_m: np.ndarray
    sxy_m: np.ndarray


def night_moments(y: np.ndarray, p: np.ndarray, nights: np.ndarray, mats: np.ndarray | None = None) -> NightMoments:
    y, p = np.asarray(y, np.float64), np.asarray(p, np.float64)
    nights = np.asarray(nights).astype(str)
    mats = np.zeros(y.size).astype(str) if mats is None else np.asarray(mats).astype(str)
    uniq, inv = np.unique(nights, return_inverse=True)
    inv = inv.reshape(-1)
    cnt = np.bincount(inv).astype(np.float64)
    mp, my = np.bincount(inv, weights=p) / cnt, np.bincount(inv, weights=y) / cnt
    pc, yc = p - mp[inv], y - my[inv]
    key = np.char.add(np.char.add(nights, "|"), mats)
    pm, ym = _centre(p, key), _centre(y, key)
    s = lambda w: np.bincount(inv, weights=w, minlength=uniq.size)  # noqa: E731
    return NightMoments(uniq, cnt, mp, my, s(pc * pc), s(yc * yc), s(pc * yc), s(pm * pm), s(ym * ym), s(pm * ym))


def weighted_corrs(counts: np.ndarray, m: NightMoments) -> dict[str, np.ndarray]:
    """Exact pooled / within / within-mat correlations of the resampled data (each drawn night kept whole)."""
    w = np.atleast_2d(counts) * m.n
    tot = w.sum(1, keepdims=True)
    gp, gy = (w * m.mp).sum(1, keepdims=True) / tot, (w * m.my).sum(1, keepdims=True) / tot
    wc = np.atleast_2d(counts)
    sxx = (wc * m.sxx).sum(1) + (w * (m.mp - gp) ** 2).sum(1)
    syy = (wc * m.syy).sum(1) + (w * (m.my - gy) ** 2).sum(1)
    sxy = (wc * m.sxy).sum(1) + (w * (m.mp - gp) * (m.my - gy)).sum(1)
    out = {}
    for name, a, b, c in (("r_pooled", sxx, syy, sxy), ("r_within", (wc * m.sxx).sum(1), (wc * m.syy).sum(1),
                                                         (wc * m.sxy).sum(1)),
                          ("r_within_mat", (wc * m.sxx_m).sum(1), (wc * m.syy_m).sum(1), (wc * m.sxy_m).sum(1))):
        with np.errstate(invalid="ignore", divide="ignore"):
            r = c / np.sqrt(a * b)
        r[(a <= CONST_TOL) | (b <= CONST_TOL)] = np.nan
        out[name] = r
    return out


def interval(stat: np.ndarray, level: float) -> tuple[float, float, int]:
    ok = stat[np.isfinite(stat)]
    if ok.size == 0:
        return float("nan"), float("nan"), int(stat.size)
    lo, hi = P6.interval(ok, level)
    return lo, hi, int(stat.size - ok.size)


# ------------------------------------------------------------------------------------------ prediction assembly

@dataclass
class DynSubject:
    subject: str
    fold: int
    y: np.ndarray
    nights: np.ndarray
    mats: np.ndarray
    keys: np.ndarray
    preds: dict = field(default_factory=dict)       # (condition, budget, seed | None) -> (n, 2)
    sources: dict = field(default_factory=dict)     # source artifact -> SHA-256
    checks: dict = field(default_factory=dict)


def _primary(path: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    y, p, pv = P3._pairs(read_predictions(path))
    m = pv["primary_test"].astype(bool)
    return y[m], p[m], {k: v[m] for k, v in pv.items()}


def _offsets(rows: list[dict], subject: str) -> dict[tuple, np.ndarray]:
    """(predictor, budget, seed | None) -> per-target offset of the frozen v1.1 pooled calibration."""
    out: dict[tuple, dict] = {}
    for r in rows:
        if r["subject_id"] != subject or r["predictor"] not in ("B", "D") or r["calibration"] != "pooled" or \
                r.get("eval_scope", "all") != "all":
            continue
        key = (r["predictor"], int(r["budget_nights"]), None if r["seed"] in ("", None) else int(r["seed"]))
        out.setdefault(key, {})[r["target"]] = float(r["offset"])
    return {k: np.array([v[t] for t in TARGETS]) for k, v in out.items()}


def load_subject(subject: str, offset_rows: list[dict], v11_rows: list[dict]) -> DynSubject:
    """Existing primary-span predictions of one subject, aligned to the C window order (nothing is retrained)."""
    fold = P5.subject_folds()[subject]
    seeds = P5.seeds()
    ref = None
    for s in seeds:
        d = P5.run_dir(subject, 0, s)
        if run_status(d) != "complete":
            raise P8DynamicError(f"P5 base run {subject} seed {s} is not complete")
        y, p, pv = _primary(d / "predictions.parquet")
        keys = P8.window_keys(pv["device_id"], pv["window_start"])
        if ref is None:
            ref = DynSubject(subject, fold, y, pv["night_id"].astype(str), pv["device_id"].astype(str), keys)
        i = P8.align(ref.keys, keys)
        if not np.array_equal(y[i], ref.y):
            raise P8DynamicError(f"{subject}: base targets differ between seeds")
        ref.preds[("C", 0, s)] = p[i]
        ref.sources[f"p5/{subject}/b00_seed{s}"] = sha256_file(d / "predictions.parquet")
    for b in CONDITIONS["E"]:
        for s in seeds:
            d = P5.run_dir(subject, b, s)
            if run_status(d) != "complete":
                raise P8DynamicError(f"P5 run {subject} b={b} seed {s} is not complete")
            y, p, pv = _primary(d / "predictions.parquet")
            i = P8.align(ref.keys, P8.window_keys(pv["device_id"], pv["window_start"]))
            if not np.array_equal(y[i], ref.y):
                raise P8DynamicError(f"{subject} b={b} seed {s}: targets differ from the base run")
            ref.preds[("E", b, s)] = p[i]
            ref.sources[f"p5/{subject}/b{b:02d}_seed{s}"] = sha256_file(d / "predictions.parquet")
    for s in seeds:
        d = P8.control_dir(subject, s)
        if run_status(d) != "complete":
            raise P8DynamicError(f"v1.1 control run {subject} seed {s} is not complete")
        y, p, pv = _primary(d / "predictions.parquet")
        i = P8.align(ref.keys, P8.window_keys(pv["device_id"], pv["window_start"]))
        if not np.array_equal(y[i], ref.y):
            raise P8DynamicError(f"{subject} control seed {s}: targets differ from the base run")
        ref.preds[("S", 14, s)] = p[i]
        ref.sources[f"p8_posthoc/init_control/{subject}/b14_seed{s}"] = sha256_file(d / "predictions.parquet")
    off = _offsets(offset_rows, subject)
    for b in CONDITIONS["D"]:
        for s in seeds:
            ref.preds[("D", b, s)] = ref.preds[("C", 0, s)] + off[("D", b, s)]
    mean, _ = P8.training_mean_value(fold)
    n = ref.y.shape[0]
    ref.preds[("A", 0, None)] = np.tile(mean, (n, 1))
    for b in CONDITIONS["D"]:
        ref.preds[("B", b, None)] = np.tile(mean + off[("B", b, None)], (n, 1))
    ref.checks["frozen_metrics_max_abs_diff"] = _consistency(ref, v11_rows)
    if ref.checks["frozen_metrics_max_abs_diff"] > CONSISTENCY_TOL:
        raise P8DynamicError(f"{subject}: reconstructed predictions do not reproduce the frozen v1.1 metrics")
    return ref


def _consistency(ds: DynSubject, v11_rows: list[dict]) -> float:
    """Largest |difference| of MAE/RMSE/bias against the frozen v1.1 per-seed table (A, B, C, D, E; pooled, all)."""
    ref = {}
    for r in v11_rows:
        if r["subject_id"] == ds.subject and r["calibration"] in ("none", "pooled") and \
                r.get("eval_scope", "all") == "all":
            ref[(r["predictor"], int(r["budget_nights"]), None if r["seed"] in ("", None) else int(r["seed"]),
                 r["target"])] = r
    worst = 0.0
    for (c, b, s), p in ds.preds.items():
        for i, t in enumerate(TARGETS):
            key = (c, b, s, t)
            if key not in ref:
                if c in "ABCDE":
                    raise P8DynamicError(f"frozen v1.1 row missing for {ds.subject} {key}")
                continue
            for k, fn in (("mae", mae), ("rmse", rmse), ("bias", bias)):
                worst = max(worst, abs(fn(ds.y[:, i], p[:, i]) - float(ref[key][k])))
    return worst


# ------------------------------------------------------------------------------------------------------ analysis

def by_seed_rows(ds: DynSubject) -> list[dict]:
    rows = []
    for (c, b, s), p in sorted(ds.preds.items(), key=lambda kv: ("ABCDESF".index(kv[0][0]), kv[0][1],
                                                                  -1 if kv[0][2] is None else kv[0][2])):
        for i, t in enumerate(TARGETS):
            st = signal_stats(ds.y[:, i], p[:, i], ds.nights, ds.mats)
            if not st["constant"] and st["identity_gap"] > IDENTITY_TOL:
                raise P8DynamicError(f"{ds.subject} {c} b={b} seed {s} {t}: identity R² = 1 + Q² − 2rQ fails "
                                     f"({st['identity_gap']:g})")
            pn = per_night_summary(ds.y[:, i], p[:, i], ds.nights) if not st["constant"] else {}
            rows.append({"subject_id": ds.subject, "fold": ds.fold, "target": t, "condition": c,
                         "condition_name": NAMES[c], "budget_nights": b, "seed": "" if s is None else s,
                         **{k: st[k] for k in ("R", "Q", "r_pooled", "r_within", "r_within_mat", "r2_pooled",
                                               "oracle_affine", "identity_gap", "mae", "rmse", "bias",
                                               "target_sd")},
                         "constant_prediction": st["constant"], **pn,
                         "n_windows": int(ds.y.shape[0]), "n_nights": int(np.unique(ds.nights).size),
                         "status": STATUS})
    return rows


def d_equals_c(rows: list[dict]) -> float:
    """D differs from C by a constant: its R, Q and correlations must equal C's (returns the largest difference)."""
    c = {(r["subject_id"], r["target"], r["seed"]): r for r in rows if r["condition"] == "C"}
    worst = 0.0
    for r in rows:
        if r["condition"] != "D":
            continue
        ref = c[(r["subject_id"], r["target"], r["seed"])]
        for k in ("R", "Q", "r_pooled", "r_within", "r_within_mat", "oracle_affine"):
            worst = max(worst, abs(r[k] - ref[k]))
    if worst > IDENTITY_TOL:
        raise P8DynamicError(f"D does not reproduce C's scale and correlation statistics ({worst:g})")
    return worst


def _nanstats(v: list[float]) -> tuple:
    a = np.array(v, np.float64)
    if not np.isfinite(a).any():
        return float("nan"), float("nan"), float("nan")
    return float(np.nanmean(a)), float(np.nanmin(a)), float(np.nanmax(a))


def seed_summary(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["subject_id"], r["target"], r["condition"], r["budget_nights"]), []).append(r)
    out = []
    for (subj, t, c, b), rs in groups.items():
        rec = {"subject_id": subj, "fold": rs[0]["fold"], "target": t, "condition": c, "condition_name": NAMES[c],
               "budget_nights": b, "n_seeds": len(rs)}
        for k in ("R", "Q", "r_pooled", "r_within", "r_within_mat", "oracle_affine", "per_night_r_median", "mae",
                  "rmse", "bias"):
            m, lo, hi = _nanstats([r.get(k, float("nan")) for r in rs])
            rec[k] = m
            if k in ("R", "Q", "r_pooled", "r_within", "r_within_mat", "oracle_affine") and len(rs) > 1:
                rec[f"{k}_seed_min"], rec[f"{k}_seed_max"] = lo, hi
        rec["oracle_affine_seeds_at_most_0_90"] = sum(1 for r in rs if np.isfinite(r["oracle_affine"])
                                                      and r["oracle_affine"] <= ORACLE_HEADROOM)
        rec.update(target_sd=rs[0]["target_sd"], constant_prediction=rs[0]["constant_prediction"],
                   n_nights_eligible=rs[0].get("n_nights_eligible", ""), n_windows=rs[0]["n_windows"],
                   n_nights=rs[0]["n_nights"], status=STATUS)
        out.append(rec)
    return out


def bootstrap_rows(ds: DynSubject) -> list[dict]:
    """Night-cluster bootstrap of the correlations; shared resampled nights for every condition and seed."""
    resamples, rng_seed, level = P6.bootstrap_settings()
    n = np.unique(ds.nights).size
    counts = P6.resample_counts(n, resamples, rng_seed)
    full = np.ones((1, n))
    moments = {k: [night_moments(ds.y[:, i], p[:, i], ds.nights, ds.mats) for i in range(len(TARGETS))]
               for k, p in ds.preds.items() if k[0] in "CDESF" and not is_constant(p[:, 0])}
    rows, boot = [], {}
    for (c, b, s), ms in sorted(moments.items(), key=lambda kv: ("CDESF".index(kv[0][0]), kv[0][1], kv[0][2])):
        for i, t in enumerate(TARGETS):
            pt = weighted_corrs(full, ms[i])
            bt = weighted_corrs(counts, ms[i])
            boot[(c, b, s, t)] = bt
            direct = signal_stats(ds.y[:, i], ds.preds[(c, b, s)][:, i], ds.nights, ds.mats)
            gap = max(abs(float(pt[k][0]) - direct[k]) for k in STATS)
            if gap > CONSISTENCY_TOL:
                raise P8DynamicError(f"night-moment statistics differ from the window-level values ({gap:g})")
            for k in STATS:
                lo, hi, n_na = interval(bt[k], level)
                rows.append({"subject_id": ds.subject, "target": t, "condition": c, "budget_nights": b, "seed": s,
                             "role": "primary" if s == P6.PRIMARY_SEED else "sensitivity", "statistic": k,
                             "point_estimate": float(pt[k][0]), "ci_lower": lo, "ci_upper": hi,
                             "interval": P6.side(lo, hi) if np.isfinite(lo) else "undefined", "n_undefined": n_na,
                             "n_nights": n, "n_resamples": resamples, "rng_seed": rng_seed, "level": level,
                             "status": STATUS})
    for first, second, budgets in (("E", "C", CONDITIONS["E"]), ("S", "E", (14,))):
        for b in budgets:
            for s in P5.seeds():
                for t in TARGETS:
                    fa = boot.get((first, b, s, t))
                    sa = boot.get((second, 0 if second == "C" else b, s, t))
                    if fa is None or sa is None:
                        continue
                    fp = weighted_corrs(full, moments[(first, b, s)][TARGETS.index(t)])["r_within"][0]
                    sp = weighted_corrs(full, moments[(second, 0 if second == "C" else b, s)]
                                        [TARGETS.index(t)])["r_within"][0]
                    lo, hi, n_na = interval(fa["r_within"] - sa["r_within"], level)
                    rows.append({"subject_id": ds.subject, "target": t, "condition": f"{first}-{second}",
                                 "budget_nights": b, "seed": s,
                                 "role": "primary" if s == P6.PRIMARY_SEED else "sensitivity",
                                 "statistic": "delta_r_within", "point_estimate": float(fp - sp), "ci_lower": lo,
                                 "ci_upper": hi, "interval": P6.side(lo, hi) if np.isfinite(lo) else "undefined",
                                 "n_undefined": n_na, "n_nights": n, "n_resamples": resamples, "rng_seed": rng_seed,
                                 "level": level, "status": STATUS})
    return rows


# ------------------------------------------------------------------------------------------ interpretation map

def r_class(seed_mean: float, side: str) -> str:
    """positive / negative / zero (plan §5); 'small' = interval excludes zero but |seed mean| < 0.10."""
    if not np.isfinite(seed_mean):
        return "na"
    if side == "above_zero" and seed_mean >= R_POS_MIN:
        return "positive"
    if side == "below_zero" and seed_mean <= -R_POS_MIN:
        return "negative"
    if side in ("above_zero", "below_zero"):
        return "small"
    return "zero"


def case_rows(summary: list[dict], boot: list[dict]) -> list[dict]:
    side = {(r["subject_id"], r["target"], r["condition"], int(r["budget_nights"]), r["statistic"]): r["interval"]
            for r in boot if r["role"] == "primary" and r["statistic"] in STATS}
    out = []
    for r in summary:
        c, b = r["condition"], int(r["budget_nights"])
        if c not in ("C", "E", "S", "F"):
            continue
        key = (r["subject_id"], r["target"], c, b)
        cls = {k: r_class(r[k], side.get(key + (k,), "undefined")) for k in STATS}
        within_pos = cls["r_within"] == "positive" and (r["subject_id"] != P8.USER02
                                                        or cls["r_within_mat"] == "positive")
        pooled_pos = cls["r_pooled"] == "positive"
        near0 = lambda x: x in ("zero", "small")  # noqa: E731
        q_pos, q_zero = r["Q"] >= Q_ZERO_BELOW, r["Q"] < Q_ZERO_BELOW
        r_one = R_ONE_BAND[0] <= r["R"] <= R_ONE_BAND[1]
        oracle = r["oracle_affine"]
        rec = {"subject_id": r["subject_id"], "target": r["target"], "condition": c, "budget_nights": b,
               "R": r["R"], "Q": r["Q"], "r_pooled": r["r_pooled"], "r_within": r["r_within"],
               "r_within_mat": r["r_within_mat"], "oracle_affine": oracle,
               "class_r_pooled": cls["r_pooled"], "class_r_within": cls["r_within"],
               "class_r_within_mat": cls["r_within_mat"], "within_positive_rule": within_pos,
               "J1": bool(q_pos and near0(cls["r_pooled"]) and near0(cls["r_within"])),
               "J2": bool(pooled_pos and not within_pos and cls["r_within"] != "negative"),
               "J3": bool(pooled_pos and within_pos),
               "J4": bool(cls["r_pooled"] == "negative" or cls["r_within"] == "negative"),
               "J5": bool(r_one and q_zero),
               "J6": bool(r_one and q_pos and (pooled_pos or within_pos)),
               "J7": bool(np.isfinite(oracle) and oracle >= ORACLE_NEAR_ONE),
               "J8_cell": bool(np.isfinite(oracle) and oracle <= ORACLE_HEADROOM),
               "unmapped_within_only": bool(within_pos and not pooled_pos), "status": STATUS}
        out.append(rec)
    return out


def headlines(cases: list[dict]) -> list[dict]:
    out = []
    for c, b in (("C", 0), ("E", 14), ("S", 14)):
        for t in TARGETS:
            rs = [r for r in cases if r["condition"] == c and r["budget_nights"] == b and r["target"] == t]
            within = sum(r["within_positive_rule"] for r in rs)
            pooled = sum(r["class_r_pooled"] == "positive" for r in rs)
            label = ("within-night co-variation supported" if within >= 2 else
                     "only between-night association" if pooled >= 2 else "little linear co-variation")
            out.append({"condition": c, "budget_nights": b, "target": t, "subjects_within_positive": within,
                        "subjects_pooled_positive": pooled, "headline": label, "status": STATUS})
    return out


def trigger(summary: list[dict]) -> dict:
    """Affine trigger (plan §7): base C; cell qualifies with seed mean ≤ 0.90 and ≥ 2 of 3 seeds ≤ 0.90."""
    per_target = {}
    for t in TARGETS:
        cells = [r for r in summary if r["condition"] == "C" and r["target"] == t]
        qual = [r["subject_id"] for r in cells if np.isfinite(r["oracle_affine"])
                and r["oracle_affine"] <= ORACLE_HEADROOM and r["oracle_affine_seeds_at_most_0_90"] >= 2]
        per_target[t] = {"qualifying_subjects": qual, "fires": len(qual) >= 2,
                         "seed_mean_oracle": {r["subject_id"]: r["oracle_affine"] for r in cells}}
    return {"fired": any(v["fires"] for v in per_target.values()), "per_target": per_target,
            "rule": "C; seed-mean R_oracle_affine <= 0.90 and >= 2 of 3 seeds; >= 2 subjects, same target"}


# ------------------------------------------------------------------------------ triggered affine comparator (F)

def affine_fit(y: np.ndarray, p: np.ndarray) -> tuple[float, float, bool]:
    """OLS with intercept of y on p (population moments); degenerate p -> (0, mean(y)), i.e. the B predictor."""
    y, p = np.asarray(y, np.float64), np.asarray(p, np.float64)
    if y.size == 0:
        raise P8DynamicError("no adaptation window for the affine fit")
    if is_constant(p):
        return 0.0, float(y.mean()), True
    a = float(((p - p.mean()) * (y - y.mean())).mean() / p.var())
    return a, float(y.mean() - a * p.mean()), False


def affine_fits(sw, base_adapt: dict[int, np.ndarray]) -> dict:
    """Per seed and target (a, c, degenerate) from the labelled adaptation windows of one budget (User02 pooled)."""
    ad = sw.mask("adaptation")
    y_ad = sw.targets[ad]
    out = {}
    for s, p in base_adapt.items():
        if p.shape != y_ad.shape:
            raise P8DynamicError("base predictions do not cover exactly the adaptation windows")
        out[s] = [affine_fit(y_ad[:, i], p[:, i]) for i in range(len(TARGETS))]
    return {"fits": out, "fit_windows": int(ad.sum()), "fit_mats": sorted(set(sw.prov["device_id"][ad].astype(str)))}


def run_affine(sess, ds: DynSubject) -> list[dict]:
    """F on the primary span: fixed (a, c) fitted on adaptation windows only; gate and fit-window checks first."""
    from src.training.trainer import device, predict_z, set_determinism, to_tensor
    sel = P5.p3_selection()
    scaler = P5.base_scaler(ds.fold, sel)
    mean, mean_subjects = P8.training_mean_value(ds.fold)
    fits_prov = [dict(scaler.fit_provenance), {"transform": "training_mean", "partition": "train",
                                               "subjects": mean_subjects}]
    primary_from = int(load_protocol()["personalization"]["primary_test_from_ordinal"])
    models = {s: P5.base_model(ds.fold, s, sel)[0] for s in P5.seeds()}
    records = []
    for b in CONDITIONS["E"]:
        nights = P5.budget_nights(sess.pers(), ds.subject, b)
        sw = sess.windows(ds.subject, b)
        ad, te = sw.mask("adaptation"), sw.mask("test")
        d = run_root() / "affine" / ds.subject / f"b{b:02d}"
        sess.gate(d, RunContext("personalization", subject=ds.subject, budget=b, input_features=list(RAW_FEATURES),
                                fit_records=fits_prov, selection_subjects=[], window_groups=sw.window_groups(ad | te)))
        checks = P8.fit_window_checks(sw, nights, ad, b, primary_from)
        write_json(d / "affine_checks.json", {"checked_at": now(), "passed": all(c["passed"] for c in checks),
                                              "checks": checks, **design_hashes()})
        if not all(c["passed"] for c in checks):
            raise P8DynamicError(f"{ds.subject} b={b}: affine fit-window checks failed")
        xa = to_tensor(sw.pressure[ad], device())
        base_adapt = {}
        for s, model in models.items():
            set_determinism(s)
            base_adapt[s] = scaler.inverse(predict_z(model, xa))
        fit = affine_fits(sw, base_adapt)
        for s, per_t in fit["fits"].items():
            ds.preds[("F", b, s)] = np.stack([a * ds.preds[("C", 0, s)][:, i] + c for i, (a, c, _) in
                                              enumerate(per_t)], 1)
            for i, (a, c, degenerate) in enumerate(per_t):
                records.append({"subject_id": ds.subject, "target": TARGETS[i], "budget_nights": b, "seed": s,
                                "slope_a": a, "intercept_c": c, "degenerate": degenerate,
                                "fit_windows": fit["fit_windows"], "fit_mats": ";".join(fit["fit_mats"]),
                                "status": "triggered_second_order_post_hoc_comparator"})
    log_test_access("affine", ds.subject)
    return records


def affine_mae_bootstrap(ds: DynSubject) -> list[dict]:
    """Paired night bootstrap of ΔMAE = MAE(F) − MAE(other) for other ∈ {B, D, E} (P6 settings)."""
    resamples, rng_seed, level = P6.bootstrap_settings()
    n = np.unique(ds.nights).size
    counts = P6.resample_counts(n, resamples, rng_seed)
    full = np.ones((1, n))
    rows = []
    for b in CONDITIONS["E"]:
        for s in P5.seeds():
            fa = P8.night_arrays(ds.y, ds.preds[("F", b, s)], ds.nights)
            for other in ("B", "D", "E"):
                oa = P8.night_arrays(ds.y, ds.preds[(other, b, None if other == "B" else s)], ds.nights)
                for t in TARGETS:
                    boot = P6.paired_effects(counts, fa[t], oa[t])["mae"]
                    lo, hi = P6.interval(boot, level)
                    rows.append({"subject_id": ds.subject, "target": t, "budget_nights": b, "seed": s,
                                 "first": "F", "second": other, "role": "primary" if s == P6.PRIMARY_SEED
                                 else "sensitivity",
                                 "point_estimate": float(P6.paired_effects(full, fa[t], oa[t])["mae"][0]),
                                 "ci_lower": lo, "ci_upper": hi, "interval": P6.side(lo, hi), "n_nights": n,
                                 "n_resamples": resamples, "rng_seed": rng_seed, "level": level,
                                 "status": "triggered_second_order_post_hoc_comparator"})
    return rows


# ------------------------------------------------------------------------------------------------------ driver

def analyse(sess=None, offset_rows: list[dict] | None = None, v11_rows: list[dict] | None = None,
            run_affine_if_triggered: bool = True) -> tuple[dict[str, list[dict]], dict]:
    load_config()
    if offset_rows is None:
        offset_rows = P6.read_csv(P6.tables_dir() / "p8_calibration_by_seed.csv")
    v11_rows = offset_rows if v11_rows is None else v11_rows
    subjects = sorted(P5.subject_folds(), key=P5.subject_folds().get)
    data = {}
    for s in subjects:
        data[s] = load_subject(s, offset_rows, v11_rows)
        log_test_access("dynamic_signal", s)
    tables = {"by_seed": [], "bootstrap": []}
    for s in subjects:
        tables["by_seed"] += by_seed_rows(data[s])
        tables["bootstrap"] += bootstrap_rows(data[s])
    prov = {"design": design_hashes(), **P3.git_state(), "checks": {}, "sources_sha256": {}}
    prov["checks"]["d_equals_c_max_abs_diff"] = d_equals_c(tables["by_seed"])
    prov["checks"]["identity_max_gap"] = max(r["identity_gap"] for r in tables["by_seed"]
                                             if not r["constant_prediction"])
    prov["checks"]["constant_rows_R_Q"] = sorted({(round(r["R"], 12), r["Q"]) for r in tables["by_seed"]
                                                  if r["constant_prediction"]})
    for s in subjects:
        prov["checks"][s] = data[s].checks
        prov["sources_sha256"].update(data[s].sources)
    tables["summary"] = seed_summary(tables["by_seed"])
    tables["oracle_affine"] = [{k: r[k] for k in ("subject_id", "target", "condition", "budget_nights", "n_seeds",
                                                  "r_pooled", "oracle_affine", "oracle_affine_seed_min",
                                                  "oracle_affine_seed_max", "oracle_affine_seeds_at_most_0_90",
                                                  "status") if k in r}
                               for r in tables["summary"] if r["condition"] in "CDES"]
    trig = trigger(tables["summary"])
    prov["affine_trigger"] = trig
    if trig["fired"] and run_affine_if_triggered:
        if sess is None:
            sess = P5.P5Session(echo=False)
        fits = []
        for s in subjects:
            fits += run_affine(sess, data[s])
        f_rows = [r for s in subjects for r in by_seed_rows(data[s]) if r["condition"] == "F"]
        tables["affine_fits"] = fits
        tables["affine_by_seed"] = f_rows
        tables["affine_summary"] = seed_summary(f_rows)
        tables["affine_bootstrap"] = [r for s in subjects for r in affine_mae_bootstrap(data[s])]
        tables["bootstrap"] += [r for s in subjects for r in bootstrap_rows(data[s]) if r["condition"] == "F"]
        tables["summary"] += tables["affine_summary"]
    tables["cases"] = case_rows(tables["summary"], tables["bootstrap"])
    tables["headlines"] = headlines(tables["cases"])
    tables["trigger"] = [{"target": t, "qualifying_subjects": ";".join(v["qualifying_subjects"]),
                          "fires": v["fires"], **{f"oracle_{k}": x for k, x in v["seed_mean_oracle"].items()},
                          "status": STATUS} for t, v in trig["per_target"].items()]
    return tables, prov


def write_tables(tables: dict[str, list[dict]], prov: dict) -> Path:
    out = metrics_dir()
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r)) or ["none"]
        write_csv(out / f"p8_dynamic_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    write_json(out / "p8_dynamic_provenance.json", prov)
    return out
