"""P5 chronological personalization runner (protocol v1.0; RAW; base = P3 final models). Logic:
src/evaluation/p5_personalization.py.

Commands (each skips runs that are verifiably complete and re-runs failed/incomplete ones):
  verify-base                        each P3 base checkpoint reproduces its stored P3 predictions bitwise
  plan                               write configs/experiments/v1.0/p5_personalization_plan.yaml (frozen inputs only)
  check [--subject S] [--budget B]   P2 gate + P5 checks for every subject x budget (no training, no evaluation)
  run [--subject S] [--budget B] [--seed K]
                                     b = 0: base-model evaluation; b > 0: fine-tuning, then the single evaluation;
                                     refuses unless the plan is committed
  aggregate                          tables in outputs/metrics/p5/ from complete runs
  status                             run completion overview
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.io_guard import write_json  # noqa: E402
from src.evaluation import p5_personalization as P  # noqa: E402
from src.evaluation.leakage import RunContext  # noqa: E402
from src.features.pressure_features import RAW_FEATURES  # noqa: E402


def subjects_arg(a) -> list[str]:
    order = sorted(P.subject_folds(), key=P.subject_folds().get)
    return order if a.subject is None else [a.subject]


def budgets_arg(a) -> list[int]:
    return P.budgets() if a.budget is None else [a.budget]


def cmd_verify_base(_a) -> int:
    out = P.verify_base(P.P5Session())
    for r in out["runs"]:
        print(f"fold {r['fold']} seed {r['seed']}: weights {r['weights_sha256'][:12]} predictions "
              f"{'identical' if r['predictions_bitwise_identical'] else 'DIFFER'}")
    print("base verification:", "PASS" if out["passed"] else "FAIL")
    return 0 if out["passed"] else 1


def cmd_plan(_a) -> int:
    doc = P.export_plan(P.P5Session())
    for s, rec in doc["subjects"].items():
        print(f"{s}: fold {rec['fold']}, adaptation lr {rec['adaptation']['lr']:g}, primary nights "
              f"{rec['primary_test']['n_nights']} ({rec['primary_test']['windows']} windows); adaptation windows "
              + ", ".join(f"b{b}={v['adaptation_windows']}" for b, v in rec["budgets"].items()))
    print(f"wrote {P.plan_yaml().name}")
    return 0


def cmd_check(a) -> int:
    sess = P.P5Session()
    sel = P.p3_selection()
    plan = P.build_plan(sess)
    ok = True
    for subject in subjects_arg(a):
        fold = P.subject_folds()[subject]
        scaler = P.base_scaler(fold, sel)
        cfg, epochs = P.adaptation_config(sel["folds"][fold]["config"])
        for b in budgets_arg(a):
            sw = sess.windows(subject, b)
            nights = P.budget_nights(sess.pers(), subject, b)
            ctx = RunContext("personalization", subject=subject, budget=b, input_features=list(RAW_FEATURES),
                             fit_records=[dict(scaler.fit_provenance)], selection_subjects=[],
                             window_groups=sw.window_groups(sw.mask("adaptation") | sw.mask("test")))
            d = P.run_root() / "checks" / f"{subject}_b{b:02d}"
            rep, _ = sess.gate(d, ctx)
            checks = P.p5_checks(subject, b, sw, nights, sess.pers(), sel, scaler, cfg, epochs,
                                 plan["subjects"][subject])
            write_json(d / "p5_checks.json", {"checks": checks})
            n_ok = sum(c["passed"] for c in checks)
            ok &= n_ok == len(checks)
            print(f"{subject} b={b}: gate {sum(c.passed for c in rep.checks)}/{len(rep.checks)}, P5 checks "
                  f"{n_ok}/{len(checks)}; adaptation windows {int(sw.mask('adaptation').sum())}, primary test "
                  f"windows {int(sw.mask('test', True).sum())}", flush=True)
    return 0 if ok else 1


def cmd_run(a) -> int:
    sess = P.P5Session()
    P.frozen_plan()                                        # refuse before touching anything if not frozen
    print("plan commit:", P.plan_commit())
    seeds = P.seeds() if a.seed is None else [a.seed]
    for subject in subjects_arg(a):
        for b in budgets_arg(a):
            for s in seeds:
                t0 = time.time()
                print(f"== {subject} b={b} seed {s}", flush=True)
                print(f"   {P.run_personalization(sess, subject, b, s)} ({time.time() - t0:.0f} s)", flush=True)
    return 0


def cmd_aggregate(_a) -> int:
    out = P.write_tables(P.aggregate())
    print(f"tables -> {out.relative_to(P.paths.PROJECT_ROOT).as_posix()}/")
    return 0


def cmd_status(_a) -> int:
    by: dict[str, int] = {}
    for r in P.run_index():
        by[r["status"]] = by.get(r["status"], 0) + 1
    print("runs:", by, "of", len(P.subject_folds()) * len(P.budgets()) * len(P.seeds()))
    print("plan:", "present" if P.plan_yaml().exists() else "absent")
    print("test accesses:", P.test_access_counts())
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("verify-base", "plan", "check", "run", "aggregate", "status"):
        p = sub.add_parser(name)
        if name in ("check", "run"):
            p.add_argument("--subject", choices=sorted(P.subject_folds()))
            p.add_argument("--budget", type=int, choices=P.budgets())
        if name == "run":
            p.add_argument("--seed", type=int, choices=P.seeds())
    a = ap.parse_args()
    return {"verify-base": cmd_verify_base, "plan": cmd_plan, "check": cmd_check, "run": cmd_run,
            "aggregate": cmd_aggregate, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
