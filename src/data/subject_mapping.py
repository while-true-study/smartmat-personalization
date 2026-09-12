"""Resolve a raw file path to subject / device / source provenance.

The mapping itself lives in configs/subject_mapping.yaml; policy in docs/DATA_POLICY.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import PurePosixPath
from typing import Any

from src.data.paths import load_config

UNKNOWN_DEVICE_VALUES = {"unknown", "unresolved", "not_applicable"}


@dataclass(frozen=True)
class SourceInfo:
    source_id: str
    raw_subdir: str
    subject_id: str
    device_id: str
    dataset_role: str
    format_family: str
    year_hint: int | None = None
    device_id_candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileProvenance:
    source_relpath: str
    source: SourceInfo
    subject_id: str
    device_id: str
    device_id_filename: str
    device_status: str  # ok | unknown | not_applicable | prefix_mismatch
    flags: tuple[str, ...] = field(default_factory=tuple)


@lru_cache(maxsize=1)
def mapping_config() -> dict[str, Any]:
    return load_config("subject_mapping.yaml")


def subject_ids() -> set[str]:
    return set(mapping_config()["subjects"])


def device_subject_map() -> dict[str, str]:
    return {str(k): v for k, v in mapping_config()["device_subject_map"].items()}


def subject_for_device(device_id: str | int) -> str:
    dev = str(device_id)
    mapping = device_subject_map()
    if dev not in mapping:
        raise KeyError(f"Unknown device_id {dev!r}; add it to configs/subject_mapping.yaml first")
    return mapping[dev]


@lru_cache(maxsize=1)
def sources() -> tuple[SourceInfo, ...]:
    out = []
    for s in mapping_config()["sources"]:
        out.append(
            SourceInfo(
                source_id=s["source_id"],
                raw_subdir=s["raw_subdir"].strip("/"),
                subject_id=s["subject_id"],
                device_id=str(s["device_id"]),
                dataset_role=s["dataset_role"],
                format_family=s["format_family"],
                year_hint=s.get("year_hint"),
                device_id_candidates=tuple(str(d) for d in s.get("device_id_candidates", [])),
            )
        )
    return tuple(out)


def to_relpath(path_like: str) -> str:
    return str(PurePosixPath(str(path_like).replace("\\", "/"))).strip("/")


def resolve_source(relpath: str) -> SourceInfo:
    """Longest raw_subdir prefix match. Raises if the file belongs to no configured source."""
    rel = to_relpath(relpath)
    best: SourceInfo | None = None
    for s in sources():
        if rel == s.raw_subdir or rel.startswith(s.raw_subdir + "/"):
            if best is None or len(s.raw_subdir) > len(best.raw_subdir):
                best = s
    if best is None:
        raise KeyError(f"No source in configs/subject_mapping.yaml covers {rel!r}")
    return best


def device_from_filename(file_name: str) -> str:
    for pat in mapping_config().get("filename_device_patterns", []):
        m = re.match(pat, file_name)
        if m:
            return m.group("device_id")
    return ""


def resolve_file(relpath: str) -> FileProvenance:
    rel = to_relpath(relpath)
    src = resolve_source(rel)
    fname = PurePosixPath(rel).name
    dev_fn = device_from_filename(fname)
    flags: list[str] = []

    if dev_fn:
        # A device ID found in a filename must belong to a known device of the same subject.
        if subject_for_device(dev_fn) != src.subject_id:
            raise ValueError(f"{rel}: filename device {dev_fn} maps to another subject than {src.subject_id}")

    if src.device_id == "unresolved":
        device_id, status = "unresolved", "prefix_mismatch"
        flags.append("device_prefix_mismatch")
    elif src.device_id in UNKNOWN_DEVICE_VALUES:
        device_id, status = src.device_id, src.device_id
    else:
        device_id, status = src.device_id, "ok"
        if subject_for_device(device_id) != src.subject_id:
            raise ValueError(f"{rel}: device {device_id} is not mapped to {src.subject_id}")
        if dev_fn and dev_fn != device_id:
            status = "prefix_mismatch"
            flags.append("device_prefix_mismatch")

    return FileProvenance(
        source_relpath=rel,
        source=src,
        subject_id=src.subject_id,
        device_id=device_id,
        device_id_filename=dev_fn,
        device_status=status,
        flags=tuple(flags),
    )
