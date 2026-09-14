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

## Placeholders

| Placeholder | Meaning |
|---|---|
| `[CITE: <topic>]` | a verified reference is needed (see `RELATED_WORK_GAPS.md`); never replaced by an unverified one |
| `[ICFICE CITATION]` | the authors' conference paper; the bibliographic details come from the PI |
| `[DATA REPOSITORY]`, `[DOI]`, `[LICENSE]` | open publication decisions (P7 checklist D1–D2) |
| `[ETHICS / IRB INFORMATION REQUIRED FROM PI]` | institutional ethics information; the provider permission (D-002) is not an IRB approval |
| `[PI DECISION: …]` | any other decision reserved for the PI |

## Privacy rules for manuscript content

- No calendar date, absolute timestamp or month of recording. Nights are ordinals or `D####`.
- No participant metadata or health information; nothing from excluded sources.
- Subjects are only `User01`, `User02`, `User07`. The two mats `22480` and `22482` belong to User02.
