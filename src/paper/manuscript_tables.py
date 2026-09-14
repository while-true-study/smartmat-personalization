"""Manuscript Tables 1-5 and the supplementary table package, built only from frozen cells (P8).

Rules (docs/P8_MANUSCRIPT_PLAN.md §7, docs/P8_TABLE_FIGURE_SELECTION.md):
- Every printed number is a formatted frozen cell. Each table cell records the cells it was built from, so a
  validator can re-resolve it. Nothing is recomputed; the only derived content is a count of subjects in a
  comparison note, whose inputs are listed with it.
- Counts and nights only; no calendar date. Supplementary tables replace calendar night ids with the night
  ordinals of the frozen trajectory table.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from src.data import paths
from src.data.io_guard import remove_file, write_csv, write_json, write_text
from src.paper import sources as S

SUBJECTS = ("User01", "User02", "User07")
TARGETS = ("temperature", "humidity")
UNIT = {"temperature": "°C", "humidity": "%RH"}
TARGET_LABEL = {"temperature": "Temperature (°C)", "humidity": "Humidity (%RH)"}
BUDGETS = ("0", "1", "3", "7", "14")
ADAPT_BUDGETS = ("1", "3", "7", "14")
MEAN_LABEL = "Unweighted mean across three held-out subjects"
SIDE = {"above_zero": "above zero", "below_zero": "below zero", "includes_zero": "includes zero"}
SIDE_SHORT = {"above_zero": "+", "below_zero": "−", "includes_zero": "0"}
GENERATED = paths.PROJECT_ROOT / "paper" / "manuscript" / "generated"
DATE = re.compile(r"(19|20)\d{2}-\d{2}-\d{2}")
NUMBER = re.compile(r"[+−-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|[+−-]?\d+(?:\.\d+)?")


@dataclass
class Cell:
    text: str
    sources: tuple[str, ...] = ()
    values: tuple[str, ...] = ()         # the formatted source values used in `text`
    constants: tuple[str, ...] = ()      # numbers written in the fixed template text (e.g. the "/3" of a count)


@dataclass
class ManuscriptTable:
    number: int
    stem: str
    header: list[str]
    rows: list[list[Cell]]
    notes: list[str] = field(default_factory=list)


def txt(text: str) -> Cell:
    return Cell(text)


def val(table: str, column: str, spec: str, **filters: object) -> Cell:
    v = S.fmt(S.cell(table, column, **filters), spec)
    return Cell(v, (S.source_id(table, column, **filters),), (v,))


def join(template: str, *cells: Cell) -> Cell:
    """Compose cells with fixed text, e.g. join('{} ± {}', mae, sd)."""
    return Cell(template.format(*(c.text for c in cells)), tuple(s for c in cells for s in c.sources),
                tuple(v for c in cells for v in c.values),
                tuple(NUMBER.findall(template.replace("{}", " "))) + tuple(k for c in cells for k in c.constants))


# --- Table 1: cohort, data and protocol --------------------------------------------------------------------------

def _fold_row(subject: str) -> dict[str, str]:
    return S.select("p3_training_mean_by_fold", held_out_subject=subject)


def _primary_counts(subject: str) -> tuple[Cell, Cell]:
    per_budget = {(r["primary_test_nights"], r["primary_test_windows"])
                  for r in S.rows("p5_budget_counts", subject_id=subject)}
    if len(per_budget) != 1:
        raise S.FrozenLookupError(f"{subject}: primary span differs between budgets: {per_budget}")
    return (val("p5_budget_counts", "primary_test_nights", "d", subject_id=subject, budget_nights=0),
            val("p5_budget_counts", "primary_test_windows", ",d", subject_id=subject, budget_nights=0))


def table1() -> ManuscriptTable:
    notes_col = {"User01": "Sensor phases s1/s2 (before/after a sensor replacement): window boundary and reporting "
                           "stratum, never an input",
                 "User02": "One subject: two concurrent mats, kept as separate streams in the same partition",
                 "User07": "—"}
    out = []
    for s in SUBJECTS:
        others = [o for o in SUBJECTS if o != s]
        if s == "User02":
            streams = txt("2 (mats 22480, 22482)")
            sessions = join("{} / {}", val("canonical_v1_summary", "sessions", "d", dataset_file="primary",
                                           subject_id=s, device_id="22480"),
                            val("canonical_v1_summary", "sessions", "d", dataset_file="primary", subject_id=s,
                                device_id="22482"))
        else:
            streams = txt("1 (mat ID not recorded)")
            sessions = val("canonical_v1_summary", "sessions", "d", dataset_file="primary", subject_id=s,
                           device_id="unknown")
        nights, windows = _primary_counts(s)
        out.append([txt(s), streams, sessions,
                    join("fold {}; training subject in folds {} and {}",
                         *[val("p3_training_mean_by_fold", "fold", "d", held_out_subject=x) for x in (s, *others)]),
                    val("p3_training_mean_by_fold", "test_n_windows", ",d", held_out_subject=s),
                    nights, windows, txt(notes_col[s])])
    return ManuscriptTable(
        1, "table1_dataset_protocol",
        ["Subject", "Mat streams", "Recording sessions", "Held out in", "Labelled 40-s windows",
         "Primary test nights (≥ 16)", "Primary test windows", "Notes"],
        out,
        ["Three subjects and four mat streams. User02's two mats belong to one subject and are never counted as two "
         "subjects. Sessions for User02 are given per mat (22480 / 22482).",
         "Labelled windows: all labelled windows of the subject, i.e. its test set when it is held out in strict "
         "leave-one-subject-out evaluation.",
         "Chronological personalization: adaptation budgets b = 0, 1, 3, 7 and 14 nights (the earliest nights); "
         "night b + 1 is an unused buffer; the primary test span (nights ≥ 16) is identical for every b.",
         "Counts only. Nights are counted, never dated."])


# --- Table 2: strict LOSO -------------------------------------------------------------------------------------------

def table2() -> ManuscriptTable:
    model_label = {"training_mean": "Training-mean predictor", "tcn_raw": "RAW-TCN"}
    metric_label = {"mae": "MAE", "rmse": "RMSE", "bias": "Bias"}
    body = []
    for t in TARGETS:
        for m in ("mae", "rmse", "bias"):
            for model in ("training_mean", "tcn_raw"):
                spec = "+.2f" if m == "bias" else ".2f"
                f = dict(model=model, target=t, metric=m)
                body.append([txt(TARGET_LABEL[t]), txt(metric_label[m]), txt(model_label[model]),
                             *[val("p3_primary_summary", c, spec, **f)
                               for c in (*SUBJECTS, "unweighted_subject_mean")]])
    worse = {}
    for t in TARGETS:
        tm = S.select("p3_primary_summary", model="training_mean", target=t, metric="mae")
        tcn = S.select("p3_primary_summary", model="tcn_raw", target=t, metric="mae")
        worse[t] = [s for s in SUBJECTS if float(tcn[s]) > float(tm[s])]
    return ManuscriptTable(
        2, "table2_strict_loso",
        ["Target", "Metric", "Predictor", "User01", "User02", "User07", MEAN_LABEL],
        body,
        [f"RAW-TCN MAE higher than the training-mean MAE: temperature in {len(worse['temperature'])} of 3 subjects; "
         f"humidity in {len(worse['humidity'])} of 3 ({', '.join(worse['humidity']) or 'none'}). Comparison of the "
         "MAE rows above.",
         "Each subject column is one outer fold, evaluated once on all labelled windows of the held-out subject "
         "(both User02 mats pooled). RAW-TCN values are means over model seeds 0, 1 and 2 (per seed: Table S1).",
         "Bias = mean of (predicted − observed); negative values mean under-estimation.",
         "The unweighted mean across three held-out subjects is descriptive, not a population estimate."])


# --- Table 3: feature families (secondary) ---------------------------------------------------------------------------

FAMILIES = ("training_mean", "RAW", "MOVEMENT", "CONTACT", "RAW+MOVEMENT", "RAW+CONTACT", "RAW+MOVEMENT+CONTACT")


def _delta(family: str, target: str) -> Cell:
    if family in ("training_mean", "RAW"):
        return txt("—")
    f = dict(family=family, target=target, metric="mae")
    return join("{} ({}/3)", val("p4_vs_raw", "delta_unweighted_mean", "+.2f", **f),
                val("p4_vs_raw", "improved_subjects", "d", **f))


def table3() -> ManuscriptTable:
    label = {"training_mean": "Training-mean predictor", "RAW": "RAW (reference)"}
    body = []
    for fam in FAMILIES:
        row = [txt(label.get(fam, fam))]
        for t in TARGETS:
            row += [val("p4_primary_summary", "unweighted_subject_mean", ".2f", model=fam, target=t, metric="mae"),
                    _delta(fam, t)]
        row += [val("p4_primary_summary", "User02", "+.2f", model=fam, target=t, metric="bias") for t in TARGETS]
        body.append(row)
    return ManuscriptTable(
        3, "table3_feature_family",
        ["Representation", "Temperature MAE (°C)", "Δ vs RAW, °C (improved)", "Humidity MAE (%RH)",
         "Δ vs RAW, %RH (improved)", "User02 bias, °C", "User02 bias, %RH"],
        body,
        ["Secondary analysis (RQ3).",
         "MAE: unweighted mean across three held-out subjects of the seed means (seeds 0, 1, 2); descriptive.",
         "Δ vs RAW = family MAE − RAW MAE (negative = lower error); in brackets the number of subjects, of three, "
         "whose MAE improved.",
         "Each representation has its own pre-declared nested selection; the comparison is between selected "
         "representations, not a fixed-model ablation.",
         "User02 bias (predicted − observed) shows the domain-level offset that remains in every representation.",
         "Per-subject values, RMSE and all pre-declared comparisons: Tables S4–S7."])


# --- Table 4: chronological personalization --------------------------------------------------------------------------

def _mae(subject: str, target: str, b: str) -> Cell:
    f = dict(subject_id=subject, target=target, budget_nights=b)
    mean = val("p5_primary_mae", "seed_mean", ".2f", **f)
    if S.cell("p5_primary_mae", "seed_sd", **f) == "":
        return mean
    return join("{} ± {}", mean, val("p5_primary_mae", "seed_sd", ".2f", **f))


def _gain(subject: str, target: str, b: str) -> Cell:
    if b == "0":
        return txt("—")
    f = dict(subject_id=subject, target=target, budget_nights=b)
    return join("{} ({}/3)", val("p5_adaptation_gain", "G_pct", "+.1f", **f),
                val("p5_adaptation_gain", "seeds_improved", "d", **f))


def table4() -> ManuscriptTable:
    body = []
    for t in TARGETS:
        for s in SUBJECTS:
            body.append([txt(TARGET_LABEL[t]), txt(s), txt("MAE"), *[_mae(s, t, b) for b in BUDGETS]])
            body.append([txt(TARGET_LABEL[t]), txt(s), txt("G_b, % (seeds improved)"),
                         *[_gain(s, t, b) for b in BUDGETS]])
        body.append([txt(TARGET_LABEL[t]), txt(MEAN_LABEL), txt("MAE"),
                     *[_mae("unweighted_mean", t, b) for b in BUDGETS]])
    return ManuscriptTable(
        4, "table4_personalization",
        ["Target", "Subject", "Quantity", "b = 0", "b = 1", "b = 3", "b = 7", "b = 14"],
        body,
        ["Primary test span: nights ≥ 16, identical for every budget b; b = 0 is the base model on this span (it "
         "differs from Table 2, which covers all nights).",
         "MAE: mean ± standard deviation over model seeds 0, 1 and 2.",
         "G_b = (MAE_0 − MAE_b) / MAE_0 × 100 %, from the seed-mean MAE; G_b > 0 is an improvement and G_b < 0 is "
         "negative transfer (the adapted model is worse than its own base model on the same nights). In brackets: "
         "seeds, of three, with G_b > 0.",
         "The unweighted mean across three held-out subjects is descriptive, not a population estimate. Bias and RMSE "
         "by budget: Table S10."])


# --- Table 5: night-level robustness --------------------------------------------------------------------------------

def table5() -> ManuscriptTable:
    body = []
    for s in SUBJECTS:
        for t in TARGETS:
            for b in ADAPT_BUDGETS:
                f = dict(subject_id=s, target=t, budget_nights=b)
                r0 = S.select("p6_bootstrap_mae", **f)
                sides = [S.select("p6_bootstrap_seed_sensitivity", metric="mae", seed=k, **f)["interval"]
                         for k in ("1", "2")]
                body.append([
                    txt(s), txt(TARGET_LABEL[t]), txt(b),
                    val("p6_bootstrap_mae", "point_estimate", "+.2f", **f),
                    join("[{}, {}]", val("p6_bootstrap_mae", "ci_lower", "+.2f", **f),
                         val("p6_bootstrap_mae", "ci_upper", "+.2f", **f)),
                    Cell(SIDE[r0["interval"]], (S.source_id("p6_bootstrap_mae", "interval", **f),)),
                    Cell(" / ".join(SIDE_SHORT[x] for x in sides),
                         tuple(S.source_id("p6_bootstrap_seed_sensitivity", "interval", metric="mae", seed=k, **f)
                               for k in ("1", "2")), (), ("0",))])       # "0" is the includes-zero symbol
    return ManuscriptTable(
        5, "table5_night_robustness",
        ["Subject", "Target", "b", "ΔMAE", "95 % interval", "Seed 0 interval", "Seeds 1 / 2"],
        body,
        ["ΔMAE = MAE(base) − MAE(adapted) on the primary test span (nights ≥ 16); ΔMAE > 0 means improvement, "
         "ΔMAE < 0 negative transfer. Units as in the Target column.",
         "Seed 0 (primary model seed): full-sample point estimate and 95 % percentile interval from 2,000 paired "
         "night-cluster bootstrap resamples of the test nights.",
         "Seeds 1 / 2: side of zero of their intervals (sensitivity, never pooled): + above zero, − below zero, "
         "0 includes zero.",
         "All 24 subject × target × budget cells are shown. The intervals describe within-subject night-level "
         "uncertainty; an interval that excludes zero is not population-level statistical significance."])


MAIN_TABLES = (table1, table2, table3, table4, table5)


# --- rendering ------------------------------------------------------------------------------------------------------

def _md_escape(text: str) -> str:
    return text.replace("|", "\\|")


def to_markdown(t: ManuscriptTable) -> str:
    lines = ["| " + " | ".join(_md_escape(h) for h in t.header) + " |", "|" + "---|" * len(t.header)]
    lines += ["| " + " | ".join(_md_escape(c.text) for c in r) + " |" for r in t.rows]
    if t.notes:
        lines += ["", "Notes:", ""] + [f"- {n}" for n in t.notes]
    return "\n".join(lines) + "\n"


def csv_rows(t: ManuscriptTable) -> list[dict[str, str]]:
    return [dict(zip(t.header, (c.text for c in r))) for r in t.rows]


def provenance(t: ManuscriptTable) -> list[dict]:
    return [{"table": t.number, "row": i, "column": t.header[j], "text": c.text, "sources": list(c.sources),
             "values": list(c.values)}
            for i, r in enumerate(t.rows) for j, c in enumerate(r) if c.sources]


def check_traceable(t: ManuscriptTable) -> list[str]:
    """Every number printed in a cell must be one of the formatted frozen values it declares."""
    problems = []
    for i, r in enumerate(t.rows):
        for j, c in enumerate(r):
            if not c.sources:
                continue
            printed = NUMBER.findall(c.text)
            declared = {v.lstrip("+") for v in (*c.values, *c.constants)}
            for num in printed:
                if num.lstrip("+") not in declared:
                    problems.append(f"Table {t.number} row {i} col {t.header[j]!r}: {num!r} not in {sorted(declared)}")
    return problems


# --- supplementary tables -------------------------------------------------------------------------------------------

SUPPLEMENT: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("S1", "Strict LOSO per seed and training-mean predictor per fold", ("p3_tcn_outer_by_seed",
                                                                         "p3_training_mean_by_fold")),
    ("S2", "Strict LOSO device and phase strata", ("p3_secondary_strata",)),
    ("S3", "Selected configurations and inner-selection score ranges (selection records)",
     ("p3_selected_configs", "p4_selected_configs", "p4_inner_score_range")),
    ("S4", "Feature families per seed", ("p4_outer_by_seed",)),
    ("S5", "Feature families versus the training-mean predictor", ("p4_vs_training_mean",)),
    ("S6", "Feature families: per-subject summary, versus RAW and the pre-declared comparisons A-E",
     ("p4_vs_raw", "p4_incremental_effects", "p4_seed_consistency", "p4_primary_summary")),
    ("S7", "Bias and offset by feature family", ("p4_bias_offset",)),
    ("S8", "Feature-family device and phase strata", ("p4_secondary_strata",)),
    ("S9", "Adaptation gain and error decomposition", ("p5_adaptation_gain",)),
    ("S10", "Personalization RMSE and bias by budget", ("p5_primary_rmse", "p5_primary_bias")),
    ("S11", "Personalization on the per-budget later span (secondary)", ("p5_later_span_mae",)),
    ("S12", "Personalization per seed", ("p5_by_seed",)),
    ("S13", "Budgets, nights and windows (night ordinals)", ("p5_budget_counts",)),
    ("S14", "User02 mat strata and User01 sensor-phase strata", ("p5_user02_device_strata",
                                                                  "p5_user01_sensor_phase")),
    ("S15", "Temporal level mismatch (post hoc, descriptive)",
     ("p5_level_diagnostic", "p6_level_mismatch_consistency", "p6_level_mismatch_spans",
      "p6_level_mismatch_trajectory")),
    ("S16", "Night-level bootstrap of RMSE and bias, and seed sensitivity",
     ("p6_bootstrap_rmse", "p6_bootstrap_bias", "p6_bootstrap_seed_sensitivity")),
    ("S17", "Start-span sensitivity (post hoc)", ("p6_drift_sensitivity",)),
    ("S18", "User02 device, quality-phase and heater-context strata", ("p6_user02_device_context",
                                                                        "p6_user02_device_context_bootstrap")),
)
FIGURE_DATA = ("p5_figure_data", "p6_figure_data")
NOT_IN_SUPPLEMENT = {"p5_per_night": "night-level predictions summary with calendar night ids; distributed through "
                                     "the release candidate with relative night keys instead",
                     "p3_primary_summary": "main Table 2",
                     "p5_primary_mae": "main Table 4", "p6_bootstrap_mae": "main Table 5"}
DATE_COLUMNS = {"p5_budget_counts": {"adaptation_first": "adaptation_first_night",
                                     "adaptation_last": "adaptation_last_night",
                                     "buffer_nights": "buffer_night"},
                "p6_level_mismatch_trajectory": {"night_id": None}}


def night_ordinals() -> dict[tuple[str, str], str]:
    """(subject, calendar night id) -> night ordinal, from the frozen trajectory table."""
    out: dict[tuple[str, str], str] = {}
    for r in S.table("p6_level_mismatch_trajectory"):
        key = (r["subject_id"], r["night_id"])
        if out.setdefault(key, r["night_ordinal"]) != r["night_ordinal"]:
            raise S.FrozenLookupError(f"inconsistent ordinal for {key}")
    return out


def public_rows(name: str) -> tuple[list[str], list[dict[str, str]]]:
    """A frozen table with calendar night ids replaced by night ordinals (or dropped)."""
    src = S.table(name)
    columns = list(src[0].keys())
    mapping = DATE_COLUMNS.get(name, {})
    ordinals = night_ordinals() if mapping else {}
    new_columns = [mapping.get(c, c) for c in columns if not (c in mapping and mapping[c] is None)]
    out = []
    for r in src:
        row = {}
        for c in columns:
            if c in mapping:
                if mapping[c] is None:
                    continue
                v = r[c]
                row[mapping[c]] = ordinals[(r["subject_id"], v)] if v else ""
            else:
                row[c] = r[c]
        out.append(row)
    if name == "p5_budget_counts":                    # consistency of the conversion with the protocol
        for r in out:
            b = int(r["budget_nights"])
            if b and (int(r["adaptation_first_night"]) != 1 or int(r["adaptation_last_night"]) != b
                      or int(r["buffer_night"]) != b + 1):
                raise S.FrozenLookupError(f"night ordinals do not match budget {b}: {r}")
    for r in out:
        for v in r.values():
            if DATE.search(v):
                raise S.FrozenLookupError(f"{name}: calendar date left in a supplementary table")
    return new_columns, out


def p7_reproduction_record() -> str:
    """Table S19: sections 6 and 8-10 of the frozen P7 report, copied verbatim."""
    text = (paths.PROJECT_ROOT / "docs" / "P7_REPRODUCIBILITY_PUBLIC_RELEASE_REPORT.md").read_text(
        encoding="utf-8").replace("\r\n", "\n")
    parts = []
    for start, stop in (("## 6. ", "## 7. "), ("## 8. ", "## 11. ")):
        i, j = text.index(start), text.index(stop)
        parts.append(text[i:j].rstrip())
    body = "\n\n".join(parts)
    body = re.sub(r"^## ", "### ", body, flags=re.M)
    if DATE.search(body):
        raise S.FrozenLookupError("calendar date in the P7 reproduction record")
    return ("# Table S19. Reproduction record\n\n"
            "Verbatim copy of sections 6 and 8–10 of the P7 reproducibility report "
            "(`docs/P7_REPRODUCIBILITY_PUBLIC_RELEASE_REPORT.md`): release manifest and checksums, core and extended "
            "reproduction, and clean-checkout results. Commit identifiers refer to the version-controlled research "
            "repository.\n\n" + body + "\n")


def supplementary_index() -> str:
    lines = ["# Supplementary tables", "",
             "Machine-readable copies of the frozen result tables (full precision). Calendar night ids are replaced "
             "by night ordinals (Table S13) or removed where the ordinal is already present (Table S15). Generated by "
             "`scripts/export_manuscript_tables.py`; do not edit by hand.", "",
             "| Table | Content | Files |", "|---|---|---|"]
    for sid, title, names in SUPPLEMENT:
        files = ", ".join(f"`{supp_file(sid, n, k, len(names))}`" for k, n in enumerate(names))
        lines.append(f"| {sid} | {title} | {files} |")
    lines.append("| S19 | Reproduction record (P7 report §6, §8–§10) | `TableS19_reproduction_record.md` |")
    lines += ["", "Figure source data: " + ", ".join(f"`FigureData_{n}.csv`" for n in FIGURE_DATA) + ".", "",
              "Not included: " + "; ".join(f"`{k}` ({v})" for k, v in NOT_IN_SUPPLEMENT.items()) + "."]
    return "\n".join(lines) + "\n"


def supp_file(sid: str, name: str, k: int, n: int) -> str:
    suffix = "abcdefgh"[k] if n > 1 else ""
    return f"Table{sid[0]}{int(sid[1:]):02d}{suffix}_{name}.csv"


# --- export ---------------------------------------------------------------------------------------------------------

def build_main() -> list[ManuscriptTable]:
    return [f() for f in MAIN_TABLES]


def export(out_dir: Path = GENERATED) -> dict[str, int]:
    """Write Tables 1-5 and the supplementary package; files from an earlier export that are no longer produced are
    removed, so the directories always equal the current build."""
    before = {p for sub in ("tables", "supplementary") if (out_dir / sub).is_dir()
              for p in (out_dir / sub).iterdir() if p.is_file()}
    tables = build_main()
    problems = [p for t in tables for p in check_traceable(t)]
    if problems:
        raise S.FrozenLookupError("untraceable table values:\n" + "\n".join(problems))
    prov = []
    for t in tables:
        write_text(out_dir / "tables" / f"{t.stem}.md", to_markdown(t))
        write_csv(out_dir / "tables" / f"{t.stem}.csv", csv_rows(t), t.header)
        prov += provenance(t)
    write_json(out_dir / "tables" / "provenance.json", prov)
    n_supp = 0
    for sid, _, names in SUPPLEMENT:
        for k, name in enumerate(names):
            cols, rws = public_rows(name)
            write_csv(out_dir / "supplementary" / supp_file(sid, name, k, len(names)), rws, cols)
            n_supp += 1
    for name in FIGURE_DATA:
        cols, rws = public_rows(name)
        write_csv(out_dir / "supplementary" / f"FigureData_{name}.csv", rws, cols)
    write_text(out_dir / "supplementary" / "TableS19_reproduction_record.md", p7_reproduction_record())
    write_text(out_dir / "supplementary" / "README.md", supplementary_index())
    written = {p for sub in ("tables", "supplementary") for p in (out_dir / sub).iterdir() if p.is_file()}
    expected = {out_dir / "tables" / f"{t.stem}{x}" for t in tables for x in (".md", ".csv")}
    expected |= {out_dir / "tables" / "provenance.json", out_dir / "supplementary" / "README.md",
                 out_dir / "supplementary" / "TableS19_reproduction_record.md"}
    expected |= {out_dir / "supplementary" / supp_file(sid, n, k, len(ns)) for sid, _, ns in SUPPLEMENT
                 for k, n in enumerate(ns)}
    expected |= {out_dir / "supplementary" / f"FigureData_{n}.csv" for n in FIGURE_DATA}
    for stale in (before | written) - expected:
        remove_file(stale)
    return {"main_tables": len(tables), "traced_cells": len(prov), "supplementary_csv": n_supp,
            "figure_data_csv": len(FIGURE_DATA)}
