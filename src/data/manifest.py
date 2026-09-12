"""File-level raw manifest: provenance, checksums and duplicate detection.

The manifest is the provenance anchor for every downstream artifact: each derived row
must be traceable to (file_id, source_relpath, sha256, subject_id, device_id).
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from src.data.io_guard import read_bytes
from src.data.subject_mapping import resolve_file

MANIFEST_COLUMNS = [
    "file_id", "source_relpath", "file_name", "extension", "size_bytes", "sha256",
    "source_id", "subject_id", "device_id", "device_id_filename", "device_status",
    "dataset_role", "format_family", "is_sensor_data", "filename_annotation",
    "byte_duplicate_group", "flags",
]

SENSOR_EXTENSIONS = {".txt", ".csv"}
_RE_HANGUL = re.compile(r"[가-힣][가-힣0-9\s]*[가-힣]|[가-힣]")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(read_bytes(path))


def file_id_for(relpath: str) -> str:
    """Stable, path-derived ID (unchanged if file content is re-checked)."""
    return "rf_" + hashlib.sha1(relpath.encode("utf-8")).hexdigest()[:10]


def filename_annotation(file_name: str) -> str:
    """Free-text notes embedded in raw filenames by the data provider (e.g. '누락부분있음')."""
    stem = Path(file_name).stem
    return " ".join(m.group(0).strip() for m in _RE_HANGUL.finditer(stem))


def iter_raw_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p


def build_records(root: Path) -> list[dict]:
    records = []
    for p in iter_raw_files(root):
        rel = p.relative_to(root).as_posix()
        prov = resolve_file(rel)
        data = read_bytes(p)
        records.append({
            "file_id": file_id_for(rel),
            "source_relpath": rel,
            "file_name": p.name,
            "extension": p.suffix.lower(),
            "size_bytes": len(data),
            "sha256": sha256_bytes(data),
            "source_id": prov.source.source_id,
            "subject_id": prov.subject_id,
            "device_id": prov.device_id,
            "device_id_filename": prov.device_id_filename,
            "device_status": prov.device_status,
            "dataset_role": prov.source.dataset_role,
            "format_family": prov.source.format_family,
            "is_sensor_data": p.suffix.lower() in SENSOR_EXTENSIONS,
            "filename_annotation": filename_annotation(p.name),
            "byte_duplicate_group": "",
            "flags": "|".join(prov.flags),
        })
    assign_duplicate_groups(records)
    return records


def find_duplicate_groups(records: Iterable[dict], key: str = "sha256") -> dict[str, list[str]]:
    """Group files whose `key` value is identical. Returns only groups with >1 member."""
    groups: dict[str, list[str]] = defaultdict(list)
    for r in records:
        groups[r[key]].append(r["source_relpath"])
    return {k: sorted(v) for k, v in groups.items() if len(v) > 1}


def assign_duplicate_groups(records: list[dict]) -> None:
    groups = find_duplicate_groups(records)
    for r in records:
        if r["sha256"] in groups:
            r["byte_duplicate_group"] = "dup_" + r["sha256"][:10]
            r["flags"] = "|".join(filter(None, [r["flags"], "byte_duplicate"]))


def read_manifest(path: str | Path) -> list[dict]:
    import csv

    with open(path, "r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def verify_raw_integrity(root: Path, manifest_rows: list[dict]) -> dict[str, list[str]]:
    """Compare raw files on disk with the manifest. All lists empty means raw is intact."""
    listed = {r["source_relpath"]: r["sha256"] for r in manifest_rows}
    on_disk = {p.relative_to(root).as_posix() for p in iter_raw_files(root)}
    return {
        "changed": sorted(p for p in listed.keys() & on_disk if sha256_file(root / p) != listed[p]),
        "missing": sorted(listed.keys() - on_disk),
        "unlisted": sorted(on_disk - listed.keys()),
    }


def compare_manifests(old: list[dict], new: list[dict]) -> dict[str, list[str]]:
    """Detect raw changes between two manifests (same raw_root)."""
    o = {r["source_relpath"]: r["sha256"] for r in old}
    n = {r["source_relpath"]: r["sha256"] for r in new}
    return {
        "modified": sorted(p for p in o.keys() & n.keys() if o[p] != n[p]),
        "removed": sorted(o.keys() - n.keys()),
        "added": sorted(n.keys() - o.keys()),
    }
