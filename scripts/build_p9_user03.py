"""P9: rebuild the User03 external-validation artifact and its QA tables (D-061; protocol v1.3).

Logic: src/data/p9_user03.py (cross-source minute reconciliation + canonical_v1 rules) and
src/evaluation/p9_external.py (windows, QA). Reads the seven paired raw files (hash-verified), writes
data/external/p9_user03_v1/ (git-ignored), data/external/p9_user03_v1_manifest.json and
outputs/metrics/p9_user03/p9_user03_qa_*.csv. No model is trained and no target value is summarised.
  python scripts/build_p9_user03.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import p9_user03 as U  # noqa: E402
from src.data.io_guard import write_csv  # noqa: E402
from src.evaluation import p9_external as E  # noqa: E402


def main() -> int:
    res = U.build()
    s = res["summary"]
    print("design:", U.design_hashes())
    for r in s["coverage"]:
        print(f"night {r['night']} {r['category']:<26} minutes {r['minutes']:>5} csv rows {r['csv_rows']:>6} "
              f"txt rows {r['txt_rows']:>6}")
    print(f"reconstructed rows {s['reconstructed_rows']}, canonical rows {s['canonical_rows']} "
          f"(dedup removed {s['dedup_removed_rows']}); dot-value audit {s['dot_value_audit']}; "
          f"punctuation-only event rows {s['event_punctuation_only_rows']}")
    ew = E.user03_windows()
    qa = E.qa_rows(ew, s)
    for name, rows in qa.items():
        cols = list(dict.fromkeys(k for r in rows for k in r))
        write_csv(E.metrics_dir() / f"p9_user03_qa_{name}.csv", rows, cols)
    for r in qa["nights"]:
        print(f"night {r['night_index']}: windows {r['windows']}, labelled {r['labelled_windows']}, "
              f"sessions {r['sessions']}")
    print("totals:", qa["totals"][0])
    write_qa_report(s, qa)
    return 0


def md(header: list[str], rows: list[list]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def write_qa_report(s: dict, qa: dict) -> None:
    import re
    from src.data import paths
    from src.data.io_guard import write_text
    blocks = {}
    blocks["sources"] = md(["Night", "Role", "File id", "SHA-256 (first 12)", "Layout", "Data rows", "Non-data lines"],
                           [[r["night"], r["role"], r["file_id"], r["sha256"][:12], r.get("layout", "csv"),
                             r["data_rows"], ", ".join(f"{k} {v}" for k, v in sorted(r["non_data_lines"].items()))
                             or "—"] for r in sorted(s["sources"], key=lambda r: (r["night"], r["role"]))])
    cats = U.CATEGORIES
    rows = []
    for n in sorted({r["night"] for r in s["coverage"]}):
        cells = []
        for c in cats:
            hit = [r for r in s["coverage"] if r["night"] == n and r["category"] == c]
            cells.append(f"{hit[0]['minutes']} / {hit[0]['csv_rows']} / {hit[0]['txt_rows']}" if hit else "—")
        rows.append([n, *cells])
    tot = [sum(r[k] for r in s["coverage"] if r["category"] == c) for c in cats for k in ("minutes",)]
    csv_total = sum(r["data_rows"] for r in s["sources"] if r["role"] == "csv")
    blocks["coverage"] = ("**Minutes / CSV rows / TXT rows per night and category.**\n\n"
                          + md(["Night", *cats], rows)
                          + f"\n\n- Included CSV rows: {s['reconstructed_rows']} of {csv_total} "
                            f"({100 * s['reconstructed_rows'] / csv_total:.2f} %); minutes by category: "
                          + ", ".join(f"{c} {t}" for c, t in zip(cats, tot)) + "."
                          + f"\n- Rows included with a punctuation-only event difference: "
                            f"{s['event_punctuation_only_rows']}."
                          + f"\n- Dot-fused value audit (nights 1–6): {s['dot_value_audit']['equal_to_csv_p1']} of "
                            f"{s['dot_value_audit']['rows']} audited rows equal the CSV P1 (audit only).")
    t = qa["totals"][0]
    blocks["windows"] = (f"- Reconstructed rows {t['reconstructed_rows']}; canonical rows after the canonical_v1 rules "
                         f"{t['canonical_rows']} (exact-copy removal {t['dedup_removed_rows']}).\n"
                         f"- Windows {t['windows']}, labelled {t['labelled_windows']}; nights with labelled windows "
                         f"{t['nights_with_labelled_windows']}.\n\n"
                         + md(["Night", "Windows", "Labelled windows", "Sessions", "≥ 10 labelled windows"],
                              [[r["night_index"], r["windows"], r["labelled_windows"], r["sessions"],
                                "yes" if r["usable_for_per_night_r"] else "no"] for r in qa["nights"]]))
    rep = paths.PROJECT_ROOT / "docs" / "P9_USER03_QA_REPORT.md"
    text = rep.read_text(encoding="utf-8").replace("\r\n", "\n")
    mark = re.compile(r"<!-- BEGIN GENERATED P9QA:(?P<n>[a-z_]+) -->.*?<!-- END GENERATED P9QA:(?P=n) -->", re.S)
    if {m.group("n") for m in mark.finditer(text)} != set(blocks):
        raise SystemExit("QA report markers differ from the generated blocks")
    text = mark.sub(lambda m: f"<!-- BEGIN GENERATED P9QA:{m.group('n')} -->\n\n{blocks[m.group('n')]}\n\n"
                              f"<!-- END GENERATED P9QA:{m.group('n')} -->", text)
    write_text(rep, text)


if __name__ == "__main__":
    raise SystemExit(main())
