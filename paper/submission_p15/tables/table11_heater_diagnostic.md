**Table 11.** Heater-context diagnostic (post hoc, descriptive), temperature. Heater-on windows: labelled windows
within 60 min after a heater-on code, with their share of all labelled windows of the held-out subject (all nights).
η²: the share of the observed temperature variance associated with the three heater contexts (all nights), to three
decimals; η² values are shown as raw-target η² → within-night-centred η². MAE (°C) on the common endpoints of
Table 10: the source-training mean and median, the heater-conditioned source constant and boosting at 900 s.
ΔMAE = MAE(source mean) − MAE(heater-conditioned source constant). Confidence intervals were obtained by the
pre-specified paired night-cluster bootstrap: whole test nights were resampled together with all their windows
(2,000 resamples, 95 % percentile intervals); windows were not resampled individually. The heater-conditioned source
constant is a diagnostic comparator, not an admissible pressure-only estimator: it uses controller codes that may
depend on the measured temperature, and it mixes heater context with the composition of the source subjects.

| Subject | Heater-on windows (share) | η² (raw → within night) | Source mean | Source median | Heater-conditioned source constant | ΔMAE [95 % CI] | Boosting 900 s |
|---|---|---|---|---|---|---|---|
| User01 | 37,750 (13.0 %) | 0.103 → 0.152 | 2.75 | 3.12 | 2.20 | +0.55 [+0.48, +0.62] | 2.18 |
| User02 | 36 (0.03 %) | 0.004 → 0.007 | 4.81 | 4.73 | 4.82 | −0.02 [−0.02, −0.01] | 4.96 |
| User07 | 5,009 (3.6 %) | 0.047 → 0.108 | 2.04 | 1.67 | 1.87 | +0.17 [+0.11, +0.22] | 1.76 |

For User02, η² after additional within-night × mat centring was
0.041; this sensitivity analysis uses a different nuisance adjustment
from the primary within-night value. User02 had heater-on context in only 36
windows, so inference about its heater-on state is very limited.
