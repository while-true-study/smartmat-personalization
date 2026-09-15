"""P9 User03 cross-source reconciliation (protocol v1.3; D-061; docs/P9_USER03_EXTERNAL_VALIDATION_PLAN.md §2–§5).

Rebuilds second-resolution User03 rows from two complementary raw exports of the same seven nights:
- the valid User03 CSV export (`user03_legacy`, minute timestamps, P1–P6, T, H, event; D-021);
- the paired TXT export (raw folder `user06_auxiliary`, second timestamps). For nights 1–6 the first pressure value
  is fused to the seconds by '.', so only P2–P6, T and H are compared and the fused value is an audit column; night 7
  has a regular P1–P6 layout.
A minute is kept only if it lies in exactly one paired file per source, both sources have the same number of data
rows in it, every row pair has identical compared fields in file order, the TXT seconds do not decrease and the events
agree up to punctuation; the provider-annotated error minute is excluded. Nothing is interpolated, imputed, invented
or joined by nearest neighbour. The rows then pass through the canonical_v1 stream builder unchanged
(`src/data/canonical.build_stream`). Raw files are read only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pyarrow as pa
import yaml

from src.data import paths
from src.data.canonical import FileChunk, build_stream, content_hash
from src.data.io_guard import read_bytes, write_json, write_parquet
from src.data.provenance import SCHEMA_CODES
from src.data.raw_parser import DataRow, parse_file
from src.evaluation import splits as S
from src.evaluation.protocol import protocol_sha256

VERSION = "v1.3"
_EPOCH = datetime(1970, 1, 1)
CATEGORIES = ("included", "csv_only", "txt_only", "ambiguous_source", "provider_annotated_error", "count_mismatch",
              "value_mismatch", "txt_time_order_violation", "event_text_mismatch")
FIELDS = {"dot_p2_p6": ("P2", "P3", "P4", "P5", "P6", "temperature", "humidity"),
          "comma_p1_p6": ("P1", "P2", "P3", "P4", "P5", "P6", "temperature", "humidity")}
_NON_WORD = re.compile(r"[^0-9A-Za-z가-힣]")


class P9DataError(RuntimeError):
    pass


# ---------------------------------------------------------------------------------------------- config / hashes

def config_yaml() -> Path:
    return paths.PROJECT_ROOT / "configs" / "experiments" / VERSION / "p9_user03_external_validation.yaml"


def plan_doc() -> Path:
    return paths.PROJECT_ROOT / "docs" / "P9_USER03_EXTERNAL_VALIDATION_PLAN.md"


def load_config() -> dict:
    doc = yaml.safe_load(config_yaml().read_text(encoding="utf-8"))
    problems = []
    if doc.get("protocol_version") != VERSION or doc.get("decision") != "D-061":
        problems.append("addendum version/decision")
    if doc["base_protocol"]["sha256"] != protocol_sha256():
        problems.append("v1.0 protocol file differs from the hash v1.3 builds on")
    if doc["external_subject"] != "User03" or doc["primary_cohort_unchanged"] != ["User01", "User02", "User07"]:
        problems.append("cohort roles differ from the plan")
    pairs = doc["sources"]["pairs"]
    if [p["night"] for p in pairs] != list(range(1, 8)) or {p["txt_layout"] for p in pairs} - set(FIELDS):
        problems.append("night pairs differ from the plan")
    if problems:
        raise P9DataError("v1.3 addendum check failed: " + "; ".join(problems))
    return doc


def design_hashes() -> dict:
    return {"protocol_version": VERSION, "decision": "D-061", "status": "post_hoc_external_sensitivity",
            "plan_sha256_lf": S.file_sha256_lf(plan_doc()), "config_sha256_lf": S.file_sha256_lf(config_yaml()),
            "base_protocol_sha256": protocol_sha256()}


def artifact_dir() -> Path:
    return paths.PROJECT_ROOT / "data" / "external" / "p9_user03_v1"


def manifest_path() -> Path:
    return paths.PROJECT_ROOT / "data" / "external" / "p9_user03_v1_manifest.json"


def raw_manifest() -> dict[str, dict]:
    with open(paths.PROJECT_ROOT / "data" / "interim" / "manifest" / "raw_file_manifest.csv", encoding="utf-8",
              newline="") as fh:
        return {r["file_id"]: r for r in csv.DictReader(fh)}


def resolve(file_id: str, expected_sha: str, manifest: dict[str, dict]) -> Path:
    """Raw path of a file id; its SHA-256 must equal the config and the committed raw manifest."""
    rec = manifest.get(file_id)
    if rec is None:
        raise P9DataError(f"{file_id}: not in the raw manifest")
    p = paths.raw_root() / rec["source_relpath"]
    digest = hashlib.sha256(read_bytes(p)).hexdigest()
    if digest != expected_sha or digest != rec["sha256"]:
        raise P9DataError(f"{file_id}: SHA-256 differs from the config or the raw manifest")
    return p


# ---------------------------------------------------------------------------------------------- pure helpers

def minute_key(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M")


def epoch_s(ts: datetime) -> int:
    d = ts - _EPOCH
    return d.days * 86400 + d.seconds


def fields_of(row: DataRow, layout: str, source: str) -> tuple[int, ...]:
    """Compared fields: P2–P6, T, H (dot layout; TXT P1 is the fused value and never compared) or P1–P6, T, H."""
    p = [int(x) for x in row.pressure]
    t, h = int(row.temp), int(row.humid)
    if layout == "dot_p2_p6":
        return (*p[1:6], t, h)
    return (*p[:6], t, h)


def event_relation(a: str, b: str) -> str:
    """identical | punctuation_only | different (events are provenance only, never model inputs)."""
    a, b = (a or "").strip(), (b or "").strip()
    if a == b:
        return "identical"
    if _NON_WORD.sub("", a) == _NON_WORD.sub("", b):
        return "punctuation_only"
    return "different"


@dataclass
class Source:
    night: int
    file_id: str
    sha256: str
    relpath: str
    layout: str
    rows: list[DataRow]
    line_types: Counter


def _by_minute(sources: list[Source]) -> dict[str, list[tuple[int, int]]]:
    """minute -> [(source index, row index)] in file order."""
    out: dict[str, list[tuple[int, int]]] = {}
    for si, s in enumerate(sources):
        for ri, r in enumerate(s.rows):
            if r.ts is None:
                raise P9DataError(f"{s.file_id}:{r.line_no}: data row without a timestamp")
            out.setdefault(minute_key(r.ts), []).append((si, ri))
    return out


def reconcile(csv_sources: list[Source], txt_sources: list[Source], annotated: dict | None) -> tuple[list[dict], list[dict]]:
    """Minute-level reconciliation. Returns (reconstructed rows, one record per minute with its category)."""
    cm, tm = _by_minute(csv_sources), _by_minute(txt_sources)
    rows, minutes = [], []
    for mk in sorted(set(cm) | set(tm)):
        c, t = cm.get(mk, []), tm.get(mk, [])
        cfiles = sorted({csv_sources[i].night for i, _ in c})
        tfiles = sorted({txt_sources[i].night for i, _ in t})
        night = cfiles[0] if len(cfiles) == 1 else (tfiles[0] if len(tfiles) == 1 else None)
        rec = {"minute": mk, "night": night, "csv_rows": len(c), "txt_rows": len(t), "event_punctuation_rows": 0}
        cat = None
        if not t:
            cat = "csv_only"
        elif not c:
            cat = "txt_only"
        elif len(cfiles) != 1 or len(tfiles) != 1 or cfiles != tfiles:
            cat = "ambiguous_source"
        txt = txt_sources[t[0][0]] if t else None
        if cat is None and annotated and txt.file_id == annotated["txt_file_id"]:
            lo, hi = annotated["time_of_day_from"], annotated["time_of_day_to"]
            if any(lo <= txt.rows[ri].ts.strftime("%H:%M:%S") <= hi for _, ri in t):
                cat = "provider_annotated_error"
        if cat is None and len(c) != len(t):
            cat = "count_mismatch"
        pairs = []
        if cat is None:
            csv_src = csv_sources[c[0][0]]
            layout = txt.layout
            for (_, ci), (_, ti) in zip(c, t):
                cr, tr = csv_src.rows[ci], txt.rows[ti]
                if fields_of(cr, layout, "csv") != fields_of(tr, layout, "txt"):
                    cat = "value_mismatch"
                    break
                pairs.append((cr, tr))
        if cat is None:
            secs = [tr.ts for _, tr in pairs]
            if any(b < a for a, b in zip(secs, secs[1:])):
                cat = "txt_time_order_violation"
        if cat is None:
            rel = [event_relation(cr.event_raw, tr.event_raw) for cr, tr in pairs]
            if "different" in rel:
                cat = "event_text_mismatch"
            rec["event_punctuation_rows"] = rel.count("punctuation_only")
        rec["category"] = cat or "included"
        minutes.append(rec)
        if cat is not None:
            continue
        csv_src = csv_sources[c[0][0]]
        for k, ((cr, tr), relation) in enumerate(zip(pairs, rel)):
            p1_txt = int(tr.pressure[0])
            rows.append({"night": night, "minute": mk, "within_minute": k, "csv_file_id": csv_src.file_id,
                         "csv_line": cr.line_no, "txt_file_id": txt.file_id, "txt_line": tr.line_no,
                         "csv_sha256": csv_src.sha256, "txt_sha256": txt.sha256, "ts": tr.ts, "ts_raw": tr.ts_raw,
                         "P": tuple(int(x) for x in cr.pressure[:6]), "temperature": int(cr.temp),
                         "humidity": int(cr.humid), "event_raw": cr.event_raw,
                         "timestamp_source": "txt_second",
                         "fsr1_source": "csv" if txt.layout == "dot_p2_p6" else "csv_equals_txt",
                         "verified_fields": ";".join(FIELDS[txt.layout]),
                         "dot_value_audit": p1_txt if txt.layout == "dot_p2_p6" else None,
                         "dot_value_equals_csv_p1": (p1_txt == int(cr.pressure[0])) if txt.layout == "dot_p2_p6"
                         else None, "event_relation": relation})
    return rows, minutes


def coverage(minutes: list[dict]) -> list[dict]:
    """Per night and category: minutes, CSV rows and TXT rows (no timestamps)."""
    out: dict[tuple, dict] = {}
    for m in minutes:
        key = (m["night"] if m["night"] is not None else 0, m["category"])
        r = out.setdefault(key, {"night": key[0], "category": key[1], "minutes": 0, "csv_rows": 0, "txt_rows": 0,
                                 "event_punctuation_rows": 0})
        r["minutes"] += 1
        r["csv_rows"] += m["csv_rows"]
        r["txt_rows"] += m["txt_rows"]
        r["event_punctuation_rows"] += m["event_punctuation_rows"]
    return [out[k] for k in sorted(out)]


def to_chunks(rows: list[dict], sources: dict[str, Source]) -> list[FileChunk]:
    """One FileChunk per night for the canonical stream builder; row identity = the CSV file id and line."""
    chunks = []
    for night in sorted({r["night"] for r in rows}):
        rs = [r for r in rows if r["night"] == night]
        src = sources[rs[0]["csv_file_id"]]
        vals = np.array([[*r["P"], r["temperature"], r["humidity"]] for r in rs], np.int64).astype(np.int16)
        chunks.append(FileChunk(
            file_id=src.file_id, relpath=f"p9_reconstructed/night{night}", source_id="user03_reconstructed",
            ts=np.array([epoch_s(r["ts"]) for r in rs], np.int64), values=vals,
            schema=np.full(len(rs), SCHEMA_CODES["p6_t_h"], np.int8),
            line_no=np.array([r["csv_line"] for r in rs], np.int32), ts_raw=[r["ts_raw"] for r in rs],
            ts_format=["ymd_hms"] * len(rs), year_source=["explicit"] * len(rs),
            event_raw=[r["event_raw"] for r in rs], chunk_key=[None] * len(rs), raw_rows=len(rs), undated_rows=0,
            dot_separator_rows=0, device_column_mismatch=0))
    return chunks


PROV_SCHEMA = pa.schema([
    ("canonical_row_id", pa.string()), ("night", pa.int8()), ("minute", pa.string()), ("within_minute", pa.int16()),
    ("csv_file_id", pa.string()), ("csv_line", pa.int32()), ("txt_file_id", pa.string()), ("txt_line", pa.int32()),
    ("csv_sha256", pa.string()), ("txt_sha256", pa.string()), ("timestamp_source", pa.string()),
    ("fsr1_source", pa.string()), ("verified_fields", pa.string()), ("dot_value_audit", pa.int16()),
    ("dot_value_equals_csv_p1", pa.bool_()), ("event_relation", pa.string())])


def provenance_table(rows: list[dict]) -> pa.Table:
    return pa.table({
        "canonical_row_id": [f"{r['csv_file_id']}:{r['csv_line']}" for r in rows],
        "night": pa.array([r["night"] for r in rows], pa.int8()), "minute": [r["minute"] for r in rows],
        "within_minute": pa.array([r["within_minute"] for r in rows], pa.int16()),
        "csv_file_id": [r["csv_file_id"] for r in rows], "csv_line": pa.array([r["csv_line"] for r in rows], pa.int32()),
        "txt_file_id": [r["txt_file_id"] for r in rows], "txt_line": pa.array([r["txt_line"] for r in rows], pa.int32()),
        "csv_sha256": [r["csv_sha256"] for r in rows], "txt_sha256": [r["txt_sha256"] for r in rows],
        "timestamp_source": [r["timestamp_source"] for r in rows], "fsr1_source": [r["fsr1_source"] for r in rows],
        "verified_fields": [r["verified_fields"] for r in rows],
        "dot_value_audit": pa.array([r["dot_value_audit"] for r in rows], pa.int16()),
        "dot_value_equals_csv_p1": pa.array([r["dot_value_equals_csv_p1"] for r in rows], pa.bool_()),
        "event_relation": [r["event_relation"] for r in rows]}, schema=PROV_SCHEMA)


# ---------------------------------------------------------------------------------------------- build

def load_sources(cfg: dict) -> tuple[list[Source], list[Source]]:
    man = raw_manifest()
    csv_s, txt_s = [], []
    for pair in cfg["sources"]["pairs"]:
        for kind, out in (("csv", csv_s), ("txt", txt_s)):
            ent = pair[kind]
            p = resolve(ent["file_id"], ent["sha256"], man)
            pf = parse_file(p)
            layout = "csv" if kind == "csv" else pair["txt_layout"]
            rows = [r for r in pf.rows]
            want_sep = "," if kind == "csv" or layout == "comma_p1_p6" else "."
            bad = [r for r in rows if r.sep != want_sep or r.schema != "p6_t_h"
                   or r.ts_format != ("ymd_hm" if kind == "csv" else "ymd_hms") or r.has_decimal]
            if bad:
                raise P9DataError(f"{ent['file_id']}: {len(bad)} data rows do not have the declared layout")
            out.append(Source(pair["night"], ent["file_id"], ent["sha256"], man[ent["file_id"]]["source_relpath"],
                              layout, rows, pf.line_types))
    return csv_s, txt_s


def canonical_cfg() -> dict:
    return yaml.safe_load((paths.PROJECT_ROOT / "configs" / "canonical_v1.yaml").read_text(encoding="utf-8"))


def build(cfg: dict | None = None, write: bool = True) -> dict:
    cfg = load_config() if cfg is None else cfg
    csv_s, txt_s = load_sources(cfg)
    rows, minutes = reconcile(csv_s, txt_s, cfg["sources"]["provider_annotated_error"])
    if not rows:
        raise P9DataError("no minute passed the reconciliation")
    by_id = {s.file_id: s for s in csv_s}
    res = build_stream(to_chunks(rows, by_id), "User03", "unknown", "external_validation", False, canonical_cfg())
    prov = provenance_table(rows)
    ids = set(res.table.column("canonical_row_id").to_pylist())
    if not ids <= set(prov.column("canonical_row_id").to_pylist()):
        raise P9DataError("a canonical row has no reconciliation provenance")
    cov = coverage(minutes)
    summary = {
        **design_hashes(),
        "sources": [{"night": s.night, "role": "csv", "file_id": s.file_id, "sha256": s.sha256,
                     "data_rows": len(s.rows), "non_data_lines": {k: v for k, v in s.line_types.items() if k != "data"}}
                    for s in csv_s] +
                   [{"night": s.night, "role": "txt", "file_id": s.file_id, "sha256": s.sha256, "layout": s.layout,
                     "data_rows": len(s.rows), "non_data_lines": {k: v for k, v in s.line_types.items() if k != "data"}}
                    for s in txt_s],
        "coverage": cov,
        "reconstructed_rows": len(rows), "canonical_rows": res.table.num_rows,
        "dedup_removed_rows": len(rows) - res.table.num_rows,
        "dot_value_audit": {"rows": sum(r["dot_value_audit"] is not None for r in rows),
                            "equal_to_csv_p1": sum(bool(r["dot_value_equals_csv_p1"]) for r in rows)},
        "event_punctuation_only_rows": sum(r["event_relation"] == "punctuation_only" for r in rows),
        "rows_content_sha256": content_hash([res.table]), "provenance_content_sha256": content_hash([prov]),
    }
    if write:
        import pyarrow.parquet as pq
        d = artifact_dir()
        write_parquet(d / "user03_rows.parquet", [res.table], res.table.schema)
        write_parquet(d / "user03_provenance.parquet", [prov], prov.schema)
        # the manifest hashes the content as stored (Parquet round trip), which is what every reader sees
        summary["rows_content_sha256"] = content_hash([pq.read_table(d / "user03_rows.parquet")])
        summary["provenance_content_sha256"] = content_hash([pq.read_table(d / "user03_provenance.parquet")])
        mt = pa.table({k: [m[k] for m in minutes] for k in ("minute", "night", "csv_rows", "txt_rows",
                                                              "event_punctuation_rows", "category")})
        write_parquet(d / "user03_minutes.parquet", [mt], mt.schema)
        write_json(manifest_path(), summary)
    return {"table": res.table, "provenance": prov, "minutes": minutes, "summary": summary}


def load_rows_table() -> pa.Table:
    import pyarrow.parquet as pq
    p = artifact_dir() / "user03_rows.parquet"
    if not p.is_file():
        raise P9DataError("reconstructed User03 rows are missing; run scripts/build_p9_user03.py")
    t = pq.read_table(p)
    man = json.loads(manifest_path().read_text(encoding="utf-8"))
    if content_hash([t]) != man["rows_content_sha256"]:
        raise P9DataError("reconstructed User03 rows differ from the committed manifest")
    return t
