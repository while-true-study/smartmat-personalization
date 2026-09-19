"""Validate the metadata-ready submission system (read only). Exit status 0 only if every check passes.

M01-M18 and L01-L04 defined, the 28 external requests mapped, no unknown or duplicate token, no value without a
confirmed status and source, the final build blocked while metadata is open, and byte-exact equivalence of the
metadata-ready manuscript with P16 outside the metadata placeholders. Logic: src/paper/submission_metadata.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper.submission_metadata import validate  # noqa: E402


def main() -> int:
    results = validate()
    failed = 0
    for name, problems in results.items():
        print(f"[{'PASS' if not problems else 'FAIL'}] {name}" + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems[:20]:
            print("    -", p)
        failed += bool(problems)
    print(f"Submission metadata validation: {len(results) - failed}/{len(results)} checks -> "
          f"{'PASS' if not failed else 'FAIL'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
