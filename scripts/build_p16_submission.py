"""Build the final editorial candidate package paper/submission_p16/ from manuscript_p16_final.md.

Same contents as the P15 package (rendered manuscript, main tables and figures, supplementary tables S1-S44 and figures
S1-S4 with their index, reference library, metadata placeholder sheet, SHA-256 manifest). Logic:
src/paper/p16_submission.py (reusing src/paper/p15_submission.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.paper import p16_submission as P  # noqa: E402


def main() -> int:
    files = P.build()
    wc = P.word_count(P.render())
    print(f"submission package: {len(files)} files in {P.PACKAGE.relative_to(paths.PROJECT_ROOT).as_posix()}; "
          f"abstract {wc['abstract']} words; main text {wc['main_text']} words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
