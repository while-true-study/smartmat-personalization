# Supplementary QA — structure, workbook and page-by-page render

| Field | Value |
|---|---|
| Files | `paper/submission_final/supplementary/Supplementary_Materials.docx` (SHA-256 472e2fb96217748027d957f30fff4c3ae3b0f197431e44c2f183e49b9189acc8); `paper/submission_final/supplementary/Supplementary_Tables_S1-S44.xlsx` (SHA-256 041775c2e52d3c99367f2575a6cf432afe15d16db35ff32bd3832503fa83855c) |
| Source | `paper/submission_p16/supplementary/` (tables, figures, README index) and the Supplementary Materials paragraph of the P16 manuscript (figure captions) |
| Template | the same Applied Sciences Word template as the main manuscript, read in place; no article-type line, left-aligned text |
| Renderer | Microsoft Word 16.0 (build 16.0.20326) through `scripts/render_docx_pages.ps1`, then PyMuPDF. Previous QA: 80 dpi. Final QA: **180 dpi**, full pages and top and bottom halves. Final PDF sha256 3f3bfce3ef291c35…; the PDF and images are in the uncommitted `work/` folder |
| Pages | 8. Every page was inspected at 80 dpi (previous QA) and again at 180 dpi (final QA), with no spot check. |

## Structure of the supplementary submission

- **Supplementary_Materials.docx:**
  - title and manuscript title;
  - a short note;
  - the list of Tables S1–S44 with their P16 titles, each naming the worksheet(s) that hold it;
  - Table S19 (reproduction record), in full;
  - Figures S1–S4 with their P16 captions.
- **Supplementary_Tables_S1-S44.xlsx:**
  - an Index sheet;
  - one worksheet per table part: 81 worksheets for the 43 tables with CSV data (S1–S18, S20–S44), 8,513 data rows,
    up to 37 columns;
  - every value stored as text exactly as in the source CSV (full precision, no spreadsheet rounding);
  - no author or date metadata beyond a fixed creation date;
  - built deterministically.
- **Deviation from the request, and why:** the request lists Tables S1–S44 inside the supplementary DOCX.
  - As Word pages, 8,513 rows and up to 37 columns could not be set legibly at the journal's minimum font size
    without reducing or splitting the tables. The instruction was not to shorten table content.
  - The tables therefore travel losslessly in the workbook, to be uploaded as a second supplementary file. Confirm
    the accepted file types in the submission system.
  - The DOCX lists every table with its number, title and worksheet.
  - Table numbering S1–S44 is unchanged.
- Figure S5 is neither created nor mentioned.

## Checks performed

| Check | Result |
|---|---|
| Tables S1–S44 listed in order, each once | yes (44) |
| Every worksheet equal, cell by cell, to its source CSV | yes (81 of 81) |
| Figures S1–S4: inline images from the P16 files, captions from P16, in order | yes (4) |
| Table S19 reproduction record | complete: the verbatim sections 6 and 8–10 of the P7 reproducibility report, with its 4 tables |
| Figure S5, night-series or night-event assets | absent |
| Local paths, user names, e-mail addresses, calendar dates, comments, tracked changes, hidden text, author properties (DOCX and workbook) | none |

## Render iterations

| Iteration | Issues found | Fix applied |
|---|---|---|
| S1 | "Article" type line on the title page. | Removed for the supplementary document. |
| S1 | Justified lines stretched by long worksheet names and command lines (pages 2 and 4). | Left-aligned body text and lists. |
| S1 | List items and paragraphs directly against the bottom rule of the reproduction tables (pages 5 and 6). | 6 pt of space after a table (the main-manuscript fix). |
| S2 (180 dpi) | none of its own. The main-manuscript fix R8 (space after a body paragraph that directly precedes a table) also applies here: the lines "Local core result …:" and "Local extended result …:" now have 6 pt above their tables. | Only page 5 changed; the word positions of the other 7 pages are identical. |
| Final | none | All 8 pages inspected again at 180 dpi. |

## Page-by-page result (final render, 180 dpi)

| Page | Content | Result |
|---|---|---|
| 1 | Journal header, title "Supplementary Materials", manuscript title, note, Supplementary Tables list S1–S20 | clean |
| 2 | Tables list S21–S40 (left-aligned; long worksheet names wrap without stretched spacing) | clean |
| 3 | Tables list S41–S44, Reproduction Record (Table S19): introduction, section 6 table (11 files with sizes and hash prefixes), manifest bullets | clean |
| 4 | Byte-exact storage and builder-fix bullets, section 8 core workflow (numbered steps 1–6 with nested bullets) | clean |
| 5 | Core-result table, section 9 extended reproduction, extended-result table, section 10 setup bullets | clean |
| 6 | Clean-checkout result table, closing bullets, Supplementary Figures heading, Figure S1 and caption | clean |
| 7 | Figures S2 and S3 with captions | clean |
| 8 | Figure S4 and caption | clean |

Long tables, repeated headers and table splitting do not apply: the four reproduction tables are short and each stays on
one page. The symbols (→, ×, §, ≥, –, …) render correctly. Figure axis labels, tick labels and legends of Figures S1–S4 are legible at 180 dpi.

The Figure S1–S4 captions end without a full stop, because they are copied verbatim from the P16 caption list. The text was not changed.

## Final status

| QA pass | Resolution | Pages inspected | Issues found | Fixes applied | Status |
|---|---|---|---|---|---|
| Previous | 80 dpi | 8 of 8 | 3 (S1 above) | S1 | PASS |
| Final | 180 dpi | 8 of 8 | none of its own | R8 applied, page 5 | PASS |

**PASS — HIGH-RESOLUTION VISUAL QA** for the supplementary DOCX (all 8 pages at 180 dpi; structure checks pass).
**PASS** for the workbook (final QA below).

## Workbook final QA (Supplementary_Tables_S1-S44.xlsx, unchanged by this step)

| Check | Result |
|---|---|
| Opens (openpyxl, read-only) | yes |
| Sheets | 82: Index plus 81 data sheets |
| Rows | 8,513 data rows (8,594 including the 81 header rows); up to 37 columns |
| Coverage of Tables S1–S44 | complete: 43 tables in 81 sheets, and Table S19 in the supplementary DOCX |
| Equality with the source CSVs | 81 of 81 sheets equal, cell by cell |
| Formulas / error cells | 0 / 0 |
| Hidden or very hidden sheets, defined names | none |
| External links, external relationship targets | none |
| Macros (vbaProject, macro-enabled content type) | none |
| Windows absolute paths, local folder names, e-mail addresses | none |
| Document properties | empty creator; fixed created and modified dates (2026-01-01) |
| Participant metadata (names, ages, sex, contact data) | none |
| Raw or private data (sensor logs, timestamps, clock times, calendar dates) | none; long digit strings are decimal fractions of result values |
| Heater-event sequence | none; S41 holds aggregate counts per control code and subject, without times or order |
| Figure S5 data, night-series or night-event assets | none |
