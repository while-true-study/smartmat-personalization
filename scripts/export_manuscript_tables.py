"""Export manuscript Tables 1-8 and the supplementary tables from the frozen paper tables (P8).

Writes paper/manuscript/generated/tables/ (Markdown, CSV, cell provenance) and
paper/manuscript/generated/supplementary/ (CSV copies without calendar dates, Table S19, index).
Nothing is recomputed; every printed number is a formatted frozen cell (src/paper/manuscript_tables.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.manuscript_tables import export  # noqa: E402


def main() -> int:
    summary = export()
    print("manuscript tables:", ", ".join(f"{k}={v}" for k, v in summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
