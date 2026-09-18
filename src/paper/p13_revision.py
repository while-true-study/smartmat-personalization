"""P13 manuscript revision: paper-facing tables for the common-pool retraining (P11) and the heater diagnostic (P12).

Nothing is recomputed. Every exported number is a cell of a committed result table (CONVENTIONS §5):
- outputs/p11_common_pool_tcn/*.csv (scripts/run_p11_common_pool_tcn.py; D-066)
- outputs/p12_heater_diagnostic/*.csv (scripts/run_p12_heater_diagnostic.py; D-067)
- paper/tables/p10_*.csv (scripts/export_p10_tables.py; D-064)
The export writes
- paper/tables/p11_*.csv and paper/tables/p12_*.csv: row-for-row copies (source tokens of the P13 manuscript source);
- paper/tables/p13_table10_common_endpoints.csv, p13_table11_heater.csv, p13_summary_values.csv: selections of those
  cells for the reworked Table 10, the new Table 11 and a few values quoted in the text (with the only arithmetic being
  a difference or a minimum/maximum of committed cells, recorded in the `derivation` column);
- paper/manuscript/revision_p13/supplementary/: Tables S35-S44 (no calendar date) and their index;
- paper/tables/p13_export_provenance.json: SHA-256 of every source file.
Before writing, the cells shared between P10, P11 and P12 are compared (tolerance 1e-9); any disagreement stops the
export. The P11/P12 output directories are only read.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
from pathlib import Path

from src.data import paths
from src.data.io_guard import read_bytes, write_csv, write_json, write_text

ROOT = paths.PROJECT_ROOT
P11_DIR = ROOT / "outputs" / "p11_common_pool_tcn"
P12_DIR = ROOT / "outputs" / "p12_heater_diagnostic"
TABLES = ROOT / "paper" / "tables"
REVISION = ROOT / "paper" / "manuscript" / "revision_p13"
SUPPLEMENTARY = REVISION / "supplementary"
SUBJECTS = ("User01", "User02", "User07")
TARGETS = ("temperature", "humidity")
TOLERANCE = 1e-9
DATE = re.compile(r"(19|20)\d{2}-\d{2}-\d{2}")

# paper/tables name -> committed result file (copied row for row)
COPIES = {
    "p11_common_pool_tcn_seed_mean": P11_DIR / "common_pool_tcn_seed_mean.csv",
    "p11_common_pool_tcn_per_seed": P11_DIR / "common_pool_tcn_per_seed.csv",
    "p11_common_pool_model_comparison": P11_DIR / "common_pool_model_comparison.csv",
    "p11_common_pool_bootstrap": P11_DIR / "common_pool_bootstrap.csv",
    "p11_common_pool_interpretation": P11_DIR / "common_pool_interpretation.csv",
    "p11_common_pool_counts": P11_DIR / "common_pool_counts.csv",
    "p11_common_pool_epoch_selection": P11_DIR / "common_pool_epoch_selection.csv",
    "p12_heater_code_audit": P12_DIR / "heater_code_audit.csv",
    "p12_heater_context_counts": P12_DIR / "heater_context_counts.csv",
    "p12_heater_target_summary": P12_DIR / "heater_target_summary.csv",
    "p12_heater_eta_squared": P12_DIR / "heater_eta_squared.csv",
    "p12_heater_constant_metrics_full": P12_DIR / "heater_constant_metrics_full.csv",
    "p12_heater_constant_metrics_common": P12_DIR / "heater_constant_metrics_common.csv",
    "p12_heater_bootstrap_full": P12_DIR / "heater_bootstrap_full.csv",
    "p12_heater_bootstrap_common": P12_DIR / "heater_bootstrap_common.csv",
    "p12_heater_predictions_metadata": P12_DIR / "heater_predictions_metadata.csv",
    "p12_heater_interpretation": P12_DIR / "heater_interpretation.csv",
    "p12_heater_history_gain_by_context": P12_DIR / "heater_history_gain_by_context.csv",
}
P10_USED = ("p10_history_metrics", "p10_history_bootstrap")

# Supplementary tables S35-S44: (id, title, [(file stem, paper/tables name)])
SUPPLEMENT = (
    ("S35", "Median constants, strict leave-one-subject-out and primary span (exploratory)",
     [("TableS35a_p10_loso_constants", "p10_loso_constants"), ("TableS35b_p10_loso_metrics", "p10_loso_metrics"),
      ("TableS35c_p10_rq2_constants", "p10_rq2_constants"), ("TableS35d_p10_rq2_summary", "p10_rq2_summary")]),
    ("S36", "Point-estimate counts of constants versus networks (exploratory)",
     [("TableS36_p10_point_counts", "p10_point_counts")]),
    ("S37", "Endpoint availability by history (exploratory)",
     [("TableS37_p10_history_availability", "p10_history_availability")]),
    ("S38", "Pressure-summary models on the common endpoints: all histories, ridge regression, bias, R and "
            "correlations, night-level intervals, selections and the pre-specified reading; the RAW-TCN trained on "
            "all 40-s windows as a training-pool sensitivity reference (exploratory)",
     [("TableS38a_p10_history_metrics", "p10_history_metrics"),
      ("TableS38b_p10_history_bootstrap", "p10_history_bootstrap"),
      ("TableS38c_p10_history_interpretation", "p10_history_interpretation"),
      ("TableS38d_p10_history_selection", "p10_history_selection"),
      ("TableS38e_p11_model_comparison_training_pools", "p11_common_pool_model_comparison")]),
    ("S39", "RAW-TCN retrained on the common endpoints: per seed and seed mean, epoch selection and pool counts "
            "(exploratory)",
     [("TableS39a_p11_tcn_per_seed", "p11_common_pool_tcn_per_seed"),
      ("TableS39b_p11_tcn_seed_mean", "p11_common_pool_tcn_seed_mean"),
      ("TableS39c_p11_epoch_selection", "p11_common_pool_epoch_selection"),
      ("TableS39d_p11_pool_counts", "p11_common_pool_counts")]),
    ("S40", "RAW-TCN retrained on the common endpoints: night-level paired bootstrap against the constants, the "
            "boosted models and the network trained on all 40-s windows, and the pre-specified reading "
            "(exploratory)",
     [("TableS40a_p11_bootstrap", "p11_common_pool_bootstrap"),
      ("TableS40b_p11_interpretation", "p11_common_pool_interpretation")]),
    ("S41", "Heater-context diagnostic: control-code audit and heater-context coverage by state, span and mat "
            "(post hoc, descriptive)",
     [("TableS41a_p12_code_audit", "p12_heater_code_audit"),
      ("TableS41b_p12_context_counts", "p12_heater_context_counts")]),
    ("S42", "Heater-context diagnostic: target level by heater context (post hoc, descriptive)",
     [("TableS42_p12_target_summary", "p12_heater_target_summary")]),
    ("S43", "Heater-context diagnostic: eta squared for both targets, raw, night-centred and night × mat-centred, "
            "three states and on/off only, both spans, with night-level intervals (post hoc, descriptive)",
     [("TableS43_p12_eta_squared", "p12_heater_eta_squared")]),
    ("S44", "Heater-context diagnostic: heater-conditioned source constant on both spans, night-level paired "
            "bootstrap, source composition, pre-specified reading, and errors of the constants and pressure models "
            "by heater context (post hoc, descriptive)",
     [("TableS44a_p12_constant_metrics_full", "p12_heater_constant_metrics_full"),
      ("TableS44b_p12_constant_metrics_common", "p12_heater_constant_metrics_common"),
      ("TableS44c_p12_bootstrap_full", "p12_heater_bootstrap_full"),
      ("TableS44d_p12_bootstrap_common", "p12_heater_bootstrap_common"),
      ("TableS44e_p12_source_composition", "p12_heater_predictions_metadata"),
      ("TableS44f_p12_interpretation", "p12_heater_interpretation"),
      ("TableS44g_p12_errors_by_context", "p12_heater_history_gain_by_context")]),
)


class P13ExportError(RuntimeError):
    pass


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise P13ExportError(f"source table missing: {path.relative_to(ROOT).as_posix()}")
    with open(path, encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        rows = list(rd)
        return list(rd.fieldnames or []), rows


def sha256(path: Path) -> str:
    return hashlib.sha256(read_bytes(path)).hexdigest()


def one(rows: list[dict], **kw) -> dict:
    hit = [r for r in rows if all(r.get(k) == str(v) for k, v in kw.items())]
    if len(hit) != 1:
        raise P13ExportError(f"expected one row for {kw}, found {len(hit)}")
    return hit[0]


def same(a: str, b: str, what: str) -> None:
    if not math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=TOLERANCE):
        raise P13ExportError(f"{what}: {a} != {b}")


# ------------------------------------------------------------------------------------------------ derived tables

def cross_check(t: dict[str, list[dict]]) -> int:
    """Cells that P10, P11 and P12 share must agree; returns the number of comparisons."""
    n = 0
    cmp_, hm = t["p11_common_pool_model_comparison"], t["p10_history_metrics"]
    for s in SUBJECTS:
        for tg in TARGETS:
            c = lambda m: one(cmp_, subject=s, target=tg, model=m)  # noqa: E731
            h = lambda **kw: one(hm, subject_id=s, target=tg, **kw)  # noqa: E731
            pairs = [(c("mean_common")["MAE"], h(predictor="training_mean_common", history_s="", seed="")["mae"]),
                     (c("median_common")["MAE"], h(predictor="training_median_common", history_s="", seed="")["mae"]),
                     (c("tcn_full_40s_seed_mean")["MAE"], h(predictor="raw_tcn", history_s="40", seed="mean")["mae"]),
                     (c("tcn_common_40s_seed_mean")["MAE"],
                      one(t["p11_common_pool_tcn_seed_mean"], subject=s, target=tg)["MAE"]),
                     (c("mean_common")["MAE"], one(t["p12_heater_constant_metrics_common"], subject_id=s, target=tg,
                                                   predictor="source_mean")["mae"]),
                     (c("median_common")["MAE"], one(t["p12_heater_constant_metrics_common"], subject_id=s,
                                                     target=tg, predictor="source_median")["mae"])]
            for hist in ("40", "300", "900"):
                pairs.append((c(f"hgb_{hist}s")["MAE"], h(predictor="hgb", history_s=hist, seed="")["mae"]))
            for a, b in pairs:
                same(a, b, f"{s} {tg}")
                n += 1
            if c("mean_common")["n_windows"] != h(predictor="training_mean_common", history_s="", seed="")["n_windows"]:
                raise P13ExportError(f"{s} {tg}: common endpoint counts differ between P10 and P11")
            n += 1
    return n


def _interval(rows: list[dict], **kw) -> str:
    return one(rows, **kw)["interval"]


def table10(t: dict[str, list[dict]]) -> list[dict]:
    cmp_, boot11, boot10 = (t["p11_common_pool_model_comparison"], t["p11_common_pool_bootstrap"],
                            t["p10_history_bootstrap"])
    out = []
    for tg in TARGETS:
        for s in SUBJECTS:
            c = lambda m: one(cmp_, subject=s, target=tg, model=m)  # noqa: E731
            mark = lambda iv: "†" if iv == "above_zero" else ""  # noqa: E731
            tcn = c("tcn_common_40s_seed_mean")
            rec = {"subject_id": s, "target": tg, "n_windows": c("mean_common")["n_windows"],
                   "n_nights": c("mean_common")["n_nights"],
                   "mae_source_mean": c("mean_common")["MAE"], "mae_source_median": c("median_common")["MAE"],
                   "mae_tcn_common": tcn["MAE"], "mae_tcn_common_seed_min": tcn["MAE_seed_min"],
                   "mae_tcn_common_seed_max": tcn["MAE_seed_max"],
                   "mae_hgb_40": c("hgb_40s")["MAE"], "mae_hgb_300": c("hgb_300s")["MAE"],
                   "mae_hgb_900": c("hgb_900s")["MAE"], "mae_tcn_full": c("tcn_full_40s_seed_mean")["MAE"],
                   "mark_tcn_common": mark(_interval(boot11, subject_id=s, target=tg, first="training_mean_common",
                                                     second="raw_tcn_common_seed0")),
                   **{f"mark_hgb_{h}": mark(_interval(boot10, subject_id=s, target=tg, first="training_mean_common",
                                                      second=f"hgb_h{h}")) for h in ("40", "300", "900")},
                   "tcn_common_minus_hgb_40": repr(float(tcn["MAE"]) - float(c("hgb_40s")["MAE"]))}
            out.append(rec)
    return out


def table11(t: dict[str, list[dict]]) -> list[dict]:
    eta, cnt, met, boot = (t["p12_heater_eta_squared"], t["p12_heater_context_counts"],
                           t["p12_heater_constant_metrics_common"], t["p12_heater_bootstrap_common"])
    cmp_ = t["p11_common_pool_model_comparison"]
    out = []
    for s in SUBJECTS:
        e = lambda v: one(eta, span="full", subject_id=s, target="temperature", variant=v,  # noqa: E731
                          scope="three_states")["eta_squared"]
        on = one(cnt, span="full", subject_id=s, mat="all", state="ON")
        m = lambda p: one(met, subject_id=s, target="temperature", predictor=p)["mae"]  # noqa: E731
        b = one(boot, subject_id=s, target="temperature", first="source_mean",
                second="heater_conditioned_source_mean")
        out.append({"subject_id": s, "on_windows_full": on["windows"], "on_nights_full": on["nights_with_state"],
                    "on_share_pct_full": repr(100.0 * float(on["share_of_windows"])),
                    "eta_raw_full": e("A1_raw"), "eta_night_centred_full": e("A2_night_centred"),
                    "eta_night_x_mat_centred_full": e("A3_night_x_mat_centred") if s == "User02" else "",
                    "mae_source_mean_common": m("source_mean"), "mae_source_median_common": m("source_median"),
                    "mae_heater_conditioned_common": m("heater_conditioned_source_mean"),
                    "delta_mae": b["point_estimate"], "ci_lower": b["ci_lower"], "ci_upper": b["ci_upper"],
                    "interval": b["interval"],
                    "mae_hgb_900_common": one(cmp_, subject=s, target="temperature", model="hgb_900s")["MAE"]})
    return out


def summary_values(t: dict[str, list[dict]], t10: list[dict]) -> list[dict]:
    """Values quoted in the text that are a minimum, maximum or difference of committed cells."""
    rows = []

    def add(key, value, derivation):
        rows.append({"key": key, "value": repr(float(value)), "derivation": derivation})

    temp = [r for r in t10 if r["target"] == "temperature"]
    diffs = [abs(float(r["tcn_common_minus_hgb_40"])) for r in temp]
    add("tcn_common_vs_hgb_40_temperature_absdiff_min", min(diffs),
        "min over subjects of |MAE(RAW-TCN common, seed mean) - MAE(HGB 40 s)|, temperature")
    add("tcn_common_vs_hgb_40_temperature_absdiff_max", max(diffs),
        "max over subjects of |MAE(RAW-TCN common, seed mean) - MAE(HGB 40 s)|, temperature")
    eta = t["p12_heater_eta_squared"]
    hum = [float(r["eta_squared"]) for r in eta if r["target"] == "humidity" and r["scope"] == "three_states"
           and r["span"] == "full"]
    add("eta_humidity_full_three_states_max", max(hum),
        "max over subjects and centring variants of eta squared, humidity, full span, three states")
    ts = t["p12_heater_target_summary"]
    for s in ("User01", "User07"):
        on = one(ts, span="full", subject_id=s, target="temperature", state="ON")
        other = [r for r in ts if r["span"] == "full" and r["subject_id"] == s and r["target"] == "temperature"
                 and r["state"] != "ON"]
        w = sum(int(r["windows"]) for r in other)
        mean_other = sum(int(r["windows"]) * float(r["mean"]) for r in other) / w
        add(f"{s}_temperature_on_minus_other_mean_full", float(on["mean"]) - mean_other,
            "mean temperature of ON windows minus the window-weighted mean of OFF and UNKNOWN windows, full span")
    return rows


# ------------------------------------------------------------------------------------------------ supplementary

def supplementary_index() -> str:
    lines = ["# Supplementary tables S35–S44 (P13 revision)", "",
             "Machine-readable copies of the committed exploratory and post-hoc result tables (full precision). "
             "No calendar date is included. Generated by `scripts/export_p13_tables.py`; do not edit by hand. "
             "Tables S1–S34 are unchanged (`paper/manuscript/generated/supplementary/`).", "",
             "| Table | Content | Files |", "|---|---|---|"]
    for sid, title, files in SUPPLEMENT:
        lines.append(f"| {sid} | {title} | " + ", ".join(f"`{stem}.csv`" for stem, _ in files) + " |")
    return "\n".join(lines) + "\n"


def export(tables_dir: Path = TABLES, revision_dir: Path = REVISION) -> dict[str, int]:
    t: dict[str, list[dict]] = {}
    cols: dict[str, list[str]] = {}
    sources: dict[str, str] = {}
    for name, src in COPIES.items():
        cols[name], t[name] = read(src)
        sources[src.relative_to(ROOT).as_posix()] = sha256(src)
    for name in P10_USED + tuple(n for _, _, fs in SUPPLEMENT for _, n in fs if n.startswith("p10_")):
        if name not in t:
            p = TABLES / f"{name}.csv"
            cols[name], t[name] = read(p)
            sources[p.relative_to(ROOT).as_posix()] = sha256(p)
    for name, rows in t.items():
        for r in rows:
            for v in r.values():
                if v and DATE.search(v):
                    raise P13ExportError(f"{name}: calendar date in a paper-facing table")
    checks = cross_check(t)
    for name in COPIES:
        write_csv(tables_dir / f"{name}.csv", t[name], cols[name])
    t10 = table10(t)
    write_csv(tables_dir / "p13_table10_common_endpoints.csv", t10, list(t10[0]))
    t11 = table11(t)
    write_csv(tables_dir / "p13_table11_heater.csv", t11, list(t11[0]))
    sv = summary_values(t, t10)
    write_csv(tables_dir / "p13_summary_values.csv", sv, ["key", "value", "derivation"])
    n_supp = 0
    for _, _, files in SUPPLEMENT:
        for stem, name in files:
            write_csv(revision_dir / "supplementary" / f"{stem}.csv", t[name], cols[name])
            n_supp += 1
    write_text(revision_dir / "supplementary" / "README.md", supplementary_index())
    write_json(tables_dir / "p13_export_provenance.json", {
        "description": "P13 manuscript revision export (scripts/export_p13_tables.py); every table is a copy or a "
                       "selection of committed result cells",
        "sources_sha256": dict(sorted(sources.items())), "cross_checks_passed": checks,
        "tolerance": TOLERANCE})
    return {"copied_tables": len(COPIES), "derived_tables": 3, "supplementary_files": n_supp,
            "cross_checks": checks}
