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
    decision = {"decided_by": "unit test", "date": "2026-01-01", "evidence": "unit test"}
    gates = values["reconciliation_gates"]
    gates["R1"].update(status="RESOLVED", author_decision={"outcome": "R1-3", **decision}, resolved_wording=[
        {"region": "sensor_methods", "from": "The temperature–humidity sensor model, its accuracy, resolution and "
         "response time, and its position relative to the body and the heater are not documented in the delivered "
         "data and are not assumed here. ", "to": ""},
        {"region": "limitation_4",
         "from": "The temperature–humidity sensor model, accuracy, resolution, response time and placement were not "
                 "documented; the", "to": "The"}])
    for gid, outcome in (("R2", "R2-1"), ("R3", "R3-1"), ("R4", "R4-1")):
        gates[gid].update(status="RESOLVED", author_decision={"outcome": outcome, **decision},
                          resolved_wording=S.RETAINED)
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
    flat = " ".join(ms.split())
    assert "are not documented in the delivered data" not in flat and "were not documented" not in flat
    assert "recorded with TEST-M06, with a manufacturer-specified accuracy of TEST-M07" in flat
    assert "4. **Sensor metadata.** The targets are treated as mat-level measurements" in flat


def test_fabricated_value_is_rejected(tmp_path, monkeypatch):
    values = S.load_values()
    values["manuscript"]["M13"]["value"] = "This research received no external funding."
    vp = tmp_path / "values.yaml"
    vp.write_text(yaml.safe_dump(values, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(S, "VALUES", vp)
    problems = S.validate()["no fabricated value (values only with CONFIRMED status and a source)"]
    assert any(p.startswith("M13:") for p in problems)


def _gate_case(tmp_path, mutate):
    vp, cp = _filled(tmp_path)
    values = yaml.safe_load(vp.read_text(encoding="utf-8"))
    mutate(values)
    vp.write_text(yaml.safe_dump(values, allow_unicode=True), encoding="utf-8")
    return S.build(final=True, values_path=vp, credit_path=cp, out_dir=tmp_path / "out")


def test_r1_all_unavailable_keeps_the_p16_wording(tmp_path):
    def mutate(v):
        for iid in S.UNAVAILABLE_ALLOWED:
            item = v["manuscript"][iid]
            item["status"], item["source"] = "UNAVAILABLE", "unit test: provider has no datasheet"
            if "fields" in item:
                item["fields"] = {k: None for k in item["fields"]}
            else:
                item["value"] = None
        v["reconciliation_gates"]["R1"]["author_decision"]["outcome"] = "R1-1"
        v["reconciliation_gates"]["R1"]["resolved_wording"] = S.RETAINED
    written, problems = _gate_case(tmp_path, mutate)
    assert problems == []
    flat = " ".join(written[0].read_text(encoding="utf-8").split())
    p16 = " ".join(S.F.rendered_markdown().split())
    sentence = "are not documented in the delivered data and are not assumed here."
    assert sentence in flat and sentence[:-1] + " [CONFIRM BEFORE SUBMISSION: temperature and humidity sensor" in p16
    assert "Temperature and relative humidity were recorded" not in flat
    assert "were not documented; the targets are treated as mat-level measurements" in flat


def test_gates_block_final_until_resolved_and_confine_edits(tmp_path):
    def open_gate(v):
        v["reconciliation_gates"]["R4"]["status"] = "OPEN"
    _, problems = _gate_case(tmp_path, open_gate)
    assert any(p.startswith("R4 reconciliation gate: OPEN") for p in problems)

    def no_evidence(v):
        v["reconciliation_gates"]["R2"]["author_decision"]["evidence"] = None
    _, problems = _gate_case(tmp_path, no_evidence)
    assert any("R2: RESOLVED needs decided_by, date and evidence" in p for p in problems)

    def wrong_region(v):
        v["reconciliation_gates"]["R1"]["resolved_wording"].append(
            {"region": "data_release", "from": "The released data", "to": "Data"})
    _, problems = _gate_case(tmp_path, wrong_region)
    assert any("R1: edit outside its regions (data_release)" in p for p in problems)

    def result_edit(v):               # a result sentence is not in any region, so the edit cannot find it
        v["reconciliation_gates"]["R1"]["resolved_wording"].append(
            {"region": "limitation_4", "from": "unweighted means 3.33 versus 3.05", "to": "3.00 versus 3.05"})
    _, problems = _gate_case(tmp_path, result_edit)
    assert any("`from` text found 0 times" in p for p in problems)

    def new_claim(v):
        v["reconciliation_gates"]["R1"]["resolved_wording"].append(
            {"region": "limitation_4", "from": "mat-level measurements",
             "to": "physiological microclimate measurements"})
    _, problems = _gate_case(tmp_path, new_claim)
    assert any("introduces a sensor-position or heater-causal term" in p for p in problems)


def test_immutable_guard_detects_a_change_outside_the_regions():
    ms = S._strip_note(S._read(S.READY_MS))
    assert S.immutable_problems(ms, ms, "ms") == []
    changed = ms.replace("| 3.12 |", "| 3.13 |", 1)                       # a Table 2 value
    assert changed != ms and S.immutable_problems(ms, changed, "ms")
