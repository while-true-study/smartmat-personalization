| Target | Predictor | MAE [seed range] | RMSE | Bias | R | Q | r pooled | r within night |
|---|---|---|---|---|---|---|---|---|
| Temperature (°C) | Training-mean predictor | 2.43 | 2.62 | −2.43 | 1.00 | 0.00 | NA | NA |
| Temperature (°C) | RAW-TCN, fold-1 configuration | 2.72 [2.69–2.79] | 2.94 | −2.69 | 1.20 | 0.65 | −0.01 | −0.00 |
| Temperature (°C) | RAW-TCN, fold-2 configuration | 2.57 [2.50–2.65] | 2.81 | −2.50 | 1.29 | 0.78 | −0.01 | −0.01 |
| Temperature (°C) | RAW-TCN, fold-3 configuration | 2.72 [2.60–2.85] | 2.95 | −2.70 | 1.19 | 0.66 | +0.01 | +0.01 |
| Humidity (%RH) | Training-mean predictor | 12.85 | 13.44 | −12.85 | 1.00 | 0.00 | NA | NA |
| Humidity (%RH) | RAW-TCN, fold-1 configuration | 20.52 [20.38–20.65] | 22.14 | −20.49 | 2.12 | 1.92 | +0.05 | +0.09 |
| Humidity (%RH) | RAW-TCN, fold-2 configuration | 19.67 [19.24–20.15] | 21.88 | −19.51 | 2.51 | 2.35 | +0.05 | +0.09 |
| Humidity (%RH) | RAW-TCN, fold-3 configuration | 20.83 [20.58–20.98] | 22.74 | −20.79 | 2.34 | 2.15 | +0.04 | +0.07 |

Notes:

- Additional external validation (post hoc, Section 3.5.7): one further subject, not part of the primary cohort, evaluated on all its labelled 40-s windows. These results are not pooled with the three primary subjects.
- Models trained on all labelled windows of the three primary subjects: the training-mean predictor and the three frozen RAW-TCN configurations of the strict leave-one-subject-out folds, each with its frozen epoch count; RAW-TCN values are means over model seeds 0, 1 and 2, in brackets the seed range of MAE.
- R = error SD / target SD, Q = prediction SD / target SD (population SDs); r within night: correlation of night-centred values. The constant predictor has R = 1, Q = 0 and undefined correlations.
- With fewer than 10 nights, no night-bootstrap interval is computed (P6 rule). MAE, RMSE and bias in °C (temperature) or %RH (humidity). Coverage, per-seed and per-night results: Tables S32–S34.
