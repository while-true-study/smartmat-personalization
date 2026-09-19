# Final metadata reconciliation gates

This policy governs how external answers enter the final submission. The records live in
`METADATA_VALUES_TEMPLATE.yaml` (`reconciliation_gates`). The rules are enforced by
`scripts/apply_submission_metadata.py --final` and `scripts/validate_submission_metadata.py`
(logic: `src/paper/submission_metadata.py`).

## 1. Two kinds of external metadata

**A. Slot values.** Examples:
- author names and order, affiliations, corresponding author, ORCID;
- funding statement and identifiers, acknowledgments, conflicts of interest, CRediT roles;
- submission date, editor name, target section, previous MDPI submissions.

These are handled by YAML substitution alone. The value replaces its token and no other text changes.

**B. Answers that change the truth of existing factual prose.** The frozen P16 manuscript and the cover letter contain
factual sentences written while the information was missing: "not documented", "may be included … subject to approval",
"no … is reused", and the release sentences. An answer can make such a sentence false.

For these, substitution alone must not produce the final build:
- an explicit author decision is required, recorded as a reconciliation gate (R1–R4);
- the affected prose is changed only to match the confirmed facts, and only inside the gate's reconcilable regions;
- the result is checked again: first the scientific-results guard (section 3), then an editorial review of the
  changed sentences and a re-render of the affected pages.

A gate is **RESOLVED** only with an explicit record:
- the outcome;
- who decided, and when;
- the evidence;
- the resolved wording.

This holds even when the answer confirms the current wording. That case is outcome "keep the wording", recorded with
`resolved_wording: CURRENT WORDING RETAINED`. Nothing is resolved by default.

## 2. Immutable versus factually reconcilable content

| IMMUTABLE (never changed by metadata) | FACTUALLY RECONCILABLE (may change only through a resolved gate or a slot token) |
|---|---|
| every result number | sensor specifications (model, accuracy, resolution, response time) |
| Tables 1–11 and S1–S44 | sensor placement description |
| Figures 1–6 and S1–S4 | ethics statement |
| research questions RQ1–RQ3 | informed consent statement |
| statistical analyses | copyright and conference-reuse disclosure |
| model, training and evaluation protocol | authorship, affiliations, funding, CRediT, acknowledgments, conflicts of interest |
| substantive interpretation of the results (Discussion, Conclusions) | data and code availability metadata |

**Equivalence requirement:**
- *Before any factual reconciliation:* the metadata-ready manuscript must be byte-identical to the rendered P16 text,
  except for the 16 placeholder segments. The check is "IMMUTABLE baseline".
- *After a reconciliation:* P16-identical text is no longer required inside the reconcilable regions. The requirement
  is "scientific results and conclusions unchanged": every character outside the regions must be identical to P16 and
  in the same order. Every result, table, figure caption, research question, analysis, protocol description,
  Discussion and Conclusion lies outside the regions.

**Reconcilable regions** (by start and end anchor; all other text is immutable):

| Region | Document | Location | Gate |
|---|---|---|---|
| sensor_methods | manuscript | 3.1, from "The temperature–humidity sensor model, its accuracy," through the sensor-methods sentence | R1 |
| limitation_4 | manuscript | 5.5, Limitation 4 "Sensor metadata" | R1 |
| heater_approval | manuscript | Data Availability, "Aggregate diagnostic results and the analysis code may be included … approval." | R2 |
| data_release | manuscript | Data Availability, data-release sentence | R3 |
| code_release | manuscript | Data Availability, code-release sentence | R3 |
| conference_note | manuscript | front-matter Note on the conference paper, with its M05 token | R4 |
| cover_reuse | cover letter | the Reuse statement | R4 |

**Checks on every edit:**
- it must lie inside a region of its own gate;
- its `from` text must occur exactly once in that region;
- it may not introduce a sensor-position claim ("body–bed interface", "skin interface", "physiological microclimate");
- it may not introduce a heater causal or mechanism claim ("caus…", "thermal mechanism", "heater effect").

## 3. Gates

Each gate records: trigger, affected source location, current statement, external evidence required, allowed
outcomes, author decision (outcome, decided_by, date, evidence), resolved wording and status (OPEN or RESOLVED).

### R1 — Sensor metadata (M06–M10; requests B01–B06)

- **Trigger:** any answer on sensor model, accuracy, resolution, response time, placement in the mat or placement
  relative to the heater, including "not available".
- **Affected locations:** 3.1 (region sensor_methods) and Limitation 4 (region limitation_4).
- **Current statement:** 3.1 says the specifications and position "are not documented in the delivered data and are not
  assumed here"; Limitation 4 says they "were not documented".
- **Evidence required:** a datasheet or a written statement per item, or a written statement that the item is not
  available. An unavailable item is recorded as status UNAVAILABLE, with its source.
- **Allowed outcomes:**
  - **R1-1 — all metadata unavailable:** the current "not documented" wording stays unchanged. The sensor-methods
    sentence (its tokens) is removed automatically, so the text returns exactly to P16. Requires M06–M10 all
    UNAVAILABLE.
  - **R1-2 — some metadata confirmed:**
    - the confirmed specifications are stated in 3.1;
    - only the still-unconfirmed items remain in the "not documented" sentence and in Limitation 4;
    - a sentence that bundles all items ("sensor metadata were not documented") is rewritten where it is no longer true;
    - requires some of M06–M10 CONFIRMED and the rest UNAVAILABLE.
  - **R1-3 — all confirmed:**
    - 3.1 states the actual specifications;
    - the no-longer-true "not documented" statements are removed from 3.1 and Limitation 4;
    - any other unresolved limitation stays (e.g. mat-level targets, no statement on measurement validity or physical
      mechanism);
    - requires M06–M10 all CONFIRMED.
- **Rules for every outcome:**
  - a confirmed placement never introduces "body–bed interface", "skin interface" or "physiological microclimate";
  - a confirmed heater-relative placement never strengthens a heater causal-effect or thermal-mechanism claim. The
    heater-context diagnostic stays descriptive, as in P16.

### R2 — Heater-diagnostic approval (M16; request B08)

- **Trigger:** the data provider's answer on including the aggregate heater-diagnostic results and analysis code.
- **Affected location:** Data Availability (region heater_approval).
- **Current statement:** "Aggregate diagnostic results and the analysis code may be included in the research release,
  subject to final author and data-provider approval."
- **Evidence required:** the written approval or refusal, with any conditions.
- **Allowed outcomes:**
  - **R2-1 — approved:** the sentence stays, or states the actual inclusion.
  - **R2-2 — not approved:** the sentence states that they are not included.
- **Always kept:** the controller-event records are not part of the public release, and the heater-context diagnostic
  cannot be reproduced independently from the public dataset alone.

### R3 — Data and code release (M16; requests B07, A11)

- **Trigger:** the redistribution permission (B07) and the code-release decision (A11).
- **Affected locations:** Data Availability (regions data_release and code_release).
- **Current statement:** the data and code sentences assume a public release with repository, identifier and license.
- **Evidence required:** the written permission and release decision, with repository, persistent identifier and
  license.
- **Allowed outcomes:**
  - **R3-1 — released:** the sentences stay and their tokens are filled.
  - **R3-2 — not released (data or code):** the sentence is replaced by the authors' statement of the actual
    availability. No "available upon request" unless the authors confirm exactly that.
- **Always kept:** the other Data Availability limitations stay as in P16.

### R4 — Conference copyright and reuse (M05; requests C04, C05)

- **Trigger:** the confirmed copyright holder and reuse status (`CONFERENCE_REUSE_CHECK.md`).
- **Affected locations:** the manuscript Note (region conference_note) and the cover-letter Reuse statement (region
  cover_reuse).
- **Current statement:** "no text, table or figure of the conference paper is reused".
- **Evidence required:** the published conference paper and the signed copyright agreement, checked item by item.
- **Allowed outcomes:**
  - **R4-1 — no reuse confirmed:** the current wording is kept.
  - **R4-2 — reuse confirmed:** the Note and the cover letter name the reused material, cite it, and state the
    permission actually obtained.
- **Never guessed:** permission.

## 4. Ethics and consent

The IRB and consent statements are metadata slots with no factual prose in P16 around them (M14, M15). The same
principle applies:
- the variant is chosen only from the actual institutional status confirmed in writing:
  - ethics, `ETHICS_STATEMENT_VARIANTS.md`: A formal approval, B exemption, C waiver, D secondary analysis under prior
    approval, E determination that review was not required;
  - consent, `CONSENT_STATEMENT_VARIANTS.md`: 1–4;
- "Not applicable", "waived" and "exempt" are never selected automatically: there is no default variant, and the final
  build refuses while `variant` is null;
- if no variant fits the institution's answer, the authors write the statement from that answer.

## 5. When `--final` refuses

`python scripts/apply_submission_metadata.py --final` writes nothing and exits with failure if any of the following
holds:
- any M01–M18 or L01–L04 item is not resolved. Resolved means CONFIRMED with every field and a source; or, for the
  sensor items M06–M10 only, UNAVAILABLE with a source.
- any token remains unfilled after the resolved gates' edits;
- the CRediT input is incomplete, or an ethics or consent variant is missing or unknown;
- any gate R1–R4 is OPEN;
- any RESOLVED gate lacks an allowed outcome, decided_by, date or evidence, or has wording that does not match its
  outcome. Outcome R1-1, R1-2 or R1-3 must also match the M06–M10 statuses.
- any edit lies outside its gate's regions, does not match its region exactly once, or introduces a forbidden term;
- any character outside the reconcilable regions differs from P16.

`--build-preview` never refuses. It applies what is resolved and leaves every open token visible.
