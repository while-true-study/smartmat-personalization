"""P0 analysis A1 — cross-subject provenance audit. Read-only on raw data.

For every pair of subjects (and every pair of sources) this measures how many rows or row
sequences of one side also occur in the other, in three modes (src/data/provenance.py):
exact timestamp, minute-floored timestamp, and timestamp-free value sequences.

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/provenance/:
  cross_subject_provenance_summary.csv    subject pair x mode
  cross_subject_provenance_by_date.csv    subject pair x mode x calendar date
  cross_subject_provenance_by_source.csv  source pair x mode (incl. same-subject pairs, labelled)
  cross_subject_file_correspondence.csv   file-level alignment for flagged cross-subject source pairs
  provenance_tables.md                    auto-generated tables for the report
  provenance_run_meta.json                parameters, manifest checksum, integrity result

Interpretation lives in docs/P0_A1_PROVENANCE_REPORT.md. This script draws no identity conclusions.

Usage:
    python scripts/audit_cross_subject_provenance.py [--k 5]
"""
from __future__ import annotations

import argparse
import platform
import sys
import time
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_json, write_text  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.provenance import (  # noqa: E402
    DEFAULT_K, MODES, SourceData, Thresholds, by_date, compare, file_correspondence, load_sources, pair_scope,
    summary_record,
)

SUMMARY_COLUMNS = [
    "scope", "subject_a", "subject_b", "source_a", "source_b", "device_a", "device_b", "comparison_mode",
    "channels_used", "comparable_rows_a", "comparable_rows_b", "matched_rows_a", "matched_rows_b",
    "match_ratio_a", "match_ratio_b", "informative_matched_a", "informative_matched_b", "co_covered_dates",
    "overlapping_dates", "first_overlap", "last_overlap", "longest_matched_run", "longest_ordered_run",
    "ts_offset_rows", "ts_offset_s_min", "ts_offset_s_median", "ts_offset_s_max", "suspicious",
]
BY_DATE_COLUMNS = ["scope", "subject_a", "subject_b", "comparison_mode", "date", "comparable_rows_a",
                   "comparable_rows_b", "matched_rows_a", "matched_rows_b", "informative_matched_a",
                   "match_ratio_a", "match_ratio_b"]
CORR_COLUMNS = ["source_a", "source_b", "comparison_mode", "file_a", "file_b", "n_b_files_matched",
                "comparable_a", "matched_a_in_file_b", "ratio_a", "comparable_b", "matched_b_in_file_a", "ratio_b",
                "a_unmatched_leading", "a_unmatched_trailing", "a_unmatched_interior",
                "b_unmatched_leading", "b_unmatched_trailing", "b_unmatched_interior",
                "a_first_ts", "a_last_ts", "b_first_ts", "b_last_ts"]


def subject_unions(sources: dict[str, SourceData]) -> dict[str, SourceData]:
    by_subject: dict[str, list[SourceData]] = {}
    for s in sources.values():
        by_subject.setdefault(s.subject_id, []).append(s)
    return {
        subj: SourceData.concat(parts, source_id="+".join(p.source_id for p in parts), subject_id=subj,
                                device_id="|".join(sorted({p.device_id for p in parts})))
        for subj, parts in sorted(by_subject.items())
    }


def render_markdown(summary: list[dict]) -> str:
    """Report-generation helper: compact tables from the summary rows (no interpretation)."""
    def pct(x):
        return "—" if x in (None, "") else f"{100 * float(x):.2f} %"

    lines = ["| subject_a | subject_b | mode | comparable a / b | matched a / b | ratio a / b | "
             "informative matched a / b | overlapping dates | longest ordered run | suspicious |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary:
        lines.append(
            f"| {r['subject_a']} | {r['subject_b']} | {r['comparison_mode']} | "
            f"{r['comparable_rows_a']:,} / {r['comparable_rows_b']:,} | {r['matched_rows_a']:,} / {r['matched_rows_b']:,} | "
            f"{pct(r['match_ratio_a'])} / {pct(r['match_ratio_b'])} | "
            f"{r['informative_matched_a']:,} / {r['informative_matched_b']:,} | {r['overlapping_dates']} | "
            f"{r['longest_ordered_run']:,} | {'**yes**' if r['suspicious'] else 'no'} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--k", type=int, default=DEFAULT_K, help="rows per value-sequence fingerprint (mode C)")
    args = ap.parse_args()
    th = Thresholds()
    t0 = time.time()

    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2

    sources = load_sources(root, manifest)
    roles = {r["source_id"]: r["dataset_role"] for r in manifest}
    subjects = subject_unions(sources)
    print(f"loaded {len(sources)} sources / {len(subjects)} subjects / "
          f"{sum(s.n for s in sources.values()):,} rows in {time.time() - t0:.0f} s")

    summary, dated = [], []
    for sa, sb in combinations(sorted(subjects), 2):
        a, b = subjects[sa], subjects[sb]
        scope = pair_scope(a.subject_id, b.subject_id)
        for mode in MODES:
            res = compare(a, b, mode, k=args.k)
            summary.append(summary_record(a, b, res, scope, th))
            for d in by_date(a, b, res):
                dated.append({"scope": scope, "subject_a": sa, "subject_b": sb, "comparison_mode": mode, **d})

    by_source, corr = [], []
    for ia, ib in combinations(sorted(sources), 2):
        a, b = sources[ia], sources[ib]
        scope = pair_scope(a.subject_id, b.subject_id)
        for mode in MODES:
            res = compare(a, b, mode, k=args.k)
            rec = summary_record(a, b, res, scope, th)
            rec.update(role_a=roles.get(ia, ""), role_b=roles.get(ib, ""))
            by_source.append(rec)
            if rec["suspicious"] and mode in ("B_minute_ts_values", "C_value_sequence"):
                for c in file_correspondence(a, b, res):
                    corr.append({"source_a": ia, "source_b": ib, "comparison_mode": mode, **c})

    out = paths.p0_output_dir("provenance")
    write_csv(out / "cross_subject_provenance_summary.csv", summary, SUMMARY_COLUMNS)
    write_csv(out / "cross_subject_provenance_by_date.csv", dated, BY_DATE_COLUMNS)
    write_csv(out / "cross_subject_provenance_by_source.csv", by_source, SUMMARY_COLUMNS + ["role_a", "role_b"])
    write_csv(out / "cross_subject_file_correspondence.csv", corr, CORR_COLUMNS)
    write_text(out / "provenance_tables.md", render_markdown(summary))
    flagged_subject = sorted({(r["subject_a"], r["subject_b"]) for r in summary if r["suspicious"]})
    flagged_source = sorted({(r["source_a"], r["source_b"]) for r in by_source if r["suspicious"]})
    write_json(out / "provenance_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"],
        "manifest_sha256": sha256_file(mpath),
        "raw_integrity": {k: len(v) for k, v in integrity.items()},
        "parameters": {"k": args.k, "min_informative_matches": th.min_informative_matches,
                       "min_ordered_run": th.min_ordered_run, "modes": list(MODES)},
        "n_sources": len(sources), "n_subjects": len(subjects),
        "n_subject_pairs": len(summary) // len(MODES), "n_source_pairs": len(by_source) // len(MODES),
        "flagged_subject_pairs": flagged_subject, "flagged_source_pairs": flagged_source,
        "python": platform.python_version(), "numpy": np.__version__,
        "runtime_s": round(time.time() - t0, 1),
    })

    print(f"subject pairs: {len(summary) // len(MODES)}  source pairs: {len(by_source) // len(MODES)}  "
          f"-> {out.relative_to(paths.PROJECT_ROOT)}  ({time.time() - t0:.0f} s)")
    print(f"flagged cross-subject subject pairs: {flagged_subject}")
    print(f"flagged cross-subject source pairs:  {flagged_source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
