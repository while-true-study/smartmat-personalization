"""Validate the P14 submission candidate (read only). Exit status 0 only if every check passes.

Logic: src/paper/p14_validation.py (P8 and P13 checks applied to manuscript_p14_revision.md, plus the P14 checks of
D-069 and D-070). scripts/validate_manuscript_results.py still checks manuscript.md and the P8 submission candidate.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.p14_validation import validate  # noqa: E402


def main() -> int:
    results = validate()
    failed = 0
    for name, problems in results.items():
        print(f"[{'PASS' if not problems else 'FAIL'}] {name}" + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems:
            print("    -", p)
        failed += bool(problems)
    print(f"P14 manuscript validation: {len(results) - failed}/{len(results)} checks -> {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
