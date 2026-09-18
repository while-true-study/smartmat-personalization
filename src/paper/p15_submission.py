"""Submission-ready candidate: rendering, package build and read-only checks of manuscript_p15_final.md.

The source `paper/manuscript/manuscript_p15_final.md` is the language-polished final text; no result number differs from
the previous candidate (every number is a source token resolved from paper/tables/). The package
`paper/submission_p15/` holds the rendered manuscript, main tables and figures, supplementary tables S1-S44 and
figures S1-S4 with their index, the reference library and a sheet of the open metadata placeholders. It contains no
raw or canonical data, no outputs, no continuous night series or heater-event sequences, no internal documents and no
version-control metadata. Earlier sources and their checks (manuscript.md, the P10/P13/P14 revisions) stay unchanged.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from src.data import paths
from src.data.io_guard import open_for_write, read_bytes, remove_file, write_json, write_text
from src.paper import manuscript_tables as T
from src.paper import manuscript_validation as V
from src.paper import p13_revision as E
from src.paper import p13_validation as P13
from src.paper import p14_validation as P14
from src.paper import references as R
from src.paper import render as RD
from src.paper import sources as S
from src.paper.manuscript_figures import FIGURES as P8_FIGURES

ROOT = paths.PROJECT_ROOT
SOURCE = ROOT / "paper" / "manuscript" / "manuscript_p15_final.md"
PACKAGE = ROOT / "paper" / "submission_p15"
RENDERED_NAME = "manuscript_p15_final_rendered.md"
RENDERED = PACKAGE / "manuscript" / RENDERED_NAME
BUILD_SCRIPT, VALIDATE_SCRIPT = "scripts/build_p15_submission.py", "scripts/validate_p15_submission.py"
FIGURE6 = P14.FIGURES_DIR / "figure6_target_distributions.png"
BASE_COMMIT = "070d2eb"                    # tip before the final-candidate work; earlier sources are compared with it
FROZEN = P14.FROZEN + ("paper/manuscript/manuscript_p14_revision.md",)
MAIN_FIGURES = [s for s in P8_FIGURES if not s.startswith("figureS")] + ["figure6_target_distributions"]
SUPP_FIGURES = [s for s in P8_FIGURES if s.startswith("figureS")]
ABSTRACT_WORDS = (190, 200)

# The only placeholders allowed in the final source: information from authors, institution or data provider.
PLACEHOLDER = re.compile(r"\[CONFIRM BEFORE SUBMISSION: ([^\]]+)\]")
ALLOWED_TOPICS = {
    "ethics": r"Institutional Review Board|exemption|waiver|secondary-use",
    "consent": r"informed consent",
    "data release": r"data release scope|redistribution|data-provider approval",
    "code release": r"code release scope",
    "sensor": r"sensor models, accuracy, resolution, response time, physical placement and placement relative to the heater",
    "authors": r"author names and order",
    "affiliations": r"^affiliations$",
    "corresponding author": r"corresponding author",
    "ORCID": r"ORCID",
    "CRediT": r"CRediT",
    "funding": r"funding",
    "conflicts": r"conflicts of interest",
    "acknowledgments": r"^acknowledgments$",
    "GenAI": r"generative-AI disclosure",
    "copyright": r"conference copyright",
    "Special Issue": r"Special Issue",
}
REQUIRED_TOPICS = [k for k in ALLOWED_TOPICS if k != "Special Issue"]      # the Special Issue goes in the cover letter
INTERNAL = re.compile(r"\bTODO\b|\bFIXME\b|\bmock\b|internal review|addendum|author check|\bP1[0-9]\b|\bD-0\d\d\b|"
                      r"\bOPEN-\d+|PI DECISION|\bPI\b|REVISION|revision_p1\d", re.I)
TERMINOLOGY = {
    "American -er/-or spelling (use centred, behaviour, labelled)": r"\bcenter(ed|ing)\b|\bbehavior\b|\blabeled\b",
    "-ise spelling (use -ize)": r"\b(initialis|normalis|standardis|optimis|organis|characteris|authoris|generalis|"
                                r"personalis)(e|ed|es|ing|ation|ations)\b",
    "unit spelling": r"° C|% RH|degC|\bdeg C\b|\b\d+ ?sec\b|\b\d+s\b",
}
EXCLUDED_IN_PACKAGE = re.compile(r"night_series|night_events|night_selection|figureS5|p13_figure_night|\.claude|"
                                 r"outputs/|DECISIONS|PI_REVIEW|RELEASE_AUDIT|PUSH_MANIFEST|\.git\b|windows\.parquet|"
                                 r"canonical_v1|control_events", re.I)


def read_source() -> str:
    return RD.read_source(SOURCE)


def render(source: str | None = None) -> str:
    text = read_source() if source is None else source
    if not FIGURE6.is_file():
        raise S.FrozenLookupError("Figure 6 missing (scripts/render_p14_figures.py)")
    text = text.replace("{{FIGURE:figure6_target_distributions}}",
                        "![Figure 6](../figures/figure6_target_distributions.png)")
    out = RD.render_manuscript(text)
    return out.replace("Rendered by scripts/build_submission_candidate.py from paper/manuscript/manuscript.md",
                       f"Rendered by {BUILD_SCRIPT} from {SOURCE.relative_to(ROOT).as_posix()}")


def placeholders(source: str) -> list[tuple[str, str]]:
    """(section, placeholder text) for every open placeholder, in order."""
    out, section = [], "Front matter"
    for line_block in re.split(r"(?m)^(#{1,4} .+)$", S.strip_comments(source)):
        if re.match(r"#{1,4} ", line_block):
            section = line_block.lstrip("#").strip()
            continue
        for m in PLACEHOLDER.finditer(line_block):
            out.append((section, " ".join(m.group(1).split())))
    return out


def _extract_table(rendered: str, number: int) -> str:
    start = rendered.index(f"**Table {number}.**")
    rest = rendered[start:]
    end = re.search(r"\|\n\n(?!\|)", rest)
    block = rest[: end.start() + 1] if end else rest
    after = rest[len(block):].lstrip("\n")
    if after.startswith("For User02") or after.startswith("Training-pool sensitivity"):   # table footnotes
        block += "\n\n" + after.split("\n\n", 1)[0]
    return block.strip() + "\n"


def _copy(src: Path, dst: Path) -> None:
    data = read_bytes(src)
    if src.suffix in (".md", ".bib", ".csv"):
        data = data.replace(b"\r\n", b"\n")
    with open_for_write(dst, "wb") as fh:
        fh.write(data)


def supplementary_index() -> str:
    lines = ["# Supplementary Materials", "",
             "Supplementary tables S1–S44 (machine-readable CSV, full precision, no calendar dates; Table S19 is a "
             "Markdown reproduction record) and supplementary figures S1–S4. Generated from the committed result "
             "tables; do not edit by hand.", "", "| Item | Content | Files |", "|---|---|---|"]
    p8 = (T.GENERATED / "supplementary" / "README.md").read_text(encoding="utf-8").splitlines()
    for line in p8:
        m = re.match(r"\| (S\d+) \| (.+?) \| (.+) \|$", line)
        if m:
            lines.append(f"| Table {m.group(1)} | {m.group(2)} | {m.group(3)} |")
    for sid, title, files in E.SUPPLEMENT:
        lines.append(f"| Table {sid} | {title} | " + ", ".join(f"`{stem}.csv`" for stem, _ in files) + " |")
    for stem in SUPP_FIGURES:
        lines.append(f"| {P8_FIGURES[stem]} | see the Supplementary Materials list of the manuscript | `{stem}.png` |")
    return "\n".join(lines) + "\n"


def metadata_sheet(source: str) -> str:
    rows = placeholders(source)
    out = ["# Open metadata before submission", "",
           "Every bracketed `[CONFIRM BEFORE SUBMISSION: …]` item of the manuscript. Fill the value in the manuscript "
           f"source, re-run `python {BUILD_SCRIPT}` and `python {VALIDATE_SCRIPT}`.",
           "", "| # | Section | Item | Value |", "|---|---|---|---|"]
    out += [f"| {i} | {sec} | {text} | |" for i, (sec, text) in enumerate(rows, 1)]
    return "\n".join(out) + "\n"


def expected_files(rendered: str) -> dict[str, Path | str]:
    """Package path -> source file (Path) or generated text (str)."""
    files: dict[str, Path | str] = {f"manuscript/{RENDERED_NAME}": rendered,
                                    "manuscript/references.bib": R.BIB_PATH,
                                    "METADATA_PLACEHOLDERS.md": metadata_sheet(read_source()),
                                    "supplementary/README.md": supplementary_index()}
    for p in sorted((T.GENERATED / "tables").glob("table*")):
        files[f"tables/{p.name}"] = p
    files["tables/table10_common_endpoints.md"] = _extract_table(rendered, 10)
    files["tables/table11_heater_diagnostic.md"] = _extract_table(rendered, 11)
    for stem in MAIN_FIGURES:
        files[f"figures/{stem}.png"] = FIGURE6 if stem.startswith("figure6") else T.GENERATED / "figures" / f"{stem}.png"
    for stem in SUPP_FIGURES:
        files[f"supplementary/figures/{stem}.png"] = T.GENERATED / "figures" / f"{stem}.png"
    for p in sorted((T.GENERATED / "supplementary").glob("TableS*")):
        files[f"supplementary/tables/{p.name}"] = p
    for _, _, stems in E.SUPPLEMENT:
        for stem, _ in stems:
            files[f"supplementary/tables/{stem}.csv"] = E.SUPPLEMENTARY / f"{stem}.csv"
    return files


def build(out: Path = PACKAGE) -> dict[str, str]:
    rendered = render()
    files = expected_files(rendered)
    before = {p for p in out.rglob("*") if p.is_file()} if out.is_dir() else set()
    for rel, src in files.items():
        if isinstance(src, str):
            write_text(out / rel, src)
        else:
            _copy(src, out / rel)
    for stale in before - {out / rel for rel in files} - {out / "MANIFEST.json"}:
        remove_file(stale)
    digests = {rel: hashlib.sha256(read_bytes(out / rel)).hexdigest() for rel in sorted(files)}
    write_json(out / "MANIFEST.json", {"description": "SHA-256 of every file of the submission-ready candidate package "
                                                      "except this manifest", "files": digests})
    return digests


# --- checks --------------------------------------------------------------------------------------------------------

def check_placeholders(source: str) -> list[str]:
    body = S.strip_comments(source)
    out = []
    for m in re.finditer(r"\[(?!@)([^\]\[]{3,})\]", re.sub(r"\{\{.*?\}\}", "TOK", body, flags=re.S)):
        text = " ".join(m.group(1).split())
        if "TOK" in text or re.match(r"[\d`+−-]", text):        # token intervals, numeric table headers
            continue
        if not text.startswith("CONFIRM BEFORE SUBMISSION: "):
            out.append(f"placeholder not in the unified form: [{text[:80]}]")
            continue
        topic = text.split(": ", 1)[1]
        if not any(re.search(rx, topic, re.I) for rx in ALLOWED_TOPICS.values()):
            out.append(f"placeholder outside the external-confirmation whitelist: [{text[:80]}]")
    found = [t for _, t in placeholders(source)]
    for key in REQUIRED_TOPICS:
        if not any(re.search(ALLOWED_TOPICS[key], t, re.I) for t in found):
            out.append(f"required external-confirmation placeholder missing: {key}")
    return out


def check_internal_notes(source: str) -> list[str]:
    return [f"internal or revision-history marker: {m.group(0)!r} near "
            f"{source[max(0, m.start() - 40):m.end() + 40]!r}" for m in INTERNAL.finditer(source)]


def check_terminology(source: str) -> list[str]:
    body = re.sub(r"\{\{.*?\}\}|\[@[^\]]*\]", " ", S.strip_comments(source), flags=re.S)
    return [f"{label}: {m.group(0)!r}" for label, rx in TERMINOLOGY.items() for m in re.finditer(rx, body)]


def check_abstract(rendered: str) -> list[str]:
    n = P13.abstract_words(rendered)
    return [] if ABSTRACT_WORDS[0] <= n <= ABSTRACT_WORDS[1] else [f"abstract has {n} words"]


def check_figure_order(rendered: str) -> list[str]:
    body = rendered.split("\n## Supplementary Materials\n")[0]
    first = []
    for m in re.finditer(r"\bFigures? (\d+)(?: and (\d+))?", body):
        for g in m.groups():
            if g and int(g) not in first:
                first.append(int(g))
    return [] if first == sorted(first) else [f"figures are not first cited in numerical order: {first}"]


def check_package(out: Path = PACKAGE) -> list[str]:
    problems = []
    if not out.is_dir():
        return ["submission package missing"]
    present = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    rendered = render()
    files = expected_files(rendered)
    problems += [f"package file missing: {rel}" for rel in sorted(set(files) - present)]
    problems += [f"unexpected package file: {rel}" for rel in sorted(present - set(files) - {"MANIFEST.json"})]
    problems += [f"excluded content in the package: {rel}" for rel in sorted(present) if EXCLUDED_IN_PACKAGE.search(rel)]
    for rel, src in files.items():
        p = out / rel
        if not p.is_file():
            continue
        data = read_bytes(p).replace(b"\r\n", b"\n")
        fresh = src.encode("utf-8") if isinstance(src, str) else read_bytes(src).replace(b"\r\n", b"\n")
        if data != fresh:
            problems.append(f"package file differs from a fresh build: {rel}")
    manifest = out / "MANIFEST.json"
    if manifest.is_file():
        recorded = json.loads(manifest.read_text(encoding="utf-8"))["files"]

        def digest(rel: str) -> str:                     # text files are hashed with LF line ends, as written
            data = read_bytes(out / rel)
            if rel.endswith((".md", ".csv", ".bib", ".json")):
                data = data.replace(b"\r\n", b"\n")
            return hashlib.sha256(data).hexdigest()
        problems += [f"manifest digest mismatch: {rel}" for rel, d in recorded.items()
                     if not (out / rel).is_file() or digest(rel) != d]
    else:
        problems.append("package MANIFEST.json missing")
    texts = {rel: (out / rel).read_text(encoding="utf-8") for rel in present
             if rel.endswith((".md", ".csv", ".bib", ".json")) and rel != "MANIFEST.json"}
    for rel, text in texts.items():
        if re.search(r"Figure S5|figureS5|t_rel_h|night_series", text):
            problems.append(f"withdrawn Figure S5 material in {rel}")
    problems += V.check_privacy({k: v for k, v in texts.items() if not k.endswith(".bib")})
    return problems


def check_frozen() -> list[str]:
    return [f"{rel} differs from commit {BASE_COMMIT}" for rel in FROZEN
            if subprocess.run(["git", "diff", "--quiet", BASE_COMMIT, "--", rel], cwd=ROOT).returncode != 0]


def validate() -> dict[str, list[str]]:
    source = read_source()
    rendered = RENDERED.read_text(encoding="utf-8").replace("\r\n", "\n") if RENDERED.is_file() else render(source)
    eta = P13.eta_strings(source)
    return {
        "tokens": P14.check_tokens(source),
        "numbers": V.check_numbers(source),
        "precision": P14.check_precision(source),
        "internal_notes": check_internal_notes(source),
        "placeholders": check_placeholders(source),
        "abstract": check_abstract(rendered),
        "numbering": P14.check_numbering(rendered) + check_figure_order(rendered),
        "figure_s5_withdrawn": P14.check_figure_s5(source, rendered),
        "claims": V.check_claims(source),
        "wording": P14.check_wording(source),
        "reproducibility_wording": P14.check_reproducibility_wording(source),
        "terminology_units": check_terminology(source) + [
            p for p in V.check_formatting(source, rendered)
            if not (p.startswith("formatting: more than two decimals") and p.split(": ")[-1].strip("'") in eta)],
        "privacy": V.check_privacy({SOURCE.name: source, "rendered": rendered}),
        "citations": V.check_citations(source, rendered),
        "rendered": [] if rendered == render(source) else ["package rendering differs from a fresh render"],
        "generated_tables": V.check_generated() + P13.check_exports(),
        "result_files": P14.check_result_files(),
        "frozen_sources": check_frozen(),
        "package": check_package(),
    }


def word_count(rendered: str) -> dict[str, int]:
    """Words of the rendered main text (Introduction to Conclusions), without tables, figure links and captions."""
    body = rendered.split("## 1. Introduction", 1)[1].split("## Supplementary Materials", 1)[0]
    body = "\n".join(line for line in body.splitlines()
                     if not line.startswith(("|", "![", "**Table", "**Figure")))
    return {"main_text": len(re.findall(r"\S+", body)), "abstract": P13.abstract_words(rendered)}
