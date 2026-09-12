"""Protocol v1.0 split construction (docs/EXPERIMENT_PROTOCOL.md §3–§5, §10; D-030, D-031, D-037, D-042).

Splits are built from canonical_v1 session/night structure only (timestamps, identity and phase labels). No
target value, pressure value or model output is read. Split records are group assignments (session or
session-night pieces with their time span), not row lists; windows are generated later inside each partition (L1).
"""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

import numpy as np

from src.data.io_guard import write_text

LOSO_OUTER = "v1.0_loso/outer_folds.csv"
LOSO_INNER = "v1.0_loso/inner_folds.csv"
PERSONALIZATION = "v1.0_personalization/chronological.csv"
SPLIT_FILES = (LOSO_OUTER, LOSO_INNER, PERSONALIZATION)

GROUP_COLUMNS = ["subject_id", "device_id", "session_id", "sensor_phase", "channel_quality_phase",
                 "start_timestamp", "end_timestamp", "n_rows"]
OUTER_COLUMNS = ["protocol_version", "split_id", "fold", "held_out_subject", *GROUP_COLUMNS[:5], "partition",
                 *GROUP_COLUMNS[5:]]
INNER_COLUMNS = ["protocol_version", "split_id", "fold", "held_out_subject", "inner_split", *GROUP_COLUMNS[:5],
                 "partition", *GROUP_COLUMNS[5:]]
PERS_COLUMNS = ["protocol_version", "split_id", "subject_id", "budget_nights", "night_id", "night_ordinal",
                "device_id", "session_id", "sensor_phase", "channel_quality_phase", "partition", "primary_test",
                "start_timestamp", "end_timestamp", "n_rows"]


class SplitError(ValueError):
    pass


def fmt_ts(sec: int) -> str:
    return str(np.datetime64(int(sec), "s")).replace("T", " ")


def group_spans(ts: np.ndarray, labels: dict[str, np.ndarray]) -> list[dict]:
    """One record per distinct label combination: first/last timestamp and row count, sorted deterministically."""
    ts = np.asarray(ts, np.int64)
    names = list(labels)
    stacked = np.stack([np.asarray(labels[n]).astype(str) for n in names], axis=1)
    uniq, inv = np.unique(stacked, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    lo = np.full(len(uniq), np.iinfo(np.int64).max)
    hi = np.full(len(uniq), np.iinfo(np.int64).min)
    np.minimum.at(lo, inv, ts)
    np.maximum.at(hi, inv, ts)
    n = np.bincount(inv, minlength=len(uniq))
    recs = [dict(zip(names, u), start=int(a), end=int(b), n_rows=int(c)) for u, a, b, c in zip(uniq, lo, hi, n)]
    return sorted(recs, key=lambda r: (r["subject_id"], r["start"], r["device_id"], r["session_id"]))


def session_records(ts, subject, device, session, sensor_phase, cq_phase) -> list[dict]:
    recs = group_spans(ts, {"subject_id": subject, "device_id": device, "session_id": session,
                            "sensor_phase": sensor_phase, "channel_quality_phase": cq_phase})
    ids = [r["session_id"] for r in recs]
    if len(ids) != len(set(ids)):
        raise SplitError("a session spans several subjects, devices or phases")
    return recs


def piece_records(ts, subject, device, session, sensor_phase, cq_phase, night) -> list[dict]:
    """Session x night pieces (a session that crosses noon is cut at the night boundary)."""
    return group_spans(ts, {"subject_id": subject, "device_id": device, "session_id": session,
                            "sensor_phase": sensor_phase, "channel_quality_phase": cq_phase, "night_id": night})


def _group_fields(r: dict) -> dict:
    return {"subject_id": r["subject_id"], "device_id": r["device_id"], "session_id": r["session_id"],
            "sensor_phase": r["sensor_phase"], "channel_quality_phase": r["channel_quality_phase"],
            "start_timestamp": fmt_ts(r["start"]), "end_timestamp": fmt_ts(r["end"]), "n_rows": r["n_rows"]}


def loso_outer(sessions: list[dict], folds: dict[int, str], cohort: list[str], version: str) -> list[dict]:
    subjects = {r["subject_id"] for r in sessions}
    if subjects != set(cohort) or set(folds.values()) != set(cohort) or len(folds) != len(cohort):
        raise SplitError(f"LOSO folds {folds} do not match the cohort {cohort} / sessions {sorted(subjects)}")
    out = []
    for fold, held in sorted(folds.items()):
        for r in sessions:
            out.append({"protocol_version": version, "split_id": f"{version}_loso", "fold": fold,
                        "held_out_subject": held, **_group_fields(r),
                        "partition": "test" if r["subject_id"] == held else "train"})
    return out


def loso_inner(sessions: list[dict], folds: dict[int, str], cohort: list[str], version: str) -> list[dict]:
    """Subject-level nested validation: the two training subjects validate each other; the held-out subject is
    absent from every inner record."""
    out = []
    for fold, held in sorted(folds.items()):
        remaining = [s for s in cohort if s != held]
        if len(remaining) != 2:
            raise SplitError("subject-level two-way inner validation needs exactly two training subjects")
        for name, (train, val) in (("A", (remaining[0], remaining[1])), ("B", (remaining[1], remaining[0]))):
            for r in sessions:
                if r["subject_id"] == held:
                    continue
                out.append({"protocol_version": version, "split_id": f"{version}_loso", "fold": fold,
                            "held_out_subject": held, "inner_split": name, **_group_fields(r),
                            "partition": "inner_train" if r["subject_id"] == train else "inner_val"})
    return out


def personalization(pieces: list[dict], budgets: list[int], buffer_nights: int, primary_from: int,
                    version: str) -> list[dict]:
    """Per subject and budget b: nights 1..b adaptation, next `buffer_nights` buffer, later nights test.
    b = 0: every night is test. `primary_test` marks nights >= primary_from (identical for all budgets)."""
    if primary_from != max(budgets) + buffer_nights + 1:
        raise SplitError("primary test span must start right after the largest budget and its buffer")
    out = []
    for subject in sorted({p["subject_id"] for p in pieces}):
        sp = [p for p in pieces if p["subject_id"] == subject]
        ordinal = {n: i + 1 for i, n in enumerate(sorted({p["night_id"] for p in sp}))}
        if len(ordinal) < primary_from:
            raise SplitError(f"{subject} has fewer nights than the primary test start")
        for b in budgets:
            for p in sorted(sp, key=lambda q: (q["start"], q["device_id"], q["session_id"])):
                k = ordinal[p["night_id"]]
                if b == 0:
                    part = "test"
                else:
                    part = "adaptation" if k <= b else "buffer" if k <= b + buffer_nights else "test"
                out.append({"protocol_version": version, "split_id": f"{version}_personalization",
                            "subject_id": subject, "budget_nights": b, "night_id": p["night_id"],
                            "night_ordinal": k, "device_id": p["device_id"], "session_id": p["session_id"],
                            "sensor_phase": p["sensor_phase"], "channel_quality_phase": p["channel_quality_phase"],
                            "partition": part, "primary_test": int(k >= primary_from),
                            "start_timestamp": fmt_ts(p["start"]), "end_timestamp": fmt_ts(p["end"]),
                            "n_rows": p["n_rows"]})
    return out


def csv_text(rows: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def write_split(path: Path, rows: list[dict], columns: list[str]) -> str:
    text = csv_text(rows, columns)
    write_text(path, text)
    return sha256_text(text)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def file_sha256_lf(path: str | Path) -> str:
    """SHA-256 of a text file with CRLF normalised to LF (checkout-independent; D-042)."""
    with open(path, "rb") as fh:
        data = fh.read()
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def read_split(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
