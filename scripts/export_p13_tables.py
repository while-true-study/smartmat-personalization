"""Export the P11/P12 paper-facing tables for the P13 manuscript revision (no hand-copied numbers; CONVENTIONS §5).

Reads outputs/p11_common_pool_tcn/ and outputs/p12_heater_diagnostic/ (read only) and paper/tables/p10_*.csv, and
writes paper/tables/p11_*.csv, p12_*.csv, p13_*.csv and paper/manuscript/revision_p13/supplementary/ (Tables S35-S44).
Logic: src/paper/p13_revision.py.

  python scripts/export_p13_tables.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.p13_revision import export  # noqa: E402


def main() -> int:
    summary = export()
    print("P13 export:", ", ".join(f"{k}={v}" for k, v in summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
