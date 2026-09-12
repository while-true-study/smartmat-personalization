"""Canonical interim dataset v1 (P0 closure; docs/DECISIONS.md D-023 … D-028).

canonical_v1 means: parsed, provenance-preserving, exact-copy-deduplicated, quality-flagged and
session-labelled rows. Nothing here resamples, interpolates, normalises, scales, windows, splits, smooths,
clips, fuses devices, extracts features or trains anything. Raw values are copied, never altered; quality
information is added as flags, never by removing rows.

Row identity: `canonical_row_id` = "<raw file_id>:<raw line number>", stable across rebuilds.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Sequence

import numpy as np
import pyarrow as pa

from src.data.duplicates import overlapping_file_pairs, row_keys, upload_copy_map
from src.data.provenance import CHANNELS, MISSING, SCHEMA_CODES, SourceData, text_code
from src.data.sensor_phase import assign_phase
from src.data.subject_mapping import channel_quality_spec, sensor_phase_spec

_EPOCH = datetime(1970, 1, 1)
N_CH = 6
PRESSURE_SCHEMA_NAMES = {0: "p6_t_h", 1: "p6_t_h_device_column", 2: "nonstandard"}
DICT = pa.dictionary(pa.int32(), pa.string())

CANONICAL_SCHEMA = pa.schema([
    ("canonical_row_id", pa.string()), ("dataset_role", DICT), ("subject_id", DICT), ("source_id", DICT),
    ("device_id", DICT),
    ("timestamp_raw", pa.string()), ("timestamp", pa.timestamp("s")), ("timestamp_resolution", DICT),
    ("timestamp_format", DICT), ("timestamp_year_source", DICT), ("timezone_status", DICT),
    ("sensor_phase", DICT), ("channel_quality_phase", DICT), ("channel_quality_flag", DICT),
    ("P1", pa.int16()), ("P2", pa.int16()), ("P3", pa.int16()), ("P4", pa.int16()), ("P5", pa.int16()),
    ("P6", pa.int16()), ("temperature", pa.int16()), ("humidity", pa.int16()),
    ("target_temp_valid", pa.bool_()), ("target_humidity_valid", pa.bool_()), ("target_quality_flag", DICT),
    ("pressure_schema", DICT), ("pressure_valid", pa.bool_()), ("pressure_upper_bound_channels", pa.int8()),
    ("pressure_all_zero", pa.bool_()), ("pressure_frame_constant_run_s", pa.int32()), ("pressure_quality_flag", DICT),
    ("event_raw", pa.string()), ("event_redacted", pa.bool_()), ("log_container", DICT),
    ("session_id", DICT), ("gap_before_s", pa.int64()), ("session_bridged_gap", pa.bool_()),
    ("source_file", DICT), ("source_file_id", DICT), ("source_row", pa.int32()), ("chunk_key", DICT),
    ("same_timestamp_group_id", pa.string()), ("same_timestamp_group_size", pa.int16()),
    ("within_timestamp_order", pa.int16()),
    ("duplicate_group_id", pa.string()), ("duplicate_count", pa.int16()),
])

PROVENANCE_SCHEMA = pa.schema([
    ("duplicate_group_id", pa.string()), ("canonical_row_id", pa.string()), ("subject_id", DICT),
    ("device_id", DICT), ("source_file", DICT), ("source_file_id", DICT), ("source_row", pa.int32()),
    ("occurrence_order", pa.int16()), ("is_canonical", pa.bool_()),
])


# ---------------------------------------------------------------------------------------------
# File extraction (compact columns; parsed rows are not kept)
# ---------------------------------------------------------------------------------------------

@dataclass
class FileChunk:
    file_id: str
    relpath: str
    source_id: str
    ts: np.ndarray                 # int64 epoch seconds of the naive local timestamp
    values: np.ndarray             # int16 (n, 8): P1..P6, temp, humid; MISSING where absent
    schema: np.ndarray             # int8 code (SCHEMA_CODES; 2 = nonstandard)
    line_no: np.ndarray            # int32
    ts_raw: list[str]
    ts_format: list[str]
    year_source: list[str]
    event_raw: list[str]
    chunk_key: list[str | None]
    raw_rows: int                  # every parsed data row, dated or not
    undated_rows: int
    dot_separator_rows: int
    device_column_mismatch: int
    decimal_notation_rows: int = 0  # values written with a decimal point (integer-valued, e.g. "28.0")


def extract_file(file_id: str, relpath: str, source_id: str, rows: Sequence, device_id: str) -> FileChunk:
    """Compact columns of one parsed file. Rows without a timestamp are counted, never guessed."""
    ts, vals, schema, line_no, ts_raw, ts_fmt, ysrc, ev, ck = [], [], [], [], [], [], [], [], []
    undated = dot = mismatch = decimal = 0
    for r in rows:
        if r.ts is None:
            undated += 1
            continue
        decimal += bool(getattr(r, "has_decimal", False))
        if r.schema in SCHEMA_CODES:
            v = list(r.pressure[:N_CH]) + [MISSING] * (N_CH - min(N_CH, len(r.pressure)))
            v += [MISSING if r.temp is None else r.temp, MISSING if r.humid is None else r.humid]
        else:
            v = [MISSING] * len(CHANNELS)        # unknown layout: nothing is mapped onto P1..P6 / T / H
        if any(x != MISSING and float(x) != int(x) for x in v):
            raise ValueError(f"{relpath}:{r.line_no}: non-integer sensor value (D-018 requires integer encoding)")
        dot += r.sep != ","
        mismatch += r.device_id is not None and r.device_id != device_id
        ts.append((r.ts - _EPOCH).days * 86400 + (r.ts - _EPOCH).seconds)
        vals.append([int(x) for x in v])
        schema.append(SCHEMA_CODES.get(r.schema, 2))
        line_no.append(r.line_no)
        ts_raw.append(r.ts_raw)
        ts_fmt.append(r.ts_format)
        ysrc.append(r.year_source)
        ev.append(r.event_raw)
        ck.append(r.chunk_key)
    return FileChunk(file_id, relpath, source_id, np.array(ts, np.int64),
                     np.array(vals, np.int64).reshape(-1, len(CHANNELS)).astype(np.int16), np.array(schema, np.int8),
                     np.array(line_no, np.int32), ts_raw, ts_fmt, ysrc, ev, ck, len(rows), undated, dot, mismatch,
                     decimal)


# ---------------------------------------------------------------------------------------------
# Row-level policies (pure functions)
# ---------------------------------------------------------------------------------------------

def target_quality(temp: np.ndarray, humid: np.ndarray, temp_band: Sequence[float],
                   humid_band: Sequence[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """D-025: per-channel validity and a cause label; values are never changed.

    Labels (one per row, by priority): ok | zero_sentinel (T = 0 and H = 0) | extreme_glitch (a value outside
    the band, whatever the other channel reads) |
    zero_value (one channel 0) | missing.
    """
    t = temp.astype(np.int64)
    h = humid.astype(np.int64)
    tm, hm = temp == MISSING, humid == MISSING
    t_ext = ~tm & (t != 0) & ((t < temp_band[0]) | (t > temp_band[1]))
    h_ext = ~hm & (h != 0) & ((h < humid_band[0]) | (h > humid_band[1]))
    t_ok = ~tm & (t != 0) & ~t_ext
    h_ok = ~hm & (h != 0) & ~h_ext
    flag = np.full(t.size, "ok", dtype=object)
    flag[(~tm & (t == 0)) ^ (~hm & (h == 0))] = "zero_value"
    flag[~tm & ~hm & (t == 0) & (h == 0)] = "zero_sentinel"
    flag[t_ext | h_ext] = "extreme_glitch"
    flag[tm | hm] = "missing"
    return t_ok, h_ok, flag


def pressure_quality(values: np.ndarray, schema: np.ndarray, vmin: int, vmax: int) -> dict[str, np.ndarray]:
    """D-018: structural validity (known 6-channel layout, all present, integers in [vmin, vmax]).

    4095 stays valid; it is counted per row (`upper_bound_channels`). Missing channels are never filled.
    """
    p = values[:, :N_CH].astype(np.int64)
    present = p != MISSING
    known = schema != 2
    complete = present.all(axis=1)
    in_range = ((p >= vmin) & (p <= vmax) | ~present).all(axis=1)
    valid = known & complete & in_range
    upper = ((p == vmax) & present).sum(axis=1).astype(np.int8)
    all_zero = complete & ~(p > 0).any(axis=1)
    flag = np.full(p.shape[0], "ok", dtype=object)
    flag[upper > 0] = "upper_bound"
    flag[~in_range] = "invalid_encoding"
    flag[known & ~complete] = "missing_channel"
    flag[~known] = "invalid_schema"
    return {"valid": valid, "upper": upper, "all_zero": all_zero, "flag": flag}


def constant_frame_run_s(ts: np.ndarray, values: np.ndarray, max_gap_s: int = 60) -> np.ndarray:
    """D-018 context: seconds spanned by the run of identical, non-zero, complete pressure frames a row belongs
    to (consecutive rows <= max_gap_s apart); 0 for all-zero or incomplete frames. Context, not validity."""
    n = ts.size
    if n == 0:
        return np.array([], np.int64)
    p = values[:, :N_CH].astype(np.int64)
    ok = (p != MISSING).all(axis=1) & (p > 0).any(axis=1)
    same = np.zeros(n, bool)
    same[1:] = (p[1:] == p[:-1]).all(axis=1) & (np.diff(ts) <= max_gap_s) & ok[1:] & ok[:-1]
    rid = np.cumsum(~same)
    first = np.full(rid.max() + 1, -1, np.int64)
    last = np.zeros(rid.max() + 1, np.int64)
    np.maximum.at(last, rid, ts)
    order_first = np.flatnonzero(~same)
    first[rid[order_first]] = ts[order_first]
    run = (last - first)[rid]
    return np.where(ok, run, 0)


def sessions(ts: np.ndarray, file_idx: np.ndarray, device_id: str, cfg: dict) -> dict[str, np.ndarray]:
    """D-024 on a time-ordered stream: session index, gap to the previous row, and bridged-gap flags."""
    n = ts.size
    dt = np.diff(ts)
    b = cfg["bridge"]
    k = np.rint(dt / b["chunk_s"]).astype(np.int64)
    aligned = (k >= 1) & (k <= b["max_chunks"]) & (np.abs(dt - k * b["chunk_s"]) <= b["tolerance_s"])
    if b.get("require_file_boundary", True):
        aligned &= file_idx[1:] != file_idx[:-1]
    bridge = aligned & (dt > cfg["gap_s"]) & (str(device_id) in {str(d) for d in b["devices"]})
    brk = (dt > cfg["gap_s"]) & ~bridge
    idx = np.concatenate([[0], np.cumsum(brk)]) if n else np.array([], np.int64)
    gap = np.concatenate([[-1], dt]) if n else np.array([], np.int64)
    bridged = np.concatenate([[False], bridge]) if n else np.array([], bool)
    return {"index": idx.astype(np.int64), "gap_before": gap.astype(np.int64), "bridged": bridged}


def same_timestamp_groups(ts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For a time-ordered stream: first position of each row's same-second group, group size, order inside."""
    n = ts.size
    if n == 0:
        return np.array([], np.int64), np.array([], np.int64), np.array([], np.int64)
    new = np.concatenate([[True], ts[1:] != ts[:-1]])
    start = np.maximum.accumulate(np.where(new, np.arange(n), 0))
    gid = np.cumsum(new) - 1
    size = np.bincount(gid)[gid]
    return start, size, np.arange(n) - start


def redact_events(events: Sequence[str], min_digits: int) -> tuple[list[str], np.ndarray]:
    rx = re.compile(r"\d{%d,}" % min_digits)
    out, flag = [], np.zeros(len(events), bool)
    for i, e in enumerate(events):
        r = rx.sub("<redacted>", e)
        out.append(r)
        flag[i] = r != e
    return out, flag


def dictionary(codes: np.ndarray, labels: Sequence[str]) -> pa.DictionaryArray:
    return pa.DictionaryArray.from_arrays(pa.array(np.asarray(codes, np.int32)), pa.array(list(labels), pa.string()))


def categorical(values: Sequence) -> pa.DictionaryArray:
    """Dictionary array from per-row labels; the dictionary is sorted so equal inputs give equal bytes."""
    arr = np.asarray(values, dtype=object)
    labels = sorted({str(v) for v in arr if v is not None})
    pos = {v: i for i, v in enumerate(labels)}
    codes = np.array([pos[str(v)] if v is not None else -1 for v in arr], np.int32)
    return pa.DictionaryArray.from_arrays(pa.array(codes, mask=codes < 0), pa.array(labels, pa.string()))


def nullable_int16(x: np.ndarray) -> pa.Array:
    return pa.array(x.astype(np.int16), mask=x == MISSING)


def content_hash(tables: Iterable[pa.Table]) -> str:
    """SHA-256 of the Arrow IPC stream of the tables (deterministic for equal content and schema)."""
    h = hashlib.sha256()
    for t in tables:
        sink = pa.BufferOutputStream()
        with pa.ipc.new_stream(sink, t.schema) as w:
            w.write_table(t)
        h.update(sink.getvalue().to_pybytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------
# Stream build
# ---------------------------------------------------------------------------------------------

@dataclass
class StreamResult:
    table: pa.Table
    provenance: pa.Table
    stats: dict = field(default_factory=dict)


def build_stream(chunks: Sequence[FileChunk], subject_id: str, device_id: str, role: str, minute_resolution: bool,
                 cfg: dict) -> StreamResult:
    """One subject + device stream: de-duplicate exact copies, order, label, flag. Values are never changed."""
    files = [c.relpath for c in chunks]
    sizes = [c.ts.size for c in chunks]
    file_idx = np.repeat(np.arange(len(chunks), dtype=np.int32), sizes)
    ts = np.concatenate([c.ts for c in chunks]) if chunks else np.array([], np.int64)
    values = np.concatenate([c.values for c in chunks]) if chunks else np.empty((0, len(CHANNELS)), np.int16)
    schema = np.concatenate([c.schema for c in chunks]) if chunks else np.array([], np.int8)
    line_no = np.concatenate([c.line_no for c in chunks]) if chunks else np.array([], np.int32)
    cat = lambda name: [x for c in chunks for x in getattr(c, name)]  # noqa: E731
    ts_raw, ts_fmt, ysrc, events, ckeys = cat("ts_raw"), cat("ts_format"), cat("year_source"), cat("event_raw"), cat("chunk_key")
    n = ts.size

    # D-014: exact upload/export copies only, within this stream, never for minute-resolution sources
    orig = np.full(n, -1, np.int64)
    if n and not (minute_resolution and not cfg["deduplication"]["apply_to_minute_resolution"]):
        uniq_ev = sorted(set(events))
        ev_lut = {e: text_code(e) for e in uniq_ev}
        src = SourceData(source_id=f"{subject_id}|{device_id}", subject_id=subject_id, device_id=device_id,
                         files=files, ts=ts, values=values, file_idx=file_idx, line_no=line_no,
                         event_code=np.array([ev_lut[e] for e in events], np.uint64), schema_code=schema)
        keys = row_keys(src)
        orig = upload_copy_map(src, keys, overlapping_file_pairs(src, keys), cfg["deduplication"]["min_block_rows"])
        copies = np.flatnonzero(orig >= 0)
        if copies.size and not np.array_equal(keys.full[copies], keys.full[orig[copies]]):
            raise ValueError(f"{subject_id}|{device_id}: a removed row differs from its original")
    kept = np.flatnonzero(orig < 0)
    order = kept[np.argsort(ts[kept], kind="stable")]          # time order; raw file/line order within a second
    t_o, f_o = ts[order], file_idx[order]

    file_ids = [c.file_id for c in chunks]
    row_id = np.array([f"{file_ids[f]}:{ln}" for f, ln in zip(file_idx, line_no)], dtype=object)
    copies_of = {}
    for c in np.flatnonzero(orig >= 0):
        copies_of.setdefault(int(orig[c]), []).append(int(c))
    dup_count = np.ones(n, np.int64)
    dup_group = np.full(n, None, dtype=object)
    for o, cs in copies_of.items():
        dup_count[o] = 1 + len(cs)
        dup_group[o] = row_id[o]

    ses = sessions(t_o, f_o, device_id, cfg["session"])
    s_names = [f"{subject_id}|{device_id}|S{k + 1:04d}" for k in range(int(ses["index"].max()) + 1 if n else 0)]
    st_start, st_size, st_order = same_timestamp_groups(t_o)
    st_gid = np.where(st_size > 1, row_id[order][st_start], None)

    bounds, names = sensor_phase_spec(subject_id)
    sensor_phase = assign_phase(t_o, bounds, names) if bounds else np.full(t_o.size, "not_applicable", dtype=object)
    qb, qn, qch = channel_quality_spec(device_id)
    cq_phase = assign_phase(t_o, qb, qn) if qb else np.full(t_o.size, qn[0], dtype=object)
    cq_flag = np.array([qch.get(p, "") or "none" for p in cq_phase], dtype=object)
    if (sensor_phase == "").any() or (cq_phase == "").any():
        raise ValueError(f"{subject_id}|{device_id}: a row falls inside a phase boundary gap")

    v_o = values[order]
    t_ok, h_ok, t_flag = target_quality(v_o[:, 6], v_o[:, 7], cfg["targets"]["temp_band"], cfg["targets"]["humid_band"])
    pq = pressure_quality(v_o, schema[order], cfg["pressure"]["min"], cfg["pressure"]["max"])
    ev_o, red = redact_events([events[i] for i in order], cfg["event_redaction_min_digits"])
    fmt_o = [ts_fmt[i] for i in order]
    schema_names = [("legacy_csv_fsr" if minute_resolution and s == 0 else PRESSURE_SCHEMA_NAMES[int(s)])
                    for s in schema[order]]
    container = ["legacy_csv" if minute_resolution else ("quasi_json_chunk" if ckeys[i] is not None else "plain_line")
                 for i in order]
    m = t_o.size

    cols = {
        "canonical_row_id": pa.array(row_id[order].tolist(), pa.string()),
        "dataset_role": categorical([role] * m), "subject_id": categorical([subject_id] * m),
        "source_id": categorical([chunks[f].source_id for f in f_o]), "device_id": categorical([str(device_id)] * m),
        "timestamp_raw": pa.array([ts_raw[i] for i in order], pa.string()),
        "timestamp": pa.array(t_o, pa.int64()).cast(pa.timestamp("s")),
        "timestamp_resolution": categorical(["minute" if f == "ymd_hm" else "second" for f in fmt_o]),
        "timestamp_format": categorical(fmt_o), "timestamp_year_source": categorical([ysrc[i] for i in order]),
        "timezone_status": categorical([cfg["timezone_status"]] * m),
        "sensor_phase": categorical(sensor_phase), "channel_quality_phase": categorical(cq_phase),
        "channel_quality_flag": categorical(cq_flag),
        **{f"P{i + 1}": nullable_int16(v_o[:, i]) for i in range(N_CH)},
        "temperature": nullable_int16(v_o[:, 6]), "humidity": nullable_int16(v_o[:, 7]),
        "target_temp_valid": pa.array(t_ok), "target_humidity_valid": pa.array(h_ok),
        "target_quality_flag": categorical(t_flag),
        "pressure_schema": categorical(schema_names), "pressure_valid": pa.array(pq["valid"]),
        "pressure_upper_bound_channels": pa.array(pq["upper"], pa.int8()), "pressure_all_zero": pa.array(pq["all_zero"]),
        "pressure_frame_constant_run_s": pa.array(constant_frame_run_s(t_o, v_o), pa.int32()),
        "pressure_quality_flag": categorical(pq["flag"]),
        "event_raw": pa.array(ev_o, pa.string()), "event_redacted": pa.array(red),
        "log_container": categorical(container),
        "session_id": dictionary(ses["index"], s_names),
        "gap_before_s": pa.array(ses["gap_before"], pa.int64(), mask=ses["gap_before"] < 0),
        "session_bridged_gap": pa.array(ses["bridged"]),
        "source_file": dictionary(f_o, files), "source_file_id": dictionary(f_o, file_ids),
        "source_row": pa.array(line_no[order], pa.int32()), "chunk_key": categorical([ckeys[i] for i in order]),
        "same_timestamp_group_id": pa.array(st_gid.tolist(), pa.string()),
        "same_timestamp_group_size": pa.array(st_size, pa.int16()),
        "within_timestamp_order": pa.array(st_order, pa.int16()),
        "duplicate_group_id": pa.array(dup_group[order].tolist(), pa.string()),
        "duplicate_count": pa.array(dup_count[order], pa.int16()),
    }
    table = pa.Table.from_arrays([cols[f.name] for f in CANONICAL_SCHEMA], schema=CANONICAL_SCHEMA)

    # duplicate provenance: every raw occurrence of every de-duplicated group, in raw file/line order
    prov_rows = []
    for o in sorted(copies_of):
        grp = sorted([o] + copies_of[o], key=lambda r: (file_idx[r], line_no[r]))
        for k, r in enumerate(grp):
            prov_rows.append((row_id[o], row_id[o], int(file_idx[r]), int(line_no[r]), k, r == o))
    pf = np.array([p[2] for p in prov_rows], np.int32)
    provenance = pa.Table.from_arrays([
        pa.array([p[0] for p in prov_rows], pa.string()), pa.array([p[1] for p in prov_rows], pa.string()),
        categorical([subject_id] * len(prov_rows)), categorical([str(device_id)] * len(prov_rows)),
        dictionary(pf, files), dictionary(pf, file_ids),
        pa.array([p[3] for p in prov_rows], pa.int32()), pa.array([p[4] for p in prov_rows], pa.int16()),
        pa.array([p[5] for p in prov_rows], pa.bool_()),
    ], schema=PROVENANCE_SCHEMA)

    # raw / removed / canonical counts per (source, sensor phase, channel-quality phase) and per file
    sp_all = assign_phase(ts, bounds, names) if bounds else np.full(n, "not_applicable", dtype=object)
    cq_all = assign_phase(ts, qb, qn) if qb else np.full(n, qn[0], dtype=object)
    src_all = np.array([chunks[f].source_id for f in range(len(chunks))], dtype=object)[file_idx] if n else np.array([], object)
    is_copy = orig >= 0
    slices: dict[tuple, dict] = {}
    for key, cp in zip(zip(src_all.tolist(), sp_all.tolist(), cq_all.tolist()), is_copy.tolist()):
        s = slices.setdefault(key, {"rows_raw_dated": 0, "rows_copies_removed": 0})
        s["rows_raw_dated"] += 1
        s["rows_copies_removed"] += cp
    per_file = []
    copies_per_file = np.bincount(file_idx[is_copy], minlength=len(chunks)) if n else np.zeros(len(chunks), int)
    for i, c in enumerate(chunks):
        per_file.append({"file_id": c.file_id, "source_relpath": c.relpath, "source_id": c.source_id,
                         "rows_raw": c.raw_rows, "rows_undated": c.undated_rows,
                         "rows_copies_removed": int(copies_per_file[i]),
                         "rows_canonical": int(c.ts.size - copies_per_file[i])})

    raw_rows = sum(c.raw_rows for c in chunks)
    undated = sum(c.undated_rows for c in chunks)
    raw_order_neg = int(sum((np.diff(c.ts) < 0).sum() for c in chunks))
    stats = {
        "subject_id": subject_id, "device_id": str(device_id), "role": role, "files": len(chunks),
        "rows_raw": raw_rows, "rows_undated": undated, "rows_copies_removed": int((orig >= 0).sum()),
        "rows_canonical": m, "duplicate_groups": len(copies_of),
        "sessions": len(s_names), "bridged_gaps": int(ses["bridged"].sum()),
        "same_timestamp_groups": int((st_size > 1).sum() - (st_order[st_size > 1] > 0).sum()),
        "rows_in_same_timestamp_groups": int((st_size > 1).sum()),
        "target_invalid_rows": int((~t_ok | ~h_ok).sum()),
        "target_flag_counts": {k: int(v) for k, v in zip(*np.unique(t_flag, return_counts=True))},
        "pressure_invalid_rows": int((~pq["valid"]).sum()), "pressure_upper_bound_rows": int((pq["upper"] > 0).sum()),
        "pressure_upper_bound_cells": int(pq["upper"].astype(np.int64).sum()),
        "pressure_all_zero_rows": int(pq["all_zero"].sum()),
        "events_redacted": int(red.sum()), "dot_separator_rows": sum(c.dot_separator_rows for c in chunks),
        "device_column_mismatch_rows": sum(c.device_column_mismatch for c in chunks),
        "decimal_notation_rows": sum(c.decimal_notation_rows for c in chunks),
        "raw_out_of_order_steps": raw_order_neg,
        "reconciles": raw_rows - undated - int((orig >= 0).sum()) == m,
        "slices": slices, "files": per_file,
    }
    return StreamResult(table, provenance, stats)
