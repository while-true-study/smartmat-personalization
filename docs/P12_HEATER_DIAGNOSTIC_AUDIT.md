# P12 audit: heater-context diagnostic (before any P12 result)

Status: read-only audit on `experiment/p12-heater-diagnostic` (child of `experiment/p11-common-pool-tcn`, `933504e`).
No target statistic by heater context was computed to write this document; §5 counts control codes only.

## 1. Governance read

| Source | What it says |
| --- | --- |
| `docs/RESEARCH_PROTOCOL.md` L9 | Inputs must not contain the targets or quantities computed from them, including "heater-control events or set-points (AHON/AHOF, BHSDOWN, BCSUP, FOH, STEMP, SLIMIT, …, which the firmware derives from temperature)". |
| D-038 (closes OPEN-10) | "**Never inputs:** … heater/control events, set-points, limits and modes … heater state inferred from targets". "heater state is not an input covariate; valid targets are kept whatever the control context; heater state between events is not reconstructed; control events serve only event-conditioned stratification or sensitivity (P6) and interpretation." |
| `docs/EXPERIMENT_PROTOCOL.md` §8, §11 | "Never inputs: … heater/control events … heater state". Secondary metrics include "event-conditioned heater-context strata (P6)". |
| `configs/experiments/v1.0/protocol.yaml` L84-94 | `forbidden_fields` (never a model input): `event_raw`, `control_event`, `heater_state`, … |
| `src/evaluation/leakage.py` L19, L254 | The gate rejects any declared input feature whose name contains `event`, `control`, `heater`, `ahon`, … (`TARGET_OR_CONTROL`). It checks **model input feature names**; it does not see or restrict stratification. |
| D-047 A.2 | Operational definition of the heater-context strata, fixed after the P5 results: "the most recent AHON or AHOF control code on the same device within 60 min before the window's target timestamp"; `after_AHON_60min`, `after_AHOF_60min`, `no_AHON_AHOF_60min`; "test-time stratification only, never as inputs, and no heater state is reconstructed". Scope: User02, primary span. |
| D-057 (v1.1) | Reused the P6 heater-context strata; excluded "heater state as an input". |
| D-064 / D-065 (P10) | Summary features exclude "heater"; P10 used **no** heater stratification. D-065: "Not claimed: thermal lag, occupancy effects …"; further experiments not started automatically. |
| D-066 (P11) | Not authorized: any further search. |
| `docs/P8_FINAL_BLOCKERS.md` C6 / OPEN-25 | The GitHub repository is public; session-level calendar dates are a publication blocker. P12 stays local and prints no calendar date. |

### Answers

- **A. Exact rule.** Heater/control fields are forbidden as **predictive model inputs** (L9, D-038, protocol §8,
  `forbidden_fields`, the gate's name check).
- **B. Does it forbid diagnostic stratification?** No. D-038 explicitly keeps control events for "event-conditioned
  stratification or sensitivity (P6) and interpretation", and protocol §11 lists heater-context strata as a secondary
  analysis. What it does forbid is any predictor that consumes heater context. The P12 heater-conditioned constant
  **does** consume it for held-out windows, so it is outside D-038 and needs an explicit **post-hoc diagnostic-only
  exception** (D-067). v1.0 is not edited retroactively.
- **C. Did P10 use heater context?** No. P6 (User02, RQ2 primary span) and the v1.1 post-hoc analyses did.
- **D. Existing definition in code.** `src/evaluation/p6_robustness.py`: `HEATER_CODES = ("AHON", "AHOF")`,
  `HEATER_WINDOW_S = 3600`, `heater_events(subject)` (L287-310) and `heater_context(device, target_ts, events)`
  (L313-326).

## 2. Properties of the existing definition (verified in code)

| Property | Finding |
| --- | --- |
| Same subject | `heater_events(subject)` filters canonical rows by `subject_id` first. User01 and User07 both carry `device_id = "unknown"`, so events must be built **per subject** and applied only to that subject's windows; P12 does that and asserts it. |
| Same mat | events are grouped by `device_id`; `heater_context` assigns labels only where `device == d`. User02's 22480 and 22482 are never mixed. |
| Past only | `k = searchsorted(event_ts, target_ts, side="right") − 1`: the latest event with `event_ts <= target_ts`. An event in the same second as the target row counts as past; a later event is never used. |
| Maximum look-back | `target_ts − event_ts <= 3600` s; otherwise `no_AHON_AHOF_60min`. |
| Several codes in one row | the last AHON/AHOF token of the row wins. |
| Session boundary | **not** applied: the look-back runs over the mat's event stream, so an event up to 60 min earlier in a previous session of the same mat is used. P12 keeps this unchanged and reports how many windows are affected. |
| No recent event | `no_AHON_AHOF_60min` (P12 label `UNKNOWN`). |
| State reconstruction | none. `ON` / `OFF` in P12 mean "the most recent code was AHON / AHOF", not a reconstructed heater state. |

P12 reuses both functions unchanged and maps `after_AHON_60min → ON`, `after_AHOF_60min → OFF`,
`no_AHON_AHOF_60min → UNKNOWN`. New in P12: the same definition is applied to User01 and User07 and to the strict-LOSO
test span (D-047 scoped it to User02's RQ2 primary span).

## 3. Why the comparator can only be a diagnostic

P1 §9: "AHON fires after the temperature has fallen … The controller reacts to temperature, and the control codes are
derived from temperature, so they are inadmissible inputs." A constant conditioned on heater context therefore uses
information derived from the target's own recent past. It can show how much target **level** travels with controller
context; it cannot be an admissible estimator and says nothing causal about the heater.

## 4. Provider legend

The code legend is in a restricted workbook (`docs/initial_dataset_inventory.md` §6.3). The repository documents only:
control codes "describe heater actions and set-point changes (e.g. `BHSDOWN` = judged hot → set-point −0.5 °C, `FOH` =
forced off at ≥ 45 °C)", and `AHON`/`AHOF` as "heater on/off codes" (`docs/P7_PUBLIC_DATA_DICTIONARY.md` §5). No other
meaning is asserted here.

## 5. Control codes in canonical_v1 (primary subjects; events, nights with the code / nights of the stream)

| Code | Class | Basis | User01 | User02 22480 | User02 22482 | User07 |
| --- | --- | --- | --- | --- | --- | --- |
| AHON | heater ON | documented ("heater on/off codes") | 1,395; 139/151 | 39; 33/45 | 122; 44/50 | 271; 90/100 |
| AHOF | heater OFF | documented | 1,408; 140/151 | 39; 33/45 | 117; 44/50 | 266; 83/100 |
| BHSDOWN | set-point | documented (judged hot → −0.5 °C) | 3,990; 141/151 | 608; 33/45 | 944; 43/50 | 1,570; 83/100 |
| FOH | forced OFF | documented (forced off at ≥ 45 °C) | – | – | 4; 1/50 | – |
| BCSUP, BHNTSDOWN, STEMP, SLIMIT, SMINLIMIT, EVENT:BURST_HOT_STEP_DOWN | set-point / limit | name only — **ambiguous** | 917; 132; 204; 44; 75; 29 | –; –; –; 4; –; – | –; –; 5; 10; –; – | 101; 37; –; –; 17; – |
| FON, FOF, EVENT:FORCED_ON, EVENT:FORCED_OFF, MON, MOF, AIHON, AIHOFF | heating-related on/off | name only — **ambiguous** | FON 6, FOF 98, FORCED_ON 9, FORCED_OFF 25, MON 2, MOF 3, AIHON 4 | FON 4, FOF 38 | FON 7, FOF 71, AIHON 15, AIHOFF 14 | FON 1, FOF 128, MON 1, AIHON 3, AIHOFF 1 |
| AMODE, MMODE, AIDONE, SCHATIDS, WSTOP | controller / mode | name only — **ambiguous** | 12; 9; 23; –; 10 | – | 22; –; –; 2; 3 | 12; 1; 34; 13; – |

Only AHON and AHOF enter the P12 heater context, exactly as in D-047. The ambiguous codes are **not** reinterpreted
and not added after the fact; in particular FOF (335 events) may also switch the heater off, which is a stated limit.

## 6. Reusable code

`p6_robustness.heater_events`, `p6_robustness.heater_context`, `P5.P5Session` / `loso_data.fold_data` (frozen windows and
partitions), `p10_history.build_subject` and `p11_common_pool_tcn.common_mask` / `pools` (common endpoints),
`LB.constants`, `p10_history.metric_row`-style metrics via `p10_level_baselines.point_metrics`,
`p10_history.bootstrap_rows` (night-cluster paired bootstrap), `P6.resample_counts` / `P6.interval`, the `io_guard`
writers.

## 7. Risks and how they are closed

| Risk | Closure |
| --- | --- |
| Future heater event used | the frozen `searchsorted(..., side="right") − 1` rule; a P12 test with a future event |
| Events of another mat or subject | per-subject event tables; per-device masks; tests for mat and subject isolation |
| Held-out labels in the constants | constants are computed on `partition == "train"` windows only; `pools` fails closed; a test |
| Definition tuned after results | definition, UNKNOWN rule, η² thresholds and cases fixed in the plan; plan/config SHA-256 written before the first result and checked at the end |
| Heater context leaks into a model | no model is fitted; nothing is passed to the leakage-gated trainers; the module imports no trainer |
| Existing artifacts changed | SHA-256 of P3 / P10 / P11 outputs and paper tables before and after |
| Calendar dates in committed files | night identifiers stay inside git-ignored outputs; documents carry none |

## 8. Verdict

Stratification by heater context is inside the protocol; the heater-conditioned constant is not and is run only under
the D-067 diagnostic-only exception. No obstacle to the descriptive analysis.
