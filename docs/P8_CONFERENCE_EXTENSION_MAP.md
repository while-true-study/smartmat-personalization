# P8 — Conference-to-journal extension map

> The journal paper extends the authors' ICFICE conference paper [ICFICE CITATION].
> - **The conference paper is not in this repository.** Its side of the map uses only what the repository records
>   (RESEARCH_PROTOCOL §1, D-032, D-040: TCN regression of temperature/humidity from multi-channel mat pressure,
>   20/30/40-s windows, a movement-fusion idea) and the PI's description (pressure representation and
>   movement/contact feature modelling).
> - Every conference-side cell marked [VERIFY] must be checked against the published paper before submission.
> - No conference number is reused: no P2–P6 choice used a value from the prior study (D-040), and no text is copied
>   verbatim.

| Conference component | Journal counterpart | Unchanged / reused | Substantially extended | New experiment / evidence | Manuscript section |
|---|---|---|---|---|---|
| Task: temperature and humidity regression from multi-channel smart-mat pressure sequences | same task, same six-channel input, targets from the heater-controlled mat microclimate | task definition | — | — | §1, §3.1 |
| TCN model | causal residual TCN re-implemented under protocol v1.0; configuration only from a nested, pre-declared search (D-040) | model family | re-implementation, search space, selection rule, seeds 0/1/2 | — | §3.4 |
| Windows of 20/30/40 s | 40-s, 8 × 5-s bin windows of observed rows, stride 20 s; split before windowing (D-032). 20/30 s declared but not run | 40 s as the comparison anchor | windowing rule without interpolation | — | §3.3, §7 |
| Movement / contact feature modelling ("movement fusion") | six pre-declared feature families (RAW, MOVEMENT, CONTACT and three combinations), each with its own selection; geometry-free features (D-039) | the idea of movement and contact representations | systematic family comparison; feature definitions | target-dependent, non-additive effects; offset not removed (P4) | §4.2, §5.2 |
| Dataset [VERIFY: subjects, sources, curation] | audited canonical_v1: provenance, exact-copy de-duplication, sessions, validity flags, explicit cohort (3 subjects, 4 streams) and excluded-source policy | — | data curation and cohort definition | — | §3.1–§3.2 |
| Evaluation split [VERIFY: conference protocol] | strict leave-one-subject-out with nested subject-level validation, single outer look, automated leakage gate (D-031, D-042) | — | — | strict unseen-user evaluation (P3) | §4.1, §5.1 |
| Baselines [VERIFY] | mandatory training-mean predictor under the same split | — | — | RAW-TCN vs training-mean per subject (P3) | §5.1 |
| — (no personalization, [VERIFY]) | chronological personalization with 0/1/3/7/14 nights, a fixed primary test span, frozen recipe (D-037, D-045) | — | — | adaptation curves, offset correction, negative transfer (P5) | §4.3, §5.3 |
| — | night-level paired cluster bootstrap, seed sensitivity, drift sensitivity (D-041, D-047) | — | — | uncertainty and robustness of every effect (P6) | §4.4, §5.4 |
| — | post-hoc temporal level-mismatch analysis | — | — | representativeness association, 23/24 cells (P6) | §5.5 |
| — | User02 per-mat, quality-phase and heater-context strata | — | — | persistent 22482 residual (P5, P6) | §5.6 |
| — | de-identified model-ready release and clean-checkout reproduction (D-049, D-050) | — | — | public reproducibility (P7) | Reproducibility, Data Availability |

**Emphasis in the manuscript:**
- Conference: pressure representation, and movement/contact feature modelling.
- Journal:
  - strict unseen-user evaluation;
  - chronological personalization;
  - negative transfer;
  - night-level robustness;
  - public reproducibility.

**To check before submission:**
- the bibliographic details of the conference paper [ICFICE CITATION];
- every [VERIFY] cell above;
- the journal's policy on extended conference papers (for example, the required share of new material and how to
  declare the prior publication) [VERIFY AGAINST APPLIED SCIENCES INSTRUCTIONS];
- that no figure or text is reused from the conference paper without citation and permission.
