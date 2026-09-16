# smartmat-mdpi-personalization

Companion research repository for an MDPI journal study on multi-channel smart-mat pressure time series.

## Purpose

Earlier work estimated temperature and relative humidity from a smart mat's six pressure channels. This study asks whether such estimates hold up under strict, deployment-like evaluation, and
whether short user-specific adaptation helps.

## Research Questions

- **RQ1 — Cross-subject generalization:** how well does a model trained on other people estimate
  temperature/humidity for an unseen subject (strict leave-one-subject-out)?
- **RQ2 — Chronological personalization:** does fine-tuning on a user's earliest data improve accuracy on
  that user's later data, and how much adaptation data is needed?
- **RQ3 — Feature contribution:** what do movement-derived and contact-structure features each contribute?

## Research Roadmap

- [x] P0 Dataset Audit & Data Freeze (merged; tag `p0-data-freeze`)
- [x] P1 Domain-shift EDA (merged; `docs/P1_DOMAIN_SHIFT_EDA_REPORT.md`)
- [x] P2 Evaluation Protocol & Split Freeze (merged; tag `p2-protocol-freeze`)
- [x] P3 Strict LOSO Baseline (merged; tag `p3-loso-baseline`; `docs/P3_STRICT_LOSO_BASELINE_REPORT.md`)
- [x] P4 Feature Ablation (merged; tag `p4-feature-ablation`; `docs/P4_FEATURE_ABLATION_REPORT.md`)
- [x] P5 User Personalization (merged; tag `p5-personalization`; `docs/P5_PERSONALIZATION_REPORT.md`)
- [x] P6 Robustness & Statistical Analysis (merged; tag `p6-robustness`; `docs/P6_ROBUSTNESS_STATISTICAL_ANALYSIS_REPORT.md`)
- [x] P7 Reproducibility & Public Data Release (release candidate `public_release_v1` reproduced from a clean checkout;
  `docs/P7_REPRODUCIBILITY_PUBLIC_RELEASE_REPORT.md`; external publication pending the license, hosting and PI
  approval, `docs/P7_PUBLIC_RELEASE_CHECKLIST.md`)
- [x] P8 Manuscript (merged as a PI-review manuscript candidate; `paper/manuscript/manuscript.md`, post-hoc
  analyses `docs/P8_POSTHOC_VALIDATION_REPORT.md` and `docs/P8_DYNAMIC_SIGNAL_REPORT.md`; submission metadata and
  release items open in `docs/P8_FINAL_BLOCKERS.md`; no `v1.0-paper` tag)
- [x] P9 User03 external sensitivity validation (post hoc, D-061; `docs/P9_USER03_EXTERNAL_VALIDATION_REPORT.md`;
  OPEN-29 closed by the provider timestamp confirmation, D-062; reproducibility closed, D-063; on branch
  `experiment/p9-user03-external-validation`, not merged)

Current status: P0 is closed and tagged `p0-data-freeze`.
- The data audit is summarised in `docs/P0_DATASET_AUDIT_REPORT.md`, and the frozen policies are in
  `docs/DECISIONS.md`.
- The canonical interim dataset v1 (parsed, provenance-preserving, de-duplicated, quality-flagged,
  session-labelled) is built with `scripts/build_canonical_v1.py`. Its manifests are committed under
  `data/interim/manifest/`.
- P1 (domain-shift EDA) is complete: `docs/P1_DOMAIN_SHIFT_EDA_REPORT.md`.
- P2 (evaluation protocol and split freeze) is complete: protocol v1.0 (`docs/EXPERIMENT_PROTOCOL.md`), tag
  `p2-protocol-freeze`.
- P3 (strict LOSO baseline) is complete: `docs/P3_STRICT_LOSO_BASELINE_REPORT.md`, tag `p3-loso-baseline`.
- P4 (feature-family comparison, RQ3) is complete: `docs/P4_FEATURE_ABLATION_REPORT.md`, tag `p4-feature-ablation`
  (D-046).
- P5 (chronological user personalization, RQ2) is complete: `docs/P5_PERSONALIZATION_REPORT.md`
  (`scripts/run_p5_personalization.py`; D-045), tag `p5-personalization`.
- P6 (robustness and statistical analysis) is complete: `docs/P6_ROBUSTNESS_STATISTICAL_ANALYSIS_REPORT.md`
  (`scripts/run_p6_robustness.py`; D-047), tag `p6-robustness`. It is analysis-only and changes no P3–P5 result.
- P7 (reproducibility and public data release) is complete as a release candidate:
  `docs/P7_REPRODUCIBILITY_PUBLIC_RELEASE_REPORT.md` (D-049, D-050).
  - The de-identified window release `public_release_v1` reproduces every P3–P6 result from a clean checkout
    (see "Reproducing the results from the public release" below).
  - External publication waits for the license, hosting/DOI and PI approval (`docs/P7_PUBLIC_RELEASE_CHECKLIST.md`).
- P8 (manuscript) is merged as a PI-review candidate: a strict evaluation of smart-mat microclimate estimation
  against simple level baselines (D-057–D-060). Submission metadata, PI approval and the public release remain open
  (`docs/P8_FINAL_BLOCKERS.md`); the `v1.0-paper` tag is not created.
- P9 (post-hoc external sensitivity validation on User03, protocol v1.3, D-061) is complete on its branch: the
  training-mean predictor had a lower error than every source-only RAW-TCN configuration for both targets, with no
  demonstrable within-night co-variation. It is not pooled with the primary three-subject results.
  - OPEN-29 is closed (D-062): the data provider confirmed that the setting problem behind the D-017 exclusion does
    not affect the second-level timestamps of the seven paired TXT nights, so the results are no longer conditional.
  - Reproducibility is closed (D-063): all nine models were retrained from scratch under the frozen protocol after
    the prediction-serialization change, and every prediction file is bitwise identical
    (`python scripts/verify_p9_user03_reproduction.py --root <dir>`).
Phase definitions: `docs/RESEARCH_PROTOCOL.md` §5.

## Repository structure

```
docs/       canonical rules, decisions, dataset inventory, phase plans   ← start here (via AGENTS.md)
configs/    paths and the subject/device/source mapping
src/        library code (raw access guard, provenance, parsing, audit)
scripts/    command-line entry points
tests/      pytest suite (subject mapping, raw immutability, provenance, parsing)
data/       raw (local only, git-ignored) · interim · processed · splits
outputs/    generated QA / EDA / metrics / predictions / figures (not committed)
paper/      manuscript, tables and figures (generated from tagged code)
```

## Reproducibility philosophy

- **Raw data are immutable.** Raw data stay local and read-only; every file is checked against a
  committed SHA-256 manifest before any processing.
- **Provenance everywhere.** Every derived record traces back to its raw file, subject and device.
  Subjects appear only under anonymous IDs (`User01`, …).
- **Decide first, then look.** Data policies, splits and the evaluation protocol are frozen and
  recorded (`docs/DECISIONS.md`) before model results are seen. Any later change becomes a new,
  explicit decision.
- **Leakage is tested, not assumed.** No subject, session or device-concurrent recording spans train
  and test, and training does not start unless the leakage checks pass.
- **Phases are auditable.** Each phase ends with a Pull Request that records its purpose, decisions,
  findings and validation. Freeze points are tagged.

## Setup

```bash
python -m pip install -r requirements.txt
python scripts/build_manifest.py     # verify raw files against the committed manifest
python scripts/audit_dataset.py      # inventory audit -> outputs/qa/dataset_audit/
python scripts/build_canonical_v1.py # canonical interim dataset v1 -> data/interim/canonical_v1/ (+ manifests)
python -m pytest
```

Raw data are not distributed with this repository (`data/raw/README.md`).

## Reproducing the results from the public release

`public_release_v1` (D-049, D-050) holds the model-ready windows, the public split copies and the reference digests.
It is enough to re-run the frozen P3–P6 results without the raw data or canonical_v1. The package metadata is under
`data/release/public_release_v1/`. `windows.parquet` (30 MB) is distributed separately: its hosting is pending
(`docs/P7_PUBLIC_RELEASE_CHECKLIST.md`), and the data owner can rebuild it byte for byte with
`scripts/build_public_release.py`. Columns and files: `docs/P7_PUBLIC_DATA_DICTIONARY.md`.

```bash
python -m pip install -r requirements.txt           # plus the torch build that matches your CUDA
python scripts/validate_public_release.py --data data/release/public_release_v1
python scripts/reproduce_public_release.py --data data/release/public_release_v1 --tier core
python scripts/reproduce_public_release.py --data data/release/public_release_v1 --tier extended
```

- **Tiers:**
  - `core` re-trains the 9 frozen P3 RAW-TCN models, re-runs the 45 P5 personalization runs and the P6 analysis.
  - `extended` also re-trains the 45 frozen P4 feature-family models.
  - Both use the committed selections and the frozen P5 plan. Neither re-runs a hyperparameter search.
- **Checks:** every prediction file bitwise against the release's reference digests, the P3 weights against the P5
  plan, and every paper table cell by cell against its committed version. The summary goes to
  `outputs/p7/reproduction/p7_reproduction_summary.json`. Exit code 0 only if every check passes.
- **Needs:** a git checkout of this repository and the release directory. Interrupted runs resume.

Environment used for the P3–P7 results and for the P7 verification:

| Component | Version / setting |
|---|---|
| OS | Windows 11 (10.0.26200) |
| Python | 3.12.1 |
| Packages | numpy 2.4.4, PyYAML 6.0.3, pyarrow 24.0.0, torch 2.12.0+cu126, matplotlib 3.10.9, pytest 9.0.2 (`requirements.txt`) |
| GPU | NVIDIA GeForce RTX 4060 Ti 16 GB, driver 581.29, CUDA 12.6, cuDNN 9.10.2 |
| Determinism | `CUBLAS_WORKSPACE_CONFIG=:4096:8` (set by the scripts), `torch.use_deterministic_algorithms(True)`, cuDNN deterministic, benchmark off, per-run seeds, no data-loader workers |
| Run time | core about 8 min on this GPU (P3 finals about 4.3 min, P5 about 3.3 min, P6 about 10 s); extended adds about 30 min (45 P4 finals); a release build by the data owner takes about 2 min |
| Disk | release package 30.6 MB; reproduction outputs about 370 MB (core) and 660 MB (extended); about 4 GB RAM and 2.2 GB GPU memory per process |

## Manuscript production (P8)

The manuscript tables, figures and submission candidate are generated from the frozen `paper/tables/` only;
no result is recomputed (D-054). The code is in `src/paper/`.

```bash
python scripts/export_manuscript_tables.py      # Tables 1–5 and S1–S19 -> paper/manuscript/generated/
python scripts/render_manuscript_figures.py     # Figures 1–4 and S1–S4 -> paper/manuscript/generated/figures/
python scripts/build_submission_candidate.py    # rendered manuscript and staging directory -> paper/submission_candidate/
python scripts/validate_manuscript_results.py   # read-only checks; exit code 0 only if all pass (--final: submission-ready)
python scripts/build_submission_docx.py --template <Applied Sciences Word template .docx>   # -> outputs/p8/submission/
```

Open submission and release items: `docs/P8_FINAL_BLOCKERS.md`.

Bitwise equality is verified on this stack only. A CPU run or another GPU, driver or library build trains in the
same deterministic way, but its floating-point results can differ in the last bits. The digest checks then fail,
and the table checks show the size of the difference. The figures are compared as well, for information only:
their PNG bytes depend on the local fonts and matplotlib build.
