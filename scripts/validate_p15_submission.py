"""Validate the submission-ready candidate (read only). Exit status 0 only if every check passes.

Checks paper/manuscript/manuscript_p15_final.md, its rendering and paper/submission_p15/ (src/paper/p15_submission.py):
tokens, precision, internal notes, placeholder whitelist, abstract length, numbering, Figure S5 withdrawal, claims and
wording, reproducibility wording, terminology and units, privacy, citations, generated-table freshness, result files,
frozen sources and package contents. scripts/validate_manuscript_results.py still checks manuscript.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.p15_submission import validate  # noqa: E402


def main() -> int:
    results = validate()
    failed = 0
    for name, problems in results.items():
        print(f"[{'PASS' if not problems else 'FAIL'}] {name}" + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems[:20]:
            print("    -", p)
        failed += bool(problems)
    print(f"P15 submission validation: {len(results) - failed}/{len(results)} checks -> {'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
