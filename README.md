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
- [ ] P4 Feature Ablation  ← **current phase** (`experiment/p4-feature-ablation`)
- [ ] P5 User Personalization
- [ ] P6 Robustness & Statistical Analysis
- [ ] P7 Reproducibility & Public Data Release
- [ ] P8 Manuscript & Final Release

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
- P4 (feature-family comparison, RQ3) is the current phase (`scripts/run_p4_feature_ablation.py`; D-044). Its results
  are recorded in `docs/P4_FEATURE_ABLATION_REPORT.md`, pending the P4 merge.
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
