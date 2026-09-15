"""Compare a clean invocation of the v1.2 dynamic-signal diagnostic with the reference outputs (D-059).

Pass criterion: every p8_dynamic_*.csv has the same columns and rows, numeric cells within 1e-12 (byte identity is
reported), and the provenance has identical design hashes, checks, trigger decision and source digests.
Usage: python scripts/verify_p8_dynamic_reproduction.py --candidate <root> [--reference outputs]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.io_guard import write_json  # noqa: E402

TOL = 1e-12


def rows(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def diff(a: str, b: str) -> float:
    if a == b:
        return 0.0
    try:
        return abs(float(a) - float(b))
    except ValueError:
        return float("inf")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference", type=Path, default=Path("outputs"))
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    ref_dir, cand_dir = (d / "metrics" / "p8_dynamic" for d in (a.reference, a.candidate))
    ok, checks = True, []
    names = sorted(p.name for p in ref_dir.glob("p8_dynamic_*.csv"))
    if names != sorted(p.name for p in cand_dir.glob("p8_dynamic_*.csv")):
        ok = False
        checks.append({"problem": "different table sets"})
    for name in names:
        r, c = rows(ref_dir / name), rows(cand_dir / name)
        shape = len(r) == len(c) and (not r or list(r[0]) == list(c[0]))
        worst = max((diff(x[k], y[k]) for x, y in zip(r, c) for k in x), default=0.0) if shape else float("inf")
        byte = (ref_dir / name).read_bytes() == (cand_dir / name).read_bytes()
        passed = shape and worst <= TOL
        ok &= passed
        checks.append({"table": name, "rows": len(r), "max_abs_diff": worst, "byte_identical": byte,
                       "passed": passed})
        print(f"{name}: {len(r)} rows, max |diff| {worst:.3g}, byte-identical {byte} -> {'PASS' if passed else 'FAIL'}")
    pr, pc = (json.loads((d / "p8_dynamic_provenance.json").read_text(encoding="utf-8")) for d in (ref_dir, cand_dir))
    same = all(pr[k] == pc[k] for k in ("design", "checks", "affine_trigger", "sources_sha256"))
    ok &= same
    checks.append({"provenance": "design, checks, trigger and source digests identical", "passed": same})
    print(f"provenance identical: {same}")
    out = a.out or (ref_dir / "p8_dynamic_reproduction_check.json")
    write_json(out, {"criterion": {"tables_abs": TOL}, "candidate_root": a.candidate.name, "passed": ok,
                     "checks": checks})
    print("reproduction:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
