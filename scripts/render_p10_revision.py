"""Render the P10 manuscript revision (D-064) without touching the P8 submission candidate.

  python scripts/render_p10_revision.py

Reads paper/manuscript/manuscript_p10_revision.md, resolves every source token against paper/tables/ (including the
exported P10 tables) and writes paper/manuscript/revision_p10/manuscript_p10_revision_rendered.md.
paper/manuscript/manuscript.md and paper/submission_candidate/ are not read for writing and stay unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_text  # noqa: E402
from src.paper import sources as S  # noqa: E402
from src.paper.render import render_manuscript  # noqa: E402

SOURCE = paths.PROJECT_ROOT / "paper" / "manuscript" / "manuscript_p10_revision.md"
OUT = paths.PROJECT_ROOT / "paper" / "manuscript" / "revision_p10" / "manuscript_p10_revision_rendered.md"


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    toks = S.tokens(text)
    for tok in toks:
        if tok.kind in ("value", "count"):
            S.resolve(tok)                               # raises on any unresolved token
    rendered = render_manuscript(text).replace(
        "from paper/manuscript/manuscript.md", "from paper/manuscript/manuscript_p10_revision.md "
                                               "(scripts/render_p10_revision.py)")
    left = S.TOKEN.findall(S.strip_comments(rendered))
    if left:
        raise SystemExit(f"unresolved tokens after rendering: {left[:5]}")
    write_text(OUT, rendered)
    print(f"{len(toks)} tokens resolved; wrote {OUT.relative_to(paths.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
