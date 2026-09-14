"""Validate a public release directory without private data (D-050). Logic: src/data/public_release.py.

Checks every artifact against manifest.json, runs the privacy/integrity validator, and rebuilds the fold and subject
window arrays to make sure they load. Exit code 0 only if every check passes.
  python scripts/validate_public_release.py [--data data/release/public_release_v1]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data import public_release as R  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, default=paths.PROJECT_ROOT / "data" / "release" / R.RELEASE_VERSION)
    a = ap.parse_args()
    checks = R.validate_release(a.data)
    try:
        rel = R.PublicRelease(a.data, verify=True)
        for f in (1, 2, 3):
            rel.fold_data(f)
        for s in R.ALLOWED_SUBJECTS:
            for b in (0, 1, 3, 7, 14):
                rel.subject_windows(s, b)
        checks.append({"check": "fold_and_subject_windows_load", "passed": True, "detail": "ok"})
    except Exception as exc:                                                        # fail closed
        checks.append({"check": "fold_and_subject_windows_load", "passed": False,
                       "detail": f"{type(exc).__name__}: {exc}"})
    for c in checks:
        print(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['check']}: {c['detail']}")
    ok = all(c["passed"] for c in checks)
    print(f"public release validation: {sum(c['passed'] for c in checks)}/{len(checks)} -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
