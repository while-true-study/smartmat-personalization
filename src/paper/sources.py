"""Read-only access to the frozen result tables and resolution of manuscript source tokens.

Every number in the manuscript and its generated tables comes from one cell of a committed table:
- `paper/tables/<name>.csv` (P3-P6 results, reproduced in P7), or
- `data/interim/manifest/canonical_v1_summary.csv` (P0 canonical-dataset counts), registered below.

Token syntax (paper/manuscript/MANUSCRIPT_NOTES.md):
    {{<table> | <col>=<value>, ... | <column> | <format>}}   one cell; the filters must select exactly one row
    {{COUNT:<table> | <col>=<value>, ...}}                  number of matching rows
    {{TABLE:<stem>}} / {{FIGURE:<stem>}}                    generated manuscript assets (rendering only)
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from src.data import paths

TABLES_DIR = paths.PROJECT_ROOT / "paper" / "tables"
EXTRA_SOURCES = {"canonical_v1_summary": paths.PROJECT_ROOT / "data" / "interim" / "manifest"
                                         / "canonical_v1_summary.csv"}
TOKEN = re.compile(r"\{\{(.*?)\}\}", re.S)
MINUS = "−"


class FrozenLookupError(LookupError):
    """A token or table cell does not resolve to exactly one frozen cell."""


def source_path(name: str) -> Path:
    if name in EXTRA_SOURCES:
        return EXTRA_SOURCES[name]
    p = TABLES_DIR / f"{name}.csv"
    if not re.fullmatch(r"[a-z0-9_]+", name) or not p.is_file():
        raise FrozenLookupError(f"unknown frozen table: {name!r}")
    return p


@lru_cache(maxsize=None)
def table(name: str) -> tuple[dict[str, str], ...]:
    with open(source_path(name), encoding="utf-8", newline="") as fh:
        return tuple(csv.DictReader(fh))


def rows(name: str, **filters: object) -> list[dict[str, str]]:
    return [r for r in table(name) if all(r.get(k) == str(v) for k, v in filters.items())]


def select(name: str, **filters: object) -> dict[str, str]:
    hit = rows(name, **filters)
    if len(hit) != 1:
        raise FrozenLookupError(f"{name} {filters}: expected one row, found {len(hit)}")
    return hit[0]


def cell(name: str, column: str, **filters: object) -> str:
    r = select(name, **filters)
    if column not in r:
        raise FrozenLookupError(f"{name}: no column {column!r}")
    return r[column]


def count(name: str, **filters: object) -> int:
    return len(rows(name, **filters))


def fmt(value: str, spec: str) -> str:
    """Format a frozen cell for print. Negative numbers use the typographic minus sign (U+2212)."""
    if spec == "s":
        return value
    if spec == "d":
        return str(int(float(value)))
    if spec == ",d":
        return f"{int(float(value)):,}"
    out = format(float(value), spec)
    return out.replace("-", MINUS)


def parse_number(text: str) -> float:
    """Inverse of `fmt` for comparisons: accepts U+2212, a leading plus and thousands separators."""
    return float(text.replace(MINUS, "-").replace(",", "").lstrip("+"))


def source_id(name: str, column: str, **filters: object) -> str:
    return f"{name}[{', '.join(f'{k}={v}' for k, v in filters.items())}].{column}"


@dataclass(frozen=True)
class Token:
    raw: str
    kind: str                                   # value | count | table | figure
    table: str = ""
    filters: dict[str, str] = field(default_factory=dict)
    column: str = ""
    spec: str = ""


def _filters(text: str) -> dict[str, str]:
    out = {}
    for kv in text.split(","):
        k, _, v = kv.partition("=")
        if not _:
            raise FrozenLookupError(f"bad filter {kv!r}")
        out[k.strip()] = v.strip()
    return out


def parse_token(body: str) -> Token:
    raw = " ".join(body.split())
    if raw.startswith("TABLE:") or raw.startswith("FIGURE:"):
        kind, _, stem = raw.partition(":")
        return Token(raw, kind.lower(), table=stem.strip())
    if raw.startswith("COUNT:"):
        parts = [x.strip() for x in raw[len("COUNT:"):].split("|")]
        if len(parts) != 2:
            raise FrozenLookupError(f"bad COUNT token: {raw}")
        return Token(raw, "count", parts[0], _filters(parts[1]))
    parts = [x.strip() for x in raw.split("|")]
    if len(parts) != 4:
        raise FrozenLookupError(f"bad value token: {raw}")
    return Token(raw, "value", parts[0], _filters(parts[1]), parts[2], parts[3])


def resolve(tok: Token) -> str:
    if tok.kind == "count":
        return str(count(tok.table, **tok.filters))
    if tok.kind == "value":
        return fmt(cell(tok.table, tok.column, **tok.filters), tok.spec)
    raise FrozenLookupError(f"{tok.kind} tokens are resolved by the renderer: {tok.raw}")


def tokens(text: str) -> list[Token]:
    """All tokens of a Markdown text, HTML comments excluded."""
    return [parse_token(m.group(1)) for m in TOKEN.finditer(strip_comments(text))]


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)
