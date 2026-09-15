"""Validate the manuscript source, generated assets and submission candidate (P8). Read-only.

Exit status 0 only if every check passes.
--rerender-figures  also re-draws every figure in a temporary directory, checks for overlapping labels and compares the
                    bytes with the committed PNGs (environment-dependent: fonts and matplotlib as in requirements.txt).
--final             also requires a final submission file: no placeholder, pending marker or unresolved bibliographic
                    field may remain. Fails while any submission blocker is open (docs/P8_FINAL_BLOCKERS.md).
--docx PATH         with --final: also check a Word file built by scripts/build_submission_docx.py (placeholders and
                    privacy scan of its text).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.paper import references as R  # noqa: E402
from src.paper import render as RD  # noqa: E402
from src.paper.docx_export import docx_text  # noqa: E402
from src.paper.manuscript_validation import check_privacy, readiness_blockers, validate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rerender-figures", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--docx", type=Path)
    args = ap.parse_args()
    results = validate(rerender_figures=args.rerender_figures)
    failed = 0
    for name, problems in results.items():
        print(f"[{'PASS' if not problems else 'FAIL'}] {name}" + (f": {len(problems)} problem(s)" if problems else ""))
        for p in problems:
            print("    -", p)
        failed += bool(problems)
    print(f"manuscript validation: {len(results) - failed}/{len(results)} checks -> {'PASS' if not failed else 'FAIL'}")
    if args.final:
        rendered = RD.RENDERED.read_text(encoding="utf-8") if RD.RENDERED.is_file() else None
        blockers = readiness_blockers(RD.read_source(), rendered)
        if args.docx:
            text = docx_text(args.docx).replace("\nReferences\n", "\n## References\n", 1)   # bibliographic dates allowed
            blockers += [f"docx: {b}" for b in readiness_blockers("", text) if not b.startswith("bibliography")]
            blockers += [f"docx: {p}" for p in check_privacy({args.docx.name: text})]
        print(f"final submission readiness: {len(blockers)} blocker(s) -> {'READY' if not blockers else 'NOT READY'}")
        for key, what in R.unconfirmed_items(R.load()).items():
            print(f"    note (not blocking): {key}: unconfirmed: {what}")
        for b in blockers:
            print("    -", b)
        failed += bool(blockers)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
