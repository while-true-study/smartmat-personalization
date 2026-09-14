# P8 — Table and figure selection

> **This is a recommendation for PI review.**
> - Nothing is deleted, and no committed table or figure changes.
> - Main and supplementary items are selections or re-formatting of frozen artifacts, produced by a deterministic
>   export (`scripts/export_manuscript_tables.py`, planned). No new metric is computed.
> - Public-facing versions use relative night identifiers only (P8 plan §8).

## 1. Main manuscript tables

| # | Content | Source (frozen) | Rows / layout | Notes |
|---|---|---|---|---|
| 1 | Dataset, cohort and protocol summary | `data/interim/manifest/canonical_v1_summary.csv` (rows, sessions per stream); `public_release_v1/manifest.json` (windows per subject); `p3_training_mean_by_fold` (LOSO train/test windows); `p5_budget_counts` (nights, primary test nights and windows) | one row per subject (User02 with its two mats as sub-rows), plus protocol columns (fold, adaptation budgets, primary span) | counts only, no performance. Nights as counts, never dates |
| 2 | Strict LOSO results | `p3_primary_summary` | training-mean vs RAW-TCN × {MAE, RMSE, bias} × {temperature, humidity}; columns User01, User02, User07, unweighted mean | seed means. The seed spread (from `p3_tcn_outer_by_seed`) can go in a footnote or in S1 |
| 3 | Feature-family comparison | `p4_primary_summary` (MAE, rank) and `p4_vs_raw` (Δ vs RAW, improved-subject count) | 7 rows (training-mean + 6 families) × {temperature, humidity} MAE per subject + unweighted mean; Δ vs RAW | footnote: each family has its own pre-declared selection. The bias columns go to S7 |
| 4 | Chronological personalization MAE | `p5_primary_mae` (seed mean ± SD) and `p5_adaptation_gain` (G, seeds improved) | subject × target rows, b = 0/1/3/7/14 columns; G at b = 14 or per budget | primary span nights ≥ 16, the same test nights for every budget |
| 5 | Night-level paired bootstrap | `p6_bootstrap_mae` (seed 0) and `p6_bootstrap_seed_sensitivity` | all 24 subject × target × budget cells: ΔMAE [95 %], side of zero, seeds 1/2 side | all 24 cells are shown, not only the favourable ones |

- **Space fallback:** Table 3 can be reduced to the unweighted-mean row per family plus the improved-subject counts,
  with the per-subject values moved to S6.
- **Split of the primary claim's evidence:** Table 5 and Figure 4 carry the pre-declared uncertainty. The post-hoc
  level-mismatch consistency table (`p6_level_mismatch_consistency`) is cited in §5.5 and placed in S15.

## 2. Supplementary tables

All 38 committed CSVs in `paper/tables/` have a role: 35 are reproduced from the release (P7) and 3 are selection
records.

| Source file | Role | Proposed item |
|---|---|---|
| `p3_primary_summary` | main | Table 2 |
| `p3_tcn_outer_by_seed` | supplementary | S1 P3 per seed |
| `p3_training_mean_by_fold` | Table 1 input; supplementary | S1 |
| `p3_secondary_strata` | supplementary | S2 P3 device/phase strata |
| `p3_selected_configs` | supplementary (selection record) | S3 selected configurations (with `p4_selected_configs`) |
| `p4_primary_summary` | main | Table 3 |
| `p4_vs_raw` | main (Δ columns) | Table 3 / S6 |
| `p4_outer_by_seed` | supplementary | S4 P4 per seed |
| `p4_vs_training_mean` | supplementary | S5 |
| `p4_incremental_effects` | supplementary | S6 pre-declared comparisons A–E |
| `p4_seed_consistency` | supplementary | S6 |
| `p4_bias_offset` | supplementary | S7 bias / offset by family |
| `p4_secondary_strata` | supplementary | S8 |
| `p4_selected_configs` | supplementary (selection record) | S3 |
| `p4_inner_score_range` | supplementary (selection record) | S3 |
| `p5_primary_mae` | main | Table 4 |
| `p5_adaptation_gain` | main (G) | Table 4 / S9 full gain decomposition |
| `p5_primary_rmse` | supplementary | S10 |
| `p5_primary_bias` | supplementary | S10 |
| `p5_later_span_mae` | supplementary (secondary span) | S11 |
| `p5_by_seed` | supplementary | S12 |
| `p5_budget_counts` | Table 1 input; supplementary | S13, with night ordinals instead of dates |
| `p5_per_night` | supplementary data only | released through `public_release_v1` / export with `D####` keys; never with calendar dates |
| `p5_user02_device_strata` | supplementary | S14 |
| `p5_user01_sensor_phase` | supplementary | S14 |
| `p5_level_diagnostic` | supplementary (post hoc) | S15 |
| `p5_figure_data` | figure source | Figures 2–3 |
| `p6_bootstrap_mae` | main | Table 5 |
| `p6_bootstrap_rmse`, `p6_bootstrap_bias` | supplementary | S16 |
| `p6_bootstrap_seed_sensitivity` | main (column); supplementary | Table 5 / S16 |
| `p6_drift_sensitivity` | supplementary (post hoc robustness) | S17 |
| `p6_level_mismatch_consistency` | supplementary (post hoc), cited in §5.5 | S15 |
| `p6_level_mismatch_spans` | supplementary (post hoc) | S15 |
| `p6_level_mismatch_trajectory` | figure source; supplementary | Figure 5 / S15, night ordinals only |
| `p6_user02_device_context` | supplementary | S18 |
| `p6_user02_device_context_bootstrap` | supplementary | S18 |
| `p6_figure_data` | figure source | Figures 4–5, S-figures |

- **Reproduction details** (release manifest, reproduction checks): S19, from P7 report §6–§10.
- **Three tables carry calendar night ids:** `p5_per_night`, `p5_budget_counts` and `p6_level_mismatch_trajectory`.
  They appear only through the export, with ordinals or `D####`.

## 3. Figures

| # | Recommendation | Source | Status |
|---|---|---|---|
| 1 | Study and evaluation pipeline: raw → canonical → strict LOSO (nested inner validation) → chronological adaptation (adaptation / buffer / primary test nights) → night-level analysis; the public-release reproduction path | none (schematic; no data) | **to create** in the figures pass |
| 2 | Temperature MAE vs adaptation budget, per subject and cohort mean, seed min–max | `paper/figures/p5_fig1_temperature_mae.png` (data `p5_figure_data`) | exists; re-render without the report caption |
| 3 | Humidity MAE vs adaptation budget | `paper/figures/p5_fig2_humidity_mae.png` | exists; re-render as for Figure 2 |
| 4 | Night-level paired bootstrap ΔMAE with 95 % intervals, temperature and humidity panels | `paper/figures/p6_fig1_bootstrap_temperature.png`, `p6_fig2_bootstrap_humidity.png` (data `p6_figure_data`) | exists; combine the two panels |
| 5 (if the limits allow) | Temporal level trajectory for the three negative/positive cases (User07 temperature, User01 humidity, User02 temperature) | `paper/figures/p6_fig4_level_trajectory.png` (x axis = night ordinal) | exists; otherwise S-figure. Labelled post hoc, descriptive |

- **Why Figure 4 is the bootstrap figure:**
  - It carries the pre-declared uncertainty (D-041) behind the primary claim.
  - The trajectory (Figure 5) explains the mechanism but is post hoc. If only four figures fit, it moves to the
    supplement and §5.5 cites it.
- **Supplementary figures:**
  - `p5_fig3_abs_bias.png` (|bias| vs budget);
  - `p5_fig4_user02_devices.png` (User02 per mat);
  - `p6_fig3_drift_temperature.png` and `p6_fig3_drift_humidity.png` (drift sensitivity);
  - `p6_fig4_level_trajectory.png` if not main.
- **Re-rendering:**
  - The committed PNGs carry report numbering in their titles ("Figure P5-1 …").
  - Manuscript versions are re-drawn from the same `*_figure_data.csv` by the export step, without report titles and
    with the same palette and marks.
  - The data and encodings do not change. The committed report figures stay as they are.
