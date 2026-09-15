"""Build paper/submission_candidate/ from the manuscript source and the generated assets (P8 formatting pass).

Renders the manuscript (source tokens, generated tables and figures, numbered citations, reference list) and copies
the public-safe generated material and author drafts into the staging directory with a SHA-256 manifest.
Run scripts/export_manuscript_tables.py and scripts/render_manuscript_figures.py first.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.render import build_candidate  # noqa: E402


def main() -> int:
    files = build_candidate()
    print(f"submission candidate: {len(files)} files (manifest: paper/submission_candidate/MANIFEST.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
