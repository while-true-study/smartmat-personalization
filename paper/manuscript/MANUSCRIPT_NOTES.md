# Manuscript working notes

Working rules for `paper/manuscript/`. The plan is `docs/P8_MANUSCRIPT_PLAN.md`.

## Files

| File | Content |
|---|---|
| `manuscript.md` | the drafting source (Markdown). First pass: architecture skeleton with evidence notes and source tokens |
| `DATA_AVAILABILITY_DRAFT.md`, `CODE_AVAILABILITY_DRAFT.md` | back-matter drafts with explicit placeholders |
| `RELATED_WORK_GAPS.md` | literature topics still to be searched and verified |
| `references.bib` | verified references only (empty until the literature pass) |
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
| `[GENERATIVE-AI DISCLOSURE REQUIRED]` / `[GENERATIVE-AI STATEMENT REQUIRED]` | MDPI template requirement (OPEN-28) |
| `[DATA REPOSITORY]`, `[DOI]`, `[LICENSE]` | open publication decisions (P7 checklist D1–D2) |
| `[ETHICS / IRB INFORMATION REQUIRED FROM PI]` | institutional ethics information; the provider permission (D-002) is not an IRB approval |
| `[PI DECISION: …]` | any other decision reserved for the PI |

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

## Section numbering (pass 2)

1. Introduction
2. Related Work (structure only)
3. Materials and Methods, with the experimental protocol as §3.5, statistics as §3.6 and reproducibility as §3.7
4. Results (4.1–4.6)
5. Discussion
6. Limitations
7. Conclusions

This follows the required-section list found for Applied Sciences (to confirm: `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`
item 1).
