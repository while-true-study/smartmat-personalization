"""Export the figure-data tables of the P13 revision figures from the canonical dataset (read only).

Writes paper/tables/p13_figure_target_distribution.csv (Figure 6; no calendar date, night id or clock time). Needs the
local canonical_v1 dataset. Since P14 (D-070) the Figure S5 night series and heater-event timing are no longer exported;
they were withdrawn from the submission candidate and from any release path.
Logic and the fixed night-selection rule: src/paper/p13_figures.py.

  python scripts/export_p13_figure_data.py && python scripts/render_p13_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.p13_figures import extract_figure_data  # noqa: E402


def main() -> int:
    summary = extract_figure_data()
    print("P13 figure data:", ", ".join(f"{k}={v}" for k, v in summary.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
