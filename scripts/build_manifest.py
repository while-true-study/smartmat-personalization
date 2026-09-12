"""Build the file-level raw manifest (P0). Read-only on raw data.

Usage:
    python scripts/build_manifest.py                 # create, or verify-and-refresh
    python scripts/build_manifest.py --accept-added  # new raw files were delivered (log it in docs/DECISIONS.md)

If a manifest already exists, the script refuses to continue when any previously
recorded raw file was modified or removed. That is a data-integrity incident, not
something to overwrite.
"""
from __future__ import annotations

import argparse
import platform
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.data.manifest import (  # noqa: E402
    MANIFEST_COLUMNS, build_records, compare_manifests, find_duplicate_groups, read_manifest, sha256_file,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accept-added", action="store_true", help="accept raw files not in the existing manifest")
    args = ap.parse_args()

    root = paths.raw_root()
    if not root.is_dir():
        print(f"ERROR: raw_root not found: {root} (configs/paths.yaml)", file=sys.stderr)
        return 1

    records = build_records(root)
    out = paths.manifest_path()

    if out.exists():
        diff = compare_manifests(read_manifest(out), records)
        if diff["modified"] or diff["removed"]:
            report = paths.audit_output_dir().parent / "raw_integrity_violation.json"
            write_json(report, {"detected_at": datetime.now().isoformat(timespec="seconds"), **diff})
            print(f"ERROR: raw files modified/removed since last manifest. Details: {report}", file=sys.stderr)
            print("Do NOT regenerate the manifest; investigate and record in docs/DECISIONS.md.", file=sys.stderr)
            return 2
        if diff["added"] and not args.accept_added:
            print(f"ERROR: {len(diff['added'])} raw files not in the existing manifest:", file=sys.stderr)
            for p in diff["added"][:20]:
                print(f"  + {p}", file=sys.stderr)
            print("Record the delivery in docs/DECISIONS.md, then re-run with --accept-added.", file=sys.stderr)
            return 3

    write_csv(out, records, MANIFEST_COLUMNS)

    pkg = paths.raw_package_root()
    package_files = {
        p.relative_to(pkg).as_posix(): sha256_file(p)
        for p in sorted(pkg.iterdir()) if p.is_file()
    }
    package_files.update({
        p.relative_to(pkg).as_posix(): sha256_file(p)
        for p in sorted((pkg / "metadata").glob("*")) if p.is_file()
    } if (pkg / "metadata").is_dir() else {})

    dup = find_duplicate_groups(records)
    write_json(out.with_suffix(".meta.json"), {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"],
        "n_files": len(records),
        "n_sensor_files": sum(r["is_sensor_data"] for r in records),
        "total_bytes": sum(r["size_bytes"] for r in records),
        "byte_duplicate_groups": dup,
        "package_level_files_sha256": package_files,
        "python": platform.python_version(),
    })

    print(f"manifest: {out.relative_to(paths.PROJECT_ROOT)}  files={len(records)}  byte-duplicate groups={len(dup)}")
    by_source: dict[str, int] = {}
    for r in records:
        by_source[r["source_id"]] = by_source.get(r["source_id"], 0) + 1
    for k, v in by_source.items():
        print(f"  {k:<36} {v:>4}")
    flagged = [r for r in records if r["flags"]]
    if flagged:
        print(f"flagged files: {len(flagged)}")
        for r in flagged:
            print(f"  [{r['flags']}] {r['source_relpath']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
