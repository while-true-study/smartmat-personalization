# P8 — Manuscript plan

> **P8 writes up frozen evidence. It adds no experiment and changes no result.**
> - Every number in the manuscript comes from the committed P3–P6 tables (`paper/tables/`) or from a deterministic
>   export of them (§7). Nothing is re-selected to look better.
> - This plan was written before any manuscript prose. It fixes the question, the narrative, the claims and what is
>   primary or secondary.
> - Publication blockers (license, hosting/DOI, PI approval, repository dates, ethics details) stay open. No draft may
>   state them as resolved (§9).

| | |
|---|---|
| Phase | P8 (`docs/RESEARCH_PROTOCOL.md` §5), branch `paper/p8-manuscript` from `p7-release-candidate` (`c9c15bc`, D-051) |
| Evidence | P3 `docs/P3_STRICT_LOSO_BASELINE_REPORT.md`, P4 `docs/P4_FEATURE_ABLATION_REPORT.md`, P5 `docs/P5_PERSONALIZATION_REPORT.md`, P6 `docs/P6_ROBUSTNESS_STATISTICAL_ANALYSIS_REPORT.md`, P7 `docs/P7_REPRODUCIBILITY_PUBLIC_RELEASE_REPORT.md` |
| Companion documents | `docs/P8_TITLE_CANDIDATES.md`, `docs/P8_TABLE_FIGURE_SELECTION.md`, `docs/P8_CONFERENCE_EXTENSION_MAP.md` |
| Manuscript source | `paper/manuscript/manuscript.md` (Markdown is the drafting source; no DOCX yet) |

## 1. Central question

> When temperature and humidity are estimated from smart-mat pressure sequences, how far can limited chronological
> personalization mitigate the generalization failure on an unseen subject/domain, and how much does its effect
> depend on the temporal representativeness of the adaptation data?

- The paper does **not** argue "personalization improves performance".
- It argues that the adaptation data decide the effect: personalization corrects a large domain-level offset when
  the early nights resemble the later ones, and creates a new offset when they do not.

## 2. Narrative arc

| Step | Phase | What the evidence shows | Main source |
|---|---|---|---|
| 1 | P3 | Under strict LOSO the error is large, heterogeneous across subjects and dominated by level offsets. The RAW-TCN is worse than the training-mean predictor for temperature in all three subjects, and better for humidity in two of three. | `p3_primary_summary`, P3 report §11–§12 |
| 2 | P4 | Movement features help temperature and contact features help humidity (direction 3/3 subjects each). The gains do not add up, and no representation removes the offset: User02's error stays ≈ 100 % offset in every family. | `p4_primary_summary`, `p4_vs_raw`, `p4_incremental_effects`, P4 report §16–§17 |
| 3 | P5 | Chronological fine-tuning corrects most of User02's offset. The same recipe introduces an offset for User07 temperature at every budget and for User01 humidity up to 7 nights. | `p5_primary_mae`, `p5_adaptation_gain`, P5 report §13–§14 |
| 4 | P6 | These directions survive night-level uncertainty (seed 0) and the choice of primary start night. User07 temperature is consistent in direction, but its interval support depends on the seed. Post hoc, the level of the adaptation nights relative to the later nights predicts the direction in 23/24 cells (descriptive). | `p6_bootstrap_*`, `p6_bootstrap_seed_sensitivity`, `p6_drift_sensitivity`, `p6_level_mismatch_*` |
| 5 | P7 | Every P3–P6 table is reproduced from a de-identified, model-ready release candidate and a clean checkout. | P7 report §8–§10 |

## 3. Claim hierarchy

### 3.1 Primary claim

> Chronological personalization can substantially reduce unseen-domain level-offset error when the early adaptation
> data are representative of later deployment conditions, but the same procedure may induce negative transfer under
> within-subject temporal level drift.

Evidence (seed means, primary span nights ≥ 16, unless stated):
- **Offset correction:** User02 temperature MAE 5.060 → 1.550 °C at b = 14 (G = +69.4 %). Bias −5.060 → −1.212 °C;
  3/3 seeds at every budget. Night bootstrap (seed 0) ΔMAE +3.466 [+3.354, +3.573] °C. Stable across start nights
  (+69.4 % to +70.5 %).
  - Sources: `p5_adaptation_gain`, `p6_bootstrap_mae`, `p6_drift_sensitivity`.
- **Negative transfer:**
  - User07 temperature, b = 1–14: G −14.4 % to −25.0 %, 0/3 seeds; bias +1.126 → about −2.1 °C.
  - User01 humidity, b = 1/3/7: G −34.6 % / −65.3 % / −44.8 %, 0/3 seeds; intervals below zero; recovery at b = 14
    (+22.5 %).
  - Sources: `p5_adaptation_gain`, `p6_bootstrap_mae`.
- **Representativeness (post hoc, descriptive):** the rule "adaptation helps if |adaptation-span mean − later mean| <
  |base bias|" agrees with the observed direction in 23 of 24 subject × target × budget cells. The exception is
  User01 temperature at b = 3.
  - Source: `p6_level_mismatch_consistency`.
- **Qualifiers that travel with the claim:** n = 3 subjects; subject, period, season and device are confounded; one
  frozen recipe; association, not mechanism.

### 3.2 Secondary claims

| # | Claim | Evidence | Qualifier |
|---|---|---|---|
| S1 | Strict LOSO performance is heterogeneous across subjects. | RAW-TCN temperature MAE 3.125 / 4.822 / 2.045 °C and humidity 20.285 / 24.591 / 9.972 %RH (User01 / 02 / 07); more than two-fold spread. Seed spread is much smaller than the spread between subjects. (`p3_primary_summary`, `p3_tcn_outer_by_seed`) | 3 folds; the domains differ in period, season and device |
| S2 | Pressure-derived movement/contact features give target-dependent, non-additive gains and do not remove the cross-domain calibration error. | MOVEMENT vs RAW temperature −0.246 °C (3/3); RAW+CONTACT vs RAW humidity −0.549 %RH (3/3). RAW+MOVEMENT+CONTACT ranks 4th (temperature) and 2nd (humidity). No family beats training-mean on the temperature cohort mean. User02 bias stays −4.69 to −4.82 °C and −23.6 to −26.5 %RH in every family. (`p4_primary_summary`, `p4_vs_raw`, `p4_incremental_effects`, `p4_bias_offset`) | each family has its own pre-declared selection; effect sizes are dominated by User01 |
| S3 | User02 is a strong offset-correction case. | See §3.1; humidity also improves at every budget (+21.4 … +44.3 %, 3/3 seeds; intervals above zero). (`p5_adaptation_gain`, `p6_bootstrap_mae`) | one subject, two mats |
| S4 | User01 humidity and User07 temperature are negative-transfer cases. | See §3.1. User07 temperature intervals exclude zero for seed 0 (4/4 budgets) and seed 2 (2/4), not seed 1 (0/4). (`p6_bootstrap_seed_sensitivity`) | User07: direction robust, interval support seed-dependent |
| S5 | Adaptation effectiveness is descriptively associated with temporal target-level representativeness. | 23/24 consistency; trajectories in `p6_level_mismatch_trajectory` / Figure P6-4. | post hoc (D-047 B), association only |
| S6 | User02/22482 keeps a residual temperature offset after adaptation. | 22482 b = 14 bias −1.975 °C (seed mean); seed-0 interval −1.923 [−2.230, −1.599]. It stays below zero in every quality-phase and heater-context stratum with ≥ 10 nights. 22480: −0.009 [−0.237, +0.229]. (`p5_user02_device_strata`, `p6_user02_device_context`) | not a confirmed device defect; mat, microclimate and control are not separable |
| S7 | All major P3–P6 results are reproducible from the anonymized public release candidate. | 102 frozen prediction files bitwise, 9 P3 weight digests, all 35 reproduced result tables (of the 38 CSV artifacts in `paper/tables/`; the other 3 are selection/provenance records), clean checkout (P7 report §8–§10) | frozen selections reused; inner searches not re-run; release not yet public |

### 3.3 Not claimed (never write)

- population-level personalization superiority, or statistical significance over a population;
- a pure biological subject effect;
- that season causes negative transfer;
- that the User01 sensor replacement causes a performance change;
- that the heater causes the device residual;
- device invariance;
- universal few-shot personalization success;
- that personalization solves domain shift in general.

**Wording rules:**
- "significant" is used only for within-subject night-level intervals, as "interval excludes zero". Never for the
  cohort.
- "Cohort mean" always means the unweighted mean of three subjects and is descriptive.
- Every claim about a direction names its subjects.

### 3.4 Report wordings not to carry over

Found while checking the evidence for this plan. The frozen reports are not edited; the manuscript uses the precise
statement.
- **P6 report §10, User07 temperature,** "direction robust (every seed and start)":
  - on the frozen primary span, all three seeds are worse at every budget;
  - across the drift grid, the **seed-mean** gain is negative at every start night, but at start night 12, b = 1, one
    of three seeds has G > 0 (`p6_drift_sensitivity`).
  The manuscript states it that way.
- **Months in the P3/P5 reports** (e.g. recording periods): not carried into the manuscript (§8).

## 4. Terminology

| Use | Avoid or qualify |
|---|---|
| chronological personalization; limited-data chronological adaptation; few-night adaptation | "few-shot personalization" as the framing. If used, state that 1–3-night adaptation did not reliably improve every target and subject. |
| unseen-subject / unseen-domain generalization; combined subject–period–season–device shift | "subject effect" alone (it implies a biological effect) |
| systematic level offset; bias | "calibration error" only when the bias is meant |
| temporal level mismatch; within-subject temporal drift | "concept drift" (not modelled) |
| negative transfer: the adapted model is worse than its own base model on the same test nights | "failure" without a reference |
| feature-family comparison (each family selected separately) | "ablation" in the strict sense of removing a feature from a fixed model |
| training-mean predictor | "naive baseline" |
| night-level paired cluster bootstrap interval | "confidence interval for the population" |

## 5. Target journal framing

- **Target:** MDPI *Applied Sciences*, engineering / applied-AI article.
- **Planned structure (pass 2):**
  1. Introduction
  2. Related Work
  3. Materials and Methods, with the experimental protocol as §3.5
  4. Results
  5. Discussion
  6. Limitations
  7. Conclusions
  The protocol moved into Materials and Methods because that section is on the required-section list found for
  Applied Sciences (`docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md` item 1, to confirm). The §-references in §6 below
  predate this renumbering; `paper/manuscript/MANUSCRIPT_NOTES.md` has the current numbering.
- **Back matter:** Data Availability, Code Availability, ethics/consent, author information.
- **Unverified:** the current Applied Sciences template and instructions have not been checked in P8. Before
  formatting, they must be verified for:
  - mandatory sections (e.g. whether Limitations may stand alone, and the order of the back-matter statements);
  - word, figure and table limits;
  - reference style;
  - whether supplementary files are accepted.
  Scientific content does not change with the template.

## 6. Section plan

The skeleton in `paper/manuscript/manuscript.md` follows this plan; §-numbers below refer to the manuscript.

- **1 Introduction:**
  - problem: pressure sensing in bedding estimates quantities without new sensors;
  - prior work [ICFICE conference paper]: TCN estimation with movement/contact features;
  - the deployment question: a completely unseen user or domain;
  - strict LOSO: heterogeneity and offsets, not fixed by representation;
  - after deployment a few nights of target-user data exist, but early nights may not represent later ones;
  - so adaptation can correct or create an offset;
  - contributions.
- **Contributions** (conservative; no "first" or "novel" without literature support):
  1. A leakage-controlled strict LOSO evaluation of smart-mat temperature/humidity estimation across three held-out
     subjects under a combined subject–period–season–device shift.
  2. A feature-family comparison: target-dependent movement/contact contributions and a persistent cross-domain
     level offset.
  3. A chronological personalization evaluation with 0/1/3/7/14 target-subject nights, showing both large gains and
     clear negative-transfer cases.
  4. Night-level robustness and privacy-preserving reproducibility:
     - paired bootstrap uncertainty;
     - temporal-drift sensitivity;
     - device residual diagnostics;
     - a derived, anonymized reproduction package.
- **2 Related Work:** topics in `paper/manuscript/RELATED_WORK_GAPS.md`. Citations are placeholders until verified.
- **3 Materials and Methods:**
  - **Data scope:**
    - primary cohort User01, User02, User07;
    - User02 has two mats (22480, 22482) and is one subject; device streams are never counted as subjects;
    - the recording periods do not overlap, so subject, period, season and device are confounded and each fold is a
      combined unseen-domain shift (D-020, D-029, A11).
  - **Preprocessing** (canonical_v1 policy only; D-014, D-018, D-024–D-028, D-033):
    - immutable raw source, exact-copy de-duplication, sessions, target validity flags;
    - no pressure interpolation, no clipping, 4095 kept, six channels;
    - User01 sensor phases, the User02 dual-mat structure;
    - the excluded / quarantined / auxiliary source policy.
    No superseded preprocessing ideas are described.
  - **Windows** (D-032–D-034): 40 s, 8 × 5-s bins, stride 20 s, last observation per bin, gaps ≤ 5 s. Splits are made
    before windowing; no window crosses a partition. Input P/4095. Targets standardised with training-partition
    statistics only. 20/30-s windows were not run and are not reported as results.
  - **Model** (D-040): causal residual TCN, the search space, AdamW, early stopping on inner validation only.
  - **Heater control codes** are never inputs (D-038).
- **4 Experimental Protocol:**
  - **RQ1:** strict LOSO with 3 folds; nested subject-level inner validation (two swapped inner splits); single outer
    test look (D-031, D-040).
  - **RQ3:** six families (RAW, MOVEMENT, CONTACT, RAW+MOVEMENT, RAW+CONTACT, RAW+MOVEMENT+CONTACT), each with its own
    pre-declared selection. This is a family comparison, not a fixed-hyperparameter ablation (D-039, D-044).
  - **RQ2:** budgets 0/1/3/7/14 nights.
    - Earliest nights for adaptation, the next night as buffer, primary test nights ≥ 16, the same primary span for
      every budget.
    - Full-parameter fine-tuning for 10 epochs at 0.1 × the selected learning rate; no target validation, no scaler
      refit (D-037, D-045).
  - **Leakage gate** (D-042).
  - **Statistics** (D-041, D-047):
    - MAE/RMSE per target, per subject first; unweighted cohort mean only as description;
    - night-level paired cluster bootstrap, 2,000 resamples, seed 0 primary, 95 % percentile interval; seeds 1/2 as
      sensitivity;
    - windows are never the sample size, and n = 3 allows no population inference.
- **5 Results:**
  - 5.1 Strict LOSO: Table 2.
  - 5.2 Feature families: Table 3.
  - 5.3 Chronological personalization: Table 4, Figures 2–3.
    - Cohort curves first: temperature 3.348 → 3.216 → 2.659 → 2.199 → 1.889 °C; humidity 17.637 → 17.893 → 18.411
      → 17.772 → 12.179 %RH.
    - Subject heterogeneity immediately after.
  - 5.4 Night-level robustness: Table 5, Figure 4.
  - 5.5 Temporal level mismatch: **labelled post hoc and descriptive**.
  - 5.6 Device residual: descriptive; not framed as a defect.
- **6 Discussion:**
  - A: unseen-domain failure is largely level calibration;
  - B: features and personalization address different problems;
  - C: personalization is not intrinsically beneficial;
  - D: temporal representativeness matters;
  - E: more nights can recover, depending on subject and target;
  - F: a device/microclimate residual remains;
  - G: **practical implication, not tested:** adaptation-data selection, drift monitoring and calibration safeguards
    are future work.
- **7 Limitations** (all required):
  - three subjects; non-overlapping periods; subject/time/season/device confounding; no population inference;
  - one frozen full-fine-tuning recipe; adaptation always uses the earliest nights; temporal drift;
  - the User01 sensor phase is confounded with time and season; User02 mat differences are not causal;
  - no 20/30-s window, 4095 or bias-only-calibration comparison;
  - the night bootstrap does not model serial dependence between nights;
  - the public release is derived and model-ready, not the raw package.
- **8 Conclusions:** the primary claim with its qualifiers; no new numbers.
- **Back matter:**
  - Data Availability (`DATA_AVAILABILITY_DRAFT.md`);
  - Code Availability (`CODE_AVAILABILITY_DRAFT.md`);
  - Reproducibility statement (P7 evidence);
  - ethics/consent: only documented statements, IRB placeholder.

## 7. Numbers policy

- **Numbers are generated, not retyped.**
  - Tables and inline values in `manuscript.md` are written as source tokens (syntax in
    `paper/manuscript/MANUSCRIPT_NOTES.md`). A deterministic renderer or export fills them from `paper/tables/`.
  - The values quoted in this plan were checked against the tables when it was written. They are for review, not for
    copying.
- **Planned tooling** (P8, later passes; none of it computes a new metric):
  - `scripts/export_manuscript_tables.py`: manuscript tables selected and reformatted from the frozen CSVs.
    - Night ids become relative keys or ordinals.
    - Rounding is declared per column.
  - `scripts/validate_manuscript_results.py`, which checks:
    - every token and number resolves to a frozen cell;
    - no absolute date in public-facing text or tables;
    - no population-significance wording;
    - every referenced table and figure exists;
    - relative night identifiers where required.
- **New derived numbers** (e.g. a percentage not in a table) are allowed only through the export script, with the
  formula stated. They are never computed by hand.

## 8. Public-facing date and privacy review

- **No calendar date or absolute timestamp** in the manuscript, its tables, figures or supplementary files. Nights are
  referred to by ordinal (night 1, night ≥ 16) or by `D####` keys.
- **Tables with calendar night ids** (`p5_per_night`, `p5_budget_counts`, `p6_level_mismatch_trajectory`) enter the
  manuscript or supplement only through the export script, with ordinals or `D####`.
- **Months and seasons:**
  - The reports mention recording months. The manuscript describes the confounding qualitatively: non-overlapping
    periods, different seasons, a warmer and more humid domain.
  - [PI DECISION: may seasons or months be named?]
- **Other rules:**
  - no participant metadata, health information or anything from the excluded sources;
  - device IDs 22480/22482 are equipment IDs (D-050);
  - the heater is described as firmware control of the mat microclimate, without log text.
- **Repository-level dates** (committed split files, P5 plan, subject mapping, three paper tables, reports) are
  outside the manuscript. Their public scope is a PI decision (P7 checklist D4). It blocks archiving the repository
  as a whole.

## 9. Blockers and gates

| Item | State | Needed before |
|---|---|---|
| Data and code license | open (PI) | Data/Code Availability final text; `v1.0-paper` |
| Hosting and DOI of `public_release_v1` | open (PI) | Data Availability final text; `v1.0-paper` |
| PI approval of the release subset and the final release | open (PI) | `v1.0-paper` |
| Public scope of repository dates | open (PI) | public repository or code archive |
| Ethics / IRB information | open (PI); provider permission (D-002) is not an IRB approval | submission |
| Conference paper bibliographic details | open (PI; not in the repository) | Introduction, extension map |
| Journal template requirements | unverified | formatting |

The PI items are tracked in `docs/DECISIONS.md`:
- OPEN-22 license;
- OPEN-23 hosting/DOI;
- OPEN-24 approval;
- OPEN-25 repository dates;
- OPEN-26 ethics/IRB;
- OPEN-27 conference paper;
- OPEN-28 generative-AI disclosure (MDPI template requirement, added in pass 3; drafted in the final integration
  pass, D-052, PI approval pending).
Funding also stays a PI placeholder: the conference paper's funding statement is not carried over.
**The compact, current list of all open items is `docs/P8_FINAL_BLOCKERS.md`** (final integration pass). It
supersedes the table above where they differ.

**Gates to `v1.0-paper`:**
- every manuscript number validated against the frozen tables;
- the privacy review above passed;
- the back-matter statements reflect the real state of each blocker;
- PI approval.
Until then the drafts keep the placeholders `[DATA REPOSITORY]`, `[DOI]`, `[LICENSE]` and
`[ETHICS / IRB INFORMATION REQUIRED FROM PI]`.

## 10. P8 passes

1. **Architecture** (this pass): plan, titles, table/figure selection, extension map, skeleton, statements with
   placeholders, related-work gaps.
2. **Literature:** verified references for `RELATED_WORK_GAPS.md` topics (separate search; nothing invented).
3. **Tables and figures:**
   - export script and manuscript tables;
   - study-pipeline schematic (Figure 1), which has no data content.
4. **Prose:** section by section from the skeleton, claims as in §3.
5. **Validation:** manuscript validator, privacy review, internal consistency with the P3–P7 reports.
6. **Final metadata:** blockers resolved or stated as open; `v1.0-paper` only after the gates in §9.

**Passes as run:**
1. architecture;
2. conference verification and prose;
3. literature and citations;
4. final integration: GenAI disclosure, captions, title comparison, final audit.
The table export, the figure re-rendering and the manuscript validator (items 3 and 5 of the list above) remain
production items (`docs/P8_FINAL_BLOCKERS.md` §3).
