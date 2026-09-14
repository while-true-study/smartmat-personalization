"""P5 chronological user personalization under frozen protocol v1.0 (RQ2; docs/EXPERIMENT_PROTOCOL.md §10; D-037,
D-040, D-041, D-043, D-045).

Per target subject s (= the held-out subject of LOSO fold k), budget b in {0, 1, 3, 7, 14} and seed in {0, 1, 2}:
- base model: the P3 final RAW-TCN of fold k with the same seed (frozen at `p3-loso-baseline`; local checkpoint,
  verified against its P3 run artifacts and predictions);
- b = 0: the base model is evaluated as it is (no training);
- b > 0: every parameter is fine-tuned on the labelled windows of s's earliest b nights (split file), AdamW, learning
  rate 0.1 x the selected base rate, the base weight decay, exactly 10 epochs, batch 256, no early stopping, no
  validation, the base model's outer target scaler (never refit);
- the model is then evaluated once on the budget's test partition. The primary span (nights >= 16) is identical
  for every budget; the per-budget later span is secondary.
Windows follow the frozen rule and are also cut at night and partition boundaries (D-037). Only RAW inputs are used.
Every run calls the P2 leakage gate and ten explicit P5 checks first (fail closed). The per-subject plan (nights,
configurations, scaler, base checkpoints) is committed before any adaptation or evaluation; runs refuse otherwise.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pyarrow as pa
import yaml

from src.data import paths
from src.data.io_guard import open_for_write, write_csv, write_json, write_parquet, write_text
from src.evaluation import p3_loso as P3
from src.evaluation import splits as S
from src.evaluation.leakage import RunContext
from src.evaluation.metrics import TARGETS, target_metrics, unweighted_subject_mean
from src.evaluation.p2_protocol import load_manifest, split_root
from src.evaluation.p3_loso import (P3Session, RunLog, _status, begin_run, complete_run, fail_run, frozen_inputs,
                                    git_state, now, read_predictions, run_status, sha256_file)
from src.evaluation.protocol import PROTOCOL_VERSION, load_protocol, night_id, protocol_sha256, window_spec
from src.evaluation.windowing import build_windows, labelled, validate_windows
from src.features.pressure_features import RAW_FEATURES, TargetScaler

P5_FAMILY = "RAW"
P3_TAG, P4_TAG = "p3-loso-baseline", "p4-feature-ablation"
SPANS = ("primary", "later")


class P5Error(RuntimeError):
    pass


class PlanNotFrozenError(P5Error):
    """Raised when an adaptation or evaluation is attempted before the P5 plan is committed."""


# --------------------------------------------------------------------------------------------------------- protocol

def budgets() -> list[int]:
    return [int(b) for b in load_protocol()["personalization"]["budgets_nights"]]


def seeds() -> list[int]:
    return [int(s) for s in load_protocol()["models"]["seeds"]]


def subject_folds() -> dict[str, int]:
    """Target subject -> the LOSO fold that holds it out (its base model)."""
    return {v: int(k) for k, v in load_protocol()["loso"]["outer_folds"].items()}


def adaptation_config(base_config: dict) -> tuple:
    """The frozen fine-tuning recipe (protocol.yaml personalization.fine_tuning) applied to a base configuration.

    Returns (TCNConfig for fine-tuning, epochs). Refuses any recipe other than the frozen one.
    """
    from src.training.trainer import TCNConfig
    ft = load_protocol()["personalization"]["fine_tuning"]
    want = {"scope": "all_parameters", "optimizer": "adamw", "lr_factor_of_selected_lr": 0.1,
            "weight_decay": "same_as_selected", "epochs": 10, "batch_size": 256, "early_stopping": "none",
            "refit_scalers": False}
    if ft != want:
        raise P5Error(f"personalization fine-tuning recipe differs from the frozen v1.0 recipe: {ft}")
    cfg = TCNConfig(channels=base_config["channels"], kernel_size=base_config["kernel_size"],
                    dropout=base_config["dropout"], lr=ft["lr_factor_of_selected_lr"] * base_config["lr"],
                    weight_decay=base_config["weight_decay"], batch_size=ft["batch_size"], max_epochs=ft["epochs"],
                    early_stopping_patience=base_config["early_stopping_patience"])
    return cfg, int(ft["epochs"])


# ---------------------------------------------------------------------------------------------------------- paths

def run_root() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "runs" / "p5"


def metrics_dir() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "metrics" / "p5"


def plan_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / PROTOCOL_VERSION / "p5_personalization_plan.yaml"


def run_dir(subject: str, budget: int, seed: int) -> Path:
    return run_root() / subject / f"b{budget:02d}_seed{seed}"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=paths.PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")


def p5_git_state() -> dict:
    tags = {t: _git("rev-list", "-n", "1", t).stdout.strip() or None for t in (P3_TAG, P4_TAG)}
    return {**git_state(), "p3_tag_commit": tags[P3_TAG], "p4_tag_commit": tags[P4_TAG]}


# ------------------------------------------------------------------------------------------------ frozen P3 base

def p3_selection() -> dict:
    """The committed P3 RAW-TCN selection (fold -> config, epochs, outer scaler), with its LF SHA-256."""
    doc = P3.frozen_selection()
    doc["file_sha256"] = S.file_sha256_lf(P3.selected_yaml())
    return doc


def weights_digest(state: dict) -> str:
    """SHA-256 over parameter names, shapes, dtypes and bytes (independent of the checkpoint container)."""
    import torch
    h = hashlib.sha256()
    for k in sorted(state):
        t = state[k].detach().to("cpu").contiguous()
        h.update(k.encode())
        h.update(str(tuple(t.shape)).encode() + str(t.dtype).encode())
        h.update(t.numpy().tobytes() if t.dtype != torch.bfloat16 else t.view(torch.int16).numpy().tobytes())
    return h.hexdigest()


def base_run_dir(fold: int, seed: int) -> Path:
    return P3.final_dir(fold, seed)


def load_base_state(fold: int, seed: int) -> tuple[dict, dict]:
    """(state dict, provenance) of the P3 final model of fold x seed; the P3 run must be verifiably complete."""
    import torch
    d = base_run_dir(fold, seed)
    if P3.run_status(d) != "complete":
        raise P5Error(f"P3 base model {d.name} is missing or not verifiably complete")
    meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
    state = torch.load(d / "model.pt", map_location="cpu", weights_only=True)
    rel = d.relative_to(paths.PROJECT_ROOT).as_posix() if d.is_relative_to(paths.PROJECT_ROOT) else d.name
    prov = {"p3_run_dir": rel, "p3_run_id": meta["run_id"],
            "file_sha256": sha256_file(d / "model.pt"), "weights_sha256": weights_digest(state),
            "p3_selection_sha256": meta["selection_sha256"], "p3_git_commit": meta["git_commit"]}
    return state, prov


def base_scaler(fold: int, sel: dict) -> TargetScaler:
    """The outer target scaler of the base model (P3 frozen statistics and fit provenance). Never refit in P5."""
    rec = sel["folds"][fold]["outer_target_scaler"]
    meta = json.loads((base_run_dir(fold, 0) / "run_meta.json").read_text(encoding="utf-8"))
    prov = {k: v for k, v in meta["scaler"].items() if k not in ("mean", "std")}
    if not (np.array_equal(meta["scaler"]["mean"], rec["mean"]) and np.array_equal(meta["scaler"]["std"], rec["std"])):
        raise P5Error(f"fold {fold}: P3 run scaler differs from the committed P3 selection")
    if prov.get("partition") != "train" or sorted(prov.get("subjects", [])) != sorted(sel["folds"][fold]
                                                                                        ["train_subjects"]):
        raise P5Error(f"fold {fold}: scaler provenance is not the outer training pool")
    return TargetScaler(np.asarray(rec["mean"], np.float64), np.asarray(rec["std"], np.float64), prov)


def base_model(fold: int, seed: int, sel: dict):
    from src.models.tcn import TCN
    from src.training.trainer import device
    cfg = sel["folds"][fold]["config"]
    state, prov = load_base_state(fold, seed)
    m = TCN(len(RAW_FEATURES), cfg["channels"], cfg["kernel_size"], cfg["dropout"])
    m.load_state_dict(state)
    return m.to(device()), state, prov


# ------------------------------------------------------------------------------------------------ split / windows

def personalization_split(split_dir: Path | None = None) -> list[dict]:
    return S.read_split((split_root() if split_dir is None else split_dir) / S.PERSONALIZATION)


def budget_nights(pers: list[dict], subject: str, budget: int) -> dict:
    """Night-level partition of subject x budget from the split file (all pieces of a night must agree)."""
    recs = [r for r in pers if r["subject_id"] == subject and int(r["budget_nights"]) == budget]
    if not recs:
        raise P5Error(f"{subject} b={budget}: not in the personalization split")
    part, ordinal, primary, pieces = {}, {}, {}, {}
    for r in recs:
        n = r["night_id"]
        if part.setdefault(n, r["partition"]) != r["partition"]:
            raise P5Error(f"{subject} b={budget}: night {n} has pieces in several partitions")
        ordinal.setdefault(n, int(r["night_ordinal"]))
        primary.setdefault(n, int(r["primary_test"]))
        key = (r["session_id"], n)
        if key in pieces:
            raise P5Error(f"{subject} b={budget}: piece {key} listed twice")
        pieces[key] = r["partition"]
    by = lambda p: sorted((n for n in part if part[n] == p), key=ordinal.get)  # noqa: E731
    return {"partition": part, "ordinal": ordinal, "pieces": pieces, "adaptation": by("adaptation"),
            "buffer": by("buffer"), "test": by("test"), "primary": sorted((n for n in part if primary[n]),
                                                                          key=ordinal.get)}


@dataclass
class SubjectWindows:
    subject: str
    budget: int
    pressure: np.ndarray            # (n, 8, 6) raw integers
    targets: np.ndarray             # (n, 2)
    labelled: np.ndarray
    partition: np.ndarray           # adaptation / buffer / test of the window (its night)
    primary: np.ndarray             # window's night is in the primary test span
    prov: dict[str, np.ndarray]
    first_labels: np.ndarray        # (n, 5): partition, session, sensor_phase, channel_quality_phase, night
    last_labels: np.ndarray
    row_ts: dict[str, tuple[int, int]]   # partition -> (first, last) timestamp of its rows
    adapt_row_max_ts: int | None    # latest timestamp of any row used by an adaptation window

    def mask(self, part: str, primary_only: bool = False) -> np.ndarray:
        m = self.labelled & (self.partition == part)
        return m & self.primary if primary_only else m

    def window_groups(self, mask: np.ndarray) -> list[tuple[tuple, tuple]]:
        pairs = np.unique(np.concatenate([self.first_labels[mask], self.last_labels[mask]], axis=1), axis=0)
        return [(tuple(r[:5]), tuple(r[5:])) for r in pairs]

    def primary_digest(self) -> str:
        """Digest of the labelled primary-test windows (device, night, window start): equal for every budget."""
        m = self.mask("test", primary_only=True)
        keys = np.char.add(np.char.add(self.prov["device_id"][m].astype(str), "|"),
                           np.char.add(np.char.add(self.prov["night_id"][m].astype(str), "|"),
                                       self.prov["window_start"][m].astype(str)))
        return hashlib.sha256("\n".join(sorted(keys.tolist())).encode()).hexdigest()


def subject_windows(rows, subject: str, budget: int, pers: list[dict]) -> SubjectWindows:
    """RQ2 windows of one subject for one budget, built inside partition x session x phase x night groups (L1)."""
    from src.training.loso_data import coded_key
    plan = budget_nights(pers, subject, budget)
    idx = np.flatnonzero(rows.subject == subject)
    if idx.size == 0:
        raise P5Error(f"{subject}: no canonical rows")
    ts = rows.ts[idx]
    nights = night_id(ts)
    sess = rows.session[idx]
    piece = coded_key(sess, nights)
    uniq, first_row, inv = np.unique(piece, return_index=True, return_inverse=True)
    part_u = []
    for i in first_row:
        key = (str(sess[i]), str(nights[i]))
        if key not in plan["pieces"]:
            raise P5Error(f"{subject} b={budget}: canonical piece {key} has no split assignment")
        part_u.append(plan["pieces"][key])
    if len(part_u) != len(plan["pieces"]):
        raise P5Error(f"{subject} b={budget}: split lists pieces that are not in canonical_v1")
    part_rows = np.array(part_u, dtype=object)[inv.reshape(-1)].astype(str)
    group = coded_key(rows.device[idx], sess, rows.sensor_phase[idx], rows.cq_phase[idx], nights, part_rows)
    spec = window_spec()
    w = build_windows(ts, group, spec)
    validate_windows(ts, group, w, spec)
    first, last = w.step_rows[:, 0], w.target_row
    lab = labelled(w, rows.temp_ok[idx], rows.humid_ok[idx])
    lbl = lambda r: np.stack([part_rows[r], sess[r], rows.sensor_phase[idx][r], rows.cq_phase[idx][r],  # noqa: E731
                              nights[r]], axis=1)
    wn = nights[last]
    prov = {"subject_id": rows.subject[idx][last], "device_id": rows.device[idx][last], "session_id": sess[last],
            "sensor_phase": rows.sensor_phase[idx][last], "channel_quality_phase": rows.cq_phase[idx][last],
            "night_id": wn, "night_ordinal": np.array([plan["ordinal"][n] for n in wn], np.int16),
            "window_start": w.t0, "window_end": w.t0 + spec.duration_s, "target_timestamp": ts[last]}
    row_ts = {p: (int(ts[part_rows == p].min()), int(ts[part_rows == p].max())) for p in np.unique(part_rows)}
    wpart = part_rows[last]
    adapt = wpart == "adaptation"
    adapt_max = int(ts[w.step_rows[adapt]].max()) if adapt.any() else None
    return SubjectWindows(subject, budget, rows.pressure[idx][w.step_rows], rows.targets[idx][last], lab, wpart,
                          np.isin(wn, plan["primary"]), prov, lbl(first), lbl(last), row_ts, adapt_max)


class P5Session(P3Session):
    """P3 session (canonical rows, gate structure) plus per subject x budget RQ2 windows."""

    def __init__(self, echo: bool = True):
        super().__init__(echo)
        self._pers = None
        self._sw: dict[tuple[str, int], SubjectWindows] = {}

    def pers(self) -> list[dict]:
        if self._pers is None:
            self._pers = personalization_split()
        return self._pers

    def windows(self, subject: str, budget: int) -> SubjectWindows:
        if (subject, budget) not in self._sw:
            self._sw[(subject, budget)] = subject_windows(self.rows(), subject, budget, self.pers())
        return self._sw[(subject, budget)]


# ------------------------------------------------------------------------------------------------------ P5 checks

def p5_checks(subject: str, budget: int, sw: SubjectWindows, nights: dict, pers: list[dict], sel: dict,
              scaler: TargetScaler, cfg, epochs: int, plan_rec: dict) -> list[dict]:
    """The ten explicit P5 leakage checks (fail closed: a check that raises counts as failed)."""
    fold = subject_folds()[subject]
    out = []

    def chk(name: str, fn):
        try:
            problem = fn()
        except Exception as exc:                                              # fail closed
            problem = f"check raised {type(exc).__name__}: {exc}"
        out.append({"check": name, "passed": problem is None, "detail": problem or "ok"})

    def base_disjoint():
        outer = [r for r in S.read_split(split_root() / S.LOSO_OUTER) if int(r["fold"]) == fold]
        train = {r["subject_id"] for r in outer if r["partition"] == "train"}
        held = {r["held_out_subject"] for r in outer}
        if held != {subject} or subject in train or train != set(sel["folds"][fold]["train_subjects"]):
            return f"fold {fold}: held out {held}, train {sorted(train)}"
    chk("base_training_subjects_exclude_target", base_disjoint)
    chk("adaptation_and_test_nights_disjoint",
        lambda: None if not set(nights["adaptation"]) & (set(nights["test"]) | set(nights["primary"]))
        else "adaptation night also in test")
    def buffer_unused():
        if set(nights["buffer"]) & (set(nights["adaptation"]) | set(nights["test"])):
            return "buffer night also in adaptation or test"
        if len(nights["buffer"]) != (1 if budget else 0):
            return f"{len(nights['buffer'])} buffer nights"
        used = sw.mask("adaptation") | sw.mask("test")
        if np.isin(sw.prov["night_id"][used], nights["buffer"]).any():
            return "a training or evaluation window lies in the buffer night"
    chk("buffer_night_unused", buffer_unused)

    def devices_together():
        part = {}
        for r in pers:
            if r["subject_id"] == subject and int(r["budget_nights"]) == budget:
                if part.setdefault(r["night_id"], r["partition"]) != r["partition"]:
                    return f"night {r['night_id']}: devices/sessions in different partitions"
    chk("all_devices_of_a_night_same_partition", devices_together)
    def pieces_once():
        recs = [(r["session_id"], r["night_id"]) for r in pers if r["subject_id"] == subject
                and int(r["budget_nights"]) == budget]
        if len(recs) != len(set(recs)) or set(recs) != set(nights["pieces"]):
            return "a session x night piece is listed in more than one partition"
        wp = {(s, n): p for s, n, p in zip(sw.prov["session_id"], sw.prov["night_id"], sw.partition)}
        if any(nights["pieces"][k] != p for k, p in wp.items()):
            return "a window's partition differs from its piece's partition"
    chk("session_night_piece_in_one_partition", pieces_once)
    chk("scaler_fit_on_outer_training_subjects_only",
        lambda: None if scaler.fit_provenance.get("partition") == "train" and subject not in
        scaler.fit_provenance.get("subjects", []) and sorted(scaler.fit_provenance["subjects"]) ==
        sorted(sel["folds"][fold]["train_subjects"]) else f"scaler provenance {scaler.fit_provenance}")
    chk("scaler_not_refit_on_target_data",
        lambda: None if np.array_equal(scaler.mean, sel["folds"][fold]["outer_target_scaler"]["mean"])
        and np.array_equal(scaler.std, sel["folds"][fold]["outer_target_scaler"]["std"]) else "scaler differs")
    chk("windows_inside_partition_night_session_phase",
        lambda: None if np.array_equal(sw.first_labels, sw.last_labels) else "a window crosses a boundary")

    def no_future_rows():
        if budget == 0:
            return None if not sw.mask("adaptation").any() else "b=0 has adaptation windows"
        later = min(sw.row_ts[p][0] for p in ("buffer", "test") if p in sw.row_ts)
        if sw.adapt_row_max_ts is None or not sw.adapt_row_max_ts < later:
            return f"adaptation rows reach {sw.adapt_row_max_ts}, buffer/test start {later}"
    chk("adaptation_windows_precede_buffer_and_test", no_future_rows)

    def recipe_frozen():
        want_cfg, want_ep = adaptation_config(sel["folds"][fold]["config"])
        if cfg != want_cfg or epochs != want_ep:
            return "adaptation configuration differs from the frozen recipe"
        if plan_rec["adaptation"]["lr"] != want_cfg.lr or plan_rec["seeds"] != seeds():
            return "committed plan differs from the frozen recipe"
        if sw.primary_digest() != plan_rec["primary_test"]["windows_sha256"]:
            return "primary test windows differ from the committed plan"
    chk("no_test_based_selection_recipe_frozen", recipe_frozen)
    return out


# ------------------------------------------------------------------------------------------------------ plan

def build_plan(sess: P5Session) -> dict:
    """Per-subject personalization plan from frozen inputs only (split, protocol, P3 selection, P3 checkpoints)."""
    sel = p3_selection()
    subjects = {}
    for subject, fold in sorted(subject_folds().items(), key=lambda kv: kv[1]):
        base_cfg = sel["folds"][fold]["config"]
        cfg, epochs = adaptation_config(base_cfg)
        scaler = base_scaler(fold, sel)
        ckpts = {}
        for s in seeds():
            _, prov = load_base_state(fold, s)
            ckpts[s] = prov
        per_budget, digests = {}, set()
        for b in budgets():
            nights = budget_nights(sess.pers(), subject, b)
            sw = sess.windows(subject, b)
            digests.add(sw.primary_digest())
            per_budget[b] = {"adaptation_nights": nights["adaptation"], "buffer_nights": nights["buffer"],
                             "later_test_nights": len(nights["test"]), "later_test_first": nights["test"][0],
                             "later_test_last": nights["test"][-1],
                             "adaptation_windows": int(sw.mask("adaptation").sum()),
                             "buffer_windows": int(sw.mask("buffer").sum()),
                             "later_test_windows": int(sw.mask("test").sum()),
                             "primary_test_windows": int(sw.mask("test", True).sum())}
        if len(digests) != 1:
            raise P5Error(f"{subject}: primary test windows differ between budgets")
        prim = budget_nights(sess.pers(), subject, 0)["primary"]
        subjects[subject] = {
            "fold": fold, "base_train_subjects": sel["folds"][fold]["train_subjects"], "base_family": P5_FAMILY,
            "base_selected_index": sel["folds"][fold]["selected_index"], "base_config": base_cfg,
            "base_final_epochs": sel["folds"][fold]["final_epochs"],
            "base_selection_sha256": sel["folds"][fold]["selection_sha256"],
            "outer_target_scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(),
                                    "n": scaler.fit_provenance["n"], "subjects": scaler.fit_provenance["subjects"],
                                    "partition": scaler.fit_provenance["partition"]},
            "base_checkpoints": ckpts,
            "adaptation": {"scope": "all_parameters", "optimizer": "adamw", "lr": cfg.lr, "base_lr": base_cfg["lr"],
                           "lr_factor": 0.1, "weight_decay": cfg.weight_decay, "epochs": epochs,
                           "batch_size": cfg.batch_size, "early_stopping": "none", "validation": "none",
                           "refit_scaler": False},
            "seeds": seeds(), "seed_pairing": "adaptation seed s starts from the base model of seed s",
            "primary_test": {"from_ordinal": int(load_protocol()["personalization"]["primary_test_from_ordinal"]),
                             "n_nights": len(prim), "nights": prim, "windows_sha256": digests.pop(),
                             "windows": per_budget[0]["primary_test_windows"]},
            "budgets": per_budget}
    return {"description": "P5 frozen personalization plan (protocol v1.0; generated by scripts/"
                           "run_p5_personalization.py plan from frozen inputs only, before any adaptation or P5 "
                           "evaluation)",
            "protocol_version": PROTOCOL_VERSION, "protocol_sha256": protocol_sha256(),
            "split_sha256": {k: v["sha256"] for k, v in load_manifest()["files"].items()},
            "family": P5_FAMILY, "budgets_nights": budgets(),
            "p3_selected_configs_sha256": sel["file_sha256"], "p3_tag": P3_TAG, "p4_tag": P4_TAG,
            "subjects": subjects}


def export_plan(sess: P5Session) -> dict:
    doc = build_plan(sess)
    text = yaml.safe_dump(doc, sort_keys=False)
    p = plan_yaml()
    if p.exists() and p.read_text(encoding="utf-8").replace("\r\n", "\n") != text:
        raise P5Error("committed P5 plan exists with different content; refusing to change it")
    write_text(p, text)
    return doc


def plan_commit() -> str:
    """Commit holding the plan; refuses unless the file is tracked and unmodified (plan before adaptation/test)."""
    try:
        rel = plan_yaml().relative_to(paths.PROJECT_ROOT).as_posix()
    except ValueError:
        raise PlanNotFrozenError(f"{plan_yaml()} is outside the repository") from None
    if not plan_yaml().exists() or _git("ls-files", "--error-unmatch", rel).returncode != 0:
        raise PlanNotFrozenError(f"{rel} is not committed")
    if _git("diff", "--quiet", "HEAD", "--", rel).returncode != 0:
        raise PlanNotFrozenError(f"{rel} differs from its committed version")
    return _git("log", "-n", "1", "--format=%H", "--", rel).stdout.strip()


def frozen_plan() -> dict:
    p = plan_yaml()
    if not p.exists():
        raise PlanNotFrozenError(f"{p.name} does not exist")
    doc = yaml.safe_load(p.read_text(encoding="utf-8"))
    if doc["protocol_sha256"] != protocol_sha256():
        raise P5Error("protocol file changed after the plan was frozen")
    if doc["split_sha256"] != {k: v["sha256"] for k, v in load_manifest()["files"].items()}:
        raise P5Error("split files changed after the plan was frozen")
    if doc["family"] != P5_FAMILY or doc["budgets_nights"] != budgets():
        raise P5Error("plan family or budgets differ from protocol v1.0")
    if sorted(doc["subjects"]) != sorted(subject_folds()):
        raise PlanNotFrozenError("plan does not cover every subject")
    return doc


# ------------------------------------------------------------------------------------------------------ run

PRED_SCHEMA = pa.schema([
    ("run_id", pa.string()), ("model", pa.string()), ("subject_id", pa.string()), ("fold", pa.int8()),
    ("budget_nights", pa.int8()), ("seed", pa.int16()), ("device_id", pa.string()), ("session_id", pa.string()),
    ("sensor_phase", pa.string()), ("channel_quality_phase", pa.string()), ("night_id", pa.string()),
    ("night_ordinal", pa.int16()), ("primary_test", pa.bool_()), ("window_start", pa.timestamp("s")),
    ("window_end", pa.timestamp("s")), ("target_timestamp", pa.timestamp("s")), ("target", pa.string()),
    ("y_true", pa.float64()), ("y_pred", pa.float64())])


def write_predictions(path: Path, run_id: str, model: str, subject: str, fold: int, budget: int, seed: int,
                      sw: SubjectWindows, mask: np.ndarray, y: np.ndarray, p: np.ndarray) -> None:
    n = int(mask.sum())
    rep = lambda a: np.tile(np.asarray(a)[mask], 2)  # noqa: E731
    t = pa.table({
        "run_id": pa.array([run_id] * 2 * n), "model": pa.array([model] * 2 * n),
        "subject_id": pa.array(rep(sw.prov["subject_id"]).astype(str)),
        "fold": pa.array(np.full(2 * n, fold, np.int8)), "budget_nights": pa.array(np.full(2 * n, budget, np.int8)),
        "seed": pa.array(np.full(2 * n, seed, np.int16)),
        **{c: pa.array(rep(sw.prov[c]).astype(str)) for c in ("device_id", "session_id", "sensor_phase",
                                                             "channel_quality_phase", "night_id")},
        "night_ordinal": pa.array(rep(sw.prov["night_ordinal"]).astype(np.int16)),
        "primary_test": pa.array(rep(sw.primary)),
        **{c: pa.array(rep(sw.prov[c]).astype("datetime64[s]"), pa.timestamp("s"))
           for c in ("window_start", "window_end", "target_timestamp")},
        "target": pa.array(np.repeat(np.array(TARGETS), n)),
        "y_true": pa.array(np.concatenate([y[:, 0], y[:, 1]])),
        "y_pred": pa.array(np.concatenate([p[:, 0], p[:, 1]]))}, schema=PRED_SCHEMA)
    write_parquet(path, [t], PRED_SCHEMA)


def span_metrics(y: np.ndarray, p: np.ndarray, primary: np.ndarray, nights: np.ndarray) -> dict:
    out = {}
    for span, m in (("primary", primary), ("later", np.ones(len(y), bool))):
        out[span] = {"metrics": target_metrics(y[m], p[m]), "n_windows": int(m.sum()),
                     "n_nights": int(np.unique(nights[m]).size)}
    return out


def per_night_rows(y: np.ndarray, p: np.ndarray, sw: SubjectWindows, mask: np.ndarray) -> list[dict]:
    nights = sw.prov["night_id"][mask]
    ordn = sw.prov["night_ordinal"][mask]
    prim = sw.primary[mask]
    uniq, inv = np.unique(nights, return_inverse=True)
    rows = []
    for i, t in enumerate(TARGETS):
        err = p[:, i] - y[:, i]
        cnt = np.bincount(inv)
        mae = np.bincount(inv, weights=np.abs(err)) / cnt
        rmse = np.sqrt(np.bincount(inv, weights=err ** 2) / cnt)
        bias = np.bincount(inv, weights=err) / cnt
        for j, n in enumerate(uniq):
            k = np.flatnonzero(inv == j)[0]
            rows.append({"night_id": n, "night_ordinal": int(ordn[k]), "primary_test": int(prim[k]), "target": t,
                         "mae": float(mae[j]), "rmse": float(rmse[j]), "bias": float(bias[j]),
                         "n_windows": int(cnt[j])})
    return rows


def log_test_access(subject: str, budget: int, seed: int, run_id: str, commit: str) -> None:
    with open_for_write(run_root() / "test_access.jsonl", "a") as fh:
        fh.write(json.dumps({"at": now(), "subject": subject, "budget": budget, "seed": seed, "run_id": run_id,
                             "plan_commit": commit}) + "\n")


def run_personalization(sess: P5Session, subject: str, budget: int, seed: int) -> str:
    import torch
    from src.training.trainer import device, environment, predict_z, set_determinism, to_tensor, train_tcn

    d = run_dir(subject, budget, seed)
    if run_status(d) == "complete":
        return "skipped (complete)"
    if budget not in budgets() or seed not in seeds() or subject not in subject_folds():
        raise P5Error(f"{subject} b={budget} seed {seed} is not a declared P5 run")
    plan = frozen_plan()                                   # refuses before anything if the plan is not frozen
    commit = plan_commit()
    rec = plan["subjects"][subject]
    fold = subject_folds()[subject]
    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_p5-{subject}-b{budget:02d}-seed{seed}"
    begin_run(d, run_id)
    log = RunLog(d, sess.echo)
    try:
        sel = p3_selection()
        if rec["base_selection_sha256"] != sel["folds"][fold]["selection_sha256"]:
            raise P5Error("P3 selection differs from the committed plan")
        nights = budget_nights(sess.pers(), subject, budget)
        if nights["adaptation"] != rec["budgets"][budget]["adaptation_nights"] or \
                nights["buffer"] != rec["budgets"][budget]["buffer_nights"]:
            raise P5Error("adaptation/buffer nights differ from the committed plan")
        sw = sess.windows(subject, budget)
        tr, te = sw.mask("adaptation"), sw.mask("test")
        scaler = base_scaler(fold, sel)                    # frozen base statistics, never refit
        ctx = RunContext("personalization", subject=subject, budget=budget, input_features=list(RAW_FEATURES),
                         fit_records=[dict(scaler.fit_provenance)], selection_subjects=[],
                         window_groups=sw.window_groups(tr | te))
        _, verified = sess.gate(d, ctx)
        cfg, epochs = adaptation_config(sel["folds"][fold]["config"])
        checks = p5_checks(subject, budget, sw, nights, sess.pers(), sel, scaler, cfg, epochs, rec)
        write_json(d / "p5_checks.json", {"checked_at": now(), "passed": all(c["passed"] for c in checks),
                                           "checks": checks})
        if not all(c["passed"] for c in checks):
            raise P5Error("P5 leakage checks failed: " + "; ".join(f"{c['check']}: {c['detail']}"
                                                                  for c in checks if not c["passed"]))
        model, state, base_prov = base_model(fold, seed, sel)
        if base_prov["weights_sha256"] != rec["base_checkpoints"][seed]["weights_sha256"]:
            raise P5Error("base checkpoint weights differ from the committed plan")
        set_determinism(seed)                              # flags recorded as used (train_tcn re-seeds)
        meta = {"run_id": run_id, "phase": "P5", "kind": "base_eval" if budget == 0 else "adaptation",
                "subject": subject, "held_out_subject": subject, "fold": fold, "budget_nights": budget, "seed": seed,
                "family": P5_FAMILY, "input_features": list(RAW_FEATURES),
                "base_config": sel["folds"][fold]["config"], "base_lr": sel["folds"][fold]["config"]["lr"],
                "adaptation_config": cfg.as_dict() if budget else None, "adaptation_epochs": epochs if budget else 0,
                "optimizer": "adamw" if budget else None, "adaptation_nights": nights["adaptation"],
                "buffer_nights": nights["buffer"], "primary_test_nights": rec["primary_test"]["nights"],
                "later_test_nights": nights["test"], "n_adaptation_windows": int(tr.sum()),
                "n_test_windows": int(te.sum()), "n_primary_test_windows": int((te & sw.primary).sum()),
                "base_checkpoint": base_prov, "p3_selected_configs_sha256": sel["file_sha256"],
                "plan_commit": commit, "plan_sha256": S.file_sha256_lf(plan_yaml()),
                "scaler": {"mean": scaler.mean.tolist(), "std": scaler.std.tolist(), **scaler.fit_provenance},
                **frozen_inputs(verified), **p5_git_state(), **environment(), "started_at": now()}
        write_json(d / "run_meta.json", meta)
        files = ["config.yaml", "run_meta.json", "leakage_check.json", "p5_checks.json"]
        write_text(d / "config.yaml", yaml.safe_dump({"subject": subject, "fold": fold, "budget_nights": budget,
                                                      "seed": seed, "family": P5_FAMILY,
                                                      "adaptation": cfg.as_dict() if budget else None,
                                                      "epochs": epochs if budget else 0}, sort_keys=False))
        if budget > 0:
            res = train_tcn(cfg, sw.pressure[tr], sw.targets[tr], scaler, seed, epochs=epochs, log=log,
                            init_state=state)
            model = res.model
            write_csv(d / "history.csv", res.history, list(res.history[0]))
            with open_for_write(d / "model.pt", "wb") as fh:
                torch.save(model.state_dict(), fh)
            files += ["history.csv", "model.pt"]
            train_info = {"epochs_run": res.epochs_run, "train_seconds": round(res.seconds, 1),
                          "model_sha256": sha256_file(d / "model.pt"), "weights_sha256":
                              weights_digest(model.state_dict())}
        else:
            train_info = {"epochs_run": 0, "model_sha256": base_prov["file_sha256"],
                          "weights_sha256": base_prov["weights_sha256"]}
        # the single test look for this model
        log_test_access(subject, budget, seed, run_id, commit)
        pred = scaler.inverse(predict_z(model, to_tensor(sw.pressure[te], device())))
        y = sw.targets[te]
        sm = span_metrics(y, pred, sw.primary[te], sw.prov["night_id"][te])
        rows = [{"run_id": run_id, "subject_id": subject, "fold": fold, "budget_nights": budget, "seed": seed,
                 "span": span, "target": t, "metric": k, "value": v, "n_windows": r["n_windows"],
                 "n_nights": r["n_nights"]}
                for span, r in sm.items() for t, dd in r["metrics"].items() for k, v in dd.items()]
        write_csv(d / "metrics.csv", rows, list(rows[0]))
        pn = [{"subject_id": subject, "fold": fold, "budget_nights": budget, "seed": seed, **r}
              for r in per_night_rows(y, pred, sw, te)]
        write_csv(d / "per_night.csv", pn, list(pn[0]))
        write_predictions(d / "predictions.parquet", run_id, "tcn_raw_personalized" if budget else "tcn_raw_base",
                          subject, fold, budget, seed, sw, te, y, pred)
        files += ["metrics.csv", "per_night.csv", "predictions.parquet"]
        meta.update(finished_at=now(), **train_info, predictions_sha256=sha256_file(d / "predictions.parquet"),
                    primary_metrics=sm["primary"]["metrics"], later_metrics=sm["later"]["metrics"])
        write_json(d / "run_meta.json", meta)
        log(f"{subject} b={budget} seed {seed}: primary {json.dumps(sm['primary']['metrics'])}")
        complete_run(d, files)
        return "complete"
    except BaseException as exc:
        fail_run(d, exc)
        raise


# --------------------------------------------------------------------------------------------- base verification

def verify_base(sess: P3Session) -> dict:
    """Each P3 base checkpoint reproduces its stored P3 outer predictions bitwise (no metric is recomputed)."""
    from src.training.trainer import device, predict_z, to_tensor
    sel = p3_selection()
    out = {"checked_at": now(), "runs": []}
    for fold in sorted(sel["folds"]):
        fd = sess.fold(fold)
        te = fd.labelled & (fd.partition == "test")
        scaler = base_scaler(fold, sel)
        x = to_tensor(fd.pressure[te], device())
        for s in seeds():
            model, _, prov = base_model(fold, s, sel)
            pred = scaler.inverse(predict_z(model, x))
            y, p_ref, _ = P3._pairs(read_predictions(base_run_dir(fold, s) / "predictions.parquet"))
            same = bool(np.array_equal(pred, p_ref) and np.array_equal(fd.targets[te], y))
            out["runs"].append({"fold": fold, "seed": s, **prov, "predictions_bitwise_identical": same})
    out["passed"] = all(r["predictions_bitwise_identical"] for r in out["runs"])
    write_json(run_root() / "base_verification.json", out)
    return out


# ------------------------------------------------------------------------------------------------------ analysis

def err_sd(rmse: float, bias: float) -> float:
    return float(np.sqrt(max(rmse ** 2 - bias ** 2, 0.0)))


def _read_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def by_seed_rows() -> list[dict]:
    """Per subject x budget x seed x span x target metrics from complete runs (fails if any run is missing)."""
    out = []
    for subject, fold in sorted(subject_folds().items(), key=lambda kv: kv[1]):
        for b in budgets():
            for s in seeds():
                d = run_dir(subject, b, s)
                if run_status(d) != "complete":
                    raise P5Error(f"{subject} b={b} seed {s} is not complete")
                m = {}
                for r in _read_csv(d / "metrics.csv"):
                    m.setdefault((r["span"], r["target"]), {"n_windows": int(r["n_windows"]),
                                                            "n_nights": int(r["n_nights"])})[r["metric"]] = \
                        float(r["value"])
                for (span, t), v in m.items():
                    out.append({"subject_id": subject, "fold": fold, "budget_nights": b, "seed": s, "span": span,
                                "target": t, "mae": v["mae"], "rmse": v["rmse"], "bias": v["bias"],
                                "err_sd": err_sd(v["rmse"], v["bias"]), "n_windows": v["n_windows"],
                                "n_nights": v["n_nights"]})
    return out


def seed_summary(rows: list[dict], span: str) -> list[dict]:
    """Seed mean/SD/min/max per subject x budget x target x metric, plus the unweighted 3-subject mean."""
    out, subjects = [], sorted(subject_folds(), key=subject_folds().get)
    for t in TARGETS:
        for metric in ("mae", "rmse", "bias", "err_sd", "abs_bias"):
            for b in budgets():
                means = {}
                for subject in subjects:
                    rs = [r for r in rows if r["subject_id"] == subject and r["budget_nights"] == b
                          and r["span"] == span and r["target"] == t]
                    v = np.array([abs(r["bias"]) if metric == "abs_bias" else r[metric] for r in rs])
                    means[subject] = float(v.mean())
                    out.append({"subject_id": subject, "fold": rs[0]["fold"], "budget_nights": b, "span": span,
                                "target": t, "metric": metric, "seed_mean": means[subject],
                                "seed_sd": float(v.std(ddof=1)), "seed_min": float(v.min()),
                                "seed_max": float(v.max()), "n_seeds": len(v), "n_windows": rs[0]["n_windows"],
                                "n_nights": rs[0]["n_nights"]})
                out.append({"subject_id": "unweighted_mean", "fold": "", "budget_nights": b, "span": span,
                            "target": t, "metric": metric, "seed_mean": unweighted_subject_mean(means),
                            "seed_sd": "", "seed_min": "", "seed_max": "", "n_seeds": 3, "n_windows": "",
                            "n_nights": ""})
    return out


def gain_rows(rows: list[dict], summary: list[dict], span: str = "primary") -> list[dict]:
    """Adaptation effect per subject, target and budget (D-045), from seed means; never clipped:
    G_b = (E_0 - E_b) / E_0 x 100 and dE_b = E_0 - E_b with E = MAE; C_b = |Bias_0| - |Bias_b|.

    Seed-paired columns compare adaptation seed s with its own base model (seed s). The cohort row
    ('unweighted_mean') takes E from the unweighted 3-subject MAE means, and averages |bias| and the error SD over
    subjects (a mean of signed biases would cancel between subjects).
    """
    val = {(r["subject_id"], r["budget_nights"], r["target"], r["metric"]): r["seed_mean"] for r in summary
           if r["span"] == span}
    subjects = sorted(subject_folds(), key=subject_folds().get)
    out = []
    for t in TARGETS:
        for b in budgets():
            subj_rows = []
            for subject in subjects:
                e0, b0, s0, r0 = (val[(subject, 0, t, m)] for m in ("mae", "bias", "err_sd", "rmse"))
                eb, bb, sb, rb = (val[(subject, b, t, m)] for m in ("mae", "bias", "err_sd", "rmse"))
                g = []
                for s in seeds():
                    m0, mb = (next(r["mae"] for r in rows if r["subject_id"] == subject and r["budget_nights"] == bud
                                   and r["seed"] == s and r["span"] == span and r["target"] == t) for bud in (0, b))
                    g.append((m0 - mb) / m0 * 100)
                subj_rows.append({"subject_id": subject, "target": t, "budget_nights": b, "span": span,
                                  "E0_mae": e0, "Eb_mae": eb, "delta_E": e0 - eb, "G_pct": (e0 - eb) / e0 * 100,
                                  "rmse_0": r0, "rmse_b": rb, "bias_0": b0, "bias_b": bb, "abs_bias_0": abs(b0),
                                  "abs_bias_b": abs(bb), "C_b": abs(b0) - abs(bb), "err_sd_0": s0, "err_sd_b": sb,
                                  "delta_err_sd": s0 - sb, "seeds_improved": int(sum(x > 0 for x in g)),
                                  "seed_G_min": min(g), "seed_G_max": max(g)})
            mean = lambda k: float(np.mean([r[k] for r in subj_rows]))  # noqa: E731
            e0 = unweighted_subject_mean({r["subject_id"]: r["E0_mae"] for r in subj_rows})
            eb = unweighted_subject_mean({r["subject_id"]: r["Eb_mae"] for r in subj_rows})
            out += subj_rows + [{"subject_id": "unweighted_mean", "target": t, "budget_nights": b, "span": span,
                                 "E0_mae": e0, "Eb_mae": eb, "delta_E": e0 - eb, "G_pct": (e0 - eb) / e0 * 100,
                                 "rmse_0": mean("rmse_0"), "rmse_b": mean("rmse_b"), "abs_bias_0": mean("abs_bias_0"),
                                 "abs_bias_b": mean("abs_bias_b"), "C_b": mean("C_b"), "err_sd_0": mean("err_sd_0"),
                                 "err_sd_b": mean("err_sd_b"), "delta_err_sd": mean("delta_err_sd"),
                                 "subjects_improved": int(sum(r["delta_E"] > 0 for r in subj_rows))}]
    return out


def strata_rows_p5(preds: dict[tuple[str, int, int], tuple]) -> list[dict]:
    """Primary-span strata: User02 devices (and 22482 quality phases), User01 sensor phases; per seed + seed mean."""
    out = []
    for (subject, b, s), (y, p, prov) in sorted(preds.items()):
        m = prov["primary_test"]
        strata = []
        if subject == "User02":
            strata += [("device", dv, prov["device_id"] == dv) for dv in ("22480", "22482")]
            strata += [("device_x_channel_quality_phase", f"22482/{q}",
                        (prov["device_id"] == "22482") & (prov["channel_quality_phase"] == q))
                       for q in ("normal", "p1_transition", "p1_response_shift")]
        if subject == "User01":
            strata += [("sensor_phase", ph, prov["sensor_phase"] == ph) for ph in ("s1", "s2")]
        for kind, name, sm in strata:
            mm = m & sm
            if not mm.any():
                continue
            for t, dd in target_metrics(y[mm], p[mm]).items():
                for k, v in dd.items():
                    out.append({"subject_id": subject, "budget_nights": b, "seed": s, "stratum_type": kind,
                                "stratum": name, "target": t, "metric": k, "value": v, "n_windows": int(mm.sum()),
                                "n_nights": int(np.unique(prov["night_id"][mm]).size)})
    means = {}
    for r in out:
        means.setdefault((r["subject_id"], r["budget_nights"], r["stratum_type"], r["stratum"], r["target"],
                          r["metric"]), []).append(r)
    for k, rs in means.items():
        v = np.array([r["value"] for r in rs])
        out.append({**{kk: rs[0][kk] for kk in ("subject_id", "budget_nights", "stratum_type", "stratum", "target",
                                                 "metric", "n_windows", "n_nights")},
                    "seed": "mean", "value": float(v.mean()), "seed_sd": float(v.std(ddof=1))})
    return out


def aggregate() -> dict[str, list[dict]]:
    plan = frozen_plan()
    rows = by_seed_rows()
    tables = {"by_seed": rows}
    prim = seed_summary(rows, "primary")
    tables["primary_summary"] = prim
    tables["later_summary"] = seed_summary(rows, "later")
    tables["adaptation_gain"] = gain_rows(rows, prim, "primary")
    tables["adaptation_gain_later"] = gain_rows(rows, tables["later_summary"], "later")
    preds, per_night, pooled = {}, [], {}
    for subject in subject_folds():
        for b in budgets():
            for s in seeds():
                d = run_dir(subject, b, s)
                pr = read_predictions(d / "predictions.parquet")
                t = pr["target"] == "temperature"
                h = pr["target"] == "humidity"
                y = np.stack([pr["y_true"][t], pr["y_true"][h]], 1)
                p = np.stack([pr["y_pred"][t], pr["y_pred"][h]], 1)
                prov = {k: v[t] for k, v in pr.items() if k not in ("target", "y_true", "y_pred")}
                preds[(subject, b, s)] = (y, p, prov)
                m = prov["primary_test"]
                logged = {(r["target"], r["metric"]): float(r["value"]) for r in _read_csv(d / "metrics.csv")
                          if r["span"] == "primary"}
                if any(logged[(tt, k)] != v for tt, dd in target_metrics(y[m], p[m]).items() for k, v in dd.items()):
                    raise P5Error(f"{d}: predictions do not reproduce metrics.csv")
                per_night += _read_csv(d / "per_night.csv")
                pooled.setdefault((b, s), []).append((y[m], p[m]))
    tables["per_night"] = per_night
    tables["strata"] = strata_rows_p5(preds)
    tables["pooled_primary"] = [{"budget_nights": b, "seed": s, "target": t, "metric": k, "value": v,
                                 "n_windows": int(sum(len(q[0]) for q in parts))}
                                for (b, s), parts in sorted(pooled.items())
                                for t, dd in target_metrics(np.concatenate([q[0] for q in parts]),
                                                            np.concatenate([q[1] for q in parts])).items()
                                for k, v in dd.items()]
    counts = []
    for subject, rec in plan["subjects"].items():
        for b in budgets():
            pb = rec["budgets"][b]
            counts.append({"subject_id": subject, "fold": rec["fold"], "budget_nights": b,
                           "adaptation_nights": len(pb["adaptation_nights"]),
                           "adaptation_first": pb["adaptation_nights"][0] if pb["adaptation_nights"] else "",
                           "adaptation_last": pb["adaptation_nights"][-1] if pb["adaptation_nights"] else "",
                           "adaptation_windows": pb["adaptation_windows"],
                           "buffer_nights": ";".join(pb["buffer_nights"]), "buffer_windows": pb["buffer_windows"],
                           "primary_test_nights": rec["primary_test"]["n_nights"],
                           "primary_test_windows": pb["primary_test_windows"],
                           "later_test_nights": pb["later_test_nights"], "later_test_windows": pb["later_test_windows"],
                           "adaptation_lr": rec["adaptation"]["lr"], "base_lr": rec["adaptation"]["base_lr"]})
    tables["budget_counts"] = counts
    return tables


def run_index() -> list[dict]:
    rows = []
    for subject in sorted(subject_folds()):
        base = run_root() / subject
        for d in (sorted(base.glob("b*_seed*")) if base.exists() else []):
            st = _status(d)
            rows.append({"subject_id": subject, "run": d.name, "status": run_status(d), "attempt": st.get("attempt"),
                         "previous_attempts": len(st.get("history", [])), "run_id": st.get("run_id"),
                         "started_at": st.get("started_at"), "finished_at": st.get("finished_at")})
    return rows


def test_access_counts() -> dict[str, int]:
    p = run_root() / "test_access.jsonl"
    counts: dict[str, int] = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            key = f"{r['subject']}|b{r['budget']}|seed{r['seed']}"
            counts[key] = counts.get(key, 0) + 1
    return counts


def write_tables(tables: dict[str, list[dict]]) -> Path:
    out = metrics_dir()
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r))
        write_csv(out / f"p5_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    idx = run_index()
    write_csv(out / "p5_run_index.csv", idx, list(idx[0]))
    write_json(out / "p5_test_access_counts.json", test_access_counts())
    return out
