"""Reproduction of the frozen P3–P6 results from public_release_v1 alone (D-050).

`public_mode` re-points the unchanged P3/P4/P5/P6 code at a release:
- data come from `PublicRelease` (windows.parquet + public split copies); canonical_v1, raw data and the private
  split files are not read (the private loaders raise while public mode is active);
- every run and table goes under one output root laid out like the repository (`outputs/runs/…`,
  `outputs/metrics/…`, `paper/tables/…`);
- every run passes a public leakage gate: the P2 split-level and run-level checks on the public split copies, with
  the release manifest in place of the canonical-data checks.
Nothing is selected or tuned: the committed P3/P4 selections and the public copy of the frozen P5 plan are used.

`compare_table` checks a reproduced table against its committed version cell by cell. A cell may differ only where
a committed calendar night id (YYYY-MM-DD) meets its public key (D####); the whole-day shift must then be the same
for every night of the subject, in every table (D-049).
"""
from __future__ import annotations

import csv
import io
import json
import re
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import numpy as np

from src.data import public_release as R
from src.data.io_guard import write_json
from src.evaluation import leakage as L
from src.evaluation import p3_loso as P3
from src.evaluation import p4_ablation as P4
from src.evaluation import p5_personalization as P5
from src.evaluation import p6_robustness as P6
from src.evaluation.protocol import PROTOCOL_VERSION, load_protocol, protocol_sha256

_ACTIVE: dict = {}


class PublicModeError(RuntimeError):
    pass


def _private_access(*_a, **_k):
    raise PublicModeError("private data (canonical_v1, raw data or private split files) are not read in public mode")


# ------------------------------------------------------------------------------------------------------ identity

def public_manifest(release: R.PublicRelease | None = None) -> dict:
    """Stand-in for the P2 split manifest: the frozen split hashes the release was built from (D-050)."""
    man = (release or _ACTIVE["release"]).manifest
    return {"protocol_version": man["protocol_version"], "protocol_sha256": man["protocol_sha256"],
            "files": {rel: {"sha256": sha} for rel, sha in man["split_sha256"].items()}}


def release_identity(release: R.PublicRelease | None = None) -> dict:
    rel = release or _ACTIVE["release"]
    man = rel.manifest
    return {"data_source": man["release_version"], "release_manifest_sha256": R.sha256_file(rel.root / "manifest.json"),
            "release_windows_sha256": man["artifacts_sha256"]["windows.parquet"],
            "source_primary_content_sha256": man.get("source_dataset", {}).get("primary_content_sha256")}


def frozen_inputs_public(verified: dict | None = None) -> dict:
    """Public replacement of `p3_loso.frozen_inputs` (recorded in every run_meta.json)."""
    man = _ACTIVE["release"].manifest
    return {"protocol_version": PROTOCOL_VERSION, "protocol_sha256": protocol_sha256(),
            "split_sha256": dict(man["split_sha256"]), "split_manifest_protocol_sha256": man["protocol_sha256"],
            **(verified or release_identity())}


def plan_yaml_public() -> Path:
    return _ACTIVE["release"].root / "p5_plan_public.yaml"


def plan_commit_public() -> str:
    """Public replacement of `p5_personalization.plan_commit`: the plan must be the one the release manifest lists."""
    rel = _ACTIVE["release"]
    sha = R.sha256_file(plan_yaml_public())
    if sha != rel.manifest["artifacts_sha256"]["p5_plan_public.yaml"]:
        raise P5.PlanNotFrozenError("p5_plan_public.yaml differs from the release manifest")
    return f"{rel.manifest['release_version']}:p5_plan_public.yaml:{sha}"


def heater_events_public(subject: str = "User02") -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Public replacement of `p6_robustness.heater_events`: the release's control_events.csv (relative seconds)."""
    from src.evaluation import splits as S
    ev = [r for r in S.read_split(_ACTIVE["release"].root / "control_events.csv") if r["subject_id"] == subject]
    out = {}
    for d in sorted({r["device_id"] for r in ev}):
        rows = sorted((int(r["time_s"]), r["code"]) for r in ev if r["device_id"] == d)
        out[d] = (np.array([r[0] for r in rows], np.int64), np.array([r[1] for r in rows], dtype=object))
    return out


# ---------------------------------------------------------------------------------------------------------- gate

def check_release_files(release: R.PublicRelease) -> str | None:
    bad = [a for a, h in release.manifest["artifacts_sha256"].items() if R.sha256_file(release.root / a) != h]
    return f"release files differ from manifest.json: {bad}" if bad else None


def session_attributes(w: R.ReleaseArrays) -> dict[str, tuple[str, str, str, str]]:
    """session_id -> (subject, device, sensor_phase, channel_quality_phase) from the windows (one value each)."""
    keys = np.stack([w.session, w.subject, w.device, w.sensor_phase, w.cq_phase], axis=1)
    uniq = np.unique(keys, axis=0)
    out = {}
    for s, *attrs in uniq.tolist():
        if s in out:
            raise PublicModeError(f"session {s} has several subject/device/phase values in the windows")
        out[s] = tuple(attrs)
    return out


def check_public_sources(records: list[dict], attrs: dict, cohort: list[str]) -> str | None:
    """L6 on the public split: primary cohort only; split attributes agree with the windows of each session."""
    subjects = {r["subject_id"] for r in records}
    if subjects & set(L.NON_PRIMARY_SUBJECTS):
        return f"non-primary or excluded subjects in split: {sorted(subjects & set(L.NON_PRIMARY_SUBJECTS))}"
    if not subjects <= set(cohort):
        return f"subjects outside the cohort: {sorted(subjects - set(cohort))}"
    for r in records:
        a = attrs.get(r["session_id"])
        if a is not None and a != (r["subject_id"], r["device_id"], r["sensor_phase"], r["channel_quality_phase"]):
            return f"{r['session_id']}: split attributes differ from its windows"
    return None


def check_window_coverage(w: R.ReleaseArrays, outer: list[dict], pers: list[dict], manifest: dict) -> str | None:
    """L2/L7 on the public side: every window lies in an assigned session (LOSO) or session x night piece (RQ2), and
    the build-time private/public equivalence gate passed."""
    loso = {r["session_id"] for r in outer if int(r["fold"]) == 1}
    miss = set(w.session[w.in_loso].tolist()) - loso
    if miss:
        return f"{len(miss)} LOSO window sessions are not in the outer split"
    pieces = {(r["session_id"], r["night_id"]) for r in pers if int(r["budget_nights"]) == 0}
    got = set(zip(w.session[w.in_rq2].tolist(), w.night[w.in_rq2].tolist()))
    if got - pieces:
        return f"{len(got - pieces)} RQ2 window pieces are not in the personalization split"
    if not manifest.get("equivalence", {}).get("passed"):
        return "the release manifest does not record a passed private/public equivalence gate"
    return None


def public_gate(release: R.PublicRelease, attrs: dict, ctx: L.RunContext | None = None) -> L.GateReport:
    """The P2 gate on a public release (same split-level and run-level rules; release manifest instead of canonical
    data). Windows never cross a partition, session, phase or night by construction: the build-time equivalence gate
    proved the release windows are the private windows, which passed L1."""
    protocol = load_protocol()
    rep = L.GateReport(protocol.get("protocol_version", "?"))
    man = release.manifest
    folds = {int(k): v for k, v in protocol["loso"]["outer_folds"].items()}
    cohort = list(protocol["data"]["subjects"])
    pz = protocol["personalization"]
    loaded: dict[str, list[dict]] = {}

    def load() -> str | None:
        for rel in R.SPLIT_RELS:
            loaded[rel] = release.split(rel)
        return None

    L._run(rep, "release_files_match_manifest", "L7/L12", lambda: check_release_files(release))
    L._run(rep, "split_files_readable", "L1", load)
    outer, inner, pers = (loaded.get(R.SPLIT_RELS[0], []), loaded.get(R.SPLIT_RELS[1], []),
                          loaded.get(R.SPLIT_RELS[2], []))
    L._run(rep, "manifest_protocol_version", "L12",
           lambda: None if man.get("protocol_version") == rep.protocol_version else "manifest/protocol mismatch")
    L._run(rep, "protocol_file_unchanged", "L12",
           lambda: None if man.get("protocol_sha256") == protocol_sha256() else "protocol.yaml differs from the "
                                                                                 "release manifest")
    L._run(rep, "outer_loso_three_folds_disjoint", "L2/L4", lambda: L.check_outer(outer, folds, cohort))
    L._run(rep, "inner_validation_subject_level", "L4", lambda: L.check_inner(inner, folds, cohort))
    L._run(rep, "personalization_chronological", "L5",
           lambda: L.check_personalization(pers, pz["budgets_nights"], pz["buffer_nights"],
                                           pz["primary_test_from_ordinal"]))
    L._run(rep, "concurrent_devices_same_partition", "L8", lambda: L.check_devices_together(outer, pers))
    L._run(rep, "primary_sources_only", "L6", lambda: check_public_sources(outer + inner + pers, attrs, cohort))
    L._run(rep, "complete_window_coverage", "L2/L7", lambda: check_window_coverage(release.w, outer, pers, man))
    if ctx is not None:
        L._run(rep, "inputs_admissible", "L9", lambda: L.check_inputs(ctx.input_features))
        L._run(rep, "no_calendar_or_identity_inputs", "L10", lambda: L.check_calendar(ctx.input_features))
        L._run(rep, "fits_training_partition_only", "L3/L11", lambda: L.check_fits(ctx, outer, pers))
        L._run(rep, "selection_excludes_held_out", "L4", lambda: L.check_selection(ctx, outer, pers))
        L._run(rep, "windows_inside_partitions", "L1", lambda: L.check_window_groups(ctx))
    return rep


# ------------------------------------------------------------------------------------------------------ session

class PublicSession(P5.P5Session):
    """P5Session (and P3Session) on a public release: fold and subject windows from the release, public gate."""

    def __init__(self, echo: bool = True, release: R.PublicRelease | None = None):
        super().__init__(echo)
        self.release = release or _ACTIVE["release"]
        self._attrs = None

    def rows(self):
        raise PublicModeError("canonical rows are not available from a public release")

    def fold(self, fold: int):
        if fold not in self._folds:
            self._folds[fold] = self.release.fold_data(fold)
        return self._folds[fold]

    def pers(self) -> list[dict]:
        return self.release.pers()

    def windows(self, subject: str, budget: int):
        if (subject, budget) not in self._sw:
            self._sw[(subject, budget)] = self.release.subject_windows(subject, budget)
        return self._sw[(subject, budget)]

    def gate(self, d: Path, ctx: L.RunContext) -> tuple[L.GateReport, dict]:
        if self._attrs is None:
            self._attrs = session_attributes(self.release.w)
        rep = public_gate(self.release, self._attrs, ctx)
        ident = release_identity(self.release)
        write_json(d / "leakage_check.json", {"checked_at": P3.now(), "mode": "public_release", **ident, "context": {
            "scheme": ctx.scheme, "fold": ctx.fold, "subject": ctx.subject, "budget": ctx.budget,
            "input_features": ctx.input_features, "fit_records": ctx.fit_records,
            "selection_subjects": ctx.selection_subjects, "n_window_group_pairs": len(ctx.window_groups)},
            **rep.to_dict()})
        L.require_pass(rep)
        return rep, ident


# --------------------------------------------------------------------------------------------------- public mode

@contextmanager
def public_mode(release: R.PublicRelease, out_root: Path):
    """Re-point P3/P4/P5/P6 at the release and at out_root for the duration of the block (restored afterwards)."""
    from src.evaluation import canonical_input, p2_protocol
    from src.training import loso_data
    out_root = Path(out_root)
    runs, metrics = out_root / "outputs" / "runs", out_root / "outputs" / "metrics"
    patches = [
        (P3, "run_root", lambda: runs / "p3"), (P3, "metrics_dir", lambda: metrics / "p3"),
        (P3, "frozen_inputs", frozen_inputs_public), (P3, "verify_canonical", _private_access),
        (P3, "load_manifest", public_manifest), (P3, "split_root", _private_access),
        (P4, "run_root", lambda: runs / "p4"), (P4, "metrics_dir", lambda: metrics / "p4"),
        (P4, "frozen_inputs", frozen_inputs_public), (P4, "load_manifest", public_manifest),
        (P5, "run_root", lambda: runs / "p5"), (P5, "metrics_dir", lambda: metrics / "p5"),
        (P5, "frozen_inputs", frozen_inputs_public), (P5, "load_manifest", public_manifest),
        (P5, "split_root", lambda: release.split_dir()), (P5, "plan_yaml", plan_yaml_public),
        (P5, "plan_commit", plan_commit_public), (P5, "P5Session", PublicSession),
        (P6, "tables_dir", lambda: out_root / "paper" / "tables"), (P6, "metrics_dir", lambda: metrics / "p6"),
        (P6, "heater_events", heater_events_public),
        (canonical_input, "verify_canonical", _private_access), (canonical_input, "load_primary", _private_access),
        (p2_protocol, "split_root", _private_access), (p2_protocol, "load_manifest", _private_access),
        (loso_data, "load_primary", _private_access), (loso_data, "split_root", _private_access),
    ]
    saved = [(m, n, getattr(m, n)) for m, n, _ in patches]
    prev = dict(_ACTIVE)
    _ACTIVE.update(release=release, out_root=out_root)
    try:
        for m, n, v in patches:
            setattr(m, n, v)
        yield
    finally:
        for m, n, v in saved:
            setattr(m, n, v)
        _ACTIVE.clear()
        _ACTIVE.update(prev)


# ---------------------------------------------------------------------------------------------------- comparison

NIGHT_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
NIGHT_KEY = re.compile(r"D\d{4}")


def night_shift(committed: str, public: str) -> int | None:
    """Whole-day shift between a committed night id (YYYY-MM-DD) and a public night key (D####), else None."""
    if NIGHT_DATE.fullmatch(committed) and NIGHT_KEY.fullmatch(public):
        return date.fromisoformat(committed).toordinal() - int(public[1:])
    return None


def _rows(p: Path) -> tuple[bytes, list[list[str]]]:
    raw = p.read_bytes().replace(b"\r\n", b"\n")
    return raw, list(csv.reader(io.StringIO(raw.decode("utf-8"))))


def _night_cells_equal(u: str, v: str, key: str, shifts: dict[str, int]) -> bool:
    """u and v hold the same nights (';'-separated lists allowed) under the subject's single whole-day shift."""
    pu, pv = u.split(";"), v.split(";")
    if len(pu) != len(pv):
        return False
    for cu, cv in zip(pu, pv):
        if cu != cv:
            s = night_shift(cu, cv)
            if s is None or shifts.setdefault(key, s) != s:
                return False
    return True


def compare_table(committed: Path, reproduced: Path, shifts: dict[str, int], max_report: int = 5) -> dict:
    """Committed vs reproduced CSV: equal cell by cell, except committed night dates against public night keys with
    one whole-day shift per subject (shared across tables through `shifts`). Line endings are normalised."""
    out = {"table": committed.name, "identical_bytes": False, "rows": 0, "night_key_cells": 0,
           "mismatched_cells": 0, "problems": []}
    if not reproduced.exists():
        out.update(passed=False, problems=["reproduced table missing"])
        return out
    ra, a = _rows(committed)
    rb, b = _rows(reproduced)
    out["rows"] = max(len(a) - 1, 0)
    if ra == rb:
        out.update(identical_bytes=True, passed=True)
        return out
    if not a or not b or a[0] != b[0]:
        out["problems"].append("header differs")
    elif len(a) != len(b):
        out["problems"].append(f"{len(a) - 1} committed rows vs {len(b) - 1} reproduced rows")
    else:
        subj = a[0].index("subject_id") if "subject_id" in a[0] else None
        for i, (x, y) in enumerate(zip(a[1:], b[1:]), 1):
            if len(x) != len(y):
                out["mismatched_cells"] += 1
                out["problems"].append(f"row {i}: {len(x)} vs {len(y)} cells")
                continue
            key = x[subj] if subj is not None else "*"
            for j, (u, v) in enumerate(zip(x, y)):
                if u == v:
                    continue
                if _night_cells_equal(u, v, key, shifts):
                    out["night_key_cells"] += 1
                    continue
                out["mismatched_cells"] += 1
                if len(out["problems"]) < max_report:
                    out["problems"].append(f"row {i} column {a[0][j]}: committed {u!r} vs reproduced {v!r}")
    out["passed"] = not out["problems"]
    return out


def compare_digest(name: str, reference: dict, got: dict) -> dict:
    same = reference == got
    return {"check": f"predictions_bitwise:{name}", "passed": same,
            "detail": "y_true and y_pred SHA-256 identical" if same else f"reference {reference} vs {got}"}


def read_json(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))
