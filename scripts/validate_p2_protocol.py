"""Run the leakage validation gate on the frozen v1.0 splits (RESEARCH_PROTOCOL L1–L12, D-042).

Canonical-only; no model, prediction or error metric. Checks:
  - split files against their SHA-256 manifest and against the canonical session structure (L1, L2, L4–L8);
  - a declared protocol run context per LOSO fold and per personalization subject/budget: admissible inputs
    (L9, L10), training-only target-scaler provenance (L3, L11), inner-validation subjects (L4);
  - windows built inside every partition with the v1.0 rule and validated against session, phase, night, partition
    and max-gap boundaries (L1); structural window counts per partition.
Exit code 0 only if every check passes (fail closed). Report: outputs/qa/p2/leakage_check.json,
outputs/qa/p2/partition_windows.csv (not committed).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.evaluation.canonical_input import verify_canonical  # noqa: E402
from src.evaluation.leakage import CheckResult, GateReport, RunContext, run_gate  # noqa: E402
from src.evaluation import splits as S  # noqa: E402
from src.evaluation.p2_protocol import load_manifest, load_structure, partition_windows, split_root  # noqa: E402
from src.evaluation.protocol import cohort, load_protocol, outer_folds, window_spec  # noqa: E402
from src.features.pressure_features import family_features  # noqa: E402


def declared_contexts() -> list[RunContext]:
    """The run contexts protocol v1.0 prescribes (what P3–P5 runners will declare)."""
    cfg = load_protocol()
    ctxs = []
    for fold, held in outer_folds().items():
        train = [s for s in cohort() if s != held]
        for fam in cfg["inputs"]["families"]:
            ctxs.append(RunContext(
                scheme="loso", fold=fold, input_features=list(family_features(fam)),
                fit_records=[{"transform": "target_zscore", "partition": "train", "subjects": train},
                             {"transform": "target_zscore", "partition": "inner_train", "subjects": [train[0]]},
                             {"transform": "target_zscore", "partition": "inner_train", "subjects": [train[1]]}],
                selection_subjects=train))
    for subj in cohort():
        others = [s for s in cohort() if s != subj]
        ctxs.append(RunContext(scheme="personalization", subject=subj, input_features=list(family_features("RAW")),
                               fit_records=[{"transform": "target_zscore", "partition": "train", "subjects": others}],
                               selection_subjects=others))
    return ctxs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=0, help="recorded for convention; the gate is deterministic")
    args = ap.parse_args()
    cfg = load_protocol()
    verified = verify_canonical()
    st = load_structure(with_flags=True)
    sessions, pieces = st.sessions(), st.pieces()
    root = split_root()
    manifest = load_manifest(root)
    full = GateReport(cfg["protocol_version"])
    base = run_gate(root, manifest, cfg, sessions, pieces, None, verified)
    full.checks += base.checks
    for ctx in declared_contexts():
        rep = run_gate(root, manifest, cfg, sessions, pieces, ctx, verified)
        tag = f"loso fold {ctx.fold}" if ctx.scheme == "loso" else f"personalization {ctx.subject}"
        fam = "+".join(sorted({f.split('_')[0] for f in ctx.input_features}))
        for c in rep.checks[len(base.checks):]:
            full.checks.append(CheckResult(f"{c.check} [{tag}; {len(ctx.input_features)} inputs {fam}]", c.rule,
                                           c.passed, c.detail))
    # windows inside partitions, built from the split files on disk (L1)
    tables = {rel: (S.read_split(root / rel), []) for rel in S.SPLIT_FILES}
    counts = []
    try:
        for d in [cfg["window"]["duration_s"]]:
            counts = partition_windows(st, tables, window_spec(d))
        full.checks.append(CheckResult("windows_built_and_validated_inside_partitions", "L1", True,
                                       f"{sum(r['windows'] for r in counts if r['scheme'] == 'loso_outer')} LOSO "
                                       "window assignments validated (session/phase/partition/night/max-gap)"))
    except Exception as exc:                                   # fail closed
        full.checks.append(CheckResult("windows_built_and_validated_inside_partitions", "L1", False, str(exc)))
    pressure_ok = bool(np.all(st.pressure_ok))
    full.checks.append(CheckResult("pressure_rows_valid_4095_retained", "D-018/D-033", pressure_ok,
                                   "all primary rows pressure_valid; no row removed or clipped" if pressure_ok
                                   else "invalid pressure rows present"))
    if verify_canonical() != verified:
        full.checks.append(CheckResult("canonical_unchanged_during_gate", "L7", False, "canonical_v1 changed"))
    out = paths.repo_path("outputs/qa/p2")
    write_json(out / "leakage_check.json", {"seed": args.seed, "canonical": verified, **full.to_dict()})
    if counts:
        cols = list(counts[0])
        write_csv(out / "partition_windows.csv", counts, cols)
    for c in full.checks:
        if not c.passed:
            print(f"FAIL {c.check} ({c.rule}): {c.detail}")
    print(f"leakage gate: {len(full.checks) - len(full.failures())}/{len(full.checks)} checks passed"
          f" -> {'PASS' if full.passed else 'FAIL'}")
    return 0 if full.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
