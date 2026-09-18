"""P13 revision: rendering and read-only checks of paper/manuscript/manuscript_p13_revision.md.

The P8 validator (src/paper/manuscript_validation.py) checks manuscript.md and the P8 submission candidate; those stay
unchanged. This module applies the same token, number, claim, privacy, placeholder, citation and formatting checks to
the P13 source and adds the checks of the P13 revision: abstract length, table/figure/supplementary numbering, figure
paths, required and forbidden wording, freshness of the exported tables, and that the frozen sources are unchanged.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from src.data import paths
from src.paper import manuscript_validation as V
from src.paper import p13_revision as E
from src.paper import render as RD
from src.paper import sources as S
from src.paper.p13_figures import FIGURES as P13_FIGURES
from src.paper.p13_figures import FIGURES_DIR

ROOT = paths.PROJECT_ROOT
SOURCE = ROOT / "paper" / "manuscript" / "manuscript_p13_revision.md"
RENDERED = E.REVISION / "manuscript_p13_revision_rendered.md"
FROZEN = ("paper/manuscript/manuscript.md", "paper/manuscript/manuscript_p10_revision.md")
ABSTRACT_WORDS = (190, 200)
N_TABLES, N_FIGURES, N_SUPP_TABLES, N_SUPP_FIGURES = 11, 6, 44, 5
REQUIRED = (
    "These mechanisms cannot be separated with the present observational data.",
    "strongly compressed toward level-dominated behaviour",
    "cross-subject pretraining did not provide consistent additional predictive value over target-only training "
    "under the tested fixed adaptation protocol",
    "diagnostic comparator",
    "potentially endogenous to the target",
)
FORBIDDEN = {
    "thermal lag demonstrated": r"thermal lag (was|is|has been) demonstrated|demonstrat\w* (a )?thermal lag",
    "thermal accumulation claim": r"(captur\w*|carr\w*) thermal accumulation",
    "heater explains the gain": r"heater (context )?explains",
    "heater caused a temperature change": r"heater (activation )?(caused|lowered|reduced) the temperature",
    "constant convergence": r"converged to a constant",
    "architecture superiority": r"superior (architecture|model family)|architecture superiority is (shown|demonstrated)",
    "review or audit trail": r"internal (mock )?review|mock review|a draft of this article|further addendum",
    "evaluative feature wording": r"information helped|helped temperature",
}


def read_source() -> str:
    return RD.read_source(SOURCE)


def _p13_figure(stem: str) -> str:
    if stem not in P13_FIGURES or not (FIGURES_DIR / f"{stem}.png").is_file():
        raise S.FrozenLookupError(f"P13 figure missing: {stem}")
    return f"![{P13_FIGURES[stem]}](figures/{stem}.png)"


def substitute_p13_figures(text: str) -> str:
    return re.sub(r"`?\{\{FIGURE:(" + "|".join(P13_FIGURES) + r")\}\}`?", lambda m: _p13_figure(m.group(1)), text)


def render(source: str | None = None) -> str:
    text = substitute_p13_figures(read_source() if source is None else source)
    out = RD.render_manuscript(text)
    out = out.replace("from paper/manuscript/manuscript.md", "from paper/manuscript/manuscript_p13_revision.md "
                                                               "(scripts/render_p13_revision.py)")
    return out.replace("](../figures/", "](../generated/figures/")


# --- P13 checks ----------------------------------------------------------------------------------------------------

ETA_SPEC = ".3f"                 # eta squared only: three decimals (values below 0.01 occur); every other metric keeps
ETA_COLUMNS = re.compile(r"^eta")  # the P8 precisions


def _eta_token(tok: S.Token) -> bool:
    return tok.kind == "value" and tok.spec == ETA_SPEC and (
        bool(ETA_COLUMNS.match(tok.column)) or tok.filters.get("key", "").startswith("eta_"))


def eta_strings(source: str) -> set[str]:
    return {S.resolve(t) for t in S.tokens(source) if _eta_token(t)}


def check_tokens(source: str) -> list[str]:
    out = [p for p in V.check_tokens(substitute_p13_figures(source))
           if not (p.startswith(f"precision {ETA_SPEC!r} not allowed") and _eta_token(
               S.parse_token(p.split(": ", 1)[1])))]
    bad = [t.raw for t in S.tokens(source) if t.kind == "value" and t.spec == ETA_SPEC and not _eta_token(t)]
    return out + [f"precision '.3f' is reserved for eta squared: {b}" for b in bad] + [
        f"P13 figure marker {s} appears {source.count('{{FIGURE:' + s + '}}')} times (expected 1)"
        for s in P13_FIGURES if s.startswith("figure6") and source.count("{{FIGURE:" + s + "}}") != 1]


def abstract_words(rendered: str) -> int:
    body = rendered.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0]
    return len(re.findall(r"\S+", body))


def check_abstract(rendered: str) -> list[str]:
    n = abstract_words(rendered)
    lo, hi = ABSTRACT_WORDS
    return [] if lo <= n <= hi else [f"abstract has {n} words (required {lo}-{hi})"]


def _sequence(found: list[int], n: int, what: str) -> list[str]:
    out = []
    if sorted(set(found)) != list(range(1, n + 1)):
        out.append(f"{what}: numbers {sorted(set(found))}, expected 1-{n}")
    dup = sorted({k for k in found if found.count(k) > 1})
    if dup:
        out.append(f"{what}: duplicated {dup}")
    if found != sorted(found):
        out.append(f"{what}: not in ascending order of appearance")
    return out


def check_numbering(rendered: str) -> list[str]:
    body = rendered.split("\n## Supplementary Materials\n")[0]
    out = _sequence([int(x) for x in re.findall(r"^\*\*Table (\d+)\.\*\*", body, flags=re.M)], N_TABLES,
                    "table captions")
    out += _sequence([int(x) for x in re.findall(r"^\*\*Figure (\d+)\.\*\*", body, flags=re.M)], N_FIGURES,
                     "figure captions")
    first = []
    for m in re.finditer(r"\bFigures? (\d+)(?: and (\d+))?", body):
        for g in m.groups():
            if g and int(g) not in first:
                first.append(int(g))
    if first != sorted(first):
        out.append(f"figures are not first cited in numerical order: {first}")
    supp = rendered.split("\n## Supplementary Materials\n", 1)[1].split("\n## ", 1)[0]
    supp = " ".join(supp.split())
    out += _sequence([int(x) for x in re.findall(r"Table S(\d+):", supp)], N_SUPP_TABLES, "supplementary tables")
    out += _sequence([int(x) for x in re.findall(r"Figure S(\d+):", supp)], N_SUPP_FIGURES, "supplementary figures")
    cited = {int(x) for x in re.findall(r"Tables? S(\d+)", body)} | {int(x) for x in re.findall(r"S(\d+)–S", body)}
    out += [f"Table S{k} is cited but not listed" for k in sorted(cited) if k > N_SUPP_TABLES]
    listed = {sid for sid, _, _ in E.SUPPLEMENT}
    for sid in (f"S{k}" for k in range(35, N_SUPP_TABLES + 1)):
        if sid not in listed:
            out.append(f"no supplementary file set for Table {sid}")
    for sid, _, files in E.SUPPLEMENT:
        for stem, _ in files:
            if not (E.SUPPLEMENTARY / f"{stem}.csv").is_file():
                out.append(f"supplementary file missing for Table {sid}: {stem}.csv")
    return out


def check_figure_paths(rendered: str) -> list[str]:
    out = []
    for target in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", rendered):
        if not (RENDERED.parent / target).resolve().is_file():
            out.append(f"figure link does not resolve: {target}")
    for stem in P13_FIGURES:
        p = FIGURES_DIR / f"{stem}.png"
        if not p.is_file():
            out.append(f"figure missing: {p.name}")
        elif V._png_size(p)[0] < 1000:
            out.append(f"{p.name}: below 1000 px wide")
    return out


def check_wording(source: str) -> list[str]:
    """Required phrases must appear; forbidden claims may appear only in a negated sentence (as in the P8 claim check);
    review and audit-trail phrases may not appear at all."""
    flat = " ".join(S.strip_comments(source).split())
    out = [f"required wording missing: {r!r}" for r in REQUIRED if r not in flat]
    for sentence in V._sentences(S.strip_comments(source)):
        for label, rx in FORBIDDEN.items():
            if re.search(rx, sentence, re.I) and (label in ("review or audit trail", "evaluative feature wording")
                                                  or not V.NEGATION.search(sentence)):
                out.append(f"forbidden wording ({label}): {sentence.strip()[:140]!r}")
    return out


def check_placeholders(source: str) -> list[str]:
    """P8 placeholder rules; the code-repository placeholder carries a URL suffix since the P10 revision."""
    out = [p for p in V.check_placeholders(source) if "[CODE REPOSITORY]" not in p]
    if "[CODE REPOSITORY" not in source:
        out.append("open blocker placeholder missing: [CODE REPOSITORY …]")
    for p in ("[TEMPERATURE–HUMIDITY SENSOR MODEL, ACCURACY AND PLACEMENT — CONFIRM WITH DATA PROVIDER]",
              "[AFFILIATIONS — CONFIRM]", "[ORCID iDs — CONFIRM]", "[OTHER ACKNOWLEDGMENTS — CONFIRM]"):
        if p not in source:
            out.append(f"open blocker placeholder missing: {p}")
    return out


def check_exports() -> list[str]:
    """The committed P11/P12/P13 paper tables and supplementary files equal a fresh export of the result tables."""
    out = []
    if not all(p.is_file() for p in E.COPIES.values()):
        return ["P11/P12 result tables not available locally; export freshness not checked"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        E.export(tmp / "tables", tmp / "revision")
        for p in sorted((tmp / "tables").iterdir()):
            committed = E.TABLES / p.name
            if not committed.is_file():
                out.append(f"exported table missing: paper/tables/{p.name}")
            elif committed.read_bytes().replace(b"\r\n", b"\n") != p.read_bytes().replace(b"\r\n", b"\n"):
                out.append(f"paper/tables/{p.name} differs from a fresh export")
        fresh = {p.name for p in (tmp / "revision" / "supplementary").iterdir()}
        present = {p.name for p in E.SUPPLEMENTARY.iterdir()} if E.SUPPLEMENTARY.is_dir() else set()
        out += [f"stale supplementary file: {x}" for x in sorted(present - fresh)]
        for name in sorted(fresh):
            a, b = E.SUPPLEMENTARY / name, tmp / "revision" / "supplementary" / name
            if not a.is_file() or a.read_bytes().replace(b"\r\n", b"\n") != b.read_bytes().replace(b"\r\n", b"\n"):
                out.append(f"supplementary file differs from a fresh export: {name}")
    return out


def check_rendered(source: str) -> list[str]:
    if not RENDERED.is_file():
        return ["rendered P13 manuscript missing"]
    if RENDERED.read_text(encoding="utf-8").replace("\r\n", "\n") != render(source):
        return ["rendered P13 manuscript differs from a fresh render of the source"]
    return []


def check_frozen() -> list[str]:
    out = []
    for rel in FROZEN:
        r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT)
        if r.returncode != 0:
            out.append(f"{rel} differs from the committed version")
    return out


def validate() -> dict[str, list[str]]:
    source = read_source()
    rendered = RENDERED.read_text(encoding="utf-8").replace("\r\n", "\n") if RENDERED.is_file() else render(source)
    return {
        "tokens": check_tokens(source),
        "numbers": V.check_numbers(source),
        "claims": V.check_claims(source),
        "wording": check_wording(source),
        "privacy": V.check_privacy({"manuscript_p13_revision.md": source, "rendered": rendered}),
        "placeholders": check_placeholders(source),
        "citations": V.check_citations(source, rendered),
        "formatting": [p for p in V.check_formatting(source, rendered)
                       if not (p.startswith("formatting: more than two decimals")
                               and p.split(": ")[-1].strip("'") in eta_strings(source))],
        "abstract": check_abstract(rendered),
        "numbering": check_numbering(rendered),
        "figures": check_figure_paths(rendered),
        "exports": check_exports(),
        "rendered": check_rendered(source),
        "frozen_sources": check_frozen(),
    }
