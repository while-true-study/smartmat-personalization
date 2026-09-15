| Representation | Temperature MAE (°C) | Δ vs RAW, °C (improved) | Fold–seed pairs improved; Δ range, °C | Humidity MAE (%RH) | Δ vs RAW, %RH (improved) | Fold–seed pairs improved; Δ range, %RH | User02 bias, °C | User02 bias, %RH |
|---|---|---|---|---|---|---|---|---|
| Training-mean predictor | 3.05 | — | — | 19.56 | — | — | −4.59 | −27.49 |
| RAW (reference) | 3.33 | — | — | 18.28 | — | — | −4.82 | −24.17 |
| MOVEMENT | 3.09 | −0.25 (3/3) | 9/9; −0.54 to −0.04 | 19.61 | +1.33 (1/3) | 3/9; −0.41 to +3.52 | −4.73 | −26.49 |
| CONTACT | 3.24 | −0.09 (3/3) | 7/9; −0.37 to +0.10 | 18.01 | −0.27 (2/3) | 4/9; −2.06 to +0.97 | −4.81 | −24.14 |
| RAW+MOVEMENT | 3.12 | −0.21 (3/3) | 8/9; −0.86 to +0.01 | 18.38 | +0.09 (1/3) | 3/9; −1.47 to +2.28 | −4.75 | −23.97 |
| RAW+CONTACT | 3.36 | +0.03 (1/3) | 3/9; −0.18 to +0.26 | 17.73 | −0.55 (3/3) | 7/9; −2.37 to +0.53 | −4.77 | −23.83 |
| RAW+MOVEMENT+CONTACT | 3.30 | −0.03 (2/3) | 5/9; −0.32 to +0.22 | 18.00 | −0.28 (2/3) | 6/9; −1.47 to +1.28 | −4.69 | −23.62 |

Notes:

- Secondary analysis (RQ3).
- MAE: unweighted mean across three held-out subjects of the seed means (seeds 0, 1, 2); descriptive.
- Δ vs RAW = family MAE − RAW MAE (negative = lower error); in brackets the number of subjects, of three, whose MAE improved.
- Seed variation: the family is compared with RAW separately for each held-out subject and model seed (nine fold–seed pairs, same seed for both); the column gives the pairs with a lower MAE and the smallest and largest per-pair Δ.
- Each representation has its own pre-declared nested selection; the comparison is between selected representations, not a fixed-model ablation.
- User02 bias (predicted − observed) shows the domain-level offset that remains in every representation.
- Per-subject values, RMSE and all pre-declared comparisons: Tables S4–S7.
