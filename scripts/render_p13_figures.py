"""Render the P13 revision Figure 6 into paper/manuscript/revision_p13/figures/ (Figure S5 withdrawn in P14, D-070).

Drawn only from the committed figure-data tables in paper/tables/ (scripts/export_p13_figure_data.py) and the frozen
source-training means. The P8 figures in paper/manuscript/generated/figures/ are not touched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.paper import manuscript_figures as MF  # noqa: E402
from src.paper.p13_figures import render_all  # noqa: E402


def main() -> int:
    for p in render_all():
        print("wrote", p.relative_to(paths.PROJECT_ROOT).as_posix(), "overlaps:", MF.QA.get(p.stem, []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
