"""P14 submission candidate (D-069, D-070): Figure S5 withdrawn, Option A wording, P14 checks."""
from __future__ import annotations

import inspect

import pytest

from src.data import paths
from src.paper import p13_figures as F
from src.paper import p14_validation as P


def test_figure_s5_source_data_are_not_in_the_tip():
    for rel in P.WITHDRAWN:
        assert not (paths.PROJECT_ROOT / rel).exists(), rel


def test_figure_scripts_no_longer_write_figure_s5_under_paper():
    assert inspect.signature(F.extract_figure_data).parameters["example_nights_dir"].default is None
    assert inspect.signature(F.render_all).parameters["include_example_nights"].default is False
    with pytest.raises(ValueError):
        F.render_all(paths.PROJECT_ROOT / "paper" / "tmp_never_written", include_example_nights=True)


def test_precision_rule_eta_three_decimals_mae_two():
    ok = "{{p13_table11_heater | subject_id=User01 | eta_raw_full | .3f}} {{p13_table11_heater | subject_id=User01 | mae_source_mean_common | .2f}}"
    assert P.check_precision(ok) == []
    bad = "{{p13_table11_heater | subject_id=User01 | eta_raw_full | .2f}} {{p13_table11_heater | subject_id=User01 | mae_source_mean_common | .1f}}"
    assert len(P.check_precision(bad)) == 2


def test_wording_rejects_request_based_access_and_unsupported_physics_but_not_placeholders():
    base = " ".join(P.REQUIRED) + "."
    assert P.check_wording(base) == []
    assert P.check_wording(base + " Data are available on reasonable request.")
    assert P.check_wording(base + " The body–bed interface microclimate was measured.")
    assert P.check_wording(base + " [PI DECISION: interim availability on reasonable request, and from whom.]") == []


def test_deterministic_claim_for_the_retrained_network_is_rejected():
    assert P.check_reproducibility_wording("Plain text.") == []
    bad = "The network retrained on the common endpoints was trained with deterministic settings."
    assert P.check_reproducibility_wording(bad)


def test_committed_p14_source_passes_its_text_checks():
    source = P.read_source()
    rendered = P.render(source)
    assert P.check_tokens(source) == [] and P.check_precision(source) == []
    assert P.check_wording(source) == [] and P.check_numbering(rendered) == []
    assert P.check_figure_s5(source, rendered) == []
