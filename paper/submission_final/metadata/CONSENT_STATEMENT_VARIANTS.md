# Informed consent statement — variants (checklist item M15; request C03)

Four drafts, one for each possible consent situation. **None is selected.**
- The answer from the IRB or ethics office and the data provider decides which one applies.
- If none fits, the authors write the statement from the answer.
- "Not applicable" is not offered as a default.

**How to use:**
1. In `METADATA_VALUES_TEMPLATE.yaml`, set `M15.fields.variant` to 1–4.
2. The fields come from item M14 (`ETHICS_INSTITUTION`, `ETHICS_REFERENCE_NUMBER`, `ETHICS_DATE`,
   `SECONDARY_USE_BASIS`).
3. Set the status to CONFIRMED and record the source.

### Variant 1 — Written informed consent obtained

```text
Written informed consent was obtained from all subjects involved in the study.
```

### Variant 2 — Consent covered by the original protocol

```text
Informed consent was obtained from all subjects under the protocol of the original data collection, approved by the Institutional Review Board of {{ETHICS_INSTITUTION}} (approval number {{ETHICS_REFERENCE_NUMBER}}), which covers the use of the recordings in this study.
```

### Variant 3 — Consent waived by the IRB

```text
The requirement for informed consent was waived by the Institutional Review Board of {{ETHICS_INSTITUTION}} (waiver number {{ETHICS_REFERENCE_NUMBER}}, {{ETHICS_DATE}}).
```

### Variant 4 — Secondary-use dataset under approved conditions

```text
This study analysed a de-identified secondary-use dataset under the approved conditions for its use: {{SECONDARY_USE_BASIS}}.
```
