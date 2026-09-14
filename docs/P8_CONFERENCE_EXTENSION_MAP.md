# P8 — Conference-to-journal extension map

> **Source of truth for the conference side:** the authors' ICFICE 2026 full paper, D.-H. Maeng and J.-S. Bang,
> "Robust Temperature and Humidity Estimation from Smart Bedding Pressure Sequences Using Movement and
> Contact-Structure Features" (file `ICFICE_2026_Fullpaper_DongHoon_Robust_TH_Estimation.pdf`, 4 pages, outside the
> repository).
> - It was read in full on 2026-09-14. A second copy with the same name has identical text.
> - Venue facts come from the ICFICE 2026 program booklet (speaker edition), which lists the paper as AI-06 in oral
>   session AI-A (details in §3).
> - Conference statements below are paraphrased, not quoted at length. No conference number is used as journal
>   evidence.
> - Missing bibliographic items stay `[VERIFY BIBLIOGRAPHIC DETAILS]`.

## 1. What the conference paper did (verified against the PDF)

- **Data and evaluation policy:**
  - six-channel pressure logs of User01–User03 in the main evaluation, and a five-channel auxiliary source that was
    excluded;
  - only User01 had second-level timestamps. User02/User03 were treated as row-order, fixed-length sequences (the
    paper's Table 1).
  - The evaluation was therefore a pragmatic fixed-length-sequence evaluation. The paper states that its results must
    not be read as strict elapsed-time window evaluation or as strict LOSO validation.
- **Method:**
  - a TCN encoder for raw pressure sequences;
  - a movement-feature MLP branch (intensity, variability, event frequency, directional change, comfort-related
    components);
  - a contact-structure MLP branch (distribution entropy, centre-of-pressure statistics, contact area, concentration);
  - late fusion by concatenation into a regression head for temperature and humidity.
- **Setup:**
  - a frozen TCN policy chosen before the contact evaluation, with target normalisation fitted on the training split;
  - soft subject-balanced sampling (alpha = 0.5) and the "baseline replication split";
  - micro (window-weighted) and macro-subject metrics;
  - nominal window settings w20/w30/w40 with several movement-feature versions.
- **Findings:**
  - Movement fusion lowered MAE relative to the raw baseline in the main w40 condition, in both the micro and the
    macro-subject metrics.
  - Contact features gave mostly macro-subject (robustness) gains, with condition-dependent micro gains: 4 of 9
    sweep settings improved both.
- **Limitations and future work, as stated:**
  - no strict elapsed-time or strict LOSO interpretation;
  - CNN-BiLSTM models and user-adaptive fine-tuning not evaluated;
  - future work: collect complete second-level timestamp logs for all users, validate strict time-based LOSO, and add
    user-adaptive fine-tuning.
- **Key sentence for the manuscript** (our wording): the journal study directly evaluates two deployment questions
  that the conference paper explicitly left as future work — strict time-based unseen-subject evaluation and
  user-adaptive fine-tuning.

## 2. Component map

| Conference component | Journal counterpart | Unchanged / reused | Substantially extended | New experiment / evidence | Manuscript section |
|---|---|---|---|---|---|
| Task: temperature/humidity regression from smart-bedding pressure sequences | same task and six-channel input; targets described as the heater-controlled mat microclimate | task definition | — | — | §1, §3.1 |
| Data: User01–User03 six-channel logs; five-channel auxiliary source excluded; second-level timestamps for User01 only | audited canonical_v1 rebuilt from the checksum-verified raw logs (provenance, exact-copy de-duplication, sessions, validity flags). Primary cohort User01, User02 (mats 22480/22482), User07, all with second-level timestamps. Minute-resolution legacy sources (User02 legacy, User03 legacy) are auxiliary and unused; the invalid source is excluded | — | data curation and cohort definition | complete strict time-based windows for every primary subject | §3.1–§3.2 |
| Pragmatic row-order, fixed-length sequences | 40-s elapsed-time windows of 8 × 5-s bins, stride 20 s, gaps ≤ 5 s, split before windowing (D-032) | — | windowing rule | — | §3.3 |
| Nominal w20/w30/w40 sweep | 40 s only. The 20/30-s sensitivity was declared but not run (limitation) | 40 s as anchor | — | — | §3.3, §6 |
| "Baseline replication split"; micro/macro-subject metrics | strict LOSO: target subject fully held out, nested subject-level (source-only) validation, one outer look, automated leakage gate (D-031, D-042) | per-subject reporting (unweighted subject mean) | — | strict unseen-subject evaluation (P3) | §3.5, §4.1 |
| Soft subject-balanced sampling (alpha = 0.5) | not used: training windows are shuffled uniformly each epoch, with no subject weighting (`src/training/trainer.py`) | — | — | — | §3.4 |
| TCN raw-pressure encoder | causal residual TCN re-implemented under protocol v1.0; configuration from a pre-declared nested search (D-040) | model family | re-implementation, search space, selection, seeds 0/1/2 | training-mean baseline comparison per subject (P3) | §3.4, §4.1 |
| Movement MLP branch + late fusion | MOVEMENT family (geometry-free movement features, D-039) as TCN input channels, alone and combined with RAW | the idea of movement-derived representation | re-defined features, pre-declared selection per family | family comparison under strict LOSO (P4) | §3.5, §4.2 |
| Contact-structure MLP branch (entropy, CoP, contact area, concentration) | CONTACT family (geometry-free contact features, D-039), alone and combined with RAW / RAW+MOVEMENT | the idea of contact-structure representation | re-defined features (no channel-layout assumption) | family comparison; persistent level offset (P4) | §3.5, §4.2 |
| No user adaptation (future work) | chronological personalization: 0/1/3/7/14 nights, one buffer night, fixed common primary test span (nights ≥ 16), frozen full fine-tuning recipe (D-037, D-045) | — | — | adaptation curves, offset correction, negative transfer (P5) | §3.5, §4.3 |
| No uncertainty analysis | night-level paired cluster bootstrap, seed sensitivity, start-span drift sensitivity (D-041, D-047) | — | — | P6 | §3.6, §4.4 |
| — | post-hoc temporal target-level mismatch analysis | — | — | P6 | §4.5 |
| — | User02 mat / quality-phase / heater-context residual strata | — | — | P5, P6 | §4.6 |
| No reproducibility package | de-identified `public_release_v1` and clean-checkout reproduction of P3–P6 (D-049, D-050) | — | — | P7 | Reproducibility |

## 3. Bibliographic record

| Item | Value | Source | Status |
|---|---|---|---|
| Title | Robust Temperature and Humidity Estimation from Smart Bedding Pressure Sequences Using Movement and Contact-Structure Features | full paper; program booklet | verified |
| Authors | Dong-Hoon Maeng, Jin-Suk Bang (Hoseo University) | full paper; program booklet | verified |
| Venue | The 18th International Conference on Future Information & Communication Engineering (ICFICE 2026), organised by KIICE, Sapporo, Japan, 7–10 July 2026 | program booklet | verified |
| Presentation | oral session AI-A, paper AI-06 | program booklet | verified |
| Proceedings identifiers | the booklet cover states ISSN 2765-3811, Vol. 17, No. 1 | program booklet | [VERIFY BIBLIOGRAPHIC DETAILS]: confirm that these identify the proceedings in which the paper appears |
| Pages, DOI, official publication URL | — | not in either source | [VERIFY BIBLIOGRAPHIC DETAILS] |
| Copyright holder of the conference paper | — | not in either source | [VERIFY] (needed for any reuse, MDPI conditions in `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`) |

**Related prior work cited by the conference paper:** S. H. Lee, J. H. Kim and J. S. Bang, a movement-score late-fusion
temperature/humidity regression study, listed there as an unpublished manuscript (2025).
- It is the "prior study" referred to in RESEARCH_PROTOCOL §1 and D-040 only if the PI confirms this [VERIFY].
- Its citability in a journal article is a PI decision.

## 4. Points to verify with the PI

- Whether the conference's User02/User03 data correspond to the journal's auxiliary legacy sources.
  - This is consistent with the minute-resolution legacy sources in canonical_v1 (D-021, D-026), but not proven.
- Which five-channel auxiliary source the conference excluded.
- The copyright holder of the conference paper, and whether the journal reuses any conference text, figure or table.
  - Planned: none. The journal figures and tables are generated from the frozen P3–P6 artifacts.
- The conference acknowledgment names a funding source (a national SW-centred university programme with a project
  number).
  - Whether it also applies to the journal work is for the PI to confirm in the Funding statement. It is not copied
    into the manuscript automatically.
