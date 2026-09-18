"""Validate the final Applied Sciences submission artifacts (read only). Exit status 0 only if every check passes.

Checks the P16 source freeze, the final title and abstract, the main and supplementary DOCX structure, scientific
equivalence with P16, the lossless supplementary workbook, the figure files, privacy and document metadata, the cover
letter, the metadata checklist, the QA reports and the manifest hashes. Runs no scientific analysis.
Logic: src/paper/final_submission.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.final_submission import validate  # noqa: E402


def main() -> int:
    results = validate()
    failed = 0
    for name, problems in results.items():
        print(f"[{'PASS' if not problems else 'FAIL'}] {name}" + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems[:20]:
            print("    -", p)
        failed += bool(problems)
    print(f"Final submission validation: {len(results) - failed}/{len(results)} checks -> "
          f"{'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
