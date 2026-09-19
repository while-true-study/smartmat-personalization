# Institutional Review Board statement — variants (checklist item M14; requests C01, C02)

Five drafts, one for each possible outcome. **None is selected.**
- The IRB or ethics office's answer decides which one applies.
- If none fits, the authors write the statement from the answer.
- "Not applicable" is not offered as a default.

**How to use:**
1. In `METADATA_VALUES_TEMPLATE.yaml`, set `M14.fields.variant` to A–E.
2. Fill the four fields, exactly as in the ethics office's document:
   - `ETHICS_INSTITUTION`: the institution whose board or office decided;
   - `ETHICS_REFERENCE_NUMBER`: the approval, exemption, waiver or determination number;
   - `ETHICS_DATE`: the date of that decision;
   - `SECONDARY_USE_BASIS`: the permission or agreement under which the recordings were used for this study.
3. Set the status to CONFIRMED and record the source.

The tool inserts the chosen text as the Institutional Review Board Statement. The same fields are used by the consent
variants.

### Variant A — Formal IRB approval

```text
The study was approved by the Institutional Review Board of {{ETHICS_INSTITUTION}} (approval number {{ETHICS_REFERENCE_NUMBER}}, {{ETHICS_DATE}}). The recordings were used for this study on the following basis: {{SECONDARY_USE_BASIS}}.
```

### Variant B — IRB exemption

```text
The study was exempted from review by the Institutional Review Board of {{ETHICS_INSTITUTION}} (exemption number {{ETHICS_REFERENCE_NUMBER}}, {{ETHICS_DATE}}). The recordings were used for this study on the following basis: {{SECONDARY_USE_BASIS}}.
```

### Variant C — Waiver

```text
The Institutional Review Board of {{ETHICS_INSTITUTION}} waived the requirement for ethical review of this study (waiver number {{ETHICS_REFERENCE_NUMBER}}, {{ETHICS_DATE}}). The recordings were used for this study on the following basis: {{SECONDARY_USE_BASIS}}.
```

### Variant D — Secondary analysis under prior approval

```text
This secondary analysis was conducted under the approval granted by the Institutional Review Board of {{ETHICS_INSTITUTION}} for the original data collection (approval number {{ETHICS_REFERENCE_NUMBER}}, {{ETHICS_DATE}}). The recordings were used for this study on the following basis: {{SECONDARY_USE_BASIS}}.
```

### Variant E — Institutional determination that review was not required

```text
The Institutional Review Board of {{ETHICS_INSTITUTION}} determined that this study did not require ethical review (determination number {{ETHICS_REFERENCE_NUMBER}}, {{ETHICS_DATE}}). The recordings were used for this study on the following basis: {{SECONDARY_USE_BASIS}}.
```
