# P16 — Final editorial revision: notes

> Source `paper/manuscript/manuscript_p16_final.md` (from `manuscript_p15_final.md`, unchanged). Editorial only: no
> experiment, analysis, number or research question changed (`scripts/validate_p16_submission.py`, check
> "scientific_equivalence": every result token of P16 is a token of P15; same research questions, tables and figures).

## Changes

| Area | Change |
|---|---|
| Introduction | six paragraphs (motivation; pressure and thermal/moisture state without a causal claim; evaluation limits; why strict leave-one-subject-out evaluation and level baselines; personalization as representation versus level recalibration; RQs and contributions); four contributions instead of seven; no result numbers; the conference relation condensed |
| Related Work | the same references and claims, condensed, with a closing link to this study per subsection |
| Methods | the external-validation, statistics and reproducibility subsections condensed; the post-hoc list merged into Section 3.6; the heading "Post-Hoc Validation Comparators (Post Hoc)" de-duplicated |
| Results | sentences repeating table values removed (Sections 4.1–4.9); neutral wording ("lower/higher MAE", "interval included zero"); the external-validation reading softened from "strengthening" to "consistent with" |
| Discussion | Section 5.2 condensed; "main negative result" → "main finding"; Section 5.5 limitations as eight numbered items (cohort, confounding, User02 mats, sensor metadata, fixed formulation and protocol, history subset, post-hoc diagnostics and heater endogeneity, no independent context measurement) |
| Conclusions | two paragraphs without numbers: what was observed; what cannot be claimed and which data are needed |
| Front matter | abstract 198 words with a closing implication on generalization; keywords: smart mat; pressure sensing; temperature and humidity estimation; temporal convolutional network; leave-one-subject-out evaluation; personalization; domain shift; baseline comparison ("negative transfer" replaced: the text reports mixed, level-dominated adaptation, not negative transfer as a general conclusion) |
| Supplementary citations | 13 previously uncited tables now cited (`docs/P16_SUPPLEMENTARY_REVIEW.md`) |
| GenAI | Claude Code versions listed only as recorded (2.1.263, 2.1.270, 2.1.276, 2.1.277); approval placeholder kept |

Main-text length (rendered, Introduction to Conclusions, without tables, captions and figure links): 15,964 → about
14,800 words.

## Reviewer questions and where the manuscript answers them

| Question | Answer in the text |
|---|---|
| Why three subjects? | Section 3.1 (cohort chosen by structural data checks before any model); Section 5.5, item 1 |
| Why 40 s? | Section 3.3 (window rule); Section 5.5, item 5 (fixed in the protocol before any result; 20-s and 30-s sensitivity analyses not run) |
| Why 300 and 900 s? | Section 3.5.8 (histories up to 15 min fixed in a written plan before computation); Section 5.5, item 6 |
| Why mean and median baselines? | Introduction ¶4; Sections 3.5.1, 4.1, 4.10 |
| Is the fine-tuning gain representation adaptation? | Sections 4.7–4.8 and 5.2 (level correction, compressed dynamics, no demonstrable tracking) |
| Scratch ≈ fine-tuning: any value of pretraining? | Sections 4.7 and 5.2 ("did not provide consistent additional predictive value … fixed adaptation protocol") |
| Does the heater explain the result? | Sections 4.11 and 5.3 (association, endogeneity, source composition; "These mechanisms cannot be separated …") |
| "Microclimate" without sensor placement? | Section 3.1 (mat-level measurements; sensor placeholder); Section 5.5, item 4 |
| Are User02's two mats a device effect? | Sections 4.6, 5.2 and 5.5, item 3 (no causal interpretation) |
| Why is a post-hoc diagnostic in the main text? | Contribution 4; Sections 3.5.9 (scope) and 5.3 (it limits the mechanistic interpretation) |
| Why can the public data not reproduce it? | Section 3.7 and the Data Availability Statement |

## Title (applied in the final editorial correction)

Final: **"Strict Unseen-Domain Evaluation of Pressure-Based Smart-Mat Temperature and Humidity Estimation against
Simple Level Baselines"**. The previous title's "Microclimate" is replaced, so that the title matches the mat-level
wording and implies no physiological or body-interface microclimate while sensor placement is unconfirmed. The
section heading "Smart Bedding, Pressure Sensing and Microclimate Monitoring" (Section 2.1) keeps the term, because it
describes the clinical literature. The cover-letter draft still carries the earlier title and is updated when the
cover letter is finalized.
