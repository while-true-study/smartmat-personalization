# External information crosswalk — request questions to placeholders

This file links each of the 28 external questions to the placeholder it fills. Sources:
- `FINAL_METADATA_CHECKLIST.md`: the meaning of M01–M18, and the "Cover-letter only" list;
- `EXTERNAL_INFORMATION_REQUEST.md`: the 28 questions.

No placeholder is filled here, and the manuscript is unchanged.

**ID notation:**
- Request IDs are written with two digits: A01 = A1 in `EXTERNAL_INFORMATION_REQUEST.md`, and so on.
- L01–L04 are the four cover-letter-only items, in the order of the checklist's "Cover-letter only" list: date,
  editor name, target section and Special Issue, prior MDPI submissions. The request file writes them as L1–L4.
- The checklist does not number these items; the request file assigned the IDs.

**How the placeholders were mapped:**
- Every "Target placeholder ID" is the ID the question already carries in `EXTERNAL_INFORMATION_REQUEST.md`.
- It was checked against the meaning of that ID in `FINAL_METADATA_CHECKLIST.md`.
- The placeholder text quoted in "Target section" is the text in the manuscript or cover letter.
- One ID may be filled by several questions: M05, M10, M12, M14, M16.

## Group A — Supervising professor and co-authors

| Request ID | Recipient | Question | Target placeholder ID | Target manuscript/cover-letter section | Required response format | Status |
|---|---|---|---|---|---|---|
| A01 | Supervising professor and all co-authors | Final author names and their order | M01 | Manuscript front matter, Authors — "[CONFIRM BEFORE SUBMISSION: final author names and order]"; cover-letter signature | Ordered list of full names, exactly as they should be printed | OPEN |
| A02 | Each author | Affiliation of each author | M02 | Manuscript front matter, Affiliations — "[…: affiliations]"; cover-letter signature | Per author: department, institution, city, country | OPEN |
| A03 | Supervising professor | Corresponding author and e-mail address | M03 | Manuscript front matter, Corresponding author — "[…: corresponding author and e-mail]"; cover-letter signature | Name of one author, and an institutional e-mail address | OPEN |
| A04 | Each author | ORCID iD of each author who has one | M04 | Manuscript front matter, ORCID — "[…: ORCID iDs]" | Per author: 16-digit ORCID iD (0000-0000-0000-0000), or "none" | OPEN |
| A05 | All authors | CRediT roles of each author | M12 | Manuscript back matter, Author Contributions — "[…: CRediT author contributions and every author's approval of the submitted version]" | Per author: CRediT roles from the 14 standard terms (e.g. Conceptualization, Methodology, Software) | OPEN |
| A06 | Supervising professor | Funding: funder, grant name and number, or no external funding | M13 | Manuscript back matter, Funding — "[…: funding statement; the conference paper's funding statement is not carried over]"; cover letter, Statements (Funding) | Funder name, grant or project name, grant number, and funded author(s); or "This research received no external funding" | OPEN |
| A07 | Supervising professor and all co-authors | Acknowledgments: people or support to thank, or none | M17 | Manuscript back matter, Acknowledgments — "[…: acknowledgments]" (the generative-AI paragraph there is separate, see A09) | One or two sentences naming people or support and their role, or "none" | OPEN |
| A08 | Each author | Conflicts of interest of each author, including any funder role | M18 | Manuscript back matter, Conflicts of Interest — "[…: conflicts of interest, including any funder role]"; cover letter, Statements | A statement per author, or "The authors declare no conflicts of interest"; plus the funder's role, or "The funders had no role …" | OPEN |
| A09 | All authors | Approval of the generative-AI disclosure (Section 3.8 and Acknowledgments), including the tools and versions it names | M11 | Manuscript 3.8. Use of Generative AI — "[…: approval of the generative-AI disclosure (this section and the Acknowledgments)]"; Acknowledgments (tools paragraph); cover letter, Statements ("[…: all authors approve this disclosure]") | "Approved" from every author, or corrections to the named tools and versions (only recorded versions) | OPEN |
| A10 | All authors | Every author's approval of the final manuscript for submission | M12 | Manuscript back matter, Author Contributions (same placeholder as A05; approval part); cover letter, Statements ("[…: every author has approved the submitted version]") | Written "approved" from each author, with the date of approval (kept by the corresponding author) | OPEN |
| A11 | Supervising professor and all co-authors | Code release: scope, repository URL, archive identifier and code license | M16 | Manuscript back matter, Data Availability Statement — "[…: final code release scope, with repository URL, archive identifier and code license]" (part b of M16); cover letter, Statements (Data and code) | Released scope (what code), repository URL, persistent archive identifier (e.g. DOI), license name (e.g. MIT); or "not released", with the reason | OPEN |

## Group B — Data provider

| Request ID | Recipient | Question | Target placeholder ID | Target manuscript/cover-letter section | Required response format | Status |
|---|---|---|---|---|---|---|
| B01 | Data provider | Temperature/humidity sensor model(s) | M06 | Manuscript 3.1. Data and Cohort — "[…: temperature and humidity sensor models, accuracy, resolution, response time, physical placement and placement relative to the heater]" (model part) | Manufacturer and model number of each sensor used | OPEN |
| B02 | Data provider | Sensor accuracy (°C and %RH) | M07 | Manuscript 3.1 — same placeholder as B01 (accuracy part) | ± value in °C and ± value in %RH, with the stated range, from the datasheet | OPEN |
| B03 | Data provider | Sensor resolution (the logs store whole °C and whole %RH) | M08 | Manuscript 3.1 — same placeholder as B01 (resolution part) | Resolution in °C and %RH from the datasheet, or "unknown" | OPEN |
| B04 | Data provider | Sensor response time | M09 | Manuscript 3.1 — same placeholder as B01 (response-time part) | Response time (e.g. τ63 in s) for temperature and humidity, or "unknown" | OPEN |
| B05 | Data provider | Physical sensor placement in the mat | M10 | Manuscript 3.1 — same placeholder as B01 (physical-placement part) | Short description of the position (layer, location in the mat), or "unknown" | OPEN |
| B06 | Data provider | Sensor placement relative to the heater | M10 | Manuscript 3.1 — same placeholder as B01 (heater-relative placement part) | Short description (distance or relation to the heater element), or "unknown" | OPEN |
| B07 | Data provider | Permission to redistribute the de-identified derived dataset, with the release scope | M16 | Manuscript back matter, Data Availability Statement — "[…: final data release scope and redistribution permission, with repository, persistent identifier and data license]" (part a of M16); cover letter, Statements | "Permitted" or "not permitted"; if permitted, the scope, repository, persistent identifier and data license | OPEN |
| B08 | Data provider | Approval to include the aggregate heater-diagnostic results and analysis code (the controller-event records themselves are not released) | M16 | Manuscript back matter, Data Availability Statement — "[…: data-provider approval for including the aggregate heater-diagnostic results and analysis code]" (part c of M16); cover letter, Statements | "Approved" or "not approved" (written), with any conditions | OPEN |

## Group C — Research ethics and administration

| Request ID | Recipient | Question | Target placeholder ID | Target manuscript/cover-letter section | Required response format | Status |
|---|---|---|---|---|---|---|
| C01 | Supervising professor, with the IRB | IRB approval (board, number, date), exemption or waiver | M14 | Manuscript back matter, Institutional Review Board Statement — "[…: Institutional Review Board approval, exemption or waiver, and secondary-use permission]"; cover letter, Statements (Ethics) | Board name, approval or exemption number and date; or the waiver decision and its basis | OPEN |
| C02 | Supervising professor, with the data provider | Permission for the secondary use of the recordings | M14 | Manuscript back matter, IRB Statement — same placeholder as C01 (secondary-use part); cover letter, Statements (Ethics) | Who granted it, and the date or reference of the permission | OPEN |
| C03 | Supervising professor, with the IRB | Informed consent wording | M15 | Manuscript back matter, Informed Consent Statement — "[…: informed consent statement]"; cover letter, Statements (Ethics) | One sentence: consent obtained from all subjects, waived (with the reason), or not applicable | OPEN |
| C04 | Supervising professor, with the conference publisher's terms | Copyright holder of the ICFICE 2026 conference paper | M05 | Manuscript front matter, Note on the conference paper — "[…: conference copyright holder and reuse status of the conference paper]"; cover letter, Expanded conference paper (Copyright) | Name of the copyright holder (e.g. the society or publisher) | OPEN |
| C05 | Supervising professor, with the conference publisher's terms | Reuse status or permission for conference material (the manuscript reuses no text, table or figure) | M05 | Manuscript front matter, Note — same placeholder as C04 (reuse part); cover letter, Expanded conference paper (Copyright) | "No permission required because no material is reused", or the permission reference and date | OPEN |

## Group D — Cover letter

| Request ID | Recipient | Question | Target placeholder ID | Target manuscript/cover-letter section | Required response format | Status |
|---|---|---|---|---|---|---|
| D01 | Corresponding author | Submission date | L01 | Cover letter, date line — "[CONFIRM BEFORE SUBMISSION: date of submission]" | Date written as it should appear in the letter (e.g. "15 October 2026") | OPEN |
| D02 | Corresponding author | Editor name | L02 | Cover letter, salutation — "Dear [CONFIRM BEFORE SUBMISSION: editor name]" | Editor's title and name, or "Editor" | OPEN |
| D03 | Supervising professor | *Applied Sciences* section and Special Issue | L03 | Cover letter, first paragraph — "[CONFIRM BEFORE SUBMISSION: section and Special Issue; …]" | Section name and Special Issue title, or "regular issue" | OPEN |
| D04 | Corresponding author | Previous MDPI submissions of this manuscript | L04 | Cover letter, Statements — "[CONFIRM BEFORE SUBMISSION: none, or the manuscript ID]" | "None", or the earlier MDPI manuscript ID | OPEN |

## Coverage check

| Placeholder ID | Meaning (from FINAL_METADATA_CHECKLIST.md) | Request IDs |
|---|---|---|
| M01 | Final author names and their order | A01 |
| M02 | Affiliation of every author | A02 |
| M03 | Corresponding author and e-mail address | A03 |
| M04 | ORCID iD of each author who has one | A04 |
| M05 | Conference paper copyright holder and reuse status | C04, C05 |
| M06 | Sensor model(s) | B01 |
| M07 | Sensor accuracy | B02 |
| M08 | Sensor resolution | B03 |
| M09 | Sensor response time | B04 |
| M10 | Physical sensor placement and placement relative to the heater | B05, B06 |
| M11 | Approval of the generative-AI disclosure | A09 |
| M12 | CRediT roles and every author's approval of the submitted version | A05, A10 |
| M13 | Funding statement | A06 |
| M14 | IRB approval, exemption or waiver, and secondary-use permission | C01, C02 |
| M15 | Informed consent statement | C03 |
| M16 | (a) data release and redistribution; (b) code release; (c) data-provider approval for the heater-diagnostic aggregates and code | B07 (a), A11 (b), B08 (c) |
| M17 | Acknowledgments | A07 |
| M18 | Conflicts of interest | A08 |
| L01 | Cover letter: date | D01 |
| L02 | Cover letter: editor name | D02 |
| L03 | Cover letter: target section and Special Issue | D03 |
| L04 | Cover letter: prior MDPI submissions | D04 |

**Totals:**
- 28 request IDs: A01–A11, B01–B08, C01–C05, D01–D04.
- Placeholder IDs: 18 of 18 M-IDs mapped, and 4 of 4 L-IDs mapped.
- There are no unmapped placeholders and no unmapped requests.
- Every status is OPEN.

**Cover-letter placeholders filled by an M-ID answer** (no separate request):
- corresponding author, name, affiliation and e-mail: A01–A03;
- conference copyright: C04, C05;
- author approval: A10;
- ethics and consent: C01–C03;
- funding and conflicts of interest: A06, A08;
- data and code: A11, B07, B08;
- generative-AI approval: A09.
