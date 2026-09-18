# Submission checklist — Applied Sciences

**Manuscript:** *Strict Unseen-Domain Evaluation of Pressure-Based Smart-Mat Temperature and Humidity Estimation against
Simple Level Baselines*

**Status:** submission artifacts complete, metadata pending. Not yet ready to send.

## A. Complete internally

- [x] Scientific manuscript frozen (P16, source commit 62b1618). No result, table value, figure or claim changed in this step.
- [x] Title (final).
- [x] Abstract (198 words).
- [x] Keywords (8).
- [x] Main manuscript in the Applied Sciences Word template: `manuscript/Applied_Sciences_SmartMat_Final.docx`, 39 pages.
- [x] Tables 1–11 and Figures 1–6 in the manuscript. The figure files, byte-identical to P16, are in `figures/`.
- [x] Supplementary files:
  - `supplementary/Supplementary_Materials.docx` (8 pages): table list, Table S19, Figures S1–S4;
  - `supplementary/Supplementary_Tables_S1-S44.xlsx`: every supplementary table at full precision.
- [x] References: 31. Every citation resolves, there are no duplicates, and no DOI was changed (`metadata/REFERENCE_FINAL_CHECK.md`).
- [x] Word formatting: headings, captions, table layout, numbered lists, references, back-matter order (`qa/DOCX_STRUCTURAL_QA.md`).
- [x] Visual QA: every page of both Word files rendered and inspected (`qa/DOCX_VISUAL_QA.md`, `qa/SUPPLEMENTARY_QA.md`).
- [x] Privacy QA: no local paths, personal document properties, comments, tracked changes or hidden text.
- [x] Scientific equivalence with P16: title, abstract, keywords, conclusions and every number identical.
- [x] Cover letter draft updated to the final title (`cover_letter/cover_letter_final_draft.md`).
- [x] Validator: `python scripts/validate_final_submission.py`.

## B. External confirmation required (18 items)

Please send these to the corresponding author. Details are in `metadata/FINAL_METADATA_CHECKLIST.md`.

| # | What is needed | From whom |
|---|---|---|
| M01 | Final author names and their order | PI and all co-authors |
| M02 | Affiliation of every author | Each author |
| M03 | Corresponding author and e-mail | PI |
| M04 | ORCID iDs | Each author |
| M05 | Copyright holder of the ICFICE 2026 conference paper and reuse status (nothing is reused) | PI |
| M06 | Temperature/humidity sensor model(s) | Data provider |
| M07 | Sensor accuracy (°C, %RH) | Data provider |
| M08 | Sensor resolution | Data provider |
| M09 | Sensor response time | Data provider |
| M10 | Sensor position in the mat and relative to the heater | Data provider |
| M11 | Approval of the generative-AI disclosure (Section 3.8 and Acknowledgments) | All authors |
| M12 | CRediT roles and every author's approval of the submitted version | All authors |
| M13 | Funding statement (or "no external funding") | PI |
| M14 | IRB approval, exemption or waiver, and permission for secondary use of the recordings | PI, with the IRB and the data provider |
| M15 | Informed consent statement | PI, with the IRB and the data provider |
| M16 | Data and code release: scope, repository, persistent identifier and licenses; data-provider approval for the aggregate heater-diagnostic results and code | PI and data provider |
| M17 | Acknowledgments | PI and all co-authors |
| M18 | Conflicts of interest, including any funder role | Each author |

**Cover letter only:**
- submission date;
- editor name;
- target section and Special Issue;
- prior MDPI submissions.

**When the answers arrive:**
1. Replace each `[CONFIRM BEFORE SUBMISSION: …]` placeholder in the final Word file
   (`manuscript/Applied_Sciences_SmartMat_Final.docx`) and in the cover letter with the confirmed value.
2. Nothing else in the manuscript changes.
3. Re-render and inspect the changed pages, then update the QA reports and the manifest.
