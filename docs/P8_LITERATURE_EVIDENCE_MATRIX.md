# P8 — Literature evidence matrix

> **Every retained reference was checked on 2026-09-14 against a primary record.**
> - **Metadata:** the Crossref record of its DOI (title, authors, venue, year, volume/pages), with the DOI resolved at
>   doi.org (HTTP 302). For the one arXiv preprint, the arXiv abstract page.
> - **Content:** the abstract, from Semantic Scholar, Crossref, OpenAlex or PubMed, or the arXiv page.
> - **Years:** print-issue year where Crossref has one; otherwise the online year.
> - A reference is retained only if a specific manuscript statement needs it and its abstract supports that
>   statement.
> - Nothing is cited from a search snippet alone, except Kadlec 2011, flagged below. Candidate metadata from the
>   authors' earlier manuscripts was re-checked and corrected: two author lists and one venue were wrong there.

Columns: key · reference (authors, title, venue, year, DOI) · type · peer-reviewed · exact claim supported · strength ·
scope limits · manuscript section. Strength: **strong** = the claim is the paper's main finding or topic;
**moderate** = the claim follows from the abstract but is secondary, model-based or single-site; **context** = cited
for background, not for a finding.

## A. Pressure injury and bed microclimate

| Key | Reference | Type | Peer-rev. | Claim supported | Strength | Limits | Section |
|---|---|---|---|---|---|---|---|
| kottner2018microclimate | Kottner, J.; Black, J.; Call, E.; Gefen, A.; Santamaria, N. Microclimate: A critical review in the context of pressure ulcer prevention. *Clin. Biomech.* **2018**, 59, 62–70. doi:10.1016/j.clinbiomech.2018.09.010 | review | YES | The skin microclimate (temperature, humidity, airflow next to the skin) is an indirect pressure-ulcer risk factor; temperature and humidity affect skin structure, function and damage thresholds | strong | the abstract notes that direct clinical evidence is limited; concerns the skin, not mat-embedded sensors | §1 ¶1, §2.1 |
| gefen2011microclimate | Gefen, A. How do microclimate factors affect the risk for superficial pressure ulcers: a mathematical modeling study. *J. Tissue Viability* **2011**, 20, 81–88. doi:10.1016/j.jtv.2010.10.002 | modelling study | YES | Higher skin and ambient temperature, higher relative humidity and higher contact pressure lower the modelled skin tolerance to superficial pressure ulcers | moderate | a mathematical model, not a clinical trial | §2.1 |
| yusuf2015microclimate | Yusuf, S.; Okuwa, M.; Shigeta, Y.; et al. Microclimate and development of pressure ulcers and superficial skin changes. *Int. Wound J.* **2015**, 12, 40–46. doi:10.1111/iwj.12048 | prospective cohort | YES | In a hospital cohort, microclimate measures differed between patients who did and did not develop pressure ulcers or superficial skin changes | moderate | single site, 71 participants; published online 2013 | §2.1 |
| mamom2023humidity | Mamom, J.; Ratanadecho, P.; Mingmalairak, C.; Rungroungdouyboon, B. Humidity-sensing mattress for long-term bedridden patients with incontinence-associated dermatitis. *Micromachines* **2023**, 14, 1178. doi:10.3390/mi14061178 | device + clinical test | YES | Humidity sensors have been built into a mattress and tested clinically for bedridden patients | moderate | direct humidity sensing, not estimation from pressure | §2.1 |

## B–C. Smart bedding and pressure-based monitoring

| Key | Reference | Type | Peer-rev. | Claim supported | Strength | Limits | Section |
|---|---|---|---|---|---|---|---|
| matar2018unobtrusive | Matar, G.; Lina, J.-M.; Carrier, J.; Kaddoum, G. Unobtrusive sleep monitoring using cardiac, breathing and movements activities: an exhaustive review. *IEEE Access* **2018**, 6, 45129–45152. doi:10.1109/ACCESS.2018.2865487 | review | YES | Unobtrusive, home-usable alternatives to polysomnography based on cardiac, breathing and movement signals are an active research area | strong | a review of sleep monitoring, not of environmental estimation | §1 ¶1, §2.1 |
| liu2013dense | Liu, J.J.; Xu, W.; Huang, M.-C.; et al. A dense pressure sensitive bedsheet design for unobtrusive sleep posture monitoring. In *Proc. IEEE PerCom 2013*, pp. 207–215. doi:10.1109/PerCom.2013.6526734 | conference | YES | A textile pressure-sensitive bedsheet allows unobtrusive monitoring of sleep posture | strong | posture, pilot-scale cohort | §2.1 |
| pouyan2017pressure | Pouyan, M.B.; Birjandtalab, J.; Zadeh, M.H.; Nourani, M.; Ostadabbas, S. A pressure map dataset for posture and subject analytics. In *Proc. IEEE EMBS BHI 2017*, pp. 65–68. doi:10.1109/BHI.2017.7897206 | conference (dataset) | YES | Commercial pressure mats measure the pressure distribution under the body continuously; posture tracking is relevant to pressure-ulcer prevention | strong | posture dataset (13 participants) | §2.1 |
| yousefi2011bed | Yousefi, R.; Ostadabbas, S.; Faezipour, M.; et al. Bed posture classification for pressure ulcer prevention. In *Proc. IEEE EMBC 2011*, pp. 7175–7178. doi:10.1109/IEMBS.2011.6091813 | conference | YES | Pressure mapping has been used to record and classify in-bed posture for pressure-ulcer prevention | strong | classification of posture, not environment | §2.1 |
| carbonaro2021textile | Carbonaro, N.; Laurino, M.; Arcarisi, L.; Menicucci, D.; Gemignani, A.; Tognetti, A. Textile-based pressure sensing matrix for in-bed monitoring of subject sleeping posture and breathing activity. *Appl. Sci.* **2021**, 11, 2552. doi:10.3390/app11062552 | journal | YES | A mattress-integrated textile pressure matrix characterises posture and movement and extracts breathing; the smart bed also collects environmental data | strong | environmental data are collected by sensors, not estimated from pressure | §2.1 |

## D–E. Temporal models for sensor regression

| Key | Reference | Type | Peer-rev. | Claim supported | Strength | Limits | Section |
|---|---|---|---|---|---|---|---|
| lea2017tcn | Lea, C.; Flynn, M.D.; Vidal, R.; Reiter, A.; Hager, G.D. Temporal convolutional networks for action segmentation and detection. In *Proc. IEEE CVPR 2017*, pp. 1003–1012. doi:10.1109/CVPR.2017.113 | conference | YES | Introduces temporal convolutional networks, i.e. hierarchies of temporal (including dilated) convolutions, for fine-grained temporal segmentation | strong | video action segmentation | §2.2 |
| bai2018tcn | Bai, S.; Kolter, J.Z.; Koltun, V. An empirical evaluation of generic convolutional and recurrent networks for sequence modeling. *arXiv* **2018**, arXiv:1803.01271 | preprint (canonical) | NO | A generic TCN outperformed canonical recurrent networks across the benchmark tasks studied, with longer effective memory; the source of the generic TCN design: causal convolutions, dilated convolutions (the paper's figure uses d = 1, 2, 4) and residual blocks with a 1×1 convolution when dimensions differ (checked in the full text, §3) | strong for the architecture; context for performance | not peer-reviewed; generic benchmarks. It is **not** cited for universal superiority | §2.2, §3.4 |
| ordonez2016deep | Ordóñez, F.J.; Roggen, D. Deep convolutional and LSTM recurrent neural networks for multimodal wearable activity recognition. *Sensors* **2016**, 16, 115. doi:10.3390/s16010115 | journal | YES | Deep networks learn features directly from raw wearable-sensor sequences, and modelling temporal dynamics matters for sensor-based recognition | strong | classification, not regression | §2.2 |
| tan2021tser | Tan, C.W.; Bergmeir, C.; Petitjean, F.; Webb, G.I. Time series extrinsic regression: predicting numeric values from time series data. *Data Min. Knowl. Discov.* **2021**, 35, 1032–1060. doi:10.1007/s10618-021-00745-9 | journal | YES | Learning a continuous scalar from a time series (time series extrinsic regression) is a distinct task from forecasting and classification | strong | benchmark archive; no smart-mat data | §2.2 |

## F. Evaluation of subject-level generalization

| Key | Reference | Type | Peer-rev. | Claim supported | Strength | Limits | Section |
|---|---|---|---|---|---|---|---|
| hammerla2015pairwise | Hammerla, N.Y.; Plötz, T. Let's (not) stick together: pairwise similarity biases cross-validation in activity recognition. In *Proc. ACM UbiComp 2015*, pp. 1041–1051. doi:10.1145/2750858.2807551 | conference | YES | Random cross-validation on segmented time series is optimistic because adjacent segments are not independent; generalization to new users must be evaluated accordingly | strong | activity recognition | §2.3, §3.3 |
| saeb2017usecase | Saeb, S.; Lonini, L.; Jayaraman, A.; Mohr, D.C.; Kording, K.P. The need to approximate the use-case in clinical machine learning. *GigaScience* **2017**, 6, gix019. doi:10.1093/gigascience/gix019 | journal | YES | Record-wise cross-validation often overestimates accuracy for new subjects; subject-wise evaluation mirrors the use case | strong | clinical prediction from wearables | §2.3 |
| kaufman2012leakage | Kaufman, S.; Rosset, S.; Perlich, C.; Stitelman, O. Leakage in data mining: formulation, detection, and avoidance. *ACM Trans. Knowl. Discov. Data* **2012**, 6, 1–21. doi:10.1145/2382577.2382579 | journal | YES | Leakage is the introduction of information about the target that would not legitimately be available | strong | general data mining | §3.5.4 |

## G–H. Personalization, subject adaptation and domain shift in human sensing

| Key | Reference | Type | Peer-rev. | Claim supported | Strength | Limits | Section |
|---|---|---|---|---|---|---|---|
| hong2016semipopulation | Hong, J.-H.; Ramos, J.; Dey, A.K. Toward personalized activity recognition systems with a semipopulation approach. *IEEE Trans. Hum.-Mach. Syst.* **2016**, 46, 101–112. doi:10.1109/THMS.2015.2489688 | journal | YES | Individual diversity limits the generalizability of population activity models; small amounts of the new user's labelled data can select suitable models of other users | strong | classification with 28 users | §2.3 |
| rokni2018personalized | Rokni, S.A.; Nourollahi, M.; Ghasemzadeh, H. Personalized human activity recognition using convolutional neural networks. In *Proc. AAAI* **2018**, 32. doi:10.1609/aaai.v32i1.12185 | conference | YES | Recognition performance drops for new users or when a user's status changes; transfer learning personalizes a CNN with minimal user supervision | strong | activity recognition (short abstract) | §2.3 |
| ferrari2020personalization | Ferrari, A.; Micucci, D.; Mobilio, M.; Napoletano, P. On the personalization of classification models for human activity recognition. *IEEE Access* **2020**, 8, 32066–32079. doi:10.1109/ACCESS.2020.2973425 | journal | YES | Personalization models that account for subject similarity improve average activity-recognition accuracy; evaluation must reflect the personalization setting | strong | smartphone accelerometer | §2.3 |
| taylor2020personalized | Taylor, S.; Jaques, N.; Nosakhare, E.; Sano, A.; Picard, R. Personalized multitask learning for predicting tomorrow's mood, stress, and health. *IEEE Trans. Affect. Comput.* **2020**, 11, 200–213. doi:10.1109/TAFFC.2017.2784832 | journal | YES | Because of individual differences, one-size-fits-all models perform poorly for wellbeing prediction from wearable and phone data; personalized models improve it | strong | a different target and multitask setting | §2.3 |
| chang2020systematic | Chang, Y.; Mathur, A.; Isopoussu, A.; Song, J.; Kawsar, F. A systematic study of unsupervised domain adaptation for robust human-activity recognition. *Proc. ACM Interact. Mob. Wearable Ubiquitous Technol.* **2020**, 4, 1–30. doi:10.1145/3380985 | journal | YES | Sensor-placement heterogeneity degrades deep activity models, and unsupervised domain adaptation is no silver bullet; its data assumptions matter | strong | wearing diversity, not subject/period shift | §2.3 |
| wilson2020multisource | Wilson, G.; Doppa, J.R.; Cook, D.J. Multi-source deep domain adaptation with weak supervision for time-series sensor data. In *Proc. ACM KDD 2020*, pp. 1768–1778. doi:10.1145/3394486.3403228 | conference | YES | Domain adaptation methods have been developed for time-series sensor data, including multi-source settings | strong | unsupervised or weakly supervised, not chronological fine-tuning | §2.3 |
| stisen2015smart | Stisen, A.; Blunck, H.; Bhattacharya, S.; et al. Smart devices are different: assessing and mitigating mobile sensing heterogeneities for activity recognition. In *Proc. ACM SenSys 2015*, pp. 127–140. doi:10.1145/2809695.2809718 | conference | YES | Sensor-, device- and workload-specific heterogeneity lowers recognition performance across devices | strong | phones and watches, not mats | §2.3, §5.5 |

## I–K. Transfer, negative transfer, drift and calibration

| Key | Reference | Type | Peer-rev. | Claim supported | Strength | Limits | Section |
|---|---|---|---|---|---|---|---|
| pan2010survey | Pan, S.J.; Yang, Q. A survey on transfer learning. *IEEE Trans. Knowl. Data Eng.* **2010**, 22, 1345–1359. doi:10.1109/TKDE.2009.191 | survey | YES | Training and future data may follow different distributions; transfer learning addresses this, including for regression | strong | cited only for the transfer-learning frame. **Not** cited for negative transfer (outside its abstract) | §2.4 |
| wang2019negative | Wang, Z.; Dai, Z.; Póczos, B.; Carbonell, J. Characterizing and avoiding negative transfer. In *Proc. IEEE/CVF CVPR 2019*, pp. 11285–11294. doi:10.1109/CVPR.2019.01155 | conference | YES | Transfer from a less related source can hurt target performance (negative transfer); the paper gives a formal definition | strong | source-task relatedness in classification | §2.4 |
| zhang2023negative | Zhang, W.; Deng, L.; Zhang, L.; Wu, D. A survey on negative transfer. *IEEE/CAA J. Autom. Sin.* **2023**, 10, 305–329. doi:10.1109/JAS.2022.106004 | survey | YES | Transfer learning is not always effective; negative transfer is a long-standing problem with many proposed remedies | strong | survey | §2.4 |
| gama2014survey | Gama, J.; Žliobaitė, I.; Bifet, A.; Pechenizkiy, M.; Bouchachia, A. A survey on concept drift adaptation. *ACM Comput. Surv.* **2014**, 46, 1–37. doi:10.1145/2523813 | survey | YES | Concept drift is a change over time in the relation between input data and the target variable; adaptive-learning strategies and their evaluation | strong | online/streaming settings | §1 ¶5, §2.4 |
| kadlec2011adaptation | Kadlec, P.; Grbić, R.; Gabrys, B. Review of adaptation mechanisms for data-driven soft sensors. *Comput. Chem. Eng.* **2011**, 35, 1–24. doi:10.1016/j.compchemeng.2010.07.034 | review | YES | Data-driven soft sensors (indirect estimators) need adaptation mechanisms; these are classified by concept-drift theory (moving windows, recursive adaptation, ensembles) | moderate: the abstract was seen only as a search summary of the publisher page (ScienceDirect blocked direct access); metadata verified | process industry | §2.4 |
| maag2018calibration | Maag, B.; Zhou, Z.; Thiele, L. A survey on sensor calibration in air pollution monitoring deployments. *IEEE Internet Things J.* **2018**, 5, 4857–4870. doi:10.1109/JIOT.2018.2853660 | survey | YES | Low-cost environmental sensors are error-prone in the field; calibration and network recalibration maintain data quality in long-term deployments | strong | air-quality sensors | §2.4 |
| delaine2019insitu | Delaine, F.; Lebental, B.; Rivano, H. In situ calibration algorithms for environmental sensor networks: a review. *IEEE Sens. J.* **2019**, 19, 5968–5978. doi:10.1109/JSEN.2019.2910317 | review | YES | Low-cost environmental sensors drift, and factory calibration may not transfer to field conditions, motivating in situ recalibration | strong | environmental sensor networks | §2.4, §5.6 |

## Conference paper

| Key | Reference | Type | Peer-rev. | Claim supported | Strength | Limits | Section |
|---|---|---|---|---|---|---|---|
| maeng2026icfice | Maeng, D.-H.; Bang, J.-S. Robust temperature and humidity estimation from smart bedding pressure sequences using movement and contact-structure features. In *Proceedings of the 18th International Conference on Future Information & Communication Engineering (ICFICE 2026)*, Sapporo, Japan, 7–10 July 2026 (oral paper AI-06) | conference | UNCLEAR (conference review process not documented in the sources read) | TCN fusion of raw, movement and contact-structure features; fixed-length-sequence evaluation; strict elapsed-time LOSO and user adaptation left to future work (verified against the full paper) | strong (own prior work) | proceedings pages, DOI and URL [VERIFY BIBLIOGRAPHIC DETAILS] | §1 ¶3, first-page note |

**Totals:** 31 retained.
- 1 preprint (arXiv, canonical TCN source).
- 1 own conference paper, whose peer-review status is unclear.
- 29 peer-reviewed: 20 journal articles and 9 conference papers (IEEE/ACM/AAAI proceedings).
- Recent work (2020 or later): 9.

## Reviewed and not retained

| Candidate | Reason |
|---|---|
| Lu et al., "Learning under concept drift: a review", IEEE TKDE | Crossref and OpenAlex expose only the early-access record (no volume or pages); Gama 2014 covers the claim |
| Widmer & Kubat 1996, "Learning in the presence of concept drift and hidden contexts", Mach. Learn. | metadata verified, but the abstract could not be read (publisher login); not cited without content |
| Moreno-Torres et al. 2012 (dataset shift); Bergmeir & Benítez 2012 (time-series CV); Kadlec et al. 2009 (soft sensors) | no verifiable abstract; not needed for a specific claim |
| He et al. 2016 (ResNet) | residual blocks are covered by the TCN source; not needed |
| Clever et al. 2020 (pose from pressure images); Li et al. 2024 (air-mattress posture) | redundant with the retained pressure-mat posture studies |
| Lockhart & Weiss 2014 | the abstract concerns data-set and methodology limitations generally; weak fit |
| International pressure-injury guideline (NPIAP/EPUAP/PPPIA) | the 3rd edition (2019) cited by the conference paper has been superseded: the official site lists a 4th edition, released in stages. The specific microclimate recommendation text was not verified. The peer-reviewed microclimate evidence above supports the manuscript's claim |
| Lee, Kim & Bang, movement-score late-fusion manuscript | a copy exists in the authors' materials, but no venue, acceptance or DOI is documented. Not cited as a publication unless the PI confirms its status (MDPI allows "submitted/accepted/in press" forms) |
| Braden et al. 1987 (Braden scale); Hochreiter & Schmidhuber 1997; Schuster & Paliwal 1997; multimodal-fusion survey | from the earlier manuscripts; no statement in this manuscript needs them |
| a pressure-textile sleep-position classification preprint (SSRN) | not peer-reviewed; redundant |
