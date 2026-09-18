"""P14 submission candidate: rendering and read-only checks of paper/manuscript/manuscript_p14_revision.md.

Reuses the P8 and P13 checks (src/paper/manuscript_validation.py, src/paper/p13_validation.py) with the P14 source,
rendering and figure directory, and adds the P14 checks (D-069, D-070): Figure S5 withdrawn from the text and its source
data absent from the tip; η² at three decimals and MAE-type values at two; no deterministic-reproduction claim for the
retrained network; D-069 recorded; post-hoc scope and paired night-cluster bootstrap stated; no request-based access
promised; supplementary Figures S1–S4 and Tables S1–S44; frozen manuscripts and result files unchanged.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

from src.data import paths
from src.paper import manuscript_validation as V
from src.paper import p13_revision as E
from src.paper import p13_validation as P13
from src.paper import render as RD
from src.paper import sources as S

ROOT = paths.PROJECT_ROOT
SOURCE = ROOT / "paper" / "manuscript" / "manuscript_p14_revision.md"
REVISION = ROOT / "paper" / "manuscript" / "revision_p14"
RENDERED = REVISION / "manuscript_p14_revision_rendered.md"
FIGURES_DIR = REVISION / "figures"
FIGURES = {"figure6_target_distributions": "Figure 6"}
BASE_COMMIT = "bfb1add"            # P13 review package; the frozen manuscripts are compared with this commit
FROZEN = ("paper/manuscript/manuscript.md", "paper/manuscript/manuscript_p10_revision.md",
          "paper/manuscript/manuscript_p13_revision.md")
WITHDRAWN = ("paper/tables/p13_figure_night_series.csv", "paper/tables/p13_figure_night_events.csv",
             "paper/tables/p13_figure_night_selection.csv",
             "paper/manuscript/revision_p13/figures/figureS5_example_nights.png")
N_TABLES, N_FIGURES, N_SUPP_TABLES, N_SUPP_FIGURES = 11, 6, 44, 4
REQUIRED = P13.REQUIRED + (
    "Heater-Context Diagnostic (Post Hoc, Descriptive)",
    "the diagnostic was not used for model selection",
    "no heater or controller field was added to the inputs",
    "no window length, history length or baseline rule was changed after its results were seen",
    "η² values are shown as raw-target η² → within-night-centred η²",
    "Confidence intervals were obtained by the pre-specified paired night-cluster bootstrap",
    "not an admissible pressure-only estimator",
    "this sensitivity analysis uses a different nuisance adjustment from the primary within-night value",
    "does not independently reproduce the heater-context diagnostic",
)
FORBIDDEN = {
    "unsupported physical claim": r"body[–-]bed interface|physiological microclimate|thermal lag at the body",
    "request-based access": r"available (up)?on (reasonable )?request|upon request|on request from",
}
MAE_COLUMNS = re.compile(r"^(mae|delta_mae|ci_lower|ci_upper|MAE)")


def read_source() -> str:
    return RD.read_source(SOURCE)


def _figure(stem: str) -> str:
    if stem not in FIGURES or not (FIGURES_DIR / f"{stem}.png").is_file():
        raise S.FrozenLookupError(f"P14 figure missing: {stem}")
    return f"![{FIGURES[stem]}](figures/{stem}.png)"


def substitute_figures(text: str) -> str:
    return re.sub(r"`?\{\{FIGURE:(" + "|".join(FIGURES) + r")\}\}`?", lambda m: _figure(m.group(1)), text)


def render(source: str | None = None) -> str:
    out = RD.render_manuscript(substitute_figures(read_source() if source is None else source))
    out = out.replace("from paper/manuscript/manuscript.md", "from paper/manuscript/manuscript_p14_revision.md "
                                                               "(scripts/render_p14_revision.py)")
    return out.replace("](../figures/", "](../generated/figures/")


# --- P14 checks ----------------------------------------------------------------------------------------------------

def check_tokens(source: str) -> list[str]:
    out = [p for p in P13.check_tokens(source) if "figure6" not in p]
    n = source.count("{{FIGURE:figure6_target_distributions}}")
    out += [] if n == 1 else [f"Figure 6 marker appears {n} times (expected 1)"]
    try:
        substitute_figures(source)
    except S.FrozenLookupError as exc:
        out.append(str(exc))
    return out


def check_precision(source: str) -> list[str]:
    out = []
    for tok in S.tokens(source):
        if tok.kind != "value":
            continue
        eta = tok.column.startswith("eta") or tok.filters.get("key", "").startswith("eta_")
        if eta and tok.spec != P13.ETA_SPEC:
            out.append(f"eta squared not at three decimals: {tok.raw}")
        if MAE_COLUMNS.match(tok.column) and tok.spec not in (".2f", "+.2f"):
            out.append(f"MAE-type value not at two decimals: {tok.raw}")
    return out


def check_figure_s5(source: str, rendered: str) -> list[str]:
    out = [f"{name} mentions Figure S5" for name, text in (("source", source), ("rendered", rendered))
           if re.search(r"Figure S5|figureS5", text)]
    tracked = subprocess.run(["git", "ls-files", "--", *WITHDRAWN], cwd=ROOT, capture_output=True, text=True).stdout
    out += [f"withdrawn file present in the working tree: {p}" for p in WITHDRAWN if (ROOT / p).exists()]
    out += [f"withdrawn file still tracked: {p}" for p in tracked.split()]
    return out


def check_reproducibility_wording(source: str) -> list[str]:
    out = [f"deterministic claim for the retrained network: {s.strip()[:140]!r}"
           for s in V._sentences(S.strip_comments(source))
           if re.search(r"determinis", s, re.I) and re.search(r"retrain|common endpoints|common pool", s, re.I)]
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    # D-069 corrects a phrase of D-068; it is required only where the decision log carries D-068 (the public research
    # snapshot publishes the decision log only up to D-063).
    if "## D-068" in decisions and "## D-069 — Correction to D-068 reproducibility wording" not in decisions:
        out.append("D-069 (correction to D-068 reproducibility wording) is not recorded in docs/DECISIONS.md")
    return out


def check_wording(source: str) -> list[str]:
    flat = " ".join(S.strip_comments(source).split())
    out = [f"required wording missing: {r!r}" for r in REQUIRED if r not in flat]
    out += P13.check_wording(source)
    unbracketed = re.sub(r"\[[^\]]*\]", " ", flat)
    for label, rx in FORBIDDEN.items():
        out += [f"forbidden wording ({label}): {m.group(0)!r}" for m in re.finditer(rx, unbracketed, re.I)]
    return out


def check_numbering(rendered: str) -> list[str]:
    body = rendered.split("\n## Supplementary Materials\n")[0]
    out = P13._sequence([int(x) for x in re.findall(r"^\*\*Table (\d+)\.\*\*", body, flags=re.M)], N_TABLES,
                        "table captions")
    out += P13._sequence([int(x) for x in re.findall(r"^\*\*Figure (\d+)\.\*\*", body, flags=re.M)], N_FIGURES,
                         "figure captions")
    supp = " ".join(rendered.split("\n## Supplementary Materials\n", 1)[1].split("\n## ", 1)[0].split())
    out += P13._sequence([int(x) for x in re.findall(r"Table S(\d+):", supp)], N_SUPP_TABLES, "supplementary tables")
    out += P13._sequence([int(x) for x in re.findall(r"Figure S(\d+):", supp)], N_SUPP_FIGURES,
                         "supplementary figures")
    cited = {int(x) for x in re.findall(r"Figures? S(\d+)", body)}
    out += [f"Figure S{k} is cited but not listed" for k in sorted(cited) if k > N_SUPP_FIGURES]
    for sid, _, files in E.SUPPLEMENT:
        out += [f"supplementary file missing for Table {sid}: {stem}.csv" for stem, _ in files
                if not (E.SUPPLEMENTARY / f"{stem}.csv").is_file()]
    return out


def check_figure_paths(rendered: str) -> list[str]:
    out = [f"figure link does not resolve: {t}" for t in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", rendered)
           if not (RENDERED.parent / t).resolve().is_file()]
    for stem in FIGURES:
        p = FIGURES_DIR / f"{stem}.png"
        if not p.is_file():
            out.append(f"figure missing: {p.name}")
        elif V._png_size(p)[0] < 1000:
            out.append(f"{p.name}: below 1000 px wide")
    return out


def check_rendered(source: str) -> list[str]:
    if not RENDERED.is_file():
        return ["rendered P14 manuscript missing"]
    if RENDERED.read_text(encoding="utf-8").replace("\r\n", "\n") != render(source):
        return ["rendered P14 manuscript differs from a fresh render of the source"]
    return []


def check_frozen() -> list[str]:
    out = []
    for rel in FROZEN:
        if subprocess.run(["git", "diff", "--quiet", BASE_COMMIT, "--", rel], cwd=ROOT).returncode != 0:
            out.append(f"{rel} differs from commit {BASE_COMMIT}")
    return out


def _rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def check_result_files() -> list[str]:
    """P11/P12 result files equal the digests recorded at export; P10 metric files equal their paper-table copies."""
    out = []
    prov = json.loads((E.TABLES / "p13_export_provenance.json").read_text(encoding="utf-8"))["sources_sha256"]
    for rel, digest in prov.items():
        p = ROOT / rel
        if not p.is_file():
            out.append(f"result file not available locally: {rel}")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            out.append(f"result file changed since the P13 export: {rel}")
    metrics = ROOT / "outputs" / "metrics" / "p10"
    for table in sorted(E.TABLES.glob("p10_*.csv")):
        src = metrics / table.name
        if src.is_file() and _rows(src) != _rows(table):
            out.append(f"outputs/metrics/p10/{table.name} differs from paper/tables/{table.name}")
    return out


def validate() -> dict[str, list[str]]:
    source = read_source()
    rendered = RENDERED.read_text(encoding="utf-8").replace("\r\n", "\n") if RENDERED.is_file() else render(source)
    eta = P13.eta_strings(source)
    return {
        "tokens": check_tokens(source),
        "numbers": V.check_numbers(source),
        "precision": check_precision(source),
        "figure_s5_withdrawn": check_figure_s5(source, rendered),
        "reproducibility_wording": check_reproducibility_wording(source),
        "claims": V.check_claims(source),
        "wording": check_wording(source),
        "privacy": V.check_privacy({"manuscript_p14_revision.md": source, "rendered": rendered}),
        "placeholders": P13.check_placeholders(source),
        "citations": V.check_citations(source, rendered),
        "formatting": [p for p in V.check_formatting(source, rendered)
                       if not (p.startswith("formatting: more than two decimals") and p.split(": ")[-1].strip("'")
                               in eta)],
        "abstract": P13.check_abstract(rendered),
        "numbering": check_numbering(rendered),
        "figures": check_figure_paths(rendered),
        "exports": P13.check_exports(),
        "rendered": check_rendered(source),
        "frozen_sources": check_frozen(),
        "result_files": check_result_files(),
    }
