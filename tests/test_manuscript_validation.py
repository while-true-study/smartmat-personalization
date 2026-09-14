"""P8 manuscript validator: passes on the repository and fails on injected problems."""
from __future__ import annotations

from src.paper import manuscript_validation as V
from src.paper import render as RD


def test_every_manuscript_token_resolves_with_an_allowed_precision():
    assert V.check_tokens(RD.read_source()) == []


def test_validator_flags_injected_problems():
    assert V.check_numbers("The error was 3.14 °C.")
    assert not V.check_numbers("Dropout {0.1, 0.3}; see Section 4.2.")
    assert V.check_claims("This proves that drift causes negative transfer.")
    assert not V.check_claims("The observations do not show that temporal drift causes negative transfer.")
    assert V.check_privacy({"x.md": "the night of 2025-08-25"})
    assert V.check_privacy({"x.md": "recorded in winter"})
    assert V.check_privacy({"x.md": "an auxiliary five-channel source from the old study"})
    assert not V.check_privacy({"x.md": "an auxiliary five-channel source excluded from the main six-channel "
                                        "evaluation"})
    assert V.check_formatting("with b=3 nights and 20 % RH")
    source = RD.read_source()
    assert V.check_placeholders(source.replace("[FUNDING TO BE CONFIRMED BY PI]",
                                               "This research received no external funding."))
    assert V.check_tokens(source.replace("| .2f}}", "| .4f}}", 1))


def test_repository_manuscript_passes_the_validator():
    results = V.validate()
    assert all(not v for v in results.values()), {k: v for k, v in results.items() if v}

def test_final_readiness_reports_open_placeholders_and_pending_bibliography():
    source = RD.read_source()
    blockers = V.readiness_blockers(source, RD.RENDERED.read_text(encoding="utf-8"))
    assert any(b.startswith("bibliography pending for maeng2026icfice") for b in blockers)
    assert any("[FUNDING TO BE CONFIRMED BY PI]" in b for b in blockers)
    def text_blockers(text):                  # the bibliography blocker comes from references.bib, not the text
        return [b for b in V.readiness_blockers("", text) if not b.startswith("bibliography")]

    assert text_blockers("A complete statement without placeholders.") == []
    assert text_blockers("Funding: [FUNDING TO BE CONFIRMED BY PI].")
    assert text_blockers("Status: BLOCKED")
