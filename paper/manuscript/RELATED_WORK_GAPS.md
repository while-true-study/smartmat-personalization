# Related work — literature gaps

> **No reference has been searched or verified yet.**
> - The manuscript uses `[CITE: <topic>]` placeholders until a reference is found, read and checked (authors, title,
>   venue, year, DOI).
> - Nothing is cited from memory, and no DOI, title or year is invented.
> - Verified entries go into `references.bib` with the claim they support.

| # | Topic | What the manuscript needs it for | Manuscript section | Search terms (starting point) | Status |
|---|---|---|---|---|---|
| 1 | Smart bedding and pressure-mat sensing | context: unobtrusive in-bed sensing with pressure arrays (sleep, posture, occupancy) | §1, §2.1 | smart mattress, pressure sensor mat, bed sensor, sleep monitoring pressure | not searched |
| 2 | Indirect estimation of temperature / humidity (bed microclimate, soft sensing) | prior approaches to estimating environmental quantities from other sensors; the bed microclimate | §1, §2.2 | bed microclimate, virtual sensor, soft sensor temperature humidity, indirect estimation | not searched |
| 3 | TCN for sensor time-series regression | the model family; causal dilated convolutions | §2.3, §3.4 | temporal convolutional network, sequence modelling, sensor regression | not searched |
| 4 | Cross-subject generalization and domain shift in wearable / ambient sensing; leave-one-subject-out | why strict LOSO; heterogeneity between subjects and domains | §1, §2.4, §6 A | leave-one-subject-out, cross-subject generalization, domain shift sensor, subject variability | not searched |
| 5 | Personalization and subject adaptation | fine-tuning with a user's own data after deployment; limited-data adaptation | §1, §2.5 | personalization, user adaptation, subject-specific fine-tuning, few-shot adaptation sensor | not searched |
| 6 | Negative transfer | adaptation that hurts; definitions | §2.5, §6 C | negative transfer, transfer learning failure | not searched |
| 7 | Temporal concept drift | non-stationarity within a user; drift detection | §1, §2.6, §6 D, G | concept drift, temporal drift, non-stationary sensor data | not searched |
| 8 | Calibration / domain-level bias correction | offset correction as a simpler alternative (untested here) | §2.6, §6 A, G | domain-level bias, calibration transfer, offset correction, recalibration | not searched |
| 9 | Leakage in evaluation (splits before windowing, subject leakage) | justification of the leakage gate and of splitting before windowing | §4.1 | data leakage cross-validation time series, subject leakage | not searched |
| 10 | Cluster / block bootstrap for dependent data | the night-level paired cluster bootstrap; its limits under serial dependence | §4.4, §7 | cluster bootstrap, block bootstrap, dependent data | not searched |
| 11 | The authors' conference paper | prior work and extension | §1 | — | details from the PI: [ICFICE CITATION] |

**Candidate sources found in the conference paper's reference list.** These are not yet verified and are not in
`references.bib`:
- the generic convolutional-vs-recurrent sequence-modelling evaluation by Bai, Kolter and Koltun (arXiv, 2018), for
  topic 3 (TCN);
- the international pressure ulcer/injury prevention and treatment clinical practice guideline (NPIAP, EPUAP, PPPIA;
  3rd ed., 2019), for the Introduction's motivation;
- a movement-score late-fusion temperature/humidity regression manuscript by Lee, Kim and Bang (listed as unpublished,
  2025). It can be cited only if the PI confirms its status.
Each must be checked against the original source before use.

**Rules for the literature pass:**
- Prefer peer-reviewed sources and read at least the abstract and method of each.
- Record the claim each reference supports.
- Do not use "first" or "novel" in the manuscript unless the verified literature supports it.
