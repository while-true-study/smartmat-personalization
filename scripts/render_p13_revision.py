"""Render the P13 manuscript revision without touching the P8 submission candidate or the P10 revision.

  python scripts/render_p13_revision.py

Reads paper/manuscript/manuscript_p13_revision.md, resolves every source token against paper/tables/, links Figure 6
from paper/manuscript/revision_p13/figures/ and writes
paper/manuscript/revision_p13/manuscript_p13_revision_rendered.md. Prints the rendered abstract word count.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_text  # noqa: E402
from src.paper import sources as S  # noqa: E402
from src.paper import p13_validation as P  # noqa: E402


def main() -> int:
    text = P.read_source()
    toks = S.tokens(text)
    for tok in toks:
        if tok.kind in ("value", "count"):
            S.resolve(tok)                               # raises on any unresolved token
    rendered = P.render(text)
    left = S.TOKEN.findall(S.strip_comments(rendered))
    if left:
        raise SystemExit(f"unresolved tokens after rendering: {left[:5]}")
    write_text(P.RENDERED, rendered)
    print(f"{len(toks)} tokens resolved; abstract {P.abstract_words(rendered)} words; "
          f"wrote {P.RENDERED.relative_to(paths.PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
