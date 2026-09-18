"""P10 part H: pressure-summary models over 40-s, 300-s and 900-s histories under strict LOSO (protocol v1.4 addendum;
D-064; docs/P10_LEVEL_BASELINE_HISTORY_PLAN.md §5–§6).

Post hoc and exploratory.
- Endpoints are the frozen v1.0 strict-LOSO 40-s windows (target row = last row before t_end = t0 + 40 s).
- A history of H seconds is the v1.0 window rule with duration H: [t_end − H, t_end) cut into 5-s bins, each step the
  last observed row of its bin, inside one gap-free (≤ 5 s) segment of one subject, mat, session, sensor phase,
  channel-quality phase (and partition, which is constant within a subject in strict LOSO). It is built with the frozen
  `windowing.build_windows`; because 40 − H is a multiple of the 20-s stride, its windows end exactly at the 40-s
  endpoints that have at least H seconds of continuous history. Nothing is interpolated, filled or clipped.
- Features: 7 summaries of each of the six channels (/4095) per history; no cross-channel, geometry, calendar,
  identity, phase, heater or target field.
- Models: Ridge (feature standardiser and target z-score fitted on the training partition) and
  HistGradientBoostingRegressor (one per target), selected on the source-only inner A/B splits with the v1.0
  criterion, refit on the outer training pool and evaluated once on the held-out subject. Every fit and every
  evaluation uses the endpoints common to all three histories.
- A P10 addendum gate (fail closed) and the v1.0 split-level gate run before any fit.
"""
from __future__ import annotations

import json
import platform
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyarrow as pa
import yaml

from src.data.io_guard import open_for_write, write_csv, write_json, write_parquet
from src.evaluation import leakage as L
from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P5
from src.evaluation import p6_robustness as P6
from src.evaluation import p8_posthoc as P8
from src.evaluation import splits as S
from src.evaluation.canonical_input import verify_canonical
from src.evaluation.metrics import TARGETS, selection_criterion
from src.evaluation.p2_protocol import load_manifest, split_root
from src.evaluation.p3_loso import now, read_predictions, run_status, sha256_file
from src.evaluation.p8_dynamic import signal_stats
from src.evaluation.protocol import load_protocol
from src.evaluation.windowing import WindowSpec, Windows, build_windows, continuity_segments, labelled
from src.evaluation import p10_level_baselines as LB
from src.features.pressure_features import PRESSURE_DIVISOR, TargetScaler

HISTORIES = (40, 300, 900)
BIN_S, STRIDE_S, MAX_GAP_S, ENDPOINT_S = 5, 20, 5, 40
CHANNELS = ("p1", "p2", "p3", "p4", "p5", "p6")
STATS = ("mean", "std", "min", "max", "last", "net_change", "abs_change_sum")
FAMILIES = ("ridge", "hgb")
RIDGE_ALPHAS = (1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0, 1000.0)
HGB_FIXED = {"learning_rate": 0.1, "max_iter": 200, "early_stopping": False, "l2_regularization": 0.0,
             "max_bins": 255, "random_state": 0}
HGB_GRID = tuple({"max_leaf_nodes": a, "min_samples_leaf": b} for a in (15, 63) for b in (100, 1000))
R_WITHIN_MIN = 0.10
USER02 = "User02"
REASONS = ("session_start", "gap_gt_5s")


class P10HistoryError(RuntimeError):
    pass


def feature_names(history: int) -> tuple[str, ...]:
    return tuple(f"h{history}_{c}_{s}" for c in CHANNELS for s in STATS)


ALLOWED_FEATURES = frozenset(n for h in HISTORIES for n in feature_names(h))


def history_spec(history: int) -> WindowSpec:
    """The v1.0 window rule with duration H (5-s bins = max gap, stride 20 s)."""
    if history % BIN_S or (ENDPOINT_S - history) % STRIDE_S:
        raise P10HistoryError(f"history {history} s is not aligned with the 40-s endpoints on the 20-s stride")
    return WindowSpec(duration_s=history, bin_s=BIN_S, stride_s=STRIDE_S, max_gap_s=MAX_GAP_S)


def grid(family: str) -> list[dict]:
    if family == "ridge":
        return [{"alpha": a} for a in RIDGE_ALPHAS]
    if family == "hgb":
        return [dict(g) for g in HGB_GRID]
    raise P10HistoryError(f"unknown family {family}")


def load_history_config() -> dict:
    """The v1.4 history section must equal the constants of this module (refuses any drift)."""
    doc = LB.load_config()["history_models"]
    problems = []
    if tuple(doc["histories_s"]) != HISTORIES or (doc["bin_s"], doc["stride_s"], doc["max_gap_s"]) != \
            (BIN_S, STRIDE_S, MAX_GAP_S):
        problems.append("histories / bins")
    if tuple(doc["features"]["per_channel"]) != ("mean", "std_ddof0", "min", "max", "last", "net_change",
                                                 "abs_change_sum"):
        problems.append("feature list")
    if tuple(doc["families"]["ridge"]["grid"]["alpha"]) != RIDGE_ALPHAS:
        problems.append("ridge grid")
    hg = doc["families"]["hgb"]
    if hg["fixed"] != HGB_FIXED or [{"max_leaf_nodes": a, "min_samples_leaf": b}
                                    for a in hg["grid"]["max_leaf_nodes"]
                                    for b in hg["grid"]["min_samples_leaf"]] != list(HGB_GRID):
        problems.append("hgb grid")
    bt = doc["bootstrap"]
    if (bt["resamples"], bt["seed"], bt["level"]) != P6.bootstrap_settings():
        problems.append("bootstrap settings")
    if problems:
        raise P10HistoryError("v1.4 history config differs from the code: " + "; ".join(problems))
    return doc


def run_root() -> Path:
    return LB.output_root() / "runs" / "p10" / "history"


def metrics_dir() -> Path:
    return LB.metrics_dir()


# ------------------------------------------------------------------------------------------------ features

def summary_features(steps: np.ndarray) -> np.ndarray:
    """(n, K, 6) raw pressure steps -> (n, 42) features in `feature_names` order (channel, then statistic)."""
    p = np.asarray(steps)
    if p.ndim != 3 or p.shape[-1] != 6 or p.shape[1] < 2:
        raise ValueError("steps must have shape (n, K >= 2, 6)")
    if np.any(p < 0) or np.any(p > PRESSURE_DIVISOR):
        raise ValueError("pressure outside 0..4095")
    x = p.astype(np.float64) / PRESSURE_DIVISOR
    d = np.diff(x, axis=1)
    stats = np.stack([x.mean(axis=1), x.std(axis=1), x.min(axis=1), x.max(axis=1), x[:, -1], x[:, -1] - x[:, 0],
                      np.abs(d).sum(axis=1)], axis=-1)                       # (n, 6, 7)
    return stats.reshape(p.shape[0], 6 * len(STATS))


# ------------------------------------------------------------------------------------------------ endpoints

@dataclass
class SubjectHistory:
    subject: str
    row_idx: np.ndarray                       # global canonical row index of the subject's rows
    t0: np.ndarray                            # 40-s endpoints: window start
    t_end: np.ndarray
    target_row: np.ndarray                    # global row index
    labelled: np.ndarray
    targets: np.ndarray                       # (n, 2)
    prov: dict[str, np.ndarray]
    available: dict[int, np.ndarray]
    reason: dict[int, np.ndarray]
    common: np.ndarray                        # labelled & available at every history
    features: dict[int, np.ndarray] = field(default_factory=dict)   # history -> (n_common, 42)
    labels_first: dict[int, np.ndarray] = field(default_factory=dict)  # history -> (n_common, 3) first-step labels
    checks: list[dict] = field(default_factory=list)

    def common_prov(self) -> dict[str, np.ndarray]:
        return {k: v[self.common] for k, v in self.prov.items()}


def endpoint_availability(ts: np.ndarray, group: np.ndarray, w40: Windows, history: int
                          ) -> tuple[np.ndarray, np.ndarray]:
    """(available, reason) for every 40-s endpoint: available iff t_end − H >= start of its continuity segment.
    Reason for an unavailable endpoint: the segment starts at its session (group) start, or after a gap > 5 s."""
    seg = continuity_segments(ts, group, MAX_GAP_S)
    seg_first = np.searchsorted(seg, np.arange(int(seg[-1]) + 1), side="left")
    first_row = seg_first[w40.segment]
    t_end = w40.t0 + ENDPOINT_S
    avail = t_end - history >= ts[first_row]
    group_start = np.r_[True, group[1:] != group[:-1]]
    reason = np.where(avail, "", np.where(group_start[first_row], REASONS[0], REASONS[1]))
    return avail, reason


def build_subject(rows, subject: str, histories: tuple[int, ...] = HISTORIES, chunk: int = 8192) -> SubjectHistory:
    """Endpoints, availability, exclusion reasons and features of one subject (fold-independent in strict LOSO)."""
    from src.training.loso_data import coded_key
    idx = np.flatnonzero(rows.subject == subject)
    if idx.size == 0:
        raise P10HistoryError(f"{subject}: no canonical rows")
    ts = rows.ts[idx]
    group = coded_key(rows.device[idx], rows.session[idx], rows.sensor_phase[idx], rows.cq_phase[idx])
    w40 = build_windows(ts, group, history_spec(ENDPOINT_S))
    lab = labelled(w40, rows.temp_ok[idx], rows.humid_ok[idx])
    last = w40.target_row
    from src.evaluation.protocol import night_id
    prov = {"subject_id": rows.subject[idx][last], "device_id": rows.device[idx][last],
            "session_id": rows.session[idx][last], "sensor_phase": rows.sensor_phase[idx][last],
            "channel_quality_phase": rows.cq_phase[idx][last], "night_id": night_id(ts[last]),
            "window_start": w40.t0, "window_end": w40.t0 + ENDPOINT_S, "target_timestamp": ts[last]}
    available, reason, windows = {}, {}, {}
    checks = []
    for h in histories:
        av, rs = endpoint_availability(ts, group, w40, h)
        wh = build_windows(ts, group, history_spec(h))                  # validates bins, gaps and groups
        order = np.argsort(wh.target_row)
        pos = np.searchsorted(wh.target_row[order], last)
        pos = np.minimum(pos, max(len(order) - 1, 0))
        found = (len(order) > 0) & (wh.target_row[order][pos] == last)
        ok_set = bool(np.array_equal(found, av)) and int(av.sum()) == len(wh)
        checks.append({"check": f"h{h}_windows_exist_exactly_at_available_endpoints", "passed": ok_set,
                       "detail": "ok" if ok_set else f"built {len(wh)}, available {int(av.sum())}"})
        j = order[pos[av]]
        ends_ok = bool(np.array_equal(wh.t0[j] + h, w40.t0[av] + ENDPOINT_S))
        seg_ok = bool(np.array_equal(wh.segment[j], w40.segment[av]))
        last_ok = bool(np.array_equal(wh.step_rows[j, -1], last[av]))
        checks.append({"check": f"h{h}_history_ends_at_endpoint_and_last_step_is_target_row",
                       "passed": ends_ok and seg_ok and last_ok,
                       "detail": f"ends {ends_ok}, segment {seg_ok}, last step {last_ok}"})
        if h == ENDPOINT_S and not bool(av.all()):
            checks.append({"check": "h40_available_everywhere", "passed": False, "detail": "a 40-s endpoint lacks 40 s"})
        available[h], reason[h] = av, rs
        windows[h] = (wh, j)
    common = lab.copy()
    for h in histories:
        common &= available[h]
    sh = SubjectHistory(subject, idx, w40.t0, w40.t0 + ENDPOINT_S, idx[last], lab, rows.targets[idx][last], prov,
                        available, reason, common, checks=checks)
    pressure = rows.pressure[idx]
    labels = np.stack([rows.session[idx], rows.sensor_phase[idx], rows.cq_phase[idx]], axis=1)
    for h in histories:
        wh, j = windows[h]
        av = available[h]
        sel = j[common[av]]                                  # history windows of the common endpoints, in order
        steps = wh.step_rows[sel]
        t_end_c = sh.t_end[common]
        future = has_future_step(ts[steps], t_end_c)
        sh.checks.append({"check": f"h{h}_no_step_row_at_or_after_endpoint", "passed": not future,
                          "detail": "ok" if not future else "a step row is at or after t_end"})
        feats = np.empty((steps.shape[0], len(CHANNELS) * len(STATS)), np.float64)
        for a in range(0, steps.shape[0], chunk):
            feats[a:a + chunk] = summary_features(pressure[steps[a:a + chunk]])
        sh.features[h] = feats
        first_lab, last_lab = labels[steps[:, 0]], labels[steps[:, -1]]
        same = bool(np.array_equal(first_lab, last_lab))
        sh.checks.append({"check": f"h{h}_first_and_last_step_same_session_and_phases", "passed": same,
                          "detail": "ok" if same else "a history crosses a session/phase boundary"})
        sh.labels_first[h] = first_lab
        del windows[h]
    return sh


def has_future_step(step_ts: np.ndarray, t_end: np.ndarray) -> bool:
    """True if any step row of a history lies at or after its endpoint (future information)."""
    return bool(np.any(np.asarray(step_ts) >= np.asarray(t_end)[:, None]))


def availability_rows(sh: SubjectHistory) -> list[dict]:
    out = []
    n_lab = int(sh.labelled.sum())
    for h in sorted(sh.available):
        av = sh.available[h] & sh.labelled
        rs = sh.reason[h][sh.labelled]
        out.append({"subject_id": sh.subject, "history_s": h, "labelled_endpoints": n_lab,
                    "available": int(av.sum()), "excluded": int(n_lab - av.sum()),
                    **{f"excluded_{r}": int((rs == r).sum()) for r in REASONS},
                    "common": int(sh.common.sum()), "common_share_of_labelled": float(sh.common.sum() / n_lab),
                    "labelled_nights": int(np.unique(sh.prov["night_id"][sh.labelled]).size),
                    "common_nights": int(np.unique(sh.prov["night_id"][sh.common]).size)})
    return out


# ------------------------------------------------------------------------------------------------ gate

def check_feature_names(names: list[str]) -> str | None:
    bad = [n for n in names if n not in ALLOWED_FEATURES]
    tokens = [n for n in names if any(t in n.lower() for t in L.TARGET_OR_CONTROL + L.CALENDAR_OR_ID)]
    if not names or bad or tokens:
        return f"inadmissible P10 feature names: {sorted(set(bad) | set(tokens))[:10]}"
    return None


def frozen_fold_windows_equal(sh: SubjectHistory, fd) -> str | None:
    """The per-subject 40-s endpoints equal the frozen fold windows of that subject (order, keys, labels, targets)."""
    m = fd.prov["subject_id"] == sh.subject
    for k in ("device_id", "session_id", "window_start", "target_timestamp"):
        if not np.array_equal(np.asarray(fd.prov[k][m]).astype(str), np.asarray(sh.prov[k]).astype(str)):
            return f"{k} differs from the frozen fold windows"
    if not np.array_equal(fd.labelled[m], sh.labelled):
        return "labelled flags differ"
    if not np.array_equal(fd.targets[m][fd.labelled[m]], sh.targets[sh.labelled]):
        return "targets differ"
    return None


def subject_roles(fold: int, outer: list[dict], inner: list[dict]) -> dict:
    """Held-out subject, training subjects and inner A/B train/val subjects of a fold, from the split files (every
    session of a subject must share its role)."""
    roles: dict = {"test": set(), "train": set(), "inner": {}}
    for r in outer:
        if int(r["fold"]) == fold:
            roles[r["partition"]].add(r["subject_id"])
    for r in inner:
        if int(r["fold"]) == fold:
            roles["inner"].setdefault(r["inner_split"], {}).setdefault(r["partition"], set()).add(r["subject_id"])
    held = roles["test"]
    if len(held) != 1 or held & roles["train"]:
        raise P10HistoryError(f"fold {fold}: held-out subject is not unique or appears in training")
    out = {"held_out": next(iter(held)), "train": sorted(roles["train"]), "inner": {}}
    for name, parts in sorted(roles["inner"].items()):
        tr, va = parts.get("inner_train", set()), parts.get("inner_val", set())
        if len(tr) != 1 or len(va) != 1 or tr & va or (tr | va) != set(out["train"]):
            raise P10HistoryError(f"fold {fold} inner {name}: not a two-subject split of the training pool")
        out["inner"][name] = (next(iter(tr)), next(iter(va)))
    return out


def addendum_gate(fold: int, roles: dict, subjects: dict[str, SubjectHistory], fd, fit_records: list[dict],
                  outer: list[dict], pers: list[dict]) -> dict:
    """The P10 addendum gate for one fold (plan §6); every check fails closed."""
    rep = L.GateReport("v1.4")

    def run(name: str, rule: str, fn) -> None:
        L._run(rep, name, rule, fn)

    for h in HISTORIES:
        run(f"feature_names_admissible_h{h}", "L9/L10", lambda h=h: check_feature_names(list(feature_names(h))))
    for s, sh in sorted(subjects.items()):
        for c in sh.checks:
            run(f"{s}:{c['check']}", "L1", lambda c=c: None if c["passed"] else c["detail"])
        run(f"{s}:endpoints_equal_frozen_fold_windows", "L1/L12", lambda sh=sh: frozen_fold_windows_equal(sh, fd))
        run(f"{s}:common_set_identical_across_histories", "P10",
            lambda sh=sh: None if len({sh.features[h].shape[0] for h in HISTORIES}) == 1
            and sh.features[HISTORIES[0]].shape[0] == int(sh.common.sum()) else "feature rows differ between histories")
    held = roles["held_out"]
    run("test_endpoints_only_held_out_subject", "L2/L4",
        lambda: None if set(subjects[held].prov["subject_id"][subjects[held].common]) == {held} else "foreign test rows")
    run("training_endpoints_exclude_held_out", "L4",
        lambda: None if held not in roles["train"] and all(
            set(subjects[s].prov["subject_id"][subjects[s].common]) == {s} for s in roles["train"]) else
        "held-out subject in training endpoints")
    ctx = L.RunContext("loso", fold=fold, fit_records=fit_records,
                       selection_subjects=sorted({v for _, v in roles["inner"].values()}))
    run("fits_training_partition_only", "L3/L11", lambda: L.check_fits(ctx, outer, pers))
    run("selection_excludes_held_out", "L4", lambda: L.check_selection(ctx, outer, pers))

    def groups() -> str | None:
        part = {s: ("test" if s == held else "train") for s in subjects}
        pairs = []
        for s, sh in subjects.items():
            lab_last = np.stack([sh.prov["session_id"], sh.prov["sensor_phase"], sh.prov["channel_quality_phase"]],
                                axis=1)[sh.common]
            for h in HISTORIES:
                first = np.unique(np.concatenate([sh.labels_first[h], lab_last], axis=1), axis=0)
                pairs += [((part[s], *r[:3]), (part[s], *r[3:])) for r in first]
        return L.check_window_groups(L.RunContext("loso", fold=fold, window_groups=pairs))
    run("windows_inside_partitions", "L1", groups)
    return rep.to_dict()


def split_level_gate(sess) -> dict:
    """The v1.0 gate without a run context (split, canonical and protocol checks); fail closed."""
    verified = verify_canonical()
    sessions, pieces = sess.structure(verified)
    rep = L.run_gate(split_root(), load_manifest(), load_protocol(), sessions, pieces, None, verified)
    L.require_pass(rep)
    return rep.to_dict()


# ------------------------------------------------------------------------------------------------ models

def fit_predict(family: str, cfg: dict, x_tr: np.ndarray, y_tr: np.ndarray, x_te: np.ndarray, *, fold: int,
                partition: str, subjects: list[str]) -> tuple[np.ndarray, list[dict]]:
    """Fit on (x_tr, y_tr) only and predict x_te; returns predictions (n, 2) and the fitted-transform provenance."""
    if family == "ridge":
        from sklearn.linear_model import Ridge
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(x_tr)
        zs = TargetScaler.fit(y_tr, scheme="loso", fold=str(fold), partition=partition, subjects=subjects)
        model = Ridge(alpha=float(cfg["alpha"])).fit(scaler.transform(x_tr), zs.transform(y_tr))
        pred = zs.inverse(model.predict(scaler.transform(x_te)))
        prov = [{"transform": "feature_standardizer", "partition": partition, "subjects": sorted(subjects),
                 "n": int(x_tr.shape[0])}, dict(zs.fit_provenance)]
        return np.asarray(pred, np.float64), prov
    if family == "hgb":
        from sklearn.ensemble import HistGradientBoostingRegressor
        pred = np.empty((x_te.shape[0], 2), np.float64)
        for i in range(2):
            m = HistGradientBoostingRegressor(**HGB_FIXED, **cfg).fit(x_tr, y_tr[:, i])
            pred[:, i] = m.predict(x_te)
        return pred, [{"transform": "hgb_model", "partition": partition, "subjects": sorted(subjects),
                       "n": int(x_tr.shape[0])}]
    raise P10HistoryError(f"unknown family {family}")


def select(scores: list[tuple[float, float]]) -> int:
    return P3.select_config(scores)


def pool(subjects: dict[str, SubjectHistory], names: list[str], history: int) -> tuple[np.ndarray, np.ndarray]:
    x = np.concatenate([subjects[s].features[history] for s in names])
    y = np.concatenate([subjects[s].targets[subjects[s].common] for s in names])
    return x, y


# ------------------------------------------------------------------------------------------------ evaluation

PRED_SCHEMA = pa.schema([
    ("fold", pa.int8()), ("family", pa.string()), ("history_s", pa.int16()), ("subject_id", pa.string()),
    ("device_id", pa.string()), ("session_id", pa.string()), ("sensor_phase", pa.string()),
    ("channel_quality_phase", pa.string()), ("night_id", pa.string()), ("window_start", pa.timestamp("s")),
    ("window_end", pa.timestamp("s")), ("target_timestamp", pa.timestamp("s")), ("target", pa.string()),
    ("y_true", pa.float64()), ("y_pred", pa.float64())])


def write_predictions(path: Path, fold: int, family: str, history: int, prov: dict, y: np.ndarray,
                      p: np.ndarray) -> None:
    n = y.shape[0]
    rep = lambda a: np.tile(np.asarray(a), 2)  # noqa: E731
    t = pa.table({"fold": pa.array(np.full(2 * n, fold, np.int8)), "family": pa.array([family] * 2 * n),
                  "history_s": pa.array(np.full(2 * n, history, np.int16)),
                  **{c: pa.array(rep(prov[c]).astype(str)) for c in ("subject_id", "device_id", "session_id",
                                                                      "sensor_phase", "channel_quality_phase",
                                                                      "night_id")},
                  **{c: pa.array(rep(prov[c]).astype("datetime64[s]"), pa.timestamp("s"))
                     for c in ("window_start", "window_end", "target_timestamp")},
                  "target": pa.array(np.repeat(np.array(TARGETS), n)),
                  "y_true": pa.array(np.concatenate([y[:, 0], y[:, 1]])),
                  "y_pred": pa.array(np.concatenate([p[:, 0], p[:, 1]]))}, schema=PRED_SCHEMA)
    write_parquet(path, [t], PRED_SCHEMA)


def metric_row(fold: int, subject: str, predictor: str, history, seed, y: np.ndarray, p: np.ndarray,
               nights: np.ndarray, mats: np.ndarray, **extra) -> list[dict]:
    out = []
    for i, t in enumerate(TARGETS):
        st = signal_stats(y[:, i], p[:, i], nights, mats if subject == USER02 else None)
        out.append({"fold": fold, "subject_id": subject, "target": t, "predictor": predictor, "history_s": history,
                    "seed": seed, **{k: st[k] for k in ("mae", "rmse", "bias", "target_sd", "R", "Q", "r_pooled",
                                                         "r_within", "r_within_mat")},
                    "n_windows": int(y.shape[0]), "n_nights": int(np.unique(nights).size), **extra})
    return out


def bootstrap_rows(fold: int, subject: str, y: np.ndarray, preds: dict[str, np.ndarray], nights: np.ndarray,
                   pairs: list[tuple[str, str, str]]) -> list[dict]:
    resamples, rng_seed, level = P6.bootstrap_settings()
    n = np.unique(nights).size
    counts = P6.resample_counts(n, resamples, rng_seed)
    full = np.ones((1, n))
    arrays = {k: P8.night_arrays(y, p, nights) for k, p in preds.items()}
    out = []
    for first, second, role in pairs:
        for t in TARGETS:
            a, b = arrays[first][t], arrays[second][t]
            P6.pair(a, b)
            boot = P6.paired_effects(counts, a, b)["mae"]
            lo, hi = P6.interval(boot, level)
            out.append({"fold": fold, "subject_id": subject, "target": t, "first": first, "second": second,
                        "role": role, "point_estimate": float(P6.paired_effects(full, a, b)["mae"][0]),
                        "ci_lower": lo, "ci_upper": hi, "interval": P6.side(lo, hi), "n_nights": int(n),
                        "n_windows": int(y.shape[0]), "n_resamples": resamples, "rng_seed": rng_seed, "level": level})
    return out


def comparison_pairs() -> list[tuple[str, str, str]]:
    out = []
    for f in FAMILIES:
        for h in HISTORIES:
            out.append(("training_mean_common", f"{f}_h{h}", "model_vs_level_baseline"))
        for h in HISTORIES[1:]:
            out.append((f"{f}_h{HISTORIES[0]}", f"{f}_h{h}", "longer_history"))
        for h in HISTORIES:
            out.append(("raw_tcn_seed0", f"{f}_h{h}", "descriptive_different_training_pool"))
    return out


def interpretation_rows(metrics: list[dict], boot: list[dict]) -> list[dict]:
    """Plan §5.6, applied mechanically."""
    side = {(r["subject_id"], r["target"], r["first"], r["second"]): r["interval"] for r in boot}
    met = {(r["subject_id"], r["target"], r["predictor"], str(r["history_s"])): r for r in metrics}
    out = []
    subjects = sorted({r["subject_id"] for r in metrics})
    for f in FAMILIES:
        for h in HISTORIES:
            for s in subjects:
                for t in TARGETS:
                    m = met[(s, t, f, str(h))]
                    rw, rwm = m["r_within"], m["r_within_mat"]
                    hc = bool(m["R"] < 1.0 and np.isfinite(rw) and rw >= R_WITHIN_MIN and
                              (s != USER02 or (np.isfinite(rwm) and rwm >= R_WITHIN_MIN)))
                    out.append({"family": f, "history_s": h, "subject_id": s, "target": t,
                                "H_a_beats_training_mean_common":
                                    side[(s, t, "training_mean_common", f"{f}_h{h}")] == "above_zero",
                                "H_b_longer_history_lower_error": "" if h == HISTORIES[0] else
                                side[(s, t, f"{f}_h{HISTORIES[0]}", f"{f}_h{h}")] == "above_zero",
                                "H_c_variation_beyond_level": hc, "mae": m["mae"], "R": m["R"],
                                "r_within": rw, "r_within_mat": rwm})
    return out


def interpretation_summary(rows: list[dict]) -> list[dict]:
    out = []
    for f in FAMILIES:
        for h in HISTORIES:
            for t in TARGETS:
                sel = [r for r in rows if r["family"] == f and r["history_s"] == h and r["target"] == t]
                a = sum(bool(r["H_a_beats_training_mean_common"]) for r in sel)
                b = "" if h == HISTORIES[0] else sum(r["H_b_longer_history_lower_error"] is True for r in sel)
                c = sum(bool(r["H_c_variation_beyond_level"]) for r in sel)
                out.append({"family": f, "history_s": h, "target": t, "subjects": len(sel), "H_a_count": a,
                            "H_a_rule_met_2_of_3": a >= 2, "H_b_count": b,
                            "H_b_rule_met_2_of_3": "" if b == "" else b >= 2, "H_c_count": c})
    return out


def environment() -> dict:
    import scipy
    import sklearn
    from threadpoolctl import threadpool_info
    return {"python": platform.python_version(), "numpy": np.__version__, "scikit_learn": sklearn.__version__,
            "scipy": scipy.__version__, "platform": platform.platform(), "processor": platform.processor(),
            "threadpools": [{k: d.get(k) for k in ("internal_api", "num_threads", "version")}
                            for d in threadpool_info()]}


# ------------------------------------------------------------------------------------------------ orchestration

def run(sess, echo=print) -> tuple[dict[str, list[dict]], dict]:
    load_history_config()
    design = LB.design_hashes()
    split_gate = split_level_gate(sess)
    rows = sess.rows()
    outer = S.read_split(split_root() / S.LOSO_OUTER)
    inner = S.read_split(split_root() / S.LOSO_INNER)
    pers = S.read_split(split_root() / S.PERSONALIZATION)
    subjects = {}
    tables: dict[str, list[dict]] = {"history_availability": [], "history_selection": [], "history_metrics": [],
                                     "history_bootstrap": []}
    for s in sorted(P5.subject_folds()):
        echo(f"{now()} building {s}")
        subjects[s] = build_subject(rows, s)
        tables["history_availability"] += availability_rows(subjects[s])
    prov = {"design": design, "generated_at": now(), **P3.frozen_inputs(), **P5.p5_git_state(),
            "environment": environment(), "split_level_gate_passed": split_gate["passed"],
            "features": {h: list(feature_names(h)) for h in HISTORIES}, "folds": {}, "prediction_files_sha256": {}}
    for fold, held in sorted({int(k): v for k, v in load_protocol()["loso"]["outer_folds"].items()}.items()):
        roles = subject_roles(fold, outer, inner)
        if roles["held_out"] != held:
            raise P10HistoryError(f"fold {fold}: held-out subject differs from the protocol")
        fd = sess.fold(fold)
        train = roles["train"]
        fits = [{"transform": t, "partition": "train", "subjects": train} for t in
                ("feature_standardizer", "target_zscore", "hgb_model", "training_mean_common",
                 "training_median_common")]
        for name, (tr_s, _) in roles["inner"].items():
            fits += [{"transform": t, "partition": "inner_train", "subjects": [tr_s]} for t in
                     ("feature_standardizer", "target_zscore", "hgb_model")]
        gate = addendum_gate(fold, roles, subjects, fd, fits, outer, pers)
        write_json(run_root() / f"fold{fold}" / "p10_gate.json", {"checked_at": now(), "split_level_v1_0": split_gate,
                                                                  "addendum": gate, **design})
        if not gate["passed"]:
            bad = [c for c in gate["checks"] if not c["passed"]]
            raise P10HistoryError(f"fold {fold}: P10 addendum gate failed: {bad[:5]}")
        test = subjects[held]
        prov_te = test.common_prov()
        y_te = test.targets[test.common]
        nights, mats = prov_te["night_id"].astype(str), prov_te["device_id"].astype(str)
        preds: dict[str, np.ndarray] = {}
        fold_rec = {"held_out": held, "train_subjects": train, "inner": roles["inner"],
                    "n_train_common": int(sum(subjects[s].common.sum() for s in train)),
                    "n_test_common": int(test.common.sum()), "selected": {}}
        for h in HISTORIES:
            x_te = test.features[h]
            inner_data = {name: (pool(subjects, [tr_s], h), pool(subjects, [va_s], h))
                          for name, (tr_s, va_s) in roles["inner"].items()}
            for family in FAMILIES:
                cfgs = grid(family)
                scores = []
                for k, cfg in enumerate(cfgs):
                    per_inner = []
                    for name in sorted(roles["inner"]):
                        tr_s, va_s = roles["inner"][name]
                        (x_a, y_a), (x_v, y_v) = inner_data[name]
                        p_v, _ = fit_predict(family, cfg, x_a, y_a, x_v, fold=fold, partition="inner_train",
                                             subjects=[tr_s])
                        per_inner.append(selection_criterion(y_v, p_v, y_a.std(axis=0)))
                    scores.append((per_inner[0], per_inner[1]))
                    tables["history_selection"].append({"fold": fold, "held_out_subject": held, "history_s": h,
                                                        "family": family, "config_index": k,
                                                        "config": json.dumps(cfg, sort_keys=True),
                                                        "inner_A_criterion": per_inner[0],
                                                        "inner_B_criterion": per_inner[1],
                                                        "mean_criterion": (per_inner[0] + per_inner[1]) / 2,
                                                        "inner_A": "->".join(roles["inner"]["A"]),
                                                        "inner_B": "->".join(roles["inner"]["B"])})
                k_sel = select(scores)
                for r in tables["history_selection"]:
                    if (r["fold"], r["history_s"], r["family"]) == (fold, h, family):
                        r["selected"] = int(r["config_index"] == k_sel)
                x_tr, y_tr = pool(subjects, train, h)
                d = run_root() / f"fold{fold}" / f"{family}_h{h}"
                write_json(d / "selection.json", {"fold": fold, "history_s": h, "family": family,
                                                  "selected_index": k_sel, "selected_config": cfgs[k_sel],
                                                  "scores": scores, "n_train": int(x_tr.shape[0]), **design,
                                                  "frozen_at": now()})
                with open_for_write(run_root() / "test_access.jsonl", "a") as fh:
                    fh.write(json.dumps({"at": now(), "fold": fold, "family": family, "history_s": h,
                                         "selected_index": k_sel, **design}) + "\n")
                p_te, _ = fit_predict(family, cfgs[k_sel], x_tr, y_tr, x_te, fold=fold, partition="train",
                                      subjects=train)
                write_predictions(d / "predictions.parquet", fold, family, h, prov_te, y_te, p_te)
                prov["prediction_files_sha256"][f"fold{fold}/{family}_h{h}"] = sha256_file(d / "predictions.parquet")
                preds[f"{family}_h{h}"] = p_te
                fold_rec["selected"][f"{family}_h{h}"] = cfgs[k_sel]
                tables["history_metrics"] += metric_row(fold, held, family, h, "", y_te, p_te, nights, mats,
                                                        train_pool="common", n_train_windows=int(x_tr.shape[0]))
                echo(f"{now()} fold {fold} {family} h{h}: selected {cfgs[k_sel]}")
        # frozen RAW-TCN on the common test endpoints
        keys_te = P8.window_keys(prov_te["device_id"], prov_te["window_start"])
        tcn_seeds = []
        for s in P5.seeds():
            rd = P3.final_dir(fold, s)
            if run_status(rd) != "complete":
                raise P10HistoryError(f"P3 final fold {fold} seed {s} not complete")
            ys, ps, pvs = LB.strict_pairs(read_predictions(rd / "predictions.parquet"))
            kk = P8.window_keys(pvs["device_id"], pvs["window_start"])
            pos = {k: i for i, k in enumerate(kk.tolist())}
            ii = np.array([pos[k] for k in keys_te.tolist()], np.int64)
            if not np.array_equal(ys[ii], y_te):
                raise P10HistoryError(f"fold {fold} seed {s}: frozen TCN targets differ on the common endpoints")
            preds[f"raw_tcn_seed{s}"] = ps[ii]
            tcn_seeds.append(ps[ii])
            tables["history_metrics"] += metric_row(fold, held, "raw_tcn", ENDPOINT_S, s, y_te, ps[ii], nights, mats,
                                                    train_pool="full_40s_labelled",
                                                    n_train_windows=int((fd.labelled & (fd.partition == "train")).sum()))
        # constants: original (full frozen pool) and common pool
        tr_full = fd.labelled & (fd.partition == "train")
        c_orig = LB.constants(fd.targets[tr_full])
        y_common_tr = np.concatenate([subjects[s].targets[subjects[s].common] for s in train])
        c_common = LB.constants(y_common_tr)
        for label, vec, pool_name, n_tr in (("training_mean_orig", c_orig["mean"], "full_40s_labelled", tr_full.sum()),
                                            ("training_median_orig", c_orig["median"], "full_40s_labelled",
                                             tr_full.sum()),
                                            ("training_mean_common", c_common["mean"], "common", len(y_common_tr)),
                                            ("training_median_common", c_common["median"], "common",
                                             len(y_common_tr))):
            p = np.tile(vec, (y_te.shape[0], 1))
            preds[label] = p
            tables["history_metrics"] += metric_row(fold, held, label, "", "", y_te, p, nights, mats,
                                                    train_pool=pool_name, n_train_windows=int(n_tr),
                                                    constant_temperature=float(vec[0]),
                                                    constant_humidity=float(vec[1]))
        tables["history_bootstrap"] += bootstrap_rows(fold, held, y_te, preds, nights, comparison_pairs())
        prov["folds"][fold] = fold_rec
    tables["history_interpretation"] = interpretation_rows(
        [r for r in tables["history_metrics"] if r["predictor"] in FAMILIES], tables["history_bootstrap"])
    tables["history_interpretation_summary"] = interpretation_summary(tables["history_interpretation"])
    tcn = [r for r in tables["history_metrics"] if r["predictor"] == "raw_tcn"]
    tables["history_metrics"] += seed_mean(tcn)
    return tables, prov


def seed_mean(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["fold"], r["subject_id"], r["target"]), []).append(r)
    out = []
    for (fold, s, t), rs in groups.items():
        rec = {k: rs[0][k] for k in ("fold", "subject_id", "target", "predictor", "history_s", "n_windows",
                                    "n_nights", "train_pool", "n_train_windows")}
        rec["seed"] = "mean"
        for k in ("mae", "rmse", "bias", "target_sd", "R", "Q", "r_pooled", "r_within", "r_within_mat"):
            rec[k] = float(np.nanmean([r[k] for r in rs])) if not all(np.isnan(r[k]) for r in rs) else float("nan")
        rec["mae_seed_min"] = float(min(r["mae"] for r in rs))
        rec["mae_seed_max"] = float(max(r["mae"] for r in rs))
        out.append(rec)
    return out


def write_tables(tables: dict[str, list[dict]], prov: dict) -> Path:
    out = metrics_dir()
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r)) or ["none"]
        write_csv(out / f"p10_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    write_json(out / "p10_history_provenance.json", prov)
    return out
