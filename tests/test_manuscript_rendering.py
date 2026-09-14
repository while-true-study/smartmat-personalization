"""P8 manuscript rendering: references, figures and the rendered submission candidate."""
from __future__ import annotations

import struct

from src.paper import manuscript_figures as F
from src.paper import references as R
from src.paper import render as RD
from src.paper import sources as S


def _png_width(path) -> int:
    return struct.unpack(">I", path.read_bytes()[16:20])[0]


def test_initials_and_citation_ranges():
    assert R.initials("Ming-Chun") == "M.-C."
    assert R.initials("J. J.") == "J.J."
    assert R.initials("Mehrdad Heydar") == "M.H."
    assert R._compress([5, 1, 2, 3]) == "[1–3,5]"
    assert R._compress([2, 3]) == "[2,3]"


def test_citations_are_numbered_by_first_appearance():
    text = "a [@x; @y] b [@z] c [@x]"
    order = R.citation_order(text)
    assert order == ["x", "y", "z"]
    assert R.number_citations(text, order) == "a [1,2] b [3] c [1]"


def test_every_bibliography_entry_is_cited_and_renders():
    entries = R.load()
    order = R.citation_order(S.strip_comments(RD.read_source()))
    assert set(order) == set(entries)
    for e in entries.values():
        assert R.render(e)


def test_conference_reference_shows_pending_fields_and_no_invented_identifiers():
    e = R.load()["maeng2026icfice"]
    for f in ("doi", "pages", "volume", "url"):
        assert not e.get(f)
    assert "[PENDING:" in R.render(e) and "doi.org" not in R.render(e)


def test_end_labels_keep_a_minimum_gap_and_stay_centred():
    placed = {n: y for y, n in F.spread_labels([[1.19, "a"], [1.21, "b"], [1.51, "c"], [2.14, "d"]], 0.2)}
    ys = sorted(placed.values())
    assert all(b - a >= 0.2 - 1e-9 for a, b in zip(ys, ys[1:]))
    assert abs(placed["d"] - 2.14) < 1e-9


def test_figures_render_without_overlapping_labels(tmp_path):
    written = F.render_all(tmp_path)
    assert len(written) == len(F.FIGURES)
    assert all(not v for v in F.QA.values()), F.QA
    assert all(_png_width(p) >= 1000 for p in written)


def test_committed_rendered_manuscript_equals_a_fresh_render():
    committed = RD.RENDERED.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert committed == RD.render_manuscript()
    assert "{{" not in committed and "[@" not in committed
