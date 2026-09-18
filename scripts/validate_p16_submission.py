"""Validate the final editorial candidate (read only). Exit status 0 only if every check passes.

All checks of scripts/validate_p15_submission.py applied to manuscript_p16_final.md and paper/submission_p16/, plus:
title and keywords, revision-history wording, scientific equivalence with P15, and unchanged P15 source.
Logic: src/paper/p16_submission.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.p16_submission import validate  # noqa: E402


def main() -> int:
    results = validate()
    failed = 0
    for name, problems in results.items():
        print(f"[{'PASS' if not problems else 'FAIL'}] {name}" + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems[:20]:
            print("    -", p)
        failed += bool(problems)
    print(f"P16 submission validation: {len(results) - failed}/{len(results)} checks -> {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
