"""P12: heater-context confound diagnostic (protocol v1.6; D-067). Logic: src/evaluation/p12_heater_diagnostic.py.
Design: docs/P12_HEATER_DIAGNOSTIC_PLAN.md.

  python scripts/run_p12_heater_diagnostic.py [--output-root DIR]

Post hoc and descriptive. No model is fitted and no heater field enters any predictive model. It reads canonical_v1, the
frozen splits and the committed P10 / P11 predictions and changes none of them.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation import p5_personalization as P5  # noqa: E402
from src.evaluation import p12_heater_diagnostic as P12  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output-root", type=Path)
    a = ap.parse_args()
    P12.set_output_root(a.output_root)
    print("design:", P12.design_hashes(), flush=True)
    sess = P5.P5Session(echo=False)
    tables, val, prov = P12.run(sess, echo=lambda m: print(m, flush=True))
    out = P12.write_outputs(tables, val, prov)
    print("validation passed: %s; wrote %s" % (val["passed"], out))
    return 0 if val["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
