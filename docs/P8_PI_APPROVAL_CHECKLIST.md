# P8 — PI approval checklist

> **What the PI (and rights holders) must decide or provide before the manuscript can be submitted.**
> - No item below has been filled by assumption. `[CONFIRM]` means a draft exists and needs approval; **BLOCKED**
>   means nothing may be written until the PI provides it.
> - Options are listed where a decision is open. None is chosen here.
> - Once an item is decided, write the decision into the manuscript source and record it in `docs/DECISIONS.md`. Then
>   rebuild (`scripts/build_submission_candidate.py`) and run `scripts/validate_manuscript_results.py --final`.
> - Journal rules cited below are from the Applied Sciences Instructions for Authors
>   (`docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`, source I).

State at the end of the P8 submission-closure pass: **no PI input received yet; every item is open.**

## Manuscript

- [ ] **Final title — [CONFIRM].**
  - Working final title (D-054): "Chronological Personalization under Unseen-Domain Shift: Offset Correction and
    Negative Transfer in Smart-Mat Temperature and Humidity Estimation".
  - Final check passed:
    - distinct from the conference title;
    - "unseen-domain" matches the stated confounding of subject, period, season and device;
    - names both offset correction and negative transfer;
    - no population claim.
- [ ] **Featured Application — [CONFIRM] (default KEEP).**
  - Encouraged, not mandatory (source I).
  - Conservative wording: an evaluation framework; "in three held-out cases"; no clinical or prevention claim.
- [ ] **Author list — BLOCKED.** Full first and last names (source I). Do not copy the conference paper's author list.
- [ ] **Author order — BLOCKED.** Decide by contribution to this journal study, not the conference order.
- [ ] **Affiliations — BLOCKED.** Complete address in PubMed/MEDLINE format: city, zip code, state/province, country.
- [ ] **Corresponding author — BLOCKED.** At least one, with e-mail.
  - The e-mail addresses of all authors are displayed on the published paper. The corresponding author must obtain
    each author's consent for this (source I).
- [ ] **ORCID — BLOCKED.** Encouraged; linked in the published paper (source I).
- [ ] **CRediT roles — BLOCKED.**
  - Only roles that each author actually performed (`paper/manuscript/AUTHOR_CONTRIBUTIONS_DRAFT.md`).
  - Every author must meet the authorship criteria and approve the submitted version (source I).
  - GenAI tools cannot be authors.
- [ ] **Funding — BLOCKED.**
  - All funding sources, with grant numbers as registered (source I).
  - The conference paper's acknowledgment names a grant. It enters this manuscript only if the PI confirms that the
    grant supported this journal study. It is not copied automatically.
- [ ] **Conflicts of Interest — BLOCKED.** A statement, including any funder role (source I).

## Ethics

- [ ] **Ethics / IRB — BLOCKED.**
  - **Journal rule for human data (source I):**
    - declare that the research followed the Declaration of Helsinki;
    - state approval by an IRB or ethics committee (project identification code, approval date, committee name);
    - or name the ethics committee that granted an exemption, with the reason;
    - or cite the local or national legislation under which approval is not required.
  - **Possible outcomes:**
    - A. approval exists → institution, code and date exactly as issued;
    - B. formal exemption → the committee's name and its stated reason;
    - C. no IRB review → the PI must establish which of the journal's routes applies. "Ethical approval was not
      required" may not be written without a legal basis or an exemption.
  - The data provider's permission to use and release the data (D-002) is **not** an ethics approval.
- [ ] **Informed consent — BLOCKED.**
  - The exact statement (source I examples): consent obtained from all subjects; not required under named
    legislation; or verbal consent with its rationale.
  - The provider reported that participant consent was obtained (D-002). The PI must confirm the wording, and whether
    the consent covers this research use and publication.

## Disclosures

- [ ] **GenAI disclosure — [CONFIRM].**
  - Draft in §3.8 and the Acknowledgments (D-053):
    - Claude Code (Anthropic; CLI 2.1.263 and 2.1.270; Claude Opus 5);
    - ChatGPT (OpenAI; historical model versions not consistently logged; GPT-5.6 Sol in the final manuscript
      review).
  - PI approval closes OPEN-28 and sets D-053 to Accepted.
- [ ] **Conference-extension disclosure — [CONFIRM].**
  - First-page note, Introduction paragraph and cover-letter statement drafted (source I rule, four conditions).
  - Needs from the PI:
    - the conference paper's proceedings volume, pages, DOI or URL, if any;
    - the copyright holder of the conference paper;
    - whether permission is needed (none expected: no text, table or figure is reused).
  - Currently BLOCKED on the bibliography (OPEN-27).

## Release and availability

- [ ] **Public release subset approval — BLOCKED.**
  - Approve `public_release_v1` (P7 checklist D3, OPEN-24): three subjects, four mat streams, relative time only, no
    raw logs or metadata.
- [ ] **Code license — BLOCKED (rights holder).**
  - Candidate options, not chosen: a permissive software license (e.g. MIT, BSD-3-Clause, Apache-2.0), a copyleft
    license (e.g. GPL-3.0), or no public license (code on request).
  - Institutional IP rules may constrain the choice.
- [ ] **Data license — BLOCKED (rights holder and data provider).**
  - Candidate options, not chosen: CC BY 4.0, CC BY-NC 4.0, CC0, or a controlled-access data-use agreement.
  - Must be compatible with the provider's permission and the participants' consent.
- [ ] **Repository public-date exposure policy — BLOCKED (OPEN-25).**
  - The committed history contains session-level recording dates outside the release package. Options, not chosen:
    - publish the whole repository as is (exposes the dates);
    - publish a sanitized copy without the date-bearing files or history (a new repository; no history rewrite in
      this one without a decision);
    - publish a release snapshot (code plus the de-identified release package);
    - archive the code only.
- [ ] **Hosting choice — BLOCKED.**
  - Candidate options, not chosen: Zenodo, Figshare, OSF, an institutional repository, or a GitHub Release archived
    with a DOI.
  - Nothing is uploaded before approval.
- [ ] **DOI / persistent identifier strategy — BLOCKED.**
  - A DOI minted by the chosen host, before submission or at acceptance, or none if data are restricted.
- [ ] **Data Availability wording — BLOCKED.** The current text states the true state: a release candidate, not
  externally published. Choose one final state:
  - A. public before submission (repository, DOI, license);
  - B. public after acceptance or publication;
  - C. available from the corresponding author under conditions;
  - D. derived public dataset only (the raw data are never released);
  - E. restricted.
  "Publicly available at DOI …" may be written only under A, or under B once it is true.
- [ ] **Code Availability wording — BLOCKED.**
  - Depends on the code license and the exposure policy above.
  - It is part of the Data Availability Statement: the template has no separate section.

## Journal format

- [ ] **Special Issue — [CONFIRM] (none selected).**
  - A search result shows an Applied Sciences Special Issue "Future Information & Communication Engineering 2024"
    linked to the ICFICE series. If any Special Issue is chosen, its own page must be read: an older
    conference-specific issue stated a 50 % new-content rule that is not a journal-wide rule.
- [ ] **Keywords — [CONFIRM].** Seven proposed (3–10 allowed): smart bedding; pressure sensing; microclimate
  estimation; temporal convolutional network; cross-subject generalization; leave-one-subject-out evaluation; user
  adaptation.
- [ ] **Scientific content — [CONFIRM].** PI approval of the abstract, tables, figures and limitations. No result may
  be changed during this review (docs/P8_MANUSCRIPT_PLAN.md §3; D-054).
