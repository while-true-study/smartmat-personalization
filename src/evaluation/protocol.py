"""Frozen evaluation protocol v1.0 (configs/experiments/v1.0/protocol.yaml; docs/EXPERIMENT_PROTOCOL.md)."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from src.data import paths
from src.evaluation.windowing import WindowSpec

PROTOCOL_VERSION = "v1.0"
PROTOCOL_PATH = Path("configs") / "experiments" / PROTOCOL_VERSION / "protocol.yaml"


def protocol_file() -> Path:
    return paths.PROJECT_ROOT / PROTOCOL_PATH


@lru_cache(maxsize=1)
def load_protocol() -> dict:
    cfg = yaml.safe_load(protocol_file().read_text(encoding="utf-8"))
    if cfg.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError(f"protocol file is not {PROTOCOL_VERSION}")
    return cfg


def protocol_sha256() -> str:
    """Hash of the protocol file with line endings normalised (checkout-independent)."""
    text = protocol_file().read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(text).hexdigest()


def window_spec(duration_s: int | None = None) -> WindowSpec:
    w = load_protocol()["window"]
    d = w["duration_s"] if duration_s is None else duration_s
    stride = w["stride_s"] * d // w["duration_s"]            # 50 % overlap for every declared duration
    return WindowSpec(duration_s=d, bin_s=w["bin_s"], stride_s=stride, max_gap_s=w["max_gap_s"])


def night_id(ts_seconds: np.ndarray) -> np.ndarray:
    """Noon-to-noon night of a naive local timestamp: date(timestamp - 12 h), as 'YYYY-MM-DD' (D-030)."""
    off = load_protocol()["grouping"]["night_offset_hours"] * 3600
    days = (np.asarray(ts_seconds, np.int64) - off) // 86400
    return np.datetime_as_string(days.astype("datetime64[D]"), unit="D")


def outer_folds() -> dict[int, str]:
    return {int(k): v for k, v in load_protocol()["loso"]["outer_folds"].items()}


def cohort() -> list[str]:
    return list(load_protocol()["data"]["subjects"])
