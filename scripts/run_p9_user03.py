"""P9: source-only RAW-TCN models and User03 external evaluation (D-061; protocol v1.3). Logic:
src/evaluation/p9_external.py. The model rule was fixed in the plan before any User03 label was evaluated.
  python scripts/run_p9_user03.py train      9 runs: 3 frozen P3 configurations x seeds 0-2 on User01+02+07
  python scripts/run_p9_user03.py analyse    metrics, per-night results and the plan §9 interpretation
"""
from __future__ import annotations

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import p9_user03 as U  # noqa: E402
from src.evaluation import p3_loso as P3  # noqa: E402
from src.evaluation import p9_external as E  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("step", choices=("train", "analyse", "all"))
    a = ap.parse_args()
    U.load_config()
    ew = E.user03_windows()
    sess = P3.P3Session()
    src = E.source_windows(sess)
    print(f"source windows {src['targets'].shape[0]}; external labelled windows {int(ew.labelled.sum())}")
    if a.step in ("train", "all"):
        for c in E.CONFIGS:
            for s in (0, 1, 2):
                print(f"config fold {c} seed {s}: {E.run_model(sess, src, ew, c, s)}", flush=True)
    if a.step in ("analyse", "all"):
        tables, extra = E.analyse(ew, src["targets"])
        extra["runs"] = {f"config_fold{c}/seed{s}": P3.sha256_file(E.run_dir(c, s) / "external_predictions.npy")
                         for c in E.CONFIGS for s in (0, 1, 2)}
        out = E.write_tables(tables, extra)
        for r in tables["summary"]:
            print(f"{r['model']:<34} cfg {r['config_fold']!s:<4} {r['target']:<11} MAE {r['mae']:.3f} "
                  f"RMSE {r['rmse']:.3f} bias {r['bias']:+.3f} R {r['R']:.3f} Q {r['Q']:.3f} "
                  f"r {r['r_pooled']:+.3f} r_within {r['r_within']:+.3f}")
        for r in tables["interpretation"]:
            print(r)
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
