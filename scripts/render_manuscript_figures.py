"""Render manuscript Figures 1-4 and S1-S4 into paper/manuscript/generated/figures/ (P8).

Figure 1 is a design schematic; every other figure is drawn from the frozen figure-data tables
(src/paper/manuscript_figures.py). The committed report figures in paper/figures/ are not touched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.paper.manuscript_figures import render_all  # noqa: E402


def main() -> int:
    for p in render_all():
        print("wrote", p.relative_to(paths.PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
