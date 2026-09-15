# Conference-extension disclosure — draft

> **Status: draft for the PI.** Bibliographic items not found in the available sources stay as placeholders.
> - Applied Sciences (authors' check of the official pages): current Special Issue pages publish extended conference papers and
>   exempt conference proceedings papers from the previous-publication exclusion.
> - No journal-wide rule on the amount of new content was found, and no percentage is claimed. The 50 % rule of an
>   older conference-specific Special Issue is not adopted (`docs/P8_APPLIED_SCIENCES_REQUIREMENTS.md`, items 15–16).
> - The full cover letter is `COVER_LETTER_DRAFT.md`.

## At a glance

| Conference study | Journal study |
|---|---|
| pragmatic fixed-length sequences | strict elapsed-time 40-s windows |
| subjects with timestamp-limited (minute-resolution) logs included | timestamp-complete primary cohort from an audited canonical dataset |
| movement/contact late-fusion framework | movement/contact representations re-evaluated as six feature families, each with frozen nested selection |
| no strict elapsed-time leave-one-subject-out evaluation | strict leave-one-subject-out evaluation with a training-mean reference and a leakage gate |
| no target-user fine-tuning | chronological personalization (0–14 nights, fixed future test span) with a negative-transfer analysis |
| — | night-level robustness analyses; post-hoc comparators (personalized constant, offset-calibrated base model, scratch initialization control) with a residual-variation analysis; a de-identified reproduction package (release candidate) |

## Conference paper

| Item | Value |
|---|---|
| Title | Robust Temperature and Humidity Estimation from Smart Bedding Pressure Sequences Using Movement and Contact-Structure Features |
| Authors | Dong-Hoon Maeng, Jin-Suk Bang |
| Venue | The 18th International Conference on Future Information & Communication Engineering (ICFICE 2026), ANA Crowne Plaza Sapporo, Japan, 7–10 July 2026 (oral, AI-06); source: the official KIICE ICFICE 2026 programme |
| Proceedings | Proceedings of ICFICE 2026, Vol. 17, No. 1, pp. 27–30; e-ISSN 2765-3811, print ISSN 2384-3004; issued by the Korea Institute of Information and Communication Engineering (KIICE) |
| DOI / article URL | none confirmed; none is given (open check, not blocking the citation) |
| Copyright holder | [COPYRIGHT HOLDER — CONFIRM] |

## What the conference paper evaluated

- A TCN fusion framework: raw pressure plus movement-derived and contact-structure feature branches, for temperature
  and humidity regression.
- The evaluation used fixed-length pressure sequences, because two users' logs lacked second-level timestamps. The
  paper itself excludes a strict elapsed-time or strict LOSO interpretation.
- User-adaptive fine-tuning was not evaluated; it was named as future work, together with strict time-based LOSO.

## What the journal manuscript adds

- **New data processing:**
  - an audited dataset rebuilt from the raw logs, with provenance, de-duplication, sessions and validity flags;
  - a primary cohort with second-level timestamps: three subjects, one of them recorded on two mats;
  - explicit auxiliary / excluded source policies.
- **New evaluation:**
  - strict elapsed-time windows;
  - strict leave-one-subject-out evaluation with nested source-only model selection, compared with a
    training-mean predictor;
  - an automated leakage gate.
- **Re-evaluated concepts:** movement-derived and contact-structure representations, as six feature families under
  the strict protocol.
- **New experiments:** chronological user personalization with 0, 1, 3, 7 and 14 adaptation nights and a fixed
  future test span.
- **New analyses:**
  - night-level paired bootstrap uncertainty;
  - seed and start-span sensitivity;
  - a post-hoc temporal level-mismatch analysis;
  - device residual strata;
  - post-hoc comparators, a residual-variation analysis and a dynamic-signal diagnostic, each fixed before it was
    computed;
  - a de-identified reproduction package with clean-checkout reproduction.
- **New conclusions:**
  - under strict unseen-domain evaluation, the error is dominated by level offsets that representation changes do
    not remove;
  - chronological personalization corrects them when the early nights represent later conditions, and produces
    negative transfer when they do not;
  - the gains are mainly level corrections that a constant computed from the adaptation nights often matches, and
    the pressure-based models show no demonstrable within-subject tracking of temperature or humidity;
  - relative improvements among pressure representations, as reported in the conference paper, do not by themselves
    establish superiority over simple level baselines under strict evaluation. The conference results are not
    disputed.

## Reuse

| Item | Status |
|---|---|
| Concepts | the task, the TCN family and the movement/contact feature ideas are reused and cited |
| Data | the journal uses the same data provider's recordings, rebuilt from the raw logs into an audited dataset. The conference data without second-level timestamps are consistent with the retained legacy minute-resolution lineage, which the journal keeps as auxiliary and does not use; exact file-level identity is not assumed. An auxiliary five-channel source excluded from the main six-channel evaluation is not used either |
| Model components | re-implemented under the journal protocol; no trained conference model is reused |
| Text | none reused. Abstract, Introduction and Conclusions are newly written |
| Figures | none reused |
| Tables | none reused; no conference number appears in the journal |
| Copyright check | [PENDING: confirm the copyright holder and whether any permission is needed; none expected if nothing is reused] |

## Cover-letter paragraph (draft)

> This manuscript is an extended version of our conference paper "Robust Temperature and Humidity Estimation from
> Smart Bedding Pressure Sequences Using Movement and Contact-Structure Features", presented at ICFICE 2026
> (Proceedings of ICFICE 2026, Vol. 17, No. 1, pp. 27–30). The conference paper is cited in the manuscript and noted on its
> first page.
>
> The conference study examined movement and contact-structure feature fusion on fixed-length pressure sequences.
> Because some logs lacked second-level timestamps, it did not perform strict elapsed-time or leave-one-subject-out
> evaluation, and it left user-adaptive fine-tuning to future work.
>
> The present manuscript addresses exactly these questions with new data processing, new experiments and new
> analyses:
> - a rebuilt, audited canonical dataset with a timestamp-complete primary cohort and strict elapsed-time windows;
> - strict leave-one-subject-out evaluation with frozen nested model selection, a training-mean reference and a
>   leakage gate;
> - a re-evaluation of the movement and contact representations under this protocol;
> - chronological user personalization with 0–14 adaptation nights on a fixed future test span, with a
>   negative-transfer analysis: it shows both large offset corrections and negative transfer;
> - night-level uncertainty and sensitivity analyses;
> - post-hoc comparators showing that the gains are mainly level corrections, which a personalized constant often
>   matches;
> - a de-identified reproduction package, prepared as a release candidate (its public release is pending).
>
> No text, figure or table of the conference paper is reused, and its results are not compared numerically with the
> journal results. [PI: confirm the copyright status.]
