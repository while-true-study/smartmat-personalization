"""P3 strict LOSO baseline runner (protocol v1.0, frozen at p2-protocol-freeze). Logic: src/evaluation/p3_loso.py.

Commands (each skips runs that are verifiably complete and re-runs failed/incomplete ones):
  check                         P2 gate inputs, split and protocol integrity (no training)
  training-mean [--fold F]      training-mean baseline (outer test evaluated once per fold)
  inner [--fold F] [--inner A|B] [--config K]
                                RAW-TCN inner search (seed 0, early stopping on inner validation)
  select [--fold F]             freeze the fold selection from its 32 complete inner runs
  export-selection              write configs/experiments/v1.0/p3_selected_configs.yaml (all folds frozen)
  final [--fold F] [--seed S]   final outer models (seeds 0/1/2, fixed epochs) + the single outer-test evaluation
  aggregate                     tables in outputs/metrics/p3/ from complete runs
  status                        run completion overview
  smoke                         engineering smoke test on synthetic data (no study data, no results)
  pipeline                      training-mean -> inner+select per fold -> export-selection -> final -> aggregate
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.evaluation import p3_loso as P  # noqa: E402
from src.evaluation.protocol import load_protocol  # noqa: E402


def folds_arg(a) -> list[int]:
    all_folds = sorted(int(k) for k in load_protocol()["loso"]["outer_folds"])
    return all_folds if a.fold is None else [a.fold]


def cmd_check(_a) -> int:
    from src.evaluation.canonical_input import verify_canonical
    from src.evaluation.leakage import RunContext
    from src.features.pressure_features import RAW_FEATURES
    sess = P.P3Session()
    d = P.run_root() / "checks"
    for f in folds_arg(_a):
        fd = sess.fold(f)
        ctx = RunContext("loso", fold=f, input_features=list(RAW_FEATURES),
                         fit_records=[{"transform": "target_zscore", "partition": "train",
                                       "subjects": fd.train_subjects}],
                         selection_subjects=fd.train_subjects, window_groups=fd.window_groups(fd.labelled))
        rep, _ = sess.gate(d / f"fold{f}", ctx)
        print(f"fold {f}: held out {fd.held_out}; windows train {int((fd.partition == 'train').sum())} / test "
              f"{int((fd.partition == 'test').sum())}; gate {len(rep.checks)}/{len(rep.checks)} pass")
    print("canonical:", verify_canonical()["content_sha256"]["primary"][:16])
    return 0


def cmd_training_mean(a) -> int:
    sess = P.P3Session()
    for f in folds_arg(a):
        print(f"training-mean fold {f}: {P.run_training_mean(sess, f)}")
    return 0


def cmd_inner(a) -> int:
    sess = P.P3Session()
    inners = P.INNER_SPLITS if a.inner is None else (a.inner,)
    ks = range(16) if a.config is None else [a.config]
    for f in folds_arg(a):
        for inner in inners:
            for k in ks:
                t0 = time.time()
                print(f"== inner fold {f} {inner} cfg {k:02d}", flush=True)
                print(f"   {P.run_inner(sess, f, inner, k)} ({time.time() - t0:.0f} s)", flush=True)
    return 0


def cmd_select(a) -> int:
    sess = P.P3Session()
    for f in folds_arg(a):
        s = P.select_fold(sess, f)
        print(f"fold {f}: selected cfg {s['selected_index']:02d} {s['selected_config']} "
              f"score {s['selection_score']:.6f} final_epochs {s['final_epochs']}")
    return 0


def cmd_export(_a) -> int:
    doc = P.export_selection()
    print(f"wrote {P.selected_yaml().name}: folds {sorted(doc['folds'])}")
    return 0


def cmd_final(a) -> int:
    sess = P.P3Session()
    seeds = [int(s) for s in load_protocol()["models"]["seeds"]] if a.seed is None else [a.seed]
    P.frozen_selection()                                   # refuse before touching anything if not frozen
    for f in folds_arg(a):
        for s in seeds:
            t0 = time.time()
            print(f"== final fold {f} seed {s}", flush=True)
            print(f"   {P.run_final(sess, f, s)} ({time.time() - t0:.0f} s)", flush=True)
    return 0


def cmd_aggregate(_a) -> int:
    tables = P.aggregate()
    out = P.metrics_dir()
    for name, rows in tables.items():
        cols = list(dict.fromkeys(k for r in rows for k in r))
        write_csv(out / f"{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    idx = P.run_index()
    write_csv(out / "run_index.csv", idx, list(idx[0]))
    write_json(out / "outer_test_access_counts.json", P.outer_access_counts())
    print(f"{len(tables)} tables -> outputs/metrics/p3/")
    return 0


def cmd_status(_a) -> int:
    rows = P.run_index()
    for kind in ("training_mean", "inner", "final"):
        rs = [r for r in rows if r["kind"] == kind]
        by = {}
        for r in rs:
            by[r["status"]] = by.get(r["status"], 0) + 1
        print(f"{kind}: {by}")
    for f in sorted(int(k) for k in load_protocol()["loso"]["outer_folds"]):
        print(f"selection fold {f}: {'frozen' if P.selection_path(f).exists() else 'not frozen'}")
    print("committed selection:", "present" if P.selected_yaml().exists() else "absent")
    print("outer-test accesses:", P.outer_access_counts())
    return 0


def cmd_smoke(_a) -> int:
    from src.training.smoke import smoke_test
    print(smoke_test())
    return 0


def cmd_pipeline(a) -> int:
    cmd_training_mean(a)
    for f in folds_arg(a):
        a2 = argparse.Namespace(fold=f, inner=None, config=None)
        cmd_inner(a2)
        cmd_select(a2)
    cmd_export(a)
    cmd_final(argparse.Namespace(fold=a.fold, seed=None))
    cmd_aggregate(a)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "training-mean", "inner", "select", "export-selection", "final", "aggregate", "status",
                 "smoke", "pipeline"):
        p = sub.add_parser(name)
        p.add_argument("--fold", type=int, choices=[1, 2, 3])
        if name == "inner":
            p.add_argument("--inner", choices=list(P.INNER_SPLITS))
            p.add_argument("--config", type=int, choices=range(16))
        if name == "final":
            p.add_argument("--seed", type=int)
    a = ap.parse_args()
    fn = {"check": cmd_check, "training-mean": cmd_training_mean, "inner": cmd_inner, "select": cmd_select,
          "export-selection": cmd_export, "final": cmd_final, "aggregate": cmd_aggregate, "status": cmd_status,
          "smoke": cmd_smoke, "pipeline": cmd_pipeline}[a.cmd]
    return fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
