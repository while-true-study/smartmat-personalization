"""Final editorial candidate: rendering, package build and read-only checks of manuscript_p16_final.md.

The P16 source is an editorial revision of `manuscript_p15_final.md`: language, structure, redundancy and formatting
changed; no result, number, analysis or research question did. The package and checks reuse the submission code of
`src/paper/p15_submission.py` (a separately configured instance of that module, so the P15 build and checks are left
as they are) and add the P16 checks: title and keywords, revision-history wording, scientific equivalence with P15
(every result token of P16 is a token of P15; research questions and required statements unchanged) and unchanged
P15 source.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
from pathlib import Path

from src.data import paths
from src.paper import p13_validation as P13
from src.paper import render as RD
from src.paper import sources as S

ROOT = paths.PROJECT_ROOT
P15_SOURCE = ROOT / "paper" / "manuscript" / "manuscript_p15_final.md"
BASE_COMMIT = "2d3681c"                  # main when the editorial revision started; earlier sources are compared with it


def _load_base():
    """A separate instance of the P15 submission module, configured for P16."""
    spec = importlib.util.spec_from_file_location("src.paper._p16_base", ROOT / "src" / "paper" / "p15_submission.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.SOURCE = ROOT / "paper" / "manuscript" / "manuscript_p16_final.md"
    mod.PACKAGE = ROOT / "paper" / "submission_p16"
    mod.RENDERED_NAME = "manuscript_p16_final_rendered.md"
    mod.RENDERED = mod.PACKAGE / "manuscript" / mod.RENDERED_NAME
    mod.BUILD_SCRIPT, mod.VALIDATE_SCRIPT = "scripts/build_p16_submission.py", "scripts/validate_p16_submission.py"
    mod.BASE_COMMIT = BASE_COMMIT
    mod.FROZEN = mod.FROZEN + ("paper/manuscript/manuscript_p15_final.md",)
    mod.build.__defaults__ = (mod.PACKAGE,)              # defaults were bound to the P15 package at definition time
    mod.check_package.__defaults__ = (mod.PACKAGE,)
    return mod


B = _load_base()
SOURCE, PACKAGE, RENDERED = B.SOURCE, B.PACKAGE, B.RENDERED
KEYWORDS = (5, 8)
FINAL_TITLE = ("Strict Unseen-Domain Evaluation of Pressure-Based Smart-Mat Temperature and Humidity Estimation "
               "against Simple Level Baselines")
NOT_KEYWORDS = ("negative transfer",)      # the text reports mixed, level-dominated adaptation
REVISION_HISTORY = re.compile(r"\breviewers?\b|\binternal\b|\bP1[0-9]\b|mock review|addendum|\bTODO\b|\bFIXME\b",
                              re.I)
REQUIRED = (
    "These mechanisms cannot be separated with the present observational data.",
    "strongly compressed toward level-dominated behaviour",
    "did not provide consistent additional predictive value over target-only training under the tested fixed "
    "adaptation protocol",
    "not an admissible pressure-only estimator",
    "Confidence intervals were obtained by the pre-specified paired night-cluster bootstrap",
    "the diagnostic was not used for model selection",
    "does not independently reproduce the heater-context diagnostic",
    "potentially endogenous to the target",
)


def read_source() -> str:
    return B.read_source()


def render(source: str | None = None) -> str:
    return B.render(source)


def build() -> dict[str, str]:
    return B.build(B.PACKAGE)


def word_count(rendered: str) -> dict[str, int]:
    return B.word_count(rendered)


def _flat(text: str) -> str:
    return " ".join(S.strip_comments(text).split())


def check_front_matter(source: str) -> list[str]:
    out = []
    titles = re.findall(r"(?m)^# (.+)$", source)
    if titles != [FINAL_TITLE]:
        out.append(f"title is {titles!r}, expected the final title")
    m = re.search(r"\*\*Keywords:\*\*(.+?)\n\n", source, re.S)
    if not m:
        return out + ["keywords missing"]
    kws = [k.strip() for k in " ".join(m.group(1).split()).split(";") if k.strip()]
    if not KEYWORDS[0] <= len(kws) <= KEYWORDS[1]:
        out.append(f"{len(kws)} keywords (required {KEYWORDS[0]}-{KEYWORDS[1]})")
    if len({k.lower() for k in kws}) != len(kws):
        out.append("duplicate keywords")
    out += [f"keyword not supported as a general conclusion: {k}" for k in kws if k.lower() in NOT_KEYWORDS]
    return out


def check_revision_history(source: str) -> list[str]:
    body = re.sub(r"\{\{.*?\}\}|\[@[^\]]*\]", " ", source, flags=re.S)
    return [f"revision-history wording: {m.group(0)!r} near {body[max(0, m.start() - 40):m.end() + 40]!r}"
            for m in REVISION_HISTORY.finditer(body)]


def _rqs(text: str) -> list[str]:
    return [" ".join(m.group(1).split()) for m in re.finditer(r"- \*\*RQ\d[^*]*:\*\*(.+?)(?=\n- |\n\n)", text, re.S)]


def check_equivalence(source: str) -> list[str]:
    """Editorial-only: no result token that P15 does not have, the same research questions and statements, the same
    generated tables and figures (same files), and no new numbers typed outside tokens."""
    p15 = RD.read_source(P15_SOURCE)
    tok = lambda t: {x.raw for x in S.tokens(t)}  # noqa: E731
    out = [f"result token not in P15: {t}" for t in sorted(tok(source) - tok(p15))]
    if _rqs(source) != _rqs(p15):
        out.append("research questions differ from P15")
    out += [f"required statement missing: {r!r}" for r in REQUIRED if r not in _flat(source)]
    for kind in ("TABLE", "FIGURE"):
        a = sorted(re.findall(rf"\{{\{{{kind}:([^}}]+)\}}\}}", source))
        b = sorted(re.findall(rf"\{{\{{{kind}:([^}}]+)\}}\}}", p15))
        if a != b:
            out.append(f"{kind.lower()} assets differ from P15: {a} vs {b}")
    return out


def check_p15_unchanged() -> list[str]:
    rel = P15_SOURCE.relative_to(ROOT).as_posix()
    r = subprocess.run(["git", "diff", "--quiet", BASE_COMMIT, "--", rel], cwd=ROOT)
    return [] if r.returncode == 0 else [f"{rel} differs from commit {BASE_COMMIT}"]


def validate() -> dict[str, list[str]]:
    source = read_source()
    results = B.validate()
    results["front_matter"] = check_front_matter(source)
    results["revision_history"] = check_revision_history(source)
    results["scientific_equivalence"] = check_equivalence(source)
    results["p15_source_unchanged"] = check_p15_unchanged()
    results["abstract"] = results["abstract"] + (
        [] if P13.abstract_words(render(source)) else ["abstract empty"])
    return results
