# DOCX structural QA — main manuscript

| Field | Value |
|---|---|
| File | `paper/submission_final/manuscript/Applied_Sciences_SmartMat_Final.docx` |
| SHA-256 | 15fcadfe3996e0cd89440c7422009b2aafa9bf82b3b6050bc16949b749716810 |
| Source | `paper/manuscript/manuscript_p16_final.md`, as rendered in `paper/submission_p16/manuscript/manuscript_p16_final_rendered.md` (source commit 62b1618c5df5726d1bc3b9cf7277e7dc7db35a2f); tables and figures from `paper/submission_p16/` |
| Template | `applsci-template.docx` (MDPI Applied Sciences Word template, OOXML), read in place from the authors' journal folder and not copied into the repository. Styles, numbering, theme, fonts, headers, footers and page setup come from the template. |
| Build | `python scripts/build_final_submission.py --template <applsci-template.docx>` (`src/paper/docx_export.py` in layout mode; deterministic: a rebuild gives the same bytes) |
| Pages | 39 (Microsoft Word 16.0 rendering; see DOCX_VISUAL_QA.md) |
| Checks | `python scripts/validate_final_submission.py` (logic in `src/paper/final_submission.py`) |

## Checks performed

| Check | Result |
|---|---|
| Paragraphs in the body | 1,555 |
| Section headings (MDPI heading styles 1–3) | 45, identical in text and order to the P16 headings (Abstract and back-matter titles are run-in labels, as in the template) |
| Numbered tables | 11 (Tables 1–11, captions in order) plus the Abbreviations table; 12 Word tables in total |
| Figures | 6 inline images (Figures 1–6, captions in order), from the P16 PNG files; aspect ratio kept, no recompression |
| Figure files for upload | `paper/submission_final/figures/`: the 6 files, byte-identical to `paper/submission_p16/figures/` |
| References | 31 entries in the MDPI_8.1_references style, numbered 1–31 (see `metadata/REFERENCE_FINAL_CHECK.md`) |
| Back matter | Supplementary Materials, Author Contributions, Funding, Institutional Review Board Statement, Informed Consent Statement, Data Availability Statement, Acknowledgments, Conflicts of Interest, all present in MDPI order; Abbreviations and References follow |
| Generative-AI disclosure | Section 3.8 and the Acknowledgments, P16 wording unchanged |
| External placeholders | 16 `[CONFIRM BEFORE SUBMISSION: …]` items, identical in text and order to the P16 source; nothing filled in |
| Unresolved tokens `{{…}}` or citation keys `[@…]` | none |
| Figure S5 or the withdrawn night-series and night-event assets | absent |
| TODO, FIXME, internal-review or revision-stage strings | none |
| Data or code offered "upon request" (not permitted) | absent |
| Sensor-placement wording ("physiological microclimate", "body–bed interface", "skin-interface") not in P16 | none introduced |
| Captions and cross-references | Captions and in-text references are static text copied from P16, and the numbering is checked above. The body has no Word fields, so no caption or cross-reference can go stale. The only fields are the template's PAGE and NUMPAGES fields in the running header, which update on rendering. |

## Scientific equivalence with P16

| Check | Result |
|---|---|
| Title | identical |
| Abstract (198 words) | identical text |
| Keywords (8) | identical |
| Conclusions | identical text |
| Every number in the body (text, tables, captions, footnotes) | the same multiset as in the P16 rendered manuscript; list markers that Word renumbers itself are excluded |
| Tables 1–11 | values, decimal places, units and footnotes as in P16; no bold added |
| P16 source, references.bib, P16 package and the P8-era cover letter | unchanged since the source commit (`git diff` against 62b1618 is empty) |

Line breaks inside table cells are controlled with invisible characters only:
- a zero-width space after "+" in feature-family names;
- no-break spaces inside "value (low–high)", "mean ± sd", "[low, high]" and "b = 0";
- non-breaking hyphens.

The text extraction used for the equivalence check maps them back, so the visible text is unchanged.

## Privacy and document metadata

| Check | Result |
|---|---|
| Local, user or temporary paths (document, styles, settings, relations, properties) | none |
| Attached-template link to a local path | removed |
| Document properties | title only; no creator, last-modified-by or company |
| Comments, tracked changes, hidden text | none |
| Customised XML and custom properties of the template | not carried over |
| E-mail addresses or calendar dates outside the reference list | none |

## Issues found and fixes applied

All fixes are layout only, in `src/paper/docx_export.py` layout mode. Default mode is unchanged, so the P8 build is not affected.

| Issue | Fix |
|---|---|
| Limitations numbered 5–12, continuing the contributions list | each numbered list restarts at 1 (numbering instances with a start override) |
| Abbreviations table counted as a 12th table | the structural check counts it separately |
| Table S19 listed twice in the supplementary list | the reproduction-record heading names it once |

The render-driven layout fixes are listed in DOCX_VISUAL_QA.md.

## Final status

**PASS.** Every structural, equivalence and privacy check above passes on this file; the validator reruns them.
