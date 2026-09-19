"""Word (DOCX) export of the rendered manuscript into the Applied Sciences Word template (P8 submission closure).

- The template is supplied by the user at run time. It is never copied into the repository: the journal's
  instructions restrict the templates to submission for peer review, not posting online.
- From the template the export keeps the styles, numbering, theme, font table, headers, footers and page setup. It
  replaces the body with the rendered manuscript, mapped onto the MDPI paragraph styles, and writes neutral document
  properties. The template's author and company fields and its link to a local template path are dropped.
- The output is deterministic for a given template and manuscript: sorted zip entries, fixed timestamps.
- While submission blockers are open, the first paragraph marks the file as a review draft.
"""
from __future__ import annotations

import re
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from src.data import paths
from src.data.io_guard import open_for_write, read_bytes
from src.paper import render as RD
from src.paper.manuscript_tables import GENERATED

OUTPUT = paths.PROJECT_ROOT / "outputs" / "p8" / "submission" / "manuscript_applsci.docx"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
EMU_PER_INCH = 914400
DPI = 300
MAX_FIGURE_WIDTH_IN = 7.0
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
STYLE = {"article_type": "MDPI11articletype", "title": "MDPI12title", "authors": "MDPI13authornames",
         "affiliation": "MDPI16affiliation", "abstract": "MDPI17abstract", "keywords": "MDPI18keywords",
         "h1": "MDPI21heading1", "h2": "MDPI22heading2", "h3": "MDPI23heading3", "text": "MDPI31text",
         "text_no_indent": "MDPI32textnoindent", "itemize": "MDPI37itemize", "bullet": "MDPI38bullet",
         "table_caption": "MDPI41tablecaption", "table_body": "MDPI42tablebody", "table_footer": "MDPI43tablefooter",
         "figure_caption": "MDPI51figurecaption", "figure": "MDPI52figure", "back_matter": "MDPI62backmatter",
         "references": "MDPI81references", "table_style": "MDPI41threelinetable"}
BULLET_NUM_ID = {"bullet": "20", "itemize": "22"}
NESTED_LEFT = 3458                 # twips; the template's level-0 bullet indent (3033) plus one hanging step (425)
BACK_MATTER = ("Supplementary Materials", "Author Contributions", "Funding", "Institutional Review Board Statement",
               "Informed Consent Statement", "Data Availability Statement", "Acknowledgments", "Conflicts of Interest")
FRONT_LABELS = {"Authors": "authors", "Affiliations": "affiliation", "Corresponding author": "affiliation",
                "ORCID": "affiliation", "Note": "affiliation", "Featured Application": "abstract",
                "Keywords": "keywords"}
INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`)")


# --- inline Markdown -> runs -------------------------------------------------------------------------------------

def runs(text: str, bold: bool = False, size_half_points: int | None = None) -> str:
    out = []
    for part in INLINE.split(text):
        if not part:
            continue
        b, i, t = bold, False, part
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            b, t = True, part[2:-2]
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            i, t = True, part[1:-1]
        elif part.startswith("`") and part.endswith("`"):
            t = part[1:-1]
        props = ("<w:b/>" if b else "") + ("<w:i/>" if i else "") + (
            f'<w:sz w:val="{size_half_points}"/><w:szCs w:val="{size_half_points}"/>' if size_half_points else "")
        out.append(f"<w:r>{f'<w:rPr>{props}</w:rPr>' if props else ''}"
                   f'<w:t xml:space="preserve">{escape(t)}</w:t></w:r>')
    return "".join(out)


def para(style: str, content: str, extra_ppr: str = "") -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="{STYLE[style]}"/>{extra_ppr}</w:pPr>{content}</w:p>'


def labelled(style: str, label: str, text: str) -> str:
    return para(style, runs(f"{label}: ", bold=True) + runs(text))


# --- blocks ---------------------------------------------------------------------------------------------------------

@dataclass
class Block:
    kind: str                     # title, heading, para, list, table, image
    level: int = 0
    text: str = ""
    items: list[tuple[int, str, bool]] = field(default_factory=list)     # (indent level, text, numbered)
    rows: list[list[str]] = field(default_factory=list)


LIST_ITEM = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")


def parse_blocks(markdown: str) -> list[Block]:
    lines = re.sub(r"<!--.*?-->", "", markdown, flags=re.S).split("\n")
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(Block("title" if level == 1 else "heading", level, line[level:].strip()))
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", lines[i].strip())[1:-1]]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(Block("table", rows=rows))
            continue
        m = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
        if m:
            blocks.append(Block("image", text=m.group(2)))
            i += 1
            continue
        if LIST_ITEM.match(line):
            items = []
            while i < len(lines) and lines[i].strip():
                lm = LIST_ITEM.match(lines[i])
                if lm:
                    items.append([len(lm.group(1)) // 2, lm.group(3), lm.group(2)[0].isdigit()])
                elif items:
                    items[-1][1] += " " + lines[i].strip()
                i += 1
            blocks.append(Block("list", items=[tuple(x) for x in items]))
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|")) \
                and not LIST_ITEM.match(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        blocks.append(Block("para", text=" ".join(buf)))
    return blocks


# --- document body ------------------------------------------------------------------------------------------------

@dataclass
class Media:
    items: list[tuple[str, str, bytes]] = field(default_factory=list)     # (rel id, part name, bytes)
    restarts: list[str] = field(default_factory=list)                    # numIds of numbered lists restarting at 1


def _png_size(data: bytes) -> tuple[int, int]:
    return struct.unpack(">II", data[16:24])


def image_xml(path: Path, media: Media, n: int) -> str:
    data = read_bytes(path)
    w_px, h_px = _png_size(data)
    w_in = min(w_px / DPI, MAX_FIGURE_WIDTH_IN)
    cx, cy = int(w_in * EMU_PER_INCH), int(w_in * h_px / w_px * EMU_PER_INCH)
    rid, name = f"rIdP8Fig{n}", f"media/p8_figure{n}.png"
    media.items.append((rid, name, data))
    return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="{1000 + n}" name="Figure {n}"/><wp:cNvGraphicFramePr>'
            f'<a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData '
            f'uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr>'
            f'<pic:cNvPr id="{1000 + n}" name="{escape(path.name)}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
            f'<a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm>'
            f'<a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/>'
            f'</a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')


TABLE_WIDTH_TWIPS = 11906 - 720 - 720      # A4 page minus the template's left and right margins
CELL_PADDING_TWIPS = 216
KEEP_TOGETHER_ROWS = 12
TEXT_SAFETY = 1.03
TABLE_FONT = {False: "pala.ttf", True: "palab.ttf"}  # Palatino Linotype, the template's table-body font


def _em_width(bold: bool):
    """Advance width of a string in em: the installed table font's metrics, else a conservative estimate."""
    try:
        from PIL import ImageFont
        font = ImageFont.truetype(TABLE_FONT[bold], 1000)
        return lambda s: font.getlength(s) / 1000
    except (ImportError, OSError):
        return lambda s: sum(0.25 if ch == " " else 0.8 if ch.isupper() or ch in "%+±×=−–—~@&#" else
                             0.3 if ch in ".,:;()[]'!|/-" else 0.56 for ch in s) * (1.08 if bold else 1.0)


ZWSP = "\u200b"                                  # zero-width space: an invisible line-break opportunity
NBSP = "\u00a0"                                  # no-break space: no line break here
UNBREAKABLE = re.compile(r"[^ ]+(?: +[%°][^ ]*)*")  # Word keeps a word together with a following "%..." or "°..." token


def _bind(cell: str) -> str:
    """Line-break control in a layout table cell: "RAW+MOVEMENT+CONTACT" may wrap after a "+"; a value with its
    range "1.83 (1.70–1.96)", "1.78 ± 0.01", an interval "[+0.11, +0.21]" and "b = 0" are kept on one line (the
    column is made wide enough for them). Only a zero-width space and no-break spaces are inserted; the visible text
    is unchanged."""
    cell = re.sub(r"(?<=[A-Z])\+(?=[A-Z])", "+" + ZWSP, cell)
    cell = re.sub(r"(?<=\d) (?=\([+−-]?\d[\d.]*–[+−-]?\d[\d.]*\))", NBSP, cell)          # "1.83 (1.70–1.96)"
    cell = re.sub(r"(?<=\d) ± (?=\d)", NBSP + "±" + NBSP, cell)                               # "1.78 ± 0.01"
    cell = re.sub(r"\[[^\]]+\]", lambda m: m.group(0).replace(", ", "," + NBSP), cell)
    return re.sub(r"(?<=\b[A-Za-z]) = (?=[\d+−-])", NBSP + "=" + NBSP, cell)


def _plain_cell(text: str) -> str:
    return re.sub(r"\*\*|`", "", text)


def column_widths(rows: list[list[str]], n_cols: int, size_half_points: int,
                  total: int = TABLE_WIDTH_TWIPS) -> list[int]:
    """Twips per column: at least the longest word of the column (no break inside a word), the rest shared in
    proportion to the single-line content width."""
    em = 20 * size_half_points / 2                        # twips per em
    regular, bold = _em_width(False), _em_width(True)
    need_min, need_line = [0.0] * n_cols, [0.0] * n_cols
    for k, r in enumerate(rows):
        width = bold if k == 0 else regular               # the header row is bold
        for c, text in enumerate(r + [""] * (n_cols - len(r))):
            t = _plain_cell(text)
            longest = max((width(p) for w in UNBREAKABLE.findall(t) for p in w.split(ZWSP)), default=0)
            need_min[c] = max(need_min[c], longest * em * TEXT_SAFETY + CELL_PADDING_TWIPS)
            need_line[c] = max(need_line[c], width(t) * em * TEXT_SAFETY + CELL_PADDING_TWIPS)
    if sum(need_line) <= total:
        return [int(w * total / sum(need_line)) for w in need_line]
    if sum(need_min) >= total:
        return [int(w * total / sum(need_min)) for w in need_min]
    spare, extra = total - sum(need_min), [b - a for a, b in zip(need_min, need_line)]
    return [int(a + spare * e / sum(extra)) for a, e in zip(need_min, extra)]


def table_xml(rows: list[list[str]], layout: bool = False) -> str:
    """`layout=True`: fixed column widths from the content (no word split), no hyphenation in cells, rows never split
    across pages, and short tables kept on one page."""
    n_cols = max(len(r) for r in rows)
    size = 16 if n_cols >= 6 else 18                      # 8 pt or 9 pt (journal minimum 8 pt)
    if layout:
        rows = [[_bind(c) for c in r] for r in rows]
        widths = column_widths(rows, n_cols, size)
        grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
        tbl_layout = '<w:tblW w:w="{}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'.format(sum(widths))
    else:
        widths = [0] * n_cols
        grid = "".join('<w:gridCol w:w="1000"/>' for _ in range(n_cols))
        tbl_layout = '<w:tblW w:w="5000" w:type="pct"/><w:tblLayout w:type="autofit"/>'
    out = [f'<w:tbl><w:tblPr><w:tblStyle w:val="{STYLE["table_style"]}"/>{tbl_layout}</w:tblPr>'
           f'<w:tblGrid>{grid}</w:tblGrid>']
    keep_all = layout and len(rows) <= KEEP_TOGETHER_ROWS
    for k, r in enumerate(rows):
        cells = []
        for c, text in enumerate(r + [""] * (n_cols - len(r))):
            border = '<w:tcBorders><w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/></w:tcBorders>' \
                if k == 0 else ""
            cell_ppr = ""
            if layout:
                cell_ppr = ("<w:keepNext/>" if keep_all and k < len(rows) - 1 else "") + "<w:suppressAutoHyphens/>"
            width = f'<w:tcW w:w="{widths[c]}" w:type="dxa"/>' if layout else '<w:tcW w:w="0" w:type="auto"/>'
            body = runs(text, bold=k == 0, size_half_points=size)
            if layout:                                    # "40-s" never wraps at its hyphen
                body = re.sub(r"(<w:t xml:space=\"preserve\">)([^<]*)", lambda m: m.group(1) + re.sub(
                    r"(?<=\S)-(?=\S)", '</w:t><w:noBreakHyphen/><w:t xml:space="preserve">', m.group(2)), body)
            cells.append(f'<w:tc><w:tcPr>{width}{border}</w:tcPr>'
                         f'{para("table_body", body, cell_ppr)}</w:tc>')
        tr = ("<w:cantSplit/>" if layout else "") + ("<w:tblHeader/>" if k == 0 else "")
        out.append(f"<w:tr>{f'<w:trPr>{tr}</w:trPr>' if tr else ''}{''.join(cells)}</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def list_xml(items: list[tuple[int, str, bool]], style_override: str | None = None,
             numbered_id: str | None = None) -> str:
    out = []
    for level, text, numbered in items:
        style = style_override or ("itemize" if numbered else "bullet")
        num_id = numbered_id if numbered and numbered_id else BULLET_NUM_ID.get(style, "")
        numpr = "" if style_override else (f'<w:numPr><w:ilvl w:val="0"/>'
                                           f'<w:numId w:val="{num_id}"/></w:numPr>')
        if level and not style_override:            # nested items: level-0 marker, indented one step further
            numpr += f'<w:ind w:left="{NESTED_LEFT + 425 * (min(level, 3) - 1)}" w:hanging="425"/>'
        out.append(para(style, runs(text), numpr))
    return "".join(out)


SPACE_AFTER_TABLE = '<w:spacing w:before="120"/>'
SPACE_BEFORE_TABLE = '<w:spacing w:after="120"/>'
BODY_STYLES = "|".join(STYLE[k] for k in ("text", "text_no_indent", "itemize", "bullet"))   # body text and lists


def _after_table(xml: str, spacing: str = SPACE_AFTER_TABLE) -> str:
    """Space between a table and the body paragraph or list that follows it (inserted in schema order)."""
    head, sep, rest = xml.partition("</w:pPr>")
    at = head.find("<w:ind ")
    head = head[:at] + spacing + head[at:] if at >= 0 else head + spacing
    return head + sep + rest


def body_xml(markdown: str, figures_dir: Path, draft_note: str | None, layout: bool = False,
             article_type: str | None = "Article", ragged: bool = False) -> tuple[str, Media]:
    """`article_type=None` omits the article-type line; `ragged=True` left-aligns body text and lists."""
    blocks = parse_blocks(markdown)
    media = Media()
    out = []
    if draft_note:
        out.append(para("text_no_indent", runs(draft_note, bold=True)))
    if article_type:
        out.append(para("article_type", runs(article_type)))
    section, fig_n, prev = "", 0, None
    back_started: dict[str, bool] = {}
    for b in blocks:
        n_out = len(out)
        if b.kind == "title":
            out.append(para("title", runs(b.text)))
        elif b.kind == "heading":
            section = b.text
            if b.level == 2 and b.text in BACK_MATTER:
                back_started[b.text] = False
            elif b.level == 2 and b.text == "Abstract":
                pass
            else:
                out.append(para({2: "h1", 3: "h2"}.get(b.level, "h3"), runs(b.text),
                                "<w:keepNext/><w:keepLines/>" if layout else ""))
        elif b.kind == "para":
            m = re.match(r"\*\*([^*]+):\*\*\s*(.*)", b.text)
            cap = re.match(r"\*\*(Table|Figure) ([0-9S]+)\.\*\*\s*(.*)", b.text)
            if cap:
                style = "table_caption" if cap.group(1) == "Table" else "figure_caption"
                keep = "<w:keepNext/><w:keepLines/>" if layout and cap.group(1) == "Table" else ""
                out.append(para(style, runs(f"{cap.group(1)} {cap.group(2)}. ", bold=True) + runs(cap.group(3)),
                                keep))
            elif m and m.group(1) in FRONT_LABELS:
                style = FRONT_LABELS[m.group(1)]
                if m.group(1) == "Authors":
                    out.append(para("authors", runs(m.group(2))))
                else:
                    out.append(labelled(style, m.group(1), m.group(2)))
            elif section == "Abstract":
                out.append(labelled("abstract", "Abstract", b.text))
            elif section in back_started:
                if not back_started[section]:
                    out.append(labelled("back_matter", section, b.text))
                    back_started[section] = True
                else:
                    out.append(para("back_matter", runs(b.text)))
            elif b.text == "Notes:" and prev is not None and prev.kind == "table":
                pass
            else:
                style = "text_no_indent" if prev is None or prev.kind in ("heading", "table", "image", "list") \
                    or (layout and re.fullmatch(r"\*\*[^*]+\*\*", b.text)) else "text"   # a bold label line
                out.append(para(style, runs(b.text)))
        elif b.kind == "list":
            if section == "References":
                refs = list_xml([(0, re.sub(r"^\d+\.\s*", "", t), False) for _, t, _ in b.items], "references")
                if layout:                                   # long DOIs and URLs: no stretched justified lines
                    refs = refs.replace(f'<w:pStyle w:val="{STYLE["references"]}"/>',
                                        f'<w:pStyle w:val="{STYLE["references"]}"/><w:jc w:val="left"/>')
                out.append(refs)
            elif prev is not None and prev.kind == "para" and prev.text == "Notes:":
                out.append("".join(para("table_footer", runs(t)) for _, t, _ in b.items))
            else:
                numbered_id = None
                if layout and any(num for _, _, num in b.items):     # each numbered list restarts at 1
                    numbered_id = str(900 + len(media.restarts))
                    media.restarts.append(numbered_id)
                out.append(list_xml(b.items, numbered_id=numbered_id))
        elif b.kind == "table":
            if layout and prev is not None and prev.kind == "para" and out \
                    and re.match(rf'<w:p><w:pPr><w:pStyle w:val="(?:{BODY_STYLES})"', out[-1]):
                out[-1] = _after_table(out[-1], SPACE_BEFORE_TABLE)      # body text directly above a table
            out.append(table_xml(b.rows, layout))
        elif b.kind == "image":
            fig_n += 1
            out.append(para("figure", image_xml(figures_dir / Path(b.text).name, media, fig_n),
                            "<w:keepNext/>" if layout else ""))
        if layout and prev is not None and prev.kind == "table" and len(out) > n_out \
                and re.match(rf'<w:p><w:pPr><w:pStyle w:val="(?:{BODY_STYLES})"', out[n_out]):
            out[n_out] = _after_table(out[n_out])
        prev = b
    body = "".join(out)
    if ragged:
        body = re.sub(rf'(<w:pPr><w:pStyle w:val="(?:{BODY_STYLES})"/>(?:(?!</w:pPr>).)*)</w:pPr>',
                      r'\1<w:jc w:val="left"/></w:pPr>', body)
    return body, media


# --- package ------------------------------------------------------------------------------------------------------

CORE = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>{title}</dc:title></cp:coreProperties>')
APP = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties '
       'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
       '<Application>Microsoft Office Word</Application></Properties>')


def build_docx(template: Path, out: Path = OUTPUT, markdown: str | None = None, figures_dir: Path | None = None,
               draft_note: str | None = None, layout: bool = False, article_type: str | None = "Article",
               ragged: bool = False) -> Path:
    """`layout=True` (final submission build): no hyphenation in table cells, table rows kept on one page, table
    captions kept with their table and figures with their caption, references left-aligned. Default off, so the P8
    build is unchanged. `article_type=None` and `ragged=True` are used for the supplementary document."""
    markdown = markdown if markdown is not None else RD.RENDERED.read_text(encoding="utf-8")
    figures_dir = figures_dir or GENERATED / "figures"
    src = zipfile.ZipFile(template)
    doc = src.read("word/document.xml").decode("utf-8")
    sect = re.findall(r"<w:sectPr\b.*?</w:sectPr>", doc, re.S)[-1]
    body, media = body_xml(markdown, figures_dir, draft_note, layout, article_type, ragged)
    title = next((b.text for b in parse_blocks(markdown) if b.kind == "title"), "")
    document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {NS}><w:body>{body}{sect}'
                f'</w:body></w:document>')
    rels = src.read("word/_rels/document.xml.rels").decode("utf-8")
    rels = rels.replace("</Relationships>", "".join(
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        f'Target="{name}"/>' for rid, name, _ in media.items) + "</Relationships>")
    settings = re.sub(r"<w:attachedTemplate [^>]*/>", "", src.read("word/settings.xml").decode("utf-8"))
    parts: dict[str, bytes] = {}
    for name in src.namelist():
        if name in ("word/_rels/settings.xml.rels", "docProps/custom.xml") or name.startswith("customXml/"):
            continue
        parts[name] = src.read(name)
    parts["word/document.xml"] = document.encode("utf-8")
    parts["word/_rels/document.xml.rels"] = rels.encode("utf-8")
    parts["word/settings.xml"] = settings.encode("utf-8")
    if media.restarts:
        numbering = src.read("word/numbering.xml").decode("utf-8")
        abstract = re.search(rf'<w:num w:numId="{BULLET_NUM_ID["itemize"]}"[^>]*>\s*<w:abstractNumId w:val="(\d+)"/>',
                             numbering).group(1)
        numbering = numbering.replace("</w:numbering>", "".join(
            f'<w:num w:numId="{n}"><w:abstractNumId w:val="{abstract}"/><w:lvlOverride w:ilvl="0">'
            f'<w:startOverride w:val="1"/></w:lvlOverride></w:num>' for n in media.restarts) + "</w:numbering>")
        parts["word/numbering.xml"] = numbering.encode("utf-8")
    parts["docProps/core.xml"] = CORE.format(title=escape(title)).encode("utf-8")
    parts["docProps/app.xml"] = APP.encode("utf-8")
    for _, name, data in media.items:
        parts["word/" + name] = data
    with open_for_write(out, "wb") as fh:
        with zipfile.ZipFile(fh, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for name in sorted(parts, key=lambda n: (n != "[Content_Types].xml", n)):
                info = zipfile.ZipInfo(name, FIXED_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, parts[name])
    return out


def docx_text(path: Path) -> str:
    """Plain text of a DOCX body (for validation)."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml).replace("<w:noBreakHyphen/>", "-").replace(ZWSP, "").replace(NBSP, " ")
    return re.sub(r"<[^>]+>", "", xml).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").lstrip()
