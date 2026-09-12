"""P2 protocol freeze: split build, split manifest and structural feasibility statistics.

Reads canonical_v1 primary rows only (src/evaluation/canonical_input.py). Uses identity, phase, session and timestamp
labels plus the target-validity and pressure-validity flags. No target value is summarised and no model, prediction,
loss or error metric exists here (P2 rule: decide first, then train).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pyarrow as pa

from src.data import paths
from src.evaluation import splits as S
from src.evaluation.canonical_input import load_primary
from src.evaluation.domain_shift import assign_slices
from src.evaluation.protocol import PROTOCOL_PATH, cohort, load_protocol, night_id, outer_folds, protocol_sha256
from src.evaluation.windowing import WindowSpec, build_windows, continuity_segments, group_key, labelled

STRUCTURE_COLUMNS = ["subject_id", "device_id", "session_id", "sensor_phase", "channel_quality_phase", "timestamp"]
FLAG_COLUMNS = ["target_temp_valid", "target_humidity_valid", "pressure_valid"]
GENERATOR_FILES = ("scripts/build_p2_splits.py", "src/evaluation/splits.py", "src/evaluation/p2_protocol.py",
                   "src/evaluation/protocol.py", str(PROTOCOL_PATH).replace("\\", "/"))


def split_root() -> Path:
    return paths.PROJECT_ROOT / load_protocol()["artifacts"]["split_dir"]


def manifest_path(split_dir: Path | None = None) -> Path:
    split_dir = split_root() if split_dir is None else split_dir
    return split_dir / Path(load_protocol()["artifacts"]["manifest"]).name


def load_manifest(split_dir: Path | None = None) -> dict:
    return json.loads(manifest_path(split_dir).read_text(encoding="utf-8"))


class Structure:
    """Label arrays of the primary rows (canonical order)."""

    def __init__(self, t: pa.Table):
        s = lambda c: t[c].cast(pa.string()).to_numpy(zero_copy_only=False).astype(str)  # noqa: E731
        self.subject, self.device, self.session = s("subject_id"), s("device_id"), s("session_id")
        self.sensor_phase, self.cq_phase = s("sensor_phase"), s("channel_quality_phase")
        self.ts = t["timestamp"].cast(pa.timestamp("s")).cast(pa.int64()).to_numpy()
        self.night = night_id(self.ts)
        names = set(t.column_names)
        self.temp_ok = t["target_temp_valid"].to_numpy(zero_copy_only=False) if "target_temp_valid" in names else None
        self.humid_ok = (t["target_humidity_valid"].to_numpy(zero_copy_only=False)
                         if "target_humidity_valid" in names else None)
        self.pressure_ok = t["pressure_valid"].to_numpy(zero_copy_only=False) if "pressure_valid" in names else None

    def sessions(self) -> list[dict]:
        return S.session_records(self.ts, self.subject, self.device, self.session, self.sensor_phase, self.cq_phase)

    def pieces(self) -> list[dict]:
        return S.piece_records(self.ts, self.subject, self.device, self.session, self.sensor_phase, self.cq_phase,
                               self.night)


def load_structure(with_flags: bool = False) -> Structure:
    return Structure(load_primary(STRUCTURE_COLUMNS + (FLAG_COLUMNS if with_flags else [])))


def canonical_structure() -> tuple[list[dict], list[dict]]:
    st = load_structure()
    return st.sessions(), st.pieces()


def build_split_tables(sessions: list[dict], pieces: list[dict]) -> dict[str, tuple[list[dict], list[str]]]:
    cfg = load_protocol()
    v, pz = cfg["protocol_version"], cfg["personalization"]
    return {
        S.LOSO_OUTER: (S.loso_outer(sessions, outer_folds(), cohort(), v), S.OUTER_COLUMNS),
        S.LOSO_INNER: (S.loso_inner(sessions, outer_folds(), cohort(), v), S.INNER_COLUMNS),
        S.PERSONALIZATION: (S.personalization(pieces, pz["budgets_nights"], pz["buffer_nights"],
                                              pz["primary_test_from_ordinal"], v), S.PERS_COLUMNS),
    }


def scheme_summary(tables: dict, pieces: list[dict]) -> dict:
    cfg = load_protocol()
    nights = {s: len({p["night_id"] for p in pieces if p["subject_id"] == s}) for s in cohort()}
    sess = {s: len({r["session_id"] for r in tables[S.LOSO_OUTER][0] if r["subject_id"] == s}) for s in cohort()}
    pz = cfg["personalization"]
    return {
        "loso": {"split_id": cfg["loso"]["split_id"], "outer_folds": {str(k): v for k, v in outer_folds().items()},
                 "inner": cfg["loso"]["inner"], "sessions_per_subject": sess},
        "personalization": {"split_id": pz["split_id"], "unit": pz["unit"], "budgets_nights": pz["budgets_nights"],
                            "buffer_nights": pz["buffer_nights"],
                            "primary_test_from_ordinal": pz["primary_test_from_ordinal"],
                            "nights_per_subject": nights,
                            "primary_test_nights_per_subject": {s: n - pz["primary_test_from_ordinal"] + 1
                                                                for s, n in nights.items()},
                            "night_definition": "date(timestamp - 12 h), naive local time (local_unspecified)"},
    }


def make_manifest(file_hashes: dict[str, dict], canonical: dict, summary: dict, build: dict) -> dict:
    gen = {}
    for rel in GENERATOR_FILES:
        p = paths.PROJECT_ROOT / rel
        gen[rel] = S.file_sha256_lf(p) if p.exists() else None
    return {
        "protocol_version": load_protocol()["protocol_version"],
        "protocol_file": str(PROTOCOL_PATH).replace("\\", "/"),
        "protocol_sha256": protocol_sha256(),
        "hash_rule": "SHA-256 of the file bytes with CRLF normalised to LF",
        "canonical": {"dataset_version": canonical["dataset_version"],
                      "schema_version": canonical["schema_version"],
                      "primary_content_sha256": canonical["content_sha256"]["primary"],
                      "primary_file_sha256": canonical["files"]["primary"],
                      "config_hash_sha256": canonical["config_hash_sha256"],
                      "raw_manifest_sha256": canonical["raw_manifest_sha256"]},
        "files": file_hashes,
        "schemes": summary,
        "generator": gen,
        "build": build,
    }


def semantic(manifest: dict) -> dict:
    """Manifest content that must be identical when the splits are rebuilt from the same canonical_v1."""
    return {k: v for k, v in manifest.items() if k not in ("build", "generator")}


# ------------------------------------------------------------------------------------ structural feasibility audit

def _segment_spans(ts: np.ndarray, group: np.ndarray, max_gap_s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    seg = continuity_segments(ts, group, max_gap_s)
    n = int(seg[-1]) + 1
    first = np.searchsorted(seg, np.arange(n), side="left")
    last = np.searchsorted(seg, np.arange(n), side="right") - 1
    return seg, first, last


def window_feasibility(st: Structure, spec: WindowSpec) -> list[dict]:
    """Per P1 domain slice: coverage kept by the continuity rule and the three candidate representations.

    A = 1-s grid (a fixed shape needs fill or mask for seconds without a row), B = a fixed number of consecutive rows
    (elapsed time varies), C = time bins with the last observation per bin (the v1.0 rule). Only timestamps and
    validity flags are used.
    """
    sl = assign_slices(st.subject, st.device, st.sensor_phase, st.cq_phase)
    group = group_key(st.subject, st.device, st.session, st.sensor_phase, st.cq_phase)
    seg, first, last = _segment_spans(st.ts, group, spec.max_gap_s)
    span = st.ts[last] - st.ts[first]
    w = build_windows(st.ts, group, spec)
    lab = labelled(w, st.temp_ok, st.humid_ok)
    base = np.int64(1) << 34
    key = seg * base + st.ts
    a = np.searchsorted(key, w.segment * base + w.t0, side="left")
    b = np.searchsorted(key, w.segment * base + w.t0 + spec.duration_s, side="left") - 1
    new_sec = np.r_[1, (np.diff(st.ts) != 0) | (seg[1:] != seg[:-1])].astype(np.int64)
    cs = np.cumsum(new_sec)
    distinct_s = cs[b] - cs[a] + 1
    rows_per_window = b - a + 1
    elapsed_c = st.ts[w.step_rows[:, -1]] - st.ts[w.step_rows[:, 0]]
    n_b = spec.duration_s // 3 + 1                                           # rows per 40 s at 3-s nominal sampling
    i = np.arange(st.ts.size - (n_b - 1))
    same = seg[i] == seg[i + n_b - 1]
    elapsed_b, start_b = (st.ts[i + n_b - 1] - st.ts[i])[same], i[same]
    gaps = (np.diff(st.ts) > spec.max_gap_s) & (group[1:] == group[:-1])
    q = lambda x: [int(v) for v in np.percentile(x, [5, 50, 95])] if x.size else None  # noqa: E731
    sess_span = {r["session_id"]: (r["end"] - r["start"]) / 3600 for r in st.sessions()}
    out = []
    for name in sorted(set(sl) - {""}):
        m = sl == name
        seg_m = np.unique(seg[m])
        s_first = {sid: sess_span[sid] for sid in np.unique(st.session[m])}
        sess_hours = float(sum(s_first.values()))
        keep = seg_m[span[seg_m] >= spec.min_span_s]
        wm = m[w.target_row]
        bm = m[start_b]
        out.append({
            "slice": name, "rows": int(m.sum()), "sessions": len(s_first), "segments": int(seg_m.size),
            "inter_row_gaps_gt_max_gap": int((gaps & m[1:]).sum()),
            "session_hours": round(sess_hours, 2),
            "gap_free_hours": round(span[seg_m].sum() / 3600, 2),
            "windowable_hours": round(span[keep].sum() / 3600, 2),
            "windowable_share": round(span[keep].sum() / 3600 / sess_hours, 4),
            "C_windows": int(wm.sum()), "C_labelled_windows": int(lab[wm].sum()),
            "C_labelled_share": round(float(lab[wm].mean()), 5) if wm.any() else None,
            "C_rows_per_window_p05_p50_p95": q(rows_per_window[wm]),
            "C_elapsed_first_to_last_step_s_p05_p50_p95": q(elapsed_c[wm]),
            "A_empty_1s_cells_share": round(float(1 - distinct_s[wm].mean() / spec.duration_s), 4) if wm.any() else None,
            "B_rows": n_b,
            "B_elapsed_s_p05_p50_p95": q(elapsed_b[bm]),
        })
    return out


def partition_windows(st: Structure, tables: dict, spec: WindowSpec) -> list[dict]:
    """Structural window counts per split partition, built inside the partitions (L1). No target value is used.

    LOSO partitions are whole subjects, so a subject's windows are the same in every fold. Personalization windows
    are additionally cut at night and partition boundaries. Every window is validated (windowing.validate_windows).
    """
    out = []
    group = group_key(st.subject, st.device, st.session, st.sensor_phase, st.cq_phase)
    w = build_windows(st.ts, group, spec)
    lab_all = labelled(w, st.temp_ok, st.humid_ok)
    for fold_row in {(int(r["fold"]), r["held_out_subject"]) for r in tables[S.LOSO_OUTER][0]}:
        fold, held = fold_row
        for part, subj_mask in (("train", st.subject != held), ("test", st.subject == held)):
            sel = subj_mask[w.target_row]
            out.append({"scheme": "loso_outer", "fold": fold, "held_out_subject": held, "subject_id": "",
                        "budget_nights": "", "partition": part, "windows": int(sel.sum()),
                        "labelled_windows": int(lab_all[sel].sum())})
    for r in sorted({(int(r["fold"]), r["inner_split"], r["subject_id"], r["partition"])
                     for r in tables[S.LOSO_INNER][0]}):
        fold, inner, subj, part = r
        sel = (st.subject == subj)[w.target_row]
        out.append({"scheme": f"loso_inner_{inner}", "fold": fold, "held_out_subject": "", "subject_id": subj,
                    "budget_nights": "", "partition": part, "windows": int(sel.sum()),
                    "labelled_windows": int(lab_all[sel].sum())})
    pers = tables[S.PERSONALIZATION][0]
    for subj in cohort():
        m_subj = st.subject == subj
        idx = np.flatnonzero(m_subj)
        nights = st.night[idx]
        for b in sorted({int(r["budget_nights"]) for r in pers}):
            part_of = {r["night_id"]: r["partition"] for r in pers
                       if r["subject_id"] == subj and int(r["budget_nights"]) == b}
            prim = {r["night_id"] for r in pers if r["subject_id"] == subj and int(r["budget_nights"]) == b
                    and int(r["primary_test"])}
            part = np.array([part_of[n] for n in np.unique(nights)])[np.unique(nights, return_inverse=True)[1]]
            g = group_key(st.device[idx], st.session[idx], st.sensor_phase[idx], st.cq_phase[idx], nights, part)
            wp = build_windows(st.ts[idx], g, spec)
            lab = labelled(wp, st.temp_ok[idx], st.humid_ok[idx])
            wpart = part[wp.target_row]
            wprim = np.isin(nights[wp.target_row], list(prim))
            for p in ("adaptation", "buffer", "test"):
                sel = wpart == p
                if p == "test":
                    for flag, s2 in (("test_primary", sel & wprim), ("test_all_later", sel)):
                        out.append({"scheme": "personalization", "fold": "", "held_out_subject": "",
                                    "subject_id": subj, "budget_nights": b, "partition": flag,
                                    "windows": int(s2.sum()), "labelled_windows": int(lab[s2].sum())})
                elif sel.any() or b > 0:
                    out.append({"scheme": "personalization", "fold": "", "held_out_subject": "",
                                "subject_id": subj, "budget_nights": b, "partition": p,
                                "windows": int(sel.sum()), "labelled_windows": int(lab[sel].sum())})
    return sorted(out, key=lambda r: (r["scheme"], str(r["fold"]), r["subject_id"], str(r["budget_nights"]),
                                      r["partition"]))
