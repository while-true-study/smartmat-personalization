# DOCX visual QA — main manuscript, page by page

| Field | Value |
|---|---|
| File | `paper/submission_final/manuscript/Applied_Sciences_SmartMat_Final.docx` |
| SHA-256 of the rendered file | 15fcadfe3996e0cd89440c7422009b2aafa9bf82b3b6050bc16949b749716810 (identical to the committed file; the earlier 80 dpi pass reviewed 86f6590b3b326487…, before fix R8) |
| Renderer | Microsoft Word 16.0 (build 16.0.20326) through COM: `scripts/render_docx_pages.ps1` opens the file read-only, updates fields and exports a PDF (final render sha256 cfcd2fdfabe07582…) |
| Page images | PyMuPDF 1.28.2. Previous QA: 80 dpi, one PNG per page. Final QA: **180 dpi**, each page as a full image and as top and bottom halves (1489 px wide) so that 8 pt table text, superscripts and figure labels are legible. The PDFs and PNGs are in `paper/submission_final/work/`, which is not committed. |
| Pages | 39. Every page was inspected at 80 dpi (previous QA) and again at 180 dpi (final QA), with no spot check. |

**Checks on every page:**
- text clipping, overlapping text, broken glyphs;
- missing symbols (°C, %RH, η², ×, ±, −, →, Δ, ≥, √, †);
- table clipping or tables outside the margins, figure cropping or distortion;
- caption separated from its table or figure;
- orphan headings and headings at the page bottom;
- large blank areas, bad manual page breaks, section-break anomalies;
- reference formatting;
- header and footer collisions, page numbers ("n of 39") and line numbers.

**Additional checks at 180 dpi:**
- °C, %RH, η², ², ±, ×, √, →, Δ, ≥, †, en dash and minus sign (−, distinct from the hyphen);
- superscripts and subscript-style labels (η², r², R_oracle, G_b, MAE_0);
- confidence intervals "[low, high]" and ranges "(low–high)" kept on one line;
- table footnotes and 8 pt table text;
- figure axis labels, tick labels, panel titles and legends (Figures 1–6);
- the reference list;
- clipping, overlap, page-edge overflow and caption separation.

## Render iterations and layout fixes

Every fix is a layout property in `src/paper/docx_export.py` (layout mode). No text, number or order was changed.

| Iteration | Issues found in the render | Fix applied |
|---|---|---|
| R1 | Headings alone at the bottom of pages. | Headings keep with the next paragraph and keep their lines together. |
| R1 | The Limitations list continued the contributions numbering (5–12). | Each numbered list restarts at 1. |
| R1 | Words hyphenated or broken inside narrow table columns. | Fixed column widths from the cell contents; no automatic hyphenation in cells; rows never split across pages. Tables of up to 12 rows are kept on one page, and the header row repeats on long tables. |
| R1 | Justified reference lines stretched by long DOIs. | References left-aligned. |
| R1 | Figures separated from their captions. | Each figure keeps with its caption. |
| R2 | Table 1 caption split between pages 5 and 6. | Table captions keep their lines together and stay with their table. |
| R3 | Table 1 header wrapped as "40-" / "s windows". | Hyphens in table cells made non-breaking. |
| R4 | Table 3 "RAW+MOVEMENT+C / ONTACT" and "(improved / )"; Table 4 "RAW-TC / N". The estimated character widths were too small for capitals. | Column widths from the metrics of the template's table font (Palatino Linotype, regular and bold). |
| R5 | Table 3 "%R / H" and "° / C". Word keeps "RAW, %RH" and "bias, °C" together, which the widths did not allow for. After that, the minimum widths of Table 3 exceeded the page. | A word followed by a "%…" or "°…" token is measured as one unit. A zero-width break opportunity after "+" in feature-family names lets "RAW+MOVEMENT+CONTACT" wrap after a "+". |
| R6 | Page 5: the bold label "Cohort:" was indented, but "Sources not used:" was not. | Bold label lines are not indented. |
| R6 | Table 6 ranges broke after the en dash ("1.70–" / "1.96)"), and "(b =" / "0)" split. Word ignored a word joiner around the dash. | No-break spaces keep "value (low–high)", "mean ± sd", "[low, high]" and "b = 0" on one line, and the column widths allow for them. |
| R7 | Page 29: a body paragraph touched the bottom rule of Table 10. | 6 pt of space before the first body paragraph or list after a table. This moved Table 10's closing paragraph to page 30. Pages 29–31 changed; the pagination of every other page was unchanged. |
| R8 (180 dpi) | Page 37: the intro line "The following abbreviations are used in this manuscript:" sat on the top rule of the Abbreviations table; its descenders touched the rule (gap 0.2 pt in the PDF). Not visible at 80 dpi. A PDF scan of every page found no other text line within 1.5 pt of a table rule. | 6 pt of space after a body paragraph that directly precedes a table (layout mode). Only page 37 changed: the word positions of the other 38 pages are identical to the previous render. |
| Final | none | The final render was inspected in full at 180 dpi, pages 1–39. |

**Accepted as layout, not defects:**
- Blank space at the foot of pages 5, 7, 22 and 30 comes from keeping tables and figures whole with their captions.
  Table 1, Figure 1, Table 6 and Table 11 do not fit in the remaining space.
- Tables 4, 5 and 8 continue on the next page, with the header row repeated and no row split.
- The running header "Appl. Sci. 2025, 15, x FOR PEER REVIEW" and the first-page footer "https://doi.org/10.3390/xxxxx"
  are template fields that the journal fills in.
- British spellings in the frozen source ("summarises", "initialised") are not changed.

## Page-by-page result (final render, 180 dpi)

| Page | Lines | Content | Result |
|---|---|---|---|
| 1 | 1–42 | Journal header and logo, article type, title (3 lines), author/affiliation/ORCID/Note placeholders, Featured Application, Abstract, Keywords, start of 1. Introduction | clean |
| 2 | 43–92 | Introduction, research questions RQ1–RQ3 | clean |
| 3 | 93–141 | Contributions 1–4, relation to the conference study, 2. Related Work, 2.1 | clean |
| 4 | 142–186 | 2.2–2.4 | clean |
| 5 | 187–221 | 3. Materials and Methods, 3.1 (sensor placeholder, cohort and excluded-source lists); blank space below because Table 1 is kept whole | clean |
| 6 | 222–257 | Table 1 with caption and footnotes, 3.2 | clean |
| 7 | 258–294 | 3.3, 3.4, 3.5; blank space below because Figure 1 is kept with its caption | clean |
| 8 | 295–324 | Figure 1 and caption, 3.5.1 | clean |
| 9 | 325–374 | 3.5.2–3.5.4 | clean |
| 10 | 375–422 | 3.5.4 rules, 3.5.5 | clean |
| 11 | 423–472 | 3.5.6, 3.5.7 | clean |
| 12 | 473–521 | 3.5.7, 3.5.8 (two-line heading) | clean |
| 13 | 522–570 | 3.5.9, 3.6 | clean |
| 14 | 571–618 | 3.6, 3.7 | clean |
| 15 | 619–654 | 3.8 (GenAI placeholder and text), 4. Results, 4.1, Table 2 with caption and footnotes | clean |
| 16 | 655–685 | 4.1 bullets, 4.2, Table 3 with caption and footnotes | clean |
| 17 | 686–716 | Table 3 footnotes, 4.3, Table 4 caption and first rows | clean |
| 18 | 717–724 | Table 4 continued (header repeated), footnotes | clean |
| 19 | 725–741 | Table 4 footnotes, Figures 2 and 3 with captions | clean |
| 20 | 742–773 | 4.3 results, 4.4, Table 5 caption and first rows | clean |
| 21 | 774–799 | Table 5 continued (header repeated), footnotes, Figure 4 and caption, 4.4 bullets | clean |
| 22 | 800–837 | 4.5–4.7; blank space below because Table 6 is kept whole | clean |
| 23 | 838–853 | Table 6 with caption and footnotes | clean |
| 24 | 854–871 | Table 7 with caption and footnotes | clean |
| 25 | 872–895 | Figure 5 and caption, 4.7 bullets | clean |
| 26 | 896–924 | 4.7, 4.8, Table 8 caption and first rows | clean |
| 27 | 925–958 | Table 8 continued (header repeated), footnotes, 4.8 bullets | clean |
| 28 | 959–998 | 4.8, 4.9, Table 9 with caption and footnotes | clean |
| 29 | 999–1022 | 4.9, 4.10, Figure 6 and caption, Table 10 with caption | clean |
| 30 | 1023–1061 | Paragraph after Table 10, 4.10 bullets, 4.11; blank space below because Table 11 is kept whole | clean |
| 31 | 1062–1102 | Table 11 with caption, 4.11 text and bullets, 5. Discussion, 5.1 | clean |
| 32 | 1103–1152 | 5.1, 5.2 | clean |
| 33 | 1153–1201 | 5.2, 5.3 | clean |
| 34 | 1202–1251 | 5.3, 5.4, 5.5 Limitations 1–4 (numbering restarts at 1) | clean |
| 35 | 1252–1301 | Limitations 5–8, 6. Conclusions, Supplementary Materials | clean |
| 36 | 1302–1349 | Supplementary Materials list (Figures S1–S4, Tables S1–S44), Author Contributions, Funding, IRB, Informed Consent, Data Availability (placeholders) | clean |
| 37 | 1350–1382 | Data Availability (code, release, controller-event paragraphs), Acknowledgments (GenAI tools), Conflicts of Interest, Abbreviations table (space above the table after fix R8) | clean |
| 38 | 1383–1433 | References 1–19 (left-aligned, DOIs unbroken) | clean |
| 39 | 1434–1460 | References 20–31 | clean |

## Final status

| QA pass | Resolution | Pages inspected | Issues found | Fixes applied | Status |
|---|---|---|---|---|---|
| Previous | 80 dpi | 39 of 39 | R1–R7 above | R1–R7 | PASS |
| Final | 180 dpi | 39 of 39 | 1: page 37, a text line touching the table rule | R8 | PASS |

**PASS — HIGH-RESOLUTION VISUAL QA.** All 39 pages of the final render were inspected at 180 dpi. No clipping,
overlap, page-edge overflow, broken glyph, missing symbol, illegible table text, figure distortion, unreadable axis
label or legend, separated caption, orphan heading or header/footer collision remains.
