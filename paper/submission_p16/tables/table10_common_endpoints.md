**Table 10.** Exploratory analysis (Section 3.5.8), strict leave-one-subject-out evaluation on the endpoints with 40-s,
300-s and 900-s histories available. MAE in °C (temperature) or %RH (humidity) of the source-training mean and median
of the common training endpoints, of the 40-s RAW-TCN retrained on the common endpoints (mean over model seeds 0, 1
and 2, in brackets the seed range) and of histogram gradient boosting on 40-s, 300-s and 900-s pressure summaries.
Every learned model was trained, selected and evaluated on the same common endpoints. †: the night-level paired
bootstrap interval of MAE(source mean) − MAE(model) lies above zero (model seed 0 for the RAW-TCN). Ridge regression,
bias, R, correlations and all intervals: Table S38; the retrained network per seed and its intervals: Tables S39–S40.

| Subject | Target | Common endpoints (windows / nights) | Source mean | Source median | RAW-TCN 40 s, common pool | Boosting 40 s | Boosting 300 s | Boosting 900 s |
|---|---|---|---|---|---|---|---|---|
| User01 | temperature | 139,735 / 137 | 2.75 | 3.12 | 2.55 (2.50–2.64) | 2.61 | 2.18† | 2.18† |
| User02 | temperature | 74,802 / 51 | 4.81 | 4.73 | 5.14 (5.12–5.15) | 5.09 | 5.03 | 4.96 |
| User07 | temperature | 61,782 / 93 | 2.04 | 1.67 | 2.22 (2.12–2.30) | 2.09 | 1.81† | 1.76† |
| User01 | humidity | 139,735 / 137 | 23.65 | 22.23 | 20.45 (19.45–21.42)† | 21.44† | 21.35† | 20.21† |
| User02 | humidity | 74,802 / 51 | 28.76 | 29.37 | 26.96 (26.78–27.12)† | 26.81† | 26.75† | 25.98† |
| User07 | humidity | 61,782 / 93 | 7.92 | 8.30 | 10.68 (10.36–11.02) | 10.31 | 9.74 | 9.58 |

Training-pool sensitivity (Table S38): the RAW-TCN trained on all labelled 40-s windows, evaluated on the same
endpoints, had a temperature MAE of 3.00, 5.02 and
2.19 °C and a humidity MAE of 20.38, 25.93 and
10.33 %RH (User01, User02, User07).
