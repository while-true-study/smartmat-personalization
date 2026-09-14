# Decisions

Single source of truth for research decisions and their rationale.

Rules:
- Entries are listed in ID order (chronological) and are append-only. To change a decision, add a new
  entry and set the old one's status to `Superseded by D-XXX`; never rewrite its content.
- Status values: `Proposed`, `Accepted`, `Rejected`, `Superseded by D-XXX`.
- Rationale must never cite test-set results. If a decision is taken after any experimental result was
  seen, the entry must say so and name the results (RESEARCH_PROTOCOL §6).
- Format of every entry:

```
## D-XXX — Decision title
Date:
Status:
Context:
Decision:
Evidence:
Consequence:
```

---

## Open decisions

Do not resolve these by assumption. Each is closed by a decision entry below.
Evidence: `docs/initial_dataset_inventory.md`. Analyses planned for P0: `docs/P0_DATASET_AUDIT_PLAN.md`.

| ID | Question | Owner | Resolve in | Blocks | Tracking |
|---|---|---|---|---|---|
| OPEN-01 | **Closed 2026-09-13 by D-017:** provider confirmed the User06 source is invalid (setting issue). User06 source `excluded_invalid` (raw kept); User03 legacy stays auxiliary; subjects not merged. History: **Identity answered:** User03 ≠ User06 (PI, 2026-09-12; D-013). **Still open: measurement provenance** — why the rows of `user03_legacy` are contained in User06's recordings of 2025-10-06…10-13, and to which subject those measurements belong. Until then the overlapping recording is provisionally quarantined from primary evaluation (D-013). Original question: `user03_legacy` is a seconds-truncated copy of `user06_auxiliary` for 2025-10-06…10-12 (99.99–100 % of User03 rows found in User06). **A1 evidence (2026-09-12):** 100 % of User03 rows (minute-level) and 100 % of its 5-row value sequences occur in User06; offsets 0–59 s; each User03 file is a contiguous excerpt of one User06 night file; ordered runs up to 13,180 sequences. Overlap is inconsistent with independent subject recordings; identity still unconfirmed. No other subject pair shares any data. | data provider | P0 | any use of User03/User06 | `docs/issues/P0-01_user03-user06-provenance.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §4; `outputs/qa/p0/provenance/` |
| OPEN-02 | **Closed for P0 2026-09-13 by D-023:** both files stay quarantined and are not part of canonical_v1. Attribution to 22482 (strong evidence) remains a provider question; non-blocking. Device of `user02/mat_22480/_prefix_mismatch/sm22482_0824.txt` and `…_0825.txt`. Evidence favours 22482 (filename prefix, JSON root key `smartmat_22482`, the only dates with a 22480 file but no 22482 file). A1: the two files share no rows with either device's files (not duplicates). **A2 evidence (2026-09-12):** they fill 22482's timeline seamlessly (start 30 min after 22482's last row, end 3 s before its next row), record simultaneously with 22480's own stream for 7.0 h, and match 22482's humidity regime (22480 − quarantined: −2 °C / −16 %RH vs typical 22480 − 22482: −2 / −19). Strong, consistent evidence for 22482; attribution still `unresolved` pending provider confirmation. A5: the gap between the two quarantined files (1,804 s) and their start relative to 22482 (1,806 s) follow 22482's lost-upload-chunk pattern (n × 1,800 s + a few s). | data provider | deferred (non-blocking) | use of those 2 files | `docs/issues/P0-02_user02-dual-device-protocol.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §5; `docs/P0_A2_USER02_DEVICE_REPORT.md` §9; `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md` §6 |
| OPEN-03 | **Use policy closed 2026-09-13 by D-036 (P2):** both mats are used as two separate input streams of one subject, with no fusion, preference or dropping, and device-stratified diagnostics. Physical placement stays a non-blocking provider question; the protocol does not depend on it. **P0 part closed 2026-09-13 by D-027:** both mats are kept as separate device streams of User02; no merge, fusion or deletion. The use policy moves to P2. Physical setup of User02's mats 22480/22482: they overlap for ~505 h and both register occupancy in 66.8 % of jointly recorded minutes, with different temperature/humidity. Same bed (body regions)? Different locations? How to use two concurrent streams (separate, one, fused)? A1: 46 co-recorded dates, 0 shared rows or sequences — concurrent but distinct streams. **A2 evidence (2026-09-12):** 253 h simultaneous recording (76 % of 22480's time); no pressure coupling (|r| ≤ 0.03 for all descriptors, no lag peak within ±30 s, movement-event coincidence at chance level, no clock offset found within ±12 h); occupancy agreement at chance under all 14 definitions (κ −0.07…0.00, "both active" 18–90 % depending on threshold); persistent T/H offset (22480 − 22482: −2 °C, −19 %RH; humidity lower on 46/46 dates); different channel-load patterns. Physical placement and the use policy for the two streams remain unresolved. **A9b (2026-09-13):** after 22482's recording gap of 2026-08-24/25 (where the two quarantined files lie, OPEN-02), 22482's P6 active share falls from 0.63 to 0.23 (δ −1.0) and its pressure-sum median from 2,031 to 1,324. Over the same nights 22480's P1 activity and pressure sum rise (δ +0.88 / +0.71). This is consistent with load moving between the mats, not with a channel fault. It is recorded as an observed distribution shift, not flagged; the cause is unresolved. | provider + PI | P2 (use policy) | model input for User02 | `docs/issues/P0-02_user02-dual-device-protocol.md`; `docs/P0_A1_PROVENANCE_REPORT.md` §5; `docs/P0_A2_USER02_DEVICE_REPORT.md` |
| OPEN-04 | **Non-blocking; protocol v1.0 does not depend on it (D-029):** RQ1 claims are stated as unseen subject under the combined subject–period–device shift. **Non-blocking; deferred to P1/P2 interpretation** (consequences documented in A11). Device IDs of User01, User07, User02 legacy, User03, User06. Recording periods hand over day-to-day (User01 → User07 → User02), suggesting reused mats. Subject and device may be confounded. **A11 evidence (2026-09-13):**<br>• A hardware ID is recorded only for the User02 mats: folder, filename, JSON root key in every file, and a row column from 08-29/08-31. Each ID maps to User02 only.<br>• User01 (all phases), User07 and both legacy sources carry no ID in filename, JSON key or rows.<br>• Hand-overs: User01 → User07 in 36.3 h; User07 → User02 mats in 14.5 h. This is consistent with moved mats but is not evidence.<br>**Reuse cannot be checked from the data; unresolved.** Consequences for RQ1 are documented: subject, period and device configuration are confounded in every fold (A11 §5). | data provider | P1/P2 (non-blocking) | RQ1 interpretation | `docs/P0_A11_COVERAGE_CONFOUNDING_REPORT.md` §3, §5 |
| OPEN-05 | **Closed 2026-09-13:** the raw package stays in place (D-005); canonical_v1 reads it through `configs/paths.yaml`. Move the raw package into `data/raw/` or keep it at `스마트 매트 데이터 정리/`? | PI | closed | nothing (path is configurable) | D-005 |
| OPEN-06 | **Closed 2026-09-13 by D-024.** Session definition (files ≠ sessions: files overlap and some span 30–57 h). **A5 evidence (2026-09-12):** confirmed quantitatively. Files hold parts of two nights (internal gap > 2 h in User01 12, 22480 3, 22482 29, User07 3 files). 22482 nights are split across files at 06:1x–09:1x with recording continuing 2–5 s later (10 boundaries), and 13 cuts lost exactly 1–3 upload chunks (n × 1,800 s + 3–8 s). 18 primary-group boundaries overlap through repeated chunks. For User01/22480/User07 most boundaries (139/150, 41/44, 97/99) fall in > 2 h gaps. No gap threshold chosen; pending A7. **A7 evidence (2026-09-12):**
- Sampling is 3 s nominal (p99 5 s) on all primary timelines.
- Gaps are bimodal: ≤ 5 min or > 2 h, with only 1–19 gaps per timeline between them.
- User01/User07 have a recurring ≈ 2-min pause (120–140 s), unrelated to upload chunks.
- Thresholds < 5 min fragment nights. 5–90 min is a plateau (≈ 1 session per night) for User01, 22480 and User07.
- 22482 has no plateau because 13 gaps are exactly 1–3 lost upload chunks at morning file cuts (mat mostly occupied on both sides). Bridging them gives 1.12–1.24 sessions per night.
- Session lengths are quantised in 30-min chunks.
- Timeline A vs de-duplicated view: identical session structure.
Candidate policy proposed as D-015 (Proposed); not accepted. | PI | P0 | splits | `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md` §6; `docs/P0_A7_TEMPORAL_GAP_REPORT.md`; D-015 |
| OPEN-07 | **Closed 2026-09-13 by D-014 (accepted), implemented in canonical_v1 (D-028).** De-duplication policy for ~204 k identical rows shared by adjacent files, and for repeated rows/timestamps within files. **A5 evidence (2026-09-12):** in the primary groups all file overlaps are exact duplicate blocks (18 pairs; all 300 repeated chunk keys identical). Repeated copies never disagree (0 between-file conflicts). Cross-file exact copies: 187,190 rows (4.33 %), plus one 600-row chunk repeated inside `sm22482_0816`. Separately, 10,997 same-second timestamps carry two *different* readings inside one file (not duplicates), 272 adjacent same-second rows are identical, and 4 rows differ only in event text. Proposal: D-014 (Proposed). A7 note: removing copied blocks row for row removes 187,814 rows in the primary groups. That is 24 more than A1 + 600, because 24 same-second identical pairs were copied along with their chunk; the originals remain. | PI | P0 | interim tables | `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md`; `docs/P0_A7_TEMPORAL_GAP_REPORT.md` §1; D-014 |
| OPEN-08 | **Closed 2026-09-13 by D-026.** Timestamp policy: year inference for MM-DD rows, legacy minute-resolution rows, timezone, and the out-of-order steps. | PI | closed | interim tables | D-026 |
| OPEN-09 | **Closed 2026-09-13 by D-025.** Handling of temp/humid sentinel zeros (chunk starts) and glitch values (−254, 256, 262). **A8 evidence (2026-09-13):**<br>• Invalid-candidate targets are 0.10 % of primary rows (4,132 of 4,136,059); no missing or non-finite values.<br>• Joint zeros (T = H = 0) arise from two mechanisms: single-row start sentinels at a recording/chunk start (125 / 51 / 61 / 118 rows in User01 / 22480 / 22482 / User07), and dropout episodes. 86 % of all zero rows fall in two episodes: User01 2025-12-28 daytime, and 22482 night 2026-08-08/09.<br>• All 147 extreme values (T −254, 171–256; H 135–262) are in that 22482 night.<br>• No abrupt jump or spike exists between valid observations within 5 s (max 1–2 °C, p99.9 1 %RH).<br>• The 148 same-second target conflicts are ±1 quantisation steps (119) or zero-vs-reading (29).<br>Flagging proposed as D-016 (Proposed); episode-level exclusion, clipping, interpolation and jump thresholds are not decided. | PI | P0 | targets | `docs/P0_A8_TARGET_QUALITY_REPORT.md`; D-016 |
| OPEN-10 | **Closed 2026-09-13 by D-038 (P2):** heater state is not an input covariate; valid targets are kept whatever the control context; heater state between events is not reconstructed; control events are used only for event-conditioned stratification/sensitivity (P6). **Deferred to P2.** Target definition under heater control: the T/H sensor measures a heater-controlled microclimate. Is heater state a covariate, a stratifier, or excluded? **A8 note (2026-09-13):** long constant-temperature runs (≥ 1 h cover 84 % of 22480 and 80 % of User07 recording time; 22480 is at 28–30 °C in 96 % of rows) while humidity keeps moving. This is consistent with 1 °C quantisation of a stable or regulated microclimate, not a frozen sensor. The cause and whether regulated periods are meaningful targets remain open. | PI | P2 (informed by P0/P1) | RQ1–RQ3 | `docs/P0_A8_TARGET_QUALITY_REPORT.md` §5 |
| OPEN-11 | **Closed 2026-09-13 by D-035/D-037 (P2):** `sensor_phase` is a window boundary and a reporting stratum, never an input; there is no phase-specific scaling (D-033); chronological spans may cross the boundary and are reported by phase. User01 pressure-sensor replacement on 2026-01-25: treat as distribution shift boundary? Effect on the chronological adaptation protocol. **A9 baseline evidence (2026-09-13):** a step, not a drift, between the morning and evening recordings of 2026-01-25. Rows with a channel at 4095: 22.1 % before, 18 rows (0.002 %) after. Pressure-sum median 4,420 → 2,976, p95 10,157 → 5,022. Mean active channels 2.07 → 3.55. The full before/after comparison is A10. **A10 evidence (2026-09-13):**<br>• The change sits in the 9.4 h recording gap 2026-01-25 08:07:26 → 17:31:21. It is the strongest change point of the User01 series (core consensus rank 1 for nights and sessions at w = 3 and 7).<br>• Nights ±14: the 4095 share drops from 16.0 % to 0, p95 from 10,889 to 5,355 and the median from 6,087 to 3,361; active channels rise from 2.72 to 3.66. Cliff's δ = ±1 with complete separation; placebo windows show no separation.<br>• The step fits better than a line. Duration, clock time, temperature, humidity and sampling are continuous across the gap.<br>• High values compress (P2/P3/P5 about ⅓ when active), while P1/P5/P6 respond more often.<br>**The boundary question is answered by D-019** (`sensor_phase` s1/s2, provenance only). Still open for P2: phase-aware preprocessing, scaling and evaluation, and whether adaptation/test spans may cross the boundary. | PI | P2 (handling) | RQ2 | `docs/P0_A10_USER01_SENSOR_PHASE_REPORT.md`; D-019 |
| OPEN-12 | **Closed 2026-09-13: moot after D-017** (User06 source excluded; relevant only if it were ever re-admitted). Adopt "`.` before P1 is a delimiter" for User06 files 1003–1011 in preprocessing (strong evidence; see inventory §8.3). A1: under this reading User06 rows align exactly with User03 rows, which have a separate `FSR1` column. | PI | — | nothing (source excluded) | `docs/P0_A1_PROVENANCE_REPORT.md` §4.4; D-017 |
| OPEN-13 | **Closed 2026-09-13 by D-023:** auxiliary sources are preserved in canonical_v1 as a separate file and are not used in primary LOSO, personalization or primary metrics; secondary/sensitivity use needs its own protocol. Whether and how auxiliary sources enter training pools. After D-017 the auxiliary pool is User02 legacy and User03 legacy, both minute-resolution and both valid data (User03 confirmed by the PI, D-021). A9 (2026-09-13): User02 legacy P5 is at 4095 in 50.8 % of rows (runs up to ≈ 112 min); User03 legacy P3–P5 at 4095 in 7–10 % of rows. | PI | closed | RQ1 | D-023; D-017; `docs/P0_A9_PRESSURE_QUALITY_REPORT.md` §3 |
| OPEN-14 | **Non-blocking; protocol v1.0 does not depend on it.** **Non-blocking; deferred to P1/P2.** No frozen P0 policy depends on these dates; the sensor-change date is confirmed by the data (D-019). Metadata date inconsistencies (e.g. heating start written as 2026-11-18, log-format change as 2026-12-17; data suggest 2025). | data provider | P1/P2 (non-blocking) | covariate timeline | — |
| OPEN-15 | **Closed 2026-09-13 by D-038 (P2):** firmware movement labels are not model inputs in v1.0; MOVEMENT features are computed from P1–P6 (D-039). Admissibility of firmware movement labels (UM/DM/LM/RM/NM) as model inputs / movement-derived features. | PI | P2 | RQ3 | — |
| OPEN-16 | **Closed 2026-09-13 by D-020:** canonical P0 primary cohort User01, User02, User07. History: final primary cohort; three candidates give only three LOSO folds; the statistical plan must reflect this (carried into P2). Provisional cohort: D-013, restated in D-017. A11: all three pass every structural check, each `eligible_with_caveat`. | PI | P0 | RQ1 | D-020; `docs/P0_A11_COVERAGE_CONFOUNDING_REPORT.md` §4 |
| OPEN-17 | **Closed 2026-09-13 by D-033 (P2):** fixed physical-range scaling P / 4095, with no fitted input scaler; 4095 is kept as observed; sensitivity analyses belong to P6. Pressure-scale differences between subjects/periods (User01 saturates at 4095; User02 max 3731; User07 max 4023): normalisation strategy that respects L3/L11. **A9 evidence (2026-09-13):**<br>• All sources have six populated channels. There are no missing channels, no non-standard layouts and no out-of-range or non-integer values.<br>• 4095 is a pile-up at the ceiling (275,601 cells vs 789 at 4094). 99.99 % of these cells are in User01 before the sensor change. 22480 has 17 cells; 22482 and User07 have none.<br>• Every non-zero constant run ≥ 1 min is a 4095 plateau. There is no interior-value stuck channel and no frozen frame on the current mats.<br>• Pressure-sum medians: User01 3,817 (old sensor ≈ 4,420, new ≈ 2,976) vs 1,764–2,037 on the current mats. Channel profiles differ (22482 more even).<br>Proposed input-validity rule D-018; 4095 handling and scaling stay open (P2, training data only). | PI | P2 | preprocessing | `docs/P0_A9_PRESSURE_QUALITY_REPORT.md`; D-018 |
| OPEN-18 | **Closed 2026-09-14 by D-049:** releases carry no calendar date; per-subject relative time (whole-day anchor shift, `D####` day indices). Public release: absolute dates or relative day indices. | PI + provider | closed | release | D-049, D-050 |
| OPEN-19 | **Closed 2026-09-13 by D-022 — class B, non-blocking but flagged. Handling fixed by D-035 (P2):** the phase is a window boundary and a reporting stratum; 22482 P1 is used as recorded, and no phase is excluded. A9b re-derived the change without assuming the date:<br>• The P1 response collapses in the recording of the night 2026-08-19 (hourly onset ≈ 08-20 02:00) and is fully shifted from 2026-08-20 21:37:33.<br>• The collapse is abrupt: complete separation over ±3/±7 nights; step R² 0.83 vs line 0.60.<br>• It is persistent to the last night (recovered fraction ≈ 0).<br>• It is P1-only: the other channels have \|δ\| ≤ 0.51, and the pressure sum without P1 is stable.<br>• 22480 and T/H show no concurrent shift, and no schema/firmware boundary is nearby.<br>The P6 decline is a separate later change (2026-08-25), recorded under OPEN-03. Cause still asked of the provider; handling in P2. Original text: User02/22482 channel P1 from 2026-08-20 (A9): active share 0.49 → 0.13, median when active 759 → 26, p99 2,007 → 371. P6 active share 0.57 → 0.28 over the same dates. P2–P5 unchanged; the other mat (22480) shows no such drop. Was the mat moved, replaced or damaged? Use of 22482 data after that date as test/adaptation data depends on it. **A11 (2026-09-13):**<br>• The affected slice is 202.0 h in 22 nights (41 % of 22482's hours); 64.9 h of it are also covered by 22480.<br>• Without it, User02 keeps 438.8 h in 45 nights.<br>• **Not blocking for the cohort** (D-020). It is a device-period quality issue whose flag (start, channels) must be defined before P0 closes: provider answer, or the short audit A9b. | data provider + PI | P2 (handling) | User02 splits | D-022; `docs/P0_A9B_USER02_CHANNEL_ANOMALY_REPORT.md`; `docs/P0_A9_PRESSURE_QUALITY_REPORT.md` §5; `docs/P0_A11_COVERAGE_CONFOUNDING_REPORT.md` §3 |
| OPEN-20 | **Non-blocking; protocol v1.0 does not depend on it (D-039):** geometry-free features only; a layout-based feature needs a protocol version bump. Physical layout of P1–P6 on the mat and the legacy `FSR_k` ↔ P_k mapping (positional assumption). A9: the strongest positive correlations are P1–P4, P2–P5, P3–P6 on all current mats. This is compatible with, but not proof of, paired positions. Needed before any spatial or channel-selection feature. | data provider | P2 (non-blocking) | spatial features | `docs/P0_A9_PRESSURE_QUALITY_REPORT.md` §2, §6 |
| OPEN-21 | **Non-blocking; not a boundary in v1.0 (D-035).** Reported as a known limitation (window rule D-032 is time-based, so the 2-s episode does not change the time scale). Other User01 acquisition changes inside `sensor_phase` s1 (A10):<br>• **2025-12-17**, the documented log-format change (first compressed log): active channels 1.51 → 2.49 and dominant-channel switches 29 → 92 /h, both with complete separation over ±7 nights. The 4095 share is unchanged.<br>• **2026-01-03…07**: a temporary 2 s sampling regime, with the 4095 share dipping for about a week.<br>• From **2026-01-08**: 3 s sampling with wider jitter.<br>• **2025-12-25**: an undocumented +49 % pressure-sum level shift.<br>Did firmware/logging changes alter pressure reporting? Should acquisition-period labels (log format, sampling regime) be carried as further provenance fields? Not merged into `sensor_phase`. | data provider + PI | P2 (non-blocking) | RQ2 spans within User01 | `docs/P0_A10_USER01_SENSOR_PHASE_REPORT.md` §6, §8 |
| OPEN-22 | **Open (P8 publication blocker).** Code license of the repository and data license of `public_release_v1`. The repository has no LICENSE file. | PI | before `v1.0-paper` | Data/Code Availability final text; external publication | P7 checklist D1; D-051 |
| OPEN-23 | **Open (P8 publication blocker).** External hosting and persistent identifier (DOI) for `public_release_v1` (`windows.parquet` is not in Git, D-050). | PI | before `v1.0-paper` | Data Availability final text; external publication | P7 checklist D2; D-051 |
| OPEN-24 | **Open (P8 publication blocker).** PI approval of the release subset (the P7 exit criterion) and of the final manuscript/release state. | PI | before `v1.0-paper` | `v1.0-paper`; external publication | P7 checklist D3; D-051 |
| OPEN-25 | **Open (P8 publication blocker).** Public scope of the session-level calendar dates in committed repository files outside the release package (split files, P5 plan, subject mapping, three paper tables, reports): keep the repository private, publish a de-identified copy, or accept. No history rewrite without a decision. | PI | before any public repository or code archive | Code Availability; public repository | P7 checklist D4; D-049 |
| OPEN-26 | **Open (P8).** Ethics / IRB information for the manuscript. The provider confirmation of consent and release permission (D-002) is not an IRB approval; no institutional identifier may be invented. | PI | before submission | IRB / informed-consent statements | `paper/manuscript/manuscript.md` |
| OPEN-27 | **Open (P8).** Bibliographic details and scope of the authors' ICFICE conference paper (not in the repository): needed for the Introduction and the extension map. | PI | before submission | Introduction; `docs/P8_CONFERENCE_EXTENSION_MAP.md` | `docs/P8_CONFERENCE_EXTENSION_MAP.md` |
| OPEN-28 | **Open (P8); disclosure drafted by D-053 (Proposed; supersedes D-052).** Still needed: the PI's approval of the text. The ChatGPT use stated by the authors is included; its historical model versions were not logged and are not inferred. Original question: Generative-AI disclosure. The MDPI template requires Materials and Methods to describe any generative-AI use for text, data, graphics, study design, analysis or interpretation, and the Acknowledgments to name the tool, version and purpose. Generative-AI assistance was used in this project; the PI decides and approves the disclosure text. | PI | before submission | Materials and Methods; Acknowledgments | `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md` item 12 |

---

## D-001 — Canonical, tool-independent documentation
Date: 2026-09-12
Status: Accepted
Context: Research rules must not depend on a particular AI tool or editor.
Decision: Research rules live only in `docs/` (`CONVENTIONS`, `RESEARCH_PROTOCOL`, `DATA_POLICY`,
`DECISIONS`, `EXPERIMENT_PROTOCOL`). `AGENTS.md` is a short entry point; `CLAUDE.md` is a thin adapter
pointing to `AGENTS.md`. No rules are duplicated in tool-specific files.
Evidence: —
Consequence: One source of truth; tool-specific files only link to `docs/`.

## D-002 — Data provider confirmation on use, release and consent
Date: 2026-09-12
Status: Accepted
Context: The repository is intended to be public and to support a public data release.
Decision:
- Data provider confirmed that raw data may be used and publicly released for research.
- Sensitive information had already been removed.
- Participant consent had been obtained.
- Public releases should still use anonymous subject IDs.
Evidence: Provider statement relayed by the PI on 2026-09-12.
Consequence: Release is permitted in principle. Note (added after inventory): `user01/metadata/*.xlsx`
still contains detailed demographic and health fields. It is classified `restricted_metadata` and
excluded from any release (DATA_POLICY §5, D-008). This does not contradict the provider's statement
but is handled conservatively.

## D-003 — User02 device mapping
Date: 2026-09-12
Status: Accepted
Context: User02's newer logs come from two physical mats, 22480 and 22482.
Decision: `subject_id = User02`, `device_id ∈ {22480, 22482}`. The two IDs are devices of one person,
never separate subjects.
Evidence: Confirmed by the data provider; also stated in the provider's package README.
Consequence: Enforced by `configs/subject_mapping.yaml` and `tests/test_subject_mapping.py`. How the
two concurrent streams are used remains open (OPEN-03).

## D-004 — Dataset roles
Date: 2026-09-12
Status: Accepted (as candidates; cohort not frozen). The User06 role is superseded by D-017 (`excluded_invalid`).
Context: Sources differ in firmware, timestamp policy and completeness.
Decision: Primary candidates = User01, User02 (new mat logs), User07; auxiliary = User02 legacy CSV,
User03 legacy, User06; restricted metadata = `user01/metadata`.
Evidence: Provided by the PI; legacy sources differ in timestamp policy and firmware.
Consequence: Candidates only; the frozen cohort is decided in P0 (OPEN-16).

## D-005 — Raw package left in place
Date: 2026-09-12
Status: Accepted
Context: The delivered raw folder is the source of truth.
Decision: The delivered package stays at `스마트 매트 데이터 정리/`; it was not moved or copied into
`data/raw/`. `configs/paths.yaml:raw_root` points to it; both locations are write-protected and
git-ignored.
Evidence: —
Consequence: The manifest stores paths relative to `raw_root`, so a later move changes one config line.
Relocation remains a PI decision (OPEN-05).

## D-006 — Prefix-mismatch files quarantined
Date: 2026-09-12
Status: Accepted
Context: Two files in the 22480 archive carry the `sm22482_` prefix.
Decision: `user02/mat_22480/_prefix_mismatch/*` get `device_id = unresolved`,
`dataset_role = quarantined`. Subject remains User02.
Evidence: Provider already isolated them; content evidence points to 22482 (inventory §8.1) but is not
confirmation.
Consequence: Excluded from all analyses until OPEN-02 is resolved. Silent reassignment is not allowed.

## D-007 — Audit-only parsing interpretations (non-binding for preprocessing)
Date: 2026-09-12
Status: Accepted (audit scope only); the year inference and line reading are adopted for canonical_v1 by D-026
Context: The inventory needed dated rows from several raw format families.
Decision: The P0 audit parser (`src/data/raw_parser.py`) reads files line by line (the JSON-like files
are not valid JSON), infers the year of `MM-DD` rows from the enclosing JSON log key, else the next key
in the file, else `year_hint` in `configs/subject_mapping.yaml` (User01 phase_b 2025, phase_c 2026,
User07 2026), and treats `.` between timestamp and P1 as a delimiter.
Evidence: inventory §5 and §8.3.
Consequence: Used only for inventory statistics. Preprocessing must adopt them explicitly (OPEN-08, OPEN-12).

## D-008 — Restricted metadata
Date: 2026-09-12
Status: Accepted
Context: `user01/metadata/meta_legacy_package.xlsx` and `meta_longitudinal.xlsx` contain demographic
and health information.
Decision: Both are `restricted_metadata`: not model input, not copied or summarised field-by-field
outside raw, not released. `*.xlsx` is git-ignored repository-wide.
Evidence: Inventory §9 (contents deliberately not reproduced).
Consequence: Only operational study-log facts may be used (pressure-sensor replacement 2026-01-25,
heating season start, log-format change, event-code legend).

## D-009 — Git initialised
Date: 2026-09-12
Status: Accepted
Context: `.gitignore` rules needed to be verifiable by tests.
Decision: `git init` was run. At the time of this entry no commit had been made.
Evidence: —
Consequence: The first commit (`1794418`, "Initial research repository setup") was later pushed to
`origin/main` on 2026-09-12 (see D-010).

## D-010 — Phased research lifecycle and Git workflow
Date: 2026-09-12
Status: Accepted
Context: The repository is public and serves as the companion record of an MDPI paper. Decisions about
data, splits and protocol must be traceable to the phase in which they were made, and results must be
linkable to the code and data that produced them.
Decision:
- The study follows nine fixed phases P0–P8 with exit criteria and freeze tags
  (`RESEARCH_PROTOCOL.md` §5).
- Git mechanics: one branch per phase created only after the previous phase is merged, PR per phase
  as research record (`.github/pull_request_template.md`), annotated freeze tags only at
  `p0-data-freeze`, `p2-protocol-freeze`, `p3-loso-baseline`, `p5-personalization`, `v1.0-paper`,
  single-line research-step commit messages without AI attribution (`CONVENTIONS.md` §6).
- Decision entries use the Date/Status/Context/Decision/Evidence/Consequence format. D-001–D-009 were
  converted to this format on 2026-09-12 without changing their content.
Evidence: PI instruction, 2026-09-12. First commit `1794418` on `main`.
Consequence: `main` holds only completed phases. No P1+ branch or tag exists until P0 is merged.

## D-011 — Track `data/raw/README.md`
Date: 2026-09-12
Status: Accepted
Context: The first commit excluded `data/raw/README.md` under a conservative "nothing under data/raw"
staging rule, so the public repository did not show where raw data belong or how they are protected.
Decision: `data/raw/README.md` is the only tracked file under `data/raw/`. It contains no raw filenames
or identifiers. All other paths under `data/raw/` stay git-ignored.
Evidence: `.gitignore` (`/data/raw/*`, `!/data/raw/README.md`); `tests/test_no_raw_modification.py`
(`test_no_raw_file_is_tracked`) allows exactly this file.
Consequence: Raw data remain local-only.

## D-012 — Start P0; no strict cohort before provenance issues are resolved
Date: 2026-09-12
Status: Accepted
Context: The inventory found identity and provenance conflicts (OPEN-01–OPEN-04), overlapping files,
sentinels/glitches, a sensor replacement and period/season confounding.
Decision: P0 (Dataset Audit & Data Freeze) starts on `research/p0-data-freeze` following
`docs/P0_DATASET_AUDIT_PLAN.md`. The strict cohort is not decided until the P0 blocking items are
resolved. During P0 no model training, window generation, resampling, interpolation, normalisation,
split generation, feature extraction or hyperparameter search is performed.
Evidence: `docs/initial_dataset_inventory.md` §7–§10.
Consequence: P0 ends with the cohort decision and the `p0-data-freeze` tag after merge into `main`.

## D-013 — User03 ≠ User06; provisional quarantine of their overlapping recording; provisional primary cohort
Date: 2026-09-12
Status: Superseded by D-017 (User03/User06 part; the provisional primary cohort is restated in D-017)
Context: P0-A1 found that 100 % of `user03_legacy` sensor rows (107,256, minute resolution) and 100 % of its
value sequences are contained in `user06_auxiliary` recordings of the nights 2025-10-06 → 10-13. The PI
relayed that User03 and User06 are different people.
Decision:
- User03 and User06 remain two distinct subjects (User03 ≠ User06). They are not merged.
- Whether the overlapping measurements are independent is unresolved. The overlap covers all of `user03_legacy`
  and the User06 nights 2025-10-06 → 10-13 that contain it.
- Until the provider clarifies the provenance, this overlapping recording is **provisionally quarantined**:
  it is not used in primary evaluation. Any other use (e.g. an auxiliary training pool) needs its own decision
  (OPEN-13). Neither subject is deleted or finally excluded. User06's non-overlapping recordings keep their
  auxiliary role.
- User01, User02 and User07 form the **provisional primary cohort**. P0 continues on that basis.
Evidence: `docs/P0_A1_PROVENANCE_REPORT.md` §4; `outputs/qa/p0/provenance/`; PI statement of 2026-09-12 that
User03 and User06 are different users.
Consequence: OPEN-01 is narrowed to measurement provenance. `configs/subject_mapping.yaml` is unchanged
(roles stay `auxiliary`); the quarantine will be encoded in the cohort definition when the cohort is frozen at
P0 exit. OPEN-16 (final cohort) stays open.

## D-014 — Remove repeated upload-chunk copies when building the canonical interim dataset
Date: 2026-09-12
Status: Accepted 2026-09-13 at P0 closure, unchanged; implemented in canonical_v1 (D-028)
Context: Adjacent raw files repeat upload chunks, and one chunk is repeated inside a file. A decision is needed
before the canonical interim dataset can be built (OPEN-07).
Decision (proposed):
- Within one subject + device group, keep one copy of each row that belongs to a repeated block: exact duplicates
  (timestamp, P1–P6, temp, humid, event) that occur in another file, and the 600-row block repeated inside
  `sm22482_0816`. Keep provenance of all copies (file, line) in the interim manifest.
- Do **not** remove or merge same-second rows with different values, adjacent identical same-second rows, or rows
  differing only in event text. These stay open.
- Never de-duplicate across devices or subjects.
Evidence: `docs/P0_A5_DUPLICATE_OVERLAP_REPORT.md`. Every primary-group file overlap is an exact duplicate block;
all 300 repeated chunk keys have identical content; 0 between-file value conflicts. Impact: 187,190 + 600 rows
(4.3 %) of 4,323,873 primary-group rows.
Consequence: If accepted, no information is lost (copies are identical). Same-second conflicts (10,997), their
alignment and resampling remain for P2. Minute-resolution legacy sources are out of scope of this proposal.

## D-015 — Candidate session boundary: gap > 30 min, with lost upload chunks bridged
Date: 2026-09-12
Status: Superseded by D-024 (bridge restricted to 22482 file boundaries)
Context: Sessions cannot be files or calendar days (A5, A7). A rule is needed to group each per-device timeline
into recording sessions without altering data. The rule must not depend on any model result; none exists yet.
Decision (proposed):
- Build sessions per subject + device on the de-duplicated timeline (D-014 view).
- A new session starts after a gap > 30 min.
- A gap of exactly 1–3 upload chunks (n × 1,800 s ± 10 s, n ≤ 3) is recorded as a missing interval inside the
  session, not as a break.
- Session membership is a label only. No timestamp, row or gap is changed.
- Within-session gaps (≈ 2-min pauses, 6–15 s sample losses, bridged missing chunks) must be handled explicitly
  by the windowing rule (P2).
Evidence: `docs/P0_A7_TEMPORAL_GAP_REPORT.md`.
- 5–90 min is a plateau for User01/22480/User07.
- The ≈ 2-min pauses rule out thresholds < 5 min.
- 13/13 chunk-aligned 22482 gaps sit at file cuts with recording continuing on both sides in most cases.
- Resulting sessions per night: 1.04 / 1.04 / 1.16 / 1.02.
- The exact value is insensitive within ±15 min (≤ 5 sessions change per timeline).
Consequence: If accepted, 22482 nights stay whole across export losses (58 instead of 71 sessions). Genuine
non-aligned interruptions > 30 min remain breaks. Isolated single-chunk recordings, the split grouping level
(session vs night) and windowing across within-session gaps stay open for P2.

## D-016 — Flag known target sentinel and glitch patterns as invalid targets (values kept)
Date: 2026-09-13
Status: Superseded by D-025 (glitch rule corrected: an out-of-band value is a glitch whatever the other channel reads)
Context: Temperature and humidity are the regression targets. A8 found a small set of values that cannot be
physical readings of an indoor sleeping microclimate, with clear, repeated patterns.
Decision (proposed):
- In the canonical interim dataset, mark the target as invalid, per channel, with a cause-preserving state:
  - the joint zero pattern T = 0 and H = 0 (`target_zero_sentinel`), in both channels;
  - values outside the candidate plausibility band (T < −10 or > 60 °C; H > 100 %RH), together with a zero in the
    other channel of the same row (`target_extreme_glitch`). Currently only the 22482 night 2026-08-08/09.
- Raw values are never replaced, clipped, interpolated or deleted. Rows keep their provenance and their
  pressure data.
- Also stored as context, not as validity: zero-run class (start sentinel / dropout run), chunk position,
  |Δ| to the previous valid value with its Δt, constant-run length, and same-second group id
  (`quality_flag_schema.csv`).
Evidence: `docs/P0_A8_TARGET_QUALITY_REPORT.md` §3–§7.
- 4,132 rows (0.10 %) of the primary groups; no other value lies outside the band.
- The patterns are exact and repeated.
- Their neighbours show normal readings.
Consequence: If accepted, models and metrics exclude flagged targets in a traceable way.
Not covered by this proposal:
- excluding whole dropout/glitch episodes;
- jump or outlier thresholds;
- treatment of the ±1 same-second pairs;
- interpolation, clipping or smoothing (P2).
The candidate band is a descriptive parameter and must not be tightened after model results are seen.

## D-017 — User06 source excluded as invalid (provider-confirmed); User03 kept as auxiliary
Date: 2026-09-13
Status: Accepted (supersedes D-013); the cohort statement is finalised by D-020
Context: A1 showed that `user03_legacy` is, row for row, a contiguous excerpt of the `user06_auxiliary`
recordings (100 % of User03 rows at minute resolution and of its value sequences). D-013 kept User03 ≠ User06
and provisionally quarantined the overlapping recording. The data provider has since confirmed that the User06
data are wrong because of a setting problem at the time, and that the User06 source should be left out.
Decision:
- User03 and User06 remain two distinct subjects. They are not merged.
- The current `user06_auxiliary` source is classified `excluded_invalid` (`quality_status: invalid`,
  `exclusion_reason: provider_confirmed_setting_issue`, `configs/subject_mapping.yaml`).
- The User06 source is excluded from every downstream analysis, from model training and evaluation, and from
  any canonical or public analysis dataset. Excluded sources are listed, with reason and decision ID, in the
  future release manifest (P7).
- The raw archive is **not** modified or deleted. Analytical exclusion, never physical deletion.
- `user03_legacy` keeps its `auxiliary` role, with its existing limitations (minute resolution; auxiliary use needs
  its own decision, OPEN-13).
- Historical audit results (inventory, A1–A8) are not rewritten. They document the data as delivered. Analyses
  from A9 onward apply this exclusion.
Evidence: `docs/P0_A1_PROVENANCE_REPORT.md` §4; provider confirmation relayed by the PI on 2026-09-13.
Consequence:
- Provisional primary cohort unchanged: User01, User02, User07.
- User03 legacy: auxiliary. User06 current source: `excluded_invalid`. User06 has no valid source (cohort
  `no_valid_source`).
- OPEN-01 is closed.
- The committed raw manifest now carries `dataset_role = excluded_invalid` for the 11 User06 files; only those
  11 cells changed, checksums are unchanged. Re-running historical audit scripts reproduces their numbers; only
  role labels of User06 rows differ. Verified on 2026-09-13 by re-running A1, A2, A5, A7 and A8 against saved
  outputs: every value is identical except 27 role cells in A1 `cross_subject_provenance_by_source.csv` and 1 in
  A5 `duplicate_summary.csv` (User06 `auxiliary` → `excluded_invalid`).
- Caveat for any future use of User03 legacy: its rows are the same measurements as part of the invalid User06
  recording. D-017 attributes them to User03, but the provider has not said whether the setting problem also
  affects them. This must be addressed before User03 legacy is used (OPEN-13).
  **Resolved by D-021:** the PI confirmed that User03 legacy is valid User03 data; only the User06 source is
  invalid.

## D-018 — Pressure input-validity rule: raw layout and encoding only (values kept)
Date: 2026-09-13
Status: Accepted 2026-09-13 at P0 closure, unchanged; implemented in canonical_v1 (D-028)
Context: P1–P6 are the model inputs. A9 checked channel presence, layout, encoding, zeros, the 4095 ceiling,
constant runs and scale on the analysis-eligible sources.
Decision (proposed):
- In the canonical interim dataset, a row's pressure input is **invalid** only if:
  - the raw line layout is not a recognised six-channel layout (`pressure_schema = nonstandard`), or fewer
    than six channels are present (`pressure_channels_present < 6`); absent channels are never filled with 0;
  - or any channel is < 0, > 4095 or non-integer (`pressure_impossible_encoding`).
- 4095 is kept as a value and flagged with the number of channels at 4095. It is not treated as missing,
  capped or excluded.
- All-zero frames, constant-run length, same-second group and the provider period label (e.g. User01 before/after
  2026-01-25) are stored as context columns. They are not validity flags.
- Raw values are never replaced, clipped, normalised, imputed or deleted. Channels are not removed.
Evidence: `docs/P0_A9_PRESSURE_QUALITY_REPORT.md` §2, §6–§8.
- The rule changes 0 rows of the current data (policies A and B). It guards the canonical builder against layout
  and encoding errors.
- A stuck heuristic (policy C) would flag 7,129 User01 rows. All of them are 4095 plateaus of the old sensor,
  not frozen hardware, so a heuristic is not proposed.
Consequence: If accepted, pressure validity is decided by raw evidence only. Not covered by this proposal (P2,
fitted on training data only where applicable):
- saturation handling;
- scaling/normalisation (OPEN-17);
- the User01 sensor-change boundary (OPEN-11);
- the 22482 P1 shift (OPEN-19);
- channel selection or spatial features (OPEN-20).

## D-019 — User01 `sensor_phase` provenance label (boundary 2026-01-25)
Date: 2026-09-13
Status: Accepted (provenance label only; handling open, OPEN-11). canonical_v1 labels timelines without a documented sensor change `not_applicable` instead of `s1` (D-028)
Context: The provider documents a pressure-sensor replacement for User01 on 2026-01-25. A10 tested this boundary
against the data without assuming it (`docs/P0_A10_USER01_SENSOR_PHASE_REPORT.md`).
Decision:
- The canonical interim dataset carries a provenance column `sensor_phase`.
- For User01:
  - `s1` = rows up to 2026-01-25 08:07:26, the last row before the recording gap;
  - `s2` = rows from 2026-01-25 17:31:21, the first row after it.
  - No row lies in between.
- All other subject/device timelines are `s1` (no documented sensor change). Changing that needs its own decision
  (e.g. OPEN-19).
- The label changes no value. It implies no normalisation, clipping, rescaling, exclusion or phase-specific model.
- The boundary is fixed now, before any model exists. It must not be moved in response to model results.
- `s1/s2` are distinct from the provider's `phase_a/b/c` source folders. `s1` spans phase_a, phase_b and phase_c
  up to the gap.
Evidence: A10 §2–§8.
- The boundary is a single recording gap on the documented date. The file after it is the provider's
  "sensor changed" file.
- It is the strongest change point of the User01 series. The core consensus ranks it first for nights and
  sessions at w = 3 and 7, with a large margin.
- Nights ±14: the 4095 share, pressure-sum p95 and active channels are completely separated (Cliff's δ = ±1).
  Placebo windows show no separation.
- It is a step rather than a drift (one-step R² 0.79–0.99 vs line 0.59–0.76).
- 4095 disappears immediately: 22.1 % of rows before, 18 isolated cells after, the first 50 h later.
- Duration, clock time, temperature, humidity, sampling and a scale-free movement proxy are continuous across the
  gap.
Consequence:
- Later phases can report, stratify or constrain by `sensor_phase` without redefining it.
- Decided in P2 (OPEN-11, OPEN-17):
  - phase-aware preprocessing or scaling;
  - whether User01 adaptation/test spans may cross the boundary;
  - per-phase reporting in LOSO.
- Other acquisition changes inside `s1` (2025-12-17 log-format/activity change, the early-January sampling
  episode) are not part of this label (OPEN-21).

## D-020 — Canonical P0 primary cohort: User01, User02, User07
Date: 2026-09-13
Status: Accepted (cohort membership; closes OPEN-16)
Context: D-013/D-017 set a provisional primary cohort. A11 checked, without any model, whether each candidate
supports strict LOSO and chronological personalization, and how subject identity is confounded with time, season
and device (`docs/P0_A11_COVERAGE_CONFOUNDING_REPORT.md`).
Decision:
- Primary cohort: **User01, User02, User07**. Subject-level evaluation keeps User02's two mats (22480, 22482)
  together as one subject.
- Auxiliary pool: User02 legacy and User03 legacy. Their use is still open (OPEN-13).
- User06: `excluded_invalid` (D-017). The two prefix-mismatch files stay quarantined (D-006, OPEN-02).
- No subject is added or removed on the basis of model results. The cohort is fixed for P1–P6 unless new
  provenance evidence forces a new decision.
- Not decided here:
  - which mat or mats of User02 feed a model (OPEN-03, P2);
  - how User01's sensor phases are handled (OPEN-11, P2);
  - how the 22482 anomaly is flagged (OPEN-19);
  - use of auxiliary data (OPEN-13).
Evidence: A11 §1–§5.
- All three pass every structural check:
  - volume: 1,784 / 576 / 833 active hours; 151 / 51 / 100 nights;
  - T/H coverage ≥ 99.8 %;
  - 0 shared recording hours between any two, and no shared rows (A1);
  - enough nights for chronological adaptation/test spans, also per User01 phase and for User02 without the
    22482 anomaly slice.
- All three are `eligible_with_caveat`; none is `not_eligible`.
Consequence:
- Three LOSO folds. Each fold also removes a calendar period, a season mix and a device/firmware configuration,
  because no two primary subjects were recorded at the same time.
- Claims are limited accordingly (A11 §6): unseen subject-period-device generalisation, not population
  generalisation or an isolated user effect.
- The statistical plan (P2) must reflect n = 3.
- A9b (2026-09-13) confirmed that the 22482 P1 anomaly does not change User02's eligibility (D-022).
- `configs/subject_mapping.yaml` keeps the role label `primary_candidate` for now. Relabelling (and the
  role-cells-only manifest rebuild it implies, as for D-017) is done with the interim dataset build, so historical
  audit outputs are not relabelled piecemeal.

## D-021 — User03 legacy is valid auxiliary data
Date: 2026-09-13
Status: Accepted (resolves the User03 caveat of D-017)
Context: D-017 excluded the User06 source as provider-confirmed invalid and kept `user03_legacy` as auxiliary. It
left open whether the setting problem also affects the User03 legacy measurements, which A1 found inside the
User06 recording.
Decision:
- `user03_legacy` is valid User03 data (PI statement, 2026-09-13). It stays `auxiliary` with
  `quality_status: ok`.
- Only the User06 source is `excluded_invalid`. User03 and User06 remain distinct subjects.
- Whether and how auxiliary sources are used is still OPEN-13.
Evidence: PI statement relayed on 2026-09-13; A1 (provenance) and A9 (auxiliary pressure quality) remain the
descriptive record.
Consequence: No configuration change (User03 legacy was already `auxiliary`/`ok`). Documents no longer describe
User03 legacy as unresolved or possibly invalid.

## D-022 — 22482 channel-quality phase: P1 response shift from 2026-08-20 (flag, values kept)
Date: 2026-09-13
Status: Accepted (provenance label only; closes OPEN-19 as class B, non-blocking but flagged)
Context: A9 saw 22482's P1 nearly stop responding around 2026-08-20. A9b tested this without assuming the date
(`docs/P0_A9B_USER02_CHANNEL_ANOMALY_REPORT.md`).
Decision:
- The canonical interim dataset carries two provenance columns per row:
  - `channel_quality_phase`: for device 22482,
    - `normal` up to 2026-08-19 08:56:10;
    - `p1_transition` for the recording 2026-08-19 19:58:23 → 2026-08-20 09:58:32, in which the onset occurs
      (hourly best split ≈ 2026-08-20 02:00);
    - `p1_response_shift` from 2026-08-20 21:37:33 to the end of the recording.
  - `channel_quality_flag`: the affected channels (`p1`), or empty.
- Every other device or timeline is `normal`. Boundaries are recording gaps, configured in
  `configs/subject_mapping.yaml` (`channel_quality_phases`). No row lies inside a gap.
- Raw values are kept. Nothing is removed, corrected, imputed, clipped, normalised or dropped as a channel.
- The boundaries are fixed now from data evidence and must not be moved after model results are seen.
Evidence: A9b.
- The strongest P1 change point is the first fully shifted night 2026-08-20 for nights and sessions at w = 3.
  At w = 7 it is the transition night 2026-08-19.
- P1 (±7 nights), with complete separation (Cliff's δ = −1):
  - active share 0.51 → 0.14;
  - median when active 741 → 26;
  - p95 1,350 → 63;
  - share of the pressure sum 16.9 % → 0.6 %.
- It is a step rather than a drift (R² 0.83 vs 0.60), and it persists to the last night.
- Other channels |δ| ≤ 0.51. The pressure sum without P1 is stable (1,780 → 1,718, δ −0.14). The fall of the
  total sum is P1's missing contribution.
- There is no concurrent shift in 22480 or in T/H.
- No schema, container, sampling or control-token change is nearby. The device_id column appears 11 days later.
Consequence:
- The flag affects 16,804 rows / 14.0 h (transition) and 229,805 rows / 192.0 h in 21 nights (shift): 38.7 % of
  22482 and 33.3 % of User02 hours.
- Even without the shifted slice, User02 keeps 447.7 h in 45 nights and meets every A11 criterion. The cohort
  (D-020) is unaffected.
- User02's last six days (2026-09-05 → 09-11) exist only on 22482 in the shifted phase. This matters for late
  test spans.
- Decided in P2:
  - using, masking or modelling P1 of 22482 in the shifted phase;
  - device selection (OPEN-03).
- The later P6 decline of 22482 (2026-08-25) is not part of this flag (OPEN-03).

## D-023 — Canonical cohort, dataset roles and auxiliary policy (P0 closure)
Date: 2026-09-13
Status: Accepted (closes OPEN-13; closes the P0 part of OPEN-02)
Context: P0 closes with a canonical interim dataset. Cohort membership was fixed by D-020, User03 legacy was
confirmed valid by D-021, and the User06 source is invalid (D-017). How each source enters canonical_v1 must now
be fixed.
Decision:
- **Primary** (`data/interim/canonical_v1/primary.parquet`): User01 (phase_a/b/c), User02 mats 22480 and 22482,
  User07. These are the only rows for primary LOSO, primary personalization and primary metric aggregation.
- **Auxiliary** (`auxiliary.parquet`, kept apart): User02 legacy and User03 legacy. Both are valid data. They are
  not used in primary LOSO, personalization or metric aggregation. Minute resolution and the legacy CSV schema
  mean they are never mixed with primary rows. Secondary or sensitivity use needs its own protocol.
- **Excluded** (`excluded_invalid`): the User06 source. It is not in canonical_v1. Raw files are kept.
- **Quarantined**: the two prefix-mismatch files. They are not in canonical_v1. Attribution (22482 is strongly
  indicated) stays a non-blocking provider question.
- **Restricted metadata**: not data, not loaded.
- For excluded and quarantined sensor files, the build counts parsed rows only, to reconcile against every
  delivered row. No value is kept.
Evidence: D-017, D-020, D-021; A1, A2, A5, A9 (auxiliary quality), A11 (coverage).
Consequence:
- canonical_v1 primary has 4,136,059 rows; auxiliary has 178,626 rows.
- Excluded: 164,185 raw rows (11 files). Quarantined: 22,205 raw rows (2 files).
- Any future admission of an excluded or quarantined source is a new dataset version.

## D-024 — Session policy (supersedes D-015)
Date: 2026-09-13
Status: Accepted (closes OPEN-06)
Context: D-015 proposed sessions split at gaps > 30 min, with lost upload chunks bridged. A7 found the chunk-loss
pattern only on 22482, at file cuts (13/13).
Decision:
- Sessions are built per subject + device stream on the de-duplicated timeline (D-014). A new session starts after
  a gap > 1,800 s.
- Exception: a gap of n × 1,800 s ± 10 s (n = 1–3) is kept inside the session only if both hold:
  - the stream is 22482;
  - the gap lies at a raw file boundary (the A7 missing-upload-chunk pattern).
- Every bridged gap is flagged on the first row after it (`session_bridged_gap`). Every row carries
  `gap_before_s`.
- Session membership is a label. It does not allow a window to span a gap. Window continuity is decided in P2.
- Legacy minute-resolution streams use the same gap rule without the exception.
- Parameters are in `configs/canonical_v1.yaml`.
Evidence: A7 §3–§5.
- The 5–90 min plateau and the ≈ 2-min pauses (A7).
- 13 bridged gaps, all on 22482.
- Session counts are unchanged from the A7/A9 candidate rule: User01 157, 22480 47, 22482 58, User07 102.
Consequence: `session_id` = "<subject>|<device>|S<nnnn>" in canonical_v1. Splits that group by session use these
labels.

## D-025 — Target quality flags (supersedes D-016)
Date: 2026-09-13
Status: Accepted (closes OPEN-09)
Context: D-016 proposed flagging joint zeros and glitches. Its glitch clause required a zero in the other channel.
A8 shows out-of-band values without such a zero (e.g. T 256 / H 152), so the clause is corrected.
Decision:
- Per row, `target_temp_valid` and `target_humidity_valid` are false for a missing value, a value of 0, or a value
  outside the plausibility band (T −10…60 °C, H 0…100 %RH).
- `target_quality_flag` records the cause, in priority order:
  - `missing`;
  - `extreme_glitch`: any out-of-band value, whatever the other channel reads;
  - `zero_sentinel`: T = 0 and H = 0;
  - `zero_value`: exactly one channel is 0;
  - `ok`.
- Values are never replaced, interpolated, smoothed or clipped. Rows are not deleted. Same-second ±1 target
  observations stay separate rows (`same_timestamp_group_id`).
- Not stored as columns, because they are derivable in P2: the zero-run class and |Δ| to the previous valid value.
  Chunk position (`chunk_key`), gaps (`gap_before_s`) and same-second groups are stored.
- The band is descriptive and must not be tightened after model results are seen.
Evidence: A8 §3–§7.
- 4,132 invalid-target rows in the primary rows (0.10 %): 3,985 zero sentinels and 147 extreme glitches.
- These equal A8's counts.
Consequence: Models and metrics can exclude flagged targets traceably. Episode exclusion and outlier rules are P2
decisions.

## D-026 — Timestamp policy (closes OPEN-08)
Date: 2026-09-13
Status: Accepted
Context: Raw timestamps come in three formats. Some lack the year, legacy exports lack seconds, and no timezone is
recorded anywhere.
Decision:
- `timestamp_raw` keeps the original string. `timestamp` holds the parsed naive local time (Parquet
  `timestamp[s]`, no timezone).
- `timestamp_resolution` is `second` or `minute`. Minute-resolution legacy rows keep minute resolution; no second
  is invented, and the parsed value's seconds field is 0 by construction.
- `timezone_status` = `local_unspecified`. Nothing is converted to UTC or any other zone.
- The year of `MM-DD` rows is inferred only from deterministic source context, recorded in
  `timestamp_year_source`:
  - the enclosing JSON log key (`json_key`);
  - else the next key in the same file (`json_key_lookahead`);
  - else the source's collection year from `configs/subject_mapping.yaml` (`config_hint`). This covers the User01
    phase_b/c plain files, whose year is fixed by the provider's collection period.
  - New-year boundaries are resolved against the anchor.
  This adopts D-007 for canonical use.
- Rows without a determinable timestamp are never guessed. The build fails if any exist; there are none.
- Out-of-order raw steps are kept as they are. Rows are ordered by timestamp, with raw file/line order inside a
  second. `source_file`/`source_row` preserve the raw order.
Evidence: inventory §5; A5; A7; the canonical_v1 build.
- 603,174 `config_hint` rows, 3,476,641 `json_key` rows and 56,244 explicit rows in primary.
- 0 undated rows.
- 1 out-of-order raw step (22482).
Consequence: Relative-time conversion for release is a P7 question (OPEN-18). Any timezone assumption would be a
new dataset version.

## D-027 — User02 dual-device canonical representation (closes the P0 part of OPEN-03)
Date: 2026-09-13
Status: Accepted
Context: 22480 and 22482 are two mats of one subject, recording concurrently but uncoupled. A2 found no pressure
coupling, chance-level occupancy agreement and a persistent T/H offset.
Decision:
- In canonical_v1, User02's rows keep `subject_id = User02` and `device_id = 22480 | 22482`, as two separate
  device streams with separate sessions, de-duplication and phases.
- Forbidden in P0:
  - a 12-channel merge;
  - row-level fusion or alignment of the two mats;
  - dropping or preferring one mat.
- For every subject-level purpose (LOSO folds, leakage checks, counts), both mats are User02 (DATA_POLICY §3).
- Which mat or mats feed a model, and how, is decided in P2.
Evidence: A1, A2, A9b, A11.
Consequence: No canonical row mixes the two mats (tested). The 22482 channel-quality flag (D-022) applies to 22482
rows only.

## D-028 — Canonical interim dataset v1: schema, build and reproducibility (P0 closure)
Date: 2026-09-13
Status: Accepted
Context: P0's exit criterion is a canonical interim dataset built from accepted rules, with provenance and a
manifest.
Decision:
- **Build.** `scripts/build_canonical_v1.py` with `src/data/canonical.py` and `configs/canonical_v1.yaml`.
  - Parquet via pyarrow 24.0.0 (typed columns, dictionary-encoded labels).
  - Output under `data/interim/canonical_v1/` (git-ignored): `primary.parquet`, `auxiliary.parquet`,
    `duplicate_provenance.parquet`.
- **Contents.** canonical_v1 is parsed, provenance-preserving, exact-copy-deduplicated (D-014), quality-flagged
  (D-018, D-022, D-025) and session-labelled (D-024) rows, nothing more. No resampling, interpolation,
  normalisation, scaling, windowing, splitting, smoothing, clipping, device fusion or feature extraction.
- **Row schema (46 columns):**
  - identity: `canonical_row_id` (= raw file_id:line), `dataset_role`, `subject_id`, `source_id`, `device_id`;
  - time: `timestamp_raw`, `timestamp`, `timestamp_resolution`, `timestamp_format`, `timestamp_year_source`,
    `timezone_status`;
  - phases: `sensor_phase` (User01 `s1`/`s2`; `not_applicable` elsewhere), `channel_quality_phase` /
    `channel_quality_flag` (22482 `normal` / `p1_transition` / `p1_response_shift`; flag `p1` or `none`);
  - values: `P1`–`P6`, `temperature`, `humidity` (raw integers; null where absent, never filled);
  - targets: `target_temp_valid`, `target_humidity_valid`, `target_quality_flag`;
  - pressure: `pressure_schema`, `pressure_valid`, `pressure_upper_bound_channels`, `pressure_all_zero`,
    `pressure_frame_constant_run_s`, `pressure_quality_flag`;
  - events: `event_raw` (digit runs of ≥ 8 masked), `event_redacted`, `log_container`;
  - sessions: `session_id`, `gap_before_s`, `session_bridged_gap`;
  - provenance: `source_file`, `source_file_id`, `source_row`, `chunk_key`;
  - same-second groups: `same_timestamp_group_id`, `same_timestamp_group_size`, `within_timestamp_order`;
  - de-duplication: `duplicate_group_id`, `duplicate_count`.
- **De-duplication provenance.** Every raw occurrence of a de-duplicated row (kept and removed) is listed with its
  file, line and occurrence order in `duplicate_provenance.parquet`.
- **Reconciliation.** The build fails, writing nothing, unless all of these hold:
  - per stream, and per source × phase slice, raw − copies = canonical;
  - every raw sensor file is accounted for once;
  - no excluded or quarantined source appears in the output;
  - roles match the file;
  - row IDs are unique;
  - every removed copy is in the provenance table;
  - in total, raw − excluded − quarantined − auxiliary − primary copies = primary canonical.
- **Manifests** (committed; no absolute paths or personal identifiers), in `data/interim/manifest/`:
  - `canonical_v1_manifest.csv`, per source × phase slice;
  - `canonical_v1_summary.csv`, per stream and in total;
  - `canonical_v1_file_manifest.csv`, per raw file;
  - `canonical_v1_content.json`: deterministic dataset/schema version, config hash, raw-manifest hash,
    content hashes and reconciliation;
  - `canonical_v1_build.json`: runtime metadata (build time, HEAD at build time, dirty flag, versions, file
    hashes).
- `sensor_phase` uses `not_applicable` for timelines without a documented sensor change (refines D-019's `s1`
  default for the canonical schema). Historical audit outputs keep their labels.
- Changing any rule or parameter creates canonical_v2. canonical_v1 is never edited in place.
Evidence: the canonical_v1 build of 2026-09-13; `tests/test_canonical.py`.
- 4,688,889 raw sensor rows − 164,185 excluded − 22,205 quarantined − 178,626 auxiliary − 187,814 primary copies
  = 4,136,059 primary rows.
- Two consecutive builds produced identical content hashes, Parquet bytes and manifests.
Consequence: P1 (EDA) and P2 (protocol) read canonical_v1 only, never raw. Splits, windows and preprocessing are
P2.

## D-029 — Protocol v1.0: data source, cohort use and change policy (P2)
Date: 2026-09-13
Status: Accepted
Context: P2 fixes the evaluation protocol before any model result exists (RESEARCH_PROTOCOL §5). Cohort membership
(D-020), dataset roles (D-023) and canonical_v1 (D-028) are frozen. This entry fixes how they enter the protocol.
Decision:
- Protocol v1.0 = `docs/EXPERIMENT_PROTOCOL.md` + `configs/experiments/v1.0/protocol.yaml`, with decisions
  D-029–D-042.
- **Data.** canonical_v1 `primary.parquet` only: User01, User02 (mats 22480 and 22482), User07. It is read through
  `src/evaluation/canonical_input.py`, which verifies the file hashes and refuses raw paths.
- **Auxiliary** sources (User02 legacy, User03 legacy) are not read by protocol v1.0. They are in no training pool,
  validation set or test set. No secondary auxiliary protocol is defined.
- The User06 source (`excluded_invalid`) and the two quarantined files are not in canonical_v1 and appear in no split.
- No subject, device, session, night or phase is removed from any partition. Quality flags stay provenance.
- **Change policy.** Any change to a v1.0 item is a new decision plus a new protocol version (v1.1, …). Results
  under both versions are reported (RESEARCH_PROTOCOL §6). The frozen state is tagged `p2-protocol-freeze` on `main`
  after the P2 merge.
Evidence: D-017, D-020, D-023, D-028; RESEARCH_PROTOCOL §3–§6.
Consequence:
- Three primary subjects give three LOSO folds.
- Every fold also holds out a collection period, a season mix and a device/sensor configuration (A11 §5; P1 §6–§7).
  The RQ1 claim is "an unseen subject under the observed combined domain shift", not a pure biological subject
  effect.

## D-030 — Night and session grouping for splits
Date: 2026-09-13
Status: Accepted
Context: Splits need an atomic time unit. Sessions (D-024) are defined per device stream. The RQ2 unit must also keep
the two concurrent User02 mats together (L8).
Decision:
- `night_id` = the calendar date of (timestamp − 12 h), on the naive local time of canonical_v1
  (`local_unspecified`, D-026). Nights run noon to noon. No timezone conversion. This is the P1 night definition
  (night index (ts − 43,200) // 86,400).
- A **subject-night** holds all primary rows of one subject, on all its devices, with the same `night_id`.
  - It is the RQ2 atomic unit (D-037).
  - It is the within-subject statistical unit (D-041).
- Split records:
  - RQ1 records are sessions (D-024).
  - RQ2 records are session × night pieces: a session that crosses noon is cut at the night boundary.
- Every recorded subject-night counts. There is no minimum duration.
Evidence: structural counts from canonical_v1.
- Nights: 151 / 51 / 100 (User01 / User02 / User07).
- Sessions: 157 / 105 / 102.
- The shortest subject-night has 2.0 h and 2,400 rows.
- Every session lies in one sensor phase and one channel-quality phase. The D-019 and D-022 boundaries fall between
  nights.
- 3 sessions cross noon, giving 367 session × night pieces.
Consequence: No split unit ever separates the two User02 mats within a night.

## D-031 — RQ1 strict LOSO outer folds and nested subject-level validation
Date: 2026-09-13
Status: Accepted
Context: RQ1 needs strict leave-one-subject-out over three subjects (L4, L6, L8). Only two subjects remain for
model selection in each fold.
Decision:
- **Outer folds:**
  - fold 1: test User01, training pool User02 + User07;
  - fold 2: test User02, training pool User01 + User07;
  - fold 3: test User07, training pool User01 + User02.
- Every source, device, session and phase of the held-out subject is test. User02's two mats are always on the same
  side. There is no device-level LOSO and no auxiliary data.
- **Inner validation** (subject level). For each fold, the two training subjects form two inner splits:
  - A: train on the first remaining subject in cohort order, validate on the second;
  - B: the same with the roles swapped.
  The held-out subject appears in no inner record.
- Model and hyperparameter selection use the inner validation only (D-040). The outer test is evaluated once per
  protocol version, with the configuration frozen before it.
- Files: `data/splits/v1.0_loso/outer_folds.csv` and `inner_folds.csv` (D-042).
Evidence: L4, L6, L8; D-020 (n = 3); DATA_POLICY §3 (User02 is one subject).
Consequence:
- The inner validation estimates transfer between only two subjects, so it is a noisy selection signal. This is
  accepted: the only alternative that yields more validation data would use the held-out subject.

## D-032 — Windowing: 40 s time-binned windows of observed rows
Date: 2026-09-13
Status: Accepted
Context:
- Primary sampling is irregular: 99.4 % of inter-row gaps are ≤ 5 s (3 s nominal, p99 5 s; A7). 0.3 % are
  same-second rows and 0.6 % exceed 5 s.
- 22,498 rows share a second with another row.
- A TCN needs a fixed input shape.
- Three representations were compared on structure only: A (1-s grid), B (fixed row count), C (time bins).
- The prior study used 20/30/40 s windows. 40 s is used as the comparison anchor, not because of its results.
Decision:
- **Continuity.** Rows of one group, with every inter-row gap ≤ 5 s, form a continuity segment. The group is:
  subject, device, session, `sensor_phase`, `channel_quality_phase` and split partition, plus `night_id` for RQ2.
  - A window never contains a gap > 5 s and never crosses a group boundary.
  - The 22482 bridged upload gaps (D-024) are never spanned.
- **Window.**
  - Span: [t0, t0 + 40 s), cut into 8 bins of 5 s, with stride 20 s (50 % overlap).
  - Starts: t0 = segment start + k · 20 s. A window exists only if t0 + 35 s ≤ the segment's last timestamp. Then
    every bin holds a row, so there are no incomplete windows.
  - Step value: the last observed row in each bin. A tie within one second takes the last row in canonical order
    (`within_timestamp_order`).
  - Pressure is never interpolated, resampled to invented values, averaged, padded or filled. Sampling
    irregularity is absorbed by the 5-s bins.
- **Target.** Temperature and humidity of the row used at the last step (window end): past/current pressure →
  current T/H. There is no forecasting, and no later row is used.
- **Sensitivity windows** (P6 only), same rule:
  - 20 s: 4 steps, stride 10 s;
  - 30 s: 6 steps, stride 15 s.
Evidence: structural audit (`scripts/audit_p2_window_feasibility.py`; P2 report §5). No model, loss or error was
computed.
- A: 64–67 % of the 1-s cells are empty in every slice, so it needs fill or mask values. Rejected.
- B (14 consecutive rows): elapsed time p05–p95 is 26–41 s on User01/s1 (the 2-s sampling episode, OPEN-21) against
  37–41 s elsewhere. The time scale would differ by domain. Rejected.
- C:
  - the first-to-last-step span is 33–37 s in every slice;
  - windows keep 97.7–99.9 % of the gap-free recording time;
  - ≥ 99.6 % of windows carry a label.
- Most of the > 5 s loss is missing time itself. User01/s1 has 13,975 such gaps, so its gap-free time is 89.9 % of
  its session time, against 96.5–99.2 % elsewhere. Segments too short for a window hold 2.3 % of its gap-free time
  (≤ 0.4 % elsewhere).
Consequence: 574,849 windows at 40 s: User01 289,672, User02 144,205, User07 140,972. The rule is implemented in
`src/evaluation/windowing.py` and every window is validated there.

## D-033 — Pressure scaling and 4095 handling (closes OPEN-17)
Date: 2026-09-13
Status: Accepted
Context: Pressure scales differ between domains:
- User01/s1 has a loaded pressure-sum median 1.5–2.9× that of the other slices (P1 §4);
- a 4095 channel appears in 22.1 % of its rows (A9, D-019).
L3/L11 forbid statistics from test data.
Decision:
- **Scaling.** P_scaled = P / 4095 for every channel: the fixed 12-bit physical range. There is no fitted input
  scaler: not per subject, device, phase or full dataset, and never with test-subject statistics. Derived features
  (D-039) are fixed formulas of the scaled values.
- **4095** stays as observed (it becomes 1.0). It is never deleted, clipped, interpolated or masked, and its rows are
  excluded from no partition, test included.
- Any fitted input transform added later must be fitted on the outer or inner training partition only, with fit
  provenance checked by the leakage gate.
- 4095 sensitivity analyses belong to P6 and do not change P3–P5.
Evidence: A9/OPEN-17; P1 §4, §6. Methodological rationale:
- The scale shift is part of the deployment domain shift that RQ1 measures.
- Statistics fitted on two training subjects would not remove it for the held-out subject. They would only make the
  input representation depend on the fold.
- Test-subject statistics are forbidden (L11).
- A fixed physical-range scale is identical in every fold and needs no fit.
Consequence: RQ1 results include User01's sensor-scale shift. It is made visible by phase-stratified reporting
(D-041), not removed.

## D-034 — Targets: joint temperature/humidity at the window end, validity and normalisation
Date: 2026-09-13
Status: Accepted
Context: D-025 flags invalid targets (0.10 % of rows) and keeps their values. P2 decides how labels are formed.
Decision:
- One model predicts temperature (°C) and humidity (%RH) jointly.
- A window is a labelled sample only if `target_temp_valid` and `target_humidity_valid` are both true at its target
  row. Otherwise the window is not used for training, validation, adaptation, early stopping or metrics.
- Targets are never interpolated, clipped, corrected or replaced. Rows with invalid targets remain input rows (targets
  are never inputs).
- There is no episode-level exclusion or outlier rule beyond the D-025 flags.
- **Normalisation.** Each target is z-scored with the mean and standard deviation of the labelled windows of the
  training partition of that fit:
  - the outer training pool for final models;
  - `inner_train` for inner models;
  - for personalization, the base model's statistics, never refitted.
- Metrics are computed after the inverse transform, in °C and %RH.
Evidence:
- D-025.
- Structural audit: ≥ 99.6 % of windows are labelled in every slice (lowest: 22482/normal, 99.60 %).
- Requiring both targets valid is the simplest joint rule, and it costs ≤ 0.4 % of windows in any slice.
Consequence: Target statistics never come from a test subject, a test night or adaptation data (checked through
`TargetScaler.fit_provenance`, L3/L11).

## D-035 — Sensor-phase and channel-quality-phase handling (P2 parts of OPEN-11 and OPEN-19)
Date: 2026-09-13
Status: Accepted
Context:
- User01 changes sensor between `s1` and `s2` (D-019).
- 22482 has a P1 response shift (D-022).
- P1 found that s1 ↔ s2 shifts pressure as much as a between-subject shift (W1/IQR 0.87), and that the 22482 shift
  changes pressure but barely the targets.
Decision:
- `sensor_phase` and `channel_quality_phase` are never model inputs. They serve window boundaries, provenance,
  stratified reporting and robustness interpretation.
- No phase is excluded, masked, re-weighted, or given its own scaler or model, in any partition (train, validation,
  adaptation, test).
- Channel P1 of 22482 in `p1_transition` and `p1_response_shift` is used as recorded.
- Chronological spans may cross phase boundaries (D-037).
- Boundaries are not moved, and no phase is dropped, after results are seen.
- The other User01 acquisition changes inside `s1` (OPEN-21) are not boundaries in v1.0. This is non-blocking.
Evidence: D-019, D-022; P1 §4–§6. Rationale:
- Removing a phase after inspecting it would redefine the test domain.
- Keeping it, with stratified reporting, makes its effect visible.
Consequence: Phase-stratified metrics are a mandatory secondary report (D-041).

## D-036 — User02 dual-device use (closes the P2 part of OPEN-03)
Date: 2026-09-13
Status: Accepted
Context: 22480 and 22482 are two concurrent, uncoupled mats of User02 with different T/H (D-027). Their physical
placement is unknown.
Decision:
- Both mats are used, as two separate input streams of one subject. Each window comes from one mat only.
- Forbidden:
  - a 12-channel merge;
  - row-level fusion or timestamp alignment;
  - target averaging;
  - using one mat as the other's ground truth;
  - preferring or dropping a mat.
- **Subject level.** User02 is one subject in folds, counts and the primary unweighted mean. Its subject metric pools
  the labelled windows of both mats.
- `device_id` is provenance only, never an input.
- Device-stratified metrics (22480, 22482) are secondary diagnostics. They never add subjects.
- Concurrent rows share the partition of their subject (LOSO) or subject-night (RQ2) (L8).
Evidence: A2 (no coupling; T/H offset); P1 §5 (22482 +3 °C, +14 %RH vs 22480 on the same nights); D-027; L8. The
protocol does not depend on the unknown physical placement.
Consequence: User02's subject metric mixes two microclimates, so device-stratified diagnostics are required.

## D-037 — RQ2 chronological personalization split
Date: 2026-09-13
Status: Accepted
Context: RQ2 fine-tunes a subject-independent model on a subject's earliest data and tests on later data (L5).
Decision:
- Per target subject, subject-nights (D-030) are numbered 1…N in time order.
- **Budgets** b ∈ {0, 1, 3, 7, 14} nights:
  - adaptation = nights 1…b (the earliest);
  - buffer = night b + 1 (one full recorded subject-night, never used);
  - per-budget test = nights ≥ b + 2;
  - b = 0 has no adaptation and no buffer.
- **Primary RQ2 test span:** nights ≥ 16 (largest budget 14 + 1 buffer + 1).
  - It is identical for every budget, including b = 0.
  - It satisfies adaptation < buffer < test for every budget.
  - The per-budget later span (≥ b + 2) is secondary.
- All devices of a subject-night share its partition. Both User02 mats are used in adaptation.
- The deployment timeline is preserved: spans may cross sensor/quality phases and seasons. No split is rebuilt to
  avoid a boundary.
- **Base model:** the RQ1 model of the fold in which the subject is held out.
- **Fine-tuning recipe** (fixed; nothing is tuned on target data):
  - all parameters, AdamW;
  - learning rate 0.1 × the selected base rate, same weight decay;
  - 10 epochs over the adaptation windows, batch 256;
  - no early stopping and no scaler refit;
  - the seeds of D-040.
- Windows are also cut at night and partition boundaries.
- File: `data/splits/v1.0_personalization/chronological.csv` (D-042).
Evidence:
- L5.
- Nights 151 / 51 / 100 give primary test spans of 136 / 36 / 85 nights.
- User01's adaptation (2025-08 to -11, `s1`) precedes a test span that crosses into `s2`.
- User02's late span holds the 22482 shift phase and six days recorded only on 22482 (D-022).
- A common test span compares budgets on identical nights. With per-budget test spans, the smaller budgets would be
  tested on earlier nights, which confounds the budget comparison with drift.
Consequence: A personalization gain cannot be attributed to pure user adaptation. Hardware, season and domain
adaptation are mixed in (P1 §11), and this is reported with phase stratification.

## D-038 — Input admissibility: control events, firmware movement labels, calendar and identity (closes OPEN-10, OPEN-15)
Date: 2026-09-13
Status: Accepted
Context:
- The mat's firmware derives heater-control events from temperature (L9).
- Firmware movement labels come from an opaque provider algorithm (OPEN-15).
- Calendar fields can proxy for season (L10; P1 §7).
Decision:
- Model inputs are functions of the P1–P6 values of the window's rows only (D-039).
- **Never inputs:**
  - temperature or humidity of any device, and target flags;
  - heater/control events, set-points, limits and modes (AHON, AHOF, BHSDOWN, BHNTSDOWN, BCSUP, STEMP, SLIMIT,
    SMINLIMIT, FON/FOF/FOH, AMODE/MMODE, AI*, EVENT:*, …);
  - heater state inferred from targets;
  - firmware movement labels (`event_raw`);
  - calendar and time fields (timestamp, date, month, season, day index, hour of day, night);
  - identity and provenance fields (subject, device, source, file, session, sensor or quality phase).
- **OPEN-10:**
  - heater state is not an input covariate;
  - valid targets are kept whatever the control context, with no removal around events;
  - heater state between events is not reconstructed;
  - control events serve only event-conditioned stratification or sensitivity (P6) and interpretation.
- **OPEN-15:** firmware movement labels are not model inputs in v1.0. They remain descriptive metadata and an
  optional diagnostic comparison. MOVEMENT features are computed from P1–P6 (D-039).
- The leakage gate enforces this with an allowlist of feature names (L9, L10).
Evidence:
- L9, L10.
- P1 §9: control codes are temperature-derived; AHON fires after a temperature fall.
- P1 §7: calendar/season confounding.
- P1 §11: the label distributions are device-dependent ("left" covers 66–73 % of rows on three streams; "right"
  leads with 35–42 % on 22482).
Consequence: RQ3 movement features are reproducible from pressure alone. Whether any firmware information helps is not
tested in v1.0.

## D-039 — RQ3 feature families; geometry-free contact features (protocol independent of OPEN-20)
Date: 2026-09-13
Status: Accepted
Context:
- RQ3 compares movement-derived and contact-structure features.
- The physical layout of P1–P6 is unknown (OPEN-20).
- Feature definitions must be fixed before P4.
Decision: per window step, from the step's six channels (and, for MOVEMENT, the previous step in the same window):
- **RAW (6):** p_c / 4095.
- **MOVEMENT (10):**
  - Δp_c / 4095 (6);
  - mean |Δp_c| / 4095;
  - Δ(pressure sum / (6 · 4095));
  - Δ(active channels / 6);
  - dominant-channel switch (0/1).
  Step 0 has no predecessor inside the window and is 0 by declaration.
- **CONTACT (11):**
  - pressure sum / (6 · 4095);
  - active channels (p_c > 0) / 6;
  - channel shares p_c / Σp (6);
  - normalised entropy of the shares;
  - maximum share;
  - across-channel standard deviation / 4095.
  An all-zero frame has zero shares, entropy and maximum share.
- The dominant channel is argmax_c p_c (lowest index on ties), or none for an all-zero frame.
- **Families:** RAW, MOVEMENT, CONTACT, RAW+MOVEMENT, RAW+CONTACT, RAW+MOVEMENT+CONTACT. The primary RQ1/RQ2
  family is RAW.
- Each family gets its own inner-validation selection (D-040). There is no feature selection.
- **Forbidden while OPEN-20 is open:** channel coordinates, centre of pressure, left/right or head/foot
  interpretation, and geometry-dependent spatial moments. A layout-based feature requires a protocol version bump.
- Implementation: `src/features/pressure_features.py` (tested).
Evidence: RESEARCH_PROTOCOL §2 (working meaning); A9 (channel pairing is compatible with, not proof of, a layout);
P1 §4 (channel profiles are device-dependent).
Consequence: Feature definitions cannot change after P4 results are seen.

## D-040 — Baselines, models, hyperparameter search, model selection and seeds
Date: 2026-09-13
Status: Accepted
Context:
- RESEARCH_PROTOCOL §3.3 requires a training-mean predictor and the prior study's approach under the same split.
- The prior study's exact configuration is not in the repository, so no value from it is assumed.
Decision:
- **Baselines** (P3, identical splits):
  1. training-mean predictor: the mean of each target over the labelled windows of the outer training pool
     (deterministic);
  2. TCN on RAW inputs: the prior study's model family, re-implemented here. Its configuration comes only from the
     search below. The 40 s window is the prior-study comparison anchor (D-032). The prior study's movement fusion is
     examined through the P4 family comparison.
- **TCN architecture:**
  - causal residual TCN with 3 blocks, dilations 1, 2, 4;
  - two causal convolutions per block, with ReLU and dropout;
  - a 1×1 residual projection when the channel count changes;
  - a linear head on the last time step with 2 outputs;
  - loss: MSE on training-standardised targets, equally weighted.
- **Search space** (16 configurations): channels {32, 64} × kernel {2, 3} × dropout {0.1, 0.3} × learning rate
  {1e-3, 3e-4}.
  - Fixed: AdamW, weight decay 1e-4, batch 256, at most 50 epochs.
  - Early stopping: patience 5 on the inner-validation criterion.
- **Selection** (per outer fold and feature family):
  - every configuration is trained on `inner_train` and scored on `inner_val` for both inner splits, with seed 0;
  - criterion: the mean over the inner splits of (MAE_T / sd_T + MAE_H / sd_H) / 2, with sd taken from that inner
    training partition. It is unit-free and used for selection only, never as an endpoint;
  - ties go to the first configuration in the declared grid order.
- **Final outer model:** retrained on the whole outer training pool with the selected configuration, for the rounded
  mean of the two inner best-epoch counts. No held-out data are used.
- **Seeds:** [0, 1, 2]. Every final model (outer and personalization) is trained once per seed. Results are reported
  per seed and as the seed mean. No seed is added or dropped after results are seen.
- The outer test is evaluated once per protocol version.
Evidence: L4; RESEARCH_PROTOCOL §3.3, §3.4, §3.6.
Consequence: 16 configurations × 2 inner splits × 3 folds × 6 families = 576 inner selection runs in P3/P4. This
budget is fixed now.

## D-041 — Metrics, aggregation and statistical reporting unit
Date: 2026-09-13
Status: Accepted
Context:
- n = 3 subjects (D-020).
- Windows are not independent (RESEARCH_PROTOCOL §3.1).
- P1 found domain-level offsets in both pressure and targets.
Decision:
- **Primary endpoints**, per target (temperature in °C and humidity in %RH, never combined):
  - MAE and RMSE over the labelled test windows of each held-out subject (User02 = both mats pooled);
  - the unweighted mean over the three subjects.
- **Secondary**, declared now:
  - mean signed error (bias);
  - window-weighted pooled metric (micro);
  - device-stratified (User02 22480 / 22482);
  - phase-stratified (User01 s1 / s2; 22482 normal / p1_transition / p1_response_shift);
  - per-night error distribution;
  - seed spread.
- **RQ2**, per subject, budget and target:
  - MAE/RMSE on the primary test span;
  - gain_b = MAE(b = 0) − MAE(b);
  - unweighted mean over subjects;
  - per-budget later span and phase strata as secondary.
- **Statistics:**
  - no population-level significance claim; all folds are shown;
  - within-subject uncertainty: night-level cluster bootstrap (test nights resampled with all their windows; 2,000
    resamples, seed 0, 95 % percentile interval), done in P6;
  - model comparison: per-subject paired differences, a night-level paired bootstrap, and the number of subjects
    improved (x/3);
  - no window-level test (e.g. a paired t-test) is used for inference.
Evidence: RESEARCH_PROTOCOL §3.1–§3.2; D-020; P1 §5–§6.
Consequence: Window counts differ roughly two-fold between subjects (User01 289,672 vs User07 140,972 at 40 s).
Subject-level unweighted aggregation stops User01 from dominating the primary claim.

## D-042 — Leakage validation gate and split artifacts
Date: 2026-09-13
Status: Accepted
Context: L1 and L12 require splits to be saved before windowing and training to refuse to start when a leakage
check fails.
Decision:
- **Split files**, committed: `data/splits/v1.0_loso/outer_folds.csv`, `data/splits/v1.0_loso/inner_folds.csv` and
  `data/splits/v1.0_personalization/chronological.csv`.
  - They are group assignments (a session, or a session × night piece) with time span, row count and phases. They
    hold no sensor or target values.
  - They are built deterministically from canonical_v1 by `scripts/build_p2_splits.py`. `--check` rebuilds them and
    compares.
- **Manifest** `data/splits/v1.0_manifest.json`:
  - protocol version and protocol-file hash;
  - canonical content/file hashes, config hash and raw-manifest hash;
  - per-file SHA-256 and row counts;
  - scheme metadata and generator hashes;
  - a `build` section (time, git commit, dirty flag), the only part that changes on rebuild.
  - Hashes are taken over bytes with CRLF normalised to LF, and `.gitattributes` keeps LF.
- `.gitignore` admits exactly these files (CONVENTIONS §6.7 amended accordingly).
- **Gate** (`src/evaluation/leakage.py`). Checks:
  - split files vs manifest (corruption);
  - canonical data vs manifest (L7);
  - three disjoint outer folds (L2/L4);
  - subject-level inner validation without the held-out subject (L4);
  - chronology, budgets, buffer and common test span (L5);
  - devices of a subject/night in one partition (L8);
  - primary sources only, no User03/User06 (L6);
  - complete canonical coverage (L2/L7);
  - with a run context: input allowlist (L9), calendar/identity fields (L10), fit provenance on training partitions
    only (L3/L11), selection subjects (L4) and windows inside partitions (L1).
- A check that raises counts as failed. `require_pass` raises `LeakageGateError`.
- Every P3+ training entry point must call `gate_for_training` before it loads training data, and must store the
  report as `leakage_check.json` (CONVENTIONS §5). `scripts/validate_p2_protocol.py` runs the gate for every
  declared v1.0 context and builds and validates every window inside its partition.
Evidence:
- Gate: 118/118 checks pass on the frozen splits.
- A rebuild from canonical_v1 gives byte-identical split files and a semantically identical manifest.
- Synthetic tests: `tests/test_leakage.py`, `test_splits.py`, `test_windowing.py`, `test_pressure_features.py`.
Consequence: Changing a split file breaks the manifest hash and the gate. A new split needs a new protocol version.

## D-043 — P3 execution environment and implementation clarifications (no protocol change)
Date: 2026-09-13
Status: Accepted
Context: P3 runs protocol v1.0 (D-040, D-041) for the first time. `requirements.txt` asks for a record of any
package that affects results. D-040 does not spell out every implementation detail of the declared TCN and its
training. These details are fixed here, before any model is trained on study data. No v1.0 item changes; the
protocol version stays v1.0.
Decision:
- **Environment.**
  - PyTorch 2.12.0 (CUDA 12.6 build) on one NVIDIA GPU.
  - Deterministic mode: `torch.use_deterministic_algorithms(True)`, cuDNN deterministic, no benchmark,
    `CUBLAS_WORKSPACE_CONFIG=:4096:8`, `num_workers` 0.
  - Every run records its environment in `run_meta.json`.
- **TCN and training details** (the standard TCN residual block; nothing added to D-040):
  - causal convolution by left zero-padding; block output = ReLU(main + residual);
  - PyTorch default initialisation;
  - no weight normalisation, no normalisation layer, no gradient clipping, no learning-rate schedule;
  - per-epoch shuffling with a seeded generator; the last partial batch is kept;
  - Python, NumPy and PyTorch (CPU and CUDA) are seeded with the run seed.
- **Early stopping** (inner runs):
  - strict improvement of the frozen criterion only;
  - best epoch = the first epoch with the lowest criterion;
  - stop after 5 epochs without improvement;
  - the inner model uses the best-epoch weights.
- **Final epoch count.** "round" in D-040 means half-up rounding (7.5 → 8), not banker's rounding.
- **Aggregation over seeds** averages the seeds' metrics, never their predictions (no ensemble is declared).
- **Bias** = mean(prediction − truth).
- **Gate schema for the training-mean predictor.** The training-mean predictor declares the RAW window schema to the
  leakage gate. It uses no input.
Evidence: D-040, D-041; `src/models/tcn.py`, `src/training/trainer.py`, `tests/test_p3_loso.py`. When this entry was
written, no model had been trained on study data; only a synthetic smoke test had run.
Consequence: P3 runs are reproducible from the committed code, the frozen protocol and the committed P3 selection
file. A change to any of these details would be a new decision and a protocol version bump.

## D-044 — P4 execution and pre-declared feature-family comparisons (no protocol change)
Date: 2026-09-13
Status: Accepted
Context:
- P4 answers RQ3 with the families of D-039 under protocol v1.0, with the selection of D-040.
- The P3 outer-test results (RAW TCN and training-mean, `docs/P3_STRICT_LOSO_BASELINE_REPORT.md` §7–§11) were seen
  before this entry was written. No P4 model had been trained.
- Nothing below changes a v1.0 item. Families, formulas, grid, selection rule, seeds and metrics stay those fixed in P2.
  This entry fixes only how P4 executes them and which descriptive comparisons are reported.
Decision:
- **Scope.**
  - Trained in P4: MOVEMENT, CONTACT, RAW+MOVEMENT, RAW+CONTACT and RAW+MOVEMENT+CONTACT.
  - Each family gets its own inner search (3 folds × 16 configurations × 2 inner splits = 96 runs, 480 in total), its
    own selection per fold, and final models for seeds 0/1/2 (45 runs).
  - RAW is not re-run. The RAW TCN and the training-mean predictor frozen at `p3-loso-baseline` are imported from the
    committed P3 tables as the reference. With P3's 96 RAW inner runs this spends exactly the 576-run budget of D-040.
- **Implementation** (P3 code and D-043 otherwise, unchanged):
  - The trainer takes the family. Inputs come from `build_inputs` (D-039 formulas, unchanged). They are computed in
    chunks of windows, which is exact because every formula is per window, and stored as float32. The TCN input width
    is the family's feature count; nothing else in the model or training changes. RAW keeps its P3 values bitwise.
  - Before a run, the family's composition, order, width and names are checked against `protocol.yaml` and D-039,
    and the leakage gate receives the family's feature list. Any mismatch stops the run (fail closed).
  - `run_meta.json` records the deterministic flags after they are switched on (the P3 report §14 note).
  - The 15 family × fold selections go to `configs/experiments/v1.0/p4_selected_configs.yaml`. Final runs refuse to
    start unless this file is committed and unmodified, and each final run records its commit.
  - The outer target scaler does not depend on the family. It must equal the P3 frozen scaler of the same fold.
- **Pre-declared comparisons.** They are descriptive; D-041 statistics are unchanged and no significance test is used.
  Δ = metric(first) − metric(second), from seed means, per target and held-out subject. Negative means the first is
  better.
  - Primary endpoints: MAE and RMSE per subject and the unweighted 3-subject mean, for all six families and the
    training-mean predictor.
  - Feature added to a model:
    - A = RAW+MOVEMENT − RAW;
    - B = RAW+CONTACT − RAW;
    - C = RAW+MOVEMENT+CONTACT − RAW;
    - D = RAW+MOVEMENT+CONTACT − RAW+MOVEMENT;
    - E = RAW+MOVEMENT+CONTACT − RAW+CONTACT.
  - Representation sufficiency, kept separate from A–E: MOVEMENT − RAW and CONTACT − RAW.
  - Every family against the training-mean predictor, with the number of seeds on each side per subject.
  - Subject consistency: improved subjects x/3. "Improved in all three held-out subjects" is used only for 3/3.
  - Seed consistency: differences between runs with the same seed index (3 subjects × 3 seeds = 9 per comparison).
    Reported: the number improved, the mean, the minimum and the maximum. Equal seed indices are a bookkeeping pairing,
    not a matched design; all seeds are reported.
  - Offset diagnostics:
    - bias per family and subject, and |bias| / MAE;
    - error SD = √(RMSE² − bias²), a descriptive split of the declared RMSE and bias into offset and variation.
  - Secondary strata as in P3: User01 s1/s2; User02 22480/22482; 22482 normal / p1_transition / p1_response_shift;
    the per-night distribution; the window-weighted pooled metric.
  - The family with the lowest unweighted mean is reported as "lowest unweighted mean in this cohort", not as the best
    model.
- **P5.** The primary personalization family stays RAW (EXPERIMENT_PROTOCOL §8), whatever P4 shows. Personalizing
  another family is secondary or needs a protocol-versioned extension.
- **Reproduction criterion,** fixed before any P4 run:
  - the 45 final runs are re-run from a clean checkout of the selection commit, using only committed code, protocol
    and selection file;
  - every final-run MAE and RMSE must agree within 1e-6; predictions are compared bitwise;
  - the inner search is not re-run in full. The inner runs of every selected configuration (15 × 2 = 30) are re-run
    and must give the same best epoch and criterion (within 1e-9);
  - selection provenance is otherwise checked through the committed selection file, its per-fold SHA-256 and the
    run-status checksums.
Evidence: D-039, D-040, D-041, D-043; `src/evaluation/p4_ablation.py`, `src/training/trainer.py`,
`tests/test_p4_features.py`, `tests/test_p4_ablation.py` (synthetic data only). When this entry was written, the P3
results were known and no P4 model had been trained.
Consequence: P4 outer results are interpreted only through these comparisons. A change to any feature formula, grid,
selection rule or epoch rule after P4 results are seen would be a protocol version bump reported next to v1.0.

## D-045 — P5 execution and pre-declared adaptation measures (no protocol change)
Date: 2026-09-14
Status: Accepted
Context:
- P5 answers RQ2 with the chronological personalization protocol of D-037, which uses the base models of D-040.
- The P3 and P4 outer-test results were seen before this entry was written. No P5 model had been adapted or
  evaluated.
- Nothing below changes a v1.0 item. The split, budgets, buffer, primary test span, fine-tuning recipe, seeds,
  metrics, windowing and RAW inputs stay as frozen in P2. The P4 results do not change the primary family (RAW,
  EXPERIMENT_PROTOCOL §8).
Decision:
- **Base models.**
  - The base model is the P3 final RAW-TCN of the fold that holds the subject out.
  - The local P3 checkpoints are used. Before use, each must be a verifiably complete P3 run, and it must reproduce
    its stored P3 outer predictions bitwise.
  - Adaptation seed s starts from the base model of seed s, so each seed is a paired chain from base to adapted
    model.
  - b = 0 evaluates the base model as it is. It is not retrained.
- **Fine-tuning.**
  - The recipe is exactly `protocol.yaml` `personalization.fine_tuning`: all parameters, AdamW, learning rate
    0.1 × the fold's selected base rate, the base weight decay, 10 epochs, batch 256, no early stopping, no validation.
  - It uses the base model's outer target scaler; nothing is refit.
  - Implementation: the P3 trainer starts from the base weights (`train_tcn(init_state=…)`). Per-epoch shuffling uses
    the seeded generator, and the last partial batch is kept (D-043).
- **Data.**
  - Windows follow D-032 and are also cut at night and partition boundaries (D-037); they are built from the split
    file.
  - Adaptation uses every labelled window of the b adaptation nights (both User02 mats).
  - Each model is evaluated once, on the labelled windows of its budget's test partition. The primary span
    (night ordinal ≥ 16) is reported apart from the per-budget later span (secondary).
- **Plan before evaluation.**
  - Before any adaptation or P5 evaluation, `configs/experiments/v1.0/p5_personalization_plan.yaml` is generated from
    frozen inputs only and committed. It holds, per subject:
    - nights;
    - window counts, and a digest proving the primary windows are identical for every budget;
    - base configuration and learning rates;
    - scaler statistics;
    - base checkpoint hashes.
  - Runs refuse unless this file is committed and unmodified.
- **Checks per run** (fail closed): the P2 gate with the personalization context, plus ten P5 checks:
  1. target not in the base training pool;
  2. adaptation and test nights disjoint;
  3. buffer night unused;
  4. all devices of a night in one partition;
  5. each session × night piece in one partition;
  6. scaler fitted on the outer training subjects only;
  7. scaler not refit;
  8. windows inside partition, night, session and phase;
  9. adaptation rows earlier than any buffer or test row;
  10. recipe equal to the frozen one, and primary windows equal to the plan.
- **Pre-declared measures** (descriptive; D-041 statistics unchanged; no significance test):
  - Primary endpoints: MAE, RMSE and bias per target, subject, budget and seed on the primary span; seed means; the
    unweighted 3-subject mean.
  - E = MAE:
    - G_b = (E_0 − E_b) / E_0 × 100;
    - ΔE_b = E_0 − E_b;
    - C_b = |Bias_0| − |Bias_b|.
    These come from seed means per subject and target. Negative values mean adaptation made things worse; nothing is
    clipped.
  - Seed-paired gains (seed s adapted vs its own base): seeds improved and the per-seed range.
  - Cohort row: G and ΔE come from the unweighted means of MAE. |bias|, C_b and the error SD are averaged over
    subjects, because signed biases would cancel.
  - Error SD = √(RMSE² − bias²), a descriptive split into offset and variation (as in D-044).
  - The per-budget later span, a window-weighted pooled metric and per-night metrics (per seed; the unit for P6) are
    secondary.
  - Strata on the primary span: User02 22480 / 22482 (and 22482 quality phases); User01 s1 / s2. No stratum gets its
    own model or scaler.
- **Reproduction criterion,** fixed before any P5 run:
  - a clean checkout of the plan commit regenerates the nine P3 base models with the committed P3 selection; their
    weights must be bitwise identical to the plan's hashes;
  - it then re-runs all 45 P5 runs. Every MAE, RMSE and bias must agree within 1e-6, and predictions are compared
    bitwise.
Evidence: D-032, D-037, D-040, D-041, D-043; `src/evaluation/p5_personalization.py`, `src/training/trainer.py`,
`tests/test_p5_personalization.py` (synthetic data only). When this entry was written, the P3 and P4 results were
known, and no P5 adaptation or evaluation had run.
Consequence: P5 results are interpreted only through these measures. A change to the recipe, the split or the base
models after P5 results are seen would be a protocol version bump reported next to v1.0.

## D-046 — P4 phase-boundary tag `p4-feature-ablation` (repository metadata only)
Date: 2026-09-14
Status: Accepted
Context:
- RESEARCH_PROTOCOL §5 and CONVENTIONS §6.5 defined no freeze tag for P4, and the P4 report and PR said none would be
  created.
- After the P4 merge (PR #5, merge commit `977b33d`), the research lead decided to mark every completed phase
  boundary explicitly, as for P2 and P3. This gives P5 a fixed reproducibility checkpoint.
Decision:
- The annotated tag `p4-feature-ablation` (tag object `ee4857c`) was created on the P4 merge commit `977b33d` and
  pushed.
- RESEARCH_PROTOCOL §5 and CONVENTIONS §6.5 list it among the freeze tags.
- It freezes nothing new: protocol v1.0, the splits and the P3/P4 results are unchanged. P5 starts from this tag.
- The P4 report's statement that no P4 tag would be created is kept as written; this entry supersedes it for the
  tag only.
- Tags are still never moved, deleted or re-pointed.
Evidence: tag `p4-feature-ablation` → `977b33d` locally and on origin; branch `experiment/p5-personalization` starts
from it.
Consequence: P0, P2, P3 and P4 boundaries are tagged. The P5 tag (`p5-personalization`) follows the P5 merge.

## D-047 — P6 robustness and uncertainty analysis plan
Date: 2026-09-14
Status: Accepted
Context:
- P6 quantifies the uncertainty and robustness of the P3–P5 results. The P5 results, including the observed
  negative transfer (User07 temperature at every budget; User01 humidity at b = 1–7), were known when this entry was
  written (`docs/P5_PERSONALIZATION_REPORT.md`). No P6 quantity had been computed.
- P6 is analysis-only. It reads frozen artifacts: committed P5 tables, the P5 run predictions (reproducible bitwise
  from `bce5e06`) and canonical_v1.
- No model is trained, re-selected or re-evaluated. No protocol item, split, plan, recipe, P3/P4/P5 result or P5
  conclusion changes. P5 primary numbers stay those of the P5 report.
Decision:
**A. Pre-declared by protocol v1.0** (D-041, `protocol.yaml` `metrics.bootstrap`, D-038):
1. **Night-level paired cluster bootstrap of the P5 adaptation effect.** Adapted model (b ∈ {1, 3, 7, 14}) vs base
   model (b = 0), per subject × target × budget.
   - Source: `paper/tables/p5_per_night.csv`, primary-test nights only (`primary_test` = 1).
   - A pair is the same subject and night. Base and adapted must have the same nights and the same window count per
     night, otherwise the analysis fails.
   - Primary: seed 0, adapted against its own base model.
   - Resampling: nights with replacement, keeping every window of a resampled night (cluster bootstrap); 2,000
     resamples.
   - RNG: `numpy.random.default_rng(0)`, drawn once per subject. The same resampled nights are used for base and
     adapted, both targets and every budget.
   - Statistic: the subject-level metric over the resampled windows, window-weighted over nights: MAE = Σ n·MAE / Σ n;
     RMSE = √(Σ n·RMSE² / Σ n); bias = Σ n·bias / Σ n.
     - ΔMAE = MAE_base − MAE_adapted;
     - ΔRMSE likewise;
     - Δ|bias| = |bias_base| − |bias_adapted| (= C_b).
     - Positive means adaptation is better.
   - Point estimate: the full sample (it equals the P5 seed-0 values).
   - Interval: the 2.5 and 97.5 percentiles (numpy linear).
   - Also reported, descriptively: the mean and median of the per-night ΔMAE (unweighted over nights), the share of
     nights with ΔMAE > 0, and the number of nights.
   - Seeds 1 and 2 get the same procedure in a separate seed-sensitivity table. They are never pooled with seed 0.
   - Wording: "within-subject night-level bootstrap interval". There are no p-values, no window-level tests and no
     inference across the three subjects.
2. **Heater-context strata.** The category is pre-declared (D-038, D-041); its operational definition is fixed here,
   after the P5 results were seen.
   - Scope: User02 (both mats) windows of the primary span.
   - Strata, by the most recent AHON or AHOF control code on the same device within 60 min before the window's target
     timestamp:
     - `after_AHON_60min`;
     - `after_AHOF_60min`;
     - `no_AHON_AHOF_60min` otherwise.
   - The codes come from canonical `event_raw` (`domain_shift.parse_event`). They are used for test-time
     stratification only, never as inputs, and no heater state is reconstructed.
   - The strata are crossed with mat (22480 / 22482) and the 22482 quality phase.
3. n = 3: there is no population-level inference.

**B. Added after the P5 results were observed** (post-hoc secondary / robustness analyses; they never replace the
P5 primary results):
4. **Drift sensitivity** of the evaluation start night.
   - Grid: s ∈ {12, 14, 16, 18, 21}. The span is the nights with ordinal ≥ s.
   - Metrics are recomputed from `p5_per_night.csv` (window-weighted) for seeds 0–2. Reported: the seed mean, the
     seeds on each side, and ΔE and G against b = 0 on the same span.
   - A budget is evaluated at s only if its adaptation and buffer nights precede s (b + 1 < s). b = 14 is therefore
     not evaluated at s = 12 and s = 14: its adaptation nights are 1–14 and its buffer night 15. This exclusion is
     fixed before any result.
   - Every other combination is feasible. The minimum is 10 nights per span; the shortest is User02 at s = 21, with
     31 nights.
   - s = 16 must reproduce the P5 primary values.
5. **Temporal target-level trajectory** per subject × target.
   - Per-night mean of the labelled window targets (RQ2 windows at b = 0).
   - A centred rolling mean over 7 recorded nights, truncated at the ends of the series.
   - Adaptation-span means (b = 1, 3, 7, 14), the primary-span mean, and the future-span mean for every s in the drift
     grid, with their differences; the base model's training-pool mean (outer scaler mean).
   - Descriptive consistency check per subject × target × budget: the expected direction is improvement if
     |adaptation mean − primary mean| < |bias₀| (P5 seed-mean base bias on the primary span), otherwise worsening.
     This is compared with the sign of the P5 G. It shows association only.
6. **User02 residual device diagnostics** for each mat × {all, 22482 quality phase, heater context}:
   - number of nights and windows; MAE, RMSE and bias at b = 0…14 (seed mean and seed 0);
   - for strata with ≥ 10 nights: a seed-0 night-cluster paired bootstrap (the same procedure as item 1, over the
     nights holding the stratum) of ΔMAE for b = 0 vs b = 14, and of the b = 14 bias;
   - smaller strata (e.g. `p1_transition`, one night) are descriptive only.

**C. Not executed in this P6 core:**
- **20/30 s sensitivity windows.** The windows are pre-declared (D-032, `protocol.yaml` `sensitivity_candidates_s`),
  but v1.0 does not specify which models, search, selection or phases they apply to. Running them needs new model
  training, which is outside this analysis-only P6. They are deferred until a decision fixes the procedure.
- **4095 sensitivity** (D-033). No procedure is declared and it needs training; deferred likewise.
- **Bias-only calibration and other adaptation recipes** are not part of v1.0. They are only proposed as a possible
  secondary experiment.

**Reproduction criterion:** the P6 analysis is deterministic. A clean checkout of the P6 code commit regenerates the
P3 base models and the P5 runs, then the P6 analysis. Every P6 table and the figure data must be byte-identical.
Evidence: D-032, D-033, D-038, D-041; `docs/P5_PERSONALIZATION_REPORT.md`. This entry was written after the P3–P5
results were seen and before any P6 computation.
Consequence: every P6 quantity is either the pre-declared uncertainty analysis (A) or labelled post-hoc (B). None
changes a P5 number or conclusion. Deferred items (C) need their own decision before they are run.

## D-048 — P6 phase-boundary tag `p6-robustness` (repository metadata only)
Date: 2026-09-14
Status: Accepted
Context: RESEARCH_PROTOCOL §5 and CONVENTIONS §6.5 defined no freeze tag for P6. As for P4 (D-046), the research
lead decided to mark the completed P6 boundary explicitly before P7.
Decision:
- The annotated tag `p6-robustness` (tag object `cfc0264`) was created on the P6 merge commit `16980ae` (PR #7) and
  pushed.
- It is a repository-level reproducibility checkpoint only. Protocol v1.0, the splits, canonical_v1 and the P3–P6
  results are unchanged.
- RESEARCH_PROTOCOL §5 and CONVENTIONS §6.5 now list it. Tags are still never moved, deleted or re-pointed.
Evidence: tag `p6-robustness` → `16980ae0095e79535b81999aed01d3240c8b560d` locally and on origin. P7 starts from it
(branch `release/p7-public-data`).
Consequence: the P0 and P2–P6 boundaries are tagged.

## D-049 — Public release temporal de-identification (closes OPEN-18)
Date: 2026-09-14
Status: Accepted
Context:
- DATA_POLICY §5.5: exact calendar dates combined with health events can re-identify a person. OPEN-18 left open
  whether public releases use absolute dates or relative day indices.
- The P3–P6 pipelines depend on the order of observations, the gaps inside a window (≤ 5 s), the 5-s bins, the
  noon-to-noon night (D-030) and the chronological night ordinal (D-037). They do not depend on the calendar date.
Decision (for `public_release_v1` and later releases unless superseded):
- **No absolute year, month or day in any release artifact.**
- **Per-subject anchor:** local midnight of the calendar date of the subject's first night (night = date(t − 12 h),
  D-030). Both User02 mats share their subject's anchor, so their concurrency is preserved.
- **Every release time is integer seconds since that anchor** (`*_time_s`). The anchor shift is a whole number of
  days, so clock time of day, the noon boundary, gaps and within-night structure are exact.
- **Night key:** `D####` = days from the anchor date to the night's date + 1 (a relative day index; gaps between
  recorded nights stay visible). Human-readable times are written `D#### HH:MM:SS`. `night_ordinal` 1…N keeps the
  D-037 numbering.
- **Preserved:** order, gaps, sessions, nights, ordinals, P5 budgets and primary span, and every P3–P6 grouping and
  metric.
- **Not preserved:** calendar date, weekday and the calendar alignment between subjects. The subjects were never
  recorded at the same time (A11).
- **Scope:** the release package.
  - The public repository already contains session-level absolute dates in committed protocol, split and result files
    (e.g. `data/splits/*`, `configs/subject_mapping.yaml`, the P5 plan, `paper/tables/p5_per_night.csv`, reports).
    These hold no sensor or target values and no health information; restricted metadata is never released.
  - Removing them would mean rewriting published history. That is not done here and is flagged for the PI.
Evidence: DATA_POLICY §5; D-030, D-032, D-037; code review of `src/training/loso_data.py`,
`src/evaluation/p5_personalization.py` and `src/evaluation/p6_robustness.py` (P7 report §2). Written after the P3–P6
results were known; no result depends on the representation of dates.
Consequence: the release reproduces every P3–P6 quantity without any calendar date. Public night keys differ from the
private date strings, so any table carrying a night key is compared through `night_ordinal`.
Note (P7 build, 2026-09-14): the public reproduction compares such cells more strictly. A committed night date and its
public key must differ by one whole-day shift per subject, the same in every table
(`src/evaluation/public_reproduction.py`, report §5). The shift values are never written out.

## D-050 — `public_release_v1`: model-ready window release, content and storage
Date: 2026-09-14
Status: Accepted
Context:
- P7 releases the minimum information needed to reproduce the P3–P6 results (DATA_POLICY §5).
- Code review found:
  - the P3/P4 models consume fold window arrays (`FoldData`: pressure windows, targets, labels, split partitions);
  - P5/P6 consume per-subject window arrays (`SubjectWindows`) and the personalization split;
  - none of them needs the rows between window steps.
- Windows are ordered by their first row, the same way in every fold, so the release can keep the training order
  that bitwise reproduction requires.
Decision:
- **Representation:** a model-ready window release (option A). Canonical rows are not released.
  - `windows.parquet` holds the union of the D-032 LOSO windows and the D-037 RQ2 windows, which are also cut at
    night boundaries. Flags `in_loso` and `in_rq2` mark membership.
  - Rows are in canonical first-row order.
  - Per window:
    - subject, device, session, sensor and quality phase;
    - night key and ordinal (D-049);
    - window start and target time (D-049);
    - the 8 × 6 raw pressure integers (0–4095, 4095 kept);
    - temperature, humidity and their validity flags at the target row.
- **Splits:** public copies of the three v1.0 split files, with the same rows, columns and semantics and D-049
  relative times.
- **P6 heater strata:** User02 AHON/AHOF control codes with relative times (codes only; no log text).
- **Also included:** a public copy of the P5 plan (night keys mapped by D-049; everything else unchanged) and
  reference digests of the frozen P3/P4/P5 prediction values, for bitwise checks.
- **Metadata:** `manifest.json` (deterministic; SHA-256 of every artifact), `schema.json`, `excluded_sources.csv`,
  `README.md`.
- **Identity:**
  - subject IDs stay `User01`, `User02`, `User07`;
  - device IDs stay `22480` / `22482` (mat hardware IDs, already used in every public document, not personal
    identifiers) and `unknown`;
  - session IDs stay `<subject>|<device>|S####`;
  - User02's two mats remain one subject.
- **Not included:**
  - the User06 source (`excluded_invalid`), the quarantined files and restricted metadata;
  - auxiliary sources (User02 legacy, User03 legacy; unused by v1.0);
  - raw provenance (source files, rows, chunk keys, file IDs);
  - `event_raw` text and firmware movement labels.
  `excluded_sources.csv` lists every excluded source with its reason and decision (DATA_POLICY §5.4).
- **Gates before a release candidate is accepted:**
  - a privacy validator: identifiers, paths, dates, restricted fields, excluded sources, hashes;
  - a private/public equivalence gate: the fold and subject window arrays rebuilt from the release must equal the
    private ones bitwise under the D-049 mapping, the split semantics must be identical, and the public P5 plan must
    equal the private plan under the night mapping.
- **Storage:**
  - `windows.parquet` is not committed to Git; the builder reproduces it byte for byte from canonical_v1. The small
    metadata is committed.
  - External hosting (GitHub Release, Zenodo, OSF, …), DOI and the data license are PI decisions. The repository has
    no LICENSE, so external publication is blocked until they are made.
- **Reproduction tiers:**
  - core: P3 training-mean and final RAW-TCN from the frozen selection, then P5, then P6;
  - extended: the P4 final runs from the frozen P4 selection.
  The inner searches are not part of any tier.
Evidence: D-002, D-017, D-023, D-042, D-049; DATA_POLICY §3–§5; P7 report §2–§4.
Consequence: public users reproduce the main results without canonical_v1. Private canonical_v1 stays the source of
truth, and the release is a derived, versioned product.
Note (P7 build, 2026-09-14):
- The public P5 plan also drops the P3 run ids and local run paths (`p3_run_id`, `p3_run_dir`); their run ids carry
  run dates. Every other value, and the key types, are unchanged; the build checks this.
- The metadata files are stored byte-exact in Git (`.gitattributes`), because `manifest.json` hashes them.

## D-051 — P7 release-candidate checkpoint tag `p7-release-candidate` (repository metadata only)
Date: 2026-09-14
Status: Accepted
Context:
- RESEARCH_PROTOCOL §5 defined no freeze tag for P7. Its exit criterion "release subset approved" is still a PI
  decision (P7 report §14).
- The research lead decided to mark the completed P7 release-candidate state explicitly before P8, as for P4 (D-046)
  and P6 (D-048).
Decision:
- The annotated tag `p7-release-candidate` (tag object `88c98b3`) was created on the P7 merge commit `c9c15bc` (PR #8)
  and pushed. P8 starts from it (branch `paper/p8-manuscript`).
- **It is a reproducibility checkpoint, not a public release.** It marks the repository state in which
  `public_release_v1` was built, validated and shown to reproduce the P3–P6 results from a clean checkout.
- **Still pending:** the code and data license, the external hosting and DOI, the PI's approval of the release subset
  and of the final release, and the public scope of the absolute dates in committed repository files.
- Protocol v1.0, the splits, canonical_v1, the release package and the P3–P7 results are unchanged. Tags are still
  never moved, deleted or re-pointed.
- RESEARCH_PROTOCOL §5 and CONVENTIONS §6.5 now list the tag.
Evidence: tag `p7-release-candidate` → `c9c15bc3ae67cafe783360011c87e5b6ccdc5daf` locally and on origin; merge
parents `16980ae` (main after P6) and `43e2fec` (P7 branch head); merge tree equal to the P7 branch tree;
`docs/P7_REPRODUCIBILITY_PUBLIC_RELEASE_REPORT.md`, `docs/P7_PUBLIC_RELEASE_CHECKLIST.md`.
Consequence: the P0 and P2–P7 boundaries are tagged. `v1.0-paper` stays reserved for the final validated manuscript
and release state (P8). It may not state that the data are public, that a DOI or license exists, or that the PI has
approved, until each is actually resolved.

## D-052 — Generative-AI disclosure draft and tool inventory (manuscript text only)
Date: 2026-09-14
Status: Superseded by D-053
Context:
- The MDPI template requires Materials and Methods to describe generative-AI use for text, data, graphics, study
  design, data collection, analysis or interpretation, and the Acknowledgments to name the tool, version and purpose
  (`docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md` item 12).
- The research lead set the principles in the P8 final integration pass:
  - disclose the use;
  - never state that a tool decided the protocol or a result;
  - name only tools and versions found in the records, and write `[VERSION TO BE CONFIRMED]` otherwise.
Decision:
- **Inventory:** the local Claude Code session logs of this repository record one tool: Claude Code (Anthropic),
  client versions 2.1.263 and 2.1.270, with the model Claude Opus 5 (`claude-opus-5`). No other AI tool appears in
  the repository or its history. Tools used outside these sessions are left as an author placeholder.
- **Manuscript §3.8:**
  - The stated purposes are code drafting and debugging, analysis-workflow organization and orchestration, research
    documentation, literature screening and reference-metadata checks, manuscript drafting, and language refinement.
  - The protocol, dataset policies, model-selection rules, statistics and interpretation boundaries are stated as
    determined and reviewed by the authors.
  - Executable results are stated as validated independently: tests, frozen-result checks, deterministic tables and
    clean-checkout reproduction.
  - No numerical result was accepted solely from AI output.
- **Acknowledgments:** the MDPI sentence with the inventoried tool, a placeholder for any other tool, and the
  authors' responsibility statement.
Evidence: local session logs (model and client version fields); `git grep` and `git log` over the repository; MDPI
Applied Sciences Word template (read directly, pass 3); `docs/P8_FINAL_BLOCKERS.md` §2.
Consequence: OPEN-28 needs only the PI's approval and the completion of the author placeholder. No result, protocol
or frozen artifact changes.

## D-053 — Generative-AI disclosure with the authors' ChatGPT statement (manuscript text only)
Date: 2026-09-15
Status: Proposed (PI approval pending; OPEN-28 stays open)
Context:
- D-052 inventoried the one tool recorded in this repository's session logs and left other tools as a placeholder.
- In the P8 formatting pass, the research lead stated a second tool:
  - ChatGPT (OpenAI), used for research planning, analysis and protocol review, manuscript architecture, manuscript
    drafting, language refinement and consistency review;
  - its historical model versions were not consistently logged; GPT-5.6 Sol was used in the final
    manuscript-review interaction.
Decision:
- **Acknowledgments:** the research lead's wording, naming both tools:
  - Claude Code (Anthropic; CLI 2.1.263 and 2.1.270; Claude Opus 5), with the purposes recorded in the logs: code
    drafting, debugging, analysis-workflow organization, repository documentation, reference-metadata checks and
    manuscript drafting;
  - ChatGPT (OpenAI), with the stated purposes and the statement that model versions were not consistently logged.
- No historical ChatGPT model version is inferred or added.
- **Manuscript §3.8** lists the combined purposes. It states that protocols, dataset policies, model-selection rules,
  statistics, reported numbers and interpretations stayed under author control and were validated independently.
- **Supersedes D-052:** the inventory and principles are unchanged; only the second tool is added.
Evidence: local Claude Code session logs (D-052); the research lead's statement in the P8 formatting pass; MDPI
Applied Sciences template (item 12 of `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`).
Consequence: the disclosure no longer has an unknown-tool placeholder. OPEN-28 closes only with the PI's approval.

## D-054 — P8 manuscript production conventions and working title
Date: 2026-09-15
Status: Accepted (research lead, P8 formatting pass)
Context: The formatting pass turns the integrated draft into a submission candidate. It must not change any result,
and every printed number must stay traceable.
Decision:
- **Working final title:** "Chronological Personalization under Unseen-Domain Shift: Offset Correction and Negative
  Transfer in Smart-Mat Temperature and Humidity Estimation".
  - "Unseen-domain" is used because subject, recording period, season and device configuration are confounded in
    the strict LOSO folds.
  - The title changes only on PI request, a journal length requirement, or an overclaim found in the final review.
- **Production code:** `src/paper/` with thin scripts:
  - `export_manuscript_tables.py`: Tables 1–5, S1–S19 and cell provenance;
  - `render_manuscript_figures.py`: Figures 1–4 and S1–S4;
  - `build_submission_candidate.py`: the rendered manuscript, numbered references and the staging directory
    `paper/submission_candidate/`;
  - `validate_manuscript_results.py`: read-only checks.
  The frozen `paper/tables/` and `paper/figures/` are inputs only.
- **Precision:** °C and %RH values are printed with two decimals, percentages with one, counts as integers.
  Negative numbers use the typographic minus sign. This is formatting of frozen cells; no value is recomputed.
- **Supplementary tables** are copies of the frozen tables. Calendar night ids are replaced by the night ordinals of
  the frozen trajectory table, and the conversion is checked against the budget definition.
- **References** are rendered from `references.bib` in the MDPI template patterns, numbered by first appearance.
  Journal names are printed in full; ISO 4 abbreviation is a formatting item. The conference entry carries a visible
  `pending` field until its bibliography is confirmed.
- **Byte-exact storage:** `paper/manuscript/generated/**` and `paper/submission_candidate/**` are `-text` in
  `.gitattributes`, as for the release package (D-050), because `MANIFEST.json` hashes them.
Evidence: `docs/P8_TABLE_FIGURE_SELECTION.md` §4–§5; `docs/P8_TITLE_CANDIDATES.md`; the validator output in
`docs/P8_FINAL_BLOCKERS.md`.
Consequence: the candidate is formatting-complete for PI review. No frozen artifact changed. Submission still depends
on the metadata and release blockers.
