| Target | Subject | MAE, B: adaptation-target mean | MAE, E: full fine-tuning | MAE, S: scratch control | Δ B − E | Δ D − E | Δ S − E | Δ B − S |
|---|---|---|---|---|---|---|---|---|
| Temperature (°C) | User01 | 1.87 | 1.75 ± 0.05 | 1.78 ± 0.01 | +0.16 [+0.11, +0.21] +/+/+ | +0.75 [+0.58, +0.91] +/+/+ | +0.06 [+0.03, +0.08] +/−/+ | +0.10 [+0.07, +0.13] +/+/+ |
| Temperature (°C) | User02 | 1.49 | 1.55 ± 0.03 | 1.57 ± 0.05 | −0.04 [−0.10, +0.02] 0/0/− | +0.09 [−0.00, +0.17] 0/0/0 | −0.01 [−0.02, +0.00] 0/+/0 | −0.03 [−0.10, +0.04] 0/−/− |
| Temperature (°C) | User07 | 2.33 | 2.36 ± 0.01 | 2.36 ± 0.03 | −0.04 [−0.06, −0.03] −/−/− | −0.29 [−0.47, −0.11] −/−/− | +0.00 [−0.01, +0.01] 0/−/+ | −0.04 [−0.06, −0.03] −/0/− |
| Humidity (%RH) | User01 | 19.09 | 16.03 ± 0.42 | 15.76 ± 0.31 | +3.31 [+2.75, +3.85] +/+/+ | +3.55 [+2.93, +4.16] +/+/+ | +0.10 [−0.11, +0.32] 0/−/+ | +3.20 [+2.81, +3.59] +/+/+ |
| Humidity (%RH) | User02 | 13.42 | 12.23 ± 0.16 | 11.55 ± 0.28 | +1.35 [+1.03, +1.65] +/+/+ | +2.64 [+2.25, +3.03] +/+/+ | −0.20 [−0.31, −0.08] −/−/− | +1.55 [+1.19, +1.89] +/+/+ |
| Humidity (%RH) | User07 | 8.29 | 8.28 ± 0.01 | 8.28 ± 0.01 | +0.02 [−0.06, +0.11] 0/0/0 | +2.20 [+1.34, +3.04] +/+/+ | +0.02 [−0.02, +0.05] 0/0/0 | +0.01 [−0.06, +0.07] 0/0/0 |

Notes:

- Post-hoc analysis (Section 3.5.5) at b = 14 on the primary span (nights ≥ 16). MAE in °C (temperature) or %RH (humidity); neural models: mean ± standard deviation over model seeds 0, 1 and 2.
- Δ X − Y = MAE(X) − MAE(Y): Δ > 0 means that Y has the lower error. Seed 0: full-sample point estimate and 95 % interval from 2,000 paired night-cluster bootstrap resamples (the Table 5 procedure, with the same resampled nights). Then the side of zero for seeds 0 / 1 / 2: + above zero, − below zero, 0 includes zero.
- D: RAW-TCN base plus the adaptation-window offset (Table 4). S: randomly initialised RAW-TCN of the same architecture, trained on nights 1–14 with the full fine-tuning recipe; only the initialisation differs from E. It is an initialization control, not an upper bound on within-subject learning.
- The intervals describe within-subject night-level uncertainty, not population-level statistical significance. All budgets: Table S25.
