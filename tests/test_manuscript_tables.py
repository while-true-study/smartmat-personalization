"""P8 manuscript tables: every printed number is a formatted frozen cell; no calendar date leaves the repository."""
from __future__ import annotations

import re

from src.paper import manuscript_tables as T
from src.paper import sources as S


def test_fmt_uses_typographic_minus_and_parse_inverts_it():
    assert S.fmt("-5.0603", "+.2f") == "−5.06"
    assert S.fmt("3.1", "+.1f") == "+3.1"
    assert S.fmt("289437", ",d") == "289,437"
    assert S.parse_number("−5.06") == -5.06


def test_token_parsing_and_resolution():
    tok = S.parse_token("p3_primary_summary | model=tcn_raw, target=temperature, metric=mae | User02 | .2f")
    assert tok.kind == "value" and tok.filters["model"] == "tcn_raw"
    assert S.resolve(tok) == S.fmt(S.cell("p3_primary_summary", "User02", model="tcn_raw", target="temperature",
                                          metric="mae"), ".2f")
    assert S.resolve(S.parse_token("COUNT:p6_level_mismatch_consistency | consistent=True")).isdigit()
    assert S.parse_token("TABLE:table2_strict_loso").kind == "table"


def test_main_tables_trace_every_number_to_a_frozen_cell():
    for t in T.build_main():
        assert T.check_traceable(t) == []
        # every numeric cell except the budget labels of Table 5 declares its frozen source cells
        untraced = [c.text for r in t.rows for c in r
                    if re.fullmatch(r"[+−\-\d.,±/()\[\] ]*\d[+−\-\d.,±/()\[\] ]*", c.text) and not c.sources
                    and not (t.number == 5 and c.text in T.ADAPT_BUDGETS)]
        assert untraced == [], (t.number, untraced)


def test_traceability_check_catches_a_hand_typed_number():
    t = T.table2()
    t.rows[0][3] = T.Cell("9.99", t.rows[0][3].sources, t.rows[0][3].values)
    assert T.check_traceable(t)


def test_table1_counts_user02_as_one_subject():
    t1 = T.table1()
    assert [r[0].text for r in t1.rows] == ["User01", "User02", "User07"]
    assert "never counted as two subjects" in t1.notes[0]


def test_table2_shows_the_temperature_training_mean_advantage():
    t2 = T.table2()
    assert "temperature in 3 of 3 subjects" in t2.notes[0]
    assert T.MEAN_LABEL in t2.header


def test_table3_is_marked_secondary():
    assert T.table3().notes[0].startswith("Secondary analysis")


def test_table4_defines_gain_and_negative_transfer():
    notes = " ".join(T.table4().notes)
    assert "G_b = (MAE_0 − MAE_b) / MAE_0" in notes and "negative transfer" in notes


def test_table5_states_sign_and_no_population_significance():
    t5 = T.table5()
    assert len(t5.rows) == 24
    notes = " ".join(t5.notes)
    assert "ΔMAE > 0 means improvement" in notes and "not population-level statistical significance" in notes


def test_supplementary_tables_replace_calendar_dates_by_ordinals():
    cols, _ = T.public_rows("p5_budget_counts")
    assert {"adaptation_first_night", "adaptation_last_night", "buffer_night"} <= set(cols)
    assert "adaptation_first" not in cols
    cols, _ = T.public_rows("p6_level_mismatch_trajectory")
    assert "night_id" not in cols and "night_ordinal" in cols
    for _, _, names in T.SUPPLEMENT:
        for name in names:
            _, rws = T.public_rows(name)
            assert not any(T.DATE.search(v) for r in rws for v in r.values()), name
    assert not T.DATE.search(T.p7_reproduction_record())


def test_committed_generated_tables_equal_a_fresh_export(tmp_path):
    T.export(tmp_path)
    for p in sorted(tmp_path.rglob("*")):
        if p.is_file():
            committed = T.GENERATED / p.relative_to(tmp_path)
            assert committed.is_file(), committed
            assert committed.read_bytes().replace(b"\r\n", b"\n") == p.read_bytes().replace(b"\r\n", b"\n"), p.name
