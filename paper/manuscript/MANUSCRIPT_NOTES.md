# Manuscript working notes

Working rules for `paper/manuscript/`. The plan is `docs/P8_MANUSCRIPT_PLAN.md`.

## Files

| File | Content |
|---|---|
| `manuscript.md` | the drafting source (Markdown). Final integration pass: integrated scientific draft with source tokens, captions and placeholders |
| `DATA_AVAILABILITY_DRAFT.md`, `CODE_AVAILABILITY_DRAFT.md` | back-matter drafts with explicit placeholders; the manuscript carries their current-state text |
| `CONFERENCE_EXTENSION_DISCLOSURE_DRAFT.md` | conference-extension disclosure and cover-letter paragraph |
| `AUTHOR_CONTRIBUTIONS_DRAFT.md` | CRediT skeleton; every role `[CONFIRM]` |
| `FIGURE1_SCHEMATIC.md` | Figure 1 specification and diagram source (no data) |
| `RELATED_WORK_GAPS.md` | resolved topic → section → reference map |
| `references.bib` | 31 verified references |
| `tables/`, `figures/` | created by the export step (planned); never edited by hand |

## Source tokens

Performance numbers are never typed into the manuscript. They are written as tokens that a deterministic renderer
(planned, with `scripts/export_manuscript_tables.py`) resolves from the frozen tables in `paper/tables/`:

```
{{<table> | <col>=<value>, … | <column> | <format>}}
```

- `<table>`: a CSV name in `paper/tables/` without `.csv`, e.g. `p5_primary_mae`.
- The filters must select exactly one row; otherwise the renderer fails.
- `<format>`: a Python format spec, e.g. `.3f`, `+.3f` or `.1%`.
- Example: `{{p5_primary_mae | subject_id=unweighted_mean, target=temperature, budget_nights=14 | seed_mean | .3f}}`.

Counts of rows are written `{{COUNT:<table> | <col>=<value>, …}}`, e.g.
`{{COUNT:p6_level_mismatch_consistency | consistent=True}}`.

Whole manuscript tables are referenced as `{{TABLE:<name>}}`. Their source, selection and rounding are defined in
`docs/P8_TABLE_FIGURE_SELECTION.md` and implemented by the export script.

## Citations (pass 3)

- **Syntax:** `[@key]` or `[@key1; @key2]`, with keys from `references.bib`. At formatting they become numbers in
  order of first appearance, in square brackets before punctuation (MDPI template).
- **Eligible references:** only entries listed in `docs/P8_LITERATURE_EVIDENCE_MATRIX.md`. Each citation must support
  the exact sentence it is attached to (`docs/P8_CITATION_AUDIT.md`).
- **Own results:** sentences reporting this study's results carry no external citation; their source is the frozen
  tables (tokens). Parallels to the literature go in separate, explicitly interpretive sentences.
- **Preprints:** the only one is the canonical TCN preprint (`bai2018tcn`, not peer-reviewed). It is cited for the
  architecture, never for universal superiority over recurrent networks.
- **Conference paper:** `maeng2026icfice`, with verified title, authors, venue and paper number. Pages, DOI and URL
  are pending (`note` field; OPEN-27).

## Placeholders

| Placeholder | Meaning |
|---|---|
| `[CITE: <topic>]` | retired in pass 3; none remain. Any new claim needing literature gets a verified reference or is reworded |
| `[ICFICE CITATION]` | retired in pass 3; replaced by `[@maeng2026icfice]` (bibliographic details pending, OPEN-27) |
| `[FUNDING TO BE CONFIRMED BY PI]` | the conference paper's funding is not carried over |
| `[GENERATIVE-AI DISCLOSURE REQUIRED]` / `[GENERATIVE-AI STATEMENT REQUIRED]` | retired in the final integration pass: §3.8 and the Acknowledgments carry the drafted disclosure (D-052), pending PI approval (OPEN-28) |
| `[OTHER GENERATIVE-AI TOOLS, IF ANY: …]` | tools used outside the inventoried repository sessions; version as `[VERSION TO BE CONFIRMED]` until known (`docs/P8_FINAL_BLOCKERS.md` §2) |
| `[DATA REPOSITORY]`, `[CODE REPOSITORY]`, `[DOI]`, `[LICENSE]` | open publication decisions (OPEN-22, OPEN-23) |
| `[ETHICS / IRB INFORMATION REQUIRED FROM PI]` | institutional ethics information; the provider permission (D-002) is not an IRB approval |
| `[INFORMED CONSENT WORDING REQUIRED FROM PI]` | the consent statement; the provider's consent confirmation is a note for the PI, not the statement |
| `[AUTHORS AND AFFILIATIONS — PI]`, `[CRediT ROLES — PI]`, `[CONFIRM]` | author list and roles; nothing assigned before PI confirmation |
| `[TITLE — PI DECISION …]`, `[FINAL LIST: PI]` | final title and keywords (`docs/P8_TITLE_CANDIDATES.md`) |
| `[PI DECISION: …]`, `[PI]` | any other decision reserved for the PI |

A placeholder is never replaced by an assumed value. `docs/P8_FINAL_BLOCKERS.md` lists every open item with its owner.

## Privacy rules for manuscript content

**Calendar-date policy (fixed in P8 pass 2):**
- **Not used:** exact calendar dates, months of recording, original night/date identifiers, absolute timestamps.
- **Allowed wording:** early / later recording period; earliest adaptation nights; future deployment nights; night
  ordinals (night 1, nights ≥ 16) or `D####` keys; sensor phase s1/s2; quality phase; recording-period shift; temporal
  drift; seasonal variation as a generic confounder.
- **Direct calendar labels** ("winter", "spring", a month name) are not scientifically necessary and are not used.
  Adding them would need PI approval and a separate decision entry.
- **Other content rules:**
  - no participant metadata or health information; nothing from excluded sources;
  - subjects are only `User01`, `User02`, `User07`; the two mats `22480` and `22482` belong to User02.
- **Bibliographic dates** (e.g. the conference year and venue dates) are not subject data and may be cited.

## Precision rules carried from evidence checks

- **Drift sensitivity:** never write that the gain sign was identical for every subject, target, budget, seed and
  start night.
  - At the aggregated subject–target–budget level, the directions were stable across the start points.
  - At the seed level there are borderline exceptions: User07 temperature, start night 12, b = 1, where 1 of 3 seeds
    is positive. `p6_drift_sensitivity` is the source.
- **User07 temperature:** the negative-transfer direction was dominant but not literally invariant. The interval
  support depends on the seed (seed 0: 4/4 budgets, seed 2: 2/4, seed 1: 0/4).
- **Low budgets:** write "one to three adaptation nights did not provide reliable improvement", not "few-shot
  personalization improves".
- **Level mismatch:** "consistent with temporal representativeness being an important condition"; never "drift
  causes negative transfer".
- **Artifact counts:** `paper/tables/` holds 38 CSV artifacts, 35 reproduced result tables and 3 selection/provenance
  records.

## Section numbering (pass 2; unchanged in the final integration pass)

1. Introduction
2. Related Work (structure only)
3. Materials and Methods, with the experimental protocol as §3.5, statistics as §3.6 and reproducibility as §3.7
4. Results (4.1–4.6)
5. Discussion
6. Limitations
7. Conclusions

This follows the required-section list found for Applied Sciences (to confirm: `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`
item 1).

## Framing rules (final integration pass)

**Research questions** (defined in §1, numbered as in `docs/RESEARCH_PROTOCOL.md`):
- RQ1: strict LOSO;
- RQ2: chronological personalization;
- RQ3: feature families. RQ3 is **secondary** and is labelled that way in §3.5.2 and §4.2.

**Evidence hierarchy:**
- primary: P3 (strict LOSO failure and level offset), P5 (offset correction and negative transfer), P6 (night-level
  uncertainty and robustness);
- secondary: P4 (target-dependent but insufficient representation gains) and P7 (reproducibility).
- The Abstract names no P4 number.

**Terminology:**

| Use as primary framing | In the manuscript | Do not use as framing |
|---|---|---|
| chronological personalization; limited-data user adaptation | title, §1, §3.5.3, §4.3, §5 | few-shot success |
| unseen-domain generalization | "unseen domain" in the Abstract, §1, §3.1 and §7 | user-independent universal model |
| systematic level offset | §1, §4.1, §5.1 | domain invariance |
| temporal level mismatch | §4.5 | robust personalization |
| negative transfer: the adapted model is worse than its own base model on the same test nights (G_b < 0) | defined in §3.6 | "failure" without a reference |

- "Unseen-subject" and "unseen-user" may describe the fold design (one subject held out). Wherever the shift is
  interpreted, the text also states that it is a combined subject–period–season–device shift.

**Other rules:**
- **Discussion question:** §5.1 asks why the same recipe helps one held-out domain and hurts another. Its account is
  descriptive, and the level-mismatch agreement is always called post hoc.
- **Negative results:** they are listed together in §5.3 and are never dropped from the Abstract, Results or
  Conclusions.
- **Reproduction scope:** write "the selected models, predictions and result tables were reproduced; the
  hyperparameter searches were not rerun". Never write "all experiments were reproduced end-to-end".
- **Generative AI:** §3.8 and the Acknowledgments may name only inventoried tools (`docs/P8_FINAL_BLOCKERS.md` §2).
  No text may say that a tool decided the protocol, the analysis or a result.
- **Kadlec 2011:** cited only for adaptive soft sensing and adaptation frameworks under distribution change, never for
  personalization effectiveness or negative transfer in this application.

**Figures and tables:**
- main: Tables 1–5 and Figures 1–4;
- supplementary: Tables S1–S19 and Figures S1–S4 (`docs/P8_TABLE_FIGURE_SELECTION.md` §4).
- Captions sit at the first citation, as the template requires (requirements item 14).
