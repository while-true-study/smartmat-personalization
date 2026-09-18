"""Build the final Applied Sciences submission artifacts from the frozen P16 manuscript (formatting only).

  python scripts/build_final_submission.py --template <path to applsci-template.docx>
  powershell -File scripts/render_docx_pages.ps1 -Docx <docx> -Pdf <pdf>        # visual QA (Microsoft Word)
  python scripts/build_final_submission.py --manifest-only --pages main=N,supplementary=M

Writes, under paper/submission_final/: manuscript/Applied_Sciences_SmartMat_Final.docx,
supplementary/Supplementary_Materials.docx, supplementary/Supplementary_Tables_S1-S44.xlsx and figures/ (Figures 1-6,
byte-identical to the P16 package). The template is read in place and never copied into the repository.
--manifest-only writes MANIFEST.json after the QA reports exist. Logic: src/paper/final_submission.py.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.paper import final_submission as F  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--template", type=Path, help="Applied Sciences Word template (.docx, OOXML)")
    ap.add_argument("--manifest-only", action="store_true")
    ap.add_argument("--pages", default="", help="page counts from the Word rendering, e.g. main=38,supplementary=9")
    a = ap.parse_args()
    if not a.manifest_only:
        if a.template is None:
            ap.error("--template is required")
        for p in (F.build_main(a.template), F.build_supplementary(a.template), F.build_workbook(),
                  *F.copy_figures()):
            print("wrote", p.relative_to(paths.PROJECT_ROOT).as_posix())
        return 0
    pages = {k: int(v) for k, v in (x.split("=") for x in a.pages.split(",") if x)}
    print("wrote", F.write_manifest(pages).relative_to(paths.PROJECT_ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
