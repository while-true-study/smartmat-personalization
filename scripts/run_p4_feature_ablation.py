"""P4 feature-family runner (protocol v1.0; RAW reference frozen at p3-loso-baseline). Logic: src/evaluation/p4_ablation.py.

Commands (each skips runs that are verifiably complete and re-runs failed/incomplete ones):
  check [--family F] [--fold K]     leakage gate for every family x fold input schema (no training)
  inner [--family F] [--fold K] [--inner A|B] [--config C]
                                    inner search (seed 0, early stopping on inner validation)
  select [--family F] [--fold K]    freeze family x fold selections from their 32 complete inner runs
  export-selection                  write configs/experiments/v1.0/p4_selected_configs.yaml (all 15 frozen)
  final [--family F] [--fold K] [--seed S]
                                    final outer models (seeds 0/1/2, fixed epochs) + the single outer-test evaluation;
                                    refuses unless the selection file is committed
  aggregate                         tables in outputs/metrics/p4/ from complete runs and the frozen P3 reference
  status                            run completion overview
Families: MOVEMENT, CONTACT, RAW+MOVEMENT, RAW+CONTACT, RAW+MOVEMENT+CONTACT (RAW is not re-run).
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation import p4_ablation as P  # noqa: E402
from src.evaluation.p3_loso import INNER_SPLITS, P3Session  # noqa: E402
from src.evaluation.protocol import load_protocol  # noqa: E402


def folds_arg(a) -> list[int]:
    all_folds = sorted(int(k) for k in load_protocol()["loso"]["outer_folds"])
    return all_folds if a.fold is None else [a.fold]


def families_arg(a) -> list[str]:
    return list(P.P4_FAMILIES) if a.family is None else [a.family]


def cmd_check(a) -> int:
    from src.evaluation.leakage import RunContext
    sess = P3Session()
    for fam in families_arg(a):
        feats = P.assert_p4_family(fam)
        for f in folds_arg(a):
            fd = sess.fold(f)
            ctx = RunContext("loso", fold=f, input_features=list(feats),
                             fit_records=[{"transform": "target_zscore", "partition": "train",
                                           "subjects": fd.train_subjects}],
                             selection_subjects=fd.train_subjects, window_groups=fd.window_groups(fd.labelled))
            rep, _ = sess.gate(P.run_root() / "checks" / P.family_slug(fam) / f"fold{f}", ctx)
            print(f"{fam} ({len(feats)} inputs) fold {f}: held out {fd.held_out}; gate "
                  f"{sum(c.passed for c in rep.checks)}/{len(rep.checks)} pass", flush=True)
    return 0


def cmd_inner(a) -> int:
    sess = P3Session()
    inners = INNER_SPLITS if a.inner is None else (a.inner,)
    ks = range(16) if a.config is None else [a.config]
    for fam in families_arg(a):
        for f in folds_arg(a):
            for inner in inners:
                for k in ks:
                    t0 = time.time()
                    print(f"== {fam} inner fold {f} {inner} cfg {k:02d}", flush=True)
                    print(f"   {P.run_inner(sess, fam, f, inner, k)} ({time.time() - t0:.0f} s)", flush=True)
    return 0


def cmd_select(a) -> int:
    sess = P3Session()
    for fam in families_arg(a):
        for f in folds_arg(a):
            s = P.select_fold(sess, fam, f)
            print(f"{fam} fold {f}: selected cfg {s['selected_index']:02d} {s['selected_config']} "
                  f"score {s['selection_score']:.6f} final_epochs {s['final_epochs']}", flush=True)
    return 0


def cmd_export(_a) -> int:
    doc = P.export_selection()
    print(f"wrote {P.selected_yaml().name}: families {list(doc['families'])}")
    return 0


def cmd_final(a) -> int:
    sess = P3Session()
    seeds = [int(s) for s in load_protocol()["models"]["seeds"]] if a.seed is None else [a.seed]
    P.frozen_selection()                                   # refuse before touching anything if not frozen
    print("selection commit:", P.selection_commit())
    for fam in families_arg(a):
        for f in folds_arg(a):
            for s in seeds:
                t0 = time.time()
                print(f"== {fam} final fold {f} seed {s}", flush=True)
                print(f"   {P.run_final(sess, fam, f, s)} ({time.time() - t0:.0f} s)", flush=True)
    return 0


def cmd_aggregate(_a) -> int:
    tables = P.aggregate()
    out = P.write_tables(tables)
    print(f"{len(tables)} tables -> {out.relative_to(P.paths.PROJECT_ROOT).as_posix()}/")
    return 0


def cmd_status(_a) -> int:
    rows = P.run_index()
    for fam in P.P4_FAMILIES:
        for kind in ("inner", "final"):
            by: dict[str, int] = {}
            for r in rows:
                if r["family"] == fam and r["kind"] == kind:
                    by[r["status"]] = by.get(r["status"], 0) + 1
            print(f"{fam:22s} {kind}: {by}")
        frozen = [f for f in folds_arg(argparse.Namespace(fold=None)) if P.selection_path(fam, f).exists()]
        print(f"{fam:22s} selection frozen for folds {frozen}")
    print("committed selection file:", "present" if P.selected_yaml().exists() else "absent")
    print("outer-test accesses:", P.outer_access_counts())
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "inner", "select", "export-selection", "final", "aggregate", "status"):
        p = sub.add_parser(name)
        p.add_argument("--fold", type=int, choices=[1, 2, 3])
        p.add_argument("--family", choices=list(P.P4_FAMILIES))
        if name == "inner":
            p.add_argument("--inner", choices=list(INNER_SPLITS))
            p.add_argument("--config", type=int, choices=range(16))
        if name == "final":
            p.add_argument("--seed", type=int)
    a = ap.parse_args()
    fn = {"check": cmd_check, "inner": cmd_inner, "select": cmd_select, "export-selection": cmd_export,
          "final": cmd_final, "aggregate": cmd_aggregate, "status": cmd_status}[a.cmd]
    return fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
