"""Reproduce the frozen P3–P6 results from the public release alone (D-050). Logic: src/evaluation/public_reproduction.py.

Needs only this repository (a git checkout) and a release directory; canonical_v1, raw data and the private split
files are never read. Nothing is searched, selected or tuned: the committed P3/P4 selections and the frozen P5 plan
are used as they are.
  core      1. release manifest and privacy/integrity validation
            2. P3 training-mean baseline and the 9 frozen RAW-TCN final models (3 folds x seeds 0/1/2)
            3. P5 personalization (45 runs) from the reproduced P3 models; P5 tables
            4. P6 analysis on the reproduced P5 tables and predictions; P6 tables
  extended  core + the 45 frozen P4 feature-family final models; P4 tables
Checks: every prediction file bitwise against reference_digests.json, the P3 model weights against the P5 plan, and
every paper table against its committed version (night ids may differ only by the per-subject D-049 day shift).
Runs that are verifiably complete are skipped, so an interrupted reproduction resumes. Exit code 0 only if every
check passes. Writes <out>/p7_reproduction_summary.json.
  python scripts/reproduce_public_release.py --data data/release/public_release_v1 --tier core|extended
                                             [--out outputs/p7/reproduction]
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse  # noqa: E402
import importlib.util  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402
from types import SimpleNamespace  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml  # noqa: E402

from src.data import paths  # noqa: E402
from src.data import public_release as R  # noqa: E402
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.evaluation import p3_loso as P3  # noqa: E402
from src.evaluation import p4_ablation as P4  # noqa: E402
from src.evaluation import p5_personalization as P5  # noqa: E402
from src.evaluation import public_reproduction as PR  # noqa: E402

P3_TABLES = ("p3_primary_summary", "p3_tcn_outer_by_seed", "p3_training_mean_by_fold", "p3_secondary_strata")
P5_TABLES = ("p5_adaptation_gain", "p5_budget_counts", "p5_by_seed", "p5_figure_data", "p5_later_span_mae",
             "p5_level_diagnostic", "p5_per_night", "p5_primary_bias", "p5_primary_mae", "p5_primary_rmse",
             "p5_user01_sensor_phase", "p5_user02_device_strata")
P6_TABLES = ("p6_bootstrap_bias", "p6_bootstrap_mae", "p6_bootstrap_rmse", "p6_bootstrap_seed_sensitivity",
             "p6_drift_sensitivity", "p6_figure_data", "p6_level_mismatch_consistency", "p6_level_mismatch_spans",
             "p6_level_mismatch_trajectory", "p6_user02_device_context", "p6_user02_device_context_bootstrap")
P4_TABLES = ("p4_bias_offset", "p4_incremental_effects", "p4_outer_by_seed", "p4_primary_summary",
             "p4_secondary_strata", "p4_seed_consistency", "p4_vs_raw", "p4_vs_training_mean")
NOT_REPRODUCED = {"p3_selected_configs.csv": "inner-search selection record (frozen input, D-050)",
                  "p4_selected_configs.csv": "inner-search selection record (frozen input, D-050)",
                  "p4_inner_score_range.csv": "inner-search scores (inner searches are not part of any tier, D-050)"}


def load_script(name: str, out_root: Path | None = None):
    """A script module from scripts/; export modules get their `paths` re-pointed at out_root."""
    spec = importlib.util.spec_from_file_location(f"_p7_{name}", paths.PROJECT_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if out_root is not None:
        mod.paths = SimpleNamespace(PROJECT_ROOT=out_root)
    return mod


class Log:
    def __init__(self):
        self.checks: list[dict] = []

    def add(self, stage: str, check: str, passed: bool, detail: str = "", informational: bool = False) -> None:
        self.checks.append({"stage": stage, "check": check, "passed": bool(passed), "detail": detail,
                            "informational": informational})
        if not passed:
            print(f"   [{'INFO' if informational else 'FAIL'}] {check}: {detail}", flush=True)

    def tables(self, stage: str, names: tuple[str, ...], out_root: Path, shifts: dict) -> None:
        for n in names:
            c = PR.compare_table(paths.PROJECT_ROOT / "paper" / "tables" / f"{n}.csv",
                                 out_root / "paper" / "tables" / f"{n}.csv", shifts)
            how = "byte-identical" if c["identical_bytes"] else (
                f"identical except {c['night_key_cells']} night-key cells (D-049 day shift)" if c["passed"]
                else "; ".join(c["problems"]))
            self.add(stage, f"table:{n}", c["passed"], f"{c['rows']} rows, {how}")

    def figures(self, stage: str, prefix: str, out_root: Path) -> None:
        for p in sorted((paths.PROJECT_ROOT / "paper" / "figures").glob(f"{prefix}_fig*.png")):
            q = out_root / "paper" / "figures" / p.name
            same = q.exists() and q.read_bytes() == p.read_bytes()
            self.add(stage, f"figure:{p.name}", same, "PNG byte-identical" if same else "PNG bytes differ "
                     "(rendering depends on the local fonts/matplotlib build; the figure data table is checked)",
                     informational=True)


def digest(log: Log, stage: str, name: str, ref: dict, pred: Path) -> None:
    c = PR.compare_digest(name, ref, R.prediction_digest(pred))
    log.add(stage, c["check"], c["passed"], c["detail"])


def write_metric_tables(out: Path, tables: dict[str, list[dict]], prefix: str = "") -> None:
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r))
        write_csv(out / f"{prefix}{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)


def stage_p3(log: Log, sess, ref: dict, plan: dict, out_root: Path, shifts: dict) -> None:
    folds = sorted(P5.subject_folds().values())
    for f in folds:
        print(f"== P3 training-mean fold {f}: {P3.run_training_mean(sess, f)}", flush=True)
        digest(log, "P3", f"p3_training_mean/fold{f}", ref["p3_training_mean"][f"fold{f}"],
               P3.training_mean_dir(f) / "predictions.parquet")
    by_fold = {v: k for k, v in P5.subject_folds().items()}
    for f in folds:
        for s in P5.seeds():
            t0 = time.time()
            print(f"== P3 final fold {f} seed {s}", flush=True)
            print(f"   {P3.run_final(sess, f, s)} ({time.time() - t0:.0f} s)", flush=True)
            digest(log, "P3", f"p3_final/fold{f}_seed{s}", ref["p3_final"][f"fold{f}_seed{s}"],
                   P3.final_dir(f, s) / "predictions.parquet")
            _, prov = P5.load_base_state(f, s)
            want = plan["subjects"][by_fold[f]]["base_checkpoints"][s]["weights_sha256"]
            log.add("P3", f"weights:p3_final/fold{f}_seed{s}", prov["weights_sha256"] == want,
                    "model weights identical to the frozen P5 plan base checkpoint"
                    if prov["weights_sha256"] == want else f"{prov['weights_sha256']} vs {want}")
    write_metric_tables(P3.metrics_dir(), P3.aggregate(include_selection=False))
    ep3 = load_script("export_p3_tables", out_root)
    ep3.export_csvs({n: ep3.read(n) for n in ("tcn_outer_summary", "tcn_outer_by_seed", "training_mean_by_fold",
                                              "secondary_strata")})
    log.tables("P3", P3_TABLES, out_root, shifts)


def stage_p5(log: Log, sess, ref: dict, out_root: Path, shifts: dict) -> None:
    vb = P5.verify_base(sess)
    log.add("P5", "base_checkpoints_reload_bitwise", vb["passed"],
            f"{sum(r['predictions_bitwise_identical'] for r in vb['runs'])}/{len(vb['runs'])} reproduced P3 models "
            "reload and predict bitwise")
    print("plan:", P5.plan_commit(), flush=True)
    for subject in sorted(P5.subject_folds(), key=P5.subject_folds().get):
        for b in P5.budgets():
            for s in P5.seeds():
                t0 = time.time()
                print(f"== P5 {subject} b={b} seed {s}", flush=True)
                print(f"   {P5.run_personalization(sess, subject, b, s)} ({time.time() - t0:.0f} s)", flush=True)
                digest(log, "P5", f"p5/{subject}/b{b:02d}_seed{s}", ref["p5"][f"{subject}/b{b:02d}_seed{s}"],
                       P5.run_dir(subject, b, s) / "predictions.parquet")
    P5.write_tables(P5.aggregate())
    load_script("diagnose_p5_levels").main()
    ep5 = load_script("export_p5_tables", out_root)
    t = {n: ep5.read(n) for n in ("primary_summary", "later_summary", "adaptation_gain", "by_seed", "per_night",
                                  "strata", "budget_counts", "pooled_primary", "level_diagnostic")}
    ep5.export_csvs(t)
    ep5.draw_figures(ep5.figure_data(t))
    log.tables("P5", P5_TABLES, out_root, shifts)
    log.figures("P5", "p5", out_root)


def stage_p6(log: Log, out_root: Path, shifts: dict) -> None:
    load_script("run_p6_robustness").main()
    ep6 = load_script("export_p6_tables", out_root)
    t = {n: ep6.read(n) for n in ("bootstrap", "bootstrap_seed_sensitivity", "drift_sensitivity", "level_trajectory",
                                  "level_spans", "level_consistency", "user02_device_context",
                                  "user02_device_context_bootstrap")}
    ep6.export_csvs(t)
    ep6.draw_figures(ep6.figure_data(t))
    log.tables("P6", P6_TABLES, out_root, shifts)
    log.figures("P6", "p6", out_root)


def stage_p4(log: Log, sess, ref: dict, out_root: Path, shifts: dict) -> None:
    for fam in P4.P4_FAMILIES:
        for f in sorted(P5.subject_folds().values()):
            for s in P5.seeds():
                t0 = time.time()
                print(f"== P4 {fam} final fold {f} seed {s}", flush=True)
                print(f"   {P4.run_final(sess, fam, f, s)} ({time.time() - t0:.0f} s)", flush=True)
                key = f"{P4.family_slug(fam)}/fold{f}_seed{s}"
                digest(log, "P4", f"p4_final/{key}", ref["p4_final"][key],
                       P4.final_dir(fam, f, s) / "predictions.parquet")
    P4.write_tables(P4.aggregate(include_selection=False, p3_root=out_root))
    ep4 = load_script("export_p4_tables", out_root)
    ep4.export_csvs({n: ep4.read(n) for n in ("family_summary", "outer_by_seed", "vs_raw", "vs_training_mean",
                                              "incremental_effects", "seed_consistency", "bias_offset",
                                              "secondary_strata")})
    log.tables("P4", P4_TABLES, out_root, shifts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, default=paths.PROJECT_ROOT / "data" / "release" / R.RELEASE_VERSION)
    ap.add_argument("--tier", choices=("core", "extended"), required=True)
    ap.add_argument("--out", type=Path, default=paths.PROJECT_ROOT / "outputs" / "p7" / "reproduction")
    a = ap.parse_args()
    out_root = a.out.resolve()
    if not out_root.is_relative_to((paths.PROJECT_ROOT / "outputs").resolve()):
        raise SystemExit("--out must lie under the repository's outputs/ directory (git-ignored)")
    from src.training.trainer import environment
    log, timing, t_all = Log(), {}, time.time()
    started = datetime.now().isoformat(timespec="seconds")

    t0 = time.time()
    for c in R.validate_release(a.data):
        log.add("release", c["check"], c["passed"], c["detail"])
    release = R.PublicRelease(a.data, verify=True)
    log.add("release", "manifest_hashes_and_windows_load", True, f"{release.manifest['counts']['windows']} windows")
    timing["release"] = round(time.time() - t0, 1)
    if not all(c["passed"] for c in log.checks):
        print("release validation failed: nothing is run")
        return 1
    ref = PR.read_json(release.root / "reference_digests.json")
    plan = yaml.safe_load((release.root / "p5_plan_public.yaml").read_text(encoding="utf-8"))
    shifts: dict[str, int] = {}
    stages = [("P3", lambda s: stage_p3(log, s, ref, plan, out_root, shifts)),
              ("P5", lambda s: stage_p5(log, s, ref, out_root, shifts)),
              ("P6", lambda s: stage_p6(log, out_root, shifts))]
    if a.tier == "extended":
        stages.append(("P4", lambda s: stage_p4(log, s, ref, out_root, shifts)))
    with PR.public_mode(release, out_root):
        sess = PR.PublicSession(echo=False)
        for name, fn in stages:
            t0 = time.time()
            fn(sess)
            timing[name] = round(time.time() - t0, 1)
            gating = [c for c in log.checks if c["stage"] == name and not c["informational"]]
            print(f"{name}: {sum(c['passed'] for c in gating)}/{len(gating)} checks pass ({timing[name]:.0f} s)",
                  flush=True)
        env = environment()
    gating = [c for c in log.checks if not c["informational"]]
    ok = all(c["passed"] for c in gating)
    summary = {
        "decision": "D-050", "tier": a.tier, "started_at": started,
        "finished_at": datetime.now().isoformat(timespec="seconds"), "seconds": timing,
        "total_seconds": round(time.time() - t_all, 1), "release": PR.release_identity(release),
        "release_version": release.manifest["release_version"], **P3.git_state(), "environment": env,
        "night_key_day_shift_subjects": sorted(shifts), "not_reproduced": NOT_REPRODUCED,
        "passed": ok, "n_checks": len(gating), "n_failed": sum(not c["passed"] for c in gating),
        "informational": [c for c in log.checks if c["informational"]], "checks": gating}
    write_json(out_root / "p7_reproduction_summary.json", summary)
    print(f"public reproduction ({a.tier}): {len(gating) - summary['n_failed']}/{len(gating)} checks -> "
          f"{'PASS' if ok else 'FAIL'}; figures byte-identical "
          f"{sum(c['passed'] for c in summary['informational'])}/{len(summary['informational'])}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
