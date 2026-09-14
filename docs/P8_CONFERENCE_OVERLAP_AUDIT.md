# P8 — Conference overlap audit

> **Compares the journal manuscript with the authors' ICFICE 2026 paper** (verified source:
> `docs/P8_CONFERENCE_EXTENSION_MAP.md` §1). The goal is an honest account of overlap for the cover letter and the
> editors.
> - It is not an argument that the journal is "new enough".
> - No result was added to enlarge the extension.

| Component | Conference | Journal | Relationship |
|---|---|---|---|
| Task | temperature/humidity regression from smart-bedding pressure | the same | retained |
| Model family | TCN encoder (with MLP feature branches, late fusion) | causal residual TCN with the feature families as input channels; configuration from a nested pre-declared search | retained (family); re-implemented |
| Raw pressure input | yes, six channels | yes, six channels, P/4095, 4095 kept | retained |
| Movement features | yes (MLP branch) | yes (MOVEMENT family, geometry-free definitions, D-039) | re-evaluated under strict LOSO |
| Contact features | yes (entropy, CoP, contact area, concentration) | yes (CONTACT family, geometry-free definitions) | re-evaluated under strict LOSO |
| Dataset policy | pragmatic; User02/User03 without second-level timestamps; row-order sequences | audited canonical_v1; primary cohort User01, User02 (two mats), User07 with second-level timestamps; explicit auxiliary / excluded policy | substantially changed |
| Time windows | fixed-length sequences, not strict elapsed-time for every user | 40-s elapsed-time windows (8 × 5-s bins) for every primary subject | new |
| LOSO | not strict (the paper says so) | strict, target subject fully held out, nested source-only selection, leakage gate | new |
| Personalization | no (future work) | chronological, 0/1/3/7/14 nights, fixed future test span | new |
| Negative transfer | no | yes (User07 temperature, User01 humidity) | new |
| Statistical uncertainty | limited (micro/macro means) | night-level paired cluster bootstrap, seed and start-span sensitivity | new |
| Public reproduction | no | de-identified release candidate; clean-checkout P3–P6 reproduction | new |
| Main conclusion | movement/contact fusion helps; contact supports subject-level robustness | representation changes do not remove the unseen-domain level offset; personalization helps or hurts depending on the temporal representativeness of the adaptation nights | different (the journal qualifies the conference conclusion under strict evaluation) |

## Risks and continuity

- **Text reuse risk: low if the rules hold.**
  - The journal Abstract, Introduction contributions and Conclusions are written from scratch.
  - Method terms (TCN, movement-derived, contact-structure) are shared, but no sentence is copied.
  - The conference paper is cited where its ideas are used.
- **Figure reuse risk: none planned.**
  - The conference Figure 1 (fusion diagram) is not reused. The journal pipeline schematic (Figure 1) is a new
    drawing of a different design: LOSO → chronological adaptation.
  - If a conference figure were reused, permission from the copyright holder would be needed first
    ([VERIFY] copyright holder).
- **Table reuse risk: none.**
  - No conference table or number appears in the journal.
  - The conference's micro/macro percentages come from a different data policy and must not be compared numerically
    with journal results.
- **Methodological continuity:**
  - same task, sensor modality, model family and feature ideas;
  - the journal re-implements them under a frozen, leakage-controlled protocol.
- **Genuinely new evidence:**
  - rebuilt audited dataset with strict timing;
  - strict LOSO with a training-mean comparison;
  - the six-family comparison under that protocol;
  - chronological personalization with offset correction and negative transfer;
  - night-level uncertainty and drift sensitivity;
  - the level-mismatch analysis;
  - device residual strata;
  - the privacy-preserving reproduction package.
- **Disclosure:** the manuscript cites the conference paper in the Introduction and notes it on the first page. The
  cover letter discloses the extension and lists the changes (`paper/manuscript/CONFERENCE_EXTENSION_DISCLOSURE_DRAFT.md`).

## Text-overlap measurement (final integration pass)

- **Method:** word n-gram shingles, lower-cased, with source tokens, citation keys and HTML comments removed. The
  integrated manuscript was compared with the text extracted from the conference full paper (the verified PDF, kept
  outside the repository) and with the authors' earlier late-fusion manuscript.
- **Conference paper:** 7 shared 6-word shingles, 3 shared 8-word shingles and 1 shared 10-word shingle (of about
  7,500 in the manuscript). All of them are two phrases:
  - the method name "raw pressure sequences with movement-derived and contact-structure features", in the
    Introduction sentence that describes the conference study and cites it;
  - the keyword string "temperature and humidity estimation; temporal convolutional network".
  No sentence is reused.
- **Earlier late-fusion manuscript:** 0 shared shingles of 6 words or more.
- **Tables and figures:** no conference table, figure or number appears. Figure 1 is a new schematic
  (`paper/manuscript/FIGURE1_SCHEMATIC.md`). The Introduction states that the conference results are not compared
  numerically, because the data policies differ.

## Formatting-pass re-check (2026-09-15)

- **Manuscript prose:** unchanged. The source still shares only the method phrase and the keyword string with the
  conference paper, as above. The keywords now differ from the conference paper's wording.
- **Rendered manuscript and cover letter:** further shared shingles come from bibliographic text only:
  - the conference paper's own title, quoted in the reference list, the first-page note and the cover letter;
  - the titles of references that both papers cite, e.g. the generic TCN preprint and the microclimate reviews.
  The earlier late-fusion manuscript overlaps only in such cited-reference titles.
- **Tables and figures:** the generated Tables 1–5 and Figures 1–4 are built from the journal's frozen tables. None
  is taken from the conference paper.
