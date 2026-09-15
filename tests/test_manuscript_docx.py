"""P8 DOCX export: MDPI style mapping, neutral metadata, no template path, deterministic output.

The journal template is not in the repository, so a minimal synthetic template with the same part layout is used.
"""
from __future__ import annotations

import zipfile

from src.paper import docx_export as D
from src.paper import render as RD

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
        "word/settings.xml": f'<w:settings {W}><w:attachedTemplate r:id="rId1"/></w:settings>',
        "word/_rels/settings.xml.rels": '<Relationships><Relationship Id="rId1" Target="file:///C:/private/'
                                        'template.dot" TargetMode="External"/></Relationships>',
        "word/styles.xml": "<w:styles/>",
        "docProps/core.xml": "<cp:coreProperties><dc:creator>Private Person</dc:creator></cp:coreProperties>",
        "docProps/app.xml": "<Properties><Company>Private Company</Company></Properties>",
    }
    with zipfile.ZipFile(path, "w") as z:
        for name, text in parts.items():
            z.writestr(name, text)
    return path


def test_parse_blocks_recognises_markdown_structures():
    md = "# Title\n\n## 1. Intro\n\nText *it* **b**.\n\n- a\n  - b\n\n| h1 | h2 |\n|---|---|\n| x | y |\n\n![F](f.png)\n"
    kinds = [b.kind for b in D.parse_blocks(md)]
    assert kinds == ["title", "heading", "para", "list", "table", "image"]
    lst = D.parse_blocks(md)[3]
    assert [lvl for lvl, _, _ in lst.items] == [0, 1]


def test_docx_maps_styles_drops_private_metadata_and_is_deterministic(tmp_path):
    template = _template(tmp_path / "template.docx")
    md = RD.RENDERED.read_text(encoding="utf-8")
    out1 = D.build_docx(template, tmp_path / "a.docx", md, draft_note="REVIEW DRAFT")
    out2 = D.build_docx(template, tmp_path / "b.docx", md, draft_note="REVIEW DRAFT")
    assert out1.read_bytes() == out2.read_bytes()
    z = zipfile.ZipFile(out1)
    names = z.namelist()
    assert "word/_rels/settings.xml.rels" not in names
    assert b"attachedTemplate" not in z.read("word/settings.xml")
    assert b"Private" not in z.read("docProps/core.xml") + z.read("docProps/app.xml")
    doc = z.read("word/document.xml").decode("utf-8")
    for style in ("MDPI12title", "MDPI17abstract", "MDPI18keywords", "MDPI21heading1", "MDPI41tablecaption",
                  "MDPI51figurecaption", "MDPI62backmatter", "MDPI81references"):
        assert f'w:val="{style}"' in doc, style
    assert doc.count('w:val="MDPI81references"') == 31
    assert doc.count("<w:tbl>") == 9                       # Tables 1-8 and the abbreviation table
    assert sum(n.startswith("word/media/p8_figure") for n in names) == 5
    text = D.docx_text(out1)
    assert text.startswith("REVIEW DRAFT")
    assert "{{" not in text and "[@" not in text
