"""Render the manuscript source into the submission candidate (P8 formatting pass).

paper/manuscript/manuscript.md (source tokens, [@key] citations, {{TABLE:…}} / {{FIGURE:…}} markers)
    -> paper/submission_candidate/manuscript/manuscript_rendered.md
       numbers resolved from the frozen tables, generated tables inlined, figures linked, citations numbered in order
       of first appearance, and the reference list rendered from references.bib.
The staging directory also receives byte copies of the generated tables, figures and supplementary files and the
author-facing drafts, with a SHA-256 manifest. Nothing private is copied: no raw or canonical data, no release
windows, no local paths.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from src.data import paths
from src.data.io_guard import open_for_write, read_bytes, remove_file, write_json, write_text
from src.paper import references as R
from src.paper import sources as S
from src.paper.manuscript_figures import FIGURES
from src.paper.manuscript_tables import GENERATED

MANUSCRIPT_DIR = paths.PROJECT_ROOT / "paper" / "manuscript"
SOURCE = MANUSCRIPT_DIR / "manuscript.md"
CANDIDATE = paths.PROJECT_ROOT / "paper" / "submission_candidate"
RENDERED = CANDIDATE / "manuscript" / "manuscript_rendered.md"
DRAFTS = {"COVER_LETTER_DRAFT.md": "cover_letter_draft.md",
          "CONFERENCE_EXTENSION_DISCLOSURE_DRAFT.md": "conference_extension_disclosure.md",
          "AUTHOR_CONTRIBUTIONS_DRAFT.md": "author_contributions_draft.md",
          "DATA_AVAILABILITY_DRAFT.md": "data_availability_draft.md",
          "CODE_AVAILABILITY_DRAFT.md": "code_availability_draft.md"}
HAND_WRITTEN = ("README_CHECKLIST.md", "FINAL_SUBMISSION_CHECKLIST.md")
MARKED_TOKEN = re.compile(r"`?\{\{(.*?)\}\}`?", re.S)


def read_source(path: Path = SOURCE) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _asset(tok: S.Token) -> str:
    if tok.kind == "table":
        p = GENERATED / "tables" / f"{tok.table}.md"
        if not p.is_file():
            raise S.FrozenLookupError(f"generated table missing: {p.name}")
        return "\n" + p.read_text(encoding="utf-8").replace("\r\n", "\n").rstrip() + "\n"
    if tok.kind == "figure":
        if tok.table not in FIGURES or not (GENERATED / "figures" / f"{tok.table}.png").is_file():
            raise S.FrozenLookupError(f"generated figure missing: {tok.table}")
        return f"![{FIGURES[tok.table]}](../figures/{tok.table}.png)"
    return S.resolve(tok)


def resolve_markers(text: str) -> str:
    return MARKED_TOKEN.sub(lambda m: _asset(S.parse_token(m.group(1))), text)


def render_manuscript(source: str | None = None) -> str:
    text = S.strip_comments(read_source() if source is None else source)
    text = re.sub(r"\n{3,}", "\n\n", text)
    entries = R.load()
    order = R.citation_order(text)
    missing = [k for k in order if k not in entries]
    if missing:
        raise S.FrozenLookupError(f"citation keys missing from references.bib: {missing}")
    text = re.sub(r"\n{3,}", "\n\n", R.number_citations(resolve_markers(text), order))
    head, sep, tail = text.partition("\n## References\n")
    if not sep:
        raise S.FrozenLookupError("manuscript has no References section")
    rest = tail.split("\n## ", 1)
    after = "\n## " + rest[1] if len(rest) > 1 else ""
    banner = ("<!-- Rendered by scripts/build_submission_candidate.py from paper/manuscript/manuscript.md. Do not edit; "
              "edit the source and re-render. Bracketed items are open placeholders (docs/P8_FINAL_BLOCKERS.md). -->\n\n")
    return banner + head + sep + "\n" + R.reference_list(order, entries) + after


def _copy(src: Path, dst: Path) -> None:
    """Byte copy; Markdown and BibTeX are normalised to LF so the copy does not depend on the checkout."""
    data = read_bytes(src)
    if src.suffix in (".md", ".bib"):
        data = data.replace(b"\r\n", b"\n")
    with open_for_write(dst, "wb") as fh:
        fh.write(data)


def build_candidate(out: Path = CANDIDATE) -> dict[str, str]:
    """Write the staging directory; return {relative path: sha256} of every file in it (README excluded).

    Files left from an earlier build that are no longer produced are removed, so the directory always equals the
    current build plus the hand-written README_CHECKLIST.md.
    """
    before = {p for p in out.rglob("*") if p.is_file()} if out.is_dir() else set()
    write_text(out / "manuscript" / "manuscript_rendered.md", render_manuscript())
    _copy(SOURCE, out / "manuscript" / "manuscript_source.md")
    _copy(R.BIB_PATH, out / "manuscript" / "references.bib")
    for p in sorted((GENERATED / "tables").glob("table*")):
        _copy(p, out / "tables" / p.name)
    for stem in FIGURES:
        sub = "supplementary/figures" if stem.startswith("figureS") else "figures"
        _copy(GENERATED / "figures" / f"{stem}.png", out / sub / f"{stem}.png")
    for p in sorted((GENERATED / "supplementary").iterdir()):
        _copy(p, out / "supplementary" / "tables" / p.name)
    for src, dst in DRAFTS.items():
        _copy(MANUSCRIPT_DIR / src, out / "drafts" / dst)
    keep = {out / name for name in HAND_WRITTEN} | {out / "MANIFEST.json"}
    produced = {out / "manuscript" / "manuscript_rendered.md", out / "manuscript" / "manuscript_source.md",
                out / "manuscript" / "references.bib"}
    produced |= {out / "tables" / p.name for p in (GENERATED / "tables").glob("table*")}
    produced |= {out / ("supplementary/figures" if s.startswith("figureS") else "figures") / f"{s}.png"
                 for s in FIGURES}
    produced |= {out / "supplementary" / "tables" / p.name for p in (GENERATED / "supplementary").iterdir()}
    produced |= {out / "drafts" / d for d in DRAFTS.values()}
    for stale in before - produced - keep:
        remove_file(stale)
    files = {}
    for p in sorted(out.rglob("*")):
        rel = p.relative_to(out).as_posix()
        if p.is_file() and rel not in (*HAND_WRITTEN, "MANIFEST.json"):
            files[rel] = hashlib.sha256(read_bytes(p)).hexdigest()
    write_json(out / "MANIFEST.json", {"description": "SHA-256 of every file in the submission candidate except this "
                                                      "manifest and the hand-written checklists",
                                       "files": files})
    return files
