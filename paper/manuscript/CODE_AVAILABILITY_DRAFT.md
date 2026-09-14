# Code Availability — draft

> **Status: draft.** The public release scope of the code repository is not decided.
> - The repository contains session-level calendar dates in committed files outside the release package: the split
>   files, the personalization plan, the subject mapping, three result tables and the phase reports (P7 checklist
>   D4).
> - It has no LICENSE file (P7 checklist D1).
> - This statement must therefore not say that the whole repository is public or archived. Final repository
>   publication is a tracked blocker (docs/P8_MANUSCRIPT_PLAN.md §9).

## Draft text (current state)

> The code used for data preparation, model training, evaluation and the reproduction of all reported results
> (P3–P7 pipelines, the public-release builder, validator and reproduction scripts) is maintained in a version-controlled
> repository.
>
> The analysis state reported in this article corresponds to the repository checkpoint `p7-release-candidate`; the
> final manuscript state will be tagged `v1.0-paper`.
>
> Public availability of the code, and its license, are pending [PI DECISION]. Code repository: [CODE REPOSITORY].
> Archive DOI: [DOI]. License: [LICENSE].

## Facts the statement may rely on (P7)

- **Reproduction:**
  - `scripts/reproduce_public_release.py --tier core|extended` reproduces the P3–P6 results from `public_release_v1`
    alone;
  - from a clean checkout, 118/118 (core) and 171/171 (extended) checks passed;
  - 102 prediction files match bitwise;
  - the 9 P3 model weights match their frozen digests.
- **What is reused:** the frozen hyperparameter selections. The inner searches are not part of the reproduction.
- **Environment** (README): Python 3.12.1, PyTorch 2.12.0 (CUDA 12.6), deterministic settings. Bitwise equality is
  verified on the recorded GPU stack only.

## Open items

| Item | Owner | Reference |
|---|---|---|
| Code license | PI | P7 checklist D1 |
| Public scope of repository content with calendar dates (keep private, publish a de-identified copy, or accept) | PI | P7 checklist D4 |
| Code archive (e.g. a DOI-issuing archive) | PI | — |
