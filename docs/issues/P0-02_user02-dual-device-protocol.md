# [P0] Clarify User02 dual-device recording protocol

> Issue draft (GitHub CLI was not available when this was written). File it on GitHub with this title
> and body, then replace the "Tracking" cells of OPEN-02 and OPEN-03 in `docs/DECISIONS.md` with the
> issue link.

**Phase:** P0 — Dataset Audit & Data Freeze · **Open decisions:** OPEN-03, OPEN-02 · **Type:** device provenance / recording protocol
**Status:** evidence quantified (P0-A1, P0-A2, 2026-09-12); placement, use policy and file attribution await the data provider

## Evidence
Reproducible analysis P0-A2 (`docs/P0_A2_USER02_DEVICE_REPORT.md`, code `scripts/audit_user02_devices.py`), read-only:
- Mats 22480 and 22482 are confirmed devices of the same subject, User02 (D-003). Both sample at a nominal 3 s
  with ±1–2 s jitter.
- **Simultaneous recording:** 253 h on 46 dates, i.e. 76 % of 22480's recording time and 51 % of 22482's.
  Rows are not sample-synchronous: 31 % have an exact same-second counterpart, 89 % within ±1 s, 99.8 % within ±3 s.
- **No pressure coupling:**
  - pressure sum, spread, active channels and frame-to-frame change are uncorrelated between the mats
    (|r| ≤ 0.03), with no peak at any lag within ±30 s;
  - large movements on one mat coincide with movements on the other only at chance level (lift 0.74–1.00
    against a ±24 h control);
  - a scan over ±12 h, pooled and per date, finds no clock offset that would hide coupling.
- **Occupancy:** "both mats active" ranges from 18 % to 90 % depending on the occupancy definition, but agreement
  beyond chance is absent under all 14 definitions (Cohen's κ −0.07 … 0.00). The previously quoted 66.8 % is the
  firmware-label value (67.2 % in A2).
- **T/H:** 22480 − 22482 median differences are −2 °C and −19 %RH (reproduced exactly). Humidity is lower on 22480
  on all 46 dates, by −4 to −27 %RH depending on the period. 22480's temperature is almost constant (28–30 °C),
  while 22482's varies (29–35 °C).
- **Recording hours:** both devices record at night. 22480 covers ~19:00–06:00 and 22482 ~20:00–09:00. Daytime
  recording is rare (0.3 % / 2.4 %). *Correction:* the earlier statement that 22482 "often records around the
  clock" came from multi-night file spans and was wrong.
- **Quarantined files (`sm22482_0824`, `sm22482_0825`, stored in the 22480 archive):** filename prefix and JSON
  root key say 22482. They fill 22482's timeline seamlessly (start 30 min after 22482's last row, end 3 s before
  its next row). They record simultaneously with 22480's own stream for 7 h (with no shared rows) and match
  22482's humidity regime. Only their storage location points to 22480.

Interpretation limited to the data: in the recorded data **the two mats do not register the same body
movements at the same time**, and they measure systematically different temperature/humidity. The data cannot
say why.

## Research impact
- The two streams must stay in the same evaluation fold (RESEARCH_PROTOCOL L8): 253 h of simultaneous recording.
- Fusing both mats into one 12-channel "body" recording is not supported by the data as they stand. Device
  behaves as a separate domain within User02 for both inputs (channel-load pattern) and targets (T/H offset).
- User02's use in the primary cohort depends on the answers below (pool both devices, choose one, or treat them
  as two within-subject domains — to be decided in P2 after confirmation).
- The two quarantined files (22,205 rows) cannot be used until their device is confirmed.

## Required clarification (data provider)
1. How were the two mats placed during 2026-07-19 → 09-11: same surface, different body regions, side by side,
   or different beds or rooms? The data show no simultaneous movement on both mats.
2. Was User02 the only person, and was nothing else, on either mat during that period?
3. Where was the temperature/humidity sensor of each mat located, and did the heater settings or control mode
   differ between the two mats?
4. Which device recorded `sm22482_0824` and `sm22482_0825`? The evidence favours 22482.
5. Are device timestamps wall-clock time from a synchronised clock, or device-local time?

## Blocking decision
- OPEN-03 → decision on how User02's concurrent streams are used (both / one / separate domains). Grouping is
  already fixed at subject level.
- OPEN-02 → device attribution of the two quarantined files.
Blocks: final User02 role in the primary cohort (OPEN-16); session definition for User02 (OPEN-06).

## Handling until resolved
Subject mapping unchanged (User02 = {22480, 22482}); device attribution of the quarantined files stays
`unresolved`. No device selection, fusion, calibration or filtering is applied.
