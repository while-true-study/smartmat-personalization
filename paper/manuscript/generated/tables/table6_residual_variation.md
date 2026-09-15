| Target | Subject | Strict LOSO: target SD | Strict LOSO: R, RAW-TCN | Primary span: target SD | R, base (b = 0) | R, full fine-tuning (b = 14) | R, scratch control (b = 14) |
|---|---|---|---|---|---|---|---|
| Temperature (°C) | User01 | 1.78 | 1.86 (1.73–2.00) | 1.77 | 1.83 (1.70–1.96) | 1.00 (0.99–1.01) | 0.99 (0.99–0.99) |
| Temperature (°C) | User02 | 1.94 | 1.08 (1.07–1.08) | 1.71 | 1.09 (1.08–1.09) | 0.96 (0.94–0.98) | 0.94 (0.93–0.95) |
| Temperature (°C) | User07 | 1.87 | 1.12 (1.09–1.14) | 1.81 | 1.14 (1.11–1.16) | 1.02 (1.02–1.02) | 1.02 (1.02–1.02) |
| Humidity (%RH) | User01 | 10.68 | 1.25 (1.21–1.29) | 8.58 | 1.37 (1.30–1.45) | 1.32 (1.26–1.37) | 1.30 (1.29–1.31) |
| Humidity (%RH) | User02 | 14.49 | 1.10 (1.10–1.11) | 13.76 | 1.09 (1.09–1.10) | 0.99 (0.98–1.00) | 0.97 (0.97–0.97) |
| Humidity (%RH) | User07 | 9.37 | 1.26 (1.23–1.28) | 9.74 | 1.23 (1.19–1.26) | 1.00 (1.00–1.00) | 1.00 (1.00–1.00) |

Notes:

- Post-hoc analysis (Section 3.5.5). R = error SD / target SD, with population standard deviations (error = predicted − observed); R is a descriptive ratio of residual to target variation, not explained variance.
- A constant predictor (the training mean A or the adaptation-target mean B) has R = 1 by construction, and a constant offset leaves R unchanged (D has the R of C). R < 1 means less residual variation than a constant predictor; R > 1 means more.
- Strict LOSO: all labelled windows of the held-out subject (the Table 2 setting). Primary span: nights ≥ 16. Target SD in °C (temperature) or %RH (humidity).
- Neural models: mean over model seeds 0, 1 and 2, in brackets the seed range. Scratch control: the same architecture and fine-tuning recipe as full fine-tuning, randomly initialised and trained on nights 1–14 only. All values: Table S23.
