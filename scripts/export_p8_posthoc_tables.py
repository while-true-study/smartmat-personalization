"""Export the P8 post-hoc validation tables and report blocks (no hand-copied numbers; CONVENTIONS §5; D-057).

Reads outputs/metrics/p8_posthoc/ (scripts/run_p8_posthoc.py) and the frozen P6 User02 context tables, and writes:
  paper/tables/p8_*.csv, paper/tables/p8_posthoc_provenance.json     paper-facing tables (committed)
  generated blocks of docs/P8_POSTHOC_VALIDATION_REPORT.md
  (<!-- BEGIN GENERATED P8:<name> --> … <!-- END GENERATED P8:<name> -->)
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
BUDGETS = ("0", "1", "3", "7", "14")
ADAPT = ("1", "3", "7", "14")
MATS = ("22480", "22482")
UNIT = {"temperature": "°C", "humidity": "%RH"}
NAMES = {"A": "Training mean", "B": "Adaptation-target mean", "C": "RAW-TCN base", "D": "RAW-TCN bias-calibrated",
         "E": "Full fine-tuning", "S": "Scratch (initialization control)"}
PER_MAT_LABEL = "post-hoc per-device calibration diagnostic added after the primary results were known"
MARK = re.compile(r"<!-- BEGIN GENERATED P8:(?P<name>[a-z_0-9]+) -->.*?<!-- END GENERATED P8:(?P=name) -->", re.S)
METRICS = paths.PROJECT_ROOT / "outputs" / "metrics" / "p8_posthoc"
TABLES = paths.PROJECT_ROOT / "paper" / "tables"


def read(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def f3(x) -> str:
    return f"{float(x):.3f}" if x not in ("", None) else ""


def f2(x) -> str:
    return f"{float(x):.2f}" if x not in ("", None) else ""


def sgn(x) -> str:
    return f"{float(x):+.3f}" if x not in ("", None) else ""


def md(header: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pick(rows: list[dict], **kw) -> dict:
    hit = [r for r in rows if all(str(r[k]) == str(v) for k, v in kw.items())]
    if len(hit) != 1:
        raise SystemExit(f"expected one row for {kw}, got {len(hit)}")
    return hit[0]


def cols(rows: list[dict], first: list[str]) -> list[str]:
    return first + [c for c in dict.fromkeys(k for r in rows for k in r) if c not in first]


# ------------------------------------------------------------------------------------------------------ tables

MAIN = ["subject_id", "target", "budget_nights", "predictor", "predictor_name", "calibration", "n_seeds", "mae",
        "mae_seed_sd", "mae_seed_min", "mae_seed_max", "rmse", "bias", "err_sd", "target_sd", "R", "R_seed_min",
        "R_seed_max", "offset_mean", "fit_windows", "n_windows", "n_nights"]
SEED = ["subject_id", "target", "budget_nights", "predictor", "predictor_name", "calibration", "seed", "mae", "rmse",
        "bias", "err_sd", "target_sd", "R", "offset", "fit_windows", "n_windows", "n_nights"]


def paper_tables(t: dict[str, list[dict]]) -> dict[str, tuple[list[dict], list[str]]]:
    summary, by_seed = t["summary"], t["by_seed"]
    primary = lambda r: r["eval_scope"] == "all" and r["calibration"] in ("none", "pooled")  # noqa: E731
    order = lambda r: (SUBJECTS.index(r["subject_id"]), TARGETS.index(r["target"]),  # noqa: E731
                       int(r["budget_nights"] or 0), r["predictor"], r["calibration"], str(r.get("seed", "")))
    main = sorted((r for r in summary if primary(r) and r["predictor"] in "ABCDE"), key=order)
    seeds = sorted((r for r in by_seed if primary(r) and r["predictor"] in "ABCDE"), key=order)
    per_mat = sorted((dict(r, eval_mat=r["eval_scope"], status=PER_MAT_LABEL) for r in summary
                      if r["subject_id"] == "User02" and r["eval_scope"] in MATS and r["predictor"] in "ABCDE"),
                     key=lambda r: (r["eval_mat"], TARGETS.index(r["target"]), int(r["budget_nights"]),
                                    r["predictor"], r["calibration"]))
    per_mat += [dict(r, status=f"not estimable ({r['reason']}); {PER_MAT_LABEL}") for r in t["not_estimable"]]
    resid = [dict(r, setting="strict_loso") for r in t["loso_summary"]]
    resid += [dict(r, setting="rq2_primary_span") for r in sorted(
        (r for r in summary if primary(r) and r["predictor"] in "ABCDES"), key=order)]
    control = []
    for r in sorted((r for r in by_seed if primary(r) and r["budget_nights"] == "14" and r["predictor"] in "BCES"),
                    key=order):
        control.append({**{k: r[k] for k in ("subject_id", "target", "predictor", "predictor_name", "seed")},
                        **{k: r[k] for k in ("mae", "rmse", "bias", "err_sd", "target_sd", "R", "n_windows",
                                             "n_nights")}})
    for r in sorted((r for r in summary if primary(r) and r["budget_nights"] == "14" and r["predictor"] in "BES"),
                    key=order):
        control.append({**{k: r[k] for k in ("subject_id", "target", "predictor", "predictor_name")},
                        "seed": "mean" if r["n_seeds"] != "1" else "", "mae_seed_sd": r["mae_seed_sd"],
                        **{k: r[k] for k in ("mae", "rmse", "bias", "err_sd", "target_sd", "R", "n_windows",
                                             "n_nights")}})
    c_base = [r for r in summary if primary(r) and r["budget_nights"] == "0" and r["predictor"] == "C"]
    control += [{**{k: r[k] for k in ("subject_id", "target", "predictor", "predictor_name")}, "seed": "mean",
                 "mae_seed_sd": r["mae_seed_sd"], **{k: r[k] for k in ("mae", "rmse", "bias", "err_sd", "target_sd",
                                                                        "R", "n_windows", "n_nights")}}
                for r in c_base]
    control.sort(key=lambda r: (SUBJECTS.index(r["subject_id"]), TARGETS.index(r["target"]), "CBES".index(
        r["predictor"]), str(r["seed"])))
    boot = sorted(t["bootstrap"], key=lambda r: (SUBJECTS.index(r["subject_id"]), TARGETS.index(r["target"]),
                                                  int(r["budget_nights"]), r["first"], r["second"], r["seed"]))
    return {"p8_calibration_main": (main, MAIN),
            "p8_calibration_by_seed": (seeds, SEED),
            "p8_calibration_user02_per_mat": (per_mat, cols(per_mat, ["status", "eval_mat"] + MAIN)),
            "p8_residual_variation": (resid, ["setting"] + [c for c in MAIN if c not in ("calibration",)]),
            "p8_initialization_control": (control, ["subject_id", "target", "predictor", "predictor_name", "seed",
                                                    "mae", "mae_seed_sd", "rmse", "bias", "err_sd", "target_sd",
                                                    "R", "n_windows", "n_nights"]),
            "p8_comparator_bootstrap": (boot, list(boot[0])),
            "p8_interpretation_cases": (t["interpretation"], cols(t["interpretation"], []))}


def paper_provenance(prov: dict) -> dict:
    """Paper-facing provenance: hashes and checks only (no run identifiers or wall-clock times)."""
    return {"description": "P8 post-hoc validation analyses (protocol v1.1 addendum, D-057); post hoc and "
                           "supplementary, never replacing a v1.0 primary result",
            "design": prov["design"], "identities": prov["identities"], "checks": prov["checks"],
            "inputs_sha256": dict(sorted(prov["inputs_sha256"].items())),
            "init_control_runs": [{k: v for k, v in r.items() if k != "run_id"} for r in prov["init_control_runs"]]}


# ------------------------------------------------------------------------------------------------ report blocks

def blocks(t: dict[str, list[dict]], heater: list[dict], heater_boot: list[dict]) -> dict[str, str]:
    summary, boot, cases = t["summary"], t["bootstrap"], t["interpretation"]
    main = [r for r in summary if r["eval_scope"] == "all" and r["calibration"] in ("none", "pooled")]
    val = lambda s, tg, b, p, k="mae": pick(main, subject_id=s, target=tg, budget_nights=b, predictor=p)[k]  # noqa
    out = {}

    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            for b in BUDGETS:
                cells = [f3(val(s, tg, "0", "A"))]
                cells += [f3(val(s, tg, b, "B"))] if b != "0" else ["—"]
                cells += [f3(val(s, tg, "0", "C"))]
                if b != "0":
                    d, e = (pick(main, subject_id=s, target=tg, budget_nights=b, predictor=p) for p in "DE")
                    cells += [f"{f3(d['mae'])} ± {f3(d['mae_seed_sd'])}", f"{f3(e['mae'])} ± {f3(e['mae_seed_sd'])}"]
                else:
                    cells += ["—", "= C"]
                rows.append([tg, s, b, *cells])
    out["calibration"] = ("**Table P8-1 — Primary span (nights ≥ 16), MAE of the five predictors (deterministic "
                          "predictors: single value; neural: seed mean ± seed SD, seeds 0–2). A and C do not depend on "
                          "b. User02: one offset pooled over both mats.**\n\n"
                          + md(["Target", "Subject", "b", "A training mean", "B adaptation mean", "C RAW-TCN base",
                                "D RAW-TCN + c_b", "E full FT"], rows))

    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            for b in ADAPT:
                rows.append([tg, s, b, *(sgn(val(s, tg, b if p in "BDE" else "0", p, "bias")) for p in "ABCDE")])
    out["bias"] = ("**Table P8-2 — Primary-span bias = mean(ŷ − y) (seed mean for C, D, E).**\n\n"
                   + md(["Target", "Subject", "b", "A", "B", "C", "D", "E"], rows))

    loso = t["loso_summary"]
    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            a = pick(loso, subject_id=s, target=tg, predictor="A")
            c = pick(loso, subject_id=s, target=tg, predictor="C")
            rows.append([tg, s, f3(a["target_sd"]), f3(a["err_sd"]), f2(a["R"]), f3(c["err_sd"]),
                         f"{f2(c['R'])} ({f2(c['R_seed_min'])}–{f2(c['R_seed_max'])})", a["n_nights"]])
    out["residual_loso"] = ("**Table P8-3 — Strict LOSO (all labelled windows of the held-out subject; the Table 2 "
                            "setting): target SD, error SD and R = error SD / target SD (population SDs; RAW-TCN: seed "
                            "mean, in brackets the seed range). R is a descriptive ratio, not explained variance.**\n\n"
                            + md(["Target", "Subject", "Target SD", "Error SD, training mean", "R, training mean",
                                  "Error SD, RAW-TCN", "R, RAW-TCN", "Nights"], rows))
    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            tsd = val(s, tg, "0", "A", "target_sd")
            for b in BUDGETS:
                cells = [f3(tsd), f"{f3(val(s, tg, '0', 'C', 'err_sd'))} / {f2(val(s, tg, '0', 'C', 'R'))}"]
                if b != "0":
                    cells.append(f"{f3(val(s, tg, b, 'E', 'err_sd'))} / {f2(val(s, tg, b, 'E', 'R'))}")
                else:
                    cells.append("= C")
                rows.append([tg, s, b, *cells])
    out["residual_rq2"] = ("**Table P8-4 — Primary span: target SD, and error SD / R of the RAW-TCN base (C; equal "
                           "for D, a constant offset) and of full fine-tuning (E); seed means. A and B have R = 1 "
                           "(constant predictors).**\n\n"
                           + md(["Target", "Subject", "b", "Target SD", "C (= D): error SD / R", "E: error SD / R"],
                                rows))

    ctl = t["by_seed"]
    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            for p in "SE":
                per = [pick(ctl, subject_id=s, target=tg, budget_nights="14", predictor=p, seed=k, eval_scope="all",
                            calibration="none") for k in ("0", "1", "2")]
                m = pick(main, subject_id=s, target=tg, budget_nights="14", predictor=p)
                rows.append([tg, s, NAMES[p], *(f3(r["mae"]) for r in per), f3(m["mae"]), sgn(m["bias"]),
                             f3(m["err_sd"]), f2(m["R"])])
            b = pick(main, subject_id=s, target=tg, budget_nights="14", predictor="B")
            rows.append([tg, s, NAMES["B"], "", "", "", f3(b["mae"]), sgn(b["bias"]), f3(b["err_sd"]), f2(b["R"])])
    out["control"] = ("**Table P8-5 — Initialization control at b = 14 (nights 1–14 for training, night 15 unused, "
                      "nights ≥ 16 evaluated): randomly initialised RAW-TCN (S) vs the pretrained full fine-tuning "
                      "(E), identical recipe; the adaptation-target mean (B) for reference.**\n\n"
                      + md(["Target", "Subject", "Predictor", "MAE seed 0", "MAE seed 1", "MAE seed 2",
                            "MAE mean", "Bias", "Error SD", "R"], rows))

    pm = [r for r in summary if r["subject_id"] == "User02" and r["eval_scope"] in MATS]
    rows = []
    for mat in MATS:
        for tg in TARGETS:
            for b in ADAPT:
                g = lambda p, c: pick(pm, eval_scope=mat, target=tg, budget_nights=b, predictor=p,  # noqa: E731
                                      calibration=c)["mae"]
                rows.append([mat, tg, b, f3(pick(pm, eval_scope=mat, target=tg, budget_nights="0", predictor="C",
                                                 calibration="none")["mae"]),
                             f3(g("B", "pooled")), f3(g("B", "per_mat")), f3(g("D", "pooled")), f3(g("D", "per_mat")),
                             f3(g("E", "none"))])
    ne = "; ".join(f"b = {r['budget_nights']} mat {r['calibration']}" for r in t["not_estimable"]) or "none"
    out["per_mat"] = (f"**Table P8-6 — User02 by mat, primary span, MAE (seed means): pooled vs per-mat offsets "
                      f"({PER_MAT_LABEL}). Not estimable: {ne}.**\n\n"
                      + md(["Mat", "Target", "b", "C base", "B pooled", "B per mat", "D pooled", "D per mat",
                            "E full FT"], rows))

    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            for b in ADAPT:
                cells = []
                for first, second in (("D", "E"), ("B", "E"), ("B", "D")):
                    r0 = pick(boot, subject_id=s, target=tg, budget_nights=b, first=first, second=second, seed="0")
                    sides = "/".join({"above_zero": "+", "below_zero": "−", "includes_zero": "0"}[
                        pick(boot, subject_id=s, target=tg, budget_nights=b, first=first, second=second,
                             seed=k)["interval"]] for k in ("0", "1", "2"))
                    cells.append(f"{sgn(r0['point_estimate'])} [{sgn(r0['ci_lower'])}, {sgn(r0['ci_upper'])}] {sides}")
                rows.append([tg, s, b, *cells])
    out["bootstrap"] = ("**Table P8-7 — Paired night-level bootstrap, Δ = MAE(first) − MAE(second) (positive = the "
                        "second predictor better): seed-0 point and 95 % interval (2,000 resamples, RNG seed 0), then "
                        "the interval side for seeds 0/1/2 (+ above zero, − below, 0 includes zero).**\n\n"
                        + md(["Target", "Subject", "b", "D − E", "B − E", "B − D"], rows))
    rows = []
    for tg in TARGETS:
        for s in SUBJECTS:
            cells = []
            for first, second in (("S", "E"), ("B", "S")):
                r0 = pick(boot, subject_id=s, target=tg, budget_nights="14", first=first, second=second, seed="0")
                sides = "/".join({"above_zero": "+", "below_zero": "−", "includes_zero": "0"}[
                    pick(boot, subject_id=s, target=tg, budget_nights="14", first=first, second=second,
                         seed=k)["interval"]] for k in ("0", "1", "2"))
                cells.append(f"{sgn(r0['point_estimate'])} [{sgn(r0['ci_lower'])}, {sgn(r0['ci_upper'])}] {sides}")
            rows.append([tg, s, *cells])
    out["bootstrap_control"] = ("**Table P8-8 — b = 14 initialization-control comparisons (same convention).**\n\n"
                                + md(["Target", "Subject", "S − E", "B − S"], rows))

    yes = lambda r, k: r.get(k) == "True"  # noqa: E731
    rows = []
    for r in cases:
        flags = [c for c, k in (("A", "case_A_B_le_E"), ("B", "case_B_D_approx_E"), ("C", "case_C_E_better_than_D"),
                                ("D", "case_D"), ("E", "case_E"), ("F", "case_F_S_better_than_B"),
                                ("G", "case_G_S_not_better_than_B"), ("H", "case_H_E_better_than_S"),
                                ("I", "case_I_S_approx_or_better_than_E")) if yes(r, k)]
        extra = [n for n, k in (("E>B", "E_better_than_B"), ("B>E", "B_better_than_E"), ("D>E", "D_better_than_E"),
                                ("B>D", "B_better_than_D"), ("D>B", "D_better_than_B"), ("S>E", "S_better_than_E"))
                 if yes(r, k)]
        rows.append([r["target"], r["subject_id"], r["budget_nights"], ", ".join(flags) or "—", ", ".join(extra) or "—"])
    count = lambda k, b=None: sum(yes(r, k) for r in cases if b is None or r["budget_nights"] == b)  # noqa: E731
    n14 = sum(r["budget_nights"] == "14" for r in cases)
    summ = [["A: B seed-mean MAE ≤ E", f"{count('case_A_B_le_E')}/{len(cases)}", f"{count('case_A_B_le_E', '14')}/{n14}"],
            ["B: D ≈ E", f"{count('case_B_D_approx_E')}/{len(cases)}", f"{count('case_B_D_approx_E', '14')}/{n14}"],
            ["C: E better than D", f"{count('case_C_E_better_than_D')}/{len(cases)}",
             f"{count('case_C_E_better_than_D', '14')}/{n14}"],
            ["(E better than B)", f"{count('E_better_than_B')}/{len(cases)}", f"{count('E_better_than_B', '14')}/{n14}"],
            ["(B better than E)", f"{count('B_better_than_E')}/{len(cases)}", f"{count('B_better_than_E', '14')}/{n14}"],
            ["(D better than E)", f"{count('D_better_than_E')}/{len(cases)}", f"{count('D_better_than_E', '14')}/{n14}"],
            ["F: S better than B (b = 14)", "", f"{count('case_F_S_better_than_B')}/{n14}"],
            ["G: S not better than B (b = 14)", "", f"{count('case_G_S_not_better_than_B')}/{n14}"],
            ["H: E better than S (b = 14)", "", f"{count('case_H_E_better_than_S')}/{n14}"],
            ["I: S ≈ E or S better (b = 14)", "", f"{count('case_I_S_approx_or_better_than_E')}/{n14}"]]
    u7 = [r for r in cases if r["subject_id"] == "User07" and r["target"] == "temperature"]
    summ += [["D (User07 temperature): D and E above C", f"{sum(yes(r, 'case_D') for r in u7)}/{len(u7)} budgets", ""],
             ["E (User07 temperature): D below C, E above C", f"{sum(yes(r, 'case_E') for r in u7)}/{len(u7)} budgets",
              ""]]
    out["cases"] = ("**Table P8-9 — Pre-registered interpretation map (plan §8): case counts over subject × target × "
                    "budget cells (b = 1, 3, 7, 14), and at b = 14.**\n\n" + md(["Case", "All budgets", "b = 14"], summ)
                    + "\n\n**Table P8-10 — Cases per cell (X>Y = X better than Y: seed-0 interval of MAE(X) − MAE(Y) "
                    "below zero and lower seed-mean MAE).**\n\n"
                    + md(["Target", "Subject", "b", "Cases", "Other pairwise results"], rows))

    out["headline"] = headline(t, main)

    rows = []
    for tg in TARGETS:
        for name in dict.fromkeys(r["stratum"] for r in heater):
            mean = [r for r in heater if r["stratum"] == name and r["seed"] == "mean" and r["target"] == tg]
            if not mean:
                continue
            g = {(r["budget_nights"], r["metric"]): r for r in mean}
            hb = [r for r in heater_boot if r["stratum"] == name and r["target"] == tg]
            b14 = next((r for r in hb if r["quantity"] == "bias_b14"), None)
            rows.append([tg, name, mean[0]["n_nights"], sgn(g[("0", "bias")]["value"]), sgn(g[("14", "bias")]["value"]),
                         f"{sgn(b14['point_estimate'])} [{sgn(b14['ci_lower'])}, {sgn(b14['ci_upper'])}]" if b14
                         else "descriptive only (< 10 nights)"])
    out["heater"] = ("**Table P8-11 — Reused frozen P6 strata (User02, primary span; no recomputation): bias at b = 0 "
                     "and b = 14 by mat, 22482 quality phase and heater context (seed mean; interval: seed 0, "
                     "night-cluster bootstrap, strata with ≥ 10 nights only).**\n\n"
                     + md(["Target", "Stratum", "Nights", "Bias b = 0", "Bias b = 14", "Bias b = 14 [95 %]"], rows))
    return out


def headline(t: dict[str, list[dict]], main: list[dict]) -> str:
    """Key counts and ranges, computed from the tables (the report prose cites no number of its own)."""
    cells = [(s, tg) for s in SUBJECTS for tg in TARGETS]
    g = lambda s, tg, b, p, k="mae": float(pick(main, subject_id=s, target=tg, budget_nights=b, predictor=p)[k])  # noqa
    rng = lambda xs: f"{min(xs):.2f}–{max(xs):.2f}"  # noqa: E731
    loso = t["loso_summary"]
    a_beats_c = [f"{s} {tg}" for s, tg in cells if g(s, tg, "0", "A") < g(s, tg, "0", "C")]
    a_loso = [f"{s} {tg}" for s, tg in cells
              if float(pick(loso, subject_id=s, target=tg, predictor="A")["mae"])
              < float(pick(loso, subject_id=s, target=tg, predictor="C")["mae"])]
    b_le_e = [(s, tg, b) for s, tg in cells for b in ADAPT if g(s, tg, b, "B") <= g(s, tg, b, "E")]
    best14 = {}
    for s, tg in cells:
        vals = {p: g(s, tg, "14" if p in "BDES" else "0", p) for p in "ABCDES"}
        best14[(s, tg)] = min(vals, key=vals.get)
    lines = [
        f"- Strict LOSO: the training mean had a lower MAE than the RAW-TCN in {len(a_loso)}/6 subject × target cells "
        f"({', '.join(a_loso)}).",
        f"- Strict LOSO: R of the RAW-TCN (seed mean) {rng([float(r['R']) for r in loso if r['predictor'] == 'C'])}; "
        "the training mean has R = 1 by construction.",
        f"- Primary span, no adaptation: the training mean (A) had a lower MAE than the RAW-TCN base (C) in "
        f"{len(a_beats_c)}/6 cells ({', '.join(a_beats_c)}).",
        f"- Primary span: R of the RAW-TCN base (C) {rng([g(s, tg, '0', 'C', 'R') for s, tg in cells])}; of full "
        f"fine-tuning at b = 14 (E) {rng([g(s, tg, '14', 'E', 'R') for s, tg in cells])}; of the scratch control (S) "
        f"{rng([g(s, tg, '14', 'S', 'R') for s, tg in cells])}.",
        f"- Adaptation-target mean (B) seed-mean MAE ≤ full fine-tuning (E): {len(b_le_e)}/24 cells "
        f"({sum(1 for x in b_le_e if x[2] == '14')}/6 at b = 14).",
        "- Lowest seed-mean MAE at b = 14 among A (training mean), B, C (base), D, E and S: "
        + "; ".join(f"{s} {tg}: {NAMES[p]}" for (s, tg), p in best14.items()) + ".",
    ]
    return "**Summary (generated from the tables below).**\n\n" + "\n".join(lines)


def reproduction_block() -> str:
    p = METRICS / "p8_reproduction_check.json"
    if not p.is_file():
        return "Clean rerun not recorded (`scripts/verify_p8_posthoc_reproduction.py` has not been run)."
    rec = json.loads(p.read_text(encoding="utf-8"))
    tables = [c for c in rec["checks"] if "table" in c]
    runs = [c for c in rec["checks"] if "run" in c]
    rows = [[c["table"], c["rows"], f"{c['max_abs_diff']:.3g}", "yes" if c["byte_identical"] else "no",
             "pass" if c["passed"] else "FAIL"] for c in tables]
    rows += [[c["run"].split("init_control/")[-1], "", "", "weights and predictions bitwise" if c.get(
        "weights_identical") and c.get("predictions_bitwise") else "differ", "pass" if c["passed"] else "FAIL"]
             for c in runs]
    return (f"**Clean rerun (fresh control runs and analysis in a separate output root; criterion: tables within "
            f"{rec['criterion']['tables_abs']:g}, control runs bitwise): {'PASS' if rec['passed'] else 'FAIL'}.**\n\n"
            + md(["Item", "Rows", "Max abs diff", "Identical", "Result"], rows))


def main() -> int:
    names =("by_seed", "summary", "not_estimable", "bootstrap", "loso_summary", "interpretation")
    t = {n: read(METRICS / f"p8_{n}.csv") for n in names}
    prov = json.loads((METRICS / "p8_posthoc_provenance.json").read_text(encoding="utf-8"))
    for name, (rows, columns) in paper_tables(t).items():
        write_csv(TABLES / f"{name}.csv", [{c: r.get(c, "") for c in columns} for r in rows], columns)
    write_json(TABLES / "p8_posthoc_provenance.json", paper_provenance(prov))
    heater = read(TABLES / "p6_user02_device_context.csv")
    heater_boot = read(TABLES / "p6_user02_device_context_bootstrap.csv")
    b = blocks(t, heater, heater_boot)
    b["reproduction"] = reproduction_block()
    rep =paths.PROJECT_ROOT / "docs" / "P8_POSTHOC_VALIDATION_REPORT.md"
    text = rep.read_text(encoding="utf-8").replace("\r\n", "\n")
    found = {m.group("name") for m in MARK.finditer(text)}
    if found != set(b):
        raise SystemExit(f"report markers {sorted(found)} != generated blocks {sorted(b)}")
    text = MARK.sub(lambda m: f"<!-- BEGIN GENERATED P8:{m.group('name')} -->\n\n{b[m.group('name')]}\n\n"
                              f"<!-- END GENERATED P8:{m.group('name')} -->", text)
    write_text(rep, text)
    print(f"wrote paper/tables/p8_*.csv, p8_posthoc_provenance.json and {len(b)} generated report blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
