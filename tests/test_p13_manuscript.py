"""P13 manuscript revision: wording, abstract and numbering checks, and the committed P13 source."""
from __future__ import annotations

from src.paper import p13_validation as P


# ------------------------------------------------------------------------------------------------ manuscript checks

def test_wording_check_requires_the_fixed_sentences_and_rejects_overclaims():
    ok = " ".join(P.REQUIRED) + "."
    assert P.check_wording(ok) == []
    assert any("required" in p for p in P.check_wording("nothing"))
    bad = ok + " The thermal lag was demonstrated here. Fine-tuning converged to a constant predictor."
    labels = " ".join(P.check_wording(bad))
    assert "thermal lag" in labels and "constant convergence" in labels
    negated = ok + " This does not imply that heater activation reduced the temperature."
    assert P.check_wording(negated) == []
    assert P.check_wording(ok + " After an internal review of a draft, we added it.")          # never allowed


def test_abstract_word_count_and_numbering_helpers():
    text = "## Abstract\n\n" + " ".join(["word"] * 195) + "\n\n**Keywords:** a; b\n"
    assert P.abstract_words(text) == 195 and P.check_abstract(text) == []
    assert P.check_abstract(text.replace("word word", "word", 10))
    assert P._sequence([1, 2, 3], 3, "x") == []
    assert P._sequence([1, 3, 2], 3, "x") and P._sequence([1, 2, 2, 3], 3, "x") and P._sequence([1, 2], 3, "x")


def test_committed_p13_source_passes_its_checks():
    source = P.read_source()
    assert P.check_tokens(source) == []
    assert P.check_wording(source) == []
    assert P.check_numbering(P.render(source)) == []
    assert P.check_abstract(P.render(source)) == []


def test_three_decimals_are_reserved_for_eta_squared():
    from src.paper import sources as S
    eta = S.parse_token("p13_table11_heater | subject_id=User02 | eta_raw_full | .3f")
    key = S.parse_token("p13_summary_values | key=eta_humidity_full_three_states_max | value | .3f")
    mae = S.parse_token("p13_table11_heater | subject_id=User02 | mae_source_mean_common | .3f")
    assert P._eta_token(eta) and P._eta_token(key) and not P._eta_token(mae)
    assert any("reserved for eta squared" in p for p in P.check_tokens(
        "{{p13_table11_heater | subject_id=User02 | mae_source_mean_common | .3f}}"))
