"""Public-release reproduction: public gate, public session, public mode and the table comparison (synthetic data)."""
from __future__ import annotations

import numpy as np
import pytest

from src.data import public_release as R
from src.evaluation import leakage as L
from src.evaluation import p3_loso as P3
from src.evaluation import p5_personalization as P5
from src.evaluation import p6_robustness as P6
from src.evaluation import public_reproduction as PR
from src.features.pressure_features import RAW_FEATURES
from tests.test_public_release import build_into


def loso_ctx(fd, **kw) -> L.RunContext:
    tr = fd.labelled & (fd.partition == "train")
    te = fd.labelled & (fd.partition == "test")
    args = {"input_features": list(RAW_FEATURES), "selection_subjects": [],
            "fit_records": [{"transform": "target_zscore", "partition": "train", "subjects": fd.train_subjects}],
            "window_groups": fd.window_groups(tr | te)} | kw
    return L.RunContext("loso", fold=fd.fold, **args)


def test_public_gate_passes_on_a_release_and_writes_its_report(tmp_path):
    out, *_ = build_into(tmp_path)
    rel = R.PublicRelease(out)
    sess = PR.PublicSession(echo=False, release=rel)
    fd = sess.fold(1)
    rep, ident = sess.gate(tmp_path / "run", loso_ctx(fd))
    assert rep.passed and len(rep.checks) == 15
    assert ident["data_source"] == R.RELEASE_VERSION
    assert (tmp_path / "run" / "leakage_check.json").exists()
    assert sess.windows("User02", 3) is sess.windows("User02", 3)
    with pytest.raises(PR.PublicModeError):
        sess.rows()


def test_public_gate_fails_closed(tmp_path):
    out, *_ = build_into(tmp_path)
    rel = R.PublicRelease(out)
    sess = PR.PublicSession(echo=False, release=rel)
    fd = sess.fold(1)
    with pytest.raises(L.LeakageGateError, match="fits_training_partition_only"):
        sess.gate(tmp_path / "a", loso_ctx(fd, fit_records=[{"transform": "target_zscore", "partition": "train",
                                                             "subjects": [fd.held_out]}]))
    with pytest.raises(L.LeakageGateError, match="no_calendar_or_identity_inputs"):
        sess.gate(tmp_path / "b", loso_ctx(fd, input_features=[*RAW_FEATURES, "night_ordinal"]))
    p = out / "splits" / "v1.0_loso" / "outer_folds.csv"
    p.write_text(p.read_text(encoding="utf-8").replace(",test,", ",train,", 1), encoding="utf-8")
    with pytest.raises(R.ReleaseError):
        R.PublicRelease(out)
    unverified = R.PublicRelease(out, verify=False)
    rep = PR.public_gate(unverified, PR.session_attributes(unverified.w), loso_ctx(fd))
    bad = {c.check for c in rep.failures()}
    assert {"release_files_match_manifest", "outer_loso_three_folds_disjoint"} <= bad


def test_public_mode_repoints_and_restores(tmp_path):
    from src.evaluation import canonical_input
    out, *_ = build_into(tmp_path)
    rel = R.PublicRelease(out)
    root = tmp_path / "repro"
    default_run_root, default_plan = P3.run_root(), P5.plan_yaml()
    with PR.public_mode(rel, root):
        assert P3.run_root() == root / "outputs" / "runs" / "p3"
        assert P5.split_root() == out / "splits" and P5.plan_yaml() == out / "p5_plan_public.yaml"
        assert P6.tables_dir() == root / "paper" / "tables"
        assert isinstance(P5.P5Session(echo=False), PR.PublicSession)
        assert P5.load_manifest()["files"] == {k: {"sha256": v} for k, v in rel.manifest["split_sha256"].items()}
        assert P3.frozen_inputs()["data_source"] == R.RELEASE_VERSION
        assert P5.plan_commit().endswith(rel.manifest["artifacts_sha256"]["p5_plan_public.yaml"])
        for fn in (canonical_input.load_primary, canonical_input.verify_canonical, P3.verify_canonical):
            with pytest.raises(PR.PublicModeError):
                fn()
        ev = P6.heater_events("User02")
        assert sorted(ev) == ["22480", "22482"] and all(np.all(np.diff(t) >= 0) for t, _ in ev.values())
        (out / "p5_plan_public.yaml").write_text("tampered: true\n", encoding="utf-8")
        with pytest.raises(P5.PlanNotFrozenError):
            P5.plan_commit()
    assert P3.run_root() == default_run_root and P5.plan_yaml() == default_plan
    assert not isinstance(P5.P5Session(echo=False), PR.PublicSession)


def write(p, text):
    p.write_bytes(text.encode("utf-8"))
    return p


def test_compare_table_allows_only_a_consistent_night_day_shift(tmp_path):
    shifts: dict[str, int] = {}
    head = "subject_id,night_id,nights,mae\n"
    a = write(tmp_path / "a.csv", head + "User01,2026-01-10,2026-01-10;2026-01-11,0.5\nUser02,2026-02-01,,0.25\n")
    b = write(tmp_path / "b.csv", head + "User01,D0003,D0003;D0004,0.5\nUser02,D0001,,0.25\n")
    c = PR.compare_table(a, b, shifts)
    assert c["passed"] and not c["identical_bytes"] and c["night_key_cells"] == 3 and sorted(shifts) == ["User01",
                                                                                                       "User02"]
    bad_shift = write(tmp_path / "c.csv", head + "User01,D0003,D0003;D0005,0.5\nUser02,D0001,,0.25\n")
    assert not PR.compare_table(a, bad_shift, dict(shifts))["passed"]
    bad_value = write(tmp_path / "d.csv", head + "User01,D0003,D0003;D0004,0.5000000001\nUser02,D0001,,0.25\n")
    r = PR.compare_table(a, bad_value, dict(shifts))
    assert not r["passed"] and r["mismatched_cells"] == 1 and "mae" in r["problems"][0]
    assert not PR.compare_table(a, write(tmp_path / "e.csv", head), {})["passed"]
    assert not PR.compare_table(a, tmp_path / "missing.csv", {})["passed"]
    same = write(tmp_path / "f.csv", a.read_bytes().decode("utf-8").replace("\n", "\r\n"))
    assert PR.compare_table(a, same, {})["identical_bytes"]
    later = write(tmp_path / "g.csv", head + "User01,D0002,D0002;D0003,0.5\nUser02,D0001,,0.25\n")
    assert not PR.compare_table(a, later, shifts)["passed"]                       # shift shared across tables
