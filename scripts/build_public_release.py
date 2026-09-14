"""Build public_release_v1 from the private workspace (D-049, D-050). Logic: src/data/public_release.py.

Needs canonical_v1, the committed v1.0 split files and P5 plan, and the frozen P3/P4/P5 run predictions (for the
reference digests). Writes data/release/public_release_v1/ (windows.parquet is git-ignored; the small metadata is
committed) and outputs/qa/p7/release_build.json. Every privacy check and the private/public equivalence gate must
pass before the manifest is written.
  python scripts/build_public_release.py [--out DIR]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from src.data import paths  # noqa: E402
from src.data import public_release as R  # noqa: E402
from src.data import subject_mapping as M  # noqa: E402
from src.data.io_guard import write_json  # noqa: E402
from src.evaluation import splits as S  # noqa: E402

BUILDER_FILES = ("src/data/public_release.py", "scripts/build_public_release.py")
BASE_TAG = "p6-robustness"
DECISION_FOR_ROLE = {"restricted_metadata": "D-008", "quarantined": "D-023", "auxiliary": "D-023"}


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=paths.PROJECT_ROOT, capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


def excluded_rows() -> list[dict]:
    out = []
    for s in M.sources():
        if s.dataset_role in ("primary_candidate",):
            continue
        reason = s.exclusion_reason or {"restricted_metadata": "restricted_metadata", "quarantined": "quarantined",
                                        "auxiliary": "auxiliary_not_used_by_protocol_v1.0"}[s.dataset_role]
        out.append({"source_id": s.source_id, "subject_id": s.subject_id, "dataset_role": s.dataset_role,
                    "exclusion_reason": reason, "exclusion_confirmed_by": s.exclusion_confirmed_by,
                    "exclusion_decision": s.exclusion_decision or DECISION_FOR_ROLE[s.dataset_role]})
    return sorted(out, key=lambda r: r["source_id"])


def user02_heater_events() -> list[tuple[str, str, int, str]]:
    import pyarrow as pa
    import pyarrow.compute as pc
    from src.evaluation.canonical_input import load_primary
    from src.evaluation.domain_shift import parse_event
    t = load_primary(["subject_id", "device_id", "timestamp", "event_raw"])
    t = t.filter(pc.equal(t["subject_id"].cast(pa.string()), "User02"))
    t = t.filter(pc.fill_null(pc.match_substring_regex(t["event_raw"].cast(pa.string()), "AHON|AHOF"), False))
    dev = t["device_id"].cast(pa.string()).to_pylist()
    ts = t["timestamp"].cast(pa.timestamp("s")).cast(pa.int64()).to_pylist()
    ev = t["event_raw"].cast(pa.string()).to_pylist()
    out = []
    for d, x, e in zip(dev, ts, ev):
        codes = [c for c in parse_event(e)[1] if c in R.HEATER_CODES]
        if codes:
            out.append(("User02", d, int(x), codes[-1]))           # as in p6_robustness.heater_events
    return out


def reference_digests() -> dict:
    root = paths.PROJECT_ROOT / "outputs" / "runs"
    ref = {"description": "SHA-256 of the frozen prediction values (y_true, y_pred float64 in stored order) of the "
                          "private reference runs; the public reproduction must match them bitwise",
           "p3_training_mean": {}, "p3_final": {}, "p4_final": {}, "p5": {}}
    for f in (1, 2, 3):
        ref["p3_training_mean"][f"fold{f}"] = R.prediction_digest(root / "p3" / "training_mean" / f"fold{f}"
                                                                  / "predictions.parquet")
        for s in (0, 1, 2):
            ref["p3_final"][f"fold{f}_seed{s}"] = R.prediction_digest(root / "p3" / "final" / f"fold{f}_seed{s}"
                                                                      / "predictions.parquet")
    for fam in ("movement", "contact", "raw_movement", "raw_contact", "raw_movement_contact"):
        for f in (1, 2, 3):
            for s in (0, 1, 2):
                ref["p4_final"][f"{fam}/fold{f}_seed{s}"] = R.prediction_digest(
                    root / "p4" / fam / "final" / f"fold{f}_seed{s}" / "predictions.parquet")
    for subj in ("User01", "User02", "User07"):
        for b in (0, 1, 3, 7, 14):
            for s in (0, 1, 2):
                ref["p5"][f"{subj}/b{b:02d}_seed{s}"] = R.prediction_digest(
                    root / "p5" / subj / f"b{b:02d}_seed{s}" / "predictions.parquet")
    return ref


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=paths.PROJECT_ROOT / "data" / "release" / R.RELEASE_VERSION)
    a = ap.parse_args()
    from src.evaluation.canonical_input import verify_canonical
    from src.evaluation.p2_protocol import load_manifest
    from src.evaluation.protocol import PROTOCOL_VERSION, load_protocol, protocol_sha256
    from src.training.loso_data import load_rows
    verified = verify_canonical()
    rows = load_rows()
    plan = yaml.safe_load((paths.PROJECT_ROOT / "configs" / "experiments" / "v1.0" / "p5_personalization_plan.yaml")
                          .read_text(encoding="utf-8"))
    raw_rows = S.read_split(paths.PROJECT_ROOT / "data" / "interim" / "manifest" / "raw_file_manifest.csv")
    raw_names = sorted({r["file_name"] for r in raw_rows} | {r["source_relpath"] for r in raw_rows})
    manifest_dir = paths.PROJECT_ROOT / "data" / "interim" / "manifest"
    identity = {
        "protocol_version": PROTOCOL_VERSION, "protocol_sha256": protocol_sha256(),
        "split_manifest_sha256": S.file_sha256_lf(paths.PROJECT_ROOT / "data" / "splits" / "v1.0_manifest.json"),
        "split_sha256": {k: v["sha256"] for k, v in load_manifest()["files"].items()},
        "source_dataset": {"dataset_version": verified["dataset_version"],
                           "primary_content_sha256": verified["content_sha256"]["primary"],
                           "primary_file_sha256": verified["files"]["primary"],
                           "canonical_content_manifest_sha256": S.file_sha256_lf(manifest_dir /
                                                                                 "canonical_v1_content.json")},
        "base_tag": BASE_TAG, "base_tag_commit": git("rev-list", "-n", "1", BASE_TAG),
        "builder_code_commit": git("log", "-n", "1", "--format=%H", "--", *BUILDER_FILES),
        "builder_sha256": {f: S.file_sha256_lf(paths.PROJECT_ROOT / f) for f in BUILDER_FILES},
        "p5_plan_sha256": S.file_sha256_lf(paths.PROJECT_ROOT / "configs" / "experiments" / "v1.0"
                                           / "p5_personalization_plan.yaml"),
        "window_rule": load_protocol()["window"] | {"note": "D-032; RQ2 windows also cut at night boundaries (D-037)"},
    }
    manifest, checks = R.build_release(a.out, rows, paths.PROJECT_ROOT / "data" / "splits", plan=plan,
                                       events=user02_heater_events(), reference=reference_digests(),
                                       excluded=excluded_rows(), budgets=[0, 1, 3, 7, 14], identity=identity,
                                       raw_names=raw_names)
    write_json(paths.PROJECT_ROOT / "outputs" / "qa" / "p7" / "release_build.json", {
        "built_at": datetime.now().isoformat(timespec="seconds"), "head": git("rev-parse", "HEAD"),
        "dirty_tracked_files": bool(git("status", "--porcelain", "--untracked-files=no")),
        "checks": checks, "artifacts_sha256": manifest["artifacts_sha256"]})
    n_ok = sum(c["passed"] for c in checks)
    print(f"release {R.RELEASE_VERSION}: {manifest['counts']['windows']} windows "
          f"({manifest['counts']['in_loso']} LOSO, {manifest['counts']['in_rq2']} RQ2); checks {n_ok}/{len(checks)}")
    for k, v in manifest["artifacts_sha256"].items():
        print(f"  {k}: {v[:16]}  {(a.out / k).stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
