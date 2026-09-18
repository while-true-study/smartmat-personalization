"""Validate the P13 manuscript revision (read only). Exit status 0 only if every check passes.

Checks paper/manuscript/manuscript_p13_revision.md and its rendering with the P8 rules (tokens, hand-typed numbers,
claims, privacy, placeholders, citations, formatting) and the P13 rules (abstract length, table, figure and
supplementary numbering, figure paths, required and forbidden wording, export freshness, rendered copy, frozen
sources). Logic: src/paper/p13_validation.py. scripts/validate_manuscript_results.py still checks manuscript.md and
the P8 submission candidate.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.p13_validation import validate  # noqa: E402


def main() -> int:
    results = validate()
    failed = 0
    for name, problems in results.items():
        print(f"[{'PASS' if not problems else 'FAIL'}] {name}" + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems:
            print("    -", p)
        failed += bool(problems)
    print(f"P13 manuscript validation: {len(results) - failed}/{len(results)} checks -> {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
