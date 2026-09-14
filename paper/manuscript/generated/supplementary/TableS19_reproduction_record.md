# Table S19. Reproduction record

Verbatim copy of sections 6 and 8–10 of the P7 reproducibility report (`docs/P7_REPRODUCIBILITY_PUBLIC_RELEASE_REPORT.md`): release manifest and checksums, core and extended reproduction, and clean-checkout results. Commit identifiers refer to the version-controlled research repository.

### 6. Release manifest and checksums

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

### 8. Core reproduction workflow

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

### 9. Extended P4 reproduction

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

### 10. Clean-checkout results

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
