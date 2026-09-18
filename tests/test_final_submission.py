"""Final submission artifacts: layout-mode DOCX export, line-break control in tables, the checks on the cover letter
and metadata checklist, and the committed artifacts against the frozen P16 source.

The journal template is not in the repository, so the layout-mode build uses a minimal synthetic template.
"""
from __future__ import annotations

import zipfile

from src.paper import docx_export as D
from src.paper import final_submission as F

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' \
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def _template(path):
    parts = {
        "[Content_Types].xml": '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/'
                               'content-types"><Default Extension="png" ContentType="image/png"/></Types>',
        "_rels/.rels": "<Relationships/>",
        "word/document.xml": f'<w:document {W}><w:body><w:p/><w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                             f'</w:sectPr></w:body></w:document>',
        "word/_rels/document.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                                        'relationships"></Relationships>',
        "word/settings.xml": f'<w:settings {W}></w:settings>',
        "word/styles.xml": "<w:styles/>",
        "word/numbering.xml": f'<w:numbering {W}><w:num w:numId="22"><w:abstractNumId w:val="7"/></w:num>'
                              f'</w:numbering>',
        "docProps/core.xml": "<cp:coreProperties/>",
        "docProps/app.xml": "<Properties/>",
    }
    with zipfile.ZipFile(path, "w") as z:
        for name, text in parts.items():
            z.writestr(name, text)
    return path


def test_line_break_control_keeps_the_visible_text_and_fits_the_page():
    cells = ["RAW+MOVEMENT+CONTACT", "1.83 (1.70–1.96)", "1.78 ± 0.01", "+0.16 [+0.11, +0.21] +/+/+", "R, base (b = 0)"]
    for c in cells:
        bound = D._bind(c)
        assert bound.replace(D.ZWSP, "").replace(D.NBSP, " ") == c
    rows = [["Representation", "Δ vs RAW, %RH (improved)", "User02 bias, °C"],
            [D._bind(cells[0]), D._bind(cells[1]), "−4.69"]]
    widths = D.column_widths(rows, 3, 16)
    assert sum(widths) <= D.TABLE_WIDTH_TWIPS and min(widths) > D.CELL_PADDING_TWIPS
    assert D.UNBREAKABLE.findall("Δ vs RAW, %RH (improved)") == ["Δ", "vs", "RAW, %RH", "(improved)"]


def test_layout_build_keeps_text_and_adds_only_layout_properties(tmp_path):
    template = _template(tmp_path / "template.docx")
    md = F.rendered_markdown()
    out = D.build_docx(template, tmp_path / "final.docx", md, F.P16_PACKAGE / "figures", layout=True)
    plain = D.build_docx(template, tmp_path / "plain.docx", md, F.P16_PACKAGE / "figures")
    z = zipfile.ZipFile(out)
    doc = z.read("word/document.xml").decode("utf-8")
    assert '<w:tblLayout w:type="fixed"/>' in doc and "<w:cantSplit/>" in doc
    assert '<w:pStyle w:val="MDPI21heading1"/><w:keepNext/><w:keepLines/>' in doc
    assert b'<w:startOverride w:val="1"/>' in z.read("word/numbering.xml")        # numbered lists restart at 1
    assert '<w:tblLayout w:type="fixed"/>' not in zipfile.ZipFile(plain).read("word/document.xml").decode("utf-8")
    assert " ".join(D.docx_text(out).split()) == " ".join(D.docx_text(plain).split())
    supp = D.build_docx(template, tmp_path / "supp.docx", "# Supplementary Materials\n\nSome text.\n",
                        tmp_path, layout=True, article_type=None, ragged=True)
    sdoc = zipfile.ZipFile(supp).read("word/document.xml").decode("utf-8")
    assert "MDPI11articletype" not in sdoc and '<w:jc w:val="left"/>' in sdoc


def test_cover_letter_and_checklist_checks_reject_bad_input(tmp_path):
    letter = tmp_path / "letter.md"
    letter.write_text(f"note\n\n---\n\nWe submit \"{F.title()}\", the first state-of-the-art study.\n",
                      encoding="utf-8")
    problems = F.cover_letter_problems(letter)
    assert any("overstated" in p for p in problems) and any("placeholders" in p for p in problems)
    checklist = tmp_path / "checklist.md"
    checklist.write_text("| M01 | a | b | c | d | CLOSED | e | f |\n", encoding="utf-8")
    problems = F.metadata_problems(checklist)
    assert any("checklist items" in p for p in problems) and any("not open" in p for p in problems)
    assert any("placeholder not in the checklist" in p for p in problems)


def test_committed_final_artifacts_pass_every_check():
    results = F.validate()
    assert {name: problems for name, problems in results.items() if problems} == {}
