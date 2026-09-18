"""Render the P14 submission candidate into paper/manuscript/revision_p14/manuscript_p14_revision_rendered.md.

Resolves every source token against paper/tables/ and links Figure 6 from paper/manuscript/revision_p14/figures/.
The P8 submission candidate and the P10/P13 revisions are not touched. Prints the rendered abstract word count.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_text  # noqa: E402
from src.paper import p13_validation as P13  # noqa: E402
from src.paper import p14_validation as P  # noqa: E402
from src.paper import sources as S  # noqa: E402


def main() -> int:
    text = P.read_source()
    toks = S.tokens(text)
    for tok in toks:
        if tok.kind in ("value", "count"):
            S.resolve(tok)
    rendered = P.render(text)
    left = S.TOKEN.findall(S.strip_comments(rendered))
    if left:
        raise SystemExit(f"unresolved tokens after rendering: {left[:5]}")
    write_text(P.RENDERED, rendered)
    print(f"{len(toks)} tokens resolved; abstract {P13.abstract_words(rendered)} words; "
          f"wrote {P.RENDERED.relative_to(paths.PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
