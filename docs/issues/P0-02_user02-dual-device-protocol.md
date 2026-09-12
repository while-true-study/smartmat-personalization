# [P0] Clarify User02 dual-device recording protocol

> Issue draft (GitHub CLI was not available when this was written). File it on GitHub with this title
> and body, then replace the "Tracking" cells of OPEN-02 and OPEN-03 in `docs/DECISIONS.md` with the
> issue link.

**Phase:** P0 — Dataset Audit & Data Freeze · **Open decisions:** OPEN-03, OPEN-02 · **Type:** device provenance / recording protocol

## Evidence
From the initial inventory (`docs/initial_dataset_inventory.md` §7.4, §8.1), read-only analysis:
- Mats 22480 and 22482 are confirmed devices of the same subject, User02 (D-003).
- Their recordings overlap in time on most nights: 53 file pairs, about 505 h of overlap in total
  (253 h of minutes with rows from both devices).
- In jointly recorded minutes, both mats register occupancy (firmware movement label ≠ `NM`) 66.8 % of
  the time; only 22480 23.3 %; only 22482 7.8 %.
- Same-minute temperature differs by a median −2 °C (correlation 0.28) and humidity by −19 %RH
  (22480 minus 22482), so the sensors do not share one microclimate.
- 22480 records mostly 19:00–06:00; 22482 often records around the clock.
- Two files in the 22480 archive carry the `sm22482_` prefix and a `smartmat_22482` JSON root key. They
  cover the only two dates (2026-08-24/25) for which 22480 has a file and 22482 does not, and they
  overlap 22480's own files for those dates with no shared rows. They are quarantined (D-006).

## Research impact
- Two concurrent streams from one person cannot be treated as independent sessions. If one device's
  night were in training and the other's in test, the model would be tested on the same night it trained
  on (RESEARCH_PROTOCOL L8).
- The analysis unit for User02 is undefined: separate streams, one selected device, or a fused
  12-channel recording each lead to different models and results.
- Different T/H levels per device mean the regression target itself differs by device.
- The two quarantined files (22,205 rows) cannot be used until their device is known.

## Required clarification (data provider)
1. How were the two mats placed during recording (same bed / different body regions / side by side /
   different rooms or beds)?
2. Was User02 the only person on both mats? Did anyone else use either mat during 2026-07-19 → 09-11?
3. Where were the temperature/humidity sensors of each mat located?
4. Which device recorded the files `sm22482_0824` and `sm22482_0825` stored in the 22480 archive?
5. Why does 22482 often record around the clock while 22480 records mostly at night?

## Blocking decision
- OPEN-03 → decision on how User02's concurrent streams are used and grouped.
- OPEN-02 → device attribution of the two quarantined files.
Blocks: User02 inclusion in the primary cohort (OPEN-16); session definition for User02 (OPEN-06).

## Handling until resolved
Subject mapping stays fixed (User02 = {22480, 22482}). Quarantined files remain excluded. P0 analysis A2
(`docs/P0_DATASET_AUDIT_PLAN.md`) quantifies co-occupancy, simultaneous movement and device signatures
reproducibly.
