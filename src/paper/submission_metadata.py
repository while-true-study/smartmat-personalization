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

Two kinds of external metadata (policy: `metadata/METADATA_RECONCILIATION_GATES.md`):
- slot values (names, affiliations, ORCID, funding, dates, editor): YAML substitution only;
- answers that can change the truth of existing factual prose: reconciliation gates R1-R4. The final build needs an
  explicit author decision for each gate. The resulting edits apply only inside the gate's FACTUALLY RECONCILABLE
  regions. Every character outside them (all results, tables, figures, research questions, analyses, protocol and
  interpretation: IMMUTABLE) must stay identical to P16, which the validator checks.
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
RECONCILIATION_DOC = META / "METADATA_RECONCILIATION_GATES.md"
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
UNAVAILABLE_ALLOWED = ("M06", "M07", "M08", "M09", "M10")     # sensor items may be confirmed as unavailable
GATE_IDS = ["R1", "R2", "R3", "R4"]
GATE_FIELDS = ("trigger", "affected_locations", "current_statement", "external_evidence_required", "allowed_outcomes",
               "author_decision", "resolved_wording", "status")
RETAINED = "CURRENT WORDING RETAINED"
# FACTUALLY RECONCILABLE regions: (document, start anchor, end anchor). Everything outside them is IMMUTABLE.
REGIONS = {
    "sensor_methods": ("ms", "The temperature–humidity sensor model, its accuracy,",
                       "{{M10_HEATER_RELATIVE_PLACEMENT}}."),
    "limitation_4": ("ms", "4. **Sensor metadata.**", "physical mechanisms is made."),
    "heater_approval": ("ms", "Aggregate diagnostic results and the analysis code may be included",
                        "{{M16_HEATER_DIAGNOSTIC_APPROVAL}}."),
    "data_release": ("ms", "The released data (", "{{M16_DATA_LICENSE}} license."),
    "code_release": ("ms", "The released code (", "{{M16_CODE_LICENSE}} license."),
    "conference_note": ("ms", "**Note:** This article is a revised and expanded", "{{M05_CONFERENCE_COPYRIGHT}}"),
    "cover_reuse": ("cl", "- **Reuse:**", "with the journal results."),
}
GATE_REGIONS = {"R1": ("sensor_methods", "limitation_4"), "R2": ("heater_approval",),
                "R3": ("data_release", "code_release"), "R4": ("conference_note", "cover_reuse")}
# outcome -> "retain" (resolved_wording must be RETAINED), "edit" (edits required) or "either"
OUTCOME_RULES = {"R1-1": "retain", "R1-2": "edit", "R1-3": "edit", "R2-1": "either", "R2-2": "edit",
                 "R3-1": "retain", "R3-2": "edit", "R4-1": "retain", "R4-2": "edit"}
# Terms an edit may not introduce: sensor-position claims and heater causal or mechanism claims.
NEW_CLAIM_TERMS = re.compile(r"body[- –]bed interface|skin[- –]interface|physiological microclimate|\bcaus\w*|"
                             r"thermal mechanism|heater effect|effect of the heater", re.I)
SENSOR_KEY = next(k for k in REPLACEMENTS if k.startswith("temperature and humidity sensor"))
# R1-1 (all sensor metadata confirmed unavailable): the sensor-methods sentence goes and the P16 wording stays exactly.
AUTO_EDITS = {"R1-1": [{"region": "sensor_methods", "from": ". " + SENSOR_METHODS, "to": "."}]}
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


def item_resolved(item: dict, iid: str = "") -> bool:
    """CONFIRMED with every field and a source; or, for sensor items, UNAVAILABLE (confirmed absent) with a source."""
    if item.get("status") == "UNAVAILABLE" and iid in UNAVAILABLE_ALLOWED:
        return bool(item.get("source")) and all(v in (None, "") for v in item_fields(item).values())
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
        if not item_resolved(item, iid) or item.get("status") != "CONFIRMED":
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


# --- reconciliation gates ------------------------------------------------------------------------------------------

def _anchor(text: str) -> re.Pattern:
    return re.compile(r"\s+".join(re.escape(w) for w in text.split()))


def region_spans(text: str, doc: str) -> dict[str, tuple[int, int]]:
    """name -> (start, end) of each reconcilable region of one ready document ("ms" or "cl")."""
    out = {}
    for name, (d, start, end) in REGIONS.items():
        if d != doc:
            continue
        ms = list(_anchor(start).finditer(text))
        if len(ms) != 1:
            raise ValueError(f"region {name}: start anchor found {len(ms)} times")
        me = _anchor(end).search(text, ms[0].start())
        if not me:
            raise ValueError(f"region {name}: end anchor not found")
        out[name] = (ms[0].start(), me.end())
    return out


def gate_edits(values: dict) -> list[dict]:
    """Edits of every RESOLVED gate (the author's edits plus the automatic edit of outcome R1-1)."""
    out = []
    for gid, g in values.get("reconciliation_gates", {}).items():
        if g.get("status") != "RESOLVED":
            continue
        out += AUTO_EDITS.get((g.get("author_decision") or {}).get("outcome"), [])
        if isinstance(g.get("resolved_wording"), list):
            out += g["resolved_wording"]
    return out


def apply_edits(text: str, doc: str, edits: list[dict]) -> tuple[str, list[str]]:
    """Apply edits inside their regions only. Returns the new text and the problems (edit outside its region,
    ambiguous or missing `from` text, a new sensor-position or heater-causal term)."""
    spans = region_spans(text, doc)
    problems, pieces, pos = [], [], 0
    for name, (start, end) in sorted(spans.items(), key=lambda kv: kv[1]):
        region = text[start:end]
        for e in (e for e in edits if e.get("region") == name):
            found = list(_anchor(e["from"]).finditer(region)) if e["from"].strip() else []
            if len(found) != 1:                   # whitespace-insensitive: line breaks in the source do not matter
                problems.append(f"edit in {name}: `from` text found {len(found)} times in the region")
                continue
            m = found[0]
            new = region[:m.start()] + e["to"] + region[m.end():]
            if len(NEW_CLAIM_TERMS.findall(new)) > len(NEW_CLAIM_TERMS.findall(region)):
                problems.append(f"edit in {name}: introduces a sensor-position or heater-causal term")
                continue
            region = new
        pieces += [text[pos:start], region]
        pos = end
    pieces.append(text[pos:])
    unknown = {e.get("region") for e in edits} - set(REGIONS)
    problems += [f"edit names an unknown region: {r}" for r in sorted(unknown, key=str)]
    return "".join(pieces), problems


def immutable_problems(original: str, edited: str, doc: str) -> list[str]:
    """Every character outside the reconcilable regions is unchanged and in order (IMMUTABLE content)."""
    spans = sorted(region_spans(original, doc).values())
    outside, pos = [], 0
    for start, end in spans:
        outside.append(original[pos:start])
        pos = end
    outside.append(original[pos:])
    at = 0
    for chunk in outside:
        k = edited.find(chunk, at)
        if k < 0 or (at == 0 and k != 0):
            return [f"text outside the reconcilable regions changed near: {chunk[:60]!r}"]
        at = k + len(chunk)
    return [] if at == len(edited) else ["text appended after the last immutable chunk"]


def gate_problems(values: dict) -> list[str]:
    """Structure of every gate; for RESOLVED gates, a complete author decision consistent with the answers."""
    gates = values.get("reconciliation_gates", {})
    out = [] if list(gates) == GATE_IDS else [f"gates {list(gates)} (expected R1-R4)"]
    ms = values["manuscript"]
    for gid, g in gates.items():
        out += [f"{gid}: missing field {f}" for f in GATE_FIELDS if f not in g]
        if g.get("status") not in ("OPEN", "RESOLVED"):
            out.append(f"{gid}: status {g.get('status')!r} (OPEN or RESOLVED)")
        allowed = set((g.get("allowed_outcomes") or {}).keys())
        if allowed != {o for o in OUTCOME_RULES if o.startswith(gid + "-")}:
            out.append(f"{gid}: allowed outcomes {sorted(allowed)}")
        if g.get("status") != "RESOLVED":
            continue
        d = g.get("author_decision") or {}
        outcome, rw = d.get("outcome"), g.get("resolved_wording")
        if outcome not in allowed:
            out.append(f"{gid}: RESOLVED without an allowed outcome")
            continue
        if not d.get("decided_by") or not d.get("date") or not d.get("evidence"):
            out.append(f"{gid}: RESOLVED needs decided_by, date and evidence")
        rule = OUTCOME_RULES[outcome]
        if rule == "retain" and rw != RETAINED:
            out.append(f"{gid}: outcome {outcome} keeps the wording; resolved_wording must be {RETAINED!r}")
        if rule == "edit" and not (isinstance(rw, list) and rw):
            out.append(f"{gid}: outcome {outcome} needs the edited wording (a list of region edits)")
        if rule == "either" and not (rw == RETAINED or (isinstance(rw, list) and rw)):
            out.append(f"{gid}: resolved_wording must be {RETAINED!r} or a list of region edits")
        if isinstance(rw, list):
            out += [f"{gid}: edit outside its regions ({e.get('region')})" for e in rw
                    if e.get("region") not in GATE_REGIONS[gid]]
        sensor = [ms[i].get("status") for i in UNAVAILABLE_ALLOWED]
        if outcome == "R1-1" and any(st != "UNAVAILABLE" for st in sensor):
            out.append("R1: outcome R1-1 needs M06-M10 all UNAVAILABLE")
        if outcome == "R1-2" and not ("CONFIRMED" in sensor and "UNAVAILABLE" in sensor):
            out.append("R1: outcome R1-2 needs some of M06-M10 CONFIRMED and some UNAVAILABLE")
        if outcome == "R1-3" and any(st != "CONFIRMED" for st in sensor):
            out.append("R1: outcome R1-3 needs M06-M10 all CONFIRMED")
    return out


def reconciled(values: dict) -> tuple[str, str, list[str]]:
    """Ready manuscript and cover letter with the resolved gates' edits, and every problem found."""
    edits = gate_edits(values)
    ms0, cl0 = _strip_note(_read(READY_MS)), _read(READY_CL)
    ms, p1 = apply_edits(ms0, "ms", edits)
    cl, p2 = apply_edits(cl0, "cl", edits)
    return ms, cl, p1 + p2 + immutable_problems(ms0, ms, "ms") + immutable_problems(cl0, cl, "cl")


# --- check, preview, final ------------------------------------------------------------------------------------------

def unresolved(values: dict | None = None, credit: dict | None = None) -> list[str]:
    """Everything that blocks the final build."""
    values = values if values is not None else load_values()
    credit = credit if credit is not None else yaml.safe_load(CREDIT.read_text(encoding="utf-8"))
    out = []
    for group in ("manuscript", "cover_letter"):
        for iid, item in values[group].items():
            if not item_resolved(item, iid):
                missing = [k for k, v in item_fields(item).items() if v in (None, "")]
                out.append(f"{iid} {item['name']}: status {item.get('status')}"
                           + (f"; missing {', '.join(missing)}" if missing else "")
                           + ("" if item.get("source") else "; no source recorded"))
    if credit_sentence(credit) is None:
        out.append("CRediT input: author names or roles missing")
    for gid, g in values.get("reconciliation_gates", {}).items():
        if g.get("status") != "RESOLVED":
            out.append(f"{gid} reconciliation gate: {g.get('status')} — author decision required")
    out += gate_problems(values)
    for iid, fields in (("M14", ETHICS), ("M15", CONSENT)):
        v = str(item_fields(values["manuscript"][iid]).get("variant"))
        if values["manuscript"][iid].get("status") == "CONFIRMED" and v not in variants(fields):
            out.append(f"{iid}: variant {v!r} is not defined in {fields.name}")
    tv = token_values(values, credit)
    ms, cl, problems = reconciled(values)
    out += problems
    left = sorted({t for text in (ms, cl) for t in TOKEN.findall(substitute(text, tv))})
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
    ms, cl, problems = reconciled(values)
    if problems:
        return [], problems
    out_dir = out_dir or (FINAL_DIR if final else PREVIEW_DIR)
    written = []
    for text, name in ((ms, "manuscript_final_source.md" if final else "manuscript_preview.md"),
                       (cl, "cover_letter_final.md" if final else "cover_letter_preview.md")):
        text = substitute(text, tv)
        with open_for_write(out_dir / name, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        written.append(out_dir / name)
    return written, []


# --- dashboard ------------------------------------------------------------------------------------------------------

def status_markdown(values: dict | None = None, credit: dict | None = None) -> str:
    values = values if values is not None else load_values()
    credit = credit if credit is not None else yaml.safe_load(CREDIT.read_text(encoding="utf-8"))
    ms, cl = values["manuscript"], values["cover_letter"]
    n_ms = sum(item_resolved(i, k) for k, i in ms.items())
    n_cl = sum(item_resolved(i, k) for k, i in cl.items())
    reqs = values["requests"]
    n_req = sum(r["status"] == "ANSWERED" for r in reqs.values())
    gates = values.get("reconciliation_gates", {})
    n_gate = sum(g["status"] == "RESOLVED" for g in gates.values())
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
        f"| Reconciliation gates (author decisions) | {n_gate} / {len(gates)} resolved |",
        f"| CRediT input | {'COMPLETE' if credit_sentence(credit) else 'OPEN'} |",
        f"| Submission status | {'READY FOR FINAL BUILD' if ready else 'WAITING FOR EXTERNAL METADATA'} |",
        "", "## Items", "", "| ID | Item | Status | Requests |", "|---|---|---|---|"]
    for iid, item in {**ms, **cl}.items():
        rq = ", ".join(r for r, v in reqs.items() if v["target"] == iid)
        st = item["status"] if not item_resolved(item, iid) else f"RESOLVED ({item['status']})"
        lines.append(f"| {iid} | {item['name']} | {st} | {rq} |")
    lines += ["", "## Reconciliation gates", "",
              "Policy: `METADATA_RECONCILIATION_GATES.md`. A gate is resolved only by an explicit author decision.", "",
              "| Gate | Trigger | Status | Outcome |", "|---|---|---|---|"]
    lines += [f"| {gid} | {' '.join(str(g['trigger']).split())} | {g['status']} | "
              f"{(g.get('author_decision') or {}).get('outcome') or '—'} |" for gid, g in gates.items()]
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
        allowed = ("OPEN", "CONFIRMED", "UNAVAILABLE") if iid in UNAVAILABLE_ALLOWED else ("OPEN", "CONFIRMED")
        if item.get("status") not in allowed:
            p.append(f"{iid}: status {item.get('status')!r} (allowed: {', '.join(allowed)})")
        if item.get("status") == "UNAVAILABLE" and not item.get("source"):
            p.append(f"{iid}: UNAVAILABLE without a source")
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

    out["IMMUTABLE baseline: metadata-ready source byte-exact with P16 outside the placeholders"] = \
        equivalence_problems()
    try:
        _, _, rec = reconciled(values)
        p = rec + gate_problems(values)
    except ValueError as e:
        p = [str(e)]
    doc = RECONCILIATION_DOC.read_text(encoding="utf-8") if RECONCILIATION_DOC.is_file() else ""
    p += [f"{RECONCILIATION_DOC.name} does not define {x}" for x in [*GATE_IDS, *REGIONS, *OUTCOME_RULES]
          if x not in doc]
    out["factual reconciliation: gates well-formed, edits confined to reconcilable regions, results unchanged"] = p

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
