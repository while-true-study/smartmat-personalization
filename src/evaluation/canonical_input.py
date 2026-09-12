"""Canonical-only input for P1 and later analyses (D-028).

From P1 on, analyses read `data/interim/canonical_v1/` only, never raw (DATA_POLICY §4.1). This module:
- refuses any path outside the canonical dataset directory or inside a protected raw root;
- verifies the Parquet files against the SHA-256 recorded in `canonical_v1_build.json` before use;
- loads the primary file only and checks it holds primary-candidate rows and no excluded source.

P1 modules must not import raw-access functions; `RAW_ACCESS_TOKENS` lists the identifiers that
`tests/test_domain_shift.py` rejects in P1 code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

from src.data import paths
from src.data.io_guard import is_protected
from src.data.subject_mapping import excluded_sources

RAW_ACCESS_TOKENS = ("raw_root", "raw_package_root", "read_bytes", "parse_file", "parse_text", "load_sources",
                     "verify_raw_integrity", "iter_raw_files", "build_records")


class CanonicalInputError(RuntimeError):
    """Raised when an analysis input is not the verified canonical dataset."""


def canonical_config() -> dict:
    return paths.load_config("canonical_v1.yaml")


def canonical_dir() -> Path:
    return paths.repo_path(canonical_config()["output_dir"])


def manifest_dir() -> Path:
    return paths.repo_path(canonical_config()["manifest_dir"])


def assert_canonical_path(path: str | Path) -> Path:
    """Only files inside the canonical dataset directory are accepted; raw roots never are."""
    p = Path(path).resolve()
    if is_protected(p):
        raise CanonicalInputError(f"refusing raw path as analysis input: {p.name}")
    root = canonical_dir().resolve()
    if p != root and root not in p.parents:
        raise CanonicalInputError(f"analysis input must come from {canonical_config()['output_dir']}: {p.name}")
    return p


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_canonical() -> dict:
    """Check every canonical Parquet file against the build record; returns the verified hashes."""
    build = json.loads((manifest_dir() / "canonical_v1_build.json").read_text(encoding="utf-8"))
    content = json.loads((manifest_dir() / "canonical_v1_content.json").read_text(encoding="utf-8"))
    out = {"dataset_version": content["dataset_version"], "schema_version": content["schema_version"],
           "content_sha256": {k: v["content_sha256"] for k, v in content["datasets"].items()},
           "config_hash_sha256": content["config_hash_sha256"], "raw_manifest_sha256": content["raw_manifest_sha256"],
           "files": {}}
    for name, rec in build["files"].items():
        p = assert_canonical_path(paths.PROJECT_ROOT / rec["path"])
        if not p.exists():
            raise CanonicalInputError(f"canonical file missing: {rec['path']}")
        actual = file_sha256(p)
        if actual != rec["sha256"]:
            raise CanonicalInputError(f"canonical file changed since the build: {rec['path']}")
        out["files"][name] = actual
    return out


def load_primary(columns: Sequence[str]):
    """Primary canonical rows (D-023). Auxiliary and excluded sources are never returned."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    p = assert_canonical_path(canonical_dir() / "primary.parquet")
    cols = list(dict.fromkeys(list(columns) + ["dataset_role", "source_id"]))
    t = pq.read_table(p, columns=cols)
    roles = set(pc.unique(t["dataset_role"].cast("string")).to_pylist())
    if roles != {"primary_candidate"}:
        raise CanonicalInputError(f"primary file holds unexpected roles: {roles}")
    bad = set(pc.unique(t["source_id"].cast("string")).to_pylist()) & {e["source_id"] for e in excluded_sources()}
    if bad:
        raise CanonicalInputError(f"excluded sources in primary file: {bad}")
    return t
