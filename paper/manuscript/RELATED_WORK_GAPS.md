# Related work — literature gaps (resolved in P8 pass 3)

> **Status: resolved.** The literature pass (2026-09-14) replaced every `[CITE: …]` placeholder in the manuscript with
> verified references.
> - Evidence per reference: `docs/P8_LITERATURE_EVIDENCE_MATRIX.md`.
> - Claim-by-claim audit: `docs/P8_CITATION_AUDIT.md`.
> - Entries: `references.bib`.

| # | Topic (pass 1) | Resolution | Keys |
|---|---|---|---|
| 1 | Smart bedding and pressure-mat sensing | §2.1, §1 ¶1–2 | matar2018unobtrusive, liu2013dense, pouyan2017pressure, yousefi2011bed, carbonaro2021textile |
| 2 | Indirect estimation of temperature / humidity; bed microclimate | §2.1, §1 ¶1–2. No verified study estimates bed temperature/humidity from pressure (apart from the authors' conference paper), so this is framed as the open question | kottner2018microclimate, gefen2011microclimate, yusuf2015microclimate, mamom2023humidity, maeng2026icfice |
| 3 | TCN for sensor time-series regression | §2.2, §3.4 | lea2017tcn, bai2018tcn, ordonez2016deep, tan2021tser |
| 4 | Cross-subject generalization / domain shift | §2.3, §1 ¶4 | hong2016semipopulation, rokni2018personalized, stisen2015smart, chang2020systematic, wilson2020multisource |
| 5 | Personalization / subject adaptation | §2.3, §1 ¶5 | rokni2018personalized, ferrari2020personalization, taylor2020personalized, hong2016semipopulation |
| 6 | Negative transfer | §2.4, §1 ¶5, §5.1 | wang2019negative, zhang2023negative, pan2010survey (transfer frame only) |
| 7 | Temporal concept drift | §2.4, §1 ¶5, §5.1, §5.6 | gama2014survey, kadlec2011adaptation |
| 8 | Calibration / domain-level bias | §2.4, §5.1, §5.6 | maag2018calibration, delaine2019insitu |
| 9 | Leakage in evaluation | §3.3, §3.5.4, §2.3 | hammerla2015pairwise, saeb2017usecase, kaufman2012leakage |
| 10 | Cluster / block bootstrap | not cited. The night-level bootstrap is part of the frozen protocol (D-041) and its limitation is stated in §6. A methodological reference can be added in a later pass if a reviewer asks | — |
| 11 | The authors' conference paper | §1 ¶3, §2.1, first-page note | maeng2026icfice (bibliographic details pending) |

**Not retained:** see the matrix, "Reviewed and not retained". In particular:
- the international pressure-injury guideline (the 2019 edition has been superseded by a staged 4th edition; the
  recommendation text was not verified);
- the unpublished late-fusion manuscript (its status is unconfirmed).
