# AGENTS.md

Entry point for any contributor or coding agent. This file defines no rules itself.

Before doing anything, read the canonical documents in `docs/`:

1. `docs/DATA_POLICY.md` — raw-data immutability, subject/device mapping, privacy, dataset roles
2. `docs/RESEARCH_PROTOCOL.md` — research questions, research lifecycle P0–P8, evaluation principles, leakage rules
3. `docs/EXPERIMENT_PROTOCOL.md` — split / preprocessing / LOSO / personalization protocol (check its status)
4. `docs/CONVENTIONS.md` — code, layout, artifacts, naming, Git workflow (branches, PRs, tags, commits)
5. `docs/DECISIONS.md` — decisions and open questions

Current phase and its plan: see the roadmap in `README.md` and `docs/P0_DATASET_AUDIT_PLAN.md`.

Machine-readable sources of truth: `configs/subject_mapping.yaml`, `configs/paths.yaml`,
`data/interim/manifest/raw_file_manifest.csv`.

If a task conflicts with these documents, belongs to a later phase, or needs a decision listed as open
in `docs/DECISIONS.md`, stop and ask instead of choosing.
