"""Verified bibliography (paper/manuscript/references.bib): parsing, citation numbering and MDPI-style rendering.

- Citations in the Markdown source are `[@key]` or `[@key1; @key2]`. They are numbered in order of first appearance
  and printed in square brackets, e.g. [1], [2,3] or [4–6] (MDPI template).
- References follow the Applied Sciences reference formats (journal article, conference proceedings, preprint).
  Only fields present in the verified entry are printed; nothing is looked up or completed here.
- Journal names use the verified `shortjournal` field (ISO abbreviation; see the header of references.bib), or the
  full name when no abbreviation is recorded. Proceedings print the conference location and dates when recorded.
- A `pending` field (e.g. the conference proceedings pages or DOI) is not printed: an unresolved bibliographic item
  is a submission blocker (`pending_items`, docs/P8_FINAL_BLOCKERS.md), not text in the submission file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.data import paths

BIB_PATH = paths.PROJECT_ROOT / "paper" / "manuscript" / "references.bib"
CITATION = re.compile(r"\[(@[^\]]+)\]")


@dataclass(frozen=True)
class Entry:
    kind: str
    key: str
    fields: dict[str, str]

    def get(self, name: str) -> str:
        return self.fields.get(name, "")


def _read_braced(text: str, i: int) -> tuple[str, int]:
    """text[i] is '{'; return the content up to the matching '}' and the index after it."""
    depth, start = 0, i
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise ValueError("unbalanced braces in references.bib")


def parse_bib(text: str) -> list[Entry]:
    entries = []
    for m in re.finditer(r"@(\w+)\{([^,\s]+),", text):
        body, _ = _read_braced(text, text.index("{", m.start()))
        fields = {}
        for f in re.finditer(r"(\w+)\s*=\s*\{", body):
            if any(f.start() < e for _, e in fields.values()):
                continue
            value, end = _read_braced(body, f.end() - 1)
            fields[f.group(1).lower()] = (value, end)
        entries.append(Entry(m.group(1).lower(), m.group(2), {k: v for k, (v, _) in fields.items()}))
    keys = [e.key for e in entries]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate keys in references.bib")
    return entries


def load(path: Path = BIB_PATH) -> dict[str, Entry]:
    return {e.key: e for e in parse_bib(path.read_text(encoding="utf-8"))}


def clean(value: str) -> str:
    v = value.replace("\\&", "&").replace("--", "–")
    v = re.sub(r"[{}]", "", v)
    return " ".join(v.split())


def initials(given: str) -> str:
    out = []
    for token in given.split():
        parts = token.strip(".").split("-")
        out.append("-".join(p[0] + "." for p in parts if p))
    return "".join(out)


def authors(value: str) -> str:
    names = []
    for person in clean(value).split(" and "):
        last, _, given = person.partition(",")
        names.append(f"{last.strip()}, {initials(given.strip())}" if given.strip() else last.strip())
    return "; ".join(names)


def _title(entry: Entry) -> str:
    t = clean(entry.get("title"))
    return t if t.endswith(("?", "!", ".")) else t + "."


def _doi(entry: Entry) -> str:
    return f" https://doi.org/{entry.get('doi')}" if entry.get("doi") else ""


def pending_items(entries: dict[str, Entry]) -> dict[str, str]:
    """Unresolved bibliographic fields, by key (reported as blockers, never printed)."""
    return {k: clean(e.get("pending")) for k, e in entries.items() if e.get("pending")}


def render(entry: Entry) -> str:
    """One reference in the MDPI template pattern (Markdown emphasis for italics and bold)."""
    head = f"{authors(entry.get('author'))} {_title(entry)}"
    year = clean(entry.get("year"))
    if entry.kind == "article":
        s = f"{head} *{clean(entry.get('shortjournal') or entry.get('journal'))}* **{year}**"
        if entry.get("volume"):
            s += f", *{clean(entry.get('volume'))}*"
        if entry.get("pages") or entry.get("eid"):
            s += f", {clean(entry.get('pages') or entry.get('eid'))}"
        return s + "." + _doi(entry)
    if entry.kind == "inproceedings":
        book = clean(entry.get("booktitle"))
        s = f"{head} In {book if book.startswith('Proceedings') else 'Proceedings of the ' + book}"
        for f in ("address", "eventdate"):
            if entry.get(f):
                s += f", {clean(entry.get(f))}"
        if year not in book and not entry.get("eventdate"):
            s += f", {year}"
        if entry.get("pages"):
            s += f"; pp. {clean(entry.get('pages'))}"
        return s + "." + _doi(entry)
    if entry.kind == "misc" and entry.get("archiveprefix").lower() == "arxiv":
        return f"{head} *arXiv* **{year}**, arXiv:{clean(entry.get('eprint'))}."
    raise ValueError(f"no rendering rule for @{entry.kind}{{{entry.key}}}")


def citation_order(markdown: str) -> list[str]:
    order: list[str] = []
    for m in CITATION.finditer(markdown):
        for k in (x.strip().lstrip("@") for x in m.group(1).split(";")):
            if k not in order:
                order.append(k)
    return order


def _compress(nums: list[int]) -> str:
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            out.append(f"{nums[i]}–{nums[j]}")
        else:
            out.extend(str(n) for n in nums[i:j + 1])
        i = j + 1
    return "[" + ",".join(out) + "]"


def number_citations(markdown: str, order: list[str]) -> str:
    index = {k: i + 1 for i, k in enumerate(order)}
    return CITATION.sub(lambda m: _compress([index[x.strip().lstrip("@")] for x in m.group(1).split(";")]),
                        markdown)


def reference_list(order: list[str], entries: dict[str, Entry]) -> str:
    return "\n".join(f"{i}. {render(entries[k])}" for i, k in enumerate(order, start=1)) + "\n"
