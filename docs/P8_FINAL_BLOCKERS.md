# P8 — Final blockers before submission, the P8 PR and `v1.0-paper`

> **State after the final dynamic-signal diagnostic** (branch `paper/p8-manuscript`). The post-hoc validation
> analyses (D-057) and the final dynamic-signal diagnostic (D-059) ran as pre-registered. The manuscript was
> reframed as a strict evaluation against simple level baselines, with a new working title (D-058, D-060).
> Scientific experimentation for this manuscript has stopped (D-059 stop rule). The
> conference bibliography is resolved (D-056); the PI handoff is `docs/P8_PI_REVIEW_REQUEST_KO.md`.
> - The manuscript is formatting-complete and in the Applied Sciences back-matter order. A Word file can be built
>   from the local template (`scripts/build_submission_docx.py`; not committed).
> - **No PI input has been received:** every PI metadata and release item below is still open. Each open item appears
>   as a bracketed placeholder in the manuscript or drafts, never as a fact.
> - `python scripts/validate_manuscript_results.py` passes (11/11). With `--final` it reports **NOT READY** while any
>   item below is open.
> - The PI's decisions are collected in `docs/P8_PI_APPROVAL_CHECKLIST.md`.

## A. Scientific blockers

**None open in the analyses.** All results and claims are fixed and validated. PI scientific approval is still
pending, and it now includes the revised interpretation and scientific identity (D-058, D-060). The post-hoc comparators show that the personalization
gains were mainly level corrections and that the pressure models showed no demonstrable within-subject tracking; the
manuscript is framed as an evaluation with a substantial negative result (`docs/P8_POSTHOC_VALIDATION_REPORT.md` §6).
See `docs/P8_PI_APPROVAL_CHECKLIST.md`, "Scientific content". No result may change during that review.

## B. Metadata blockers (PI / authors)

| # | Item | State | Placeholder | Tracking |
|---|---|---|---|---|
| B1 | Authors, order, affiliations (PubMed format), corresponding author and e-mail, ORCID | BLOCKED | `[AUTHOR NAMES AND ORDER — CONFIRM]`, `[AFFILIATIONS — CONFIRM]`, `[NAME AND E-MAIL — CONFIRM]`, `[ORCID iDs — CONFIRM]` | — |
| B2 | CRediT roles | BLOCKED | `[CRediT ROLES — CONFIRM]` | — |
| B3 | Funding (the conference grant only if confirmed to apply) | BLOCKED | `[FUNDING TO BE CONFIRMED BY PI]` | — |
| B4 | Conflicts of interest; other acknowledgments | BLOCKED | `[CONFLICTS OF INTEREST — CONFIRM]`, `[OTHER ACKNOWLEDGMENTS — CONFIRM]` | — |
| B5 | Ethics: IRB approval (code, date, committee), exemption, or the legislation that exempts the study. Provider permission is not one of these | BLOCKED | `[ETHICS / IRB INFORMATION REQUIRED FROM PI]` | OPEN-26 |
| B6 | Informed consent statement | BLOCKED | `[INFORMED CONSENT WORDING REQUIRED FROM PI]` | OPEN-26 |
| B7 | GenAI disclosure approval | drafted; PI approval pending | §3.8 and Acknowledgments | OPEN-28; D-053 (Proposed) |
| B8 | Conference bibliography | **RESOLVED** (D-056): title, authors, year, Vol. 17, No. 1, pp. 27–30, e-ISSN 2765-3811, print ISSN 2384-3004, KIICE, 7–10 July 2026, Sapporo. **Open, not blocking:** official confirmation that no DOI exists; a paper-specific URL. Neither is printed | `unconfirmed` field in `references.bib` | OPEN-27 |
| B9 | Conference copyright holder and reuse-right status | BLOCKED. **A submission-compliance item** (Applied Sciences condition 3; cover letter), **not a manuscript blocker**: no conference text, table or figure is reused. Needed before submission | `[COPYRIGHT HOLDER — CONFIRM]` in the cover letter and disclosure draft | OPEN-27 |
| B10 | Scientific identity, final title, keywords, Featured Application | identity reframed as a strict evaluation against simple level baselines; working title "Strict Unseen-Domain Evaluation of Smart-Mat Microclimate Estimation against Simple Level Baselines" (D-060; earlier titles recorded); eight keywords; Featured Application revised; PI approval required | — | D-054, D-058, D-060 |
| B11 | Every author's approval of the submission (mandatory cover-letter statement) | BLOCKED | `[CONFIRM: every author has approved]` | — |
| B12 | Target Special Issue: Applied Sciences "Future Information & Communication Engineering 2026" (section Computing and Artificial Intelligence; Guest Editors Yun Seop Yu, Dae-hwan Kim, Daesung Lee; deadline 30 June 2027; selected papers from ICFICE 2026) | RECOMMENDED / PI CONFIRMATION REQUIRED | `[TARGET SPECIAL ISSUE — PI CONFIRMATION REQUIRED]` in the cover letter | D-056 |

## C. External-release blockers

| # | Item | State | Tracking |
|---|---|---|---|
| C1 | Code license (options only; not chosen) | BLOCKED | OPEN-22 |
| C2 | Data license (options only; not chosen) | BLOCKED | OPEN-22 |
| C3 | Hosting (Zenodo / Figshare / OSF / institutional / GitHub Release with DOI; nothing uploaded) | BLOCKED | OPEN-23 |
| C4 | DOI / persistent identifier strategy | BLOCKED | OPEN-23 |
| C5 | PI approval of the release subset and of the final release | BLOCKED | OPEN-24 |
| C6 | Repository public-date exposure policy (whole / sanitized copy / release snapshot / code-only archive; no history rewrite without a decision) | BLOCKED | OPEN-25 |
| C7 | Data Availability final state (A public before submission, B after acceptance, C on request, D derived data only, E restricted) and the Code Availability wording | BLOCKED | depends on C1–C6 |

Whether hosting and a DOI are needed **before** submission depends on the state chosen in C7. The journal requires an
accurate statement at submission (restrictions disclosed), not a deposit (`docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`
item 11).

## D. Submission-format blockers

| # | Item | State |
|---|---|---|
| D1 | Re-read the live Applied Sciences Instructions page (requirements were verified from its 2025-11-17 archived copy) | NEEDS FINAL CHECK |
| D2 | Confirm the current template version (the local template is the 2025 version) and rebuild the DOCX from it | NEEDS FINAL CHECK |
| D3 | Special Issue page read directly before submission. The authors read it; mdpi.com is blocked here | NEEDS FINAL CHECK (B12) |
| D4 | Cover letter completion (`paper/manuscript/COVER_LETTER_DRAFT.md`) | final draft; placeholders B1, B3–B6, B9, B11, B12 |

**Resolved in the closure pass:**
- section structure checked against the instructions;
- references in the journal patterns: NLM ISO abbreviations, conference locations and dates from Crossref;
- first-page conference note (a verified requirement);
- abbreviations defined at first use;
- software versions stated in Methods;
- back matter in the template order;
- supplementary list in the "Figure S1: title" form;
- DOCX builder with the MDPI styles.

## G. Generative-AI tools (OPEN-28, D-053)

| Product | Provider | Model / version | Evidence | Purpose |
|---|---|---|---|---|
| Claude Code (command-line client) | Anthropic | CLI 2.1.263 and 2.1.270; Claude Opus 5 (`claude-opus-5`) | local session logs of this repository | code drafting and debugging; analysis-workflow organization; repository documentation; reference-metadata checks; manuscript drafting |
| ChatGPT | OpenAI | historical model versions not consistently logged (stated as such, not inferred); GPT-5.6 Sol for the final manuscript review | authors' statement | research planning; analysis and protocol review; manuscript architecture; drafting; language refinement; consistency review |

## Readiness rules

- **P8 PR — ready only when** all of the following hold:
  - PI scientific approval;
  - B1–B7 resolved (B8 is resolved);
  - D1 and D2 confirmed;
  - `validate_manuscript_results.py --final --docx <DOCX>` reports READY.
  - C1–C7 must be resolved as far as the chosen Data Availability state requires.
- **`v1.0-paper`:**
  - created only after the P8 PR is merged, on the P8 merge commit on `main`, never on a branch head;
  - requires the final artifact validated, the submission metadata fixed, and the frozen P3–P7 artifacts unchanged
    against `p7-release-candidate`.

## Conference venue: source conflict

| Source | ICFICE 2026 venue |
|---|---|
| Official KIICE ICFICE 2026 programme and presenter guide (**primary**) | ANA Crowne Plaza Sapporo, Japan, 7–10 July 2026 |
| Current Applied Sciences Special Issue page | Hotel Nikko Guam, USA |

**Policy (D-056):**
- the KIICE programme is used for the conference's bibliographic and venue data;
- the manuscript and its references say Sapporo, Japan;
- the Special Issue page's Guam wording is not copied as conference provenance;
- the cover letter omits the venue;
- the discrepancy is not discussed in the manuscript.

