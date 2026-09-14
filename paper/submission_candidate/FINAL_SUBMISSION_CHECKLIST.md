# Final submission checklist

> Tick an item only when it is done and recorded; do not tick it on an assumption. Details and options:
> `docs/P8_PI_APPROVAL_CHECKLIST.md`. Open blockers: `docs/P8_FINAL_BLOCKERS.md`.
>
> The file is ready for submission only when every box is ticked and
> `python scripts/validate_manuscript_results.py --final --docx <built DOCX>` reports READY.

**State at the end of the P8 submission-closure pass: no item ticked.** The draft validation passes (11/11). The
final-readiness check reports the open placeholders and the pending conference bibliography.

## Scientific

- [ ] PI scientific approval (no result, statistic or interpretation boundary changes at this step)
- [ ] Title approved (working final title, D-054)
- [ ] Abstract approved (200 words; source-linked numbers)
- [ ] Tables 1–5 approved
- [ ] Figures 1–4 approved
- [ ] Limitations approved

## Authorship

- [ ] Author list and order (decided for this journal study, not copied from the conference paper)
- [ ] Affiliations (PubMed/MEDLINE address format)
- [ ] Corresponding author and e-mail; consent of all authors to show their e-mails
- [ ] ORCID iDs
- [ ] CRediT roles (only the roles actually performed)

## Compliance

- [ ] Funding (conference grant only if confirmed to apply)
- [ ] IRB: approval (code, date, committee), exemption, or the legislation that exempts it
- [ ] Informed consent statement
- [ ] Conflicts of interest
- [ ] GenAI disclosure approved (OPEN-28; D-053 → Accepted)
- [ ] Conference extension: first-page note, Introduction paragraph, cover-letter statement of the changes
- [ ] Conference copyright holder and permission status; conference bibliography (OPEN-27)

## Availability

- [ ] Code license
- [ ] Data license
- [ ] Code scope (repository date exposure policy, OPEN-25)
- [ ] Data scope (release subset approval, OPEN-24)
- [ ] Hosting
- [ ] DOI / persistent identifier
- [ ] Data Availability Statement final state (A–E) written as true

## Formatting

- [ ] Live Applied Sciences Instructions page re-read; current template version confirmed
- [ ] DOCX built from the current template: `python scripts/build_submission_docx.py --template <template.docx>`
- [ ] References checked in the DOCX (numbering, abbreviations, DOIs, conference details)
- [ ] Keywords confirmed
- [ ] Featured Application kept or removed
- [ ] Supplementary material uploaded (Tables S1–S19, Figures S1–S4) and listed in the back matter
- [ ] Cover letter completed and every author's approval obtained
