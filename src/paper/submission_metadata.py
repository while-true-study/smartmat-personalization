"""Metadata-ready submission sources: external metadata as named tokens, filled from one YAML file.

The P16 manuscript (`paper/manuscript/manuscript_p16_final.md`, rendered in `paper/submission_p16/`) stays the
scientific source of truth and is never edited. `manuscript_metadata_ready.md` is generated from the rendered P16
text by replacing only its 16 `[CONFIRM BEFORE SUBMISSION: ...]` placeholder segments with metadata tokens
(`{{M01_AUTHORS}}` ...); the equivalence guard rebuilds it from P16 and compares byte for byte. The cover letter
has its own ready copy.

Values come from `METADATA_VALUES_TEMPLATE.yaml` (items M01-M18 and L01-L04), the CRediT input file and the ethics and
consent variant files. Nothing is filled in by this module: an item counts only when its status is CONFIRMED, every
field has a value and a source is recorded.
- preview: substitutes what is confirmed and keeps every other token visible;
- final: refuses while any item, dependent-text review or CRediT entry is open, and writes the final build sources.
Approval tokens (generative-AI disclosure, submitted-version approval, heater-diagnostic approval) record an approval
and print nothing in the manuscript.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from src.data.io_guard import open_for_write
from src.paper import final_submission as F

META = F.FINAL / "metadata"
VALUES = META / "METADATA_VALUES_TEMPLATE.yaml"
CREDIT = META / "CREDIT_INPUT_TEMPLATE.yaml"
ETHICS = META / "ETHICS_STATEMENT_VARIANTS.md"
CONSENT = META / "CONSENT_STATEMENT_VARIANTS.md"
CROSSWALK = META / "EXTERNAL_INFORMATION_CROSSWALK.md"
GENAI = META / "GENAI_FINAL_DRAFT.md"
REUSE = META / "CONFERENCE_REUSE_CHECK.md"
STATUS_FILE = META / "METADATA_STATUS.md"
READY_MS = F.FINAL / "manuscript" / "manuscript_metadata_ready.md"
READY_CL = F.FINAL / "cover_letter" / "cover_letter_metadata_ready.md"
PREVIEW_DIR = F.FINAL / "work" / "metadata_preview"          # not committed (.gitignore: work/)
FINAL_DIR = F.FINAL / "metadata_applied"

TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
PLACEHOLDER = re.compile(r"\[CONFIRM BEFORE SUBMISSION: [^\]]+\]")
M_IDS = [f"M{k:02d}" for k in range(1, 19)]
L_IDS = [f"L{k:02d}" for k in range(1, 5)]
REQUEST_IDS = [f"{g}{k:02d}" for g, n in (("A", 11), ("B", 8), ("C", 5), ("D", 4)) for k in range(1, n + 1)]
APPROVAL_TOKENS = ("M11_GENAI_ALL_AUTHOR_APPROVAL", "M12_ALL_AUTHOR_APPROVAL", "M16_HEATER_DIAGNOSTIC_APPROVAL")
GENERATED = {"M12_AUTHOR_CONTRIBUTIONS": "M12", "M14_IRB_STATEMENT": "M14", "M15_INFORMED_CONSENT": "M15"}
ETHICS_FIELDS = ("ETHICS_INSTITUTION", "ETHICS_REFERENCE_NUMBER", "ETHICS_DATE", "SECONDARY_USE_BASIS")
CREDIT_ROLES = ("Conceptualization", "Methodology", "Software", "Validation", "Formal analysis", "Investigation",
                "Resources", "Data curation", "Writing – original draft", "Writing – review & editing",
                "Visualization", "Supervision", "Project administration", "Funding acquisition")
HYPE = re.compile(r"\bnovel\b|\bfirst\b|state[- ]of[- ]the[- ]art|superior|breakthrough|\bproves?\b|"
                  r"negative transfer|available (up)?on request", re.I)

SENSOR_METHODS = (
    "Temperature and relative humidity were recorded with {{M06_SENSOR_MODEL}}, with a manufacturer-specified "
    "accuracy of {{M07_SENSOR_ACCURACY}}, a resolution of {{M08_SENSOR_RESOLUTION}} and a response time of "
    "{{M09_SENSOR_RESPONSE_TIME}}. Within the mat, the temperature–humidity sensor was located "
    "{{M10_SENSOR_PLACEMENT}}; relative to the heater, it was located {{M10_HEATER_RELATIVE_PLACEMENT}}.")
DATA_RELEASE = ("The released data ({{M16_DATA_SCOPE}}) are available at {{M16_DATA_REPOSITORY_URL}} (persistent "
                "identifier: {{M16_DATA_IDENTIFIER}}) under the {{M16_DATA_LICENSE}} license.")
CODE_RELEASE = ("The released code ({{M16_CODE_SCOPE}}) is available at {{M16_CODE_REPOSITORY_URL}} (archive "
                "identifier: {{M16_CODE_IDENTIFIER}}) under the {{M16_CODE_LICENSE}} license.")

# P16 placeholder text -> what replaces the placeholder in the metadata-ready source. The sensor placeholder closes a
# sentence ("... are not assumed here [placeholder]."), so its segment includes the space before and the full stop.
REPLACEMENTS = {
    "final author names and order": "{{M01_AUTHORS}}",
    "affiliations": "{{M02_AFFILIATIONS}}",
    "corresponding author and e-mail": "{{M03_CORRESPONDING_AUTHOR}}",
    "ORCID iDs": "{{M04_ORCID}}",
    "conference copyright holder and reuse status of the conference paper": "{{M05_CONFERENCE_COPYRIGHT}}",
    "temperature and humidity sensor models, accuracy, resolution, response time, physical placement and placement "
    "relative to the heater": ". " + SENSOR_METHODS,
    "approval of the generative-AI disclosure (this section and the Acknowledgments)":
        "{{M11_GENAI_ALL_AUTHOR_APPROVAL}}",
    "CRediT author contributions and every author's approval of the submitted version":
        "{{M12_AUTHOR_CONTRIBUTIONS}} {{M12_ALL_AUTHOR_APPROVAL}}",
    "funding statement; the conference paper's funding statement is not carried over": "{{M13_FUNDING}}",
    "Institutional Review Board approval, exemption or waiver, and secondary-use permission": "{{M14_IRB_STATEMENT}}",
    "informed consent statement": "{{M15_INFORMED_CONSENT}}",
    "final data release scope and redistribution permission, with repository, persistent identifier and data license":
        DATA_RELEASE,
    "final code release scope, with repository URL, archive identifier and code license": CODE_RELEASE,
    "data-provider approval for including the aggregate heater-diagnostic results and analysis code":
        "{{M16_HEATER_DIAGNOSTIC_APPROVAL}}",
    "acknowledgments": "{{M17_ACKNOWLEDGMENTS}}",
    "conflicts of interest, including any funder role": "{{M18_CONFLICTS_OF_INTEREST}}",
}
SENSOR_KEY = next(k for k in REPLACEMENTS if k.startswith("temperature and humidity sensor"))
READY_NOTE = ("<!-- Metadata-ready copy of the P16 manuscript, generated by scripts/apply_submission_metadata.py "
              "--generate. It differs from the rendered P16 text only at the 16 external-metadata placeholders, "
              "which are named metadata tokens filled from "
              "paper/submission_final/metadata/METADATA_VALUES_TEMPLATE.yaml. Do not edit by hand. -->\n")


# --- the metadata-ready manuscript ----------------------------------------------------------------------------------

def _flat(s: str) -> str:
    return " ".join(s.split())


def _segments(rendered: str) -> list[tuple[int, int, str]]:
    """(start, end, placeholder key) of the 16 placeholder segments in the rendered P16 text, in order."""
    out = []
    for m in PLACEHOLDER.finditer(rendered):
        key = _flat(m.group(0)[len("[CONFIRM BEFORE SUBMISSION: "):-1])
        start, end = m.start(), m.end()
        if key == SENSOR_KEY:
            if rendered[start - 1] != " " or rendered[end] != ".":
                raise ValueError("sensor placeholder is no longer at the end of its sentence")
            start, end = start - 1, end + 1
        out.append((start, end, key))
    return out


def expected_ready(rendered: str | None = None) -> str:
    """The metadata-ready source as it must be: P16 with only the placeholder segments replaced."""
    rendered = rendered if rendered is not None else F.rendered_markdown()
    parts, pos = [READY_NOTE], 0
    segs = _segments(rendered)
    if sorted(k for *_, k in segs) != sorted(REPLACEMENTS):
        raise ValueError("the P16 placeholders differ from the metadata-token map")
    for start, end, key in segs:
        parts += [rendered[pos:start], REPLACEMENTS[key]]
        pos = end
    parts.append(rendered[pos:])
    return "".join(parts)


def generate_ready() -> Path:
    with open_for_write(READY_MS, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(expected_ready())
    return READY_MS


def equivalence_problems() -> list[str]:
    """Byte-exact: the committed metadata-ready source equals P16 with only the metadata segments replaced."""
    if not READY_MS.is_file():
        return ["manuscript_metadata_ready.md missing"]
    got = READY_MS.read_text(encoding="utf-8").replace("\r\n", "\n")
    want = expected_ready()
    if got == want:
        return []
    i = next((k for k, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
    return [f"metadata-ready manuscript differs from P16 outside the metadata placeholders near: {got[i:i + 60]!r}"]


# --- values ---------------------------------------------------------------------------------------------------------

def load_values(path: Path | None = None) -> dict:
    return yaml.safe_load((path or VALUES).read_text(encoding="utf-8"))


def item_fields(item: dict) -> dict[str, object]:
    """Token or field name -> value of one item (single-token items use `token` and `value`)."""
    if "fields" in item:
        return dict(item["fields"])
    return {item["token"]: item.get("value")}


def item_resolved(item: dict) -> bool:
    return (item.get("status") == "CONFIRMED" and bool(item.get("source"))
            and all(v not in (None, "") for v in item_fields(item).values()))


def variants(path: Path) -> dict[str, str]:
    """Variant key -> statement text, from the ```text blocks under '### Variant X' headings."""
    text = path.read_text(encoding="utf-8")
    return {m.group(1): " ".join(m.group(2).split())
            for m in re.finditer(r"^### Variant (\w+)\b.*?\n```text\n(.*?)\n```", text, re.S | re.M)}


def credit_sentence(credit: dict) -> str | None:
    """MDPI Author Contributions sentence from the CRediT input, or None while any author or role is missing."""
    authors = credit.get("authors") or []
    if not authors or any(not a.get("name") or not a.get("roles") for a in authors):
        return None
    if any(r not in CREDIT_ROLES for a in authors for r in a["roles"]):
        raise ValueError("unknown CRediT role")

    def initials(a: dict) -> str:
        if a.get("initials"):
            return a["initials"]
        return "".join("-".join(p[0] + "." for p in part.split("-")) for part in a["name"].split())

    parts = []
    for role in CREDIT_ROLES:
        who = [initials(a) for a in authors if role in a["roles"]]
        if who:
            names = who[0] if len(who) == 1 else ", ".join(who[:-1]) + " and " + who[-1]
            parts.append(f"{role if not parts else role[0].lower() + role[1:]}, {names}")
    return "; ".join(parts) + "."


def token_values(values: dict, credit: dict) -> dict[str, str]:
    """Every token with a confirmed value (approval tokens map to their approval record)."""
    out: dict[str, str] = {}
    items = {**values["manuscript"], **values["cover_letter"]}
    for iid, item in items.items():
        if not item_resolved(item):
            continue
        if iid in ("M14", "M15"):
            continue
        for k, v in item_fields(item).items():
            if TOKEN.fullmatch("{{" + k + "}}"):
                out[k] = str(v)
    m12, m14, m15 = values["manuscript"]["M12"], values["manuscript"]["M14"], values["manuscript"]["M15"]
    if item_resolved(m12) and credit_sentence(credit):
        out["M12_AUTHOR_CONTRIBUTIONS"] = credit_sentence(credit)
    if item_resolved(m14):
        f = item_fields(m14)
        ethics = _fill(variants(ETHICS).get(str(f["variant"]), ""), f)
        if ethics:
            out["M14_IRB_STATEMENT"] = ethics
        if item_resolved(m15):
            consent = _fill(variants(CONSENT).get(str(item_fields(m15)["variant"]), ""), f)
            if consent:
                out["M15_INFORMED_CONSENT"] = consent
    return out


def _fill(text: str, fields: dict) -> str:
    return TOKEN.sub(lambda m: str(fields.get(m.group(1), m.group(0))), text) if text else ""


def substitute(text: str, values: dict[str, str]) -> str:
    """Replace known tokens; an approval token with a confirmed approval prints nothing (with its leading space)."""
    for tok in APPROVAL_TOKENS:
        if tok in values:
            text = re.sub(r" ?\{\{" + tok + r"\}\}", "", text)
    return TOKEN.sub(lambda m: values.get(m.group(1), m.group(0)), text)


# --- check, preview, final ------------------------------------------------------------------------------------------

def unresolved(values: dict | None = None, credit: dict | None = None) -> list[str]:
    """Everything that blocks the final build."""
    values = values if values is not None else load_values()
    credit = credit if credit is not None else yaml.safe_load(CREDIT.read_text(encoding="utf-8"))
    out = []
    for group in ("manuscript", "cover_letter"):
        for iid, item in values[group].items():
            if not item_resolved(item):
                missing = [k for k, v in item_fields(item).items() if v in (None, "")]
                out.append(f"{iid} {item['name']}: status {item.get('status')}"
                           + (f"; missing {', '.join(missing)}" if missing else "")
                           + ("" if item.get("source") else "; no source recorded"))
    if credit_sentence(credit) is None:
        out.append("CRediT input: author names or roles missing")
    for rid, review in values.get("dependent_text_review", {}).items():
        if review.get("status") != "DONE":
            out.append(f"{rid} dependent-text review: {review.get('status')} — {review['text'][:70]}…")
    for iid, fields in (("M14", ETHICS), ("M15", CONSENT)):
        v = str(item_fields(values["manuscript"][iid]).get("variant"))
        if values["manuscript"][iid].get("status") == "CONFIRMED" and v not in variants(fields):
            out.append(f"{iid}: variant {v!r} is not defined in {fields.name}")
    tv = token_values(values, credit)
    left = sorted({t for src in (READY_MS, READY_CL) for t in TOKEN.findall(substitute(_read(src), tv))})
    out += [f"token without a confirmed value: {{{{{t}}}}}" for t in left]
    return out


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8").replace("\r\n", "\n")


def _strip_note(text: str) -> str:
    return text.split("\n", 1)[1] if text.startswith("<!-- Metadata-ready") else text


def build(final: bool, values_path: Path | None = None, credit_path: Path | None = None,
          out_dir: Path | None = None) -> tuple[list[Path], list[str]]:
    """Write the manuscript and cover-letter build sources. Final mode writes nothing while anything is unresolved."""
    values = load_values(values_path)
    credit = yaml.safe_load((credit_path or CREDIT).read_text(encoding="utf-8"))
    problems = unresolved(values, credit) if final else []
    if problems:
        return [], problems
    tv = token_values(values, credit)
    out_dir = out_dir or (FINAL_DIR if final else PREVIEW_DIR)
    written = []
    for src, name in ((READY_MS, "manuscript_final_source.md" if final else "manuscript_preview.md"),
                      (READY_CL, "cover_letter_final.md" if final else "cover_letter_preview.md")):
        text = substitute(_strip_note(_read(src)), tv)
        with open_for_write(out_dir / name, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        written.append(out_dir / name)
    return written, []


# --- dashboard ------------------------------------------------------------------------------------------------------

def status_markdown(values: dict | None = None, credit: dict | None = None) -> str:
    values = values if values is not None else load_values()
    credit = credit if credit is not None else yaml.safe_load(CREDIT.read_text(encoding="utf-8"))
    ms, cl = values["manuscript"], values["cover_letter"]
    n_ms = sum(item_resolved(i) for i in ms.values())
    n_cl = sum(item_resolved(i) for i in cl.values())
    reqs = values["requests"]
    n_req = sum(r["status"] == "ANSWERED" for r in reqs.values())
    reviews = values.get("dependent_text_review", {})
    n_rev = sum(r["status"] == "DONE" for r in reviews.values())
    ready = not unresolved(values, credit)
    lines = [
        "# Metadata status", "",
        "Generated by `python scripts/apply_submission_metadata.py --status` from `METADATA_VALUES_TEMPLATE.yaml`.",
        "Update the YAML when an answer arrives, then regenerate this file.", "",
        "| Area | Status |", "|---|---|",
        "| Scientific manuscript | FROZEN (P16, source commit 62b1618) |",
        "| Submission formatting | COMPLETE |",
        "| Visual QA | PASS — 180 dpi |",
        f"| Manuscript metadata | {n_ms} / {len(ms)} items resolved |",
        f"| Cover letter | {n_cl} / {len(cl)} external items resolved |",
        f"| External requests | {n_req} / {len(reqs)} answered |",
        f"| Dependent-text reviews | {n_rev} / {len(reviews)} done |",
        f"| CRediT input | {'COMPLETE' if credit_sentence(credit) else 'OPEN'} |",
        f"| Submission status | {'READY FOR FINAL BUILD' if ready else 'WAITING FOR EXTERNAL METADATA'} |",
        "", "## Items", "", "| ID | Item | Status | Requests |", "|---|---|---|---|"]
    for iid, item in {**ms, **cl}.items():
        rq = ", ".join(r for r, v in reqs.items() if v["target"] == iid)
        lines.append(f"| {iid} | {item['name']} | {'RESOLVED' if item_resolved(item) else item['status']} | {rq} |")
    lines += ["", "## Dependent-text reviews", "", "| ID | Status | Text to review when the answer arrives |",
              "|---|---|---|"]
    lines += [f"| {rid} | {r['status']} | {r['text']} |" for rid, r in reviews.items()]
    return "\n".join(lines) + "\n"


def write_status() -> Path:
    with open_for_write(STATUS_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(status_markdown())
    return STATUS_FILE


# --- GenAI draft ----------------------------------------------------------------------------------------------------

def genai_paragraphs() -> tuple[str, str]:
    """The P16 Section 3.8 paragraph and the generative-AI paragraph of the Acknowledgments, verbatim."""
    md = F.rendered_markdown()
    sec = md.split("### 3.8. Use of Generative AI", 1)[1].split("\n## ", 1)[0]
    s38 = next(p for p in sec.split("\n\n") if p.strip() and not p.strip().startswith("[CONFIRM"))
    ack = md.split("## Acknowledgments", 1)[1].split("\n## ", 1)[0]
    a = next(p for p in ack.split("\n\n") if p.strip().startswith("During the preparation"))
    return _flat(s38), _flat(a)


# --- validation -----------------------------------------------------------------------------------------------------

def crosswalk_rows() -> list[tuple[str, str]]:
    return re.findall(r"^\| ([A-D]\d\d) \| [^|]+ \| [^|]+ \| ((?:M|L)\d\d) \| .* \| OPEN \|$",
                      CROSSWALK.read_text(encoding="utf-8"), re.M)


def validate() -> dict[str, list[str]]:
    values = load_values()
    credit = yaml.safe_load(CREDIT.read_text(encoding="utf-8"))
    ms, cl = values["manuscript"], values["cover_letter"]
    out: dict[str, list[str]] = {}

    p = [] if list(ms) == M_IDS else [f"manuscript items {list(ms)}"]
    p += [] if list(cl) == L_IDS else [f"cover-letter items {list(cl)}"]
    for iid, item in {**ms, **cl}.items():
        p += [f"{iid}: missing {k}" for k in ("name", "status", "source") if k not in item]
        if "fields" not in item and not ("token" in item and "value" in item):
            p.append(f"{iid}: needs token and value, or fields")
    out["M01-M18 and L01-L04 defined"] = p

    rows = crosswalk_rows()
    p = [] if [r for r, _ in rows] == REQUEST_IDS else [f"crosswalk requests {[r for r, _ in rows]}"]
    mapped = {t for _, t in rows}
    p += [f"not mapped: {i}" for i in M_IDS + L_IDS if i not in mapped]
    reqs = values["requests"]
    p += [] if list(reqs) == REQUEST_IDS else ["YAML requests differ from A01-D04"]
    p += [f"{r}: YAML target {reqs[r]['target']} differs from crosswalk {t}" for r, t in rows
          if r in reqs and reqs[r]["target"] != t]
    out["28 requests mapped (crosswalk and YAML agree)"] = p

    defined: list[str] = []
    for iid, item in {**ms, **cl}.items():
        if iid not in ("M14", "M15"):                     # variant fields, not manuscript tokens
            defined += [k for k in item_fields(item) if TOKEN.fullmatch("{{" + k + "}}")]
    defined += list(GENERATED)
    used = {t for src in (READY_MS, READY_CL) for t in TOKEN.findall(_read(src))}
    p = [f"duplicate token definition: {t}" for t in sorted({t for t in defined if defined.count(t) > 1})]
    p += [f"unknown token in a ready source: {t}" for t in sorted(used - set(defined))]
    p += [f"defined token never used: {t}" for t in sorted(set(defined) - used)]
    for vfile, allowed in ((ETHICS, set(ETHICS_FIELDS)), (CONSENT, set(ETHICS_FIELDS))):
        v = variants(vfile)
        p += [f"{vfile.name}: unknown placeholder {t}" for text in v.values() for t in TOKEN.findall(text)
              if t not in allowed]
    p += [] if sorted(variants(ETHICS)) == list("ABCDE") else [f"ethics variants {sorted(variants(ETHICS))}"]
    p += [] if sorted(variants(CONSENT)) == ["1", "2", "3", "4"] else [f"consent variants {sorted(variants(CONSENT))}"]
    out["tokens: none unknown, none duplicated, every one used"] = p

    p = []
    for iid, item in {**ms, **cl}.items():
        filled = [k for k, v in item_fields(item).items() if v not in (None, "")]
        if filled and not (item.get("status") == "CONFIRMED" and item.get("source")):
            p.append(f"{iid}: value without CONFIRMED status and source ({', '.join(filled)})")
        if item.get("status") not in ("OPEN", "CONFIRMED"):
            p.append(f"{iid}: status {item.get('status')!r}")
    if [a for a in credit.get("authors", []) if a.get("name") or a.get("roles")] and \
            not all(i.get("status") == "CONFIRMED" for i in (ms["M01"], ms["M12"])):
        p.append("CRediT input filled while M01/M12 are not confirmed")
    if list(credit.get("allowed_roles", [])) != list(CREDIT_ROLES):
        p.append("CRediT allowed roles differ from the 14 CRediT terms")
    reuse = REUSE.read_text(encoding="utf-8")
    p += [f"conference reuse check: row not OPEN: {r[:50]}" for r in re.findall(r"^\| \d+ \|.*$", reuse, re.M)
          if not r.rstrip().endswith("| OPEN |")]
    out["no fabricated value (values only with CONFIRMED status and a source)"] = p

    blocked = unresolved(values, credit)
    written, problems = build(final=True) if blocked else ([], ["(nothing open)"])
    out["final mode blocked while metadata is open"] = [] if (blocked and not written and problems) else \
        ["final mode would build although metadata is open"] if blocked else []

    out["P16 scientific equivalence (byte-exact outside the metadata placeholders)"] = equivalence_problems()

    cl_text = _read(READY_CL)
    p = [f"cover letter: overstated or disallowed wording {m.group(0)!r}"
         for m in HYPE.finditer(cl_text.split("\n---\n", 1)[-1])]
    p += [] if F.title() in _flat(cl_text) else ["cover letter: final title missing"]
    p += [f"cover letter: bracketed placeholder left: {m.group(0)[:40]}" for m in PLACEHOLDER.finditer(cl_text)]
    s38, ack = genai_paragraphs()
    g = _flat(GENAI.read_text(encoding="utf-8"))
    p += [] if s38 in g and ack in g and "{{M11_GENAI_ALL_AUTHOR_APPROVAL}}" in g else \
        ["GENAI_FINAL_DRAFT.md does not carry the P16 wording verbatim with the approval token"]
    p += [] if _read(STATUS_FILE) == status_markdown(values, credit) else \
        ["METADATA_STATUS.md is out of date (run --status)"]
    out["cover letter, GenAI draft and status dashboard"] = p
    return out
