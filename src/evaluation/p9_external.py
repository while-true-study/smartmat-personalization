"""P9 post-hoc external sensitivity validation on User03 (protocol v1.3; D-061; plan §6–§10).

- User03 windows: the reconstructed external artifact (`src/data/p9_user03.py`) windowed exactly like a strict LOSO
  held-out subject (protocol v1.0 window spec; groups subject/device/session/phases/partition; noon-to-noon nights).
- Models: the three frozen P3 RAW-TCN configurations (the folds selected different ones), each with its frozen epoch
  count, trained on all labelled windows of User01, User02 and User07 (union of the P3 outer test windows) with a
  source-fitted target scaler, seeds 0–2; no early stopping, no validation. Comparator: the source training mean.
- User03 is used for evaluation only; explicit guards check it (the v1.0 gate's LOSO rules cannot express a model
  trained on all three primary subjects, so its input and window-group checks are reused and the rest is explicit).
- Metrics reuse the v1.2 definitions (`p8_dynamic.signal_stats`, population SDs) plus per-night MAE/bias/r.
- Interpretation rules of plan §9; night-level intervals only with at least 10 usable nights (P6).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from src.data import paths
from src.data import p9_user03 as U
from src.data.io_guard import open_for_write, write_csv, write_json, write_text
from src.evaluation import p3_loso as P3
from src.evaluation import p8_dynamic as PD
from src.evaluation.leakage import RunContext, check_calendar, check_inputs, check_window_groups
from src.evaluation.metrics import TARGETS
from src.evaluation.p3_loso import (RunLog, begin_run, complete_run, fail_run, frozen_inputs, git_state, now,
                                    run_status, sha256_file)
from src.evaluation.protocol import night_id, window_spec
from src.evaluation.windowing import build_windows, labelled, validate_windows
from src.features.pressure_features import RAW_FEATURES, TargetScaler
from src.training.loso_data import coded_key, rows_from_table

SOURCES = ("User01", "User02", "User07")
CONFIGS = (1, 2, 3)                    # the fold whose frozen selection defines the configuration
MIN_BOOT_NIGHTS = 10
MIN_NIGHT_WINDOWS = PD.MIN_NIGHT_WINDOWS
TWO_THIRDS = 2 / 3
R_FLOOR = PD.R_POS_MIN


class P9Error(RuntimeError):
    pass


def run_root() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "runs" / "p9_user03"


def metrics_dir() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "metrics" / "p9_user03"


def run_dir(config: int, seed: int) -> Path:
    return run_root() / f"config_fold{config}" / f"seed{seed}"


# ---------------------------------------------------------------------------------------------- User03 windows

@dataclass
class ExternalWindows:
    pressure: np.ndarray
    targets: np.ndarray
    labelled: np.ndarray
    night: np.ndarray                  # noon-to-noon night id (local only)
    night_index: np.ndarray            # 1..n in time order (committed outputs use this)
    session: np.ndarray
    window_start: np.ndarray
    first_labels: np.ndarray
    last_labels: np.ndarray
    rows_sha256: str

    def window_groups(self, mask: np.ndarray) -> list[tuple[tuple, tuple]]:
        pairs = np.unique(np.concatenate([self.first_labels[mask], self.last_labels[mask]], axis=1), axis=0)
        return [(tuple(r[:4]), tuple(r[4:])) for r in pairs]


def user03_windows() -> ExternalWindows:
    t = U.load_rows_table()
    rows = rows_from_table(t)
    if set(rows.subject) != {"User03"}:
        raise P9Error("the external artifact must hold User03 rows only")
    part = np.full(rows.ts.size, "external")
    spec = window_spec()
    group = coded_key(rows.subject, rows.device, rows.session, rows.sensor_phase, rows.cq_phase, part)
    w = build_windows(rows.ts, group, spec)
    validate_windows(rows.ts, group, w, spec)
    first, last = w.step_rows[:, 0], w.target_row
    lab = labelled(w, rows.temp_ok, rows.humid_ok)
    lbl = lambda r: np.stack([part[r], rows.session[r], rows.sensor_phase[r], rows.cq_phase[r]], axis=1)  # noqa: E731
    nights = night_id(rows.ts[last]).astype(str)
    order = {n: i + 1 for i, n in enumerate(sorted(set(nights)))}
    man = json.loads(U.manifest_path().read_text(encoding="utf-8"))
    return ExternalWindows(rows.pressure[w.step_rows], rows.targets[last], lab, nights,
                           np.array([order[n] for n in nights], np.int16), rows.session[last], w.t0, lbl(first),
                           lbl(last), man["rows_content_sha256"])


def qa_rows(ew: ExternalWindows, summary: dict) -> dict[str, list[dict]]:
    """Coverage and window QA before any model output (no timestamps, no target values)."""
    nights = []
    for k in sorted(set(ew.night_index.tolist())):
        m = ew.night_index == k
        nights.append({"night_index": k, "windows": int(m.sum()), "labelled_windows": int((m & ew.labelled).sum()),
                       "sessions": int(np.unique(ew.session[m]).size),
                       "usable_for_per_night_r": bool((m & ew.labelled).sum() >= MIN_NIGHT_WINDOWS)})
    return {"coverage": summary["coverage"], "nights": nights,
            "totals": [{"csv_data_rows": sum(s["data_rows"] for s in summary["sources"] if s["role"] == "csv"),
                        "excluded_csv_rows": sum(s["data_rows"] for s in summary["sources"] if s["role"] == "csv")
                        - summary["reconstructed_rows"],
                        "included_minutes": sum(c["minutes"] for c in summary["coverage"] if c["category"] == "included"),
                        "excluded_minutes": sum(c["minutes"] for c in summary["coverage"] if c["category"] != "included"),
                        "reconstructed_rows": summary["reconstructed_rows"], "canonical_rows": summary["canonical_rows"],
                        "dedup_removed_rows": summary["dedup_removed_rows"], "windows": int(ew.labelled.size),
                        "labelled_windows": int(ew.labelled.sum()),
                        "nights_with_labelled_windows": int(sum(r["labelled_windows"] > 0 for r in nights)),
                        "event_punctuation_only_rows": summary["event_punctuation_only_rows"],
                        "dot_value_rows": summary["dot_value_audit"]["rows"],
                        "dot_value_equal_to_csv_p1": summary["dot_value_audit"]["equal_to_csv_p1"]}]}


# ---------------------------------------------------------------------------------------------- source data

def source_windows(sess: P3.P3Session) -> dict:
    """All labelled windows of the three primary subjects: the union of the P3 outer test windows."""
    parts = {"pressure": [], "targets": [], "subject": [], "groups": []}
    for fold in CONFIGS:
        fd = sess.fold(fold)
        te = fd.labelled & (fd.partition == "test")
        if set(fd.prov["subject_id"][te]) != {fd.held_out}:
            raise P9Error(f"fold {fold}: test windows are not the held-out subject")
        parts["pressure"].append(fd.pressure[te])
        parts["targets"].append(fd.targets[te])
        parts["subject"].append(fd.prov["subject_id"][te])
        parts["groups"] += fd.window_groups(te)
    subj = np.concatenate(parts["subject"])
    if set(subj) != set(SOURCES):
        raise P9Error(f"source windows cover {sorted(set(subj))}, expected {SOURCES}")
    return {"pressure": np.concatenate(parts["pressure"]), "targets": np.concatenate(parts["targets"]),
            "subject": subj, "groups": parts["groups"]}


def guards(src: dict, ew: ExternalWindows, scaler: TargetScaler | None) -> list[dict]:
    """Explicit P9 leakage guards (fail closed)."""
    out = []

    def chk(name, fn):
        try:
            problem = fn()
        except Exception as exc:                                               # fail closed
            problem = f"check raised {type(exc).__name__}: {exc}"
        out.append({"check": name, "passed": problem is None, "detail": problem or "ok"})

    chk("training_windows_are_primary_subjects_only",
        lambda: None if set(src["subject"]) == set(SOURCES) and "User03" not in set(src["subject"])
        else f"training subjects {sorted(set(src['subject']))}")
    chk("scaler_fit_on_source_windows_only",
        lambda: None if scaler is None or (sorted(scaler.fit_provenance.get("subjects", [])) == sorted(SOURCES)
                                           and scaler.fit_provenance.get("n") == int(src["targets"].shape[0]))
        else f"scaler provenance {scaler.fit_provenance}")
    chk("inputs_raw_only", lambda: check_inputs(list(RAW_FEATURES)) or check_calendar(list(RAW_FEATURES)) or
        (None if list(RAW_FEATURES) == [f"raw_p{i}" for i in range(1, 7)] else "non-RAW inputs"))
    chk("source_windows_inside_boundaries",
        lambda: check_window_groups(RunContext("loso", fold=0, window_groups=src["groups"])))
    chk("external_windows_inside_boundaries",
        lambda: check_window_groups(RunContext("loso", fold=0, window_groups=ew.window_groups(ew.labelled))))
    chk("no_early_stopping_no_validation", lambda: None)   # enforced by train_tcn(epochs=...) without validation data
    return out


def frozen_config(config: int) -> tuple:
    from src.training.trainer import TCNConfig
    sel = P3.frozen_selection()["folds"][config]
    return TCNConfig(**sel["config"]), int(sel["final_epochs"]), sel


def training_mean(src: dict) -> np.ndarray:
    return P3.training_mean(src["targets"])


# ---------------------------------------------------------------------------------------------- runs

def run_model(sess: P3.P3Session, src: dict, ew: ExternalWindows, config: int, seed: int) -> str:
    import torch
    from src.training.trainer import device, environment, predict_z, to_tensor, train_tcn
    d = run_dir(config, seed)
    if run_status(d) == "complete":
        return "skipped (complete)"
    begin_run(d, f"p9-user03-config{config}-seed{seed}")
    log = RunLog(d, sess.echo)
    try:
        cfg, epochs, sel = frozen_config(config)
        scaler = TargetScaler.fit(src["targets"], scheme="p9_external", fold="all_primary", partition="train",
                                  subjects=list(SOURCES))
        checks = guards(src, ew, scaler)
        write_json(d / "p9_checks.json", {"checked_at": now(), "passed": all(c["passed"] for c in checks),
                                          "checks": checks})
        if not all(c["passed"] for c in checks):
            raise P9Error("P9 guards failed: " + "; ".join(c["check"] for c in checks if not c["passed"]))
        meta = {"run_id": f"p9-user03-config{config}-seed{seed}", **U.design_hashes(), "config_fold": config,
                "selected_index": sel["selected_index"], "config": cfg.as_dict(), "epochs": epochs, "seed": seed,
                "train_subjects": list(SOURCES), "n_train_windows": int(src["targets"].shape[0]),
                "n_external_windows": int(ew.labelled.sum()), "external_rows_sha256": ew.rows_sha256,
                "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance},
                **frozen_inputs(), **git_state(), **environment(), "started_at": now()}
        write_json(d / "run_meta.json", meta)
        res = train_tcn(cfg, src["pressure"], src["targets"], scaler, seed, epochs=epochs, log=log)
        write_csv(d / "history.csv", res.history, list(res.history[0]))
        with open_for_write(d / "model.pt", "wb") as fh:
            torch.save(res.model.state_dict(), fh)
        m = ew.labelled
        pred = scaler.inverse(predict_z(res.model, to_tensor(ew.pressure[m], device())))
        write_json(d / "external_predictions.json", {"n": int(m.sum()), "sha256_of_values":
                                                     hashlib.sha256(pred.tobytes()).hexdigest()})
        with open_for_write(d / "external_predictions.npy", "wb") as fh:
            np.lib.format.write_array(fh, pred)
        meta.update(finished_at=now(), epochs_run=res.epochs_run, train_seconds=round(res.seconds, 1),
                    model_sha256=sha256_file(d / "model.pt"), predictions_sha256=sha256_file(d / "external_predictions.npy"))
        write_json(d / "run_meta.json", meta)
        complete_run(d, ["run_meta.json", "p9_checks.json", "history.csv", "model.pt", "external_predictions.npy",
                         "external_predictions.json"])
        return "complete"
    except BaseException as exc:
        fail_run(d, exc)
        raise


def load_predictions(config: int, seed: int) -> np.ndarray:
    d = run_dir(config, seed)
    if run_status(d) != "complete":
        raise P9Error(f"P9 run config {config} seed {seed} is not complete")
    return np.load(d / "external_predictions.npy")


# ---------------------------------------------------------------------------------------------- metrics

def metric_rows(y: np.ndarray, p: np.ndarray, nights: np.ndarray, night_index: np.ndarray, model: str,
                config: int | str, seed: int | str) -> tuple[list[dict], list[dict]]:
    rows, per_night = [], []
    for i, t in enumerate(TARGETS):
        st = PD.signal_stats(y[:, i], p[:, i], nights)
        pn = PD.per_night_summary(y[:, i], p[:, i], nights) if not st["constant"] else {}
        rows.append({"model": model, "config_fold": config, "seed": seed, "target": t,
                     **{k: st[k] for k in ("mae", "rmse", "bias", "R", "Q", "r_pooled", "r_within", "target_sd",
                                           "identity_gap")},
                     "constant_prediction": st["constant"], **pn, "n_windows": int(y.shape[0]),
                     "n_nights": int(np.unique(nights).size)})
        for k in sorted(set(night_index.tolist())):
            m = night_index == k
            e = p[m, i] - y[m, i]
            r = PD._corr(p[m, i], y[m, i]) if m.sum() >= MIN_NIGHT_WINDOWS and np.std(y[m, i]) > PD.CONST_TOL \
                else float("nan")
            per_night.append({"model": model, "config_fold": config, "seed": seed, "target": t, "night_index": k,
                              "mae": float(np.abs(e).mean()), "bias": float(e.mean()), "r": r,
                              "n_windows": int(m.sum())})
    return rows, per_night


def analyse(ew: ExternalWindows, src_targets: np.ndarray) -> tuple[dict[str, list[dict]], dict]:
    m = ew.labelled
    y, nights, nidx = ew.targets[m], ew.night[m], ew.night_index[m]
    by_seed, per_night = [], []
    tm = P3.training_mean(src_targets)
    r_, pn_ = metric_rows(y, np.tile(tm, (y.shape[0], 1)), nights, nidx, "training_mean", "", "")
    by_seed += r_
    per_night += pn_
    for c in CONFIGS:
        for s in (0, 1, 2):
            r_, pn_ = metric_rows(y, load_predictions(c, s), nights, nidx, "raw_tcn", c, s)
            by_seed += r_
            per_night += pn_
    for r in by_seed:
        if not r["constant_prediction"] and r["identity_gap"] > PD.IDENTITY_TOL:
            raise P9Error("identity R² = 1 + Q² − 2rQ fails")
    summary = seed_summary(by_seed)
    night_summary = seed_mean_per_night(per_night)
    interp = interpretation(summary, night_summary)
    return {"by_seed": by_seed, "per_night": per_night, "summary": summary, "per_night_summary": night_summary,
            "interpretation": interp}, {"training_mean": tm.tolist()}


def seed_summary(by_seed: list[dict]) -> list[dict]:
    out = []
    groups: dict[tuple, list[dict]] = {}
    for r in by_seed:
        groups.setdefault((r["model"], r["config_fold"], r["target"]), []).append(r)
    for (model, c, t), rs in groups.items():
        rec = {"model": model, "config_fold": c, "target": t, "n_seeds": len(rs)}
        for k in ("mae", "rmse", "bias", "R", "Q", "r_pooled", "r_within", "per_night_r_median"):
            v = np.array([r.get(k, float("nan")) for r in rs], np.float64)
            rec[k] = float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")
            if len(rs) > 1 and k in ("mae", "rmse", "bias", "R", "Q", "r_pooled", "r_within"):
                rec[f"{k}_seed_min"] = float(np.nanmin(v))
                rec[f"{k}_seed_max"] = float(np.nanmax(v))
        rec.update(target_sd=rs[0]["target_sd"], n_windows=rs[0]["n_windows"], n_nights=rs[0]["n_nights"])
        out.append(rec)
    for t in TARGETS:                                   # descriptive unweighted mean over configurations
        cfgs = [r for r in out if r["model"] == "raw_tcn" and r["target"] == t]
        rec = {"model": "raw_tcn_mean_over_configurations", "config_fold": "all", "target": t, "n_seeds": 9}
        for k in ("mae", "rmse", "bias", "R", "Q", "r_pooled", "r_within"):
            rec[k] = float(np.mean([r[k] for r in cfgs]))
        rec.update(target_sd=cfgs[0]["target_sd"], n_windows=cfgs[0]["n_windows"], n_nights=cfgs[0]["n_nights"])
        out.append(rec)
    return out


def seed_mean_per_night(per_night: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in per_night:
        groups.setdefault((r["model"], r["config_fold"], r["target"], r["night_index"]), []).append(r)
    out = []
    for (model, c, t, k), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), kv[0][2], kv[0][3])):
        rr = np.array([r["r"] for r in rs], np.float64)
        out.append({"model": model, "config_fold": c, "target": t, "night_index": k,
                    "mae": float(np.mean([r["mae"] for r in rs])), "bias": float(np.mean([r["bias"] for r in rs])),
                    "r": float(np.nanmean(rr)) if np.isfinite(rr).any() else float("nan"),
                    "n_windows": rs[0]["n_windows"], "n_seeds": len(rs)})
    return out


def interpretation(summary: list[dict], night_summary: list[dict]) -> list[dict]:
    """Plan §9 rules per target (no rule depends on a User03-based choice)."""
    out = []
    for t in TARGETS:
        tm = next(r for r in summary if r["model"] == "training_mean" and r["target"] == t)
        tm_n = {r["night_index"]: r["mae"] for r in night_summary if r["model"] == "training_mean" and r["target"] == t}
        nights = sorted(tm_n)
        tcn_better, tm_better, within_sup, within_abs, per_cfg = True, True, True, True, []
        for c in CONFIGS:
            s = next(r for r in summary if r["model"] == "raw_tcn" and r["config_fold"] == c and r["target"] == t)
            cn = {r["night_index"]: r for r in night_summary if r["model"] == "raw_tcn" and r["config_fold"] == c
                  and r["target"] == t}
            nights_tcn_lower = sum(cn[k]["mae"] < tm_n[k] for k in nights)
            nights_tm_lower = sum(tm_n[k] < cn[k]["mae"] for k in nights)
            elig = [k for k in nights if np.isfinite(cn[k]["r"])]
            pos = sum(cn[k]["r"] > 0 for k in elig)
            tcn_better &= s["mae"] < tm["mae"] and nights_tcn_lower >= TWO_THIRDS * len(nights)
            tm_better &= tm["mae"] < s["mae"] and nights_tm_lower >= TWO_THIRDS * len(nights)
            within_sup &= s["r_within"] >= R_FLOOR and len(elig) > 0 and pos >= TWO_THIRDS * len(elig)
            within_abs &= abs(s["r_within"]) < R_FLOOR
            per_cfg.append({"config_fold": c, "nights_tcn_lower_mae": nights_tcn_lower, "nights_tm_lower_mae":
                            nights_tm_lower, "eligible_nights_r": len(elig), "nights_r_positive": pos})
        out.append({"target": t, "n_nights": len(nights),
                    "comparison": "raw_tcn_better" if tcn_better else "training_mean_better" if tm_better else "mixed",
                    "within_night_covariation": "supported" if within_sup else "absent" if within_abs
                    else "inconclusive",
                    "night_bootstrap": "computed" if len(nights) >= MIN_BOOT_NIGHTS else "not computed (< 10 nights)",
                    **{f"cfg{r['config_fold']}_{k}": v for r in per_cfg for k, v in r.items() if k != "config_fold"}})
    comp = {r["target"]: r["comparison"] for r in out}
    cov = {r["target"]: r["within_night_covariation"] for r in out}
    contradicts = {t: comp[t] == "raw_tcn_better" or cov[t] == "supported" for t in TARGETS}
    relation = ("strengthened" if not any(contradicts.values()) else
                "weakened" if all(contradicts.values()) else "mixed")
    for r in out:
        r["relation_to_n3"] = relation
    return out


def write_tables(tables: dict[str, list[dict]], extra: dict, qa: dict[str, list[dict]] | None = None) -> Path:
    out = metrics_dir()
    for name, rows in {**tables, **({f"qa_{k}": v for k, v in qa.items()} if qa else {})}.items():
        cols = list(dict.fromkeys(k for r in rows for k in r)) or ["none"]
        write_csv(out / f"p9_user03_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    write_json(out / "p9_user03_provenance.json", {**U.design_hashes(), **git_state(), **extra})
    return out
