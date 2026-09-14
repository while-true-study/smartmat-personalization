"""Post-hoc descriptive P5 diagnostic (written after the P5 results were seen; not pre-declared in D-045).

Mean temperature and humidity of the labelled windows of each budget's adaptation nights, against the primary test
span and the base model's outer training pool (its target-scaler mean). No model, prediction or error is involved,
and nothing here feeds back into any run. Output: outputs/metrics/p5/p5_level_diagnostic.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.io_guard import write_csv  # noqa: E402
from src.evaluation import p5_personalization as P  # noqa: E402


def main() -> int:
    sess = P.P5Session(echo=False)
    sel = P.p3_selection()
    rows = []
    for subject, fold in sorted(P.subject_folds().items(), key=lambda kv: kv[1]):
        prim = sess.windows(subject, 0)
        m = prim.mask("test", primary_only=True)
        yt = prim.targets[m].mean(0)
        pool = sel["folds"][fold]["outer_target_scaler"]["mean"]
        for b in P.budgets():
            sw = sess.windows(subject, b)
            a = sw.mask("adaptation")
            ya = sw.targets[a].mean(0) if a.any() else [float("nan")] * 2
            for i, t in enumerate(("temperature", "humidity")):
                rows.append({"subject_id": subject, "fold": fold, "budget_nights": b, "target": t,
                             "adaptation_mean": float(ya[i]) if a.any() else "",
                             "primary_test_mean": float(yt[i]), "training_pool_mean": float(pool[i]),
                             "adaptation_minus_primary": float(ya[i] - yt[i]) if a.any() else "",
                             "training_pool_minus_primary": float(pool[i] - yt[i]),
                             "adaptation_windows": int(a.sum()), "primary_test_windows": int(m.sum())})
    out = P.metrics_dir() / "p5_level_diagnostic.csv"
    write_csv(out, rows, list(rows[0]))
    print(f"wrote {out.relative_to(P.paths.PROJECT_ROOT).as_posix()} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
