"""Build the Word (DOCX) version of the rendered manuscript in the Applied Sciences Word template (P8).

The template is not part of the repository (the journal restricts it to submission for peer review). Pass the local
copy of the current Applied Sciences Word template (.docx):

    python scripts/build_submission_docx.py --template <path to applsci-template.docx>

The output goes to outputs/p8/submission/ (git-ignored). While any submission blocker is open, the document starts with
a review-draft notice. Run scripts/build_submission_candidate.py first.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.paper import render as RD  # noqa: E402
from src.paper.docx_export import OUTPUT, build_docx  # noqa: E402
from src.paper.manuscript_validation import readiness_blockers  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", required=True, type=Path, help="Applied Sciences Word template (.docx)")
    ap.add_argument("--out", type=Path, default=OUTPUT)
    args = ap.parse_args()
    rendered = RD.RENDERED.read_text(encoding="utf-8")
    blockers = readiness_blockers(RD.read_source(), rendered)
    note = (f"REVIEW DRAFT - NOT FOR SUBMISSION: {len(blockers)} open placeholder(s) or blocker(s) remain "
            "(docs/P8_FINAL_BLOCKERS.md).") if blockers else None
    out = build_docx(args.template, args.out, rendered, draft_note=note)
    shown = out.relative_to(paths.PROJECT_ROOT) if out.is_relative_to(paths.PROJECT_ROOT) else out
    print(f"wrote {shown.as_posix()} ({'review draft' if note else 'final'}; {len(blockers)} blocker(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
