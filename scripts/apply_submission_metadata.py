"""Fill the external submission metadata into the metadata-ready manuscript and cover letter (no scientific change).

  python scripts/apply_submission_metadata.py --check          # list what is still unresolved
  python scripts/apply_submission_metadata.py --status         # regenerate metadata/METADATA_STATUS.md
  python scripts/apply_submission_metadata.py --build-preview  # write previews to work/ (open tokens kept visible)
  python scripts/apply_submission_metadata.py --final          # write metadata_applied/; FAILS while anything is open
  python scripts/apply_submission_metadata.py --generate       # regenerate manuscript_metadata_ready.md from P16

Values: paper/submission_final/metadata/METADATA_VALUES_TEMPLATE.yaml and CREDIT_INPUT_TEMPLATE.yaml.
Logic: src/paper/submission_metadata.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.paper import submission_metadata as S  # noqa: E402


def rel(p: Path) -> str:
    return p.relative_to(paths.PROJECT_ROOT).as_posix()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    for flag in ("--check", "--status", "--build-preview", "--final", "--generate"):
        g.add_argument(flag, action="store_true")
    a = ap.parse_args()
    if a.generate:
        print("wrote", rel(S.generate_ready()))
        return 0
    if a.status:
        print("wrote", rel(S.write_status()))
        return 0
    if a.check:
        open_items = S.unresolved()
        for p in open_items:
            print("OPEN:", p)
        print(f"{len(open_items)} unresolved item(s)" if open_items else "no unresolved metadata")
        return 1 if open_items else 0
    written, problems = S.build(final=a.final)
    if problems:
        for p in problems:
            print("UNRESOLVED:", p)
        print(f"FAIL: final build refused, {len(problems)} unresolved item(s); nothing was written")
        return 1
    for p in written:
        print("wrote", rel(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
