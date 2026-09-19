# Cover letter — metadata-ready

> **Status: complete text; only the metadata tokens are open.**
> - Built from `cover_letter_final_draft.md`: the scientific summary and the conference-paper section are unchanged.
>   The statements now point to the manuscript's own back-matter statements instead of repeating open placeholders.
> - Tokens: `L01`–`L04` (cover-letter items), `M03` (signature) and `M05` (conference copyright). They are filled
>   from `paper/submission_final/metadata/METADATA_VALUES_TEMPLATE.yaml` by `scripts/apply_submission_metadata.py`.
> - The approval sentences below are true only once items M11 and M12 are confirmed. The final build refuses to run
>   before that.

---

{{L01_SUBMISSION_DATE}}

Dear {{L02_EDITOR_NAME}},

We submit the manuscript **"Strict Unseen-Domain Evaluation of Pressure-Based Smart-Mat Temperature and Humidity
Estimation against Simple Level Baselines"** for consideration as an Article in *Applied Sciences*,
{{L03_SECTION_OR_SPECIAL_ISSUE}}.

**Summary.**
- Pressure-sensing smart mats could provide mat-level temperature and humidity estimates without extra sensors, but a
  deployed model meets users, recording periods and mats that it has not seen.
- We evaluated temporal convolutional networks on 40-s pressure windows from three subjects (four mat streams) under
  strict leave-one-subject-out evaluation, in which each held-out subject forms an unseen domain, and compared them
  with simple level baselines (training-mean and training-median constants).
- Errors were dominated by subject-dependent level offsets. For temperature, the network did not outperform the
  training-mean predictor for any held-out subject, and no pressure-feature representation removed the offsets.
- Chronological personalization on each subject's earliest 1–14 nights, evaluated on a fixed later test span, gave
  mixed results: a large offset correction in one subject and degradation in another. Post-hoc comparators, fixed in
  written plans before they were computed, showed that the gains were mainly level corrections: a personalized
  constant computed from the same adaptation labels was a strong competitor, the adapted predictions were strongly
  compressed toward level-dominated behaviour, and no consistent within-night co-variation with the targets was
  found.
- In a controlled longer-history comparison on endpoints with 15 min of continuous history, exploratory
  gradient-boosted models on 5–15-min pressure summaries reduced the temperature error in two of three subjects, and
  the network retrained on the same endpoints did not change the primary conclusion.
- A descriptive heater-context diagnostic found heater and controller context associated with temperature in the same
  two subjects, so the longer-history gain cannot be attributed specifically to pressure. The manuscript interprets
  the results with this confounding in view and does not claim a thermal mechanism.
- With three subjects, the findings are reported as cases with night-level uncertainty, not as population estimates;
  generalization beyond these three retrospective cases is untested. The main message is methodological: such
  estimators should be reported against simple level baselines, with subject-level results and night-level
  uncertainty.
- The work fits the journal's scope in applied sensing and machine learning: an evaluation of a sensing application
  under deployment-like conditions, with a de-identified, model-ready release candidate from which the primary models,
  predictions and tables were reproduced.

**Expanded conference paper.** This manuscript is a revised and expanded version of our conference paper "Robust
Temperature and Humidity Estimation from Smart Bedding Pressure Sequences Using Movement and Contact-Structure
Features", presented at the 18th International Conference on Future Information & Communication Engineering
(ICFICE 2026) and published in its proceedings (Volume 17, Number 1, pp. 27–30). The conference paper is cited in the
manuscript and noted on its title page.
- **Scope of the conference paper:** the same broad regression task and the temporal convolutional network lineage;
  a late-fusion model of movement and contact features; evaluation on pragmatic fixed-length sequences, because part of
  the logs lacked second-level timestamps; no strict elapsed-time leave-one-subject-out evaluation and no target-user
  fine-tuning.
- **What the journal article adds:**
  - an audited canonical dataset rebuilt from the raw logs, with a primary cohort restricted to subjects with complete
    second-level timestamps;
  - strict leave-one-subject-out evaluation with nested model selection, simple level baselines and an automated
    leakage gate, and a comparison of six pressure feature families under this protocol;
  - chronological personalization with 0, 1, 3, 7 and 14 adaptation nights on a common future test span, with
    night-level paired cluster-bootstrap uncertainty and seed and start-span sensitivity;
  - post-hoc comparators (personalized constant, offset-calibrated base model, scratch initialization control), a
    residual-variation analysis and a dynamic-signal diagnostic;
  - an additional external validation on one further subject, not pooled with the primary cohort;
  - the controlled longer-history comparison and the descriptive heater-context diagnostic;
  - a de-identified release candidate and a clean-checkout reproduction of the primary models, predictions and tables.
- **Relation to the conference results:** the present study does not show that the conference results were wrong.
  It shows that relative improvements among pressure representations do not, by themselves, establish an advantage
  over simple level baselines under subject-wise and chronological evaluation.
- **Reuse:** no text, table or figure of the conference paper is reused, and its results are not compared numerically
  with the journal results.
- **Copyright:** {{M05_CONFERENCE_COPYRIGHT}}

**Statements.**
- We confirm that neither the manuscript nor any parts of its content are currently under consideration for
  publication with or published in another journal.
- All authors have approved the manuscript and agree with its submission to *Applied Sciences*.
- Prior submissions of this manuscript to MDPI journals: {{L04_PREVIOUS_MDPI_SUBMISSION_STATUS}}.
- Ethics approval, informed consent, funding and conflicts of interest are stated in the corresponding back-matter
  statements of the manuscript.
- Data and code: a de-identified, model-ready dataset is prepared as a release candidate. The controller-event records
  used in the heater-context diagnostic are not included in the public release. The release scope, repository,
  persistent identifiers and licenses are given in the Data Availability Statement.
- The use of generative AI tools is disclosed in Materials and Methods (Section 3.8) and in the Acknowledgments, and
  all authors have approved this disclosure.

Sincerely,

{{M03_CORRESPONDING_AUTHOR}}
On behalf of all authors
