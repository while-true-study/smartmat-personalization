# P8 — Title candidates

> **No final title is fixed** (PI decision). The candidates are ranked against five criteria:
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
- **No final title is fixed.** This is a PI decision (`docs/P8_FINAL_BLOCKERS.md` item 16).

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
