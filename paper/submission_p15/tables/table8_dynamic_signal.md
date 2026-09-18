| Target | Subject | Model | R | Q | r pooled [95 %] | r within night [95 %] | r within night × mat | R_oracle |
|---|---|---|---|---|---|---|---|---|
| Temperature (°C) | User01 | Base model (b = 0) | 1.83 | 1.59 | +0.06 [+0.01, +0.10] | +0.02 [−0.02, +0.04] | +0.02 | 1.00 |
| Temperature (°C) | User01 | Full fine-tuning (b = 14) | 1.00 | 0.26 | +0.14 [+0.11, +0.22] | −0.00 [−0.03, +0.01] | −0.00 | 0.99 |
| Temperature (°C) | User01 | Scratch control (b = 14) | 0.99 | 0.15 | +0.14 [+0.07, +0.16] | +0.01 [−0.02, +0.03] | +0.01 | 0.99 |
| Temperature (°C) | User02 | Base model (b = 0) | 1.09 | 0.24 | −0.26 [−0.33, −0.19] | −0.28 [−0.36, −0.21] | −0.05 | 0.97 |
| Temperature (°C) | User02 | Full fine-tuning (b = 14) | 0.96 | 0.30 | +0.28 [+0.27, +0.40] | +0.31 [+0.30, +0.43] | +0.09 | 0.96 |
| Temperature (°C) | User02 | Scratch control (b = 14) | 0.94 | 0.26 | +0.36 [+0.32, +0.44] | +0.40 [+0.36, +0.47] | +0.12 | 0.93 |
| Temperature (°C) | User07 | Base model (b = 0) | 1.14 | 0.69 | +0.13 [+0.05, +0.18] | −0.02 [−0.05, +0.02] | −0.02 | 0.99 |
| Temperature (°C) | User07 | Full fine-tuning (b = 14) | 1.02 | 0.13 | −0.11 [−0.18, −0.08] | +0.04 [−0.01, +0.07] | +0.04 | 0.99 |
| Temperature (°C) | User07 | Scratch control (b = 14) | 1.02 | 0.10 | −0.14 [−0.20, −0.07] | +0.04 [−0.02, +0.08] | +0.04 | 0.99 |
| Humidity (%RH) | User01 | Base model (b = 0) | 1.37 | 0.94 | +0.01 [−0.04, +0.04] | −0.02 [−0.03, +0.02] | −0.02 | 1.00 |
| Humidity (%RH) | User01 | Full fine-tuning (b = 14) | 1.32 | 0.72 | −0.15 [−0.24, −0.08] | −0.04 [−0.07, −0.02] | −0.04 | 0.99 |
| Humidity (%RH) | User01 | Scratch control (b = 14) | 1.30 | 0.73 | −0.11 [−0.16, −0.05] | −0.07 [−0.10, −0.04] | −0.07 | 0.99 |
| Humidity (%RH) | User02 | Base model (b = 0) | 1.09 | 0.26 | −0.26 [−0.33, −0.19] | −0.37 [−0.45, −0.30] | −0.11 | 0.97 |
| Humidity (%RH) | User02 | Full fine-tuning (b = 14) | 0.99 | 0.24 | +0.17 [+0.14, +0.29] | +0.27 [+0.25, +0.39] | +0.01 | 0.99 |
| Humidity (%RH) | User02 | Scratch control (b = 14) | 0.97 | 0.25 | +0.24 [+0.17, +0.31] | +0.37 [+0.31, +0.43] | +0.02 | 0.97 |
| Humidity (%RH) | User07 | Base model (b = 0) | 1.23 | 0.73 | +0.02 [−0.08, +0.08] | −0.04 [−0.13, +0.01] | −0.04 | 1.00 |
| Humidity (%RH) | User07 | Full fine-tuning (b = 14) | 1.00 | 0.14 | +0.09 [+0.03, +0.16] | +0.04 [−0.00, +0.12] | +0.04 | 1.00 |
| Humidity (%RH) | User07 | Scratch control (b = 14) | 1.00 | 0.10 | +0.08 [+0.00, +0.15] | +0.06 [−0.00, +0.12] | +0.06 | 1.00 |

Notes:

- Second-order post-hoc diagnostic (Section 3.5.6) on the primary span (nights ≥ 16). R, Q, R_oracle and the correlations are means over model seeds 0, 1 and 2, the values the case classification uses; intervals: model seed 0, 2,000 night-cluster bootstrap resamples.
- R = error SD / target SD and Q = prediction SD / target SD (population SDs), with R² = 1 + Q² − 2·r·Q for the pooled correlation r. r within night: correlation of night-centred predictions and targets (primary tracking diagnostic); r within night × mat: centred within night and mat (differs only for User02, whose two mats share each night).
- R_oracle = √(1 − r²) for the pooled r: the smallest R that an affine recalibration fitted on the same test labels could reach. It is a retrospective oracle, not a result: fitting on test labels would be leakage.
- The base model plus the adaptation offset (D in Table 4) has exactly the base model's values; the constant predictors A and B have R = 1, Q = 0 and undefined correlations. All budgets and seeds: Tables S27–S31.
