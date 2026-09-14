# P7 — Reproducibility & Public Data Release

> **P7 packages and reproduces. It changes no P3–P6 result.**
> - No search, selection, recipe, bootstrap setting, preprocessing, cohort, subject exclusion or target filter was
>   changed. Protocol v1.0, the splits, canonical_v1 and the raw data are unchanged.
> - The release candidate `public_release_v1` reproduces every committed P3–P6 result table from the release alone:
>   bitwise predictions, identical model weights, identical tables.
> - **Status: release candidate ready; external publication pending.** The data license, the hosting/DOI and the PI's
>   approval of the release subset are open (§14).

| | |
|---|---|
| Phase | P7 (`docs/RESEARCH_PROTOCOL.md` §5), branch `release/p7-public-data` (from `p6-robustness` = `16980ae`) |
| Decisions | D-048 (P6 tag documentation), D-049 (temporal de-identification; closes OPEN-18), D-050 (release content, storage, gates, tiers) |
| Code | `src/data/public_release.py`, `scripts/build_public_release.py`, `scripts/validate_public_release.py`, `src/evaluation/public_reproduction.py`, `scripts/reproduce_public_release.py`; tests `tests/test_public_release.py`, `tests/test_public_reproduction.py` |
| Release | `data/release/public_release_v1/` (metadata committed; `windows.parquet` is rebuilt by the builder and not in Git) |
| Documentation | `docs/P7_PUBLIC_DATA_DICTIONARY.md`, `docs/P7_PUBLIC_RELEASE_CHECKLIST.md`, the package `README.md`, the repository `README.md` (environment and commands) |

## 1. Purpose

- **P7 turns the frozen study into something others can check:**
  - a derived, de-identified public dataset;
  - a reproduction path that needs only that dataset and this repository.
- **In scope:**
  - record the `p6-robustness` tag (D-048);
  - decide how time is published (D-049) and what is published (D-050);
  - a deterministic builder with a privacy validator and a private/public equivalence gate;
  - two reproduction tiers, run locally and from a clean checkout;
  - documentation: data dictionary, release README, environment, checklist, this report.
- **Out of scope:** new experiments, new searches, the 20/30-s window and 4095 sensitivities (D-047 C), any
  calibration, and the license and hosting decisions (PI).

## 2. P7 release decisions

- **D-048:** the annotated tag `p6-robustness` (tag object `cfc0264` → `16980ae`) was recorded in RESEARCH_PROTOCOL §5
  and CONVENTIONS §6.5. It is repository metadata only.
- **D-049 (closes OPEN-18):** no calendar date in any release file; per-subject relative time (§5).
- **D-050:** a model-ready window release (option A).
  - Code review showed that the models consume only window arrays: `FoldData` for P3/P4, `SubjectWindows` for
    P5/P6. They never use the rows between window steps.
  - Windows are ordered by their first row in every fold, so the release keeps the training order that bitwise
    reproduction needs.
  - A canonical row table would publish far more (every row, the event field, provenance). Publishing only metrics
    would allow no reproduction.
  - D-050 also fixes the gates (privacy validator, equivalence), the storage (metadata in Git, `windows.parquet`
    outside) and the two tiers. Inner searches are in neither tier.
- **Build notes recorded in D-049/D-050:**
  - the public P5 plan also drops the P3 run ids and local run paths;
  - night-bearing tables are compared through a single per-subject day shift;
  - the metadata is stored byte-exact.

Commits on the branch:

| Commit | Content |
|---|---|
| `ddbfed5` | P6 tag documentation (D-048) |
| `40a59ab` | release policy: D-049, D-050, OPEN-18 closed, `.gitignore` for `windows.parquet` |
| `d3e6cfa` | builder, loader, privacy validator, equivalence gate and their tests |
| `ad97599`, `33c68f8`, `b8b6696`, `2e9ec9c`, `5ff6a52`, `402c1ff` | builder fixes found while building and reproducing (§6) |
| `8df45ef`, `9c6ac83`, `de590f9`, `96f78a8`, `59f903e` | release metadata, data dictionary, and manifest refreshes after each builder fix |
| `bd6506d` | public reproduction pipeline |
| this report's commit | results, checklist, environment |

## 3. Privacy and de-identification

- **What the release holds.** `windows.parquet` has 64 fixed columns:
  - anonymous IDs;
  - phase labels;
  - relative night key and ordinal;
  - relative seconds;
  - window-set flags;
  - 48 pressure integers;
  - the two targets and their validity flags.
  The other files are the split copies, 317 heater codes, the plan, digests, schema, the excluded-source list,
  README and manifest.
- **Build checks:** 65/65.
  - The validator runs before the manifest is written (22 checks) and again after it (23).
  - The equivalence gate adds 18 checks, and the P5 plan adds 2.
- **Public validator, release only:** 24/24 (`scripts/validate_public_release.py`).

| Rule (P7 instructions, DATA_POLICY §5) | How it is enforced | Result |
|---|---|---|
| no source path, folder or file name, `source_relpath` | text scan of every file: absolute-path patterns, raw-package folder patterns, and every file name and relative path in the raw file manifest (375 rows) | none |
| no participant name or initials | no field can hold them: IDs must be in fixed sets (`User01/02/07`, `unknown/22480/22482`, `S####`); field names such as `name` or `initials` are flagged in every data file. The repository stores no names, so there is no list to scan for. | none |
| no restricted metadata (health, medication, medical-event dates) | the metadata source is excluded; health and demographic field words are flagged in every data file | none |
| no messenger or chat ID, no long digit identifier | patterns `chatIDs=`, messenger names, runs of ≥ 9 digits (hashes excepted) | none |
| no raw log text, no quarantined or User06 values | no `event_raw` column; control codes restricted to `AHON`/`AHOF`; only primary windows (equivalence gate); excluded source names are flagged outside `excluded_sources.csv` and README | none |
| no absolute path or machine username | path patterns (drive letters, `/Users/`, `/home/`, `AppData`, …); no environment data is written into the release | none |
| no token, password or secret | secret and credential patterns (`402c1ff`) | none |
| no absolute date | date patterns (dashed, slashed, dotted, compact 8-digit, Korean year); no date-typed column; night ids must match `D####`; times are integers | none |
| provenance fields removed | `file_id`, `source_line_no`, source and chunk columns are forbidden in the schema | none |
| User02's mats stay one subject | check `user02_mats_are_one_subject` | pass |

- **Anonymous IDs** `User01`, `User02`, `User07` are kept; User02's `22480`/`22482` are one subject. The device IDs are
  kept as equipment IDs (D-050).
- **Excluded by default** (listed in `excluded_sources.csv` and the manifest, no data):
  - the provider-confirmed invalid User06 source;
  - the quarantined prefix-mismatch files;
  - the restricted metadata;
  - the auxiliary User02 and User03 legacy sources.
- **Outside the release.** The repository itself carries session-level dates in committed files (splits, P5 plan,
  subject mapping, three paper tables, reports). This was flagged in D-049. It is a PI decision before the
  repository is made public (checklist D4). No history was rewritten.

## 4. Public dataset schema

- `windows.parquet`: 575,265 windows.
  - 574,849 in the LOSO set (P3/P4), 574,848 in the RQ2 set (P5/P6), 574,432 in both.
  - Per subject: 289,672 (User01), 144,205 (User02), 141,388 (User07).
  - 574,823 labelled (both validity flags true).
- Column-level documentation (dtype, unit, range, meaning, role, privacy transformation): `docs/P7_PUBLIC_DATA_DICTIONARY.md`.
  Machine-readable: `schema.json`.
- **Model input:** the 48 pressure integers only, divided by 4095 by the models. The P4 derived families are computed
  from them by the committed feature code, and no feature is precomputed. Time, identity, phase and control fields
  are never inputs; the leakage gate checks this in every run.
- **Arrays rebuilt by `PublicRelease`:**
  - `fold_data(k)`: the LOSO windows with the outer and inner partitions of their session.
  - `subject_windows(s, b)`: a subject's RQ2 windows with the partition of their (session, night) piece at budget b.
  The equivalence gate (§7) proves both equal the private arrays.

## 5. Relative-time transformation

- **Anchor:** local midnight of the date of the subject's first night (date of first row − 12 h); one per subject.
- **Time:** `time_s` = timestamp − anchor. Night key `D####` = ⌊(time_s − 43,200)/86,400⌋ + 1. Readable
  `D#### HH:MM:SS`.
- **Invariants:**
  - order, gaps and durations, clock time of day, the noon boundary, night grouping and ordinals, and the concurrency
    of the two User02 mats are exact;
  - calendar date, weekday and the calendar alignment between subjects are removed.
- **How the invariants were verified:**
  - **Tests:** on synthetic data, the mapping keeps night grouping, differences and time of day; relative times
    round-trip; negative times are refused.
  - **Equivalence gate:** every model-ready array equals its private counterpart (§7).
  - **Reproduction:** every P5/P6 night-level result is identical. The bootstrap resamples nights in sorted night-key
    order, and `D####` sorts exactly like the calendar dates, so even the resamples are identical.
- **Comparison rule for committed tables:**
  - A committed night date and its public key may differ only by one whole-day shift per subject.
  - The shift must be the same in every table.
  - The shift values are never written out.
  - Three tables carry night ids: `p5_per_night` (8,538 cells), `p5_budget_counts` (36 cells) and
    `p6_level_mismatch_trajectory` (604 cells). All three subjects' shifts are consistent across them.

## 6. Release manifest and checksums

| File | Bytes | SHA-256 (first 16) |
|---|---|---|
| `windows.parquet` | 29,955,714 | `79fdf6cd80eb2cac` |
| `splits/v1.0_loso/outer_folds.csv` | 128,717 | `6f2fc7d22925d9a3` |
| `splits/v1.0_loso/inner_folds.csv` | 182,258 | `a25e6efa9b1aa740` |
| `splits/v1.0_personalization/chronological.csv` | 243,641 | `129c37e6c0e63752` |
| `control_events.csv` | 13,309 | `63a1ec18e2f6a4c0` |
| `p5_plan_public.yaml` | 17,083 | `ff769d7673ad2a78` |
| `reference_digests.json` | 24,295 | `8ebb401ec26760ec` |
| `schema.json` | 16,063 | `7bf0919fdb3fc1f6` |
| `excluded_sources.csv` | 486 | `954c468953687d11` |
| `README.md` | 5,567 | `4c6685c8b7c7b2c2` |
| `manifest.json` | 8,186 | `72ac8cf347696d92` |

- **The manifest records:**
  - release version, protocol version and hash, split hashes and the split manifest hash;
  - source-dataset identity (canonical_v1 primary content and file hashes);
  - base tag `p6-robustness` → `16980ae`, builder commit `402c1ff` and the builder file hashes;
  - P5 plan hash, window rule, subjects, streams and counts;
  - target, pressure, time, split and window-set representation;
  - excluded sources with reason, confirmation and decision (DATA_POLICY §5.4);
  - the public/private primary-window digests, the equivalence result, the privacy checks passed;
  - the SHA-256 of every other file.
- **Determinism:** an in-place rebuild and a rebuild into a fresh directory are byte-identical for all 11 files,
  including the manifest.
- **Byte-exact Git storage:** `.gitattributes` keeps `data/release/**` free of line-ending conversion. Two of the
  CSVs use CRLF (`write_csv`), and a Windows checkout with `core.autocrlf=true` would otherwise change their bytes.
- **Builder fixes found while building and reproducing.** Each was committed before the rebuild that used it, so the
  manifest records a clean builder commit:
  - the public plan's description now mentions the removed run ids; split copies are verified on load (`ad97599`);
  - a stale manifest in the output directory entered the build checks (`33c68f8`), and its deletion now goes through
    `io_guard` (`b8b6696`);
  - **the public plan had lost its integer budget and seed keys** through a JSON round trip, which would have broken
    every public P5 run; a new build check compares the public plan with the private plan key by key (`2e9ec9c`);
  - the manifest's excluded-source list gains `exclusion_confirmed_by` (`5ff6a52`);
  - the validator scans for secrets (`402c1ff`).
  Every fix left `windows.parquet` and the other data files byte-identical.

## 7. Private/public equivalence

- **At build time,** with canonical_v1 available, the gate rebuilds every model-ready array from the public files and
  compares it with the private one:
  - **LOSO folds 1–3:** pressure, targets, labels, outer and inner partitions and provenance (under the D-049 time
    mapping) are bitwise equal. All 574,849 windows are included.
  - **15 subject × budget sets:** the P5 arrays (pressure, targets, labels, partitions, primary flags, provenance)
    are bitwise equal.
  - **Split files:** each public split equals the D-049 mapping of the private split, row for row.
  - **P5 plan:**
    - the public primary-window digests match the private digests recorded in the frozen plan;
    - the public plan equals the private plan except for the mapped nights and the removed run ids.
- **Result:** 18/18 equivalence checks and 2/2 plan checks pass.
- `PublicSubjectWindows.primary_digest` returns the private digest only when the public digest equals the value in
  the manifest, so the P5 check "primary test windows equal the committed plan" works unchanged from the release.

## 8. Core reproduction workflow

`python scripts/reproduce_public_release.py --data data/release/public_release_v1 --tier core`:

1. **Release:** the privacy/integrity validator and the manifest hashes (24 checks). Nothing runs if one fails.
2. **Public mode** (`src/evaluation/public_reproduction.py`):
   - The unchanged P3/P4/P5/P6 code reads the release through `PublicSession`.
   - canonical_v1, the raw data and the private split files raise if touched.
   - Runs and tables go under `outputs/p7/reproduction/`.
   - Every run passes the public leakage gate before training. This is the P2 gate on the public split copies:
     split-level L2/L4/L5/L6/L8, run-level L1/L3/L4/L9/L10/L11, and the release manifest in place of the
     canonical-data check L7.
3. **P3:**
   - training-mean for folds 1–3;
   - the 9 RAW-TCN finals from the committed P3 selection;
   - prediction digests, and weights against the P5 plan's base-checkpoint digests;
   - P3 tables.
4. **P5:**
   - the reproduced P3 models reload and predict bitwise;
   - the 45 runs from the public plan (b = 0 base evaluation; b > 0 fine-tuning with the frozen recipe);
   - prediction digests;
   - aggregation, the level diagnostic, and the P5 tables and figures.
5. **P6:** the unchanged analysis on the reproduced P5 tables and predictions, then the P6 tables and figures.
6. **Comparison:** every paper table against the committed one (§5 rule). The figures are compared for information.
   The summary goes to `outputs/p7/reproduction/p7_reproduction_summary.json`.

- **Not reproduced by design** (D-050): the inner searches. `p3_selected_configs.csv`, `p4_selected_configs.csv` and
  `p4_inner_score_range.csv` are selection records; the frozen selections are inputs of both tiers.

Local core result (release manifest of `de590f9`; data files identical to the final release):

| Stage | Checks | Result |
|---|---|---|
| release | 24 | pass |
| P3 | 3 training-mean + 9 final prediction digests, 9 weight digests, 4 tables | 25/25 |
| P5 | base reload 9/9, 45 prediction digests, 12 tables | 58/58 |
| P6 | 11 tables | 11/11 |
| **total** | | **118/118 PASS** |
| figures (information) | 9 PNG | 9/9 byte-identical |

- **Tables:** 25 of 28 are byte-identical. The other 3 are identical except for night-key cells (§5).
- **Run time:** 467 s (P3 256 s, P5 201 s, P6 9 s).

## 9. Extended P4 reproduction

`--tier extended` runs the core tier, skipping complete runs but re-checking everything, and then the P4 stage:
- **Runs:** the 45 P4 finals (5 families × 3 folds × 3 seeds) from the committed P4 selection, in public mode with
  the public gate. The derived MOVEMENT/CONTACT inputs are computed from the released pressure values by the
  committed feature code.
- **Checks:**
  - every prediction file against its reference digest;
  - `p4_ablation.aggregate` on the reproduced P4 runs, with the RAW reference taken from the **reproduced** P3
    tables (not the committed ones);
  - the 8 P4 result tables compared with the committed tables.

Local extended result (release manifest of `96f78a8`; data files identical to the final release):

| Stage | Checks | Result |
|---|---|---|
| release, P3, P5, P6 | as in §8 | 24 + 25/25 + 58/58 + 11/11 |
| P4 | 45 prediction digests, 8 tables | 53/53 |
| **total** | | **171/171 PASS** |
| figures (information) | 9 PNG | 9/9 byte-identical |

- **Tables:** all 8 P4 tables are byte-identical: `p4_primary_summary`, `p4_outer_by_seed`, `p4_vs_raw`,
  `p4_vs_training_mean`, `p4_incremental_effects`, `p4_seed_consistency`, `p4_bias_offset`, `p4_secondary_strata`.
- **Run time:** P4 stage 1,808 s. The core stages took 44 s because their runs were already complete and only
  re-checked.

## 10. Clean-checkout results

- **Setup:**
  - a detached git worktree at `59f903e`: the final release metadata, manifest `72ac8cf3…`, builder `402c1ff`;
  - `windows.parquet` copied into `data/release/public_release_v1/` (the manifest verifies it);
  - nothing else: no canonical_v1, no raw data (only `data/raw/README.md`), no `outputs/`.
  - To prove the private split files are not needed, the committed `data/splits/v1.0_*` files were deleted from the
    worktree before the runs. That is a working-tree deletion only, which is why the run records a dirty tree.
- **Sequence:** full test suite → public validator → `--tier core` → `--tier extended`, into the worktree's own
  `outputs/p7/reproduction/`.

| Step | Result | Time |
|---|---|---|
| `pytest` | 328 passed, 8 skipped (tests that need raw data or canonical_v1) | 49 s |
| `validate_public_release.py` | 24/24 PASS | — |
| core: release / P3 / P5 / P6 | 24 / 25/25 / 58/58 / 11/11 → **118/118 PASS** | 469 s (P3 260, P5 198, P6 9) |
| extended: core stages re-checked, then P4 | 24 / 25 / 58 / 11 / 53/53 → **171/171 PASS** | 1,873 s (P4 1,829) |
| figures (information) | 9/9 PNG byte-identical, in both tiers | — |

- **Across local and clean runs,** every one of the 102 frozen prediction files (3 P3 training-mean, 9 P3 final,
  45 P4 final, 45 P5) matched its reference digest bitwise, and the 9 P3 weight digests equal the frozen P5 plan.
- **All 35 compared tables pass** (4 P3, 8 P4, 12 P5, 11 P6). 32 are byte-identical, and 3 differ only in night-key
  cells, under one consistent day shift per subject.
- The public-mode guards (§8) would have raised on any access to canonical_v1 or the private splits. None was
  raised.

## 11. Environment

| Component | Version / setting |
|---|---|
| OS | Windows 11 (10.0.26200) |
| Python | 3.12.1 |
| Packages | numpy 2.4.4, PyYAML 6.0.3, pyarrow 24.0.0, torch 2.12.0+cu126, matplotlib 3.10.9, pytest 9.0.2 (`requirements.txt`, unchanged in P7) |
| GPU | NVIDIA GeForce RTX 4060 Ti 16 GB, driver 581.29, CUDA 12.6, cuDNN 9.10.2 |
| Determinism | `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `torch.use_deterministic_algorithms(True)`, cuDNN deterministic, benchmark off, seeds per run, no data-loader workers |
| Run time | core about 8 min on this GPU (P3 finals about 4.3 min, P5 about 3.3 min, P6 about 10 s); extended adds about 30 min (45 P4 finals); a release build by the data owner takes about 2 min |
| Disk | release package 30.6 MB; reproduction outputs about 370 MB (core) and 660 MB (extended); about 4 GB RAM and 2.2 GB GPU memory per process |

- No dependency version was changed.
- **Changes to frozen code, all reproduction infrastructure:**
  - `p3_loso.aggregate` and `p4_ablation.aggregate/p3_reference` gain an option to leave out the inner-search
    tables;
  - `export_p3_tables` gains `export_csvs`;
  - `export_p4_tables` skips absent inner-search tables;
  - `run_p6_robustness` hashes its inputs where they were read;
  - `io_guard` gains `remove_file`.
  With defaults, the private P3/P4/P6 aggregation and export regenerate every committed table, figure and report
  block unchanged (checked before the pipeline commit).
- **Bitwise equality is established on this stack.** On a CPU, or another GPU, driver or library build, the same
  deterministic procedure can differ in the last floating-point bits. The digest checks would then fail by design,
  and the table comparison would show the size of the difference. No other stack was tested.

## 12. Excluded material

- **Sources** (no data; listed in `excluded_sources.csv` and the manifest):

  | Source | Role | Reason | Decision |
  |---|---|---|---|
  | `user01_metadata` | restricted metadata | restricted participant metadata | D-008 |
  | `user02_legacy_csv` | auxiliary | not used by protocol v1.0 | D-023 |
  | `user02_mat_22480_prefix_mismatch` | quarantined | unresolved device attribution | D-023 |
  | `user03_legacy` | auxiliary | not used by protocol v1.0 | D-023 |
  | `user06_auxiliary` | excluded invalid | setting issue confirmed by the data provider | D-017 |

- **Content not released:**
  - raw logs, canonical rows, the event text, firmware movement labels, provenance (source files, rows, chunk keys,
    file IDs);
  - absolute timestamps;
  - inner-search runs, checkpoints and predictions;
  - P3–P6 run directories. These are regenerated by the tiers; their prediction values are fixed by the digests.
- **Rows between window steps:** `windows.parquet` keeps only the 8 step rows of each window. The models never use
  the others.

## 13. Known limitations

- **Scope of the release.** It reproduces protocol v1.0's analyses. It is not a general-purpose dataset: windows
  follow the frozen 40-s rule, and other window lengths or row-level analyses cannot be derived from it.
- **Three subjects.** Subject, period, season, device and microclimate are confounded, so there is no population-level
  inference (unchanged from P3–P6).
- **Bitwise equality is platform-bound** (§11).
- **Inner searches are not in any tier.** The selections are taken as committed. A full-search option was not
  provided: it would re-train 96 P3 and 480 P4 inner runs, and D-050 leaves it out.
- **The release is one derived product.** Private canonical_v1 stays the source of truth. `windows.parquet` can be
  rebuilt only by the data owner.
- **Names and initials** are prevented structurally, not by a name scan: no list of names exists to scan for (§3).
- **Dates in the repository.** Absolute session-level dates remain in committed repository files outside the
  release (checklist D4).

## 14. External publication blockers

These are PI decisions. None of them is ticked automatically (`docs/P7_PUBLIC_RELEASE_CHECKLIST.md` §D).

1. **License:** license decision required before external publication. Both the data license of the package and a
   code license for the repository are needed; the repository has no LICENSE file.
2. **Hosting and DOI** for `windows.parquet` and the package (GitHub Release, Zenodo, Figshare, OSF, …). Nothing has
   been uploaded.
3. **PI approval of the release subset:** this is the P7 exit criterion "release subset approved". The provider's
   permission for public research release is on record (D-002).
4. **Absolute dates in committed repository files**, before the repository itself is made public.
5. **Citation and data-availability text,** written in P8.

## 15. P8 handoff

- **Manuscript-ready tables** (committed, generated by script, reproduced from the release):
  - P3: `p3_primary_summary`, `p3_tcn_outer_by_seed`, `p3_training_mean_by_fold`, `p3_secondary_strata`, and
    `p3_selected_configs` (selection record).
  - P4: `p4_primary_summary`, `p4_outer_by_seed`, `p4_vs_raw`, `p4_vs_training_mean`, `p4_incremental_effects`,
    `p4_seed_consistency`, `p4_bias_offset`, `p4_secondary_strata`, and `p4_selected_configs` /
    `p4_inner_score_range` (selection records).
  - P5: `p5_primary_mae/rmse/bias`, `p5_adaptation_gain`, `p5_by_seed`, `p5_later_span_mae`, `p5_budget_counts`,
    `p5_per_night`, `p5_user02_device_strata`, `p5_user01_sensor_phase`, `p5_level_diagnostic`, `p5_figure_data`.
  - P6: `p6_bootstrap_mae/rmse/bias`, `p6_bootstrap_seed_sensitivity`, `p6_drift_sensitivity`,
    `p6_level_mismatch_*`, `p6_user02_device_context*`, `p6_figure_data`.
  - For a public manuscript, the tables that carry calendar night ids (`p5_per_night`, `p5_budget_counts`,
    `p6_level_mismatch_trajectory`) should be shown with relative night keys or ordinals.
- **Manuscript-ready figures:**
  - `paper/figures/p5_fig1_temperature_mae.png`, `p5_fig2_humidity_mae.png`, `p5_fig3_abs_bias.png`,
    `p5_fig4_user02_devices.png`;
  - `p6_fig1_bootstrap_temperature.png`, `p6_fig2_bootstrap_humidity.png`, `p6_fig3_drift_temperature.png`,
    `p6_fig3_drift_humidity.png`, `p6_fig4_level_trajectory.png`.
  All 9 were regenerated byte-identically from the release on the recorded stack.
- **Reproducibility statement (draft facts):**
  - All models, predictions and tables of the study can be regenerated from the public release `public_release_v1`
    and the tagged code, without the raw data.
  - On the recorded environment (§11), re-running the frozen models from the release reproduced every prediction
    bitwise: 102 prediction files, 9 P3 model weights, and every result table, P3–P6 (§8–§10), including from a clean
    checkout.
  - The hyperparameter selections were not re-run (inner searches are outside the release tiers).
- **Data-availability statement, inputs:**
  - release name and version `public_release_v1`;
  - content: three anonymous subjects, four mat streams, 575,265 model-ready 40-s windows;
  - relative time only (D-049); the exclusions in §12;
  - manifest SHA-256 `72ac8cf347696d929b4408e3e1b21895cfe18b80a0d748188b47311c43f0f70f`;
  - raw data not distributed (provider README; restricted metadata never released);
  - still missing: license, repository/DOI and access conditions (§14).
- **Unresolved items:**
  - the §14 blockers;
  - the deferred secondary analyses from P6 (20/30-s window and 4095 sensitivity; adaptation-span bias calibration),
    which need their own decisions;
  - the `v1.0-paper` freeze in P8.
