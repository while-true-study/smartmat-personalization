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

- [ ] P0 Dataset Audit & Data Freeze  ← **current phase** (`research/p0-data-freeze`)
- [ ] P1 Domain-shift EDA
- [ ] P2 Evaluation Protocol & Split Freeze
- [ ] P3 Strict LOSO Baseline
- [ ] P4 Feature Ablation
- [ ] P5 User Personalization
- [ ] P6 Robustness & Statistical Analysis
- [ ] P7 Reproducibility & Public Data Release
- [ ] P8 Manuscript & Final Release

Current status: the raw data have been inventoried (`docs/initial_dataset_inventory.md`), and P0
provenance and quality questions are open (`docs/P0_DATASET_AUDIT_PLAN.md`, `docs/DECISIONS.md`).
No preprocessing, splitting or model training has been done, so there are no results yet.
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
python -m pytest
```

Raw data are not distributed with this repository (`data/raw/README.md`).
