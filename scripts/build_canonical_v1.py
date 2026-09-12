"""Build the canonical interim dataset v1 (P0 closure). Read-only on raw data.

Policies: docs/DECISIONS.md D-023 … D-028; parameters: configs/canonical_v1.yaml. Primary and auxiliary
sources become two Parquet files; the provider-confirmed invalid source (User06), the quarantined files and
restricted metadata are not loaded (excluded/quarantined sensor files are parsed for a row count only, so the
build reconciles against every delivered row; no value of them is kept).

The build fails, writing nothing, if any reconciliation check fails.

Writes:
  data/interim/canonical_v1/primary.parquet               primary cohort rows (not committed)
  data/interim/canonical_v1/auxiliary.parquet             valid auxiliary rows, kept apart (not committed)
  data/interim/canonical_v1/duplicate_provenance.parquet  every raw occurrence of every de-duplicated row
  data/interim/manifest/canonical_v1_manifest.csv         per source x phase slice (committed)
  data/interim/manifest/canonical_v1_summary.csv          reconciliation per stream and in total (committed)
  data/interim/manifest/canonical_v1_file_manifest.csv    per raw sensor file (committed)
  data/interim/manifest/canonical_v1_content.json         deterministic content metadata (committed)
  data/interim/manifest/canonical_v1_build.json           runtime metadata of the last build (committed)
"""
from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.canonical import CANONICAL_SCHEMA, PROVENANCE_SCHEMA, build_stream, content_hash, extract_file  # noqa: E402
from src.data.duplicates import subject_device_groups  # noqa: E402
from src.data.io_guard import write_csv, write_json, write_parquet  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.raw_parser import parse_file  # noqa: E402
from src.data.subject_mapping import resolve_source, sources  # noqa: E402

CONFIG_FILES = ("canonical_v1.yaml", "paths.yaml", "subject_mapping.yaml")
DATASET_OF_ROLE = {"primary_candidate": "primary", "auxiliary": "auxiliary"}
_EPOCH = datetime(1970, 1, 1)


def iso(ts_value) -> str | None:
    if ts_value is None:
        return None
    if isinstance(ts_value, datetime):
        return ts_value.isoformat(sep=" ")
    return (_EPOCH + timedelta(seconds=int(ts_value))).isoformat(sep=" ")


def config_hash() -> str:
    h = hashlib.sha256()
    for name in CONFIG_FILES:
        h.update(name.encode() + b"\0" + (paths.CONFIG_DIR / name).read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def git_state() -> dict:
    run = lambda *a: subprocess.run(["git", *a], cwd=paths.PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")  # noqa: E731
    head = run("rev-parse", "HEAD").stdout.strip()
    dirty = bool(run("status", "--porcelain", "--untracked-files=no").stdout.strip())
    return {"git_commit": head or None, "git_dirty_tracked_files": dirty}


def columns(rows: list[dict], first: list[str]) -> list[str]:
    cols = list(first)
    for r in rows:
        cols += [k for k in r if k not in cols]
    return cols


def slice_table(t: pa.Table) -> dict[tuple, dict]:
    """Per (source, sensor phase, channel-quality phase): canonical rows, span, sessions, valid rows."""
    t2 = t.select(["source_id", "sensor_phase", "channel_quality_phase", "timestamp", "session_id",
                   "target_temp_valid", "target_humidity_valid", "pressure_valid", "pressure_upper_bound_channels"])
    t2 = t2.append_column("target_valid", pc.and_(t2["target_temp_valid"], t2["target_humidity_valid"]))
    t2 = t2.append_column("upper_bound_row", pc.greater(t2["pressure_upper_bound_channels"], 0))
    for c in ("source_id", "sensor_phase", "channel_quality_phase", "session_id"):
        t2 = t2.set_column(t2.schema.get_field_index(c), c, pc.cast(t2[c], pa.string()))
    g = t2.group_by(["source_id", "sensor_phase", "channel_quality_phase"]).aggregate([
        ("timestamp", "min"), ("timestamp", "max"), ("timestamp", "count"), ("session_id", "count_distinct"),
        ("target_valid", "sum"), ("pressure_valid", "sum"), ("upper_bound_row", "sum")])
    out = {}
    for r in g.to_pylist():
        out[(r["source_id"], r["sensor_phase"], r["channel_quality_phase"])] = r
    return out


def main() -> int:
    t_start = time.time()
    cfg = paths.load_config("canonical_v1.yaml")
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2

    eligible_groups = subject_device_groups(manifest, eligible_only=True)
    eligible_sources = set().union(*(g["sources"] for g in eligible_groups.values()))
    results = {"primary": [], "auxiliary": []}
    for key in sorted(eligible_groups):
        g = eligible_groups[key]
        if len(g["roles"]) != 1:
            print(f"ERROR: mixed roles in stream {key}: {g['roles']}", file=sys.stderr)
            return 3
        role = next(iter(g["roles"]))
        files = sorted((r for r in manifest if r["source_id"] in g["sources"] and r["is_sensor_data"] == "True"),
                       key=lambda r: r["source_relpath"])
        chunks = []
        for r in files:
            info = resolve_source(r["source_relpath"])
            pf = parse_file(root / r["source_relpath"], year_hint=info.year_hint)
            chunks.append(extract_file(r["file_id"], r["source_relpath"], r["source_id"], pf.rows, key[1]))
        res = build_stream(chunks, key[0], key[1], role, g["families"] == {"legacy_csv_ymd_hm"}, cfg)
        results[DATASET_OF_ROLE[role]].append(res)
        print(f"  {key[0]}|{key[1]:<8} {role:<17} raw={res.stats['rows_raw']:>9,} copies={res.stats['rows_copies_removed']:>7,} "
              f"canonical={res.stats['rows_canonical']:>9,} sessions={res.stats['sessions']}")

    # excluded / quarantined sensor files: row count only (no value is kept)
    not_loaded = []
    for s in sources():
        if s.source_id in eligible_sources:
            continue
        files = [r for r in manifest if r["source_id"] == s.source_id]
        sensor = [r for r in files if r["is_sensor_data"] == "True"]
        n_rows = sum(parse_file(root / r["source_relpath"], year_hint=s.year_hint).line_types["data"] for r in sensor)
        not_loaded.append({"source_id": s.source_id, "subject_id": s.subject_id, "device_id": s.device_id,
                           "role": s.dataset_role, "quality_status": s.quality_status, "files": len(files),
                           "sensor_files": len(sensor), "rows_raw": n_rows,
                           "status": {"excluded_invalid": "excluded", "quarantined": "quarantined"}.get(s.dataset_role, "not_sensor_data"),
                           "reason": s.exclusion_reason or s.dataset_role, "decision": s.exclusion_decision or
                           {"quarantined": "D-006", "restricted_metadata": "D-008"}.get(s.dataset_role, "")})

    # ---- reconciliation (build fails on any discrepancy) ---------------------------------------------
    errors = []
    all_res = results["primary"] + results["auxiliary"]
    for res in all_res:
        st = res.stats
        if not st["reconciles"]:
            errors.append(f"{st['subject_id']}|{st['device_id']}: raw - undated - copies != canonical")
        if st["rows_undated"]:
            errors.append(f"{st['subject_id']}|{st['device_id']}: {st['rows_undated']} rows without a timestamp")
        if st["rows_canonical"] != res.table.num_rows:
            errors.append(f"{st['subject_id']}|{st['device_id']}: table size mismatch")
        if int(pc.sum(pc.invert(res.provenance["is_canonical"])).as_py() or 0) != st["rows_copies_removed"]:
            errors.append(f"{st['subject_id']}|{st['device_id']}: provenance does not list every removed copy")
    excluded_ids = {r["source_id"] for r in not_loaded}
    for ds, lst in results.items():
        ids = pa.chunked_array([r.table["canonical_row_id"] for r in lst]) if lst else pa.chunked_array([], pa.string())
        if len(ids) != pc.count_distinct(ids).as_py():
            errors.append(f"{ds}: canonical_row_id not unique")
        values = lambda col: {v for r in lst for v in pc.unique(pc.cast(r.table[col], pa.string())).to_pylist()}  # noqa: E731
        src_ids = values("source_id")
        if src_ids & excluded_ids:
            errors.append(f"{ds}: contains excluded/quarantined sources {src_ids & excluded_ids}")
        roles = values("dataset_role")
        if roles - {"primary_candidate" if ds == "primary" else "auxiliary"}:
            errors.append(f"{ds}: unexpected roles {roles}")
    total_sensor_rows = sum(r.stats["rows_raw"] for r in all_res) + sum(r["rows_raw"] for r in not_loaded)
    accounted = [f["file_id"] for r in all_res for f in r.stats["files"]]
    accounted += [x["file_id"] for x in manifest if x["is_sensor_data"] == "True" and x["source_id"] in excluded_ids]
    expected = sorted(x["file_id"] for x in manifest if x["is_sensor_data"] == "True")
    if sorted(accounted) != expected:
        errors.append("not every raw sensor file is accounted for exactly once")
    if errors:
        print("ERROR: reconciliation failed; nothing written:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 3

    # ---- write ---------------------------------------------------------------------------------------
    out_dir, man_dir = paths.repo_path(cfg["output_dir"]), paths.repo_path(cfg["manifest_dir"])
    written = {}
    for ds in ("primary", "auxiliary"):
        p = write_parquet(out_dir / f"{ds}.parquet", [r.table for r in results[ds]], CANONICAL_SCHEMA)
        written[ds] = p
    p = write_parquet(out_dir / "duplicate_provenance.parquet", [r.provenance for r in all_res], PROVENANCE_SCHEMA)
    written["duplicate_provenance"] = p

    man_rows, sum_rows, file_rows = [], [], []
    for ds in ("primary", "auxiliary"):
        for res in results[ds]:
            st = res.stats
            agg = slice_table(res.table)
            for (src, sp, cq), cnt in sorted(st["slices"].items()):
                a = agg.get((src, sp, cq), {})
                info = next(s for s in sources() if s.source_id == src)
                man_rows.append({
                    "dataset_version": cfg["dataset_version"], "dataset_file": ds, "subject_id": st["subject_id"],
                    "source_id": src, "device_id": st["device_id"], "role": info.dataset_role, "quality_status": info.quality_status,
                    "sensor_phase": sp, "channel_quality_phase": cq,
                    "rows_raw": cnt["rows_raw_dated"], "rows_copies_removed": cnt["rows_copies_removed"],
                    "rows_canonical": a.get("timestamp_count", 0), "sessions": a.get("session_id_count_distinct", 0),
                    "first_timestamp": iso(a.get("timestamp_min")), "last_timestamp": iso(a.get("timestamp_max")),
                    "target_valid_rows": a.get("target_valid_sum", 0), "pressure_valid_rows": a.get("pressure_valid_sum", 0),
                    "pressure_upper_bound_rows": a.get("upper_bound_row_sum", 0), "status": "included"})
                if cnt["rows_raw_dated"] - cnt["rows_copies_removed"] != a.get("timestamp_count", 0):
                    print(f"ERROR: slice reconciliation failed for {src}/{sp}/{cq}", file=sys.stderr)
                    return 3
            sum_rows.append({"dataset_file": ds, **{k: v for k, v in st.items() if k not in ("slices", "files", "target_flag_counts")},
                             **{f"target_flag_{k}": v for k, v in st["target_flag_counts"].items()}})
            file_rows += [{"dataset_file": ds, **f} for f in st["files"]]
    for r in not_loaded:
        man_rows.append({"dataset_version": cfg["dataset_version"], "dataset_file": "none", "subject_id": r["subject_id"],
                         "source_id": r["source_id"], "device_id": r["device_id"], "role": r["role"],
                         "quality_status": r["quality_status"], "sensor_phase": "not_loaded", "channel_quality_phase": "not_loaded",
                         "rows_raw": r["rows_raw"], "rows_copies_removed": 0, "rows_canonical": 0, "sessions": 0,
                         "status": r["status"], "status_reason": r["reason"], "status_decision": r["decision"]})
        sum_rows.append({"dataset_file": "none", "subject_id": r["subject_id"], "device_id": r["device_id"],
                         "role": r["role"], "files": r["sensor_files"], "rows_raw": r["rows_raw"], "rows_canonical": 0,
                         "status": r["status"]})
        for f in (x for x in manifest if x["source_id"] == r["source_id"] and x["is_sensor_data"] == "True"):
            file_rows.append({"dataset_file": "none", "file_id": f["file_id"], "source_relpath": f["source_relpath"],
                              "source_id": f["source_id"], "rows_canonical": 0, "status": r["status"]})
    tot = {ds: sum(r.stats["rows_canonical"] for r in results[ds]) for ds in results}
    copies = {ds: sum(r.stats["rows_copies_removed"] for r in results[ds]) for ds in results}
    raw = {ds: sum(r.stats["rows_raw"] for r in results[ds]) for ds in results}
    excl = sum(r["rows_raw"] for r in not_loaded if r["status"] == "excluded")
    quar = sum(r["rows_raw"] for r in not_loaded if r["status"] == "quarantined")
    sum_rows.append({"dataset_file": "TOTAL", "status": "equation",
                     "rows_raw": total_sensor_rows,
                     "detail": (f"{total_sensor_rows} raw sensor rows - {excl} excluded - {quar} quarantined - "
                                f"{raw['auxiliary']} auxiliary (kept apart) - {copies['primary']} primary copies = "
                                f"{tot['primary']} primary canonical rows; auxiliary: {raw['auxiliary']} - {copies['auxiliary']} = "
                                f"{tot['auxiliary']}"),
                     "rows_canonical": tot["primary"] + tot["auxiliary"]})
    if total_sensor_rows - excl - quar - raw["auxiliary"] - copies["primary"] != tot["primary"]:
        print("ERROR: total equation failed", file=sys.stderr)
        return 3

    write_csv(man_dir / "canonical_v1_manifest.csv", man_rows, columns(man_rows, [
        "dataset_version", "dataset_file", "subject_id", "source_id", "device_id", "role", "quality_status",
        "sensor_phase", "channel_quality_phase", "rows_raw", "rows_copies_removed", "rows_canonical", "sessions",
        "first_timestamp", "last_timestamp", "target_valid_rows", "pressure_valid_rows", "status"]))
    write_csv(man_dir / "canonical_v1_summary.csv", sum_rows, columns(sum_rows, ["dataset_file", "subject_id", "device_id", "role"]))
    write_csv(man_dir / "canonical_v1_file_manifest.csv", file_rows, columns(file_rows, ["dataset_file", "file_id", "source_relpath"]))

    content = {
        "dataset_version": cfg["dataset_version"], "schema_version": cfg["schema_version"],
        "config_hash_sha256": config_hash(), "raw_manifest_sha256": sha256_file(mpath),
        "canonical_schema": [f"{f.name}:{f.type}" for f in CANONICAL_SCHEMA],
        "provenance_schema": [f"{f.name}:{f.type}" for f in PROVENANCE_SCHEMA],
        "datasets": {ds: {"rows": tot[ds], "streams": len(results[ds]),
                          "content_sha256": content_hash([r.table for r in results[ds]])} for ds in results},
        "duplicate_provenance": {"rows": sum(r.provenance.num_rows for r in all_res),
                                 "content_sha256": content_hash([r.provenance for r in all_res])},
        "reconciliation": {"raw_sensor_rows_total": total_sensor_rows, "excluded_rows": excl, "quarantined_rows": quar,
                           "auxiliary_raw_rows": raw["auxiliary"], "primary_raw_rows": raw["primary"],
                           "primary_copies_removed": copies["primary"], "primary_canonical_rows": tot["primary"],
                           "auxiliary_canonical_rows": tot["auxiliary"]},
    }
    write_json(man_dir / "canonical_v1_content.json", content)
    write_json(man_dir / "canonical_v1_build.json", {
        "build_timestamp": datetime.now().isoformat(timespec="seconds"), **git_state(),
        "python": platform.python_version(), "numpy": np.__version__, "pyarrow": pa.__version__,
        "files": {k: {"path": str(v.relative_to(paths.PROJECT_ROOT).as_posix()), "bytes": v.stat().st_size,
                      "sha256": sha256_file(v)} for k, v in written.items()},
        "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"canonical_v1 built in {time.time() - t_start:.0f} s: primary {tot['primary']:,} rows, auxiliary {tot['auxiliary']:,} rows; "
          f"content {content['datasets']['primary']['content_sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
