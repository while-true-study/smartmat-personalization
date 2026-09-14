"""Validate the manuscript source, generated assets and submission candidate (P8). Read-only.

Exit status 0 only if every check passes. --rerender-figures also re-draws every figure in a temporary directory,
checks for overlapping labels and compares the bytes with the committed PNGs (environment-dependent: fonts and the
matplotlib version must match requirements.txt).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.manuscript_validation import validate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rerender-figures", action="store_true")
    args = ap.parse_args()
    results = validate(rerender_figures=args.rerender_figures)
    failed = 0
    for name, problems in results.items():
        print(f"[{'PASS' if not problems else 'FAIL'}] {name}" + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems:
            print("    -", p)
        failed += bool(problems)
    print(f"manuscript validation: {len(results) - failed}/{len(results)} checks -> {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
