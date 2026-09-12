"""Build the frozen protocol v1.0 split files and their SHA-256 manifest (D-031, D-037, D-042).

Canonical-only. Writes, before any window exists (L1):
  data/splits/v1.0_loso/outer_folds.csv
  data/splits/v1.0_loso/inner_folds.csv
  data/splits/v1.0_personalization/chronological.csv
  data/splits/v1.0_manifest.json
Split files are deterministic (byte-identical on rebuild from the same canonical_v1). The manifest's `build`
section (time, git commit) is the only part that changes between rebuilds.
Use --check to rebuild in memory and compare with the committed files without writing.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_json  # noqa: E402
from src.evaluation import splits as S  # noqa: E402
from src.evaluation.canonical_input import verify_canonical  # noqa: E402
from src.evaluation.p2_protocol import (build_split_tables, load_manifest, load_structure, make_manifest,  # noqa: E402
                                        manifest_path, scheme_summary, semantic, split_root)


def git_state() -> dict:
    run = lambda *a: subprocess.run(["git", *a], cwd=paths.PROJECT_ROOT, capture_output=True, text=True,  # noqa: E731
                                    encoding="utf-8")
    head = run("rev-parse", "HEAD").stdout.strip()
    dirty = bool(run("status", "--porcelain", "--untracked-files=no").stdout.strip())
    return {"git_commit": head or None, "git_dirty_tracked_files": dirty}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=0, help="recorded for convention; split construction is deterministic")
    ap.add_argument("--check", action="store_true", help="rebuild in memory and compare with the files on disk")
    args = ap.parse_args()
    before = verify_canonical()
    st = load_structure()
    sessions, pieces = st.sessions(), st.pieces()
    tables = build_split_tables(sessions, pieces)
    root = split_root()
    hashes = {rel: {"sha256": S.sha256_text(S.csv_text(rows, cols)), "rows": len(rows)}
              for rel, (rows, cols) in tables.items()}
    summary = scheme_summary(tables, pieces)
    if args.check:
        on_disk = {rel: S.file_sha256_lf(root / rel) if (root / rel).exists() else None for rel in S.SPLIT_FILES}
        ok = all(on_disk[rel] == hashes[rel]["sha256"] for rel in S.SPLIT_FILES)
        man = load_manifest(root) if manifest_path(root).exists() else {}
        fresh = make_manifest(hashes, before, summary, {})
        ok = ok and semantic(man) == semantic(fresh)
        for rel in S.SPLIT_FILES:
            print(f"{rel}: {'identical' if on_disk[rel] == hashes[rel]['sha256'] else 'DIFFERENT'}")
        print(f"manifest (semantic): {'identical' if semantic(man) == semantic(fresh) else 'DIFFERENT'}")
        return 0 if ok else 1
    for rel, (rows, cols) in tables.items():
        S.write_split(root / rel, rows, cols)
    if verify_canonical() != before:
        print("ERROR: canonical_v1 changed during the build", file=sys.stderr)
        return 3
    build = {"generated_at": datetime.now().isoformat(timespec="seconds"), "seed": args.seed, **git_state(),
             "python": sys.version.split()[0]}
    write_json(manifest_path(root), make_manifest(hashes, before, summary, build))
    for rel, h in hashes.items():
        print(f"{rel}: {h['rows']} rows, sha256 {h['sha256'][:16]}")
    print(f"manifest -> {manifest_path(root).relative_to(paths.PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
