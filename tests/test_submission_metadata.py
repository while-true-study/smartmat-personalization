"""Metadata-ready submission system: equivalence with P16, the final-mode guard, substitution and the CRediT formatter.

Filled values below are synthetic test strings written to a temporary copy of the YAML; the committed templates stay
open.
"""
from __future__ import annotations

import yaml

from src.paper import submission_metadata as S


def test_committed_system_passes_every_check():
    assert {k: v for k, v in S.validate().items() if v} == {}


def test_ready_manuscript_equals_p16_outside_the_placeholders():
    ready = S.expected_ready()
    assert S.PLACEHOLDER.search(ready) is None
    restored = ready
    assert len(S._segments(S.F.rendered_markdown())) == 16
    # every placeholder segment becomes exactly its token text, and nothing else changes
    rendered = S.F.rendered_markdown()
    for start, end, key in reversed(S._segments(rendered)):
        rendered = rendered[:start] + S.REPLACEMENTS[key] + rendered[end:]
    assert S.READY_NOTE + rendered == restored


def test_final_mode_blocked_while_open_and_preview_keeps_tokens(tmp_path):
    problems = S.unresolved()
    assert any(p.startswith("M01 ") for p in problems) and any(p.startswith("L04 ") for p in problems)
    written, problems = S.build(final=True, out_dir=tmp_path / "final")
    assert written == [] and problems and not (tmp_path / "final").exists()
    written, problems = S.build(final=False, out_dir=tmp_path / "preview")
    assert problems == [] and "{{M01_AUTHORS}}" in written[0].read_text(encoding="utf-8")


def _filled(tmp_path):
    values = S.load_values()
    for group in ("manuscript", "cover_letter"):
        for iid, item in values[group].items():
            if "fields" in item:
                item["fields"] = {k: f"TEST-{k}" for k in item["fields"]}
            else:
                item["value"] = f"TEST-{iid}"
            item["status"], item["source"] = "CONFIRMED", "unit test"
    values["manuscript"]["M14"]["fields"]["variant"] = "D"
    values["manuscript"]["M15"]["fields"]["variant"] = "4"
    for r in values["dependent_text_review"].values():
        r["status"], r["decision"] = "DONE", "unit test"
    credit = {"authors": [{"name": "Test Author-One", "roles": ["Conceptualization", "Software"]},
                          {"name": "Second Tester", "initials": "S.T.", "roles": ["Software"]}],
              "allowed_roles": list(S.CREDIT_ROLES)}
    vp, cp = tmp_path / "values.yaml", tmp_path / "credit.yaml"
    vp.write_text(yaml.safe_dump(values, allow_unicode=True), encoding="utf-8")
    cp.write_text(yaml.safe_dump(credit, allow_unicode=True), encoding="utf-8")
    return vp, cp


def test_final_mode_with_every_value_leaves_no_token(tmp_path):
    vp, cp = _filled(tmp_path)
    written, problems = S.build(final=True, values_path=vp, credit_path=cp, out_dir=tmp_path / "out")
    assert problems == []
    ms, cl = (p.read_text(encoding="utf-8") for p in written)
    assert not S.TOKEN.search(ms) and not S.TOKEN.search(cl)
    assert "TEST-M11" not in ms and "TEST-M16_HEATER_DIAGNOSTIC_APPROVAL" not in ms       # approvals print nothing
    assert "subject to final author and data-provider approval." in " ".join(ms.split())
    assert "Conceptualization, T.A.-O.; software, T.A.-O. and S.T." in ms
    assert "This secondary analysis was conducted under the approval granted by the Institutional Review Board of " \
           "TEST-ETHICS_INSTITUTION" in ms
    assert "TEST-L02" in cl and "TEST-M03" in cl


def test_fabricated_value_is_rejected(tmp_path, monkeypatch):
    values = S.load_values()
    values["manuscript"]["M13"]["value"] = "This research received no external funding."
    vp = tmp_path / "values.yaml"
    vp.write_text(yaml.safe_dump(values, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(S, "VALUES", vp)
    problems = S.validate()["no fabricated value (values only with CONFIRMED status and a source)"]
    assert any(p.startswith("M13:") for p in problems)
