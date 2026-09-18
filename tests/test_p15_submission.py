"""Submission-ready candidate: placeholder whitelist, internal-note and terminology rules, package exclusions."""
from __future__ import annotations

from src.paper import p15_submission as P


def test_committed_final_source_passes_its_text_checks():
    source = P.read_source()
    assert P.check_placeholders(source) == []
    assert P.check_internal_notes(source) == []
    assert P.check_terminology(source) == []
    lo, hi = P.ABSTRACT_WORDS
    assert lo <= P.word_count(P.render(source))["abstract"] <= hi


def test_placeholders_must_be_unified_and_external():
    ok = " ".join(f"[CONFIRM BEFORE SUBMISSION: {t}]" for t in (
        "Institutional Review Board approval", "informed consent statement", "final data release scope",
        "final code release scope", "temperature and humidity sensor models, accuracy, resolution, response time, "
        "physical placement and placement relative to the heater", "final author names and order", "affiliations",
        "corresponding author and e-mail", "ORCID iDs", "CRediT author contributions", "funding statement",
        "conflicts of interest", "acknowledgments", "approval of the generative-AI disclosure",
        "conference copyright holder"))
    assert P.check_placeholders(ok) == []
    assert any("unified form" in p for p in P.check_placeholders(ok + " [FUNDING TO BE CONFIRMED BY PI]"))
    assert any("whitelist" in p for p in P.check_placeholders(ok + " [CONFIRM BEFORE SUBMISSION: new results]"))
    assert any("missing: funding" in p for p in P.check_placeholders(ok.replace("funding statement", "x funding")
                                                                     .replace("funding", "fund")))
    assert P.check_placeholders(ok + " [95 % CI] [`{{a | b=c | d | .2f}}`, `{{a | b=c | e | .2f}}`]") == []


def test_internal_notes_and_terminology_rules():
    assert P.check_internal_notes("A fourth protocol addendum (D-064) after the mock review; TODO")
    assert P.check_internal_notes("Rendered by scripts/build_p15_submission.py.") == []
    assert P.check_terminology("The values were night-centered and the behavior was labeled.")
    assert P.check_terminology("A standardised target.")
    assert P.check_terminology("Random cross-validation is optimistic; values are night-centred.") == []


def test_package_excludes_private_and_withdrawn_material():
    for rel in ("tables/p13_figure_night_series.csv", "supplementary/figures/figureS5_example_nights.png",
                "docs/DECISIONS.md", "outputs/p12_heater_diagnostic/x.csv", ".claude/settings.json",
                "data/release/public_release_v1/windows.parquet"):
        assert P.EXCLUDED_IN_PACKAGE.search(rel), rel
    assert not any(P.EXCLUDED_IN_PACKAGE.search(rel) for rel in P.expected_files(P.render()))
