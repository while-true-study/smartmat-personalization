"""P8 post-hoc validation analyses (protocol v1.1 addendum; D-057). Logic: src/evaluation/p8_posthoc.py.

Design fixed in docs/P8_POSTHOC_VALIDATION_PLAN.md and configs/experiments/v1.1/posthoc_validation.yaml before any
of these analyses touched the test span. Frozen P3/P5 artifacts are read, never changed.
  python scripts/run_p8_posthoc.py control [--subject S] [--seed N]   initialization-control runs (b = 14, seeds 0-2)
  python scripts/run_p8_posthoc.py analyse                            calibration, residual variation, bootstrap, cases
  python scripts/run_p8_posthoc.py all                                control, then analyse
  --output-root DIR   runs and metrics under DIR instead of outputs/ (clean reproduction)
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation import p5_personalization as P5  # noqa: E402
from src.evaluation import p6_robustness as P6  # noqa: E402
from src.evaluation import p8_posthoc as P8  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=("control", "analyse", "all"))
    ap.add_argument("--subject", choices=sorted(P5.subject_folds()))
    ap.add_argument("--seed", type=int, choices=P5.seeds())
    ap.add_argument("--output-root", type=Path)
    a = ap.parse_args()
    P8.set_output_root(a.output_root)
    P8.load_addendum()
    print("design:", P8.design_hashes())
    sess = P5.P5Session()
    if a.step in ("control", "all"):
        for subject in sorted(P5.subject_folds(), key=P5.subject_folds().get):
            if a.subject and subject != a.subject:
                continue
            for s in P5.seeds():
                if a.seed is not None and s != a.seed:
                    continue
                print(f"control {subject} seed {s}: {P8.run_init_control(sess, subject, s)}", flush=True)
    if a.step in ("analyse", "all"):
        p6_mae = P6.read_csv(P6.tables_dir() / "p6_bootstrap_mae.csv")
        tables, prov = P8.analyse(sess, p6_mae)
        out = P8.write_tables(tables, prov)
        print("identities:", prov["identities"])
        for subject, c in prov["checks"].items():
            print(subject, {k: v for k, v in c.items() if k != "fit_windows"})
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
