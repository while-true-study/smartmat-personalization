"""P0 analysis A11 — subject / device / temporal coverage and confounding audit. Read-only on raw data.

One coverage view of who was recorded when, on which device, sensor phase (D-019), schema, log container
and sampling regime; overlap between subjects on actually recorded days and minutes; subject x season /
device / domain confounding; structural eligibility of the provisional primary cohort. Analysis-eligible
sources only (D-017); excluded, quarantined and restricted sources appear in the table with their status but
are not loaded. Nothing is removed, resampled, split or modelled.

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/coverage/:
  canonical_coverage.csv          one row per source x sensor phase slice, plus subject / device / phase domains
  monthly_subject_coverage.csv    domain x month: recording days, active hours, valid-target rows (+ hours matrix)
  subject_temporal_overlap.csv    every pair of domains: shared days / weeks / months / recording hours
  device_subject_matrix.csv       device evidence per source and hand-over gaps between subjects
  confounding_matrix.csv          domain x (season, quarter, month, sensor phase, device, schema, container, regime)
  primary_cohort_eligibility.csv  structural checks and status per primary subject
  schema_firmware_events.csv      boundaries and shifts on the timeline, with a status that is never mixed
  figures/coverage_timeline.png   QA figure
  coverage_run_meta.json
"""
from __future__ import annotations

import platform
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.coverage import (  # noqa: E402
    DAY_S, USABLE_DAY_MIN, check, chronological_capacity, coverage_summary, daily_labels, daily_step_regime,
    day_of, eligibility, minutes, month_of, month_range, monthly_coverage, overlap, quarter_of, regime_runs,
    season_of,
)
from src.data.duplicates import overlapping_file_pairs, row_keys, subject_device_groups, upload_copy_mask  # noqa: E402
from src.data.io_guard import open_for_write, write_csv, write_json  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.pressure_quality import pressure_matrix, pressure_policy_masks  # noqa: E402
from src.data.provenance import SourceData  # noqa: E402
from src.data.raw_parser import parse_file  # noqa: E402
from src.data.sensor_phase import assign_phase  # noqa: E402
from src.data.subject_mapping import resolve_source, sensor_phase_spec, sources  # noqa: E402
from src.data.target_quality import channel_states, channel_values  # noqa: E402

PRIMARY_SUBJECTS = ("User01", "User02", "User07")
SCHEMA_NAMES = {0: "p6_t_h", 1: "p6_t_h_device_column", 2: "nonstandard"}
MIN_HOURS, MIN_NIGHTS, MIN_TARGET_COVERAGE, MIN_SPLIT_NIGHTS = 100, 20, 0.95, 7   # structural thresholds
P1_ANOMALY_22482 = datetime(2026, 8, 20)                                           # A9 / OPEN-19 marker
# Structural caveats already on record (DECISIONS.md); A11 only lists them, it does not re-derive them.
KNOWN_CAVEATS = {
    "User01": ["two sensor phases s1/s2 (D-019): phase-aware spans and reporting needed (OPEN-11)",
               "acquisition changes inside s1: 2025-12-17 activity shift, 2026-01 sampling episode (OPEN-21)",
               "device ID unknown; possible mat reuse across subjects cannot be checked (OPEN-04)"],
    "User02": ["two concurrent mats 22480/22482; physical setup and use policy open (OPEN-03)",
               "22482 P1 response collapse from 2026-08-20 (OPEN-19)",
               "2 prefix-mismatch files quarantined and excluded (OPEN-02)"],
    "User07": ["device ID unknown; possible mat reuse across subjects cannot be checked (OPEN-04)"],
}
# Timeline events from earlier audits and provider notes (status values never mixed; see coverage.EVENT_STATUSES).
DOCUMENTED_EVENTS = [
    ("User01", "2026-01-25", "confirmed_metadata_boundary", "pressure-sensor replacement; s1 -> s2",
     "provider note + A10 step (D-019)", "sensor_phase"),
    ("User01", "2025-11-18", "documented_metadata_event", "heating season start (metadata; year inferred)",
     "restricted metadata; no step in A10 (OPEN-14)", "none"),
    ("User01", "2025-12-17", "observed_distribution_shift", "active channels 1.51 -> 2.49, switch rate x3",
     "A10 §6; coincides with the log-container change (OPEN-21)", "none (cause open)"),
    ("User01", "2025-12-25", "observed_distribution_shift", "pressure-sum level +49 %", "A10 §6; cause unknown",
     "none (cause open)"),
    ("User02/22482", "2026-08-20", "unresolved_anomaly", "P1 nearly silent, P6 active share halves",
     "A9 §5 (OPEN-19)", "none (cause open)"),
    ("User01", "2025-12-28", "target_quality_episode", "daytime T/H zero-dropout runs", "A8 §3 (D-016 proposed)",
     "target flag"),
    ("User02/22482", "2026-08-08", "target_quality_episode", "night of T/H zeros and extreme glitches",
     "A8 §3 (D-016 proposed)", "target flag"),
]
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID, SURFACE, AUX = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb", "#9a9892"
_EPOCH = datetime(1970, 1, 1)


def iso(s) -> str:
    return (_EPOCH + timedelta(seconds=int(s))).isoformat(sep=" ")


def columns(rows: list[dict], first: list[str]) -> list[str]:
    cols = list(first)
    for r in rows:
        cols += [k for k in r if k not in cols]
    return cols


def load_with_identity(root: Path, manifest: list[dict], source_ids: set[str]):
    """Parse each source once (read-only); also collect device evidence found inside the files."""
    by_source: dict[str, list[dict]] = {}
    for r in manifest:
        if str(r["is_sensor_data"]) == "True" and r["source_id"] in source_ids:
            by_source.setdefault(r["source_id"], []).append(r)
    loaded, evidence = {}, {}
    for sid, recs in sorted(by_source.items()):
        info = resolve_source(recs[0]["source_relpath"])
        ev = {"root_key_devices": Counter(), "row_device_column": Counter(),
              "filename_devices": Counter(r["device_id_filename"] for r in recs if r.get("device_id_filename"))}

        def gen():
            for r in recs:
                pf = parse_file(root / r["source_relpath"], year_hint=info.year_hint)
                ev["root_key_devices"].update({k.split("_", 1)[1]: v for k, v in pf.root_keys.items() if "_" in k})
                ev["row_device_column"].update(x.device_id for x in pf.rows if x.device_id)
                yield r["source_relpath"], pf.rows

        loaded[sid] = SourceData.from_rows(sid, recs[0]["subject_id"], recs[0]["device_id"], gen())
        evidence[sid] = ev
    return loaded, evidence


def group_arrays(src: SourceData, minute_res: bool) -> dict:
    """Audit view of one subject/device group and the per-row labels A11 needs."""
    keys = row_keys(src)
    copies = np.zeros(src.n, bool) if minute_res else upload_copy_mask(src, keys, overlapping_file_pairs(src, keys))
    keep = np.flatnonzero(~copies)
    rows = keep[np.argsort(src.ts[keep], kind="stable")]
    ts = src.ts[rows]
    P, pres = pressure_matrix(src, rows)
    schema = src.schema_code[rows]
    bad = pressure_policy_masks(P, pres, schema, np.zeros(rows.size, bool))["B_A_plus_impossible_encoding"]
    temp, tm = channel_values(src, rows, "temp")
    humid, hm = channel_values(src, rows, "humid")
    t_ok, h_ok = channel_states(temp, "temp", tm)["valid"], channel_states(humid, "humid", hm)["valid"]
    src_of_file = np.array([resolve_source(f).source_id for f in src.files])
    bounds, names = sensor_phase_spec(src.subject_id)
    container = "csv_minute" if minute_res else None
    raw_phase = assign_phase(src.ts, bounds, names)                  # raw rows (before de-duplication)
    schema_names = np.array([SCHEMA_NAMES[int(c)] for c in schema], dtype=object)
    if minute_res:
        schema_names[schema_names == "p6_t_h"] = "legacy_csv_fsr_p6_t_h"   # FSR1..6 columns, mapped by position
    return {
        "ts": ts, "source": src_of_file[src.file_idx[rows]], "schema": schema_names,
        "container": (np.full(rows.size, container, dtype=object) if container else
                      np.where(src.chunk_idx[rows] >= 0, "quasi_json_chunks", "plain_lines")),
        "phase": assign_phase(ts, bounds, names), "audit_valid": ~bad & t_ok & h_ok, "t_ok": t_ok, "h_ok": h_ok,
        "raw_rows": Counter(zip(src_of_file[src.file_idx].tolist(), raw_phase.tolist())), "minute_res": minute_res,
    }


def periods(ts: np.ndarray, labels: np.ndarray) -> str:
    labs, dates = daily_labels(ts, labels)
    return "; ".join(f"{lab} {a}..{b}" for lab, a, b in regime_runs(labs, dates))


def main() -> int:
    t_start = time.time()
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2
    groups = subject_device_groups(manifest, eligible_only=True)
    assert not any(s == "User06" for s, _ in groups), "User06 source must be excluded (D-017)"
    eligible = set().union(*(g["sources"] for g in groups.values()))
    loaded, evidence = load_with_identity(root, manifest, eligible)
    G = {}
    for key, g in groups.items():
        src = SourceData.concat([loaded[s] for s in sorted(g["sources"])], "+".join(sorted(g["sources"])), *key)
        G[key] = group_arrays(src, g["families"] == {"legacy_csv_ymd_hm"})
    del loaded

    # ---- domains: subject, device, phase and auxiliary views (a device ID is never a subject) -----------------
    def dom(keys_, source=None, phase=None):
        parts = []
        for k in keys_:
            a = G[k]
            m = np.ones(a["ts"].size, bool)
            if source:
                m &= a["source"] == source
            if phase:
                m &= a["phase"] == phase
            parts.append({f: (v[m] if isinstance(v, np.ndarray) else v) for f, v in a.items()})
        cat = lambda f: np.concatenate([p[f] for p in parts])  # noqa: E731
        return {f: cat(f) for f in ("ts", "audit_valid", "t_ok", "h_ok", "schema", "container", "phase", "source")}

    u01, u02a, u02b, u07 = ("User01", "unknown"), ("User02", "22480"), ("User02", "22482"), ("User07", "unknown")
    domains = {
        "User01": dom([u01]), "User01/s1": dom([u01], phase="s1"), "User01/s2": dom([u01], phase="s2"),
        "User02": dom([u02a, u02b]), "User02/22480": dom([u02a]), "User02/22482": dom([u02b]),
        "User07": dom([u07]),
        "User02/legacy (aux)": dom([("User02", "unknown")]), "User03/legacy (aux)": dom([("User03", "unknown")]),
    }
    kind = {"User01": "subject", "User02": "subject (both mats)", "User07": "subject", "User01/s1": "sensor_phase",
            "User01/s2": "sensor_phase", "User02/22480": "device", "User02/22482": "device",
            "User02/legacy (aux)": "auxiliary", "User03/legacy (aux)": "auxiliary"}

    def regimes(d):
        labs, dates = daily_step_regime(d["ts"])
        return "; ".join(f"{lab} {a}..{b}" for lab, a, b in regime_runs(labs, dates))

    # ---- canonical coverage table ------------------------------------------------------------------------------
    cov = []
    for s in sources():
        base = {"level": "source_slice", "subject_id": s.subject_id, "source_id": s.source_id, "role": s.dataset_role,
                "quality_status": s.quality_status, "device_id": s.device_id, "format_family": s.format_family,
                "exclusion_status": "included" if s.analysis_eligible else "excluded",
                "exclusion_reason": "" if s.analysis_eligible else (s.exclusion_reason or s.dataset_role),
                "exclusion_decision": s.exclusion_decision or ("D-006" if s.dataset_role == "quarantined" else
                                                               "D-008" if s.dataset_role == "restricted_metadata" else "")}
        files = [r for r in manifest if r["source_id"] == s.source_id]
        base["files"] = len(files)
        if not s.analysis_eligible:
            cov.append({**base, "sensor_phase": "not_analysed", "schema_version": "not_analysed",
                        "firmware_schema_period": "not_analysed", "raw_rows": "not_analysed"})
            continue
        key = (s.subject_id, s.device_id)
        a = G[key]
        for ph in sorted(set(a["phase"][a["source"] == s.source_id].tolist())):
            m = (a["source"] == s.source_id) & (a["phase"] == ph)
            ts = a["ts"][m]
            summ = coverage_summary(ts, a["audit_valid"][m], a["t_ok"][m], a["h_ok"][m],
                                    raw_rows=a["raw_rows"][(s.source_id, ph)])
            schemas = sorted(set(a["schema"][m].tolist()))
            dev_first = ts[a["schema"][m] == "p6_t_h_device_column"]
            cov.append({**base, "sensor_phase": ph, "schema_version": "+".join(schemas),
                        "firmware_schema_period": (f"container: {periods(ts, a['container'][m])}"
                                                   + (f" | device_id column from {iso(dev_first.min())[:10]}" if dev_first.size else "")),
                        "sampling_regimes": "minute_resolution" if a["minute_res"] else regimes({"ts": ts}),
                        **{k: (iso(v) if k.endswith("timestamp") else v) for k, v in summ.items()}})
    for name, d in domains.items():
        summ = coverage_summary(d["ts"], d["audit_valid"], d["t_ok"], d["h_ok"])
        cov.append({"level": kind[name], "subject_id": name.split("/")[0], "source_id": "+".join(sorted(set(d["source"].tolist()))),
                    "domain": name, "sensor_phase": "+".join(sorted(set(d["phase"].tolist()))),
                    "schema_version": "+".join(sorted(set(d["schema"].tolist()))),
                    "sampling_regimes": regimes(d) if "legacy" not in name else "minute_resolution",
                    **{k: (iso(v) if k.endswith("timestamp") else v) for k, v in summ.items() if k != "raw_rows"}})

    # ---- monthly coverage --------------------------------------------------------------------------------------
    all_ts = np.concatenate([d["ts"] for d in domains.values()])
    months = month_range(month_of(int(all_ts.min()) // DAY_S), month_of(int(all_ts.max()) // DAY_S))
    mon_rows = []
    for name, d in domains.items():
        for r in monthly_coverage(d["ts"], d["t_ok"] & d["h_ok"], months):
            mon_rows.append({"domain": name, "kind": kind[name], **r})
    matrix = [{"domain": name, **{r["month"]: r["active_recording_hours"] for r in mon_rows if r["domain"] == name}}
              for name in domains]

    # ---- overlaps ----------------------------------------------------------------------------------------------
    ov_rows = []
    names = list(domains)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a.split("/")[0] == b.split("/")[0] and not ({a, b} == {"User02/22480", "User02/22482"}):
                continue                                   # same subject: only the two mats are compared
            ov_rows.append({"domain_a": a, "domain_b": b, "pair_type": _pair_type(kind[a], kind[b], a, b),
                            **overlap(domains[a]["ts"], domains[b]["ts"])})

    # ---- 22482 anomaly slice ------------------------------------------------------------------------------------
    cut = int((P1_ANOMALY_22482 - _EPOCH).total_seconds())
    t82, t80 = domains["User02/22482"]["ts"], domains["User02/22480"]["ts"]
    after82 = t82[t82 >= cut]
    anomaly = {"rows": int(after82.size), "active_hours": round(minutes(after82).size / 60, 2),
               "share_of_22482_hours": round(minutes(after82).size / max(1, minutes(t82).size), 4),
               "nights": int(np.unique((after82 - DAY_S // 2) // DAY_S).size),
               "hours_also_covered_by_22480": round(np.intersect1d(minutes(after82), minutes(t80[t80 >= cut])).size / 60, 2),
               "user02_hours_after_cut": round(minutes(np.concatenate([after82, t80[t80 >= cut]])).size / 60, 2),
               "user02_hours_without_22482_after_cut": round(minutes(np.concatenate([t82[t82 < cut], t80])).size / 60, 2),
               "user02_nights_without_22482_after_cut": int(np.unique((np.concatenate([t82[t82 < cut], t80]) - DAY_S // 2) // DAY_S).size)}

    # ---- confounding matrix -------------------------------------------------------------------------------------
    conf = []
    for name, d in domains.items():
        m_idx = d["ts"] // 60
        _, first = np.unique(m_idx, return_index=True)            # one row per recording minute
        seas = np.array([season_of(int(x) // DAY_S) for x in d["ts"][first]])
        labels = {
            "season": seas, "season_of_year": np.array([s.split("-", 1)[1] for s in seas]),
            "quarter": np.array([quarter_of(int(x) // DAY_S) for x in d["ts"][first]]),
            "month": np.array([month_of(int(x) // DAY_S) for x in d["ts"][first]]),
            "sensor_phase": d["phase"][first], "schema_version": d["schema"][first], "log_container": d["container"][first],
            "sampling_regime": _row_regime(d["ts"])[first],
        }
        for factor, lab in labels.items():
            for level, n in sorted(Counter(lab.tolist()).items()):
                conf.append({"domain": name, "kind": kind[name], "factor": factor, "level": level, "hours": round(n / 60, 2)})
    for subj in PRIMARY_SUBJECTS:                                   # co-coverage with the other primary subjects
        mine = {r["level"]: r["hours"] for r in conf if r["domain"] == subj and r["factor"] == "season"}
        others = {r["level"] for r in conf if r["domain"] in PRIMARY_SUBJECTS and r["domain"] != subj and r["factor"] == "season"}
        mon_mine = {r["level"]: r["hours"] for r in conf if r["domain"] == subj and r["factor"] == "month"}
        mon_oth = {r["level"] for r in conf if r["domain"] in PRIMARY_SUBJECTS and r["domain"] != subj and r["factor"] == "month"}
        tot = sum(mine.values())
        conf.append({"domain": subj, "kind": "summary", "factor": "share_hours_in_seasons_shared_with_other_primary",
                     "level": ";".join(sorted(k for k in mine if k in others)),
                     "hours": round(sum(v for k, v in mine.items() if k in others) / tot, 4)})
        conf.append({"domain": subj, "kind": "summary", "factor": "share_hours_in_months_shared_with_other_primary",
                     "level": ";".join(sorted(k for k in mon_mine if k in mon_oth)),
                     "hours": round(sum(v for k, v in mon_mine.items() if k in mon_oth) / tot, 4)})
        conf.append({"domain": subj, "kind": "summary", "factor": "seasons_observed_only_in_this_subject",
                     "level": ";".join(sorted(k for k in mine if k not in others)),
                     "hours": round(sum(v for k, v in mine.items() if k not in others), 2)})
        soy = {r["level"]: r["hours"] for r in conf if r["domain"] == subj and r["factor"] == "season_of_year"}
        soy_oth = {r["level"] for r in conf if r["domain"] in PRIMARY_SUBJECTS and r["domain"] != subj and r["factor"] == "season_of_year"}
        conf.append({"domain": subj, "kind": "summary", "factor": "seasons_of_year_observed_only_in_this_subject",
                     "level": ";".join(sorted(k for k in soy if k not in soy_oth)),
                     "hours": round(sum(v for k, v in soy.items() if k not in soy_oth), 2)})

    # ---- device evidence and hand-over gaps --------------------------------------------------------------------
    dev_rows = []
    for s in sources():
        if s.dataset_role == "restricted_metadata":
            continue
        ev = evidence.get(s.source_id)
        dev_rows.append({"kind": "source_device_evidence", "subject_id": s.subject_id, "source_id": s.source_id,
                         "role": s.dataset_role, "config_device_id": s.device_id,
                         "filename_device_ids": _fmt(ev["filename_devices"]) if ev else "not_analysed",
                         "json_root_key_device_ids": _fmt(ev["root_key_devices"]) if ev else "not_analysed",
                         "row_device_column_ids": _fmt(ev["row_device_column"]) if ev else "not_analysed",
                         "hardware_id_available": bool(ev and (ev["root_key_devices"] or ev["row_device_column"] or ev["filename_devices"]))})
    seen: dict[str, set] = {}
    for r in dev_rows:
        for field in ("config_device_id", "filename_device_ids", "json_root_key_device_ids", "row_device_column_ids"):
            for dv in str(r[field]).split(";"):
                dv = dv.split(":")[0].strip()
                if dv.isdigit():
                    seen.setdefault(dv, set()).add(r["subject_id"])
    for dv, subj in sorted(seen.items()):
        dev_rows.append({"kind": "device_to_subjects", "config_device_id": dv, "subject_id": ";".join(sorted(subj)),
                         "reused_across_subjects": len(subj) > 1})
    order = sorted(PRIMARY_SUBJECTS, key=lambda n: domains[n]["ts"].min())
    for a, b in zip(order[:-1], order[1:]):
        ga, gb = domains[a]["ts"].max(), domains[b]["ts"].min()
        dev_rows.append({"kind": "handover", "subject_id": f"{a} -> {b}", "source_id": f"{iso(ga)} -> {iso(gb)}",
                         "handover_gap_h": round((gb - ga) / 3600, 2)})
    for mat in ("User02/22480", "User02/22482"):
        first_b = domains[mat]["ts"].min()
        prev = domains["User07"]["ts"].max()
        dev_rows.append({"kind": "handover", "subject_id": f"User07 -> {mat}", "source_id": f"{iso(prev)} -> {iso(first_b)}",
                         "handover_gap_h": round((first_b - prev) / 3600, 2)})

    # ---- primary cohort eligibility ----------------------------------------------------------------------------
    el_rows = []
    cov_by = {r["domain"]: r for r in cov if r.get("domain")}
    for subj in PRIMARY_SUBJECTS:
        c = cov_by[subj]
        d = domains[subj]
        others = [o for o in PRIMARY_SUBJECTS if o != subj]
        shared_h = sum(overlap(d["ts"], domains[o]["ts"])["overlap_recording_hours"] for o in others)
        cap = chronological_capacity((d["ts"] - DAY_S // 2) // DAY_S, MIN_SPLIT_NIGHTS)
        checks = {
            "recording_volume": "pass" if c["active_recording_hours"] >= MIN_HOURS and c["recording_nights"] >= MIN_NIGHTS else "fail",
            "target_coverage": check(min(c["temperature_coverage"], c["humidity_coverage"]), MIN_TARGET_COVERAGE),
            "provenance_resolved": "pass",          # all primary rows resolve to one subject; A1: no rows shared across subjects
            "separable_without_subject_leakage": "pass" if shared_h == 0 else "fail",
            "future_chronological_data": "pass" if cap["can_split"] else "fail",
            "personalization_length": "pass" if cap["nights"] >= 2 * MIN_SPLIT_NIGHTS + 1 else "fail",
        }
        caveats = list(KNOWN_CAVEATS[subj])
        only = next(r["level"] for r in conf if r["domain"] == subj and r["factor"] == "seasons_of_year_observed_only_in_this_subject")
        if only:
            caveats.append(f"only primary subject observed in season: {only}")
        phase_nights = {ph: int(np.unique(((d["ts"][d["phase"] == ph]) - DAY_S // 2) // DAY_S).size)
                        for ph in sorted(set(d["phase"].tolist()))}
        el_rows.append({"subject_id": subj, **checks, "status": eligibility(checks, caveats),
                        "active_recording_hours": c["active_recording_hours"], "recording_nights": c["recording_nights"],
                        "span_days": c["span_days"], "min_target_coverage": min(c["temperature_coverage"], c["humidity_coverage"]),
                        "shared_recording_hours_with_other_primary": shared_h,
                        "nights_per_sensor_phase": ";".join(f"{k}:{v}" for k, v in phase_nights.items()),
                        "caveats": " | ".join(caveats)})

    # ---- schema / firmware / shift events ----------------------------------------------------------------------
    ev_rows = []
    for name in ("User01", "User02/22480", "User02/22482", "User07"):
        d = domains[name]
        labs, dates = daily_step_regime(d["ts"])
        for (l0, _, e0), (l1, s1, _) in zip(regime_runs(labs, dates)[:-1], regime_runs(labs, dates)[1:]):
            ev_rows.append({"domain": name, "date": s1, "status": "observed_sampling_regime_change",
                            "description": f"dominant step {l0} -> {l1} (previous day {e0})", "evidence": "A11 per-day steps; A10 §8",
                            "provenance_field": "sampling_regime"})
        clabs, cdates = daily_labels(d["ts"], d["container"])
        for (l0, _, _), (l1, s1, _) in zip(regime_runs(clabs, cdates)[:-1], regime_runs(clabs, cdates)[1:]):
            ev_rows.append({"domain": name, "date": s1, "status": "observed_schema_boundary",
                            "description": f"log container {l0} -> {l1}", "evidence": "raw line layout", "provenance_field": "log_container"})
        dev = d["ts"][d["schema"] == "p6_t_h_device_column"]
        if dev.size:
            ev_rows.append({"domain": name, "date": iso(dev.min())[:10], "status": "observed_schema_boundary",
                            "description": "device_id column added to data rows", "evidence": "raw line layout (A9 §6)",
                            "provenance_field": "pressure_schema"})
    for dm, dt, st, desc, evd, field in DOCUMENTED_EVENTS:
        ev_rows.append({"domain": dm, "date": dt, "status": st, "description": desc, "evidence": evd, "provenance_field": field})
    ev_rows.sort(key=lambda r: (r["date"], r["domain"]))

    od = paths.p0_output_dir("coverage")
    write_csv(od / "canonical_coverage.csv", cov, columns(cov, [
        "level", "domain", "subject_id", "source_id", "role", "quality_status", "device_id", "sensor_phase", "schema_version",
        "firmware_schema_period", "sampling_regimes", "first_timestamp", "last_timestamp", "recording_days",
        "usable_recording_days", "raw_rows", "audit_valid_rows", "active_recording_hours", "dominant_sampling_interval",
        "temperature_coverage", "humidity_coverage", "exclusion_status", "exclusion_reason"]))
    write_csv(od / "monthly_subject_coverage.csv", mon_rows, columns(mon_rows, ["domain", "kind", "month"]))
    write_csv(od / "monthly_active_hours_matrix.csv", matrix, ["domain"] + months)
    write_csv(od / "subject_temporal_overlap.csv", ov_rows, columns(ov_rows, ["domain_a", "domain_b", "pair_type"]))
    write_csv(od / "device_subject_matrix.csv", dev_rows, columns(dev_rows, ["kind", "subject_id", "source_id"]))
    write_csv(od / "confounding_matrix.csv", conf, ["domain", "kind", "factor", "level", "hours"])
    write_csv(od / "primary_cohort_eligibility.csv", el_rows, columns(el_rows, ["subject_id", "status"]))
    write_csv(od / "schema_firmware_events.csv", ev_rows, ["date", "domain", "status", "description", "evidence", "provenance_field"])
    figs = make_figure(od, domains, ev_rows)
    write_json(od / "coverage_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"], "manifest_sha256": sha256_file(mpath),
        "raw_integrity": {k: len(v) for k, v in integrity.items()}, "analysed_sources": sorted(eligible),
        "thresholds": {"usable_day_audit_valid_minutes": USABLE_DAY_MIN, "min_active_hours": MIN_HOURS,
                       "min_recording_nights": MIN_NIGHTS, "min_target_coverage": MIN_TARGET_COVERAGE,
                       "min_nights_per_chronological_part": MIN_SPLIT_NIGHTS},
        "user02_22482_after_2026_08_20": anomaly, "months": months, "figures": figs,
        "python": platform.python_version(), "numpy": np.__version__, "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"A11 done in {time.time() - t_start:.0f} s -> {od.relative_to(paths.PROJECT_ROOT)}  figures={figs}")
    return 0


def _pair_type(ka: str, kb: str, a: str, b: str) -> str:
    if {a, b} == {"User02/22480", "User02/22482"}:
        return "same_subject_devices"
    if "auxiliary" in (ka, kb):
        return "involves_auxiliary"
    if ka.startswith("subject") and kb.startswith("subject"):
        return "primary_subjects"
    return "subject_slices"


def _row_regime(ts: np.ndarray) -> np.ndarray:
    """Per-row label of the dominant sampling step of the row's calendar day."""
    labs, dates = daily_step_regime(ts)
    lut = dict(zip(dates, labs))
    d = np.asarray(ts) // DAY_S
    uniq, inv = np.unique(d, return_inverse=True)
    return np.array([lut[day_of(int(x)).isoformat()] for x in uniq], dtype=object)[inv]


def _fmt(c: Counter) -> str:
    return ";".join(f"{k}:{v}" for k, v in sorted(c.items())) if c else "none"


def make_figure(od: Path, domains: dict, events: list[dict]) -> list[str]:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
    except ImportError:
        return []
    rows = [("User01/s1", SERIES_COLORS[0]), ("User01/s2", SERIES_COLORS[0]), ("User02/22480", SERIES_COLORS[1]),
            ("User02/22482", SERIES_COLORS[1]), ("User07", SERIES_COLORS[2]),
            ("User02/legacy (aux)", AUX), ("User03/legacy (aux)", AUX)]
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=150, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    d0 = datetime(2025, 8, 1)
    bands = [(datetime(2025, 8, 1), datetime(2025, 9, 1), "summer"), (datetime(2025, 9, 1), datetime(2025, 12, 1), "autumn"),
             (datetime(2025, 12, 1), datetime(2026, 3, 1), "winter"), (datetime(2026, 3, 1), datetime(2026, 6, 1), "spring"),
             (datetime(2026, 6, 1), datetime(2026, 9, 1), "summer"), (datetime(2026, 9, 1), datetime(2026, 10, 1), "autumn")]
    for i, (a, b, lab) in enumerate(bands):
        ax.axvspan(a, b, color=GRID if i % 2 == 0 else SURFACE, alpha=0.5, zorder=0)
        ax.text(a + (b - a) / 2, len(rows) - 0.35, lab, ha="center", va="bottom", fontsize=7, color=INK2)
    for y, (name, color) in enumerate(rows[::-1]):
        dd = np.unique(domains[name]["ts"] // DAY_S)
        spans = [((_EPOCH + timedelta(days=int(x))), timedelta(days=1)) for x in dd]
        ax.broken_barh([(mdates.date2num(a), 1.0) for a, _ in spans], (y - 0.32, 0.64), facecolors=color,
                       edgecolor=SURFACE, linewidth=0.3)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([n for n, _ in rows[::-1]], fontsize=8, color=INK)
    y_of = {n: len(rows) - 1 - i for i, (n, _) in enumerate(rows)}
    marks = {"confirmed_metadata_boundary": ("|", INK, 11), "observed_schema_boundary": ("v", INK2, 5),
             "observed_sampling_regime_change": ("x", INK2, 5), "unresolved_anomaly": ("D", "#c0392b", 5)}
    used = set()
    for e in events:
        if e["status"] not in marks:
            continue
        dm = e["domain"] if e["domain"] in y_of else ("User01/s1" if e["domain"] == "User01" else None)
        if dm is None:
            continue
        if e["domain"] == "User01" and e["date"] >= "2026-01-25":
            dm = "User01/s2" if e["status"] != "confirmed_metadata_boundary" else "User01/s1"
        mk, col, size = marks[e["status"]]
        ax.plot(datetime.fromisoformat(e["date"]), y_of[dm] + (0.45 if mk != "|" else 0), marker=mk, color=col,
                markersize=size, linestyle="none", zorder=5)
        used.add(e["status"])
    ax.axvline(datetime(2026, 1, 25, 12), color=INK, linewidth=0.9, linestyle="--", zorder=4)
    ax.set_xlim(d0, datetime(2026, 10, 1))
    ax.set_ylim(-0.6, len(rows) - 0.1)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.tick_params(colors=INK2, labelsize=7)
    for s in ax.spines.values():
        s.set_color(GRID)
    handles = [Patch(color=SERIES_COLORS[0], label="User01"), Patch(color=SERIES_COLORS[1], label="User02"),
               Patch(color=SERIES_COLORS[2], label="User07"), Patch(color=AUX, label="auxiliary (legacy)")]
    labels_ev = {"observed_schema_boundary": "schema / log-container boundary", "observed_sampling_regime_change":
                 "sampling-regime change", "unresolved_anomaly": "unresolved anomaly (22482 P1)"}
    for st, lab in labels_ev.items():
        if st in used:
            mk, col, size = marks[st]
            handles.append(plt.Line2D([], [], marker=mk, color=col, linestyle="none", markersize=size, label=lab))
    handles.append(plt.Line2D([], [], color=INK, linestyle="--", label="User01 sensor change (D-019)"))
    ax.legend(handles=handles, frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=4)
    ax.set_title("Recorded days per subject / device / sensor phase (analysis-eligible sources; User06 excluded)",
                 loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    p = od / "figures" / "coverage_timeline.png"
    with open_for_write(p, "wb") as fh:
        fig.savefig(fh, format="png", facecolor=SURFACE)
    plt.close(fig)
    return [p.name]


if __name__ == "__main__":
    raise SystemExit(main())
