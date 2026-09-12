"""P0 analysis A2 — User02 dual-device overlap audit. Read-only on raw data.

Describes how User02's devices 22480 and 22482 (and the two quarantined prefix-mismatch files)
record in time and relate in pressure, occupancy and temperature/humidity. Nothing is merged,
resampled, interpolated, deleted or decided here (src/data/device_overlap.py).

Outputs (regenerable, not committed; docs/CONVENTIONS.md §5) under outputs/qa/p0/user02_devices/:
  device_summary.csv            coverage, sampling interval and gap statistics per device
  temporal_overlap.csv          joint / exclusive recording time (summary per coverage rule, and per date)
  aligned_device_comparison.csv alignment sensitivity, pressure correlations, T/H differences, movement events
  lagged_correlation.csv        correlation profile over lags -30..+30 s and a ±24 h control
  event_lag_scan.csv            supplementary: movement-event coincidence over lags ±12 h (clock-offset check)
  event_lag_scan_by_date.csv    the same scan per date (day-specific clock offsets)
  daily_th_difference.csv       per-date T/H differences on paired rows
  occupancy_sensitivity.csv     both / only-one / neither active under many occupancy definitions
  device_distributions.csv      per-device distributions (channels, pressure sum, activity, T/H)
  daily_device_profile.csv      per-device, per-date profile (used for the prefix-mismatch comparison)
  prefix_mismatch_evidence.csv  evidence items for the device attribution of the quarantined files
  user02_devices_run_meta.json  parameters, manifest checksum, integrity result

Interpretation: docs/P0_A2_USER02_DEVICE_REPORT.md.
"""
from __future__ import annotations

import platform
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data import paths  # noqa: E402
from src.data.device_overlap import (  # noqa: E402
    DAY_S, alignment_sensitivity, analysis_view, coverage_mask, diff_summary, event_coincidence, event_lag_scan,
    group_by_subject, interval_stats, lagged_correlation, lookup, occupancy_table, overlap_summary, pair_rows,
    pearson, pressure_features, quantiles, spearman, th_valid,
)
from src.data.io_guard import write_csv, write_json  # noqa: E402
from src.data.manifest import read_manifest, sha256_file, verify_raw_integrity  # noqa: E402
from src.data.provenance import load_sources  # noqa: E402
from src.data.raw_parser import parse_file  # noqa: E402

DEVICES = {"22480": "user02_mat_22480", "22482": "user02_mat_22482",
           "unresolved": "user02_mat_22480_prefix_mismatch"}
G_VALUES, G_MAIN = (10, 60, 300), 60           # coverage rules (max gap a row covers); not a session rule
TOLERANCES = (0, 1, 3)
LAGS = list(range(-30, 31))
SCAN_LAGS = list(range(-12 * 3600, 12 * 3600 + 1, 5))   # supplementary clock-offset check
ABS_THRESHOLDS = (0, 50, 100, 200, 500, 1000, 2000)
QUANTILE_THRESHOLDS = (0.10, 0.25, 0.50)
ACTIVE_CHANNELS = (1, 2, 3)
EVENT_QUANTILES = (0.90, 0.95, 0.99)
FEATURES = ("pressure_sum", "pressure_mean", "pressure_std", "active_channels", "change_magnitude")
_EPOCH = datetime(1970, 1, 1)


def iso(sec) -> str:
    return (_EPOCH + timedelta(seconds=int(sec))).isoformat(sep=" ")


def day_iso(day: int) -> str:
    return (_EPOCH + timedelta(days=int(day))).date().isoformat()


def per_day(mask: np.ndarray, t0: int) -> dict[int, float]:
    """Covered hours per calendar day."""
    idx = np.flatnonzero(mask)
    days = (t0 + idx) // DAY_S
    u, c = np.unique(days, return_counts=True)
    return {int(d): n / 3600.0 for d, n in zip(u, c)}


def daytime_hours(mask: np.ndarray, t0: int) -> dict[int, float]:
    idx = np.flatnonzero(mask)
    sec = t0 + idx
    day_sel = ((sec % DAY_S) // 3600 >= 9) & ((sec % DAY_S) // 3600 < 18)
    u, c = np.unique(sec[day_sel] // DAY_S, return_counts=True)
    return {int(d): n / 3600.0 for d, n in zip(u, c)}


def long_rows(section: str, d: dict, **keys) -> list[dict]:
    return [{"section": section, **keys, "metric": k, "value": v} for k, v in d.items()]


def main() -> int:
    t_start = time.time()
    root, mpath = paths.raw_root(), paths.manifest_path()
    manifest = read_manifest(mpath)
    integrity = verify_raw_integrity(root, manifest)
    if any(integrity.values()):
        print(f"ERROR: raw/manifest mismatch: { {k: v[:5] for k, v in integrity.items()} }", file=sys.stderr)
        return 2

    sources = load_sources(root, manifest, DEVICES.values())
    groups = group_by_subject(sources.values())
    assert list(groups) == ["User02"], f"User02 streams must form one evaluation group, got {groups}"
    views = {label: analysis_view(sources[sid], label) for label, sid in DEVICES.items()}
    feats = {k: pressure_features(v) for k, v in views.items()}
    valid = {k: th_valid(v) for k, v in views.items()}
    t0 = int(min(v.ts.min() for v in views.values()))
    n_sec = int(max(v.ts.max() for v in views.values())) - t0 + 1
    cov = {(k, g): coverage_mask(v.ts, t0, n_sec, g) for k, v in views.items() for g in G_VALUES}
    out = paths.p0_output_dir("user02_devices")
    A, B = views["22480"], views["22482"]
    fa, fb = feats["22480"], feats["22482"]

    # ---- 1. device summary -----------------------------------------------------------------------
    summary = []
    for k, v in views.items():
        row = {"device": k, "source_id": v.source_id, "subject_id": v.subject_id, "device_id": v.device_id,
               "n_files": v.n_files, "n_raw_rows": v.n_raw, "n_exact_duplicate_rows": v.n_exact_duplicates,
               "n_conflicting_timestamps": v.n_conflicting_ts, "n_view_rows": v.n,
               "first_ts": iso(v.ts.min()), "last_ts": iso(v.ts.max()),
               "recording_days": int(np.unique(v.ts // DAY_S).size),
               "duration_h": round(float(v.ts.max() - v.ts.min()) / 3600, 2)}
        for g in G_VALUES:
            row[f"active_hours_gap{g}s"] = round(float(cov[(k, g)].sum()) / 3600, 2)
        row.update(interval_stats(v.ts))
        summary.append(row)
    write_csv(out / "device_summary.csv", summary, list(summary[0].keys()))

    # ---- 2. temporal overlap -------------------------------------------------------------------------
    overlap = []
    for a, b in (("22480", "22482"), ("unresolved", "22480"), ("unresolved", "22482")):
        dates_both = np.intersect1d(np.unique(views[a].ts // DAY_S), np.unique(views[b].ts // DAY_S))
        for g in G_VALUES:
            s = overlap_summary(cov[(a, g)], cov[(b, g)])
            overlap.append({"device_a": a, "device_b": b, "level": "summary", "max_gap_s": g, "date": "",
                            "overlapping_dates": int(dates_both.size),
                            **{k: (round(x, 4) if isinstance(x, float) else x) for k, x in s.items()}})
    pa, pb = per_day(cov[("22480", G_MAIN)], t0), per_day(cov[("22482", G_MAIN)], t0)
    joint_main = cov[("22480", G_MAIN)] & cov[("22482", G_MAIN)]
    pj = per_day(joint_main, t0)
    for d in sorted(set(pa) | set(pb)):
        ha, hb, hj = pa.get(d, 0.0), pb.get(d, 0.0), pj.get(d, 0.0)
        overlap.append({"device_a": "22480", "device_b": "22482", "level": "date", "max_gap_s": G_MAIN,
                        "date": day_iso(d), "overlapping_dates": "", "hours_a": round(ha, 3), "hours_b": round(hb, 3),
                        "hours_both": round(hj, 3), "hours_only_a": round(ha - hj, 3), "hours_only_b": round(hb - hj, 3),
                        "hours_union": round(ha + hb - hj, 3),
                        "ratio_both_of_union": round(hj / (ha + hb - hj), 4) if ha + hb - hj else None})
    ocols = ["device_a", "device_b", "level", "max_gap_s", "date", "overlapping_dates", "hours_a", "hours_b",
             "hours_both", "hours_only_a", "hours_only_b", "hours_union", "ratio_both_of_union", "ratio_both_of_a",
             "ratio_both_of_b", "n_only_a_periods_ge_30min", "n_only_b_periods_ge_30min"]
    write_csv(out / "temporal_overlap.csv", [{c: r.get(c, "") for c in ocols} for r in overlap], ocols)

    # ---- 3. alignment, pressure relationship, T/H, movement events -----------------------------------
    rows_a = lookup(joint_main, t0, A.ts)
    rows_b = lookup(joint_main, t0, B.ts)
    comp = []
    comp += long_rows("alignment", alignment_sensitivity(A.ts, B.ts, rows_a, TOLERANCES), direction="22480->22482",
                      subset="joint_coverage", tolerance_s="")
    comp += long_rows("alignment", alignment_sensitivity(B.ts, A.ts, rows_b, TOLERANCES), direction="22482->22480",
                      subset="joint_coverage", tolerance_s="")
    comp += long_rows("alignment", alignment_sensitivity(A.ts, B.ts, None, TOLERANCES), direction="22480->22482",
                      subset="all_rows", tolerance_s="")
    active_a, active_b = fa["pressure_sum"] > 0, fb["pressure_sum"] > 0
    pairs = {tol: pair_rows(A.ts, B.ts, tol, 0, rows_a) for tol in (1, 3)}
    for tol, (ia, jb) in pairs.items():
        for subset, keep in (("all_pairs", np.ones(ia.size, bool)), ("both_active", active_a[ia] & active_b[jb])):
            for f in FEATURES:
                x, y = fa[f][ia[keep]], fb[f][jb[keep]]
                comp += long_rows("pressure", {"n_pairs": int(keep.sum()), "pearson": pearson(x, y),
                                               "spearman": spearman(x, y)},
                                  direction="22480~22482", subset=f"{subset}:{f}", tolerance_s=tol)
        vv = valid["22480"][ia] & valid["22482"][jb]
        for var in ("temp", "humid"):
            x = getattr(A, var)[ia[vv]].astype(float)
            y = getattr(B, var)[jb[vv]].astype(float)
            comp += long_rows("th", diff_summary(x, y), direction="22480-22482", subset=var, tolerance_s=tol)
    # inventory reconciliation: per-minute medians (as in docs/initial_dataset_inventory.md §7.4)
    for var in ("temp", "humid"):
        med = {}
        for k, v in (("22480", A), ("22482", B)):
            sel = valid[k]
            mins = v.ts[sel] // 60
            vals = getattr(v, var)[sel].astype(float)
            order = np.argsort(mins, kind="stable")
            mins, vals = mins[order], vals[order]
            u, start = np.unique(mins, return_index=True)
            med[k] = dict(zip(u.tolist(), [float(np.median(s)) for s in np.split(vals, start[1:])]))
        common = sorted(set(med["22480"]) & set(med["22482"]))
        d = np.array([med["22480"][m] - med["22482"][m] for m in common])
        comp += long_rows("th_inventory_method", {"n_minutes": len(common), "median_diff": float(np.median(d)),
                                                  "pearson": pearson(np.array([med["22480"][m] for m in common]),
                                                                     np.array([med["22482"][m] for m in common]))},
                          direction="22480-22482", subset=var, tolerance_s="minute_median")
    # movement events: large frame-to-frame changes on each device
    for q in EVENT_QUANTILES:
        thr = {k: float(np.nanquantile(feats[k]["change_magnitude"][feats[k]["pressure_sum"] > 0], q))
               for k in ("22480", "22482")}
        ev_a = np.nan_to_num(fa["change_magnitude"]) >= thr["22480"]
        ev_b = np.nan_to_num(fb["change_magnitude"]) >= thr["22482"]
        for w in (3, 10):
            for direction, args in (("22480->22482", (A.ts, ev_a, B.ts, ev_b, w, rows_a, DAY_S, cov[("22482", G_MAIN)], t0)),
                                    ("22482->22480", (B.ts, ev_b, A.ts, ev_a, w, rows_b, DAY_S, cov[("22480", G_MAIN)], t0))):
                r = event_coincidence(*args)
                r.update(threshold_a=thr[direction[:5]], threshold_b=thr[direction[-5:]])
                comp += long_rows("movement_events", r, direction=direction, subset=f"q{q:.2f}", tolerance_s=w)
    write_csv(out / "aligned_device_comparison.csv", comp,
              ["section", "direction", "subset", "tolerance_s", "metric", "value"])

    # ---- 3b. lagged correlation ---------------------------------------------------------------------------
    lag_rows = []
    lags = LAGS + [DAY_S, -DAY_S]
    for f in ("change_magnitude", "pressure_sum"):
        for subset, gate in (("all_pairs", None), ("both_active", (active_a, active_b))):
            prof = lagged_correlation(A.ts, fa[f], B.ts, fb[f], lags, tol_s=1, rows_a=rows_a,
                                      gate_a=None if gate is None else gate[0], gate_b=None if gate is None else gate[1])
            lag_rows += [{"feature": f, "subset": subset, **r} for r in prof]
    write_csv(out / "lagged_correlation.csv", lag_rows, ["feature", "subset", "lag_s", "n_pairs", "pearson", "spearman"])

    # ---- 3c. supplementary: wide event-lag scan to rule out a clock offset between devices -------------------
    thr95 = {k: float(np.nanquantile(feats[k]["change_magnitude"][feats[k]["pressure_sum"] > 0], 0.95))
             for k in ("22480", "22482")}
    ev_a95 = (np.nan_to_num(fa["change_magnitude"]) >= thr95["22480"]) & rows_a
    ev_b95 = np.nan_to_num(fb["change_magnitude"]) >= thr95["22482"]
    scan = event_lag_scan(A.ts, ev_a95, B.ts, ev_b95, SCAN_LAGS, 3, cov[("22482", G_MAIN)], t0)
    write_csv(out / "event_lag_scan.csv", scan, ["lag_s", "n_events", "share"])
    # per date: a day-specific clock offset would be diluted in the pooled scan
    per_date_scan = []
    a_days = A.ts // DAY_S
    for d in np.unique(a_days[ev_a95]):
        day_ev = ev_a95 & (a_days == d)
        rows = event_lag_scan(A.ts, day_ev, B.ts, ev_b95, SCAN_LAGS, 3, cov[("22482", G_MAIN)], t0)
        # a real offset would align most of the day's events: require >= half of them to be comparable
        good = [r for r in rows if r["n_events"] >= max(30, 0.5 * int(day_ev.sum()))]
        if not good:
            continue
        shares = np.array([r["share"] for r in good])
        best = max(good, key=lambda r: r["share"])
        at0 = next((r for r in rows if r["lag_s"] == 0), {})
        per_date_scan.append({"date": day_iso(d), "n_events_lag0": at0.get("n_events"), "share_lag0": at0.get("share"),
                              "median_share": float(np.median(shares)), "p99_share": float(np.percentile(shares, 99)),
                              "max_share": best["share"], "lag_at_max_s": best["lag_s"], "n_events_at_max": best["n_events"]})
    write_csv(out / "event_lag_scan_by_date.csv", per_date_scan, list(per_date_scan[0].keys()))

    # ---- 4. daily T/H difference ----------------------------------------------------------------------------
    ia, jb = pairs[1]
    vv = valid["22480"][ia] & valid["22482"][jb]
    ia, jb = ia[vv], jb[vv]
    days = A.ts[ia] // DAY_S
    daily = []
    for d in np.unique(days):
        s = days == d
        ta, tb = A.temp[ia[s]].astype(float), B.temp[jb[s]].astype(float)
        ha, hb = A.humid[ia[s]].astype(float), B.humid[jb[s]].astype(float)
        daily.append({
            "date": day_iso(d), "n_pairs": int(s.sum()),
            "temp_median_22480": float(np.median(ta)), "temp_median_22482": float(np.median(tb)),
            "temp_median_diff": float(np.median(ta - tb)), "temp_mean_diff": float((ta - tb).mean()),
            "temp_mae": float(np.abs(ta - tb).mean()), "temp_pearson": pearson(ta, tb),
            "humid_median_22480": float(np.median(ha)), "humid_median_22482": float(np.median(hb)),
            "humid_median_diff": float(np.median(ha - hb)), "humid_mean_diff": float((ha - hb).mean()),
            "humid_mae": float(np.abs(ha - hb).mean()), "humid_pearson": pearson(ha, hb),
        })
    write_csv(out / "daily_th_difference.csv", daily, list(daily[0].keys()))

    # ---- 5. occupancy sensitivity ----------------------------------------------------------------------------
    ia, jb = pairs[1]
    sa, sb = fa["pressure_sum"][ia], fb["pressure_sum"][jb]
    occ = []

    def add(definition, thr_a, thr_b, act_a, act_b):
        occ.append({"definition": definition, "threshold_22480": thr_a, "threshold_22482": thr_b,
                    **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in occupancy_table(act_a, act_b).items()}})

    for thr in ABS_THRESHOLDS:
        add(f"pressure_sum>{thr}", thr, thr, sa > thr, sb > thr)
    for q in QUANTILE_THRESHOLDS:
        qa = float(np.quantile(fa["pressure_sum"][fa["pressure_sum"] > 0], q))
        qb = float(np.quantile(fb["pressure_sum"][fb["pressure_sum"] > 0], q))
        add(f"pressure_sum>device_nonzero_q{q:.2f}", qa, qb, sa > qa, sb > qb)
    for k in ACTIVE_CHANNELS:
        add(f"active_channels>={k}", k, k, fa["active_channels"][ia] >= k, fb["active_channels"][jb] >= k)
    lab = (A.fw_absent[ia] >= 0) & (B.fw_absent[jb] >= 0)
    add("firmware_label!=NM", "firmware", "firmware", A.fw_absent[ia][lab] == 0, B.fw_absent[jb][lab] == 0)
    write_csv(out / "occupancy_sensitivity.csv", occ, list(occ[0].keys()))

    # ---- 6. device distributions ------------------------------------------------------------------------------
    dist = []
    for k, v in views.items():
        f = feats[k]
        for c in range(6):
            x = v.p[:, c].astype(float)
            dist += [{"device": k, "variable": f"p{c + 1}", "stat": s, "value": val}
                     for s, val in {**quantiles(x), "share_zero": float((x == 0).mean()),
                                    "share_at_4095": float((x == 4095).mean())}.items()]
        act = f["pressure_sum"] > 0
        dist += [{"device": k, "variable": "pressure_sum", "stat": s, "value": val} for s, val in quantiles(f["pressure_sum"]).items()]
        dist += [{"device": k, "variable": "pressure_sum_active", "stat": s, "value": val}
                 for s, val in quantiles(f["pressure_sum"][act]).items()]
        dist.append({"device": k, "variable": "pressure_sum", "stat": "share_zero", "value": float((~act).mean())})
        for n_act in range(7):
            dist.append({"device": k, "variable": "active_channels", "stat": f"share_eq_{n_act}",
                         "value": float((f["active_channels"] == n_act).mean())})
        for var in ("temp", "humid"):
            x = getattr(v, var)[valid[k]].astype(float)
            dist += [{"device": k, "variable": var, "stat": s, "value": val} for s, val in quantiles(x).items()]
        dist.append({"device": k, "variable": "th", "stat": "share_implausible", "value": float((~valid[k]).mean())})
        dist.append({"device": k, "variable": "firmware_label", "stat": "share_NM",
                     "value": float((v.fw_absent == 1).mean())})
    write_csv(out / "device_distributions.csv", dist, ["device", "variable", "stat", "value"])

    # ---- 7. daily device profile -------------------------------------------------------------------------------
    profile = []
    for k, v in views.items():
        f = feats[k]
        hrs, day_hrs = per_day(cov[(k, G_MAIN)], t0), daytime_hours(cov[(k, G_MAIN)], t0)
        vdays = v.ts // DAY_S
        for d in np.unique(vdays):
            s = vdays == d
            act = s & (f["pressure_sum"] > 0)
            ok = s & valid[k]
            profile.append({
                "device": k, "date": day_iso(d), "n_rows": int(s.sum()),
                "recorded_hours": round(hrs.get(int(d), 0.0), 3), "daytime_hours_09_18": round(day_hrs.get(int(d), 0.0), 3),
                "temp_median": float(np.median(v.temp[ok])) if ok.any() else None,
                "humid_median": float(np.median(v.humid[ok])) if ok.any() else None,
                "pressure_sum_active_p95": float(np.percentile(f["pressure_sum"][act], 95)) if act.any() else None,
                "share_zero_pressure": float((f["pressure_sum"][s] == 0).mean()),
                "max_channel_value": int(v.p[s].max()),
            })
    write_csv(out / "daily_device_profile.csv", profile, list(profile[0].keys()))

    # ---- 8. prefix-mismatch evidence ----------------------------------------------------------------------------
    Q = views["unresolved"]
    q_recs = [r for r in manifest if r["source_id"] == DEVICES["unresolved"]]
    ev = []

    def item(name, observed, ref80, ref82, points_to, note=""):
        ev.append({"evidence": name, "observed": observed, "reference_22480": ref80, "reference_22482": ref82,
                   "points_to": points_to, "note": note})

    item("storage_folder", "user02/mat_22480/_prefix_mismatch", "files delivered in the 22480 archive", "",
         "22480", "provider packaging; the provider itself isolated the files")
    item("filename_prefix", ",".join(sorted({r["device_id_filename"] for r in q_recs})), "sm22480_", "sm22482_", "22482")
    roots = sorted({k for r in q_recs for k in parse_file(root / r["source_relpath"]).root_keys if k.startswith("smartmat_")})
    item("json_root_key", ",".join(roots), "smartmat_22480", "smartmat_22482",
         "22482" if roots == ["smartmat_22482"] else "ambiguous")
    q_days = sorted({day_iso(d) for d in np.unique(Q.ts // DAY_S)})
    a_files = {r["file_name"][-8:-4] for r in manifest if r["source_id"] == DEVICES["22480"]}
    b_files = {r["file_name"][-8:-4] for r in manifest if r["source_id"] == DEVICES["22482"]}
    q_names = {r["file_name"][-8:-4] for r in q_recs}
    item("file_dates_missing", ",".join(sorted(q_names)),
         "has own files: " + ",".join(sorted(q_names & a_files)), "missing: " + ",".join(sorted(q_names - b_files)),
         "22482" if q_names - b_files == q_names and q_names <= a_files else "ambiguous")
    s80 = overlap_summary(cov[("unresolved", G_MAIN)], cov[("22480", G_MAIN)])
    s82 = overlap_summary(cov[("unresolved", G_MAIN)], cov[("22482", G_MAIN)])
    item("concurrent_recording_hours", f"with 22480: {s80['hours_both']:.2f} h; with 22482: {s82['hours_both']:.2f} h",
         f"{s80['hours_both']:.2f} h simultaneous with 22480's own stream, 0 shared rows (A1)",
         f"{s82['hours_both']:.2f} h", "22482" if s80["hours_both"] > 0.5 and s82["hours_both"] < s80["hours_both"] else "ambiguous",
         "one device cannot log two different streams at the same time, unless 22480's own files for these dates are misattributed")
    qf, ql = int(Q.ts.min()), int(Q.ts.max())
    for k, v in (("22480", A), ("22482", B)):
        before = v.ts[v.ts < qf]
        after = v.ts[v.ts > ql]
        ev_gap = (f"{(qf - before.max()) / 60:.1f} min after its last row" if before.size else "none before",
                  f"{(after.min() - ql) / 60:.1f} min before its next row" if after.size else "none after")
        ev.append({"evidence": f"continuity_with_{k}", "observed": f"quarantined starts {iso(qf)}, ends {iso(ql)}",
                   "reference_22480": "; ".join(ev_gap) if k == "22480" else "",
                   "reference_22482": "; ".join(ev_gap) if k == "22482" else "", "points_to": "see_values",
                   "note": "gap between the device's own rows and the quarantined span"})
    # daily-profile comparison with neighbouring dates (±7 days)
    prof_by = {}
    for r in profile:
        prof_by.setdefault(r["device"], {})[r["date"]] = r
    qd = [datetime.fromisoformat(x).date() for x in q_days]
    window = {(min(qd) + timedelta(days=i)).isoformat() for i in range(-7, (max(qd) - min(qd)).days + 8)} - set(q_days)
    # Duration-sensitive metrics use only interior (full) days of the quarantined span. A metric points to a
    # device only if the two devices' neighbouring-day ranges do not overlap (i.e. it can discriminate).
    interior = q_days[1:-1] if len(q_days) >= 3 else q_days
    for metric, days_used in (("recorded_hours", interior), ("daytime_hours_09_18", interior),
                              ("max_channel_value", interior), ("temp_median", q_days), ("humid_median", q_days),
                              ("pressure_sum_active_p95", q_days), ("share_zero_pressure", q_days)):
        qv = [prof_by["unresolved"][d][metric] for d in days_used if d in prof_by["unresolved"]]
        rng = {}
        for k in ("22480", "22482"):
            vals = [prof_by[k][d][metric] for d in window if d in prof_by.get(k, {}) and prof_by[k][d][metric] is not None]
            rng[k] = (min(vals), max(vals)) if vals else None
        inside = {k: rng[k] is not None and all(rng[k][0] <= x <= rng[k][1] for x in qv if x is not None) for k in rng}
        separated = rng["22480"] and rng["22482"] and (rng["22480"][1] < rng["22482"][0] or rng["22482"][1] < rng["22480"][0])
        pt = ("neutral (device ranges overlap)" if not separated else
              "22482" if inside["22482"] and not inside["22480"] else
              "22480" if inside["22480"] and not inside["22482"] else "ambiguous")
        fmt = lambda r: "" if r is None else f"{r[0]:.3g}..{r[1]:.3g} (neighbouring days)"  # noqa: E731
        item(f"daily_{metric}", ", ".join(f"{x:.3g}" for x in qv if x is not None), fmt(rng["22480"]), fmt(rng["22482"]),
             pt, f"days used: {','.join(days_used)}")
    # T/H relation during concurrent time with 22480, compared with the typical 22480-22482 relation
    joint_q = cov[("unresolved", G_MAIN)] & cov[("22480", G_MAIN)]
    iq, ja = pair_rows(Q.ts, A.ts, 1, 0, lookup(joint_q, t0, Q.ts))
    ok = valid["unresolved"][iq] & valid["22480"][ja]
    typical = {r["subset"]: r["value"] for r in comp if r["section"] == "th" and r["tolerance_s"] == 1 and r["metric"] == "median_diff"}
    for var in ("temp", "humid"):
        d = diff_summary(getattr(A, var)[ja[ok]].astype(float), getattr(Q, var)[iq[ok]].astype(float))
        similar = d.get("n_pairs", 0) > 0 and np.sign(d["median_diff"]) == np.sign(typical[var]) and \
            abs(d["median_diff"] - typical[var]) <= max(1.0, 0.5 * abs(typical[var]))
        item(f"{var}_diff_22480_minus_quarantined", f"median {d.get('median_diff')} (n={d.get('n_pairs')})",
             "0 expected if same device", f"typical 22480-22482 median diff: {typical[var]}",
             "22482" if similar else "ambiguous")
    write_csv(out / "prefix_mismatch_evidence.csv", ev,
              ["evidence", "observed", "reference_22480", "reference_22482", "points_to", "note"])

    write_json(out / "user02_devices_run_meta.json", {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "raw_root": paths.path_config()["raw_root"], "manifest_sha256": sha256_file(mpath),
        "raw_integrity": {k: len(v) for k, v in integrity.items()},
        "evaluation_groups": groups,
        "parameters": {"coverage_max_gap_s": G_VALUES, "main_coverage_max_gap_s": G_MAIN, "tolerances_s": TOLERANCES,
                       "lags_s": [LAGS[0], LAGS[-1]], "scan_lags_s": [SCAN_LAGS[0], SCAN_LAGS[-1], 5],
                       "control_shift_s": DAY_S, "abs_thresholds": ABS_THRESHOLDS,
                       "quantile_thresholds": QUANTILE_THRESHOLDS, "active_channels": ACTIVE_CHANNELS,
                       "event_quantiles": EVENT_QUANTILES, "change_max_step_s": 5,
                       "th_plausible": "0 < temp < 60 and 0 < humid <= 100 (descriptive mask)"},
        "python": platform.python_version(), "numpy": np.__version__,
        "runtime_s": round(time.time() - t_start, 1),
    })
    print(f"A2 done in {time.time() - t_start:.0f} s -> {out.relative_to(paths.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
