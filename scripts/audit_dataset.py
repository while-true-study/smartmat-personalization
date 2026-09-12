"""P0 raw dataset audit (inventory level). Read-only on raw data; writes only to outputs/qa/.

What it reports (per file, per source, per subject):
  subjects / devices / file counts / date range / row counts / pressure channel count /
  temperature & humidity presence / timestamp formats / approximate sampling interval /
  schema variants / byte- and content-level duplicates / cross-file row overlap /
  filename-vs-folder device mismatch / structural anomalies.

It deliberately does NOT clean, resample, interpolate, window, split or normalise anything.

Usage:
    python scripts/build_manifest.py   # first
    python scripts/audit_dataset.py
"""
from __future__ import annotations

import hashlib
import platform
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_json, write_text  # noqa: E402
from src.data.manifest import find_duplicate_groups, read_manifest, sha256_file  # noqa: E402
from src.data.raw_parser import parse_file  # noqa: E402
from src.data.subject_mapping import resolve_source  # noqa: E402

ADC_MAX = 4095
TEMP_RANGE = (-10, 60)
HUMID_RANGE = (0, 100)
GAP_MINUTES = (1, 10, 60)
_RE_FNAME_DATE = re.compile(r"(?:^|_)(?:(?P<y>20\d{2}))?(?P<m>[01]\d)(?P<d>[0-3]\d)(?:T|_|\.|$)")

FILE_COLUMNS = [
    "file_id", "source_relpath", "source_id", "subject_id", "device_id", "dataset_role", "size_bytes",
    "encoding", "has_bom", "line_endings", "n_lines", "n_data_rows", "n_nondata_lines", "line_type_counts",
    "schemas", "header_variants", "ts_formats", "year_sources", "n_ts_unparsed",
    "first_ts", "last_ts", "first_ts_in_file_order", "span_hours", "filename_date", "filename_date_matches",
    "median_dt_s", "p05_dt_s", "p95_dt_s", "n_dt_zero", "n_dt_negative", "max_backward_s",
    "n_gap_gt_1min", "n_gap_gt_10min", "n_gap_gt_60min", "max_gap_min", "median_rows_per_minute",
    "n_dup_rows", "n_dup_timestamps", "n_pressure_channels", "pressure_min", "pressure_max",
    "n_pressure_cells_at_adc_max", "frac_rows_all_zero_pressure",
    "temp_present", "temp_min", "temp_max", "n_temp_zero", "n_temp_out_of_range",
    "humid_present", "humid_min", "humid_max", "n_humid_zero", "n_humid_out_of_range",
    "n_decimal_rows", "sep_counts", "device_id_column_values", "json_root_keys",
    "n_chunk_keys", "n_dup_chunk_keys", "movement_counts", "n_control_events", "data_rows_sha256",
    "filename_annotation", "flags",
]


def _fmt_counter(c: Counter | dict) -> str:
    return ";".join(f"{k}={v}" for k, v in sorted(c.items(), key=lambda kv: (-kv[1], str(kv[0]))))


def _row_hash(fp: tuple) -> int:
    return int.from_bytes(hashlib.blake2b(repr(fp).encode("utf-8"), digest_size=8).digest(), "little")


def _filename_date(name: str) -> tuple[int | None, int, int] | None:
    m = _RE_FNAME_DATE.search(Path(name).stem)
    if not m:
        return None
    return (int(m["y"]) if m["y"] else None, int(m["m"]), int(m["d"]))


def audit_file(rec: dict, root: Path) -> tuple[dict, np.ndarray, list[dict], Counter, Counter, dict]:
    src = resolve_source(rec["source_relpath"])
    pf = parse_file(root / rec["source_relpath"], year_hint=src.year_hint)
    rows = pf.rows
    flags: list[str] = [f for f in rec["flags"].split("|") if f]
    issues: list[dict] = []

    def issue(code: str, severity: str, detail: str) -> None:
        issues.append({"source_relpath": rec["source_relpath"], "subject_id": rec["subject_id"],
                       "severity": severity, "code": code, "detail": detail})
        flags.append(code)

    ts_list = [r.ts for r in rows if r.ts is not None]
    epoch = np.array([t.timestamp() for t in ts_list], dtype=np.int64) if ts_list else np.array([], dtype=np.int64)
    dt = np.diff(epoch) if epoch.size > 1 else np.array([], dtype=np.int64)
    pos = dt[dt > 0]

    pressure = np.array([r.pressure for r in rows if len(r.pressure) == 6], dtype=float)
    temps = np.array([r.temp for r in rows if r.temp is not None], dtype=float)
    hums = np.array([r.humid for r in rows if r.humid is not None], dtype=float)
    fps = [r.fingerprint() for r in rows]
    hashes = np.unique(np.array([_row_hash(fp) for fp in fps], dtype=np.uint64)) if fps else np.array([], np.uint64)
    n_dup_rows = len(fps) - len(set(fps))
    sec_ts = [r.ts for r in rows if r.ts is not None and r.ts_format != "ymd_hm"]
    n_dup_ts = len(sec_ts) - len(set(sec_ts))

    minute_counts = Counter(t.replace(second=0) for t in ts_list)
    fdate = _filename_date(rec["file_name"])
    first = min(ts_list) if ts_list else None
    last = max(ts_list) if ts_list else None
    fdate_match = ""
    if fdate and first:
        y, m, d = fdate
        covered = set()
        cur = (first - timedelta(hours=12)).date()
        while cur <= last.date():
            covered.add((cur.month, cur.day))
            cur += timedelta(days=1)
        fdate_match = str((m, d) in covered)

    schemas = Counter(r.schema for r in rows)
    ts_formats = Counter(r.ts_format for r in rows)
    year_sources = Counter(r.year_source for r in rows)
    seps = Counter(r.sep for r in rows)
    dev_col = Counter(r.device_id for r in rows if r.device_id)
    movement = Counter(r.movement or "none" for r in rows)
    controls = Counter(r.control for r in rows if r.control)
    nondata = {k: v for k, v in pf.line_types.items() if k != "data"}
    root_keys = Counter({k: v for k, v in pf.root_keys.items() if k != "logs"})

    # ---- issues -------------------------------------------------------------------------
    if "device_prefix_mismatch" in flags:
        issues.append({"source_relpath": rec["source_relpath"], "subject_id": rec["subject_id"],
                       "severity": "high", "code": "device_prefix_mismatch",
                       "detail": f"folder device={rec['device_id']} filename device={rec['device_id_filename']}"})
    content_devices = {k.split("_", 1)[1] for k in root_keys if "_" in k} | set(dev_col)
    folder_dev = rec["device_id"]
    if content_devices:
        if folder_dev in ("unresolved", "unknown"):
            issue("device_in_content", "info", f"content declares device(s) {sorted(content_devices)}")
        elif content_devices != {folder_dev}:
            issue("content_device_mismatch", "high", f"folder={folder_dev} content={sorted(content_devices)}")
    if not rows:
        issue("no_data_rows", "high", "no parsable sensor rows")
    if seps.get(".", 0):
        issue("dot_separator_before_p1", "high", f"{seps['.']} rows use '.' between timestamp and P1")
    if ts_formats.get("ymd_hm", 0):
        issue("minute_resolution_timestamps", "high", f"{ts_formats['ymd_hm']} rows have HH:MM timestamps (no seconds)")
    if year_sources.get("config_hint", 0):
        issue("year_inferred_from_config", "medium", f"{year_sources['config_hint']} MM-DD rows dated with year_hint")
    if year_sources.get("unresolved", 0) or year_sources.get("invalid", 0):
        issue("timestamp_unresolved", "high", _fmt_counter(year_sources))
    for kind, sev in (("crash_dump", "medium"), ("malformed_data", "high"), ("nvs_log", "low"),
                      ("device_log", "low"), ("empty_csv_row", "low")):
        if nondata.get(kind):
            issue(f"nondata_{kind}", sev, f"{nondata[kind]} lines; e.g. {pf.samples.get(kind, [''])[0]}")
    if len(schemas) > 1:
        issue("mixed_schema_in_file", "medium", _fmt_counter(schemas))
    if any(s.startswith("nonstandard") for s in schemas):
        issue("nonstandard_schema", "high", _fmt_counter(schemas))
    n_neg = int((dt < 0).sum())
    if n_neg:
        issue("time_goes_backwards", "high", f"{n_neg} backward steps, largest {int(-dt.min())} s")
    if n_dup_rows:
        issue("duplicate_rows_in_file", "medium", f"{n_dup_rows} exact duplicate rows")
    if n_dup_ts:
        issue("duplicate_timestamps_in_file", "low", f"{n_dup_ts} repeated second-resolution timestamps")
    if temps.size and (temps == 0).any():
        issue("temp_zero_values", "medium", f"{int((temps == 0).sum())} rows with temp == 0")
    if hums.size and (hums == 0).any():
        issue("humid_zero_values", "medium", f"{int((hums == 0).sum())} rows with humid == 0")
    n_t_oor = int(((temps < TEMP_RANGE[0]) | (temps > TEMP_RANGE[1])).sum()) if temps.size else 0
    n_h_oor = int(((hums < HUMID_RANGE[0]) | (hums > HUMID_RANGE[1])).sum()) if hums.size else 0
    if n_t_oor or n_h_oor:
        issue("temp_humid_out_of_range", "high", f"temp oor={n_t_oor}, humid oor={n_h_oor}")
    if pressure.size and ((pressure < 0) | (pressure > ADC_MAX)).any():
        issue("pressure_out_of_adc_range", "high", f"min={pressure.min()} max={pressure.max()}")
    if fdate_match == "False":
        issue("filename_date_mismatch", "medium", f"filename date {fdate} vs content {first}..{last}")
    if rec["filename_annotation"]:
        issue("provider_filename_annotation", "medium", rec["filename_annotation"])
    if len(pf.chunk_keys) != len(set(pf.chunk_keys)):
        issue("duplicate_chunk_keys", "high", f"{len(pf.chunk_keys) - len(set(pf.chunk_keys))} repeated JSON log keys")

    row = {
        "file_id": rec["file_id"], "source_relpath": rec["source_relpath"], "source_id": rec["source_id"],
        "subject_id": rec["subject_id"], "device_id": rec["device_id"], "dataset_role": rec["dataset_role"],
        "size_bytes": rec["size_bytes"], "encoding": pf.encoding, "has_bom": pf.has_bom,
        "line_endings": _fmt_counter({k: v for k, v in pf.line_endings.items() if v}),
        "n_lines": pf.n_lines, "n_data_rows": len(rows), "n_nondata_lines": sum(nondata.values()),
        "line_type_counts": _fmt_counter(pf.line_types), "schemas": _fmt_counter(schemas),
        "header_variants": " || ".join(pf.headers), "ts_formats": _fmt_counter(ts_formats),
        "year_sources": _fmt_counter(year_sources), "n_ts_unparsed": len(rows) - len(ts_list),
        "first_ts": first, "last_ts": last, "first_ts_in_file_order": ts_list[0] if ts_list else None,
        "span_hours": round((last - first).total_seconds() / 3600, 2) if first else None,
        "filename_date": "-".join(str(x) for x in fdate if x is not None) if fdate else "",
        "filename_date_matches": fdate_match,
        "median_dt_s": float(np.median(pos)) if pos.size else None,
        "p05_dt_s": float(np.percentile(pos, 5)) if pos.size else None,
        "p95_dt_s": float(np.percentile(pos, 95)) if pos.size else None,
        "n_dt_zero": int((dt == 0).sum()), "n_dt_negative": n_neg,
        "max_backward_s": int(-dt.min()) if n_neg else 0,
        "n_gap_gt_1min": int((dt > 60).sum()), "n_gap_gt_10min": int((dt > 600).sum()),
        "n_gap_gt_60min": int((dt > 3600).sum()), "max_gap_min": round(float(dt.max()) / 60, 1) if dt.size else None,
        "median_rows_per_minute": float(np.median(list(minute_counts.values()))) if minute_counts else None,
        "n_dup_rows": n_dup_rows, "n_dup_timestamps": n_dup_ts,
        "n_pressure_channels": _fmt_counter(Counter(len(r.pressure) for r in rows)),
        "pressure_min": float(pressure.min()) if pressure.size else None,
        "pressure_max": float(pressure.max()) if pressure.size else None,
        "n_pressure_cells_at_adc_max": int((pressure == ADC_MAX).sum()) if pressure.size else 0,
        "frac_rows_all_zero_pressure": round(float((pressure.sum(axis=1) == 0).mean()), 4) if pressure.size else None,
        "temp_present": bool(temps.size), "temp_min": float(temps.min()) if temps.size else None,
        "temp_max": float(temps.max()) if temps.size else None, "n_temp_zero": int((temps == 0).sum()),
        "n_temp_out_of_range": n_t_oor,
        "humid_present": bool(hums.size), "humid_min": float(hums.min()) if hums.size else None,
        "humid_max": float(hums.max()) if hums.size else None, "n_humid_zero": int((hums == 0).sum()),
        "n_humid_out_of_range": n_h_oor,
        "n_decimal_rows": sum(r.has_decimal for r in rows), "sep_counts": _fmt_counter(seps),
        "device_id_column_values": _fmt_counter(dev_col), "json_root_keys": _fmt_counter(root_keys),
        "n_chunk_keys": len(pf.chunk_keys), "n_dup_chunk_keys": len(pf.chunk_keys) - len(set(pf.chunk_keys)),
        "movement_counts": _fmt_counter(movement), "n_control_events": sum(controls.values()),
        "data_rows_sha256": hashlib.sha256("\n".join(map(repr, fps)).encode("utf-8")).hexdigest() if fps else "",
        "filename_annotation": rec["filename_annotation"], "flags": "|".join(dict.fromkeys(flags)),
    }
    meta = {"first": first, "last": last, "subject": rec["subject_id"], "device": rec["device_id"],
            "source_id": rec["source_id"], "role": rec["dataset_role"]}
    return row, hashes, issues, controls, Counter(r.event_raw.split()[-1] for r in rows if r.event_raw), meta


def cross_file_overlap(meta: dict[str, dict], hashes: dict[str, np.ndarray]) -> list[dict]:
    """Pairs of files whose time ranges overlap, with shared-row counts."""
    items = sorted(((m["first"], m["last"], fid) for fid, m in meta.items() if m["first"]), key=lambda x: x[0])
    out = []
    for i, (a0, a1, fa) in enumerate(items):
        for b0, b1, fb in items[i + 1:]:
            if b0 > a1:
                break
            ov_h = (min(a1, b1) - max(a0, b0)).total_seconds() / 3600
            shared = int(np.intersect1d(hashes[fa], hashes[fb], assume_unique=True).size)
            ma, mb = meta[fa], meta[fb]
            out.append({
                "file_a": ma["relpath"], "file_b": mb["relpath"],
                "subject_a": ma["subject"], "subject_b": mb["subject"],
                "device_a": ma["device"], "device_b": mb["device"],
                "same_subject": ma["subject"] == mb["subject"],
                "same_source": ma["source_id"] == mb["source_id"],
                "overlap_hours": round(ov_h, 2), "n_shared_rows": shared,
                "n_rows_a": int(hashes[fa].size), "n_rows_b": int(hashes[fb].size),
            })
    return out


def aggregate(rows: list[dict], key: str) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    out = []
    for k, g in groups.items():
        sensor = [r for r in g if r["n_data_rows"]]
        firsts = [r["first_ts"] for r in sensor if r["first_ts"]]
        lasts = [r["last_ts"] for r in sensor if r["last_ts"]]
        med = [r["median_dt_s"] for r in sensor if r["median_dt_s"] is not None]
        rpm = [r["median_rows_per_minute"] for r in sensor if r["median_rows_per_minute"] is not None]
        def merge(col: str) -> str:
            total: Counter = Counter()
            for r in sensor:
                for item in filter(None, r[col].split(";")):
                    k, v = item.rsplit("=", 1)
                    total[k] += int(v)
            return _fmt_counter(total)

        out.append({
            key: k,
            "subjects": ",".join(sorted({r["subject_id"] for r in g})),
            "devices": ",".join(sorted({r["device_id"] for r in g})),
            "roles": ",".join(sorted({r["dataset_role"] for r in g})),
            "n_files": len(g), "n_sensor_files": len(sensor),
            "n_data_rows": sum(r["n_data_rows"] for r in sensor),
            "first_ts": min(firsts) if firsts else None, "last_ts": max(lasts) if lasts else None,
            "n_distinct_dates": len({(r["first_ts"] - timedelta(hours=12)).date() for r in sensor if r["first_ts"]}),
            "total_span_hours": round(sum(r["span_hours"] or 0 for r in sensor), 1),
            "median_of_file_median_dt_s": float(np.median(med)) if med else None,
            "median_rows_per_minute": float(np.median(rpm)) if rpm else None,
            "schemas": merge("schemas"), "ts_formats": merge("ts_formats"), "year_sources": merge("year_sources"),
            "pressure_channels": merge("n_pressure_channels"),
            "temp_present": all(r["temp_present"] for r in sensor) if sensor else False,
            "humid_present": all(r["humid_present"] for r in sensor) if sensor else False,
            "temp_range": f"{min(r['temp_min'] for r in sensor if r['temp_present'])}..{max(r['temp_max'] for r in sensor if r['temp_present'])}" if sensor else "",
            "humid_range": f"{min(r['humid_min'] for r in sensor if r['humid_present'])}..{max(r['humid_max'] for r in sensor if r['humid_present'])}" if sensor else "",
            "n_temp_zero": sum(r["n_temp_zero"] for r in sensor), "n_humid_zero": sum(r["n_humid_zero"] for r in sensor),
            "pressure_max": max((r["pressure_max"] for r in sensor if r["pressure_max"] is not None), default=None),
            "n_nondata_lines": sum(r["n_nondata_lines"] for r in sensor),
            "n_dup_rows": sum(r["n_dup_rows"] for r in sensor),
            "n_dt_negative": sum(r["n_dt_negative"] for r in sensor),
            "n_files_filename_date_mismatch": sum(r["filename_date_matches"] == "False" for r in sensor),
        })
    return out


def main() -> int:
    root = paths.raw_root()
    mpath = paths.manifest_path()
    if not mpath.exists():
        print("ERROR: manifest missing; run scripts/build_manifest.py first", file=sys.stderr)
        return 1
    manifest = read_manifest(mpath)
    for r in manifest:
        r["size_bytes"] = int(r["size_bytes"])
        r["is_sensor_data"] = r["is_sensor_data"] == "True"

    # 1. integrity: raw must still match the manifest
    changed = [r["source_relpath"] for r in manifest if sha256_file(root / r["source_relpath"]) != r["sha256"]]
    on_disk = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    missing = sorted({r["source_relpath"] for r in manifest} - on_disk)
    unlisted = sorted(on_disk - {r["source_relpath"] for r in manifest})
    if changed or missing or unlisted:
        print(f"ERROR: raw/manifest mismatch. changed={changed[:5]} missing={missing[:5]} unlisted={unlisted[:5]}",
              file=sys.stderr)
        return 2

    out_dir = paths.audit_output_dir()
    file_rows, issues, meta, hashes = [], [], {}, {}
    control_vocab: Counter = Counter()
    event_tail_vocab: Counter = Counter()
    event_by_source: dict[str, Counter] = defaultdict(Counter)

    for rec in manifest:
        if not rec["is_sensor_data"]:
            issues.append({"source_relpath": rec["source_relpath"], "subject_id": rec["subject_id"],
                           "severity": "info", "code": "non_sensor_file",
                           "detail": f"{rec['dataset_role']} ({rec['extension']}); not parsed"})
            continue
        row, h, iss, ctrl, tails, m = audit_file(rec, root)
        file_rows.append(row)
        issues.extend(iss)
        hashes[rec["file_id"]] = h
        m["relpath"] = rec["source_relpath"]
        meta[rec["file_id"]] = m
        control_vocab.update(ctrl)
        event_tail_vocab.update(tails)
        for k, v in ctrl.items():
            event_by_source[rec["source_id"]][f"control:{k}"] += v
        for k, v in tails.items():
            event_by_source[rec["source_id"]][f"last_token:{k}"] += v

    # 2. cross-file checks
    content_dups = find_duplicate_groups([r for r in file_rows if r["data_rows_sha256"]], key="data_rows_sha256")
    overlaps = cross_file_overlap(meta, hashes)
    for o in overlaps:
        if o["n_shared_rows"]:
            sev = "high"
            code = "rows_shared_across_files" if o["same_subject"] else "rows_shared_across_subjects"
            issues.append({"source_relpath": f"{o['file_a']} <-> {o['file_b']}", "subject_id": o["subject_a"],
                           "severity": sev, "code": code, "detail": f"{o['n_shared_rows']} identical rows"})
        elif o["same_subject"] and o["device_a"] != o["device_b"] and o["overlap_hours"] > 0:
            issues.append({"source_relpath": f"{o['file_a']} <-> {o['file_b']}", "subject_id": o["subject_a"],
                           "severity": "high", "code": "concurrent_devices_same_subject",
                           "detail": f"{o['overlap_hours']} h of simultaneous recording on devices "
                                     f"{o['device_a']} and {o['device_b']}"})
        elif o["same_subject"] and o["overlap_hours"] > 0:
            issues.append({"source_relpath": f"{o['file_a']} <-> {o['file_b']}", "subject_id": o["subject_a"],
                           "severity": "medium", "code": "time_overlap_same_subject_device",
                           "detail": f"{o['overlap_hours']} h overlap, no identical rows"})

    # 3. write outputs
    write_csv(out_dir / "file_audit.csv", file_rows, FILE_COLUMNS)
    src_rows = aggregate(file_rows, "source_id")
    subj_rows = aggregate(file_rows, "subject_id")
    write_csv(out_dir / "source_summary.csv", src_rows, list(src_rows[0].keys()))
    write_csv(out_dir / "subject_summary.csv", subj_rows, list(subj_rows[0].keys()))
    write_csv(out_dir / "issues.csv", issues, ["severity", "code", "subject_id", "source_relpath", "detail"])
    ov_cols = ["file_a", "file_b", "subject_a", "subject_b", "device_a", "device_b", "same_subject",
               "same_source", "overlap_hours", "n_shared_rows", "n_rows_a", "n_rows_b"]
    write_csv(out_dir / "cross_file_time_overlap.csv", overlaps, ov_cols)
    write_csv(out_dir / "content_duplicate_groups.csv",
              [{"data_rows_sha256": k, "files": " | ".join(v)} for k, v in content_dups.items()],
              ["data_rows_sha256", "files"])
    write_csv(out_dir / "event_vocabulary.csv",
              [{"source_id": s, "token": t, "count": n} for s, c in event_by_source.items() for t, n in c.most_common()],
              ["source_id", "token", "count"])

    issue_counts = Counter((i["severity"], i["code"]) for i in issues)
    summary = {
        "audited_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"],
        "manifest_sha256": sha256_file(mpath),
        "python": platform.python_version(),
        "n_manifest_files": len(manifest), "n_sensor_files": len(file_rows),
        "n_data_rows": sum(r["n_data_rows"] for r in file_rows),
        "byte_duplicate_groups": find_duplicate_groups(manifest),
        "content_duplicate_groups": content_dups,
        "n_overlap_pairs": len(overlaps),
        "n_overlap_pairs_with_shared_rows": sum(o["n_shared_rows"] > 0 for o in overlaps),
        "issue_counts": {f"{s}:{c}": n for (s, c), n in sorted(issue_counts.items())},
        "control_event_vocabulary": dict(control_vocab.most_common()),
    }
    write_json(out_dir / "audit_summary.json", summary)

    lines = [f"# P0 raw dataset audit — {summary['audited_at']}", "",
             f"raw_root: `{summary['raw_root']}`  manifest sha256: `{summary['manifest_sha256'][:16]}…`", "",
             "## Subjects", "", "| subject | roles | devices | files | rows | first | last |", "|---|---|---|---|---|---|---|"]
    for s in subj_rows:
        lines.append(f"| {s['subject_id']} | {s['roles']} | {s['devices']} | {s['n_sensor_files']} | "
                     f"{s['n_data_rows']:,} | {s['first_ts']} | {s['last_ts']} |")
    lines += ["", "## Issues (severity:code → count)", ""]
    lines += [f"- {k}: {v}" for k, v in summary["issue_counts"].items()]
    write_text(out_dir / "audit_report.md", "\n".join(lines) + "\n")

    print(f"audited {len(file_rows)} sensor files, {summary['n_data_rows']:,} data rows -> "
          f"{out_dir.relative_to(paths.PROJECT_ROOT)}")
    for k, v in summary["issue_counts"].items():
        print(f"  {k:<60} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
