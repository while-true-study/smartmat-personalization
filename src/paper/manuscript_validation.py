"""Manuscript validator (P8): read-only checks of the manuscript source, generated assets and submission candidate.

Every check returns a list of problems; an empty list is a pass. Nothing here writes or rewrites content.
Checks (docs/P8_FINAL_BLOCKERS.md, paper/manuscript/MANUSCRIPT_NOTES.md):
  tokens        every source token resolves to one frozen cell; allowed precisions; every main table/figure marker
  numbers       no hand-typed decimal or percentage outside tokens, except declared design constants
  generated     generated tables and supplementary files equal a fresh build; every table cell traces to frozen cells
  rendered      the committed rendered manuscript equals a fresh render; the candidate manifest matches its files
  citations     every key exists, every entry is cited, references numbered in order of first appearance
  privacy       no calendar date, month or season, excluded-source id, local path or e-mail; five-channel wording
  claims        no unsupported phrase unless negated in the same sentence
  placeholders  open blockers stay visible as placeholders; no statement presents them as resolved
  conference    the conference reference carries no invented DOI, pages, volume or URL
  figures       every figure exists at print resolution; optional re-render with text-overlap check
  formatting    unit spelling, b notation, sign conventions, subject count, precision
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import tempfile
from pathlib import Path

from src.paper import manuscript_tables as T
from src.paper import references as R
from src.paper import render as RD
from src.paper import sources as S
from src.paper.manuscript_figures import FIGURES

ALLOWED_SPECS = {".2f", "+.2f", ".1f", "+.1f", "d", ",d", "s"}
MAIN_TABLES = ("table1_dataset_protocol", "table2_strict_loso", "table3_feature_family", "table4_personalization",
               "table5_night_robustness", "table6_residual_variation", "table7_posthoc_comparators",
               "table8_dynamic_signal", "table9_external_validation")
MAIN_FIGURES = ("figure1_study_design", "figure2_temperature_personalization", "figure3_humidity_personalization",
                "figure4_night_robustness", "figure5_posthoc_comparators")
# Decimals or percentages that may be typed: design constants of the frozen protocol, not results.
DESIGN_LITERALS = {"0.1", "0.3", "95 %", "100 %",
                   "0.10", "0.90"}                    # v1.2 addendum thresholds (D-059), design constants
MONTHS = r"January|February|March|April|June|July|August|September|October|November|December"
PRIVATE = {
    "ISO calendar date": re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b"),
    "compact calendar date": re.compile(r"(?<![\d.])20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)"),
    "season label": re.compile(r"\b(winter|spring|summer|autumn)\b", re.I),
    # User03 may appear only as the post-hoc external sensitivity subject (D-061); User04–User06 never
    "excluded or auxiliary subject id": re.compile(r"User0[4-6]"),
    "local path": re.compile(r"[A-Za-z]:\\|/Users/|/home/|\bDesktop\b|스마트|학술지|\.claude"),
    "e-mail address": re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}"),
}
FIVE_CHANNEL_OK = re.compile(r"an auxiliary five-channel source excluded from the main six-channel evaluation", re.I)
FORBIDDEN = {
    "significant(ly)": r"\bsignifican(t|tly|ce)\b",
    "remarkable": r"\bremarkabl",
    "dramatic": r"\bdramatic",
    "novelty claim": r"\bnovel\b|\bfirst (study|work|to|time)\b",
    "state of the art": r"state[- ]of[- ]the[- ]art",
    "universal": r"\buniversal(ly)?\b",
    "robust personalization": r"robust personali[sz]ation",
    "few-shot": r"few-shot",
    "domain invariance": r"domain invarian",
    "proof": r"\bprove[sn]?\b|\bproof\b",
    "causal claim": r"\bcause[sd]?\b|\bcausal(ly)? (effect|relation|interpretation|claim|mechanism|link)",
    "all seeds": r"\b(every|all) seeds?\b",
    "end-to-end": r"end-to-end",
    "publicly available": r"\b(publicly|openly) available\b",
    "population inference": r"\bpopulation[- ]level\b|\bgenerali[sz]es? to (the )?population",
}
NEGATION = re.compile(r"\b(no|not|never|nor|neither|without|cannot|do not|does not|did not|rather than)\b", re.I)
# Open blockers (docs/P8_FINAL_BLOCKERS.md). When the PI resolves one, remove it here in the same commit.
OPEN_PLACEHOLDERS = ("[FUNDING TO BE CONFIRMED BY PI]", "[ETHICS / IRB INFORMATION REQUIRED FROM PI]",
                     "[INFORMED CONSENT WORDING REQUIRED FROM PI]", "[DATA REPOSITORY]", "[CODE REPOSITORY]", "[DOI]",
                     "[LICENSE]", "[AUTHOR NAMES AND ORDER — CONFIRM]", "[CRediT ROLES — CONFIRM]",
                     "[CONFLICTS OF INTEREST — CONFIRM]")
RESOLVED_LOOKING = {
    "funding stated": r"received no external funding|was funded by",
    "IRB approval stated": r"approved by the (Institutional Review Board|Ethics Committee)|ethical review and approval "
                           r"were waived",
    "consent stated": r"informed consent was obtained from all subjects|consent was waived",
    "public data stated": r"\b(publicly|openly) available\b|is available at https?://",
    "DOI or URL in availability statements": r"https?://|doi\.org|\b10\.\d{4,9}/",
    "license stated": r"\bCC[- ]BY\b|Creative Commons|MIT License|Apache License|GPL",
    "conflicts stated": r"declare no conflicts? of interest",
}
AVAILABILITY_SECTIONS = ("Data Availability Statement", "Funding", "Conflicts of Interest",
                         "Institutional Review Board Statement", "Informed Consent Statement")
# Placeholder patterns that may not appear in a final submission file (--final).
FINAL_FORBIDDEN = {
    "confirmation placeholder": r"\[[^\]]*CONFIRM[^\]]*\]",
    "PI placeholder": r"\[[^\]]*(PI DECISION|FROM PI|BY PI|— PI)[^\]]*\]",
    "open repository/DOI/license placeholder": r"\[(DATA REPOSITORY|CODE REPOSITORY|DOI|LICENSE)\]",
    "pending marker": r"\[PENDING[^\]]*\]|\bBLOCKED\b",
    "unrendered source token or citation": r"\{\{|\[@",
}


def _sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## (.+)$", text, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def _sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text)
    return re.split(r"(?<=[.;:!?])\s+(?=[A-Z(\[*`-])|\s-\s", flat)


def _body(source: str) -> str:
    """Source without comments, tokens and code spans (what is typed by hand)."""
    t = S.strip_comments(source)
    t = re.sub(r"`?\{\{.*?\}\}`?", " ", t, flags=re.S)
    return re.sub(r"`[^`]*`", " ", t)


# --- checks -------------------------------------------------------------------------------------------------------

def check_tokens(source: str) -> list[str]:
    out = []
    toks = S.tokens(source)
    for tok in toks:
        try:
            if tok.kind in ("value", "count"):
                S.resolve(tok)
                if tok.kind == "value" and tok.spec not in ALLOWED_SPECS:
                    out.append(f"precision {tok.spec!r} not allowed: {tok.raw}")
            else:
                RD._asset(tok)
        except (S.FrozenLookupError, ValueError, KeyError) as exc:
            out.append(f"unresolved token: {tok.raw} ({exc})")
    for kind, stems in (("table", MAIN_TABLES), ("figure", MAIN_FIGURES)):
        found = [t.table for t in toks if t.kind == kind]
        for stem in stems:
            if found.count(stem) != 1:
                out.append(f"{kind} marker {stem} appears {found.count(stem)} times (expected 1)")
    return out


def check_numbers(source: str) -> list[str]:
    body = _body(source)
    body = re.sub(r"Sections? \d+(\.\d+)*(–\d+(\.\d+)*)?|§\d+(\.\d+)*|^#+ \d+(\.\d+)*\.?", " ", body, flags=re.M)
    body = re.sub(r"\(Section \d+(\.\d+)*\)", " ", body)
    body = re.sub(r"GPT-\d+(\.\d+)*", " ", body)                      # product version names, not results
    body = re.sub(r"\b(Python|PyTorch|CUDA|NumPy|PyArrow|Matplotlib|cuDNN|pytest)\s+\d+(\.\d+)*", " ", body)  # software
    hits = [m.group(0).strip() for m in re.finditer(r"(?<![\w.])\d+\.\d+(?![\w.])|\d+(\.\d+)?\s?%", body)]
    return [f"hand-typed number outside a source token: {h!r}" for h in hits if h not in DESIGN_LITERALS]


def check_generated(generated: Path = T.GENERATED) -> list[str]:
    out = []
    for t in T.build_main():
        out += T.check_traceable(t)
        for suffix, fresh in ((".md", T.to_markdown(t)), (".csv", None)):
            p = generated / "tables" / f"{t.stem}{suffix}"
            if not p.is_file():
                out.append(f"generated table missing: {p.name}")
                continue
            committed = p.read_text(encoding="utf-8").replace("\r\n", "\n")
            if fresh is None:
                rows = [line.split(",")[0] for line in committed.splitlines()[1:]]
                if len(rows) != len(t.rows):
                    out.append(f"{p.name}: {len(rows)} rows, fresh build has {len(t.rows)}")
            elif committed != fresh:
                out.append(f"{p.name} differs from a fresh build from the frozen tables")
    with tempfile.TemporaryDirectory() as tmp:
        T.export(Path(tmp))
        fresh_files = {p.relative_to(tmp).as_posix() for p in Path(tmp).rglob("*") if p.is_file()}
        committed_files = {p.relative_to(generated).as_posix() for sub in ("tables", "supplementary")
                           if (generated / sub).is_dir() for p in (generated / sub).rglob("*") if p.is_file()}
        out += [f"stale generated file: {x}" for x in sorted(committed_files - fresh_files)]
        for p in sorted((Path(tmp)).rglob("*")):
            if p.is_file():
                rel = p.relative_to(tmp)
                committed = generated / rel
                if not committed.is_file():
                    out.append(f"generated file missing: {rel.as_posix()}")
                elif committed.read_bytes().replace(b"\r\n", b"\n") != p.read_bytes().replace(b"\r\n", b"\n"):
                    out.append(f"generated file differs from a fresh build: {rel.as_posix()}")
    return out


def check_rendered(source: str, candidate: Path = RD.CANDIDATE) -> list[str]:
    out = []
    rendered = candidate / "manuscript" / "manuscript_rendered.md"
    if not rendered.is_file():
        return ["rendered manuscript missing"]
    if rendered.read_text(encoding="utf-8").replace("\r\n", "\n") != RD.render_manuscript(source):
        out.append("rendered manuscript differs from a fresh render of the source (hand edit or stale build)")
    manifest = candidate / "MANIFEST.json"
    if not manifest.is_file():
        return out + ["candidate MANIFEST.json missing"]
    files = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    present = {p.relative_to(candidate).as_posix() for p in candidate.rglob("*") if p.is_file()}
    for rel, digest in files.items():
        p = candidate / rel
        if not p.is_file():
            out.append(f"candidate file missing: {rel}")
        elif hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            out.append(f"candidate file changed after the build: {rel}")
    extra = present - set(files) - {"MANIFEST.json", *RD.HAND_WRITTEN}
    out += [f"candidate file not in the manifest: {x}" for x in sorted(extra)]
    out += [f"candidate {name} missing" for name in RD.HAND_WRITTEN if name not in present]
    for rel in files:
        src = {"manuscript/manuscript_source.md": RD.SOURCE, "manuscript/references.bib": R.BIB_PATH}.get(rel)
        if src and src.read_bytes().replace(b"\r\n", b"\n") != (candidate / rel).read_bytes().replace(b"\r\n", b"\n"):
            out.append(f"candidate copy is stale: {rel}")
    return out


def check_citations(source: str, rendered: str | None = None) -> list[str]:
    out = []
    entries = R.load()
    order = R.citation_order(S.strip_comments(source))
    out += [f"citation key not in references.bib: {k}" for k in order if k not in entries]
    out += [f"references.bib entry never cited: {k}" for k in entries if k not in order]
    if rendered is not None:
        body, _, refs = rendered.partition("\n## References\n")
        if "[@" in rendered:
            out.append("unrendered citation in the rendered manuscript")
        first = []
        for m in re.finditer(r"\[(\d[\d,–]*)\]", body):
            for part in m.group(1).split(","):
                a, _, b = part.partition("–")
                for n in range(int(a), int(b or a) + 1):
                    if n not in first:
                        first.append(n)
        if first != list(range(1, len(first) + 1)):
            out.append("citation numbers are not in order of first appearance")
        listed = re.findall(r"^(\d+)\. ", refs.split("\n## ")[0], flags=re.M)
        if [int(x) for x in listed] != list(range(1, len(order) + 1)):
            out.append("rendered reference list does not match the citation order")
    return out


def _lines_without_bibliography(text: str) -> str:
    """Drop the reference list and lines that describe the conference itself (bibliographic dates are allowed)."""
    head = text.split("\n## References\n")[0]
    tail = text.split("\n## References\n")[1].split("\n## ", 1) if "\n## References\n" in text else ["", ""]
    rest = ("\n## " + tail[1]) if len(tail) > 1 else ""
    return "\n".join(line for line in (head + rest).splitlines() if "ICFICE" not in line)


def check_privacy(texts: dict[str, str]) -> list[str]:
    out = []
    for name, text in texts.items():
        if name.endswith(".bib"):                    # bibliographic dates are allowed; comment lines are provenance
            text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))
            text = re.sub(r"(eventdate|note)\s*=\s*\{[^}]*\}", "", text)
        scan = _lines_without_bibliography(text)
        for label, rx in PRIVATE.items():
            for m in rx.finditer(scan):
                out.append(f"{name}: {label}: {m.group(0)!r}")
        for m in re.finditer(rf"\b({MONTHS})\b|\bMay\s+\d|\d\s+May\b", scan):
            out.append(f"{name}: month name: {m.group(0)!r}")
        for m in re.finditer(r"five-channel", text, re.I):
            window = text[max(0, m.start() - 20):m.end() + 60]
            if not FIVE_CHANNEL_OK.search(window.replace("\n", " ")):
                out.append(f"{name}: five-channel source outside the approved public wording")
    return out


def check_claims(source: str) -> list[str]:
    out = []
    text = _body(source)
    for sentence in _sentences(text):
        for label, rx in FORBIDDEN.items():
            if re.search(rx, sentence, re.I) and not NEGATION.search(sentence):
                out.append(f"unsupported phrase ({label}): {sentence.strip()[:140]}")
    return out


def check_placeholders(source: str) -> list[str]:
    out = [f"open blocker placeholder missing: {p}" for p in OPEN_PLACEHOLDERS if p not in source]
    secs = _sections(S.strip_comments(source))
    for name in AVAILABILITY_SECTIONS:
        body = secs.get(name)
        if body is None:
            out.append(f"back-matter section missing: {name}")
            continue
        for label, rx in RESOLVED_LOOKING.items():
            if re.search(rx, body, re.I):
                out.append(f"{name}: {label} while the blocker is open")
    return out


def check_conference() -> list[str]:
    e = R.load().get("maeng2026icfice")
    if e is None:
        return ["conference reference maeng2026icfice missing"]
    # volume, issue and pages are verified (D-056); a DOI or URL may be printed only after it is confirmed
    out = [f"conference reference has an unconfirmed field: {f}" for f in ("doi", "url")
           if e.get(f) and e.get("unconfirmed")]
    if "[PENDING" in R.render(e):
        out.append("rendered conference reference prints a pending marker (it must be a blocker, not text)")
    # the same proceedings record everywhere it is quoted (D-056); the KIICE venue, never the Special Issue page's
    v, n, pp = (R.clean(e.get(f)) for f in ("volume", "number", "pages"))
    date = R.clean(e.get("eventdate"))
    texts = {name: RD.read_source(RD.MANUSCRIPT_DIR / name)
             for name in ("manuscript.md", "COVER_LETTER_DRAFT.md", "CONFERENCE_EXTENSION_DISCLOSURE_DRAFT.md")}
    expected = {"COVER_LETTER_DRAFT.md": f"Volume {v}, Number {n}, pp. {pp}",
                "CONFERENCE_EXTENSION_DISCLOSURE_DRAFT.md": f"Vol. {v}, No. {n}, pp. {pp}",
                "manuscript.md": f"Sapporo, Japan, {date}"}
    for name, phrase in expected.items():
        if " ".join(phrase.split()) not in " ".join(texts[name].split()):
            out.append(f"{name}: conference record does not match references.bib ({phrase!r} missing)")
    for name, text in texts.items():
        if "Guam" in S.strip_comments(text):
            out.append(f"{name}: names Guam as the conference venue (the KIICE programme says Sapporo)")
    return out


def readiness_blockers(source: str, rendered: str | None) -> list[str]:
    """Items that keep the candidate from being a final submission file (--final). Not failures of the draft."""
    out = [f"bibliography pending for {k}: {v}" for k, v in R.pending_items(R.load()).items()]
    text = rendered if rendered is not None else S.strip_comments(source)
    if source:                                   # the cover letter is part of the submission
        letter = RD.read_source(RD.MANUSCRIPT_DIR / "COVER_LETTER_DRAFT.md").split("\n---\n", 1)[-1]
        out += [f"cover letter: {b}" for b in readiness_blockers("", letter)]
    seen: set[int] = set()
    for label, rx in FINAL_FORBIDDEN.items():
        for m in re.finditer(rx, text):
            if m.start() not in seen:
                seen.add(m.start())
                flat = " ".join(m.group(0).split())
                out.append(f"{label}: {flat[:90]}")
    return out


def _png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", head[16:24])


def check_figures(generated: Path = T.GENERATED, rerender: bool = False) -> list[str]:
    out = []
    for stem in FIGURES:
        p = generated / "figures" / f"{stem}.png"
        if not p.is_file():
            out.append(f"figure missing: {p.name}")
            continue
        w, _ = _png_size(p)
        if w < 1000:
            out.append(f"{p.name}: {w} px wide, below 1000 px")
    if rerender:
        from src.paper import manuscript_figures as F
        with tempfile.TemporaryDirectory() as tmp:
            F.render_all(Path(tmp))
            for stem, overlaps in F.QA.items():
                out += [f"{stem}: overlapping labels {a!r} / {b!r}" for a, b in overlaps]
                fresh = (Path(tmp) / f"{stem}.png").read_bytes()
                if (generated / "figures" / f"{stem}.png").read_bytes() != fresh:
                    out.append(f"{stem}.png differs from a fresh render (environment or data change)")
    return out


def check_formatting(source: str, rendered: str | None = None) -> list[str]:
    out = []
    body = _body(source)
    rules = {
        "unit spelling": r"% RH|degC|° C\b|deg\. ?C",
        "budget notation (write b = n)": r"\bb=\d",
        "reversed sign convention": r"adapted\s*[−-]\s*base",
        "subject count (three subjects; User02's mats are one subject)": r"\b(four|4) subjects\b|\bn\s*=\s*4\b",
    }
    for label, rx in rules.items():
        for m in re.finditer(rx, body):
            out.append(f"formatting: {label}: {m.group(0)!r}")
    if rendered is not None:
        scan = rendered.split("\n## References\n")[0]
        for m in re.finditer(r"(?<![\w.])[+−-]?\d+\.\d{3,}(?![\w.])", scan):
            out.append(f"formatting: more than two decimals in the rendered text: {m.group(0)!r}")
    return out


def public_texts(candidate: Path = RD.CANDIDATE) -> dict[str, str]:
    texts = {"manuscript.md": RD.read_source()}
    for p in sorted(candidate.rglob("*")):
        if p.is_file() and p.suffix in (".md", ".csv", ".bib", ".json"):
            texts[p.relative_to(candidate).as_posix()] = p.read_text(encoding="utf-8")
    return texts


def validate(rerender_figures: bool = False) -> dict[str, list[str]]:
    source = RD.read_source()
    rendered_path = RD.RENDERED
    rendered = rendered_path.read_text(encoding="utf-8").replace("\r\n", "\n") if rendered_path.is_file() else None
    return {
        "tokens": check_tokens(source),
        "numbers": check_numbers(source),
        "generated": check_generated(),
        "rendered": check_rendered(source),
        "citations": check_citations(source, rendered),
        "privacy": check_privacy(public_texts()),
        "claims": check_claims(source) + [f"{name}: {p}" for name in ("COVER_LETTER_DRAFT.md",
                                                                        "CONFERENCE_EXTENSION_DISCLOSURE_DRAFT.md")
                                           for p in check_claims(RD.read_source(RD.MANUSCRIPT_DIR / name))],
        "placeholders": check_placeholders(source),
        "conference": check_conference(),
        "figures": check_figures(rerender=rerender_figures),
        "formatting": check_formatting(source, rendered),
    }
