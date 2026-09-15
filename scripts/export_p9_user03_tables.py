"""Export the P9 User03 external-validation tables and report blocks (no hand-copied numbers; D-061).

Reads outputs/metrics/p9_user03/ (scripts/build_p9_user03.py, scripts/run_p9_user03.py) and writes:
  paper/tables/p9_user03_*.csv, paper/tables/p9_user03_provenance.json     paper-facing (night indices only, no dates)
  generated blocks of docs/P9_USER03_EXTERNAL_VALIDATION_REPORT.md
  (<!-- BEGIN GENERATED P9:<name> --> … <!-- END GENERATED P9:<name> -->)
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

METRICS = paths.PROJECT_ROOT / "outputs" / "metrics" / "p9_user03"
TABLES = paths.PROJECT_ROOT / "paper" / "tables"
NAMES = ("qa_coverage", "qa_nights", "qa_totals", "summary", "by_seed", "per_night_summary", "interpretation")
MARK = re.compile(r"<!-- BEGIN GENERATED P9:(?P<n>[a-z_0-9]+) -->.*?<!-- END GENERATED P9:(?P=n) -->", re.S)
TARGETS = ("temperature", "humidity")
LABEL = {"training_mean": "Training mean", "raw_tcn": "RAW-TCN", "raw_tcn_mean_over_configurations":
         "RAW-TCN, mean of the three configurations (descriptive)"}


def read(name: str) -> list[dict]:
    with open(METRICS / f"p9_user03_{name}.csv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def f3(x) -> str:
    return "NA" if x in ("", "nan", None) else f"{float(x):.3f}"


def s3(x) -> str:
    return "NA" if x in ("", "nan", None) else f"{float(x):+.3f}"


def md(header, rows) -> str:
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def blocks(t: dict[str, list[dict]]) -> dict[str, str]:
    b = {}
    rows = []
    for tg in TARGETS:
        for r in [x for x in t["summary"] if x["target"] == tg]:
            cfg = "" if r["config_fold"] in ("", "all") else f" (fold-{r['config_fold']} configuration)"
            rng = (f" [{f3(r['mae_seed_min'])}–{f3(r['mae_seed_max'])}]" if r.get("mae_seed_min") not in (None, "")
                   else "")
            rows.append([tg, LABEL[r["model"]] + cfg, f3(r["mae"]) + rng, f3(r["rmse"]), s3(r["bias"]), f3(r["R"]),
                         f3(r["Q"]), s3(r["r_pooled"]), s3(r["r_within"]), s3(r.get("per_night_r_median", ""))])
    b["summary"] = ("**Table P9-1 — User03 external validation (all labelled windows): training-mean predictor and the "
                    "three source-only RAW-TCN configurations (seed mean over seeds 0–2; brackets: seed range of MAE). "
                    "No night-bootstrap interval (fewer than 10 nights).**\n\n"
                    + md(["Target", "Predictor", "MAE", "RMSE", "Bias", "R", "Q", "r pooled", "r within night",
                          "median per-night r"], rows))
    rows = []
    for r in t["by_seed"]:
        if r["model"] == "raw_tcn":
            rows.append([r["target"], r["config_fold"], r["seed"], f3(r["mae"]), s3(r["bias"]), f3(r["R"]),
                         f3(r["Q"]), s3(r["r_pooled"]), s3(r["r_within"])])
    b["seeds"] = ("**Table P9-2 — Per seed.**\n\n"
                  + md(["Target", "Configuration (fold)", "Seed", "MAE", "Bias", "R", "Q", "r pooled",
                        "r within night"], rows))
    rows = []
    ns = t["per_night_summary"]
    nights = sorted({int(r["night_index"]) for r in ns})
    for tg in TARGETS:
        for key in [("training_mean", "")] + [("raw_tcn", str(c)) for c in (1, 2, 3)]:
            rs = {int(r["night_index"]): r for r in ns if r["model"] == key[0] and r["config_fold"] == key[1]
                  and r["target"] == tg}
            rows.append([tg, LABEL[key[0]] + (f" ({key[1]})" if key[1] else ""),
                         *[f"{f3(rs[k]['mae'])} / {s3(rs[k]['r'])}" for k in nights]])
    b["nights"] = ("**Table P9-3 — Per night (seed mean): MAE / per-night r (NA for the constant predictor).**\n\n"
                   + md(["Target", "Predictor", *[f"night {k}" for k in nights]], rows))
    rows = [[r["target"], r["comparison"].replace("_", " "), r["within_night_covariation"], r["night_bootstrap"],
             r["relation_to_n3"]] for r in t["interpretation"]]
    b["interpretation"] = ("**Table P9-4 — Pre-registered interpretation (plan §9).**\n\n"
                           + md(["Target", "Comparison", "Within-night co-variation", "Night bootstrap",
                                 "Relation to the N = 3 findings"], rows))
    return b


def main() -> int:
    t = {n: read(n) for n in NAMES}
    for n in NAMES:
        rows = [dict(r, protocol_version="v1.3", status="post_hoc_external_sensitivity") for r in t[n]]
        cols = list(dict.fromkeys(k for r in rows for k in r))
        write_csv(TABLES / f"p9_user03_{n}.csv", rows, cols)
    prov = json.loads((METRICS / "p9_user03_provenance.json").read_text(encoding="utf-8"))
    man = json.loads((paths.PROJECT_ROOT / "data" / "external" / "p9_user03_v1_manifest.json").read_text(encoding="utf-8"))
    write_json(TABLES / "p9_user03_provenance.json", {
        "description": "P9 post-hoc external sensitivity validation on User03 (protocol v1.3, D-061); not part of the "
                       "primary cohort; conditional on OPEN-29", **{k: prov[k] for k in (
                           "protocol_version", "decision", "status", "plan_sha256_lf", "config_sha256_lf",
                           "base_protocol_sha256")},
        "analysis_git_commit": prov.get("git_commit"), "analysis_tree_dirty": prov.get("git_dirty_tracked_files"),
        "source_files": [{k: s[k] for k in ("night", "role", "file_id", "sha256")} for s in man["sources"]],
        "external_rows_content_sha256": man["rows_content_sha256"], "training_mean": prov["training_mean"],
        "prediction_sha256": prov["runs"]})
    b = blocks(t)
    rep = paths.PROJECT_ROOT / "docs" / "P9_USER03_EXTERNAL_VALIDATION_REPORT.md"
    text = rep.read_text(encoding="utf-8").replace("\r\n", "\n")
    if {m.group("n") for m in MARK.finditer(text)} != set(b):
        raise SystemExit("report markers differ from the generated blocks")
    text = MARK.sub(lambda m: f"<!-- BEGIN GENERATED P9:{m.group('n')} -->\n\n{b[m.group('n')]}\n\n"
                              f"<!-- END GENERATED P9:{m.group('n')} -->", text)
    write_text(rep, text)
    print(f"wrote paper/tables/p9_user03_*.csv, p9_user03_provenance.json and {len(b)} report blocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
