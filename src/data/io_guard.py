"""The only module allowed to open files for writing.

Every write in src/ and scripts/ must go through this module so that raw data
(configs/paths.yaml: protected_roots) can never be modified, deleted or overwritten.
tests/test_no_raw_modification.py enforces this statically.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.data.paths import protected_roots


class RawWriteError(PermissionError):
    """Raised when code attempts to write inside a protected raw-data root."""


def _norm(path: Path) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def is_protected(path: str | Path) -> bool:
    target = _norm(Path(path))
    for root in protected_roots():
        r = _norm(root)
        if target == r or target.startswith(r + os.sep):
            return True
    return False


def assert_writable(path: str | Path) -> Path:
    p = Path(path).resolve()
    if is_protected(p):
        raise RawWriteError(f"Refusing to write inside protected raw-data root: {p}")
    return p


def open_for_write(path: str | Path, mode: str = "w", **kwargs: Any):
    if not any(c in mode for c in "wax+"):
        raise ValueError(f"open_for_write needs a write mode, got {mode!r}")
    p = assert_writable(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if "b" not in mode:
        kwargs.setdefault("encoding", "utf-8")
    return open(p, mode, **kwargs)


def write_text(path: str | Path, text: str) -> Path:
    with open_for_write(path, "w", newline="\n") as fh:
        fh.write(text)
    return Path(path)


def write_json(path: str | Path, obj: Any) -> Path:
    return write_text(path, json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n")


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], columns: Sequence[str]) -> Path:
    with open_for_write(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns), extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return Path(path)


def write_parquet(path: str | Path, tables: Iterable[Any], schema: Any) -> Path:
    """Write pyarrow tables (same schema) as one Parquet file, one row group per table."""
    import pyarrow.parquet as pq

    with open_for_write(path, "wb") as fh:
        writer = pq.ParquetWriter(fh, schema, compression="zstd", use_dictionary=True)
        try:
            for t in tables:
                writer.write_table(t)
        finally:
            writer.close()
    return Path(path)


def read_bytes(path: str | Path) -> bytes:
    """Read-only access; the only way raw files are opened."""
    with open(path, "rb") as fh:
        return fh.read()
