"""Export the P10 tables and report blocks (no hand-copied numbers; CONVENTIONS §5; D-064).

Reads outputs/metrics/p10/ (scripts/run_p10_level_baselines.py, scripts/run_p10_history.py) and writes:
  paper/tables/p10_*.csv, paper/tables/p10_*_provenance.json      paper-facing tables (committed)
  generated blocks of docs/P10_LEVEL_BASELINE_HISTORY_REPORT.md
  (<!-- BEGIN GENERATED P10:<name> --> … <!-- END GENERATED P10:<name> -->)

  python scripts/export_p10_tables.py [--rerun-root DIR]   DIR: a clean rerun to compare cell by cell
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.io_guard import write_csv, write_json, write_text  # noqa: E402

SUBJECTS = ("User01", "User02", "User07")
TARGETS = ("temperature", "humidity")
ADAPT = ("1", "3", "7", "14")
HISTORIES = ("40", "300", "900")
FAMILIES = {"ridge": "Ridge", "hgb": "HistGB"}
METRICS = paths.PROJECT_ROOT / "outputs" / "metrics" / "p10"
TABLES = paths.PROJECT_ROOT / "paper" / "tables"
REPORT = paths.PROJECT_ROOT / "docs" / "P10_LEVEL_BASELINE_HISTORY_REPORT.md"
MARK = re.compile(r"<!-- BEGIN GENERATED P10:(?P<name>[a-z_0-9]+) -->.*?<!-- END GENERATED P10:(?P=name) -->", re.S)
EXPORT = ("reproduction_check", "loso_constants", "loso_metrics", "rq2_constants", "rq2_metrics", "rq2_summary",
          "point_counts", "history_availability", "history_selection", "history_metrics", "history_bootstrap",
          "history_interpretation", "history_interpretation_summary")
PROVENANCE = ("p10_level_baselines_provenance.json", "p10_history_provenance.json")


def read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def num(x, fmt: str) -> str:
    if x in ("", None):
        return ""
    v = float(x)
    return "NA" if math.isnan(v) else format(v, fmt)


def md(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def one(rows: list[dict], **kw) -> dict:
    hit = [r for r in rows if all(str(r.get(k)) == str(v) for k, v in kw.items())]
    if len(hit) != 1:
        raise SystemExit(f"expected one row for {kw}, found {len(hit)}")
    return hit[0]


# ------------------------------------------------------------------------------------------------ blocks

def block_repro(t: dict) -> str:
    chk = t["reproduction_check"]
    scopes = {}
    for r in chk:
        s = scopes.setdefault(r["scope"], {"n": 0, "failed": 0, "max": 0.0, "exact": 0})
        s["n"] += 1
        s["failed"] += r["passed"] != "True"
        if r["kind"] == "float":
            s["max"] = max(s["max"], float(r["abs_diff"]))
        else:
            s["exact"] += 1
    rows = [[k, v["n"], v["exact"], v["n"] - v["exact"], v["failed"], f"{v['max']:.2e}"] for k, v in scopes.items()]
    total_failed = sum(v["failed"] for v in scopes.values())
    head = (f"**Table P10-1 — Reproduction check (tolerance: absolute 1e-9, relative 0; exact for keys, targets and "
            f"counts): {'PASS' if total_failed == 0 else 'FAIL'}, {len(chk)} checks, {total_failed} failed.**")
    return head + "\n\n" + md(["Scope", "Checks", "Exact", "Floating-point", "Failed", "Max abs diff"], rows)


def block_loso_median(t: dict) -> str:
    rows = []
    const = t["loso_constants"]
    for tg in TARGETS:
        for s in SUBJECTS:
            m = {p: one(t["loso_metrics"], subject_id=s, target=tg, predictor=p, seed=seed)
                 for p, seed in (("training_mean", ""), ("training_median", ""), ("raw_tcn", "mean"))}
            cm = one(const, subject_id=s, target=tg, statistic="training_mean")
            cd = one(const, subject_id=s, target=tg, statistic="training_median")
            rows.append([tg, s, f"{float(cm['value']):.2f} / {float(cd['value']):.2f}",
                         *[f"{num(m[p]['mae'], '.3f')} ({num(m[p]['bias'], '+.2f')})" for p in m],
                         f"{num(m['raw_tcn']['rmse'], '.3f')}", m["training_mean"]["n_windows"],
                         m["training_mean"]["n_nights"], f"{cm['n_train_windows']} / {cm['n_train_nights']}"])
    return ("**Table P10-2 — Strict LOSO, all labelled windows of the held-out subject: MAE (bias) of the source-"
            "training mean, the source-training median and the RAW-TCN (seed mean over seeds 0–2). Constants: one "
            "deterministic value each (mean / median). Fitting: labelled windows / nights of the outer training "
            "pool.**\n\n" +
            md(["Target", "Held-out subject", "Constant mean / median", "Training mean MAE (bias)",
                "Training median MAE (bias)", "RAW-TCN MAE (bias)", "RAW-TCN RMSE", "Test windows", "Test nights",
                "Fit windows / nights"], rows))


def block_rq2_median(t: dict) -> str:
    sm = t["rq2_summary"]
    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            a = one(sm, subject_id=s, target=tg, budget_nights=0, predictor="A")
            am = one(sm, subject_id=s, target=tg, budget_nights=0, predictor="A_med")
            c = one(sm, subject_id=s, target=tg, budget_nights=0, predictor="C")
            rows.append([tg, s, 0, num(a["mae"], ".3f"), num(am["mae"], ".3f"), "", "",
                         f"C {num(c['mae'], '.3f')} ± {num(c['mae_seed_sd'], '.3f')}", "", "", "", "", "",
                         "", f"{a['n_windows']} / {a['n_nights']}"])
            for b in ADAPT:
                g = {p: one(sm, subject_id=s, target=tg, budget_nights=b, predictor=p) for p in ("B", "B_med", "E",
                                                                                                "D")}
                sc = [r for r in sm if r["subject_id"] == s and r["target"] == tg and r["budget_nights"] == b
                      and r["predictor"] == "S"]
                rows.append([tg, s, b, "", "", num(g["B"]["mae"], ".3f"), num(g["B_med"]["mae"], ".3f"),
                             f"{num(g['E']['mae'], '.3f')} ± {num(g['E']['mae_seed_sd'], '.3f')}",
                             num(g["D"]["mae"], ".3f"), num(sc[0]["mae"], ".3f") if sc else "",
                             num(g["B"]["bias"], "+.2f"), num(g["B_med"]["bias"], "+.2f"), num(g["E"]["bias"], "+.2f"),
                             f"{g['B']['fit_windows']} / {g['B']['fit_nights']}", ""])
    return ("**Table P10-3 — Personalization, common primary span (nights ≥ 16): MAE of the source-training mean (A) "
            "and median (A_med), the adaptation-target mean (B) and median (B_med), full fine-tuning (E, seed mean ± "
            "SD), the offset-calibrated base (D, reused from v1.1, seed mean) and the scratch control (S, b = 14, "
            "seed mean); biases of B, B_med and E; labelled adaptation windows / nights. Row b = 0 shows A, A_med and "
            "the base model C. User02: constants pooled over both mats.**\n\n" +
            md(["Target", "Subject", "b", "A", "A_med", "B", "B_med", "E (C at b = 0)", "D", "S", "bias B",
                "bias B_med", "bias E", "fit windows / nights", "eval windows / nights"], rows))


def block_counts(t: dict) -> str:
    rows = [[r["setting"], r["comparison"], f"{r['count']}/{r['cells']}", r["cells_true"].replace(";", "; ")]
            for r in t["point_counts"]]
    return ("**Table P10-4 — Point-estimate counts: cells in which a constant's MAE is ≤ the neural seed-mean MAE. "
            "Descriptive only; not non-inferiority, equivalence or absence of a difference. Each constant counted "
            "separately.**\n\n" + md(["Setting", "Comparison", "Count", "Cells"], rows))


def block_availability(t: dict) -> str:
    rows = [[r["subject_id"], r["history_s"], r["labelled_endpoints"], r["available"], r["excluded"],
             r["excluded_session_start"], r["excluded_gap_gt_5s"], r["common"],
             f"{100 * float(r['common_share_of_labelled']):.1f} %", f"{r['common_nights']} / {r['labelled_nights']}"]
            for r in t["history_availability"]]
    return ("**Table P10-5 — Endpoint availability by history (labelled strict-LOSO endpoints). Excluded: the "
            "gap-free (≤ 5 s) segment starts less than H before the endpoint, at the session start or after an "
            "intra-session gap > 5 s. Common: available at 40, 300 and 900 s; every P10 model is trained, selected "
            "and evaluated on common endpoints only.**\n\n" +
            md(["Subject", "History (s)", "Labelled", "Available", "Excluded", "…session start", "…gap > 5 s",
                "Common", "Common share", "Common / labelled nights"], rows))


def block_history(t: dict) -> str:
    met = t["history_metrics"]
    out = []
    for tg in TARGETS:
        rows = []
        for s in SUBJECTS:
            def add(label, r):
                rows.append([s, label, num(r["mae"], ".3f"), num(r["bias"], "+.2f"), num(r["R"], ".2f"),
                             num(r["Q"], ".2f"), num(r["r_pooled"], "+.3f"), num(r["r_within"], "+.3f"),
                             num(r["r_within_mat"], "+.3f") if s == "User02" else "", r["train_pool"]])
            for f, name in FAMILIES.items():
                for h in HISTORIES:
                    add(f"{name} {h} s", one(met, subject_id=s, target=tg, predictor=f, history_s=h, seed=""))
            add("RAW-TCN 40 s (seed mean)", one(met, subject_id=s, target=tg, predictor="raw_tcn", seed="mean"))
            for p, name in (("training_mean_common", "Training mean (common pool)"),
                            ("training_median_common", "Training median (common pool)"),
                            ("training_mean_orig", "Training mean (full pool)"),
                            ("training_median_orig", "Training median (full pool)")):
                add(name, one(met, subject_id=s, target=tg, predictor=p))
        unit = "°C" if tg == "temperature" else "%RH"
        n = {s: one(met, subject_id=s, target=tg, predictor="training_mean_common") for s in SUBJECTS}
        cap = "; ".join(f"{s} {n[s]['n_windows']} windows / {n[s]['n_nights']} nights" for s in SUBJECTS)
        out.append(f"**Table P10-6{'a' if tg == 'temperature' else 'b'} — {tg.capitalize()} ({unit}), strict LOSO, "
                   f"common test endpoints ({cap}). R = error SD / target SD; Q = prediction SD / target SD; "
                   "correlations pooled, night-centred and (User02) night × mat-centred. The RAW-TCN was trained on "
                   "the full 40-s pool, the summary models on the common pool.**\n\n" +
                   md(["Subject", "Predictor", "MAE", "Bias", "R", "Q", "r pooled", "r within night",
                       "r within night × mat", "Training pool"], rows))
    return "\n\n".join(out)


def block_boot(t: dict) -> str:
    rows = [[r["subject_id"], r["target"], f"{r['first']} − {r['second']}", r["role"],
             f"{num(r['point_estimate'], '+.3f')} [{num(r['ci_lower'], '+.3f')}, {num(r['ci_upper'], '+.3f')}]",
             r["interval"]] for r in t["history_bootstrap"]]
    return ("**Table P10-7 — Night-level paired bootstrap on the common test endpoints, Δ = MAE(first) − MAE(second) "
            "(positive: second lower error); 2,000 resamples, RNG seed 0, 95 % percentile. Nights resampled "
            "independently. RAW-TCN comparisons are descriptive (different training pools).**\n\n" +
            md(["Subject", "Target", "Comparison", "Role", "Δ [95 %]", "Interval"], rows))


def block_interp(t: dict) -> str:
    rows = [[FAMILIES[r["family"]], r["history_s"], r["target"], f"{r['H_a_count']}/3",
             "yes" if r["H_a_rule_met_2_of_3"] == "True" else "no",
             "" if r["H_b_count"] == "" else f"{r['H_b_count']}/3",
             "" if r["H_b_rule_met_2_of_3"] == "" else ("yes" if r["H_b_rule_met_2_of_3"] == "True" else "no"),
             f"{r['H_c_count']}/3"] for r in t["history_interpretation_summary"]]
    cells = [[FAMILIES[r["family"]], r["history_s"], r["subject_id"], r["target"],
              "yes" if r["H_a_beats_training_mean_common"] == "True" else "no",
              {"": "", "True": "yes", "False": "no"}[r["H_b_longer_history_lower_error"]],
              "yes" if r["H_c_variation_beyond_level"] == "True" else "no"] for r in t["history_interpretation"]]
    return ("**Table P10-8 — Pre-registered interpretation map (plan §5.6). H-a: the (training mean, common pool) − "
            "model interval lies above zero. H-b: the (40 s − H) interval of the same family lies above zero. H-c: "
            "R < 1 and night-centred r ≥ 0.10 (User02 also night × mat-centred r ≥ 0.10).**\n\n" +
            md(["Family", "History (s)", "Target", "H-a subjects", "H-a rule (≥ 2/3)", "H-b subjects",
                "H-b rule (≥ 2/3)", "H-c subjects"], rows) +
            "\n\n**Table P10-9 — Per cell.**\n\n" +
            md(["Family", "History (s)", "Subject", "Target", "H-a", "H-b", "H-c"], cells))


def block_selection(t: dict) -> str:
    rows = [[r["fold"], r["held_out_subject"], FAMILIES[r["family"]], r["history_s"], r["config"],
             num(r["mean_criterion"], ".4f")] for r in t["history_selection"] if r["selected"] == "1"]
    return ("**Table P10-10 — Selected configurations (source-only inner A/B criterion; all grid scores in "
            "`paper/tables/p10_history_selection.csv`).**\n\n" +
            md(["Fold", "Held-out", "Family", "History (s)", "Selected", "Inner criterion"], rows))


def block_rerun(rerun: Path | None) -> str:
    if rerun is None:
        return "_No clean rerun compared in this export._"
    rows, ok_all = [], True
    for name in EXPORT:
        a, b = read(METRICS / f"p10_{name}.csv"), read(rerun / "metrics" / "p10" / f"p10_{name}.csv")
        same = a == b
        worst = 0.0
        if not same and len(a) == len(b):
            for ra, rb in zip(a, b):
                for k in ra:
                    try:
                        worst = max(worst, abs(float(ra[k]) - float(rb[k])))
                    except (TypeError, ValueError):
                        worst = math.inf if ra[k] != rb[k] else worst
        ok = same
        ok_all &= ok
        rows.append([f"p10_{name}.csv", len(a), "yes" if same else "no", f"{worst:.2e}", "pass" if ok else "FAIL"])
    return (f"**Clean rerun into a separate output root: {'PASS' if ok_all else 'FAIL'} (every table cell identical; "
            "provenance timestamps excluded).**\n\n" + md(["Table", "Rows", "Identical", "Max abs diff", "Result"],
                                                          rows))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rerun-root", type=Path)
    a = ap.parse_args()
    t = {n: read(METRICS / f"p10_{n}.csv") for n in EXPORT}
    for n in EXPORT:
        rows = t[n]
        cols = list(rows[0]) if rows else ["none"]
        write_csv(TABLES / f"p10_{n}.csv", rows, cols)
    for p in PROVENANCE:
        write_json(TABLES / p, json.loads((METRICS / p).read_text(encoding="utf-8")))
    blocks = {"repro": block_repro(t), "loso_median": block_loso_median(t), "rq2_median": block_rq2_median(t),
              "counts": block_counts(t), "availability": block_availability(t), "history": block_history(t),
              "bootstrap": block_boot(t), "interpretation": block_interp(t), "selection": block_selection(t),
              "rerun": block_rerun(a.rerun_root)}
    text = REPORT.read_text(encoding="utf-8")
    seen = set()

    def sub(m: re.Match) -> str:
        seen.add(m.group("name"))
        return f"<!-- BEGIN GENERATED P10:{m.group('name')} -->\n\n{blocks[m.group('name')]}\n\n" \
               f"<!-- END GENERATED P10:{m.group('name')} -->"
    text = MARK.sub(sub, text)
    missing = set(blocks) - seen
    if missing:
        raise SystemExit(f"report lacks generated blocks: {sorted(missing)}")
    write_text(REPORT, text)
    print(f"exported {len(EXPORT)} tables and {len(PROVENANCE)} provenance files; report blocks {sorted(seen)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
