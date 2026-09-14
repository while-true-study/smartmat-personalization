| Target | Subject | Quantity | b = 0 | b = 1 | b = 3 | b = 7 | b = 14 |
|---|---|---|---|---|---|---|---|
| Temperature (°C) | User01 | MAE | 3.09 ± 0.26 | 3.14 ± 0.31 | 2.85 ± 0.10 | 2.31 ± 0.10 | 1.75 ± 0.05 |
| Temperature (°C) | User01 | G_b, % (seeds improved) | — | −1.7 (0/3) | +7.7 (3/3) | +25.5 (3/3) | +43.3 (3/3) |
| Temperature (°C) | User02 | MAE | 5.06 ± 0.07 | 4.34 ± 0.03 | 2.76 ± 0.32 | 1.96 ± 0.04 | 1.55 ± 0.03 |
| Temperature (°C) | User02 | G_b, % (seeds improved) | — | +14.3 (3/3) | +45.5 (3/3) | +61.3 (3/3) | +69.4 (3/3) |
| Temperature (°C) | User07 | MAE | 1.89 ± 0.16 | 2.16 ± 0.01 | 2.37 ± 0.00 | 2.33 ± 0.01 | 2.36 ± 0.01 |
| Temperature (°C) | User07 | G_b, % (seeds improved) | — | −14.4 (0/3) | −25.0 (0/3) | −23.3 (0/3) | −25.0 (0/3) |
| Temperature (°C) | Unweighted mean across three held-out subjects | MAE | 3.35 | 3.22 | 2.66 | 2.20 | 1.89 |
| Humidity (%RH) | User01 | MAE | 20.68 ± 1.34 | 27.83 ± 2.28 | 34.19 ± 1.22 | 29.95 ± 0.51 | 16.03 ± 0.42 |
| Humidity (%RH) | User01 | G_b, % (seeds improved) | — | −34.6 (0/3) | −65.3 (0/3) | −44.8 (0/3) | +22.5 (3/3) |
| Humidity (%RH) | User02 | MAE | 21.98 ± 0.50 | 17.29 ± 0.45 | 12.70 ± 0.84 | 14.99 ± 0.21 | 12.23 ± 0.16 |
| Humidity (%RH) | User02 | G_b, % (seeds improved) | — | +21.4 (3/3) | +42.2 (3/3) | +31.8 (3/3) | +44.3 (3/3) |
| Humidity (%RH) | User07 | MAE | 10.25 ± 0.30 | 8.56 ± 0.06 | 8.35 ± 0.05 | 8.38 ± 0.03 | 8.28 ± 0.01 |
| Humidity (%RH) | User07 | G_b, % (seeds improved) | — | +16.5 (3/3) | +18.6 (3/3) | +18.2 (3/3) | +19.2 (3/3) |
| Humidity (%RH) | Unweighted mean across three held-out subjects | MAE | 17.64 | 17.89 | 18.41 | 17.77 | 12.18 |

Notes:

- Primary test span: nights ≥ 16, identical for every budget b; b = 0 is the base model on this span (it differs from Table 2, which covers all nights).
- MAE: mean ± standard deviation over model seeds 0, 1 and 2.
- G_b = (MAE_0 − MAE_b) / MAE_0 × 100 %, from the seed-mean MAE; G_b > 0 is an improvement and G_b < 0 is negative transfer (the adapted model is worse than its own base model on the same nights). In brackets: seeds, of three, with G_b > 0.
- The unweighted mean across three held-out subjects is descriptive, not a population estimate. Bias and RMSE by budget: Table S10.
