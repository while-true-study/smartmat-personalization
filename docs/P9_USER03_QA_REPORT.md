# P9 — User03 external-validation artifact: QA report (protocol v1.3, D-061, D-062)

> **Status:** written from the reconstruction and windowing outputs **before any model output on User03 was
> computed**. No target value is summarised here; only counts and validity flags.
> - Generated blocks: `scripts/build_p9_user03.py` (tables from `outputs/metrics/p9_user03/p9_user03_qa_*.csv`).
> - Nights are numbered 1–7 in time order; no calendar date appears.
> - **Timestamp validity confirmed (D-062, 2026-09-16):** the data provider confirmed that the setting problem
>   behind the D-017 exclusion does not affect the second-level timestamps of the seven paired TXT nights.
>   OPEN-29 is closed and these results are no longer conditional. No count or flag in this report changed.

## 1. Sources (hash-verified)

<!-- BEGIN GENERATED P9QA:sources -->

| Night | Role | File id | SHA-256 (first 12) | Layout | Data rows | Non-data lines |
|---|---|---|---|---|---|---|
| 1 | csv | rf_c72768b318 | e752e8b384b0 | csv | 19024 | header 1, nvs_log 14 |
| 1 | txt | rf_2944020ba0 | 5ae65cc15d88 | dot_p2_p6 | 20060 | nvs_log 14 |
| 2 | csv | rf_472f51ed15 | 9d774f21c13c | csv | 14518 | header 1, nvs_log 3 |
| 2 | txt | rf_1fb716dd00 | 58bb113ab41d | dot_p2_p6 | 17478 | nvs_log 6 |
| 3 | csv | rf_f035bd1571 | e2946d520330 | csv | 13402 | header 1, nvs_log 4 |
| 3 | txt | rf_0b4ddadd99 | 7cbbca907730 | dot_p2_p6 | 14817 | blank 120, crash_dump 190, device_log 96, nvs_log 17 |
| 4 | csv | rf_d2e74f5942 | 69e77bf246e6 | csv | 15717 | header 1, nvs_log 23 |
| 4 | txt | rf_8c0064f0b6 | 427e64008dfa | dot_p2_p6 | 15717 | nvs_log 23 |
| 5 | csv | rf_3cf412a98b | f9953d815e0e | csv | 15076 | header 1, nvs_log 35 |
| 5 | txt | rf_ab6b6cd91c | bf6ff33911c5 | dot_p2_p6 | 15260 | nvs_log 39 |
| 6 | csv | rf_40880f4fea | 8147f080ce59 | csv | 14531 | header 1, nvs_log 5 |
| 6 | txt | rf_7a1b82ea57 | 6e8c763d03a1 | dot_p2_p6 | 14531 | nvs_log 5 |
| 7 | csv | rf_5cad1a3c7b | ed1fa26d51d8 | csv | 14988 | header 1, nvs_log 2 |
| 7 | txt | rf_f49bb1007e | 95b1867d6dc5 | comma_p1_p6 | 15250 | nvs_log 2 |

<!-- END GENERATED P9QA:sources -->

## 2. Minute reconciliation coverage

The rule was fixed in the plan (`docs/P9_USER03_EXTERNAL_VALIDATION_PLAN.md` §4) before this run: one paired file per
source, equal row counts, identical compared fields in file order, non-decreasing TXT seconds, events equal up to
punctuation, and the provider-annotated error minute excluded. No row was interpolated, imputed, re-timed or joined
by nearest neighbour.

<!-- BEGIN GENERATED P9QA:coverage -->

**Minutes / CSV rows / TXT rows per night and category.**

| Night | included | csv_only | txt_only | ambiguous_source | provider_annotated_error | count_mismatch | value_mismatch | txt_time_order_violation | event_text_mismatch |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 722 / 19011 / 19011 | — | 38 / 0 / 1022 | — | — | 1 / 13 / 27 | — | — | — |
| 2 | 557 / 14502 / 14502 | — | 122 / 0 / 2950 | — | — | 1 / 16 / 26 | — | — | — |
| 3 | 636 / 13395 / 13395 | — | 60 / 0 / 1386 | — | 1 / 5 / 12 | 1 / 2 / 24 | — | — | — |
| 4 | 799 / 15717 / 15717 | — | — | — | — | — | — | — | — |
| 5 | 841 / 15066 / 15066 | — | 10 / 0 / 175 | — | — | 1 / 10 / 19 | — | — | — |
| 6 | 764 / 14531 / 14531 | — | — | — | — | — | — | — | — |
| 7 | 778 / 14970 / 14970 | — | 13 / 0 / 258 | — | — | 1 / 18 / 22 | — | — | — |

- Included CSV rows: 107192 of 107256 (99.94 %); minutes by category: included 5097, csv_only 0, txt_only 243, ambiguous_source 0, provider_annotated_error 1, count_mismatch 5, value_mismatch 0, txt_time_order_violation 0, event_text_mismatch 0.
- Rows included with a punctuation-only event difference: 1.
- Dot-fused value audit (nights 1–6): 92222 of 92222 audited rows equal the CSV P1 (audit only).

<!-- END GENERATED P9QA:coverage -->

## 3. Canonical processing and windows

<!-- BEGIN GENERATED P9QA:windows -->

- Reconstructed rows 107192; canonical rows after the canonical_v1 rules 107192 (exact-copy removal 0).
- Windows 13753, labelled 13749; nights with labelled windows 7.

| Night | Windows | Labelled windows | Sessions | ≥ 10 labelled windows |
|---|---|---|---|---|
| 1 | 2148 | 2148 | 1 | yes |
| 2 | 1614 | 1614 | 1 | yes |
| 3 | 1600 | 1600 | 1 | yes |
| 4 | 2324 | 2323 | 1 | yes |
| 5 | 1899 | 1897 | 1 | yes |
| 6 | 2072 | 2071 | 1 | yes |
| 7 | 2096 | 2096 | 1 | yes |

<!-- END GENERATED P9QA:windows -->

## 4. Reading

- **Coverage:** almost every row of the valid User03 CSV export passed the reconciliation. The excluded CSV rows
  lie in a few count-mismatch minutes and in the provider-annotated error minute. The TXT-only minutes are TXT
  recording beyond the CSV export, which cannot be corroborated. No value mismatch, TXT ordering violation or event
  text mismatch occurred.
- **Dot-fused value audit:** the value fused to the seconds in the TXT files of nights 1–6 equalled the CSV P1 in
  every audited row. As fixed in the plan, it is recorded as an audit and is not used.
- **Canonical rules:** no exact-copy block was removed (D-014). Each night forms one session.
- **Nights and windows:** every night has labelled windows. The night count is below the P6 minimum of 10 nights
  for night-cluster intervals, so, as pre-specified, the external results are reported without night-bootstrap
  intervals, with seed ranges and per-night results instead.
