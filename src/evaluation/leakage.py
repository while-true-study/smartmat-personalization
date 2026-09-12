"""Leakage validation gate (RESEARCH_PROTOCOL L1–L12; docs/EXPERIMENT_PROTOCOL.md §12; D-042).

`run_gate` checks the frozen split files against their manifest and against the canonical session structure, and,
when a run context is given, the run's input schema, fitted-transform provenance, model-selection data and windows.
Every check fails closed: a check that raises is reported as failed. `require_pass` raises LeakageGateError on any
failure; every training entry point must call `gate_for_training` before it touches data (L12).
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from src.evaluation import splits as S
from src.features.pressure_features import ADMISSIBLE_FEATURES

TARGET_OR_CONTROL = ("temperature", "humidity", "temp", "humid", "target", "event", "control", "heater", "ahon",
                     "ahof", "bhsdown", "bcsup", "stemp", "slimit", "setpoint", "set_point", "movement_label",
                     "firmware")
CALENDAR_OR_ID = ("timestamp", "date", "month", "season", "hour", "day", "night", "week", "subject", "device",
                  "source", "session", "sensor_phase", "channel_quality", "file", "row_id")
EXCLUDED_SUBJECTS = ("User06",)
NON_PRIMARY_SUBJECTS = ("User03", "User06")


class LeakageGateError(RuntimeError):
    pass


@dataclass
class CheckResult:
    check: str
    rule: str
    passed: bool
    detail: str = ""


@dataclass
class GateReport:
    protocol_version: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)

    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        return {"protocol_version": self.protocol_version, "passed": self.passed,
                "n_checks": len(self.checks), "n_failed": len(self.failures()),
                "checks": [asdict(c) for c in self.checks]}


@dataclass
class RunContext:
    """What a training/evaluation run declares about itself (checked against the split).

    scheme: 'loso' or 'personalization'; fold: outer fold (int) for loso; subject/budget for personalization.
    input_features: model input names; fit_records: TargetScaler.fit_provenance dicts (and any other fitted
    transform); selection_subjects: subjects whose data were used for validation / early stopping / selection;
    window_groups: per window, the (partition, session_id, sensor_phase, channel_quality_phase[, night_id]) labels
    of its first and last step rows.
    """
    scheme: str
    fold: int | None = None
    subject: str | None = None
    budget: int | None = None
    input_features: list[str] = field(default_factory=list)
    fit_records: list[dict] = field(default_factory=list)
    selection_subjects: list[str] = field(default_factory=list)
    window_groups: list[tuple[tuple, tuple]] = field(default_factory=list)


def _run(report: GateReport, check: str, rule: str, fn: Callable[[], str | None]) -> None:
    try:
        problem = fn()
        report.checks.append(CheckResult(check, rule, problem is None, problem or "ok"))
    except Exception as exc:                                   # fail closed
        report.checks.append(CheckResult(check, rule, False, f"check raised {type(exc).__name__}: {exc}"))


# ----------------------------------------------------------------------------------------------- split-level checks

def check_manifest(split_dir: Path, manifest: dict) -> str | None:
    problems = []
    for rel in S.SPLIT_FILES:
        rec = manifest.get("files", {}).get(rel)
        p = split_dir / rel
        if rec is None or not p.exists():
            problems.append(f"{rel}: missing from manifest or disk")
            continue
        if S.file_sha256_lf(p) != rec["sha256"]:
            problems.append(f"{rel}: SHA-256 differs from the manifest (corrupted or edited split)")
    return "; ".join(problems) or None


def check_outer(outer: list[dict], folds: dict[int, str], cohort: list[str]) -> str | None:
    by_fold = defaultdict(list)
    for r in outer:
        by_fold[int(r["fold"])].append(r)
    if sorted(by_fold) != sorted(folds) or len(folds) != 3:
        return f"outer folds {sorted(by_fold)} != declared {sorted(folds)} (exactly 3 required)"
    sessions = None
    for f, rows in by_fold.items():
        held = folds[f]
        ids = [r["session_id"] for r in rows]
        if len(ids) != len(set(ids)):
            return f"fold {f}: a session is assigned twice"
        if sessions is None:
            sessions = set(ids)
        elif set(ids) != sessions:
            return f"fold {f}: session set differs between folds"
        for r in rows:
            want = "test" if r["subject_id"] == held else "train"
            if r["partition"] != want or r["held_out_subject"] != held:
                return f"fold {f}: {r['session_id']} is {r['partition']}, expected {want}"
        if {r["subject_id"] for r in rows if r["partition"] == "train"} & {held}:
            return f"fold {f}: held-out subject in training"
        if {r["subject_id"] for r in rows} != set(cohort):
            return f"fold {f}: subjects differ from the cohort"
    return None


def check_inner(inner: list[dict], folds: dict[int, str], cohort: list[str]) -> str | None:
    for f, held in folds.items():
        rows = [r for r in inner if int(r["fold"]) == f]
        if any(r["subject_id"] == held for r in rows):
            return f"fold {f}: held-out subject {held} appears in inner validation"
        splits = defaultdict(lambda: defaultdict(set))
        for r in rows:
            splits[r["inner_split"]][r["partition"]].add(r["subject_id"])
        if sorted(splits) != ["A", "B"]:
            return f"fold {f}: inner splits {sorted(splits)} != ['A', 'B']"
        remaining = {s for s in cohort if s != held}
        pairs = set()
        for name, parts in splits.items():
            tr, va = parts.get("inner_train", set()), parts.get("inner_val", set())
            if len(tr) != 1 or len(va) != 1 or tr & va or (tr | va) != remaining:
                return f"fold {f} inner {name}: train {sorted(tr)} / val {sorted(va)} is not a subject-level split"
            pairs.add((next(iter(tr)), next(iter(va))))
        if len(pairs) != 2:
            return f"fold {f}: inner A and B are not swapped"
    return None


def check_personalization(pers: list[dict], budgets: list[int], buffer_nights: int, primary_from: int) -> str | None:
    groups = defaultdict(list)
    for r in pers:
        groups[(r["subject_id"], int(r["budget_nights"]))].append(r)
    subjects = {s for s, _ in groups}
    for s in subjects:
        if sorted(b for ss, b in groups if ss == s) != sorted(budgets):
            return f"{s}: budgets differ from {budgets}"
    primary_sets = defaultdict(set)
    for (s, b), rows in groups.items():
        night_part = {}
        for r in rows:
            k, part = int(r["night_ordinal"]), r["partition"]
            if night_part.setdefault(r["night_id"], part) != part:
                return f"{s} b={b}: night {r['night_id']} split across partitions (devices or sessions)"
            want = "test" if b == 0 else ("adaptation" if k <= b else "buffer" if k <= b + buffer_nights else "test")
            if part != want:
                return f"{s} b={b}: night ordinal {k} is {part}, expected {want}"
            if int(r["primary_test"]) != int(k >= primary_from):
                return f"{s} b={b}: primary_test flag wrong at ordinal {k}"
            if int(r["primary_test"]):
                primary_sets[s].add((b, r["night_id"]))
        # chronology on real time spans: adaptation < buffer < test
        span = defaultdict(lambda: [None, None])
        for r in rows:
            lo, hi = span[r["partition"]]
            span[r["partition"]] = [min(lo or r["start_timestamp"], r["start_timestamp"]),
                                    max(hi or r["end_timestamp"], r["end_timestamp"])]
        order = [p for p in ("adaptation", "buffer", "test") if p in span]
        for a, c in zip(order, order[1:]):
            if not span[a][1] < span[c][0]:
                return f"{s} b={b}: {a} ends {span[a][1]} not before {c} starts {span[c][0]}"
        if b > 0:
            n_adapt = len({r["night_id"] for r in rows if r["partition"] == "adaptation"})
            n_buf = len({r["night_id"] for r in rows if r["partition"] == "buffer"})
            if n_adapt != b or n_buf != buffer_nights:
                return f"{s} b={b}: {n_adapt} adaptation / {n_buf} buffer nights"
    for s in subjects:
        per_budget = defaultdict(set)
        for b, n in primary_sets[s]:
            per_budget[b].add(n)
        if len({frozenset(v) for v in per_budget.values()}) != 1:
            return f"{s}: primary test nights differ between budgets"
    return None


def check_devices_together(outer: list[dict], pers: list[dict]) -> str | None:
    part = {}
    for r in outer:
        key = (r["fold"], r["subject_id"])
        if part.setdefault(key, r["partition"]) != r["partition"]:
            return f"fold {r['fold']}: devices/sessions of {r['subject_id']} in different partitions"
    part = {}
    for r in pers:
        key = (r["subject_id"], r["budget_nights"], r["night_id"])
        if part.setdefault(key, r["partition"]) != r["partition"]:
            return f"{r['subject_id']} b={r['budget_nights']} night {r['night_id']}: devices split across partitions"
    return None


def check_sources(records: list[dict], canonical_sessions: list[dict], cohort: list[str]) -> str | None:
    subjects = {r["subject_id"] for r in records}
    bad = subjects & set(NON_PRIMARY_SUBJECTS)
    if bad:
        return f"non-primary or excluded subjects in split: {sorted(bad)}"
    if not subjects <= set(cohort):
        return f"subjects outside the cohort: {sorted(subjects - set(cohort))}"
    canon = {r["session_id"]: r for r in canonical_sessions}
    for r in records:
        c = canon.get(r["session_id"])
        if c is None:
            return f"{r['session_id']} is not a canonical primary session (auxiliary/excluded/quarantined?)"
        for k in ("subject_id", "device_id", "sensor_phase", "channel_quality_phase"):
            if r[k] != c[k]:
                return f"{r['session_id']}: {k} {r[k]} != canonical {c[k]}"
    return None


def check_coverage(outer: list[dict], pers: list[dict], canonical_sessions: list[dict],
                   canonical_pieces: list[dict]) -> str | None:
    """Every canonical primary session is assigned (nothing silently dropped), with its exact span and rows."""
    want = {r["session_id"]: (S.fmt_ts(r["start"]), S.fmt_ts(r["end"]), str(r["n_rows"])) for r in canonical_sessions}
    got = {r["session_id"]: (r["start_timestamp"], r["end_timestamp"], str(r["n_rows"]))
           for r in outer if int(r["fold"]) == 1}
    if got != want:
        missing, extra = set(want) - set(got), set(got) - set(want)
        diff = [k for k in set(want) & set(got) if want[k] != got[k]]
        return f"LOSO sessions differ from canonical: missing {len(missing)}, extra {len(extra)}, span {len(diff)}"
    want_p = {(r["session_id"], r["night_id"]): (S.fmt_ts(r["start"]), S.fmt_ts(r["end"]), str(r["n_rows"]))
              for r in canonical_pieces}
    for b in {r["budget_nights"] for r in pers}:
        got_p = {(r["session_id"], r["night_id"]): (r["start_timestamp"], r["end_timestamp"], str(r["n_rows"]))
                 for r in pers if r["budget_nights"] == b}
        if got_p != want_p:
            return f"personalization pieces (budget {b}) differ from canonical session x night pieces"
    return None


# ------------------------------------------------------------------------------------------------- run-level checks

def check_inputs(features: list[str]) -> str | None:
    if not features:
        return "no input features declared"
    bad = [f for f in features if f not in ADMISSIBLE_FEATURES]
    named = [f for f in features if any(tok in f.lower() for tok in TARGET_OR_CONTROL)]
    if bad or named:
        return f"inadmissible inputs: {sorted(set(bad) | set(named))}"
    return None


def check_calendar(features: list[str]) -> str | None:
    named = [f for f in features if any(tok in f.lower() for tok in CALENDAR_OR_ID)]
    return f"calendar/identity inputs: {sorted(named)}" if named else None


def _training_scope(ctx: RunContext, outer: list[dict], pers: list[dict]) -> tuple[set, set]:
    """(allowed fit subjects, forbidden subjects) for the run's scheme."""
    if ctx.scheme == "loso":
        held = {r["held_out_subject"] for r in outer if int(r["fold"]) == ctx.fold}
        train = {r["subject_id"] for r in outer if int(r["fold"]) == ctx.fold and r["partition"] == "train"}
        return train, held
    if ctx.scheme == "personalization":
        others = {r["subject_id"] for r in pers} - {ctx.subject}
        return others, {ctx.subject}
    raise ValueError(f"unknown scheme {ctx.scheme}")


def check_fits(ctx: RunContext, outer: list[dict], pers: list[dict]) -> str | None:
    allowed, forbidden = _training_scope(ctx, outer, pers)
    for rec in ctx.fit_records:
        subj = set(rec.get("subjects") or [])
        if not subj:
            return f"fitted transform {rec.get('transform')} has no fit provenance"
        if subj & forbidden:
            return f"{rec.get('transform')} fitted with held-out/target subject data {sorted(subj & forbidden)} (L11)"
        if not subj <= allowed:
            return f"{rec.get('transform')} fitted on subjects outside the training partition: {sorted(subj - allowed)}"
        if rec.get("partition") not in ("train", "inner_train"):
            return f"{rec.get('transform')} fitted on partition {rec.get('partition')!r}"
    return None


def check_selection(ctx: RunContext, outer: list[dict], pers: list[dict]) -> str | None:
    allowed, forbidden = _training_scope(ctx, outer, pers)
    used = set(ctx.selection_subjects)
    if used & forbidden:
        return f"held-out/target subject used for validation or selection: {sorted(used & forbidden)}"
    if not used <= allowed:
        return f"selection used subjects outside the training pool: {sorted(used - allowed)}"
    return None


def check_window_groups(ctx: RunContext) -> str | None:
    for i, (first, last) in enumerate(ctx.window_groups):
        if tuple(first) != tuple(last):
            return f"window {i} crosses a partition/session/phase boundary: {first} -> {last}"
    return None


# ------------------------------------------------------------------------------------------------------------ gate

def check_canonical(manifest: dict, verified: dict | None) -> str | None:
    """The canonical data the splits were built from is the data present now (de-duplicated canonical_v1, L7)."""
    if verified is None:
        return "canonical_v1 was not verified"
    m = manifest.get("canonical", {})
    now = {"dataset_version": verified["dataset_version"],
           "primary_content_sha256": verified["content_sha256"]["primary"],
           "primary_file_sha256": verified["files"]["primary"]}
    diff = [k for k, v in now.items() if m.get(k) != v]
    return f"canonical data differ from the split manifest: {diff}" if diff else None


def check_protocol_file(manifest: dict) -> str | None:
    """The protocol parameters in force are the ones the splits were frozen with."""
    from src.evaluation.protocol import protocol_sha256

    if manifest.get("protocol_sha256") != protocol_sha256():
        return "configs/experiments/v1.0/protocol.yaml differs from the frozen protocol hash in the split manifest"
    return None


def run_gate(split_dir: Path, manifest: dict, protocol: dict, canonical_sessions: list[dict],
             canonical_pieces: list[dict], ctx: RunContext | None = None,
             canonical_verified: dict | None = None) -> GateReport:
    rep = GateReport(protocol.get("protocol_version", "?"))
    _run(rep, "canonical_matches_split_manifest", "L7", lambda: check_canonical(manifest, canonical_verified))
    folds = {int(k): v for k, v in protocol["loso"]["outer_folds"].items()}
    cohort = list(protocol["data"]["subjects"])
    pz = protocol["personalization"]
    loaded: dict[str, list[dict]] = {}

    def load() -> str | None:
        for rel in S.SPLIT_FILES:
            loaded[rel] = S.read_split(split_dir / rel)
        return None

    _run(rep, "split_files_match_manifest", "L1/L12", lambda: check_manifest(split_dir, manifest))
    _run(rep, "split_files_readable", "L1", load)
    outer, inner, pers = (loaded.get(S.LOSO_OUTER, []), loaded.get(S.LOSO_INNER, []),
                          loaded.get(S.PERSONALIZATION, []))
    _run(rep, "manifest_protocol_version", "L12",
         lambda: None if manifest.get("protocol_version") == rep.protocol_version else "manifest/protocol mismatch")
    _run(rep, "protocol_file_unchanged", "L12", lambda: check_protocol_file(manifest))
    _run(rep, "outer_loso_three_folds_disjoint", "L2/L4", lambda: check_outer(outer, folds, cohort))
    _run(rep, "inner_validation_subject_level", "L4", lambda: check_inner(inner, folds, cohort))
    _run(rep, "personalization_chronological", "L5",
         lambda: check_personalization(pers, pz["budgets_nights"], pz["buffer_nights"], pz["primary_test_from_ordinal"]))
    _run(rep, "concurrent_devices_same_partition", "L8", lambda: check_devices_together(outer, pers))
    _run(rep, "primary_sources_only", "L6", lambda: check_sources(outer + inner + pers, canonical_sessions, cohort))
    _run(rep, "complete_canonical_coverage", "L2/L7", lambda: check_coverage(outer, pers, canonical_sessions,
                                                                             canonical_pieces))
    if ctx is not None:
        _run(rep, "inputs_admissible", "L9", lambda: check_inputs(ctx.input_features))
        _run(rep, "no_calendar_or_identity_inputs", "L10", lambda: check_calendar(ctx.input_features))
        _run(rep, "fits_training_partition_only", "L3/L11", lambda: check_fits(ctx, outer, pers))
        _run(rep, "selection_excludes_held_out", "L4", lambda: check_selection(ctx, outer, pers))
        _run(rep, "windows_inside_partitions", "L1", lambda: check_window_groups(ctx))
    return rep


def require_pass(report: GateReport) -> GateReport:
    if not report.passed:
        lines = "; ".join(f"{c.check} ({c.rule}): {c.detail}" for c in report.failures()) or "no checks ran"
        raise LeakageGateError(f"leakage gate failed — training must not start: {lines}")
    return report


def gate_for_training(ctx: RunContext, split_dir: Path | None = None) -> GateReport:
    """Entry point for P3+ runners: loads the frozen protocol, manifest and canonical structure, runs every check
    including the run context, and raises LeakageGateError on any failure (L12)."""
    from src.evaluation.canonical_input import verify_canonical
    from src.evaluation.p2_protocol import canonical_structure, load_manifest, split_root
    from src.evaluation.protocol import load_protocol

    split_dir = split_root() if split_dir is None else split_dir
    verified = verify_canonical()
    sessions, pieces = canonical_structure()
    rep = run_gate(split_dir, load_manifest(split_dir), load_protocol(), sessions, pieces, ctx, verified)
    return require_pass(rep)


def report_json(report: GateReport) -> str:
    return json.dumps(report.to_dict(), indent=2)
