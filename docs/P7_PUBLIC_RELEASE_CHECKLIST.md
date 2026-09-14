# P7 — Public release checklist (`public_release_v1`)

> Status: **release candidate ready; external publication pending.**
> - Every technical item below passes.
> - The items marked **BLOCKED** are decisions for the principal investigator (PI). They are never ticked
>   automatically.
> - Nothing has been uploaded or published: no GitHub Release, Zenodo, Figshare or OSF deposit, and no DOI.

Legend: **DONE** = verified in P7 · **BLOCKED** = needs a PI decision before external publication.

## A. Content and privacy (D-049, D-050)

| # | Item | Status | Evidence |
|---|---|---|---|
| A1 | Public representation decided: model-ready windows, not the canonical row table | DONE | D-050 |
| A2 | Only the three primary subjects, under anonymous IDs `User01` / `User02` / `User07`; User02's two mats stay one subject | DONE | build check `window_values_allowed_ids_ranges_relative_time`; validator |
| A3 | No calendar date and no absolute timestamp anywhere in the package (relative time, D-049) | DONE | validator text scan of every file; window columns are integers |
| A4 | No name, initials, folder name, file name, source path, messenger ID, machine username, secret or raw log text | DONE | validator text scan (paths, messenger IDs, long digit runs, raw file names from the raw manifest) |
| A5 | No restricted participant metadata (health, medication, medical-event dates) | DONE | validator `restricted_fields:*`; the metadata source is listed as excluded |
| A6 | Excluded: provider-confirmed invalid source, quarantined files, restricted metadata, auxiliary legacy sources | DONE | `excluded_sources.csv` and the manifest list, with reason, confirmation and decision (DATA_POLICY §5.4); no window of these sources |
| A7 | Heater control codes limited to `AHON` / `AHOF` of User02, no raw event text | DONE | validator `control_events_codes_only` |
| A8 | Device IDs `22480` / `22482` kept (equipment IDs) | DONE | D-050; the PI may revisit this |
| A9 | Provenance fields (`file_id`, `source_line_no`) removed | DONE | frozen window schema |

## B. Integrity and equivalence

| # | Item | Status | Evidence |
|---|---|---|---|
| B1 | Deterministic builder; in-place and fresh rebuilds byte-identical | DONE | 11/11 files identical |
| B2 | Manifest with SHA-256 of every file; metadata committed byte-exact (`.gitattributes`) | DONE | `manifest.json` |
| B3 | Private/public equivalence: every fold and subject × budget array bitwise equal | DONE | 18 equivalence checks, 65/65 build checks |
| B4 | Public validator passes without private data | DONE | `scripts/validate_public_release.py` 24/24 |
| B5 | Data dictionary and release README | DONE | `docs/P7_PUBLIC_DATA_DICTIONARY.md`, package `README.md` |

## C. Reproduction

| # | Item | Status | Evidence |
|---|---|---|---|
| C1 | Core tier (P3 → P5 → P6) from the release alone matches the committed results | DONE | `docs/P7_REPRODUCIBILITY_PUBLIC_RELEASE_REPORT.md` §8 |
| C2 | Extended tier (P4 finals) matches the committed results | DONE | report §9 |
| C3 | Clean checkout (repository + release package only) reproduces both tiers | DONE | report §10 |
| C4 | Environment, determinism flags and run times documented | DONE | `README.md`, report §11 |

## D. Decisions required before external publication

| # | Item | Status | Note |
|---|---|---|---|
| D1 | **Data license** of the release package, and the code license of the repository (there is no LICENSE file) | **BLOCKED** | License decision required before external publication. |
| D2 | **Hosting and persistent identifier** for `windows.parquet` and the package (repository, GitHub Release, Zenodo / Figshare / OSF; DOI) | **BLOCKED** | `windows.parquet` (30 MB) is not in Git; it is rebuilt byte for byte by the builder. |
| D3 | **PI approval of this release subset** (P7 exit criterion "release subset approved", RESEARCH_PROTOCOL §5) | **BLOCKED** | The provider's permission for public research release is on record (D-002, DATA_POLICY §5). The subset itself still needs the PI's sign-off. |
| D4 | **Absolute recording dates in committed repository files** (not in the release package) | **BLOCKED** | See below. Decide before the repository itself is made public. |
| D5 | Citation text and data-availability statement | **BLOCKED** | written with the manuscript (P8) from report §15 |

D4 detail: the repository, not the release, carries session-level calendar dates. Examples:
- the committed v1.0 split files under `data/splits/`;
- the P5 plan and the subject mapping under `configs/`;
- the canonical_v1 manifest;
- `paper/tables/p5_per_night.csv`, `p5_budget_counts.csv` and `p6_level_mismatch_trajectory.csv`;
- the P0–P5 reports and `docs/DECISIONS.md`;
- a few code and test constants.

These files are hashed or tagged frozen artifacts. P7 has not edited them or rewritten history, because either would
move frozen hashes and tags. The options are for the PI: keep the repository private, publish a de-identified copy
of the repository, or accept the dates.
