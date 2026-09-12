# smartmat-mdpi-personalization

Research repository for an MDPI journal study on multi-channel smart-mat pressure time series.
It extends prior pressure-based temperature/humidity regression to test:

1. cross-subject generalization to unseen subjects,
2. chronological user-adaptive fine-tuning,
3. the contribution of movement-derived and contact-structure features.

**Status (2026-09-12):** repository bootstrap and P0 raw-data inventory only. No preprocessing,
splitting, windowing or model training has been done. See `docs/EXPERIMENT_PROTOCOL.md`.

## Start here

- `AGENTS.md` — entry point for contributors and coding agents
- `docs/` — canonical rules: `DATA_POLICY`, `RESEARCH_PROTOCOL`, `EXPERIMENT_PROTOCOL`, `CONVENTIONS`, `DECISIONS`
- `docs/initial_dataset_inventory.md` — what the raw data contain and the issues found

## Setup

```bash
python -m pip install -r requirements.txt
python scripts/build_manifest.py     # checksum manifest of raw files (verifies them against the existing one)
python scripts/audit_dataset.py      # P0 inventory audit -> outputs/qa/dataset_audit/
python -m pytest
```

Raw data are not part of this repository. The delivered package is expected at
`스마트 매트 데이터 정리/` (configured in `configs/paths.yaml`) and is read-only.
