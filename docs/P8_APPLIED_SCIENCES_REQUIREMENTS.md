# P8 — Applied Sciences submission requirements

> **No item below is marked VERIFIED.**
> - On 2026-09-14, every official MDPI page tried returned HTTP 403 to automated access, both via WebFetch and a direct
>   request: the journal's Instructions for Authors, the Word template file, the layout, LaTeX and ethics pages.
> - The only available evidence is web-search summaries of the official mdpi.com pages, retrieved the same day. They
>   are secondary: the page itself was not read.
> - Every item is therefore **NEEDS FINAL CHECK** and must be confirmed against
>   https://www.mdpi.com/journal/applsci/instructions (and the pages linked there) before formatting and submission.
> - Where nothing was found, the item says so. No requirement is invented; in particular, **no fixed "percentage of
>   new content" for extended conference papers was found**, so none is assumed.

| # | Requirement | Evidence (source, 2026-09-14) | Status | Manuscript consequence |
|---|---|---|---|---|
| 1 | Research-article structure: required sections are author information, Abstract, Keywords, Introduction, Materials and Methods, Results, Conclusions, figures and tables with captions, funding, author contributions, conflicts of interest and other ethics statements | search summary of the Applied Sciences Instructions for Authors | NEEDS FINAL CHECK | Sections: 1 Introduction, 2 Related Work, 3 Materials and Methods (the experimental protocol becomes §3.5–§3.6), 4 Results, 5 Discussion, 6 Limitations, 7 Conclusions. Check that a separate Related Work and Limitations section is acceptable; otherwise Related Work moves into §1 and Limitations into §5. Content does not change |
| 2 | Word and LaTeX templates | search result lists an Applied Sciences Word template file on mdpi.com; LaTeX template not reached | NEEDS FINAL CHECK | Markdown stays the drafting source; conversion to the template comes after the prose is stable |
| 3 | Abstract: about 200 words at most, one paragraph, structured without headings (background, methods, results, conclusions) | search summary of the Instructions for Authors | NEEDS FINAL CHECK | Abstract written in the next pass, after the body is stable, to about 200 words |
| 4 | Keywords: three to ten | search summary of the Instructions for Authors | NEEDS FINAL CHECK | keep the list at ≤ 10 (currently 8, to be finalised) |
| 5 | Author Contributions (MDPI refers to the CRediT taxonomy) | search summary of MDPI author/ethics pages | NEEDS FINAL CHECK | [PI] |
| 6 | Funding statement | search summary (required section list) | NEEDS FINAL CHECK | [PI]; the conference acknowledgment's funding is not copied automatically |
| 7 | Institutional Review Board Statement and Informed Consent Statement (research involving humans) | search summary ("other ethics statements"); the exact wording was not reached | NEEDS FINAL CHECK | `[ETHICS / IRB INFORMATION REQUIRED FROM PI]`. The provider's consent confirmation (D-002) is stated as such and is not an IRB approval |
| 8 | Data Availability Statement; MDPI Research Data Policies (FAIR sharing encouraged; deposit in a trusted repository or state why not; suggested statements on the ethics page) | search summary of MDPI instructions / research data policy | NEEDS FINAL CHECK | `DATA_AVAILABILITY_DRAFT.md` keeps `[DATA REPOSITORY]`, `[DOI]`, `[LICENSE]` until OPEN-22/23 are resolved |
| 9 | Conflicts of Interest statement | search summary | NEEDS FINAL CHECK | [PI] |
| 10 | References: numbered in square brackets before punctuation ([1], [1–3], [1,3]); any consistent style with the essential elements; DOIs encouraged; ACS Style Guide as the formatting reference | search summary of the Instructions / MDPI reference guide | NEEDS FINAL CHECK | `[CITE: …]` placeholders become numbered references in the literature pass; `references.bib` keeps DOIs |
| 11 | Supplementary materials: citations in supplementary files must also appear in the main text and the reference list | search summary | NEEDS FINAL CHECK | the supplementary tables S1–S19 cite nothing that is not also cited in the main text |
| 12 | Extended conference papers. The conditions below come from several MDPI journals' instructions (e.g. Information, Materials, Software, Modelling), not directly from Applied Sciences: the paper is expanded to the size of a research article; the conference paper is cited and noted on the first page; permission from the copyright holder if the authors do not hold it; disclosure in the cover letter with a statement of what changed | search summary of other MDPI journals' instructions | NEEDS FINAL CHECK (for Applied Sciences specifically) | The disclosure draft follows all four conditions conservatively: citation, a first-page note, a copyright check, and a cover-letter statement of changes. No numeric new-content threshold is assumed |
| 13 | Prior publication: manuscripts must not have been published or be under consideration elsewhere, except conference proceedings papers | search summary of the Applied Sciences Instructions for Authors | NEEDS FINAL CHECK | consistent with submitting an extension of the ICFICE paper; disclose it |
| 14 | Cover letter: required; concise; explains significance, context and fit with the journal scope | search summary | NEEDS FINAL CHECK | cover letter drafted after the Abstract, including the conference-extension paragraph |
| 15 | Peer review: single-blind (information) | search summary | NEEDS FINAL CHECK | the manuscript need not be anonymised (if confirmed) |
| 16 | Word count / page limit for research articles | not found | NEEDS FINAL CHECK | none assumed. The main text limits itself to 5 tables and 4–5 figures (selection doc) |
| 17 | Article processing charge (information, not a manuscript requirement) | search summary (an APC amount in CHF) | NEEDS FINAL CHECK | PI budget question; not recorded as a requirement |

## Search sources consulted (2026-09-14)

Summaries only; each official page returned HTTP 403 when opened directly:
- https://www.mdpi.com/journal/applsci/instructions (Applied Sciences Instructions for Authors)
- https://www.mdpi.com/authors/references and https://www.mdpi.com/files/authors/mdpi_references_guide.pdf (reference
  style)
- https://www.mdpi.com/ethics (research and publication ethics, research data policies)
- https://www.mdpi.com/journal/information/instructions, https://www.mdpi.com/journal/materials/instructions (other
  MDPI journals' extended-conference-paper conditions)
- https://www.mdpi.com/journal/applsci/special_issues (conference-selected Special Issues exist; the target is a
  regular submission unless the PI chooses a Special Issue)

## Final check procedure

1. Open the Applied Sciences Instructions for Authors in a browser. Confirm or correct items 1–17, recording the date
   and exact wording.
2. Download the current template, and re-map sections if required. Science content must not change.
3. Confirm the conference-extension conditions for Applied Sciences (item 12) and whether a Special Issue is
   targeted.
4. Update this file: VERIFIED only for items read on the official page.
