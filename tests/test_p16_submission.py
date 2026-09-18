"""Final editorial candidate: scientific equivalence with P15, front matter and revision-history rules."""
from __future__ import annotations

from src.paper import p15_submission as P15
from src.paper import p16_submission as P


def test_committed_p16_source_is_editorially_equivalent_to_p15():
    source = P.read_source()
    assert P.check_equivalence(source) == []
    assert P.check_front_matter(source) == []
    assert P.check_revision_history(source) == []
    lo, hi = P.B.ABSTRACT_WORDS
    assert lo <= P.word_count(P.render(source))["abstract"] <= hi


def test_equivalence_rejects_a_new_result_token_and_changed_questions():
    source = P.read_source()
    new_tok = source + "\n{{p13_table11_heater | subject_id=User01 | mae_source_mean_common | .1f}}\n"
    assert any("not in P15" in p for p in P.check_equivalence(new_tok))
    changed = source.replace("How accurate and how systematic", "How accurate", 1)
    assert any("research questions" in p for p in P.check_equivalence(changed))


def test_front_matter_and_revision_history_rules():
    head = f"# {P.FINAL_TITLE}\n\n**Keywords:** "
    assert P.check_front_matter(head + "a; b; c\n\n")                         # too few keywords
    assert P.check_front_matter(head + "a; b; c; d; e\n\n") == []
    assert P.check_front_matter(head + "a; b; c; d; negative transfer\n\n")   # not a keyword of this study
    assert P.check_front_matter("# Old Microclimate Title\n\n**Keywords:** a; b; c; d; e\n\n")
    assert P.check_revision_history("After the internal review (P12), an addendum was written.")
    assert P.check_revision_history("Rendered by scripts/build_p16_submission.py.") == []


def test_p16_package_is_configured_separately_from_p15():
    assert P.PACKAGE != P15.PACKAGE and P.SOURCE != P15.SOURCE
    assert P15.RENDERED_NAME == "manuscript_p15_final_rendered.md"
    assert P.B.RENDERED_NAME == "manuscript_p16_final_rendered.md"
