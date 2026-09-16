# P8 — PI approval checklist

> **The inputs only the PI or the rights holders can give.** Nothing below is filled by assumption.
> - Answer in place, or in the Korean request `docs/P8_PI_REVIEW_REQUEST_KO.md`.
> - After each answer: write it into the manuscript source, record it in `docs/DECISIONS.md`, rebuild with
>   `scripts/build_submission_candidate.py`, and run `scripts/validate_manuscript_results.py --final`.
> - Journal rules are from the Applied Sciences instructions (`docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`).
>
> **State (metadata-resolution pass): no PI answer received.** Resolved without the PI: the conference bibliography
> (D-056).

## A. Authorship — BLOCKED

- [ ] Final author list (full first and last names): ______
- [ ] Author order, decided for this journal study rather than copied from the conference paper: ______
- [ ] Affiliation of each author (department, institution, city, postcode, country): ______
- [ ] Corresponding author and e-mail: ______. All authors' e-mails are published; each author must consent.
- [ ] ORCID iDs: ______
- [ ] CRediT roles. Only the roles each author actually performed; unused roles are left out:
  - Conceptualization ______, Methodology ______, Software ______, Validation ______, Formal analysis ______,
    Investigation ______, Resources ______, Data curation ______
  - Writing—original draft ______, Writing—review and editing ______, Visualization ______, Supervision ______,
    Project administration ______, Funding acquisition ______
- [ ] All authors approved the submission (mandatory cover-letter statement): yes / no

## B. Ethics — BLOCKED (highest priority)

Mark exactly one route. Without one of them, "ethical approval was not required" may not be written:
- [ ] 1. IRB approval: committee/institution ______; approval number ______; approval date ______
- [ ] 2. IRB or ethics-committee exemption: institution ______; exemption/reference number (if any) ______; reason
  ______
- [ ] 3. Review not required by law or regulation: the legislation or institutional rule that applies ______

The data provider's permission to use and release the data (D-002) is none of these routes.

## C. Consent — BLOCKED

- [ ] Was informed consent for participation obtained? yes / no (form: written / verbal / other ______)
- [ ] Is separate consent for publication needed? No participant is identifiable; confirm: yes / no
- [ ] Exact wording for the manuscript: ______

## D. Funding — BLOCKED

- [ ] Does the conference paper's grant also fund this journal study? yes / no
- [ ] Funder(s): ______; grant number(s): ______; author(s) responsible for funding acquisition: ______
- [ ] APC funding (if any): ______

## E. Conflicts of interest — BLOCKED

- [ ] None, or the exact statement: ______

## F. GenAI disclosure — [CONFIRM]

- [ ] Approve the draft in §3.8 and the Acknowledgments (D-053):
  - Claude Code (Anthropic; CLI 2.1.263 and 2.1.270; Claude Opus 5): code drafting, debugging,
    analysis-workflow organization, repository documentation, reference-metadata checks, manuscript drafting;
  - ChatGPT (OpenAI): research planning, protocol/analysis review, manuscript architecture, drafting, language
    refinement, consistency review. Historical model versions were not consistently logged; GPT-5.6 Sol was used for
    the final manuscript review.
  Approve as written / change: ______

## G. Release — BLOCKED

- [ ] Approve `public_release_v1` (three subjects, four mat streams, relative time, no raw logs or metadata):
  yes / no
- [ ] Code license (e.g. MIT, BSD-3-Clause, Apache-2.0, GPL-3.0, or none): ______
- [ ] Data license (e.g. CC BY 4.0, CC BY-NC 4.0, CC0, controlled access): ______
- [ ] Hosting (Zenodo / Figshare / OSF / institutional repository / GitHub Release with an archival DOI): ______
- [ ] DOI strategy (before submission / at acceptance / none): ______
- [ ] Public scope of the code: whole repository / sanitized copy / release snapshot / code-only archive: ______
- [ ] Is exposing the session-level recording dates in the committed history acceptable? yes / no
- [ ] Data Availability state: A public before submission / B after acceptance / C on request / D derived data only /
  E restricted: ______

## H. Journal — [CONFIRM]

- [ ] Submit to *Applied Sciences*, Special Issue "Future Information & Communication Engineering 2026" (section
  Computing and Artificial Intelligence; selected papers from ICFICE 2026; deadline 30 June 2027)? yes / no
- [ ] Copyright holder of the ICFICE 2026 paper, and whether its reuse terms need a permission (no conference material
  is reused): ______
- [ ] Scientific identity: a strict evaluation / failure-analysis study against simple level baselines (D-060),
  instead of a neural-personalization study: approve / comments ______
- [ ] Title: the working title "Strict Unseen-Domain Evaluation of Smart-Mat Microclimate Estimation against Simple
  Level Baselines" (D-060) / the alternative in `docs/P8_TITLE_CANDIDATES.md` §7 / an earlier title (D-058, D-054) /
  other: ______
- [ ] Keep the eight keywords and the revised Featured Application? yes / changes: ______
- [ ] Scientific approval of the abstract, tables, figures and limitations, including the post-hoc validation
  (Tables 6–7, Figure 5, the A/B/D columns of Table 4; D-057), the dynamic-signal diagnostic (Table 8; D-059) and
  the revised interpretation (D-058, D-060). No result may change at this step: yes / comments ______
- [ ] Additional external validation on User03 (post hoc; Section 3.5.7, Section 4.9, Table 9, Tables S32–S34;
  D-061): keep in the submission / withdraw / comments ______
- [x] **OPEN-29 — closed 2026-09-16 (D-062), no PI action required.** The data provider confirmed that the setting
  problem reported for the excluded auxiliary folder does not affect the second-level timestamps of the seven
  complementary User03 exports. The confirmation was relayed by the PI and recorded on 2026-09-16; the
  correspondence is private and is not reproduced in the repository. The P9 results are no longer conditional, the
  withdrawal contingency has lapsed, and no number changed.
