"""Repository path resolution. Values come from configs/paths.yaml."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"


def load_config(name: str) -> dict[str, Any]:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@lru_cache(maxsize=1)
def path_config() -> dict[str, Any]:
    return load_config("paths.yaml")


def repo_path(rel: str) -> Path:
    return (PROJECT_ROOT / rel).resolve()


def raw_root() -> Path:
    return repo_path(path_config()["raw_root"])


def raw_package_root() -> Path:
    return repo_path(path_config()["raw_package_root"])


def protected_roots() -> list[Path]:
    return [repo_path(p) for p in path_config()["protected_roots"]]


def manifest_path() -> Path:
    return repo_path(path_config()["manifest_path"])


def audit_output_dir() -> Path:
    return repo_path(path_config()["audit_output_dir"])
