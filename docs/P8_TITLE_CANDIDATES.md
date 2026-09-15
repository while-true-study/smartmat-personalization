# P8 — Title candidates

> **Working title (dynamic-signal diagnostic, D-060):** "Strict Unseen-Domain Evaluation of Smart-Mat Microclimate
> Estimation against Simple Level Baselines" (§7). It replaced the D-058 title, which had replaced the D-054 title;
> PI confirmation is required, and the PI may choose any recorded candidate. The history below is kept.

> **History.** Before the working title was set, the candidates were ranked against five criteria:
> 1. framing priority: chronological personalization under unseen-user/domain shift, then benefit **and** negative
>    transfer, then smart-mat temperature/humidity estimation;
> 2. no population-level or robustness overstatement;
> 3. Applied Sciences style (descriptive, searchable);
> 4. clear differentiation from the conference title "Robust Temperature and Humidity Estimation from Smart Bedding
>    Pressure Sequences Using Movement and Contact-Structure Features";
> 5. length.

## Top 3 (second pass)

| Rank | Title | Novelty signal | Precision | Overclaim risk | Conference differentiation |
|---|---|---|---|---|---|
| 1 | **Chronological Personalization under Unseen-User Domain Shift: Offset Correction and Negative Transfer in Smart-Mat Temperature and Humidity Estimation** | high: names the new question (personalization under unseen-user shift) and both outcomes | high: every term maps to a result (offset correction: User02; negative transfer: User07, User01) | low: no claim that personalization works in general | strong: shares no framing words with the conference title except the task |
| 2 | **When Does User Adaptation Help? Chronological Personalization of Smart-Mat Temperature and Humidity Estimation under Unseen-User Domain Shift** | high: the question form signals the conditional finding | medium: "help" is informal; the negative outcome is only implied | low | strong |
| 3 | **Limited-Data User Adaptation for Smart-Mat Temperature and Humidity Estimation: Benefits and Negative Transfer under Temporal Drift** | medium: "temporal drift" signals the mechanism | medium-high: "under temporal drift" could be read as a tested cause; the drift association is descriptive | medium: see precision | strong |

- **Recommendation:** rank 1. It follows the framing priority exactly, and each noun phrase is supported by a
  frozen result.
- **If the editor prefers a shorter title:** "Chronological Personalization of Smart-Mat Temperature and Humidity
  Estimation: Offset Correction and Negative Transfer" (13 words). It drops "unseen-user domain shift", which the
  abstract must then carry.

## Pass 3 re-evaluation (after the literature review)

- **The terms readers search for** in the reviewed literature are "personalization" / "personalized", "negative
  transfer", "domain adaptation / domain shift", "concept drift", and "smart bed / pressure mat / mattress". Rank 1
  contains three of them plus the task, so it stays first.
- **Novelty signal:** the reviewed personalization and negative-transfer work concerns activity or state recognition.
  Naming temperature/humidity estimation and "chronological" together marks the difference without claiming "first".
- **Audience:** "chronological personalization" is precise but uncommon. The Abstract's first two sentences explain
  it, so the title needs no gloss.
- **Device term:** the literature uses "pressure mat", "pressure-sensing mattress" and "smart bed". "Smart-mat"
  matches this study's device and the conference paper's domain ("smart bedding"). Replacing it with "pressure-mat"
  is an equally precise alternative if the editor prefers.
- **Result:** the ranking is unchanged: 1 > 2 > 3. No final title is fixed (PI).

## Final integration pass: "unseen-user" vs "unseen-domain"

Rank 1 is adopted as the primary candidate. Before the title freeze, two variants were compared:
- **A:** "Chronological Personalization under **Unseen-User Domain Shift**: Offset Correction and Negative Transfer in
  Smart-Mat Temperature and Humidity Estimation" (17 words, 150 characters).
- **B:** "Chronological Personalization under **Unseen-Domain Shift**: Offset Correction and Negative Transfer in
  Smart-Mat Temperature and Humidity Estimation" (16 words, 145 characters).

| Criterion | A (unseen-user) | B (unseen-domain) |
|---|---|---|
| Distinct from the conference title | yes: shares only the task words | yes: the same |
| Central novelty is personalization / negative transfer | yes | yes |
| No population claim | yes | yes |
| Length | 17 words | 16 words |
| Risk of reading the shift as a pure subject (biological) effect | **medium**: "unseen-user" places the cause of the shift in the person, but subject, recording period, season and mat are confounded in every fold (§3.1 of the manuscript) | **low**: matches the manuscript's own wording ("combined unseen-domain shift, not a pure subject effect") |
| Search terms | "unseen user" is common in the personalization literature | "domain shift" is kept; "personalization" already signals the user level |
| Precision against the evidence | the folds are defined by subject, so literally correct for the design, not for the interpretation | correct for both the design and the interpretation, once the Abstract says that each held-out fold combines a new subject, recording period and mat (it does) |

- **Recommendation: B, "…under Unseen-Domain Shift…".** It is technically more precise for a confounded
  subject–period–season–device shift and one word shorter. It loses no framing term: "Personalization" carries the
  user, and the Abstract defines the domain.
- **A stays the alternative** if the PI prefers the user-level wording for searchability. In that case, the Abstract
  and §3.1 already state that the shift is combined.
- The shorter fallback is unaffected, because it drops the shift phrase altogether: "Chronological Personalization
  of Smart-Mat Temperature and Humidity Estimation: Offset Correction and Negative Transfer".
- Adopted as the working final title in the formatting pass (D-054). The PI may still change it (`docs/P8_FINAL_BLOCKERS.md` B10).

## 6. Post-hoc validation re-evaluation (D-058)

The post-hoc validation plan (`docs/P8_POSTHOC_VALIDATION_PLAN.md` §8) fixed in advance that the title would be
re-evaluated after the results, with an evaluation-focused title favoured if the simple baselines dominated. The
results (`docs/P8_POSTHOC_VALIDATION_REPORT.md` §5–§6):
- a personalized constant was not worse than full fine-tuning in half of the subject × target × budget cells, including
  the case the old subtitle's "Offset Correction" rests on (User02 temperature);
- the pressure-based models showed no demonstrable within-subject tracking (residual-variation ratio about 1 or more);
- cross-subject pretraining added little over a scratch control;
- the training mean beat the neural models for every strict-LOSO temperature cell.

The simple baselines do not dominate every cell, but they match or beat the neural approach often enough that the
paper's contribution is the evaluation, not a demonstration of personalization.

| Criterion | D-054 title: "Chronological Personalization under Unseen-Domain Shift: Offset Correction and Negative Transfer in Smart-Mat Temperature and Humidity Estimation" | Proposed: "Evaluating Chronological Personalization for Smart-Mat Microclimate Estimation under Unseen-Domain Shift" |
|---|---|---|
| Accuracy of each term | "Offset Correction" is true of the outcomes, but, attached to personalization, reads as a capability of the neural adaptation; the constant comparator achieved the same correction | every term is neutral and true: an evaluation of chronological personalization, for microclimate estimation, under the confounded shift |
| Overclaim risk after the post-hoc results | low–medium: implies that personalization is the mechanism of offset correction | low: states the design, not an outcome |
| Signals the negative result | partly ("Negative Transfer") | through "Evaluating"; the negative result is in the Abstract |
| Search terms | personalization, domain shift, negative transfer, temperature, humidity | personalization, domain shift, microclimate; "negative transfer" moves to the keywords |
| Distinct from the conference title | yes | yes |
| Length | 16 words | 13 words |
| Precision of "microclimate" | — | the targets are the mat-surface temperature and relative humidity, i.e. the bed microclimate (Section 3.1); the Abstract names both quantities |

- **Recommendation: adopt the proposed title.** It is shorter, makes no outcome claim that the post-hoc comparators
  weaken, and matches the paper's reframed contribution: an evaluation with a substantial negative result.
- **Adopted as the working title (D-058)**, explicitly and not silently; the change is listed in the PI review request
  and the PI checklist.
- **The PI may restore the D-054 title.** It remains accurate as a description of the primary outcomes; it would then
  need the Abstract to carry the comparator result, which it already does.
- **Keywords:** "negative transfer" and "baseline comparison" were added so the search terms of the D-054 subtitle are
  not lost.

## Earlier candidates (first pass), for the record

| Candidate | Why not in the top 3 |
|---|---|
| Chronological Personalization for Smart-Mat Temperature and Humidity Estimation under Unseen-User Domain Shift: Offset Correction and Negative Transfer | merged into rank 1 (word order improved) |
| When User Adaptation Helps or Hurts: Chronological Personalization of Smart-Mat Temperature and Humidity Estimation | drops the unseen-user half |
| Cross-Subject Generalization and Chronological Personalization of Temperature and Humidity Estimation from Smart-Mat Pressure Sequences | does not signal the negative-transfer finding |
| Chronological Personalization for Smart-Mat Temperature and Humidity Estimation under Unseen-User Domain Shift | could be read as "personalization works" |
| Robust Temperature and Humidity Estimation from Smart-Mat Pressure Sequences under Cross-Subject Shift and Chronological Personalization | "robust" overclaims and repeats the conference title's first word. **Rejected.** |
| Level Offsets, Temporal Drift and Few-Night Personalization in Smart-Mat Temperature and Humidity Estimation | less searchable; "few-night" reads as a success claim |

**Avoid in any title:**
- robust personalization;
- "universally improved";
- few-shot success;
- population generalization;
- "first" or "novel";
- the conference title's lead phrase "Robust Temperature and Humidity Estimation".

## 7. Final re-evaluation after the dynamic-signal diagnostic (D-060)

The task fixed the decision rule before the results:
- if within-night co-variation (J3) is not consistently supported and simple level baselines remain the dominant
  practical comparator, strongly favour the neutral baseline/evaluation title;
- if clear within-night co-variation exists across subjects and targets, keep a formulation that allows a
  calibration or dynamic-signal interpretation.

**Result** (`docs/P8_DYNAMIC_SIGNAL_REPORT.md`):
- J3 held in one cell only (the scratch control for User02 temperature);
- no condition met the headline rule of at least two subjects;
- pooled associations were level alignments;
- the oracle affine ratio was at least 0.93 everywhere;
- simple level baselines remain the practical comparator.
The first branch applies.

| Candidate | Accuracy after v1.2 | Overclaim risk | Signals the baseline comparison | Words |
|---|---|---|---|---|
| **"Strict Unseen-Domain Evaluation of Smart-Mat Microclimate Estimation against Simple Level Baselines"** (preferred neutral) | every term true: strict unseen-domain evaluation, the task, and the comparator that decides the result | low: states the design and the comparator, not an outcome | yes, in the title | 13 |
| "Evaluating Pressure-Based Smart-Mat Microclimate Estimation against Simple Level Baselines under Unseen-Domain Shift" (alternative) | true; names the input modality | low | yes | 14 |
| "Evaluating Chronological Personalization for Smart-Mat Microclimate Estimation under Unseen-Domain Shift" (D-058) | true, but centres personalization, which is now one condition among several | low–medium: implies personalization is the object whose value is at stake | no | 13 |
| "Chronological Personalization under Unseen-Domain Shift: Offset Correction and Negative Transfer in …" (D-054) | the outcomes are true, but it frames offset correction as a capability of the neural adaptation | medium after v1.1/v1.2 | no | 16 |

- **Recommendation: the preferred neutral candidate.** It puts the strict evaluation and the simple level baselines,
  the two things that decide the paper's result, in the title.
- **The alternative** is acceptable if the PI prefers to name pressure explicitly. The Abstract names it in either
  case.
- "Personalization" and "negative transfer" remain in the Abstract, the body and the keywords.
- **Adopted as the working title (D-060)**, explicitly. PI approval is pending.
