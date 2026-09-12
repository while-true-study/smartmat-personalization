"""P0 analysis A5 — cross-file duplicate and temporal-overlap audit. Read-only on raw data.

Groups rows by (subject_id, device_id) from configs/subject_mapping.yaml and, inside each group,
separates exact duplicates, metadata-only differences, conflicting timestamps, repeated sequences
and pure time overlaps (src/data/duplicates.py). Duplicate-removal policies are only simulated as
row counts: no row is removed and no interim dataset is produced.

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/duplicates/:
  duplicate_summary.csv         one row per subject/device group
  file_ranges.csv               per file: time range, rows, chunks, internal gaps
  overlapping_file_pairs.csv    every file pair whose time ranges intersect
  duplicate_sequences.csv       contiguous repeated blocks (>= 10 rows) between file pairs and within one file
  timestamp_conflicts.csv       one row per timestamp with different sensor/target values
  metadata_only_differences.csv event-text pairs among otherwise identical rows
  dedup_policy_impact.csv       hypothetical row counts per policy
  file_boundaries.csv           consecutive-file boundaries: overlap / gap bins
  repeated_chunk_keys.csv       JSON upload-chunk keys stored in more than one file
  cross_device_diagnostic.csv   User02 device-to-device equality (diagnostic only)
  duplicates_run_meta.json      parameters, manifest checksum, integrity result

Usage:
    python scripts/audit_cross_file_duplicates.py
"""
from __future__ import annotations

import gc
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.duplicates import (  # noqa: E402
    cross_device_equality, duplicate_counts, file_boundaries, file_ranges, metadata_only_differences,
    overlapping_file_pairs, policy_impact, repeated_chunk_keys, repeated_sequences, row_keys, subject_device_groups,
    timestamp_conflicts, within_file_repeated_blocks,
)
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.provenance import SourceData, load_sources  # noqa: E402

MIN_SEQUENCE_ROWS = 10
PRIMARY_SUBJECTS = {"User01", "User02", "User07"}   # provisional primary cohort (D-013)
_EPOCH = datetime(1970, 1, 1)


def iso(sec) -> str:
    return "" if sec in (None, "") else (_EPOCH + timedelta(seconds=int(sec))).isoformat(sep=" ")


def merged_hours(intervals: list[tuple[int, int]]) -> float:
    total, cur = 0, None
    for s, e in sorted(intervals):
        if cur is None or s > cur[1]:
            if cur:
                total += cur[1] - cur[0]
            cur = [s, e]
        else:
            cur[1] = max(cur[1], e)
    if cur:
        total += cur[1] - cur[0]
    return total / 3600.0


def columns(rows: list[dict], preferred: list[str] | None = None) -> list[str]:
    cols = list(preferred or [])
    for r in rows:
        for k in r:
            if k not in cols and not k.startswith("_"):
                cols.append(k)
    return cols


def main() -> int:
    t_start = time.time()
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2

    groups = subject_device_groups(manifest)

    summary, ranges_out, pairs_out, seqs_out, conf_out, meta_out, pol_out = [], [], [], [], [], [], []
    bnd_out, chunk_out = [], []
    device_streams: dict[str, tuple[SourceData, object]] = {}

    for (subject, device), g in sorted(groups.items()):
        label = f"{subject}|{device}"
        minute_res = g["families"] == {"legacy_csv_ymd_hm"}
        primary = subject in PRIMARY_SUBJECTS and g["roles"] == {"primary_candidate"}
        loaded = load_sources(root, manifest, g["sources"])
        src = SourceData.concat([loaded[s] for s in sorted(loaded)], "+".join(sorted(loaded)), subject, device)
        keys = row_keys(src)
        counts = duplicate_counts(src, keys)
        fr = file_ranges(src)
        pairs = overlapping_file_pairs(src, keys)
        seqs = repeated_sequences(src, keys, pairs, MIN_SEQUENCE_ROWS)
        inner = within_file_repeated_blocks(src, keys, MIN_SEQUENCE_ROWS) if not minute_res else []
        conf = [] if minute_res else timestamp_conflicts(src, keys)
        meta = metadata_only_differences(src, keys)
        bnd = file_boundaries(src, pairs)
        chunks = repeated_chunk_keys(src, keys)

        rel = Counter(p["relation"] for p in pairs)
        kinds = Counter(c["kind"] for c in conf)
        longest = max(seqs, key=lambda s: s["matched_rows"], default=None)
        summary.append({
            "group": label, "subject_id": subject, "device_id": device, "sources": ",".join(sorted(g["sources"])),
            "dataset_roles": ",".join(sorted(g["roles"])), "primary_candidate": primary,
            "timestamp_resolution": "minute" if minute_res else "second", "files": len(src.files), **counts,
            "overlapping_file_pairs": len(pairs), "pairs_duplicate_block": rel.get("duplicate_block", 0),
            "pairs_partial_duplicate": rel.get("partial_duplicate", 0), "pairs_time_overlap_only": rel.get("time_overlap_only", 0),
            "repeated_sequences": len(seqs), "rows_in_repeated_sequences": int(sum(s["matched_rows"] for s in seqs)),
            "longest_sequence_rows": longest["matched_rows"] if longest else 0,
            "longest_sequence_h": longest["duration_h"] if longest else 0,
            "longest_sequence_files": f"{longest['file_a']} -> {longest['file_b']}" if longest else "",
            "duplicated_recording_h": round(merged_hours([(s["first_matching_ts"], s["last_matching_ts"]) for s in seqs + inner]), 3),
            "within_file_repeated_blocks": len(inner), "rows_in_within_file_blocks": int(sum(s["matched_rows"] for s in inner)),
            "conflicts_sensor": kinds.get("sensor_conflict", 0), "conflicts_target": kinds.get("target_conflict", 0),
            "conflicts_sensor_and_target": kinds.get("sensor_and_target_conflict", 0),
            "conflicts_within_file": sum(c["origin"] == "within_file" for c in conf),
            "conflicts_within_file_adjacent": sum(c["origin"] == "within_file" and c["adjacent_lines"] for c in conf),
            "conflicts_within_file_copied_to_other_file": sum(c["origin"] == "within_file" and not c["same_file"] for c in conf),
            "conflicts_between_files": sum(c["origin"] == "between_files" for c in conf),
            "conflicts_with_th_sentinel": sum(c["involves_th_sentinel"] for c in conf),
            "conflicts_with_control_event": sum(c["involves_control_event"] for c in conf),
            "repeated_chunk_keys": len(chunks),
            "repeated_chunk_keys_identical": sum(c["relation"] == "identical" for c in chunks),
            "boundaries": len(bnd), "boundaries_overlap_repeated": sum(b["boundary_kind"] == "overlap_with_repeated_rows" for b in bnd),
            "boundaries_overlap_distinct": sum(b["boundary_kind"] == "overlap_distinct_rows" for b in bnd),
            "files_with_internal_gap_gt_2h": sum(f.get("internal_gaps_gt_2h", 0) > 0 for f in fr),
        })
        for f in fr:
            ranges_out.append({"group": label, **{k: (iso(v) if k in ("first_ts", "last_ts") else v) for k, v in f.items()}})
        for p in pairs:
            pairs_out.append({"group": label, **{k: (iso(v) if k in ("overlap_start", "overlap_end") else v)
                                                  for k, v in p.items() if not k.startswith("_")}})
        for s in seqs + inner:
            seqs_out.append({"group": label, **{k: (iso(v) if k.endswith("_ts") else v) for k, v in s.items()}})
        for c in conf:
            conf_out.append({"group": label, **{k: (iso(v) if k == "ts" else
                                                     (_EPOCH + timedelta(days=v)).date().isoformat() if k == "date" else v)
                                                 for k, v in c.items()}})
        meta_out += [{"group": label, **m} for m in meta]
        pol_out += [{"group": label, "primary_candidate": primary,
                     "timestamp_resolution": "minute" if minute_res else "second", **p}
                    for p in policy_impact(counts, minute_res)]
        bnd_out += [{"group": label, **b} for b in bnd]
        chunk_out += [{"group": label, **c} for c in chunks]
        if subject == "User02" and device in {"22480", "22482", "unresolved"}:
            device_streams[device] = (src, keys)
        else:
            del src, keys
        del loaded
        gc.collect()
        print(f"  {label:<20} rows={counts['raw_rows']:>9,} exact_dup={counts['exact_duplicate_rows']:>7,} "
              f"conflicting_ts={counts['conflicting_timestamps']:>6,} pairs={len(pairs):>3} seqs={len(seqs):>3}")

    cross = [cross_device_equality(*device_streams[a], *device_streams[b])
             for a, b in combinations(sorted(device_streams), 2)]

    # policy totals: provisional primary cohort (second-resolution groups) and all second-resolution groups
    for scope, sel in (("TOTAL_primary_second_resolution",
                        lambda r: r["primary_candidate"] and r["timestamp_resolution"] == "second"),
                       ("TOTAL_all_second_resolution", lambda r: r["timestamp_resolution"] == "second")):
        for pol in dict.fromkeys(r["policy"] for r in pol_out):
            rows = [r for r in pol_out if r["policy"] == pol and not r["group"].startswith("TOTAL") and sel(r)]
            raw = sum(r["raw_rows"] for r in rows)
            kept = sum(r["rows_after"] for r in rows)
            unresolved = sum(int(r["unresolved_items"] or 0) for r in rows)
            pol_out.append({"group": scope, "primary_candidate": "", "timestamp_resolution": "second",
                            "policy": pol, "raw_rows": raw, "rows_after": kept,
                            "rows_removed": raw - kept, "pct_removed": round(100 * (raw - kept) / raw, 4) if raw else None,
                            "unresolved_items": unresolved, "status": "aggregate", "description": ""})

    out = paths.p0_output_dir("duplicates")
    write_csv(out / "duplicate_summary.csv", summary, columns(summary))
    write_csv(out / "file_ranges.csv", ranges_out, columns(ranges_out))
    write_csv(out / "overlapping_file_pairs.csv", pairs_out, columns(pairs_out))
    write_csv(out / "duplicate_sequences.csv", seqs_out, columns(seqs_out, ["group", "file_a", "file_b"]))
    write_csv(out / "timestamp_conflicts.csv", conf_out, columns(conf_out, ["group", "ts", "date", "kind"]))
    write_csv(out / "metadata_only_differences.csv", meta_out, ["group", "event_a", "event_b", "count"])
    write_csv(out / "dedup_policy_impact.csv", pol_out, columns(pol_out))
    write_csv(out / "file_boundaries.csv", bnd_out, columns(bnd_out))
    write_csv(out / "repeated_chunk_keys.csv", chunk_out, ["group", "chunk_key", "n_files", "files", "rows_per_copy", "relation"])
    write_csv(out / "cross_device_diagnostic.csv", cross, columns(cross))
    write_json(out / "duplicates_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"], "manifest_sha256": sha256_file(mpath),
        "raw_integrity": {k: len(v) for k, v in integrity.items()},
        "parameters": {"min_sequence_rows": MIN_SEQUENCE_ROWS, "duplicate_block_rule": ">=95% of rows in overlap shared",
                       "groups": sorted(f"{s}|{d}" for s, d in groups)},
        "python": platform.python_version(), "numpy": np.__version__, "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"A5 done in {time.time() - t_start:.0f} s -> {out.relative_to(paths.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
