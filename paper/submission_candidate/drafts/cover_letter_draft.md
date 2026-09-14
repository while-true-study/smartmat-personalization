# Cover letter — final draft

> **Status: final draft; not sendable until the bracketed items are confirmed.**
> - It follows the Applied Sciences cover-letter rules and the four conditions for expanded conference papers
>   (`docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`, items 15–17).
> - No percentage of new content is claimed.
> - Suggested or excluded reviewers go into the submission system, not into this letter.
> - The statement that all authors approved the submission may be sent only after every author has done so.

---

[DATE — at submission]

Dear Editor,

We submit the manuscript **"Chronological Personalization under Unseen-Domain Shift: Offset Correction and Negative
Transfer in Smart-Mat Temperature and Humidity Estimation"** for consideration as an Article in *Applied Sciences*
[SECTION; SPECIAL ISSUE, IF ANY — CONFIRM].

**Summary and fit to the journal.**
- Pressure-sensing smart mats could estimate the temperature and humidity of the bed microclimate without
  additional sensors.
- We ask how such estimates behave for a user, recording period and mat that the model has not seen, and how far a
  few nights of the new user's data help.
- Under strict leave-one-subject-out evaluation, the errors are dominated by systematic level offsets that
  alternative pressure representations do not remove.
- Chronological fine-tuning on the user's earliest nights corrects a large offset in one case and produces negative
  transfer in others. The direction of adaptation is associated with how well the early nights represent the later
  period.
- With three subjects, the findings are reported as cases with night-level uncertainty, not as population estimates.
- The work fits the journal's scope in applied sensing and machine learning for health-related monitoring: a
  deployment-oriented evaluation of a sensing application, with a reproducible, de-identified data package.

**Expanded conference paper.** This manuscript is a revised and expanded version of our conference paper "Robust
Temperature and Humidity Estimation from Smart Bedding Pressure Sequences Using Movement and Contact-Structure
Features", presented at the 18th International Conference on Future Information & Communication Engineering
(ICFICE 2026), Sapporo, Japan, 7–10 July 2026 [PROCEEDINGS VOLUME, PAGES AND DOI OR URL — CONFIRM]. The conference
paper is cited in the manuscript and noted on its first page.
- **Scope of the conference paper:**
  - the same broad regression task (temperature and humidity from smart-bedding pressure sequences) and the temporal
    convolutional network lineage;
  - a late-fusion framework for movement-derived and contact-structure features;
  - evaluation on pragmatic fixed-length sequences, because part of the logs lacked second-level timestamps;
  - no strict elapsed-time leave-one-subject-out evaluation and no target-user fine-tuning. The paper named both as
    future work.
- **What has changed in the journal article:**
  - an audited canonical dataset rebuilt from the raw logs, with a timestamp-complete primary cohort;
  - strict elapsed-time leave-one-subject-out evaluation with frozen nested model selection, a training-mean
    reference and a leakage gate;
  - a revised comparison of the movement and contact representations under this protocol;
  - chronological personalization with 0–14 adaptation nights on a fixed future test span, with a negative-transfer
    analysis;
  - night-level robustness analyses (paired cluster bootstrap, seed and start-span sensitivity);
  - a de-identified reproduction package, from which the selected models, predictions and result tables were
    reproduced. It is prepared as a release candidate, and its public release is pending.
- **Reuse:** no text, table or figure of the conference paper is reused, and its results are not compared
  numerically with the journal results.
- **Copyright:** the copyright of the conference paper is held by [COPYRIGHT HOLDER — CONFIRM]. [PERMISSION: not
  required because no material is reused / obtained on DATE — CONFIRM]

**Statements.**
- We confirm that neither the manuscript nor any parts of its content are currently under consideration for
  publication with or published in another journal.
- All authors have approved the manuscript and agree with its submission to Applied Sciences. [CONFIRM: every author
  has approved]
- Prior submissions of this manuscript to MDPI journals: [NONE / MANUSCRIPT ID — CONFIRM]
- Ethics and consent: [ETHICS / IRB INFORMATION REQUIRED FROM PI]; [INFORMED CONSENT WORDING REQUIRED FROM PI].
- Funding: [FUNDING TO BE CONFIRMED BY PI]. Conflicts of interest: [CONFLICTS OF INTEREST — CONFIRM].
- Data and code: the de-identified dataset is prepared as a release candidate. Its license, repository and persistent
  identifier are pending, and the Data Availability Statement says so. [UPDATE WHEN RESOLVED]
- The use of generative AI tools is disclosed in Materials and Methods (Section 3.8) and in the Acknowledgments.

Sincerely,

[CORRESPONDING AUTHOR NAME, AFFILIATION AND E-MAIL — CONFIRM]
