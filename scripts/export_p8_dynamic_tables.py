"""Export the v1.2 dynamic-signal diagnostic tables and report blocks (no hand-copied numbers; D-059).

Reads outputs/metrics/p8_dynamic/ (scripts/run_p8_dynamic.py) and writes:
  paper/tables/p8_dynamic_*.csv, paper/tables/p8_dynamic_provenance.json     paper-facing tables (committed)
  generated blocks of docs/P8_DYNAMIC_SIGNAL_REPORT.md
  (<!-- BEGIN GENERATED P8D:<name> --> … <!-- END GENERATED P8D:<name> -->)
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_json, write_text  # noqa: E402

SUBJECTS = ("User01", "User02", "User07")
TARGETS = ("temperature", "humidity")
METRICS = paths.PROJECT_ROOT / "outputs" / "metrics" / "p8_dynamic"
TABLES = paths.PROJECT_ROOT / "paper" / "tables"
MARK = re.compile(r"<!-- BEGIN GENERATED P8D:(?P<name>[a-z_0-9]+) -->.*?<!-- END GENERATED P8D:(?P=name) -->", re.S)
NAMES = {"C": "RAW-TCN base (b = 0)", "D": "RAW-TCN + offset", "E": "full fine-tuning", "S": "scratch control"}
PAPER = ("summary", "by_seed", "bootstrap", "oracle_affine", "cases", "headlines", "trigger")
JCASES = ("J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8_cell", "unmapped_within_only")


def read(name: str) -> list[dict]:
    with open(METRICS / f"p8_dynamic_{name}.csv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def f3(x) -> str:
    return "NA" if x in ("", None, "nan") else f"{float(x):.3f}"


def s3(x) -> str:
    return "NA" if x in ("", None, "nan") else f"{float(x):+.3f}"


def md(header: list[str], rows: list[list]) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def pick(rows: list[dict], **kw) -> dict:
    hit = [r for r in rows if all(str(r[k]) == str(v) for k, v in kw.items())]
    if len(hit) != 1:
        raise SystemExit(f"expected one row for {kw}, got {len(hit)}")
    return hit[0]


def export_tables(t: dict[str, list[dict]], prov: dict) -> None:
    for name in PAPER:
        rows = [dict(r, protocol_version="v1.2") for r in t[name]]
        cols = list(dict.fromkeys(k for r in rows for k in r))
        write_csv(TABLES / f"p8_dynamic_{name}.csv", [{c: r.get(c, "") for c in cols} for r in rows], cols)
    write_json(TABLES / "p8_dynamic_provenance.json", {
        "description": "P8 final dynamic-signal diagnostic (protocol v1.2 addendum, D-059); second-order post hoc, "
                       "diagnostic, supplementary", "design": prov["design"],
        "analysis_git_commit": prov["git_commit"], "analysis_tree_dirty": prov["git_dirty_tracked_files"],
        "checks": prov["checks"], "affine_trigger": prov["affine_trigger"],
        "sources_sha256": dict(sorted(prov["sources_sha256"].items()))})


def _ci(boot: list[dict], subj: str, tgt: str, cond: str, b: str, stat: str, seed: str = "0") -> str:
    r = pick(boot, subject_id=subj, target=tgt, condition=cond, budget_nights=b, seed=seed, statistic=stat)
    return f"[{s3(r['ci_lower'])}, {s3(r['ci_upper'])}]"


def blocks(t: dict[str, list[dict]], prov: dict) -> dict[str, str]:
    summ, boot, cases = t["summary"], t["bootstrap"], t["cases"]
    out = {}
    h = t["headlines"]
    trig = prov["affine_trigger"]
    lines = [f"- {r['condition']} (b = {r['budget_nights']}), {r['target']}: **{r['headline']}** (within-night "
             f"positive in {r['subjects_within_positive']}/3 subjects, pooled positive in "
             f"{r['subjects_pooled_positive']}/3)." for r in h]
    lines.append(f"- Affine-calibration trigger: **{'fired' if trig['fired'] else 'not fired'}** "
                 + "; ".join(f"{tg}: qualifying subjects {v['qualifying_subjects'] or 'none'}"
                             for tg, v in trig["per_target"].items()) + ".")
    ors = [float(r["oracle_affine"]) for r in summ if r["condition"] in "CES" and r["oracle_affine"] not in ("", "nan")]
    lines.append(f"- Retrospective oracle affine ratio over all neural conditions and budgets: {min(ors):.3f}–"
                 f"{max(ors):.3f}.")
    ck = prov["checks"]
    lines.append(f"- Checks: identity max gap {ck['identity_max_gap']:.1e}; D vs C max difference "
                 f"{ck['d_equals_c_max_abs_diff']:.1e}; constant rows (R, Q) = {ck['constant_rows_R_Q']}.")
    out["headline"] = "**Summary (generated).**\n\n" + "\n".join(lines)

    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            for c, b in (("C", "0"), ("E", "14"), ("S", "14")):
                r = pick(summ, subject_id=s, target=tg, condition=c, budget_nights=b)
                cs = pick(cases, subject_id=s, target=tg, condition=c, budget_nights=b)
                rows.append([tg, s, NAMES[c], f3(r["R"]), f3(r["Q"]),
                             f"{s3(r['r_pooled'])} {_ci(boot, s, tg, c, b, 'r_pooled')}",
                             f"{s3(r['r_within'])} {_ci(boot, s, tg, c, b, 'r_within')}",
                             f"{s3(r['r_within_mat'])} {_ci(boot, s, tg, c, b, 'r_within_mat')}",
                             f3(r["oracle_affine"]), s3(r["per_night_r_median"]), r["n_nights_eligible"],
                             ", ".join(j.replace("_cell", "").replace("unmapped_within_only", "within-only")
                                       for j in JCASES if cs[j] == "True") or "—"])
    out["main"] = ("**Table P8D-1 — Base model (C, b = 0), full fine-tuning (E, b = 14) and scratch control (S, "
                   "b = 14) on the primary span: seed means; brackets: seed-0 95 % night-cluster bootstrap interval. "
                   "D (base + offset) has exactly C's values. A and B (constants): R = 1, Q = 0, r = NA.**\n\n"
                   + md(["Target", "Subject", "Model", "R", "Q", "r pooled", "r within night", "r within night × mat",
                         "R_oracle_affine", "median per-night r", "eligible nights", "Cases"], rows))

    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            for b in ("1", "3", "7", "14"):
                r = pick(summ, subject_id=s, target=tg, condition="E", budget_nights=b)
                cs = pick(cases, subject_id=s, target=tg, condition="E", budget_nights=b)
                rows.append([tg, s, b, f3(r["R"]), f3(r["Q"]),
                             f"{s3(r['r_pooled'])} {_ci(boot, s, tg, 'E', b, 'r_pooled')}",
                             f"{s3(r['r_within'])} {_ci(boot, s, tg, 'E', b, 'r_within')}",
                             f"{s3(r['r_within_mat'])}", f3(r["oracle_affine"]),
                             ", ".join(j.replace("_cell", "").replace("unmapped_within_only", "within-only")
                                       for j in JCASES if cs[j] == "True") or "—"])
    out["budgets"] = ("**Table P8D-2 — Full fine-tuning at every budget (seed means; seed-0 intervals).**\n\n"
                      + md(["Target", "Subject", "b", "R", "Q", "r pooled", "r within night", "r within night × mat",
                            "R_oracle_affine", "Cases"], rows))

    bs = t["by_seed"]
    rows = []
    side = {"above_zero": "+", "below_zero": "−", "includes_zero": "0", "undefined": "NA"}
    for tg in TARGETS:
        for s in SUBJECTS:
            for c, b in (("C", "0"), ("E", "14"), ("S", "14")):
                cells = []
                for stat in ("r_pooled", "r_within", "r_within_mat", "oracle_affine"):
                    vals = []
                    for k in ("0", "1", "2"):
                        r = pick(bs, subject_id=s, target=tg, condition=c, budget_nights=b, seed=k)
                        v = f3(r[stat]) if stat == "oracle_affine" else s3(r[stat])
                        if stat != "oracle_affine":
                            v += " " + side[pick(boot, subject_id=s, target=tg, condition=c, budget_nights=b,
                                                 seed=k, statistic=stat)["interval"]]
                        vals.append(v)
                    cells.append(" / ".join(vals))
                rows.append([tg, s, NAMES[c], *cells])
    out["seeds"] = ("**Table P8D-3 — Seed sensitivity: seeds 0 / 1 / 2 (each with the side of its own 95 % interval: "
                    "+ above zero, − below, 0 includes zero).**\n\n"
                    + md(["Target", "Subject", "Model", "r pooled", "r within night", "r within night × mat",
                          "R_oracle_affine"], rows))

    rows = []
    for c, b in (("C", "0"), ("E", "1"), ("E", "3"), ("E", "7"), ("E", "14"), ("S", "14")):
        cs = [r for r in cases if r["condition"] == c and r["budget_nights"] == b]
        rows.append([c, b, *(sum(r[j] == "True" for r in cs) for j in JCASES), len(cs)])
    out["cases"] = ("**Table P8D-4 — Pre-registered cases J1–J8 (plan §6): number of subject × target cells per "
                    "condition (J8 = cell-level oracle ratio ≤ 0.90; the consistent pattern is the §7 trigger).**\n\n"
                    + md(["Model", "b", *[j.replace("_cell", "").replace("unmapped_within_only", "within-only")
                                          for j in JCASES], "Cells"], rows))

    dr = [r for r in boot if r["statistic"] == "delta_r_within" and r["seed"] == "0"]
    rows = [[r["target"], r["subject_id"], r["condition"], r["budget_nights"],
             f"{s3(r['point_estimate'])} [{s3(r['ci_lower'])}, {s3(r['ci_upper'])}]"] for r in dr]
    out["paired"] = ("**Table P8D-5 — Paired change of the within-night correlation on the same resampled nights "
                     "(seed 0): E − C at every budget and S − E at b = 14.**\n\n"
                     + md(["Target", "Subject", "Comparison", "b", "Δ r within night [95 %]"], rows))

    p = METRICS / "p8_dynamic_reproduction_check.json"
    if p.is_file():
        rec = json.loads(p.read_text(encoding="utf-8"))
        rows = [[c["table"], c["rows"], f"{c['max_abs_diff']:.3g}", "yes" if c["byte_identical"] else "no",
                 "pass" if c["passed"] else "FAIL"] for c in rec["checks"] if "table" in c]
        out["reproduction"] = (f"**Clean invocation into a separate output root: {'PASS' if rec['passed'] else 'FAIL'}"
                               f" (tables within {rec['criterion']['tables_abs']:g}; provenance design, checks, "
                               "trigger and source digests identical).**\n\n"
                               + md(["Table", "Rows", "Max abs diff", "Byte-identical", "Result"], rows))
    else:
        out["reproduction"] = "Clean invocation not recorded yet."
    return out


def main() -> int:
    t = {n: read(n) for n in PAPER}
    prov = json.loads((METRICS / "p8_dynamic_provenance.json").read_text(encoding="utf-8"))
    export_tables(t, prov)
    b = blocks(t, prov)
    rep = paths.PROJECT_ROOT / "docs" / "P8_DYNAMIC_SIGNAL_REPORT.md"
    text = rep.read_text(encoding="utf-8").replace("\r\n", "\n")
    found = {m.group("name") for m in MARK.finditer(text)}
    if found != set(b):
        raise SystemExit(f"report markers {sorted(found)} != generated blocks {sorted(b)}")
    text = MARK.sub(lambda m: f"<!-- BEGIN GENERATED P8D:{m.group('name')} -->\n\n{b[m.group('name')]}\n\n"
                              f"<!-- END GENERATED P8D:{m.group('name')} -->", text)
    write_text(rep, text)
    print(f"wrote paper/tables/p8_dynamic_*.csv, p8_dynamic_provenance.json and {len(b)} report blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
