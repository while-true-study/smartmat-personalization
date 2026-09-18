"""Build the submission-ready candidate package paper/submission_p15/ from manuscript_p15_final.md.

Renders the manuscript (source tokens, generated tables, Figure 6, numbered citations and references) and copies the
main tables and figures, supplementary tables S1-S44 and figures S1-S4, the reference library and a sheet of the open
metadata placeholders, with a SHA-256 manifest. Run scripts/export_manuscript_tables.py, scripts/export_p13_tables.py
and scripts/render_p14_figures.py first. Logic: src/paper/p15_submission.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.paper import p15_submission as P  # noqa: E402


def main() -> int:
    files = P.build()
    wc = P.word_count(P.render())
    print(f"submission package: {len(files)} files in {P.PACKAGE.relative_to(paths.PROJECT_ROOT).as_posix()}; "
          f"abstract {wc['abstract']} words; main text {wc['main_text']} words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
