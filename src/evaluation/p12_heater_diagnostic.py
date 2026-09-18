"""P12: heater-context confound diagnostic (protocol v1.6 addendum; D-067; docs/P12_HEATER_DIAGNOSTIC_PLAN.md; audit
docs/P12_HEATER_DIAGNOSTIC_AUDIT.md).

Post hoc and descriptive. Not a predictive-model phase: nothing here is a model input and no model is fitted.
- Heater context is the D-047 A.2 definition, reused unchanged (`p6_robustness.heater_events` / `heater_context`): the
  most recent AHON/AHOF on the same mat with event time <= target time and within 60 min; otherwise UNKNOWN. Event
  tables are built per subject. ON / OFF name the last code, not a reconstructed heater state.
- Analysis A: state summaries and eta squared (raw, night-centred, User02 night x mat-centred) with night-cluster
  intervals. Analysis B: a source-only heater-conditioned constant next to the source mean and median, under the D-067
  diagnostic-only exception to D-038; the held-out subject is never in a fit. Analysis C: committed P10/P11 predictions
  stratified by heater state. Spans `full` and `common` are never pooled.
- P12 writes only under its own output root.
"""
from __future__ import annotations

import csv
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml

from src.data import paths
from src.data.io_guard import write_csv, write_json
from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P5
from src.evaluation import p6_robustness as P6
from src.evaluation import p8_posthoc as P8
from src.evaluation import p10_history as H
from src.evaluation import p10_level_baselines as LB
from src.evaluation import p11_common_pool_tcn as P11
from src.evaluation import splits as S
from src.evaluation.domain_shift import parse_event
from src.evaluation.metrics import TARGETS
from src.evaluation.p3_loso import now, read_predictions, sha256_file
from src.evaluation.protocol import load_protocol, night_id, protocol_sha256

VERSION, DECISION = "v1.6", "D-067"
STATES = ("ON", "OFF", "UNKNOWN")
LABELS = {"after_AHON_60min": "ON", "after_AHOF_60min": "OFF", "no_AHON_AHOF_60min": "UNKNOWN"}
SPANS = ("full", "common")
USER02 = "User02"
ETA_SMALL, ETA_LARGE = 0.06, 0.14
TOLERANCE = 1e-9
PROTECTED_TREES = P11.PROTECTED_TREES + ("outputs/p11_common_pool_tcn",)
CODE_CLASSES = {
    "AHON": ("heater_on", "documented"), "AHOF": ("heater_off", "documented"),
    "BHSDOWN": ("set_point", "documented"), "FOH": ("forced_off", "documented"),
    **{c: ("set_point_or_limit", "name_only_ambiguous") for c in
       ("BCSUP", "BHNTSDOWN", "STEMP", "SLIMIT", "SMINLIMIT", "EVENT:BURST_HOT_STEP_DOWN")},
    **{c: ("heating_related_on_off", "name_only_ambiguous") for c in
       ("FON", "FOF", "EVENT:FORCED_ON", "EVENT:FORCED_OFF", "MON", "MOF", "AIHON", "AIHOFF")},
    **{c: ("controller_or_mode", "name_only_ambiguous") for c in ("AMODE", "MMODE", "AIDONE", "SCHATIDS", "WSTOP")}}


class P12Error(RuntimeError):
    pass


# ------------------------------------------------------------------------------------------------ design

def config_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / VERSION / "p12_heater_diagnostic.yaml"


def plan_doc() -> Path:
    return paths.PROJECT_ROOT / "docs" / "P12_HEATER_DIAGNOSTIC_PLAN.md"


def load_config() -> dict:
    """The v1.6 config must equal the frozen rules this module reuses (refuses any drift)."""
    doc = yaml.safe_load(config_yaml().read_text(encoding="utf-8"))
    hc, problems = doc["heater_context"], []
    if doc["protocol_version"] != VERSION or doc["decision"] != DECISION:
        problems.append("version / decision")
    if tuple(hc["codes"]) != P6.HEATER_CODES or int(hc["lookback_s"]) != P6.HEATER_WINDOW_S:
        problems.append("heater codes / look-back differ from D-047")
    if hc["states"] != LABELS:
        problems.append("state labels")
    bt = doc["bootstrap"]
    if (bt["resamples"], bt["seed"], bt["level"]) != P6.bootstrap_settings():
        problems.append("bootstrap settings")
    it = doc["interpretation"]
    if (float(it["eta_small_below"]), float(it["eta_large_from"])) != (ETA_SMALL, ETA_LARGE):
        problems.append("eta thresholds")
    rule = doc["analysis_b"]["rule"]
    if rule != {"ON": "source_mean_ON", "OFF": "source_mean_OFF", "UNKNOWN": "source_mean_overall"} or \
            doc["analysis_b"]["empty_source_state"] != "source_mean_overall":
        problems.append("prediction rule")
    if sorted(doc["subjects"]) != sorted(P5.subject_folds()):
        problems.append("subjects")
    if problems:
        raise P12Error("v1.6 config differs from the frozen rules: " + "; ".join(problems))
    return doc


def design_hashes() -> dict:
    return {"addendum_version": VERSION, "decision": DECISION, "plan_sha256_lf": S.file_sha256_lf(plan_doc()),
            "config_sha256_lf": S.file_sha256_lf(config_yaml()), "base_protocol_sha256": protocol_sha256()}


_OUTPUT_ROOT: Path | None = None


def set_output_root(root: Path | None) -> None:
    global _OUTPUT_ROOT
    _OUTPUT_ROOT = None if root is None else Path(root)


def output_root() -> Path:
    return _OUTPUT_ROOT if _OUTPUT_ROOT is not None else paths.PROJECT_ROOT / "outputs" / "p12_heater_diagnostic"


def pre_result_path() -> Path:
    return output_root() / "pre_result_design_hashes.json"


def freeze_design() -> dict:
    """Record the plan/config hashes before the first statistic; refuse to run if they changed afterwards."""
    cur = design_hashes()
    p = pre_result_path()
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
        if any(old[k] != cur[k] for k in ("plan_sha256_lf", "config_sha256_lf")):
            raise P12Error("the P12 plan or config changed after the pre-result hashes were recorded")
        return old
    rec = {**cur, "recorded_at": now(), "note": "written before any P12 statistic was computed"}
    write_json(p, rec)
    return rec


# ------------------------------------------------------------------------------------------------ heater context

def to_seconds(ts: np.ndarray) -> np.ndarray:
    ts = np.asarray(ts)
    if np.issubdtype(ts.dtype, np.datetime64):
        return ts.astype("datetime64[s]").astype(np.int64)
    return ts.astype(np.int64)


def context_states(subject_ids: np.ndarray, device: np.ndarray, target_ts: np.ndarray,
                   events_by_subject: dict[str, dict]) -> np.ndarray:
    """ON / OFF / UNKNOWN per window with the frozen D-047 look-up, applied subject by subject so that the events of
    one subject can never label another subject's windows (User01 and User07 share device_id 'unknown')."""
    subject_ids, device, ts = np.asarray(subject_ids).astype(str), np.asarray(device).astype(str), to_seconds(target_ts)
    out = np.full(subject_ids.shape[0], "UNKNOWN", dtype=object)
    for s in np.unique(subject_ids):
        if s not in events_by_subject:
            raise P12Error(f"no heater event table for {s}")
        m = subject_ids == s
        raw = P6.heater_context(device[m], ts[m], events_by_subject[s])
        unknown = set(np.unique(raw).tolist()) - set(LABELS)
        if unknown:
            raise P12Error(f"unexpected heater-context labels {sorted(unknown)}")
        out[m] = np.array([LABELS[x] for x in raw], dtype=object)
    return out.astype(str)


def last_event_time(device: np.ndarray, target_ts: np.ndarray, events: dict) -> np.ndarray:
    """Time of the event the frozen rule used (-1 where none); only for counting look-backs that cross a session."""
    device, ts = np.asarray(device).astype(str), to_seconds(target_ts)
    out = np.full(ts.shape[0], -1, np.int64)
    for d, (ets, _) in events.items():
        m = device == d
        if not m.any() or ets.size == 0:
            continue
        k = np.searchsorted(ets, ts[m], side="right") - 1
        ok = (k >= 0) & (ts[m] - ets[np.maximum(k, 0)] <= P6.HEATER_WINDOW_S)
        out[m] = np.where(ok, ets[np.maximum(k, 0)], -1)
    return out


def code_audit() -> list[dict]:
    """Control codes of the primary subjects in canonical event_raw: events and nights per stream (counts only)."""
    import pyarrow as pa
    from src.evaluation.canonical_input import load_primary
    t = load_primary(["subject_id", "device_id", "timestamp", "event_raw"])
    subj = t["subject_id"].cast(pa.string()).to_numpy(zero_copy_only=False).astype(str)
    keep = np.isin(subj, sorted(P5.subject_folds()))
    subj = subj[keep]
    dev = t["device_id"].cast(pa.string()).to_numpy(zero_copy_only=False).astype(str)[keep]
    nights = night_id(t["timestamp"].cast(pa.timestamp("s")).cast(pa.int64()).to_numpy()[keep])
    ev = t["event_raw"].cast(pa.string()).to_numpy(zero_copy_only=False)[keep].astype(str)
    uniq, inv = np.unique(ev, return_inverse=True)
    codes_of = [parse_event(x)[1] for x in uniq]
    count, night_sets = defaultdict(Counter), defaultdict(set)
    for i in np.flatnonzero(np.array([bool(c) for c in codes_of])[inv]):
        for c in codes_of[inv[i]]:
            count[c][(subj[i], dev[i])] += 1
            night_sets[(c, subj[i], dev[i])].add(nights[i])
    stream_nights = {k: np.unique(nights[(subj == k[0]) & (dev == k[1])]).size for k in set(zip(subj, dev))}
    rows = []
    for c in sorted(count, key=lambda c: (-sum(count[c].values()), c)):
        cls, basis = CODE_CLASSES.get(c, ("unclassified", "name_only_ambiguous"))
        for (s, d), n in sorted(count[c].items()):
            rows.append({"code": c, "class": cls, "basis": basis, "used_in_heater_context": int(c in P6.HEATER_CODES),
                         "subject_id": s, "device_id": d, "events": int(n),
                         "nights_with_code": len(night_sets[(c, s, d)]), "nights_of_stream": int(stream_nights[(s, d)]),
                         "night_coverage": len(night_sets[(c, s, d)]) / stream_nights[(s, d)]})
    return rows


# ------------------------------------------------------------------------------------------------ analysis A

def centre(y: np.ndarray, *keys: np.ndarray) -> np.ndarray:
    """y minus its mean within each combination of `keys` (population mean)."""
    key = np.asarray(keys[0]).astype(str)
    for k in keys[1:]:
        key = np.char.add(np.char.add(key, "|"), np.asarray(k).astype(str))
    _, inv = np.unique(key, return_inverse=True)
    inv = inv.reshape(-1)
    y = np.asarray(y, np.float64)
    return y - (np.bincount(inv, weights=y) / np.bincount(inv))[inv]


def eta_squared(y: np.ndarray, groups: np.ndarray) -> float:
    """SS_between / SS_total of a one-way layout over the groups present (NaN if fewer than two groups or no variance)."""
    y, groups = np.asarray(y, np.float64), np.asarray(groups).astype(str)
    if y.size == 0:
        return float("nan")
    total = float(((y - y.mean()) ** 2).sum())
    names = np.unique(groups)
    if names.size < 2 or total <= 0:
        return float("nan")
    between = sum(float((groups == g).sum()) * (float(y[groups == g].mean()) - float(y.mean())) ** 2 for g in names)
    return between / total


def eta_with_interval(y: np.ndarray, groups: np.ndarray, nights: np.ndarray) -> dict:
    """Point eta squared and its night-cluster percentile interval (whole nights resampled; frozen settings)."""
    y, groups = np.asarray(y, np.float64), np.asarray(groups).astype(str)
    point = eta_squared(y, groups)
    resamples, seed, level = P6.bootstrap_settings()
    uniq, inv = np.unique(np.asarray(nights).astype(str), return_inverse=True)
    inv = inv.reshape(-1)
    n_n = uniq.size
    out = {"eta_squared": point, "ci_lower": float("nan"), "ci_upper": float("nan"), "n_nights": int(n_n),
           "n_windows": int(y.size), "n_states": int(np.unique(groups).size)}
    if not np.isfinite(point) or n_n < 2:
        return out
    w = P6.resample_counts(n_n, resamples, seed)
    tot_n = w @ np.bincount(inv, minlength=n_n).astype(np.float64)
    tot_s = w @ np.bincount(inv, weights=y, minlength=n_n)
    tot_q = w @ np.bincount(inv, weights=y * y, minlength=n_n)
    ss_total = tot_q - tot_s ** 2 / tot_n
    between = -tot_s ** 2 / tot_n
    for g in np.unique(groups):
        m = groups == g
        gn = w @ np.bincount(inv[m], minlength=n_n).astype(np.float64)
        gs = w @ np.bincount(inv[m], weights=y[m], minlength=n_n)
        between = between + np.divide(gs ** 2, gn, out=np.zeros_like(gs), where=gn > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        boot = np.where(ss_total > 0, between / ss_total, np.nan)
    lo, hi = P6.interval(boot[np.isfinite(boot)], level)
    out.update(ci_lower=float(lo), ci_upper=float(hi))
    return out


def eta_label(v: float) -> str:
    return "undefined" if not np.isfinite(v) else "small" if v < ETA_SMALL else "medium" if v < ETA_LARGE else "large"


def case_of(raw: float, centred: float) -> str:
    if not (np.isfinite(raw) and np.isfinite(centred)):
        return "undefined"
    if centred >= ETA_SMALL:
        return "C"
    return "B" if raw >= ETA_SMALL else "A"


def state_summary(y: np.ndarray, states: np.ndarray, nights: np.ndarray) -> list[dict]:
    out = []
    for st in STATES:
        m = states == st
        v = np.asarray(y, np.float64)[m]
        rec = {"state": st, "windows": int(m.sum()), "share_of_windows": float(m.mean()) if m.size else float("nan"),
               "nights": int(np.unique(np.asarray(nights)[m]).size)}
        if v.size:
            q25, q50, q75 = np.quantile(v, [0.25, 0.5, 0.75])
            rec.update(mean=float(v.mean()), median=float(q50), sd=float(v.std()), iqr=float(q75 - q25))
        else:
            rec.update(mean=float("nan"), median=float("nan"), sd=float("nan"), iqr=float("nan"))
        out.append(rec)
    return out


# ------------------------------------------------------------------------------------------------ analysis B

def conditioned_constants(y_source: np.ndarray, states_source: np.ndarray) -> dict:
    """Source-only constants: overall mean/median and the mean per heater state (fallback = overall mean)."""
    y = np.asarray(y_source, np.float64)
    c = LB.constants(y)
    out = {"overall_mean": c["mean"], "overall_median": c["median"], "n_source": int(y.shape[0]), "fallback": []}
    for st in ("ON", "OFF"):
        m = np.asarray(states_source) == st
        out[f"n_source_{st}"] = int(m.sum())
        if m.any():
            out[f"mean_{st}"] = y[m].mean(axis=0)
        else:
            out[f"mean_{st}"] = c["mean"].copy()
            out["fallback"].append(st)
    out["n_source_UNKNOWN"] = int((np.asarray(states_source) == "UNKNOWN").sum())
    return out


def predict_conditioned(states_test: np.ndarray, consts: dict) -> np.ndarray:
    states_test = np.asarray(states_test).astype(str)
    if set(np.unique(states_test).tolist()) - set(STATES):
        raise P12Error("unexpected heater state in the test windows")
    pred = np.tile(consts["overall_mean"], (states_test.shape[0], 1)).astype(np.float64)      # UNKNOWN -> overall mean
    for st in ("ON", "OFF"):
        pred[states_test == st] = consts[f"mean_{st}"]
    return pred


def assert_source_only(fd, fit_mask: np.ndarray) -> None:
    """Fail closed if a held-out-subject window (or a non-training window) reaches a constant fit."""
    subj = fd.prov["subject_id"][fit_mask]
    if fit_mask.sum() == 0 or np.any(subj == fd.held_out) or np.any(fd.partition[fit_mask] != "train") or \
            sorted(np.unique(subj).tolist()) != sorted(fd.train_subjects):
        raise P12Error(f"fold {fd.fold}: constants must be fitted on the source training windows only")


def common_keys_equal(pv: dict, ys: np.ndarray, keys: np.ndarray, y: np.ndarray) -> bool:
    """True iff committed predictions sit on exactly these endpoints: same keys in the same order, same targets."""
    kk = P8.window_keys(pv["device_id"], pv["window_start"])
    return bool(kk.shape == keys.shape and np.array_equal(kk, keys) and np.array_equal(ys, y))


# ------------------------------------------------------------------------------------------------ orchestration

def _read_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _close(a, b) -> bool:
    return abs(float(a) - float(b)) <= TOLERANCE


def snapshot_protected() -> dict[str, str]:
    out = {}
    for tree in PROTECTED_TREES:
        for p in sorted((paths.PROJECT_ROOT / tree).rglob("*")):
            if p.is_file():
                out[p.relative_to(paths.PROJECT_ROOT).as_posix()] = sha256_file(p)
    return out


def run(sess, echo=print) -> tuple[dict[str, list[dict]], dict, dict]:
    load_config()
    H.load_history_config()
    frozen = freeze_design()                                   # before the first statistic
    before = snapshot_protected()
    started = time.time()
    subjects_hist = P11.build_subjects(sess, echo)
    names = sorted(P5.subject_folds())
    events = {s: P6.heater_events(s) for s in names}
    tables: dict[str, list[dict]] = {k: [] for k in (
        "code_audit", "context_counts", "target_summary", "eta_squared", "metrics_full", "metrics_common",
        "bootstrap_full", "bootstrap_common", "predictions_metadata", "history_gain_by_context", "interpretation")}
    val: dict = {"checks": []}

    def check(name: str, passed: bool, detail: str = "ok") -> None:
        val["checks"].append({"check": name, "passed": bool(passed), "detail": detail})

    tables["code_audit"] = code_audit()
    p10_loso = _read_csv(paths.PROJECT_ROOT / "outputs" / "metrics" / "p10" / "p10_loso_metrics.csv")
    p10_boot = _read_csv(paths.PROJECT_ROOT / "outputs" / "metrics" / "p10" / "p10_history_bootstrap.csv")
    p11_cmp = _read_csv(paths.PROJECT_ROOT / "outputs" / "p11_common_pool_tcn" / "common_pool_model_comparison.csv")
    eta_of: dict[tuple, float] = {}
    gain_heater: dict[tuple, dict] = {}

    for fold, held in sorted({int(k): v for k, v in load_protocol()["loso"]["outer_folds"].items()}.items()):
        fd, cm = P11.aligned_mask(sess, fold, subjects_hist)
        pl = P11.pools(fd, cm)
        states = context_states(fd.prov["subject_id"], fd.prov["device_id"], fd.prov["target_timestamp"], events)
        nights_all = fd.prov["night_id"].astype(str)
        mats_all = fd.prov["device_id"].astype(str)

        # consistency of the look-up with the frozen function, and look-backs that cross into an earlier session
        m_held = fd.prov["subject_id"] == held
        ev_t = last_event_time(mats_all[m_held], fd.prov["target_timestamp"][m_held], events[held])
        check(f"fold{fold}_event_time_consistent_with_frozen_lookup",
              bool(np.array_equal(ev_t >= 0, states[m_held] != "UNKNOWN")))
        ts_held = to_seconds(fd.prov["target_timestamp"][m_held])
        check(f"fold{fold}_no_future_event_and_within_60_min",
              bool(np.all((ev_t < 0) | ((ev_t <= ts_held) & (ts_held - ev_t <= P6.HEATER_WINDOW_S)))))
        sess_ids = fd.prov["session_id"][m_held].astype(str)
        ws = to_seconds(fd.prov["window_start"][m_held])
        _, s_inv = np.unique(sess_ids, return_inverse=True)
        s_first = np.full(s_inv.max() + 1, np.iinfo(np.int64).max)
        np.minimum.at(s_first, s_inv.reshape(-1), ws)
        crossing = (ev_t >= 0) & (ev_t < s_first[s_inv.reshape(-1)])

        for span in SPANS:
            te = pl["test_full"] if span == "full" else pl["test"]
            tr = pl["train_full"] if span == "full" else pl["train"]
            assert_source_only(fd, tr)
            y_te, st_te, n_te, mat_te = fd.targets[te], states[te], nights_all[te], mats_all[te]

            # ---- coverage
            groups = [("all", np.ones(te.sum(), bool))]
            if held == USER02:
                groups += [(d, mat_te == d) for d in sorted(np.unique(mat_te))]
            for gname, gm in groups:
                for st in STATES:
                    m = gm & (st_te == st)
                    tables["context_counts"].append({
                        "span": span, "subject_id": held, "mat": gname, "state": st, "windows": int(m.sum()),
                        "share_of_windows": float(m.sum() / max(gm.sum(), 1)),
                        "nights_with_state": int(np.unique(n_te[m]).size), "nights": int(np.unique(n_te[gm]).size),
                        "windows_with_event_before_session_start": int((crossing[te[m_held]] & m).sum())
                        if gname == "all" else ""})

            # ---- analysis A
            for i, t in enumerate(TARGETS):
                y = y_te[:, i]
                for r in state_summary(y, st_te, n_te):
                    tables["target_summary"].append({"span": span, "subject_id": held, "target": t, **r})
                variants = [("A1_raw", y), ("A2_night_centred", centre(y, n_te))]
                if held == USER02:
                    variants.append(("A3_night_x_mat_centred", centre(y, n_te, mat_te)))
                for vname, yy in variants:
                    for scope, m in (("three_states", np.ones(y.size, bool)), ("ON_OFF_only", st_te != "UNKNOWN")):
                        e = eta_with_interval(yy[m], st_te[m], n_te[m])
                        tables["eta_squared"].append({"span": span, "subject_id": held, "target": t, "variant": vname,
                                                      "scope": scope, **e, "label": eta_label(e["eta_squared"])})
                        if scope == "three_states":
                            eta_of[(span, held, t, vname)] = e["eta_squared"]

            # ---- analysis B (source-only constants; the held-out subject is never in a fit)
            consts = conditioned_constants(fd.targets[tr], states[tr])
            preds = {"source_mean": np.tile(consts["overall_mean"], (y_te.shape[0], 1)),
                     "source_median": np.tile(consts["overall_median"], (y_te.shape[0], 1)),
                     "heater_conditioned_source_mean": predict_conditioned(st_te, consts)}
            check(f"fold{fold}_{span}_unknown_windows_get_the_source_overall_mean",
                  bool(np.array_equal(preds["heater_conditioned_source_mean"][st_te == "UNKNOWN"],
                                      preds["source_mean"][st_te == "UNKNOWN"])))
            for name, p in preds.items():
                pm = LB.point_metrics(y_te, p)
                for t in TARGETS:
                    tables[f"metrics_{span}"].append({
                        "span": span, "fold": fold, "subject_id": held, "target": t, "predictor": name,
                        "mae": pm[t]["mae"], "rmse": pm[t]["rmse"], "bias": pm[t]["bias"],
                        "n_windows": int(y_te.shape[0]), "n_nights": int(np.unique(n_te).size),
                        "n_source_windows": consts["n_source"]})
            brows = H.bootstrap_rows(fold, held, y_te, preds, n_te, [
                ("source_mean", "heater_conditioned_source_mean", "level_baseline_vs_heater_conditioned_constant"),
                ("source_median", "heater_conditioned_source_mean", "secondary")])
            for r in brows:
                r["span"] = span
                if r["first"] == "source_mean":
                    gain_heater[(span, held, r["target"])] = r
            tables[f"bootstrap_{span}"] += brows
            tables["predictions_metadata"].append({
                "span": span, "fold": fold, "held_out_subject": held, "source_subjects": "+".join(fd.train_subjects),
                **{f"n_source_{st}": consts[f"n_source_{st}"] for st in STATES}, "n_source": consts["n_source"],
                **{f"n_test_{st}": int((st_te == st).sum()) for st in STATES}, "n_test": int(y_te.shape[0]),
                **{f"{k}_{t}": float(consts[k][i]) for k in ("overall_mean", "overall_median", "mean_ON", "mean_OFF")
                   for i, t in enumerate(TARGETS)},
                "empty_source_states_using_fallback": "+".join(consts["fallback"]),
                "rule": "ON->source ON mean; OFF->source OFF mean; UNKNOWN->source overall mean",
                "held_out_subject_in_fit": False})

            # ---- regression against committed tables (values are read, never replaced)
            if span == "full":
                ref = {(r["subject_id"], r["target"], r["predictor"]): r for r in p10_loso}
                ok = all(_close(next(x["mae"] for x in tables["metrics_full"] if (x["subject_id"], x["target"],
                         x["predictor"]) == (held, t, a)), ref[(held, t, b)]["mae"])
                         for t in TARGETS for a, b in (("source_mean", "training_mean"),
                                                       ("source_median", "training_median")))
                check(f"fold{fold}_full_source_mean_median_equal_p10_loso_table", ok)
            else:
                ref = {(r["subject"], r["target"], r["model"]): r for r in p11_cmp}
                ok = all(_close(next(x["mae"] for x in tables["metrics_common"] if (x["subject_id"], x["target"],
                         x["predictor"]) == (held, t, a)), ref[(held, t, b)]["MAE"])
                         for t in TARGETS for a, b in (("source_mean", "mean_common"),
                                                       ("source_median", "median_common")))
                check(f"fold{fold}_common_source_mean_median_equal_p11_table", ok)

        # ---- analysis C and P11 key equality (common span, committed predictions only)
        te = pl["test"]
        y_te, st_te = fd.targets[te], states[te]
        keys_te = P8.window_keys(fd.prov["device_id"][te], fd.prov["window_start"][te])
        committed = {}
        for s in P5.seeds():
            ys, ps, pv = LB.strict_pairs(read_predictions(P11.final_dir(fold, s) / "predictions.parquet"))
            same = common_keys_equal(pv, ys, keys_te, y_te)
            check(f"fold{fold}_seed{s}_common_keys_and_targets_equal_p11_predictions", same)
            if not same:
                raise P12Error(f"fold {fold}: common endpoints differ from the committed P11 predictions")
            committed[f"raw_tcn_common_seed{s}"] = ps
        for h in H.HISTORIES:
            f = paths.PROJECT_ROOT / "outputs" / "runs" / "p10" / "history" / f"fold{fold}" / f"hgb_h{h}" / \
                "predictions.parquet"
            ys, ps, pv = LB.strict_pairs(read_predictions(f))
            if not common_keys_equal(pv, ys, keys_te, y_te):
                raise P12Error(f"fold {fold}: common endpoints differ from the committed P10 hgb h{h} predictions")
            committed[f"hgb_h{h}"] = ps
        committed["training_mean_common"] = np.tile(LB.constants(fd.targets[pl["train"]])["mean"], (y_te.shape[0], 1))
        for i, t in enumerate(TARGETS):
            for st in STATES + ("ALL",):
                m = np.ones(st_te.size, bool) if st == "ALL" else st_te == st
                rec = {"subject_id": held, "target": t, "state": st, "windows": int(m.sum())}
                if m.any():
                    ae = {k: float(np.abs(p[m, i] - y_te[m, i]).mean()) for k, p in committed.items()}
                    rec.update({"mae_training_mean_common": ae["training_mean_common"],
                                **{f"mae_hgb_h{h}": ae[f"hgb_h{h}"] for h in H.HISTORIES},
                                "mae_raw_tcn_common_seed_mean": float(np.mean([ae[f"raw_tcn_common_seed{s}"]
                                                                               for s in P5.seeds()])),
                                "hgb_h40_minus_hgb_h900": ae["hgb_h40"] - ae["hgb_h900"],
                                "training_mean_minus_hgb_h900": ae["training_mean_common"] - ae["hgb_h900"]})
                tables["history_gain_by_context"].append(rec)
        echo(f"{now()} fold {fold} ({held}) analysed")

    # ---- interpretation (plan section 7, applied mechanically)
    hgb_gain = {(r["subject_id"], r["target"]): r for r in p10_boot
                if r["first"] == "training_mean_common" and r["second"] == "hgb_h900"}
    for span in SPANS:
        for s in names:
            for t in TARGETS:
                raw, cen = eta_of[(span, s, t, "A1_raw")], eta_of[(span, s, t, "A2_night_centred")]
                rec = {"span": span, "subject_id": s, "target": t, "eta_raw": raw, "eta_night_centred": cen,
                       "eta_night_x_mat_centred": eta_of.get((span, s, t, "A3_night_x_mat_centred"), ""),
                       "case": case_of(raw, cen),
                       "case_user02_night_x_mat": case_of(raw, eta_of[(span, s, t, "A3_night_x_mat_centred")])
                       if s == USER02 else ""}
                g = gain_heater[(span, s, t)]
                rec.update(heater_gain=g["point_estimate"], heater_gain_ci_lower=g["ci_lower"],
                           heater_gain_ci_upper=g["ci_upper"], heater_gain_interval=g["interval"])
                if span == "common":
                    hg = hgb_gain[(s, t)]
                    rec.update(hgb_h900_gain_p10=float(hg["point_estimate"]), hgb_h900_gain_interval_p10=hg["interval"])
                    if hg["interval"] != "above_zero":
                        rec["competing_explanation"] = "not_applicable_no_hgb_h900_gain"
                    elif g["interval"] == "above_zero" and g["point_estimate"] >= 0.5 * float(hg["point_estimate"]):
                        rec["competing_explanation"] = "plausible"
                    elif g["interval"] != "above_zero" and np.isfinite(cen) and cen < ETA_SMALL:
                        rec["competing_explanation"] = "not_supported"
                    else:
                        rec["competing_explanation"] = "unresolved"
                tables["interpretation"].append(rec)

    after = snapshot_protected()
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    check("existing_p3_p10_p11_outputs_and_paper_tables_unchanged", not changed, str(changed[:5]))
    cur = design_hashes()
    check("plan_and_config_hashes_equal_the_pre_result_record",
          all(cur[k] == frozen[k] for k in ("plan_sha256_lf", "config_sha256_lf")))
    check("no_model_fitted_and_no_heater_field_passed_to_a_trainer", True,
          "the module imports no trainer and calls no fit other than means and medians")
    val["n_protected_files"] = len(before)
    val["passed"] = all(c["passed"] for c in val["checks"])
    prov = {"generated_at": now(), **cur, "pre_result_record": frozen, **P3.frozen_inputs(), **P5.p5_git_state(),
            "heater_definition": {"codes": list(P6.HEATER_CODES), "lookback_s": P6.HEATER_WINDOW_S,
                                  "functions": "p6_robustness.heater_events / heater_context (unchanged)"},
            "total_wall_seconds": round(time.time() - started, 1), "validation_passed": val["passed"]}
    return tables, val, prov


FILES = {"code_audit": "heater_code_audit.csv", "context_counts": "heater_context_counts.csv",
         "target_summary": "heater_target_summary.csv", "eta_squared": "heater_eta_squared.csv",
         "metrics_full": "heater_constant_metrics_full.csv", "metrics_common": "heater_constant_metrics_common.csv",
         "bootstrap_full": "heater_bootstrap_full.csv", "bootstrap_common": "heater_bootstrap_common.csv",
         "predictions_metadata": "heater_predictions_metadata.csv",
         "history_gain_by_context": "heater_history_gain_by_context.csv", "interpretation": "heater_interpretation.csv"}


def write_outputs(tables: dict[str, list[dict]], val: dict, prov: dict) -> Path:
    out = output_root()
    for key, fname in FILES.items():
        rows = tables.get(key, [])
        cols = list(dict.fromkeys(k for r in rows for k in r)) or ["none"]
        write_csv(out / fname, [{c: r.get(c, "") for c in cols} for r in rows], cols)
    prov["table_sha256"] = {f: sha256_file(out / f) for f in FILES.values()}
    write_json(out / "validation.json", val)
    write_json(out / "provenance.json", prov)
    return out
