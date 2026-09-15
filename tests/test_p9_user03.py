"""P9 User03 external validation: reconciliation, canonical processing, guards and rules (synthetic data, plus a
deterministic rebuild check against the committed manifest when the raw package is present)."""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta

import numpy as np
import pytest

from src.data import p9_user03 as U
from src.data.canonical import build_stream
from src.data.raw_parser import DataRow
from src.evaluation import p9_external as E

T0 = datetime(2030, 1, 1, 22, 0, 0)


def row(ts: datetime, p: tuple, t=25, h=50, event="자리비움", fmt="ymd_hms", sep=",", line=1) -> DataRow:
    return DataRow(line_no=line, ts_raw=ts.strftime("%Y-%m-%d %H:%M:%S" if fmt == "ymd_hms" else "%Y-%m-%d %H:%M"),
                   ts_format=fmt, ts=ts, year_source="explicit", sep=sep, n_values=8, schema="p6_t_h",
                   device_id=None, pressure=tuple(p), temp=t, humid=h, event_raw=event, movement=None, control=None,
                   chunk_key=None, has_decimal=False)


def minute_pair(start: datetime, n: int, layout: str = "dot_p2_p6", **kw) -> tuple[list[DataRow], list[DataRow]]:
    """n CSV rows (minute stamps) and n TXT rows (second stamps) of the same minute with identical values."""
    csv, txt = [], []
    for i in range(n):
        p = (i + 1, 10 * i, 20, 30, 40, 4095 if i % 2 else 5)
        csv.append(row(start.replace(second=0), p, fmt="ymd_hm", line=i + 2, **kw))
        txt_p = p if layout == "comma_p1_p6" else (999,) + p[1:]          # dot layout: fused value never compared
        txt.append(row(start + timedelta(seconds=3 * i), txt_p, sep="," if layout == "comma_p1_p6" else ".",
                       line=i + 1, **kw))
    return csv, txt


def sources(csv_rows, txt_rows, layout="dot_p2_p6", night=1):
    return ([U.Source(night, f"c{night}", "c" * 64, f"c{night}.csv", "csv", csv_rows, Counter())],
            [U.Source(night, f"t{night}", "t" * 64, f"t{night}.txt", layout, txt_rows, Counter())])


def cats(minutes):
    return [m["category"] for m in minutes]


# ------------------------------------------------------------------------------------------ reconciliation rules

def test_matching_minute_is_included_with_txt_seconds_and_csv_p1():
    c, t = minute_pair(T0, 5)
    rows, minutes = U.reconcile(*sources(c, t), None)
    assert cats(minutes) == ["included"] and len(rows) == 5
    assert [r["ts"] for r in rows] == [x.ts for x in t]                # timestamps are the TXT ones, never invented
    assert [r["P"][0] for r in rows] == [x.pressure[0] for x in c]     # P1 from the CSV
    assert all(r["fsr1_source"] == "csv" and r["timestamp_source"] == "txt_second" for r in rows)
    assert all(r["dot_value_audit"] == 999 and r["dot_value_equals_csv_p1"] is False for r in rows)


def test_night_seven_layout_compares_p1_too():
    c, t = minute_pair(T0, 4, layout="comma_p1_p6")
    rows, minutes = U.reconcile(*sources(c, t, layout="comma_p1_p6"), None)
    assert cats(minutes) == ["included"] and rows[0]["fsr1_source"] == "csv_equals_txt"
    t[1] = row(t[1].ts, (77,) + t[1].pressure[1:], sep=",")
    assert cats(U.reconcile(*sources(c, t, layout="comma_p1_p6"), None)[1]) == ["value_mismatch"]


def test_count_mismatch_value_mismatch_and_single_source_minutes_are_excluded():
    c, t = minute_pair(T0, 5)
    assert cats(U.reconcile(*sources(c, t[:4]), None)[1]) == ["count_mismatch"]
    t2 = list(t)
    t2[2] = row(t2[2].ts, t2[2].pressure[:3] + (31,) + t2[2].pressure[4:], sep=".")
    assert cats(U.reconcile(*sources(c, t2), None)[1]) == ["value_mismatch"]
    t3 = list(t)
    t3[0] = row(t3[0].ts, t3[0].pressure, t=26, sep=".")
    assert cats(U.reconcile(*sources(c, t3), None)[1]) == ["value_mismatch"]      # temperature compared
    c2, t4 = minute_pair(T0 + timedelta(minutes=1), 3)
    rows, minutes = U.reconcile(*sources(c, t + t4), None)
    assert sorted(cats(minutes)) == ["included", "txt_only"] and len(rows) == 5
    rows, minutes = U.reconcile(*sources(c + c2, t), None)
    assert sorted(cats(minutes)) == ["csv_only", "included"]


def test_minute_split_across_files_is_ambiguous():
    c, t = minute_pair(T0, 4)
    cs, ts = sources(c[:2], t)
    cs.append(U.Source(2, "c2", "c" * 64, "c2.csv", "csv", c[2:], Counter()))
    assert cats(U.reconcile(cs, ts, None)[1]) == ["ambiguous_source"]


def test_decreasing_seconds_and_event_rules():
    c, t = minute_pair(T0, 3)
    t[2] = row(T0 + timedelta(seconds=1), t[2].pressure, sep=".")
    assert cats(U.reconcile(*sources(c, t), None)[1]) == ["txt_time_order_violation"]
    c, t = minute_pair(T0, 3)
    t[1] = row(t[1].ts, t[1].pressure, event="자리비움.", sep=".")
    rows, minutes = U.reconcile(*sources(c, t), None)
    assert cats(minutes) == ["included"] and minutes[0]["event_punctuation_rows"] == 1
    assert rows[1]["event_relation"] == "punctuation_only" and rows[1]["event_raw"] == "자리비움"   # CSV event kept
    t[1] = row(t[1].ts, t[1].pressure, event="우로이동", sep=".")
    assert cats(U.reconcile(*sources(c, t), None)[1]) == ["event_text_mismatch"]
    assert U.event_relation(" 자리비움 ", "자리비움") == "identical"
    assert U.event_relation("a, b", "ab") == "punctuation_only"
    assert U.event_relation("up", "down") == "different"


def test_provider_annotated_error_minute_is_excluded():
    c, t = minute_pair(T0.replace(hour=7, minute=20, second=10), 4)
    ann = {"txt_file_id": "t1", "time_of_day_from": "07:20:11", "time_of_day_to": "07:20:51"}
    assert cats(U.reconcile(*sources(c, t), ann)[1]) == ["provider_annotated_error"]
    other = {"txt_file_id": "t9", "time_of_day_from": "07:20:11", "time_of_day_to": "07:20:51"}
    assert cats(U.reconcile(*sources(c, t), other)[1]) == ["included"]


def test_no_row_is_invented_or_interpolated():
    rows, minutes = [], []
    c_all, t_all = [], []
    for k in range(6):
        c, t = minute_pair(T0 + timedelta(minutes=k), 4 + k % 3)
        if k == 2:
            t = t[:-1]                                                     # a partial minute
        c_all += c
        t_all += t
    rows, minutes = U.reconcile(*sources(c_all, t_all), None)
    txt_ts = {x.ts for x in t_all}
    assert all(r["ts"] in txt_ts for r in rows)
    assert len(rows) == sum(m["csv_rows"] for m in minutes if m["category"] == "included")
    assert "count_mismatch" in cats(minutes)


def test_reconstructed_rows_pass_through_the_canonical_builder():
    c, t = [], []
    for k in range(3):
        cc, tt = minute_pair(T0 + timedelta(minutes=k), 20)
        c += cc
        t += [row(x.ts, x.pressure, sep=".", line=x.line_no + 100 * k) for x in tt]
    c = [row(x.ts, x.pressure, fmt="ymd_hm", line=i + 2) for i, x in enumerate(c)]
    cs, ts = sources(c, t)
    rows, _ = U.reconcile(cs, ts, None)
    import yaml
    from src.data import paths
    cfg = yaml.safe_load((paths.PROJECT_ROOT / "configs" / "canonical_v1.yaml").read_text(encoding="utf-8"))
    res = build_stream(U.to_chunks(rows, {cs[0].file_id: cs[0]}), "User03", "unknown", "external_validation", False,
                       cfg)
    assert res.table.num_rows == len(rows)
    assert set(res.table.column("timestamp_resolution").to_pylist()) == {"second"}
    assert set(res.table.column("session_id").to_pylist()) == {"User03|unknown|S0001"}
    ids = res.table.column("canonical_row_id").to_pylist()
    assert set(ids) <= set(U.provenance_table(rows).column("canonical_row_id").to_pylist())


# ------------------------------------------------------------------------------------------ evaluation rules

def _summary(tm_mae, tcn_mae, r_within):
    s = [{"model": "training_mean", "config_fold": "", "target": t, "mae": tm_mae, "r_within": float("nan")}
         for t in ("temperature", "humidity")]
    s += [{"model": "raw_tcn", "config_fold": c, "target": t, "mae": tcn_mae, "r_within": r_within}
          for c in E.CONFIGS for t in ("temperature", "humidity")]
    return s


def _nights(tm_mae, tcn_mae, r, n=7):
    out = [{"model": "training_mean", "config_fold": "", "target": t, "night_index": k, "mae": tm_mae, "r": np.nan}
           for t in ("temperature", "humidity") for k in range(1, n + 1)]
    out += [{"model": "raw_tcn", "config_fold": c, "target": t, "night_index": k, "mae": tcn_mae, "r": r}
            for c in E.CONFIGS for t in ("temperature", "humidity") for k in range(1, n + 1)]
    return out


def test_interpretation_rules_follow_the_plan():
    r = E.interpretation(_summary(2.0, 1.5, 0.3), _nights(2.0, 1.5, 0.3))
    assert all(x["comparison"] == "raw_tcn_better" and x["within_night_covariation"] == "supported" for x in r)
    assert r[0]["relation_to_n3"] == "weakened" and r[0]["night_bootstrap"].startswith("not computed")
    r = E.interpretation(_summary(1.5, 2.0, 0.02), _nights(1.5, 2.0, 0.02))
    assert all(x["comparison"] == "training_mean_better" and x["within_night_covariation"] == "absent" for x in r)
    assert r[0]["relation_to_n3"] == "strengthened"
    n = _nights(1.5, 2.0, 0.02)
    for x in n:                                   # the TCN is lower on only 3 of 7 nights: not "better"
        if x["model"] == "raw_tcn" and x["night_index"] <= 3:
            x["mae"] = 1.0
    r = E.interpretation(_summary(1.8, 1.7, 0.02), n)
    assert r[0]["comparison"] == "mixed"


def test_guards_refuse_user03_in_training_and_a_foreign_scaler():
    from src.features.pressure_features import TargetScaler
    ew = E.ExternalWindows(np.zeros((2, 8, 6)), np.zeros((2, 2)), np.ones(2, bool), np.array(["a", "a"]),
                           np.array([1, 1]), np.array(["s", "s"]), np.array([0, 20]),
                           np.array([["external", "s", "s1", "normal"]] * 2),
                           np.array([["external", "s", "s1", "normal"]] * 2), "x")
    y = np.random.default_rng(0).normal(25, 1, (30, 2))
    ok = {"subject": np.repeat(["User01", "User02", "User07"], 10), "targets": y, "groups": []}
    sc = TargetScaler.fit(y, scheme="p9_external", fold="all_primary", partition="train", subjects=list(E.SOURCES))
    assert all(c["passed"] for c in E.guards(ok, ew, sc))
    bad = dict(ok, subject=np.array(["User01"] * 29 + ["User03"]))
    failed = {c["check"] for c in E.guards(bad, ew, sc) if not c["passed"]}
    assert "training_windows_are_primary_subjects_only" in failed
    foreign = TargetScaler.fit(y, scheme="x", fold="x", partition="train", subjects=["User01", "User03"])
    assert "scaler_fit_on_source_windows_only" in {c["check"] for c in E.guards(ok, ew, foreign) if not c["passed"]}


def test_constant_training_mean_has_undefined_correlations():
    y = np.random.default_rng(1).normal(25, 1, (60, 2))
    nights = np.repeat(["n1", "n2", "n3"], 20)
    rows, pn = E.metric_rows(y, np.tile([24.0, 50.0], (60, 1)), nights, np.repeat([1, 2, 3], 20), "training_mean",
                             "", "")
    assert all(np.isnan(r["r_pooled"]) and r["Q"] == 0.0 and r["R"] == pytest.approx(1.0) for r in rows)
    assert len(pn) == 2 * 3


# ------------------------------------------------------------------------------------------ real sources

def _have_raw() -> bool:
    try:
        U.resolve("rf_c72768b318", "e752e8b384b01ff1c62dcc18a4c8ceca5bee3154694c4c10fcb272811c55c5bf", U.raw_manifest())
        return U.manifest_path().is_file()
    except Exception:
        return False


@pytest.mark.skipif(not _have_raw(), reason="raw package or committed P9 manifest not available")
def test_real_rebuild_is_deterministic_and_matches_the_committed_manifest():
    res = U.build(write=False)
    man = json.loads(U.manifest_path().read_text(encoding="utf-8"))
    assert res["summary"]["coverage"] == man["coverage"]
    assert res["summary"]["reconstructed_rows"] == man["reconstructed_rows"]
    assert [s["sha256"] for s in res["summary"]["sources"]] == [s["sha256"] for s in man["sources"]]
    assert man["plan_sha256_lf"] == U.design_hashes()["plan_sha256_lf"]


def test_source_hash_mismatch_is_refused(tmp_path, monkeypatch):
    with pytest.raises(U.P9DataError):
        U.resolve("rf_c72768b318", "0" * 64, U.raw_manifest())


@pytest.mark.skipif(not U.manifest_path().is_file(), reason="P9 manifest not built")
def test_committed_p9_outputs_carry_no_date_or_foreign_subject():
    date = re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b")
    text = U.manifest_path().read_text(encoding="utf-8")
    assert not date.search(text) and "User06" not in text
    from src.data import paths
    for p in sorted((paths.PROJECT_ROOT / "paper" / "tables").glob("p9_user03_*.csv")):
        t = p.read_text(encoding="utf-8")
        assert not date.search(t) and "night_id" not in t.splitlines()[0], p.name
