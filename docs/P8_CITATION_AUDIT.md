# P8 — Claim-to-citation audit

> **Every sentence in `paper/manuscript/manuscript.md` that cites an external source** (53 cited lines, extracted
> mechanically), and every uncited external claim found on reading, was checked against the evidence in
> `docs/P8_LITERATURE_EVIDENCE_MATRIX.md`, on 2026-09-14.
> - **Status:** PASS = supported by the cited abstract (or full text where stated); WEAK = supported only in part;
>   UNSUPPORTED = not supported.
> - Every WEAK or UNSUPPORTED item was reworded, re-cited or removed before this audit was committed. The *Action*
>   column records how.
> - Sentences reporting this study's results carry no external citation; their source is the frozen tables.

## Cited claims

| # | Location | Claim (as written or condensed) | Keys | Support | Status | Action |
|---|---|---|---|---|---|---|
| 1 | first-page note; §1 ¶3; §2.1 ¶3 | The conference study fused raw, movement and contact features in a TCN, evaluated fixed-length sequences, disclaimed strict elapsed-time/LOSO interpretation, and left strict LOSO and user adaptation to future work | maeng2026icfice | full paper read | PASS | — |
| 2 | §1 ¶1 | Pressure mats and bedsheets have been used to monitor sleep posture | liu2013dense, yousefi2011bed | both abstracts | PASS | — |
| 3 | §1 ¶1 | … and breathing | carbonaro2021textile | abstract (breathing rate extraction) | PASS | — |
| 4 | §1 ¶1 | Part of a broader effort to replace laboratory sleep studies by unobtrusive home monitoring | matar2018unobtrusive | abstract (alternatives to PSG usable at home) | PASS | — |
| 5 | §1 ¶1; §2.1 | The skin microclimate (temperature, humidity) is an indirect pressure-injury risk factor | kottner2018microclimate | abstract | PASS | the conference paper's guideline citation was replaced by this peer-reviewed review |
| 6 | §1 ¶2; §2.1 | Temperature/humidity can be measured with sensors built into a mattress | mamom2023humidity | abstract | PASS | — |
| 7 | §1 ¶2 | Pressure sequences reflect posture, body contact and movement | liu2013dense, carbonaro2021textile | abstracts (posture; posture/movement) | PASS | "occupancy" removed: not in the sources |
| 8 | §1 ¶2 | Whether pressure carries enough information to estimate temperature/humidity is not established | — (framed as the research question) | author statement | PASS | the earlier "which interact with the microclimate" wording was removed as unsupported |
| 9 | §1 ¶3; §2.2 | TCNs: temporal convolution hierarchies; the generic TCN | lea2017tcn, bai2018tcn | abstracts; Bai full text §3 | PASS | — |
| 10 | §1 ¶4 | Sensor models lose accuracy for new users and on different devices | hong2016semipopulation, rokni2018personalized, stisen2015smart | abstracts | PASS | — |
| 11 | §1 ¶5 | Personalization with a small amount of the new user's data, or with data from similar users, has improved recognition accuracy | hong2016semipopulation, ferrari2020personalization | abstracts (83.4 % vs 77 %; "improves, on average, the accuracy") | PASS (after fix) | WEAK before: it cited rokni2018personalized, whose abstract states the framework but not an improvement. Re-cited |
| 12 | §1 ¶5; §2.4; §5.1 | Concept drift: the relation between inputs and target changes over time | gama2014survey | abstract (definition) | PASS | — |
| 13 | §1 ¶5; §2.4; §5.1 | Transfer can hurt target performance (negative transfer) | wang2019negative, zhang2023negative | abstracts | PASS | — |
| 14 | §2.1 | Commercial pressure-map data set, released publicly, for posture and subject analytics | pouyan2017pressure | abstract ("released publicly") | PASS | — |
| 15 | §2.1 | Pressure-mat posture classification explicitly for pressure-injury prevention (Yousefi) | yousefi2011bed | abstract | PASS | the motivation was first attributed to both papers; limited to Yousefi |
| 16 | §2.1 | A mattress-integrated textile pressure matrix characterises posture/movement and extracts breathing; the smart bed also collects environmental data | carbonaro2021textile | abstract ("can detect environmental data") | PASS (after fix) | WEAK before: "environmental sensors alongside the pressure layer" was an inference. Reworded to the abstract's content |
| 17 | §2.1 | Modelling: higher temperature and humidity lower skin tolerance | gefen2011microclimate | PubMed abstract | PASS | — |
| 18 | §2.1 | Microclimate differences between patients who did and did not develop skin damage | yusuf2015microclimate | abstract (prospective cohort) | PASS | — |
| 19 | §2.1 ¶3 | In the studies reviewed here, the microclimate is measured, not estimated from pressure | — (scope statement about the cited set) | author statement | PASS (after fix) | WEAK before: "has received less attention" was a field-wide claim without systematic-review support. Narrowed to the reviewed studies |
| 20 | §2.2 | A generic TCN (causal, dilated convolutions, residual blocks) outperformed recurrent networks on the benchmark tasks studied, with longer effective memory | bai2018tcn | abstract and full text §3 | PASS | worded "on the benchmark tasks studied"; no universal-superiority claim |
| 21 | §2.2 | Deep networks learning from raw wearable-sensor sequences and modelling temporal dynamics have been proposed | ordonez2016deep | abstract | PASS (after fix) | WEAK before: "have become common" is a trend claim one paper cannot support. Reworded |
| 22 | §2.2 | Estimating a continuous value from a time series is time series extrinsic regression, distinct from forecasting and classification | tan2021tser | abstract | PASS | — |
| 23 | §2.2 | TCN used as a studied model family; no superiority claimed | — | author statement | PASS | — |
| 24 | §2.3; §3.3 | Random CV over segmented time series is optimistic because adjacent segments are dependent | hammerla2015pairwise | abstract | PASS | — |
| 25 | §2.3; §3.5.4 | Record-wise validation overestimates accuracy for new subjects; subject-wise mirrors the use case | saeb2017usecase | abstract ("massively overestimates") | PASS | — |
| 26 | §2.3 | Individual diversity limits population activity models | hong2016semipopulation | abstract | PASS | — |
| 27 | §2.3 | Accuracy drops for new users or when a user's condition changes; transfer learning personalizes with minimal supervision | rokni2018personalized | abstract | PASS | — |
| 28 | §2.3 | One-size-fits-all models perform poorly when outcomes vary between individuals; personalized multitask models | taylor2020personalized | abstract | PASS | — |
| 29 | §2.3; §1 ¶4; §5.5 | Device heterogeneity degrades recognition | stisen2015smart | abstract | PASS | — |
| 30 | §2.3 | Sensor-placement heterogeneity degrades recognition; UDA assumptions can fail | chang2020systematic | abstract | PASS | — |
| 31 | §2.3 | Domain adaptation for time-series sensor data | wilson2020multisource | abstract | PASS | — |
| 32 | §2.3 | Personalization with the new user's data or with similar users | hong2016semipopulation, ferrari2020personalization | abstracts | PASS | — |
| 33 | §2.3 scope gap | Regression of environmental quantities for unseen users under combined shift, with chronological adaptation and a fixed later test span, is less examined | — | author scope judgement, stated as a gap without "first" or "novel" | PASS | the "usually with cross-validation over comparable periods" clause was removed (unsupported generalisation) |
| 34 | §2.4 | Training and later data can follow different distributions; transfer learning addresses this | pan2010survey | abstract | PASS | not cited for negative transfer (outside its abstract) |
| 35 | §2.4 | Negative transfer has motivated many remedies | zhang2023negative | abstract ("various approaches have been proposed") | PASS | — |
| 36 | §2.4; §5.6 | Soft-sensor adaptation mechanisms organised around concept drift | kadlec2011adaptation | abstract seen only via a search summary of the publisher page; metadata verified | PASS (moderate) | flagged in the matrix; replace with a directly read source if one becomes available |
| 37 | §2.4 | Low-cost environmental sensors are error-prone and drift; calibration and in situ recalibration maintain data quality | maag2018calibration, delaine2019insitu | abstracts | PASS (after fix) | WEAK before: "recalibration is a standard way" was stronger than the abstracts. Reworded |
| 38 | §3.4 | The TCN follows the generic design: causal dilated convolutions, residual blocks with a 1×1 convolution when channels change | bai2018tcn | full text §3 (figure: d = 1, 2, 4; 1×1 residual convolution) | PASS | — |
| 39 | §3.5.4 | Leakage: information about the target not available in deployment | kaufman2012leakage | abstract | PASS | — |
| 40 | §5.1 | Field calibration corrects systematic sensor errors (parallel, interpretive) | maag2018calibration, delaine2019insitu | abstracts | PASS (after fix) | WEAK before: "corrects sensor offsets" named offsets specifically. Reworded; kept apart from the result sentence |
| 41 | §5.1 | Parallels to concept drift and negative transfer, labelled interpretive and untested | gama2014survey, wang2019negative | abstracts | PASS | the earlier draft attached a calibration citation to this study's own result; moved into a separate sentence |
| 42 | §5.6 | Candidate safeguards: drift monitoring, adaptive estimators, recalibration (not tested here) | gama2014survey, kadlec2011adaptation, delaine2019insitu | abstracts | PASS | — |

## Uncited external statements checked

| Location | Statement | Status | Action |
|---|---|---|---|
| §1 ¶2 | Estimating from existing signals avoids adding and maintaining further sensors | PASS (logical consequence; no citation needed) | — |
| §3.1 | The mats contain a heater under firmware control that writes control codes | PASS (project data documentation, D-038) | — |
| §3.3 | Overlapping windows are not independent | PASS (cited, #24) | — |
| Featured Application | Potential application; use would need calibration and drift safeguards | PASS (conditional, no performance claim) | — |

## Removed or not used

- **The international pressure-injury guideline:** the conference paper's 2019 edition has been superseded (the
  official site lists a staged 4th edition), and the recommendation text was not verified. Its claim is covered by
  the peer-reviewed microclimate papers.
- **The unpublished late-fusion manuscript:** not cited while its status is unconfirmed.
- **Citations on this study's own results:** none remain.

## Result

- **42 cited claims, all PASS now.**
  - 7 were WEAK at audit and corrected before commit: #11, #16, #19, #21, #37, #40, and the §2.3 clause in #33.
  - Earlier corrections made while drafting are recorded in the Action column: #5, #7, #8, #15, #41.
  - None remains WEAK or UNSUPPORTED. One reference (Kadlec 2011) stands on moderate evidence and is flagged.
- **Coverage:** all 31 bibliography entries are cited, and every citation key exists in `references.bib`. No
  `[CITE: …]` placeholder remains.
