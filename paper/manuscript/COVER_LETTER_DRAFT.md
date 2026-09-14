# Cover letter — draft

> **Status: draft for the PI.** Bracketed items are placeholders and must not be sent as written. No percentage of
> new content is claimed. Conference-extension conduct follows `docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md` item 15.

---

[DATE — at submission]

Dear Editor,

We submit the manuscript **"Chronological Personalization under Unseen-Domain Shift: Offset Correction and Negative
Transfer in Smart-Mat Temperature and Humidity Estimation"** for consideration as a research article in *Applied
Sciences* [SECTION OR SPECIAL ISSUE, IF ANY — CONFIRM].

**Summary.** Pressure-sensing smart mats could estimate the temperature and humidity of the bed microclimate without
additional sensors. We ask how such estimates behave for a user, recording period and mat that the model has not
seen, and how far a few nights of the new user's data help. Under strict leave-one-subject-out evaluation, the
errors are dominated by systematic level offsets that alternative pressure representations do not remove.
Chronological fine-tuning on the user's earliest nights corrects a large offset in one case and produces negative
transfer in others. The direction of adaptation is associated with how well the early nights represent the later
period. With three subjects, the findings are reported as cases, with night-level uncertainty, not as population
estimates.

**Relation to our conference paper.** This manuscript extends our conference paper "Robust Temperature and Humidity
Estimation from Smart Bedding Pressure Sequences Using Movement and Contact-Structure Features", presented at the
18th International Conference on Future Information & Communication Engineering (ICFICE 2026)
[PROCEEDINGS VOLUME, PAGES AND DOI — CONFIRM]. The conference paper is cited in the manuscript and noted on its first
page.
- **Shared:** the broad regression task (temperature and humidity from smart-bedding pressure sequences) and the
  temporal convolutional network lineage, including the movement-derived and contact-structure feature ideas.
- **Limits of the conference study:** it evaluated a late-fusion framework on pragmatic fixed-length sequences,
  because part of the logs lacked second-level timestamps. It did not perform strict elapsed-time
  leave-one-subject-out evaluation or target-user fine-tuning, and it named both as future work.
- **New in the journal article:**
  - an audited canonical dataset rebuilt from the raw logs, with a timestamp-complete primary cohort;
  - strict elapsed-time leave-one-subject-out evaluation with frozen nested model selection and a leakage gate;
  - a revised comparison of the movement and contact representations under this protocol;
  - chronological personalization with 0–14 adaptation nights on a fixed future test span, with a negative-transfer
    analysis;
  - night-level robustness analyses (paired cluster bootstrap, seed and start-span sensitivity);
  - a de-identified reproduction package, from which the selected models, predictions and result tables were
    reproduced (prepared as a release candidate; its public release is pending).
- **Reuse:** no text, table or figure of the conference paper is reused, and its results are not compared numerically
  with the journal results. [COPYRIGHT HOLDER OF THE CONFERENCE PAPER — CONFIRM; no permission is expected to be
  needed because nothing is reused.]

**Other statements.**
- The manuscript has not been published and is not under consideration elsewhere, apart from the conference paper
  described above. [CONFIRM]
- Data and code: the de-identified dataset is prepared as a release candidate; its license, repository and DOI are
  pending, and the manuscript states this. [CONFIRM AT SUBMISSION]
- Ethics and consent: [ETHICS / IRB INFORMATION REQUIRED FROM PI]; [INFORMED CONSENT WORDING REQUIRED FROM PI].
- Use of generative AI is disclosed in Materials and Methods (Section 3.8) and in the Acknowledgments.
- Funding: [FUNDING TO BE CONFIRMED BY PI]. Conflicts of interest: [CONFIRM].

Sincerely,

[CORRESPONDING AUTHOR NAME, AFFILIATION AND CONTACT — CONFIRM]
