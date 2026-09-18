"""Render Figure 6 of the P14 submission candidate into paper/manuscript/revision_p14/figures/.

Drawn only from paper/tables/p13_figure_target_distribution.csv and the frozen source-training means. Figure S5 is
withdrawn (D-070) and is not drawn. The P8 and P13 figures are not touched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.paper import manuscript_figures as MF  # noqa: E402
from src.paper import p14_validation as P14  # noqa: E402
from src.paper.p13_figures import figure6  # noqa: E402


def main() -> int:
    p = figure6(P14.FIGURES_DIR)
    print("wrote", p.relative_to(paths.PROJECT_ROOT).as_posix(), "overlaps:", MF.QA.get(p.stem, []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
