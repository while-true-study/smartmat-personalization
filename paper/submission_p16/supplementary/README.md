# Supplementary Materials

Supplementary tables S1–S44 (machine-readable CSV, full precision, no calendar dates; Table S19 is a Markdown reproduction record) and supplementary figures S1–S4. Generated from the committed result tables; do not edit by hand.

| Item | Content | Files |
|---|---|---|
| Table S1 | Strict LOSO per seed and training-mean predictor per fold | `TableS01a_p3_tcn_outer_by_seed.csv`, `TableS01b_p3_training_mean_by_fold.csv` |
| Table S2 | Strict LOSO device and phase strata | `TableS02_p3_secondary_strata.csv` |
| Table S3 | Selected configurations and inner-selection score ranges (selection records) | `TableS03a_p3_selected_configs.csv`, `TableS03b_p4_selected_configs.csv`, `TableS03c_p4_inner_score_range.csv` |
| Table S4 | Feature families per seed | `TableS04_p4_outer_by_seed.csv` |
| Table S5 | Feature families versus the training-mean predictor | `TableS05_p4_vs_training_mean.csv` |
| Table S6 | Feature families: per-subject summary, versus RAW and the pre-declared comparisons A-E | `TableS06a_p4_vs_raw.csv`, `TableS06b_p4_incremental_effects.csv`, `TableS06c_p4_seed_consistency.csv`, `TableS06d_p4_primary_summary.csv` |
| Table S7 | Bias and offset by feature family | `TableS07_p4_bias_offset.csv` |
| Table S8 | Feature-family device and phase strata | `TableS08_p4_secondary_strata.csv` |
| Table S9 | Adaptation gain and error decomposition | `TableS09_p5_adaptation_gain.csv` |
| Table S10 | Personalization RMSE and bias by budget | `TableS10a_p5_primary_rmse.csv`, `TableS10b_p5_primary_bias.csv` |
| Table S11 | Personalization on the per-budget later span (secondary) | `TableS11_p5_later_span_mae.csv` |
| Table S12 | Personalization per seed | `TableS12_p5_by_seed.csv` |
| Table S13 | Budgets, nights and windows (night ordinals) | `TableS13_p5_budget_counts.csv` |
| Table S14 | User02 mat strata and User01 sensor-phase strata | `TableS14a_p5_user02_device_strata.csv`, `TableS14b_p5_user01_sensor_phase.csv` |
| Table S15 | Temporal level mismatch (post hoc, descriptive) | `TableS15a_p5_level_diagnostic.csv`, `TableS15b_p6_level_mismatch_consistency.csv`, `TableS15c_p6_level_mismatch_spans.csv`, `TableS15d_p6_level_mismatch_trajectory.csv` |
| Table S16 | Night-level bootstrap of RMSE and bias, and seed sensitivity | `TableS16a_p6_bootstrap_rmse.csv`, `TableS16b_p6_bootstrap_bias.csv`, `TableS16c_p6_bootstrap_seed_sensitivity.csv` |
| Table S17 | Start-span sensitivity (post hoc) | `TableS17_p6_drift_sensitivity.csv` |
| Table S18 | User02 device, quality-phase and heater-context strata | `TableS18a_p6_user02_device_context.csv`, `TableS18b_p6_user02_device_context_bootstrap.csv` |
| Table S19 | Reproduction record (P7 report §6, §8–§10) | `TableS19_reproduction_record.md` |
| Table S20 | Post-hoc calibration comparators A–E on the primary span (seed summary) | `TableS20_p8_calibration_main.csv` |
| Table S21 | Post-hoc calibration comparators per seed | `TableS21_p8_calibration_by_seed.csv` |
| Table S22 | User02 per-mat calibration diagnostic (post hoc, added after the primary results were known) | `TableS22_p8_calibration_user02_per_mat.csv` |
| Table S23 | Residual variation: target SD, error SD and R (post hoc) | `TableS23_p8_residual_variation.csv` |
| Table S24 | Initialization control at b = 14 (post hoc) | `TableS24_p8_initialization_control.csv` |
| Table S25 | Night-level bootstrap of the comparator differences, all budgets and seeds (post hoc) | `TableS25_p8_comparator_bootstrap.csv` |
| Table S26 | Pre-registered interpretation map: cases per subject, target and budget (post hoc) | `TableS26_p8_interpretation_cases.csv` |
| Table S27 | Dynamic-signal diagnostic: R, Q, pooled and within-night correlations, oracle ratio (seed summary; second-order post hoc) | `TableS27_p8_dynamic_summary.csv` |
| Table S28 | Dynamic-signal diagnostic per seed (second-order post hoc) | `TableS28_p8_dynamic_by_seed.csv` |
| Table S29 | Dynamic-signal diagnostic: night-cluster bootstrap of the correlations (second-order post hoc) | `TableS29_p8_dynamic_bootstrap.csv` |
| Table S30 | Retrospective oracle affine ratio and the affine-calibration trigger (second-order post hoc) | `TableS30a_p8_dynamic_oracle_affine.csv`, `TableS30b_p8_dynamic_trigger.csv` |
| Table S31 | Pre-registered dynamic-signal cases J1–J8 and headlines (second-order post hoc) | `TableS31a_p8_dynamic_cases.csv`, `TableS31b_p8_dynamic_headlines.csv` |
| Table S32 | Additional external validation: source reconciliation coverage and windows (post hoc) | `TableS32a_p9_user03_qa_coverage.csv`, `TableS32b_p9_user03_qa_nights.csv`, `TableS32c_p9_user03_qa_totals.csv` |
| Table S33 | Additional external validation: results per predictor, configuration and seed (post hoc) | `TableS33a_p9_user03_summary.csv`, `TableS33b_p9_user03_by_seed.csv` |
| Table S34 | Additional external validation: per-night results and the pre-registered interpretation (post hoc) | `TableS34a_p9_user03_per_night_summary.csv`, `TableS34b_p9_user03_interpretation.csv` |
| Table S35 | Median constants, strict leave-one-subject-out and primary span (exploratory) | `TableS35a_p10_loso_constants.csv`, `TableS35b_p10_loso_metrics.csv`, `TableS35c_p10_rq2_constants.csv`, `TableS35d_p10_rq2_summary.csv` |
| Table S36 | Point-estimate counts of constants versus networks (exploratory) | `TableS36_p10_point_counts.csv` |
| Table S37 | Endpoint availability by history (exploratory) | `TableS37_p10_history_availability.csv` |
| Table S38 | Pressure-summary models on the common endpoints: all histories, ridge regression, bias, R and correlations, night-level intervals, selections and the pre-specified reading; the RAW-TCN trained on all 40-s windows as a training-pool sensitivity reference (exploratory) | `TableS38a_p10_history_metrics.csv`, `TableS38b_p10_history_bootstrap.csv`, `TableS38c_p10_history_interpretation.csv`, `TableS38d_p10_history_selection.csv`, `TableS38e_p11_model_comparison_training_pools.csv` |
| Table S39 | RAW-TCN retrained on the common endpoints: per seed and seed mean, epoch selection and pool counts (exploratory) | `TableS39a_p11_tcn_per_seed.csv`, `TableS39b_p11_tcn_seed_mean.csv`, `TableS39c_p11_epoch_selection.csv`, `TableS39d_p11_pool_counts.csv` |
| Table S40 | RAW-TCN retrained on the common endpoints: night-level paired bootstrap against the constants, the boosted models and the network trained on all 40-s windows, and the pre-specified reading (exploratory) | `TableS40a_p11_bootstrap.csv`, `TableS40b_p11_interpretation.csv` |
| Table S41 | Heater-context diagnostic: control-code audit and heater-context coverage by state, span and mat (post hoc, descriptive) | `TableS41a_p12_code_audit.csv`, `TableS41b_p12_context_counts.csv` |
| Table S42 | Heater-context diagnostic: target level by heater context (post hoc, descriptive) | `TableS42_p12_target_summary.csv` |
| Table S43 | Heater-context diagnostic: eta squared for both targets, raw, night-centred and night × mat-centred, three states and on/off only, both spans, with night-level intervals (post hoc, descriptive) | `TableS43_p12_eta_squared.csv` |
| Table S44 | Heater-context diagnostic: heater-conditioned source constant on both spans, night-level paired bootstrap, source composition, pre-specified reading, and errors of the constants and pressure models by heater context (post hoc, descriptive) | `TableS44a_p12_constant_metrics_full.csv`, `TableS44b_p12_constant_metrics_common.csv`, `TableS44c_p12_bootstrap_full.csv`, `TableS44d_p12_bootstrap_common.csv`, `TableS44e_p12_source_composition.csv`, `TableS44f_p12_interpretation.csv`, `TableS44g_p12_errors_by_context.csv` |
| Figure S1 | see the Supplementary Materials list of the manuscript | `figureS1_abs_bias.png` |
| Figure S2 | see the Supplementary Materials list of the manuscript | `figureS2_start_span_sensitivity.png` |
| Figure S3 | see the Supplementary Materials list of the manuscript | `figureS3_level_trajectory.png` |
| Figure S4 | see the Supplementary Materials list of the manuscript | `figureS4_user02_mats.png` |
