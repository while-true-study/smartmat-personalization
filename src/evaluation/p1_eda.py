"""P1 domain-shift EDA pipeline: canonical_v1 in, descriptive tables out (no model, split, window or scaling).

Called by scripts/run_p1_domain_eda.py. Reads only the verified primary canonical file; auxiliary sources
and excluded sources never enter (src/evaluation/canonical_input.py).
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from src.data.coverage import season_of
from src.evaluation.domain_shift import (
    MAIN_SLICES, MINOR_SLICES, POOLED, POOLED_PAIRS, WITHIN_PAIRS, assign_slices, binned_trend, channel_shares,
    distance, event_trajectory, hour_of_day, hours_since_session_start, iqr, night_index, parse_event,
    pooled_masks, pressure_descriptors, spearman, summarize, unit_stat, value_distribution,
)

COLUMNS = ["subject_id", "device_id", "sensor_phase", "channel_quality_phase", "timestamp", "P1", "P2", "P3", "P4",
           "P5", "P6", "temperature", "humidity", "target_temp_valid", "target_humidity_valid", "target_quality_flag",
           "pressure_valid", "pressure_upper_bound_channels", "session_id", "event_raw"]
OFFSETS_S = (-1800, -600, 0, 600, 1800, 3600)
MIN_EVENTS = 20
_EPOCH = date(1970, 1, 1)


def _dict_codes(col: pa.ChunkedArray) -> tuple[np.ndarray, list[str]]:
    """Integer codes and labels of a (dictionary or string) column; row groups share one dictionary after unify."""
    if pa.types.is_dictionary(col.type):
        arr = col.unify_dictionaries().combine_chunks()
    else:
        arr = col.combine_chunks().dictionary_encode()
    return arr.indices.to_numpy(zero_copy_only=False).astype(np.int64), arr.dictionary.to_pylist()


class Data:
    """Column arrays of the primary canonical rows with the derived EDA labels."""

    def __init__(self, t: pa.Table):
        codes, labels = {}, {}
        for c in ("subject_id", "device_id", "sensor_phase", "channel_quality_phase", "session_id"):
            codes[c], labels[c] = _dict_codes(t[c])
        combo = np.stack([codes[c] for c in ("subject_id", "device_id", "sensor_phase", "channel_quality_phase")], axis=1)
        uniq, inv = np.unique(combo, axis=0, return_inverse=True)
        lab = lambda c, i: labels[c][i]  # noqa: E731
        combo_slice = assign_slices(np.array([lab("subject_id", u[0]) for u in uniq], object),
                                    np.array([lab("device_id", u[1]) for u in uniq], object),
                                    np.array([lab("sensor_phase", u[2]) for u in uniq], object),
                                    np.array([lab("channel_quality_phase", u[3]) for u in uniq], object))
        self.slice = combo_slice[inv.ravel()]
        if (self.slice == "").any():
            raise ValueError("rows outside the primary domain slices")
        self.subject = np.array(labels["subject_id"], object)[codes["subject_id"]]
        self.device = np.array(labels["device_id"], object)[codes["device_id"]]
        self.session = codes["session_id"]
        # Parquet stores timestamp[s] as milliseconds; normalise to epoch seconds of the naive local time
        self.ts = t["timestamp"].cast(pa.timestamp("s")).cast(pa.int64()).to_numpy()
        self.p = np.stack([pc.fill_null(t[f"P{i}"], 0).to_numpy().astype(np.int64) for i in range(1, 7)], axis=1)
        self.pvalid = t["pressure_valid"].to_numpy()
        self.temp = pc.fill_null(t["temperature"], 0).to_numpy().astype(np.float64)
        self.humid = pc.fill_null(t["humidity"], 0).to_numpy().astype(np.float64)
        self.t_ok = t["target_temp_valid"].to_numpy()
        self.h_ok = t["target_humidity_valid"].to_numpy()
        fc, fl = _dict_codes(t["target_quality_flag"])
        self.tflag = np.array(fl, object)[fc]
        self.event_code, self.event_values = _dict_codes(t["event_raw"])
        self.pd = pressure_descriptors(self.p, self.pvalid)
        self.shares = channel_shares(self.p, self.pd.loaded)
        self.night = night_index(self.ts)
        self.day = self.ts // 86400
        days, dinv = np.unique(self.day, return_inverse=True)
        self.month = np.array([(_EPOCH + timedelta(days=int(d))).isoformat()[:7] for d in days], object)[dinv]
        self.season = np.array([season_of(int(d)) for d in days], object)[dinv]
        self.hour = hour_of_day(self.ts)
        self.rel_h = hours_since_session_start(self.ts, self.session)
        self.stream = codes["subject_id"] * 1000 + codes["device_id"]          # one id per subject + device stream

    def masks(self) -> dict[str, np.ndarray]:
        out = {s: self.slice == s for s in MAIN_SLICES + MINOR_SLICES}
        out.update(pooled_masks(self.subject, self.device))
        return out


def _iso_day(d) -> str:
    return (_EPOCH + timedelta(days=int(d))).isoformat()


def slice_role(name: str) -> str:
    return "main" if name in MAIN_SLICES else ("minor_reported" if name in MINOR_SLICES else "pooled_secondary")


def domain_slice_summary(D: Data, masks: dict) -> list[dict]:
    rows = []
    for name, m in masks.items():
        if not m.any():
            continue
        loaded = m & D.pd.loaded
        dom = np.bincount(D.pd.dominant[loaded], minlength=6) / max(1, loaded.sum())
        sh = np.nanmean(D.shares[loaded], axis=0) if loaded.any() else np.full(6, np.nan)
        rows.append({
            "slice": name, "analysis_role": slice_role(name), "rows": int(m.sum()), "loaded_rows": int(loaded.sum()),
            "sessions": int(np.unique(D.session[m]).size), "nights": int(np.unique(D.night[m]).size),
            "recording_hours": round(np.unique(D.ts[m] // 60).size / 60, 2),
            "first_date": _iso_day(D.day[m].min()), "last_date": _iso_day(D.day[m].max()),
            "months": ";".join(sorted(set(D.month[m].tolist()))), "seasons": ";".join(sorted(set(D.season[m].tolist()))),
            "target_valid_rows": int((m & D.t_ok & D.h_ok).sum()),
            "target_invalid_share": round(float((m & ~(D.t_ok & D.h_ok)).sum() / m.sum()), 6),
            "all_zero_share": round(float((m & D.pd.all_zero).sum() / m.sum()), 5),
            "upper_bound_row_share": round(float((m & (D.pd.upper > 0)).sum() / m.sum()), 6),
            **{f"dominant_share_p{i + 1}": round(float(dom[i]), 4) for i in range(6)},
            **{f"mean_contribution_p{i + 1}": round(float(sh[i]), 4) for i in range(6)},
        })
    return rows


def pressure_distribution(D: Data, masks: dict) -> list[dict]:
    variables = {**{f"P{i + 1}": D.p[:, i] for i in range(6)}, "pressure_sum": D.pd.total, "pressure_mean": D.pd.mean,
                 "pressure_std": D.pd.std, "active_channel_count": D.pd.active,
                 **{f"p{i + 1}_share": D.shares[:, i] for i in range(6)}}
    rows = []
    for name, m in masks.items():
        if not m.any():
            continue
        filters = {"all_rows": m & D.pvalid, "loaded_rows": m & D.pd.loaded,
                   "loaded_rows_excl_upper_bound": m & D.pd.loaded & (D.pd.upper == 0)}
        for var, x in variables.items():
            for fname, fm in filters.items():
                if var.endswith("_share") and fname == "all_rows":
                    continue
                s = summarize(x[fm])
                u, v = unit_stat(x[fm], D.night[fm])
                rows.append({"slice": name, "analysis_role": slice_role(name), "variable": var, "row_filter": fname, **s,
                             "upper_bound_row_share": round(float((fm & (D.pd.upper > 0)).sum() / max(1, fm.sum())), 6),
                             "nights": int(u.size), "night_median_median": float(np.median(v)) if v.size else None,
                             "night_median_iqr": iqr(v) if v.size else None})
    return rows


def target_distribution(D: Data, masks: dict) -> list[dict]:
    rows = []
    for name, m in masks.items():
        if not m.any():
            continue
        for var, x, ok in (("temperature", D.temp, D.t_ok), ("humidity", D.humid, D.h_ok)):
            v = m & ok
            flags = Counter(D.tflag[m & ~ok].tolist())
            s = summarize(x[v])
            un, vn = unit_stat(x[v], D.night[v])
            ud, vd = unit_stat(x[v], D.day[v])
            _, within_iqr = unit_stat(x[v], D.night[v], fn=lambda a: np.percentile(a, 75) - np.percentile(a, 25))
            _, within_rng = unit_stat(x[v], D.night[v], fn=lambda a: np.percentile(a, 95) - np.percentile(a, 5))
            rows.append({"slice": name, "analysis_role": slice_role(name), "variable": var, "rows": int(m.sum()),
                         "invalid_rows": int((m & ~ok).sum()), "invalid_share": round(float((m & ~ok).sum() / m.sum()), 6),
                         "invalid_causes": "; ".join(f"{k}:{c}" for k, c in sorted(flags.items())), **s,
                         **value_distribution(x[v].astype(np.int64)),
                         "nights": int(un.size), "night_median_median": float(np.median(vn)), "night_median_iqr": iqr(vn),
                         "night_median_min": float(vn.min()), "night_median_max": float(vn.max()),
                         "day_median_median": float(np.median(vd)), "day_median_iqr": iqr(vd),
                         "within_night_iqr_median": float(np.median(within_iqr)),
                         "within_night_p05_p95_range_median": float(np.median(within_rng))})
    return rows


def _gap_days(D: Data, a: np.ndarray, b: np.ndarray) -> float:
    a0, a1, b0, b1 = D.ts[a].min(), D.ts[a].max(), D.ts[b].min(), D.ts[b].max()
    return round(max(b0 - a1, a0 - b1, 0) / 86400, 2)


def distance_matrix(D: Data, masks: dict) -> list[dict]:
    pairs = []
    for i, a in enumerate(MAIN_SLICES):
        for b in MAIN_SLICES[i + 1:]:
            same = a.split("/")[0] == b.split("/")[0]
            pairs.append((a, b, "within_subject" if same else "between_subject_slice", (a, b) in WITHIN_PAIRS))
    pairs += [(a, b, "between_subject_pooled", False) for a, b in POOLED_PAIRS]
    variables = [("pressure_sum", D.pd.total, "loaded"), ("active_channel_count", D.pd.active, "loaded")]
    variables += [(f"P{i + 1}", D.p[:, i], "loaded") for i in range(6)]
    variables += [("temperature", D.temp, "t_ok"), ("humidity", D.humid, "h_ok")]
    rows = []
    for a, b, ptype, focus in pairs:
        ma, mb = masks[a], masks[b]
        for var, x, basis in variables:
            ok = D.pd.loaded if basis == "loaded" else (D.t_ok if basis == "t_ok" else D.h_ok)
            fa, fb = ma & ok, mb & ok
            d = distance(x[fa], x[fb], D.night[fa], D.night[fb])
            rows.append({"domain_a": a, "domain_b": b, "pair_type": ptype, "focus_within_pair": focus,
                         "variable": var, "row_basis": "loaded rows" if basis == "loaded" else "valid target rows",
                         "gap_between_domains_days": _gap_days(D, ma, mb), **d})
    return rows


def temporal_distribution(D: Data, masks: dict) -> list[dict]:
    rows = []
    for name in MAIN_SLICES + MINOR_SLICES:
        m = masks[name]
        for ptype, lab in (("month", D.month), ("season", D.season)):
            for per in sorted(set(lab[m].tolist())):
                pm = m & (lab == per)
                ld, tv, hv = pm & D.pd.loaded, pm & D.t_ok, pm & D.h_ok
                _, tn = unit_stat(D.temp[tv], D.night[tv])
                _, hn = unit_stat(D.humid[hv], D.night[hv])
                rows.append({"slice": name, "period_type": ptype, "period": per, "rows": int(pm.sum()),
                             "nights": int(np.unique(D.night[pm]).size),
                             "pressure_sum_median_loaded": float(np.median(D.pd.total[ld])) if ld.any() else None,
                             "active_channels_mean_loaded": round(float(D.pd.active[ld].mean()), 4) if ld.any() else None,
                             "temperature_median": float(np.median(D.temp[tv])) if tv.any() else None,
                             "temperature_iqr": iqr(D.temp[tv]) if tv.any() else None,
                             "humidity_median": float(np.median(D.humid[hv])) if hv.any() else None,
                             "humidity_iqr": iqr(D.humid[hv]) if hv.any() else None,
                             "temperature_night_median_median": float(np.median(tn)) if tn.size else None,
                             "humidity_night_median_median": float(np.median(hn)) if hn.size else None})
    return rows


def time_of_night(D: Data, masks: dict) -> list[dict]:
    rows = []
    # deviation of each valid target from its own night median (removes between-night level differences)
    for name in MAIN_SLICES:
        m = masks[name]
        dev = {}
        for var, x, ok in (("temperature", D.temp, D.t_ok), ("humidity", D.humid, D.h_ok)):
            v = m & ok
            un, vn = unit_stat(x[v], D.night[v])
            lut = dict(zip(un.tolist(), vn.tolist()))
            d = np.full(D.ts.size, np.nan)
            idx = np.flatnonzero(v)
            d[idx] = x[idx] - np.array([lut[n] for n in D.night[idx].tolist()])
            dev[var] = d
        for btype, lab in (("hour_of_day", D.hour), ("hours_since_session_start",
                                                    np.minimum(np.floor(D.rel_h), 12).astype(np.int64))):
            for b in sorted(set(lab[m].tolist())):
                bm = m & (lab == b)
                ld, tv, hv = bm & D.pd.loaded, bm & D.t_ok, bm & D.h_ok
                rows.append({"slice": name, "bin_type": btype, "bin": int(b), "rows": int(bm.sum()),
                             "share_of_slice_rows": round(float(bm.sum() / m.sum()), 5),
                             "loaded_share": round(float(ld.sum() / max(1, bm.sum())), 4),
                             "pressure_sum_median_loaded": float(np.median(D.pd.total[ld])) if ld.any() else None,
                             "active_channels_mean_loaded": round(float(D.pd.active[ld].mean()), 4) if ld.any() else None,
                             "temperature_median": float(np.median(D.temp[tv])) if tv.any() else None,
                             "humidity_median": float(np.median(D.humid[hv])) if hv.any() else None,
                             "temperature_dev_from_night_median": float(np.nanmedian(dev["temperature"][tv])) if tv.any() else None,
                             "humidity_dev_from_night_median": float(np.nanmedian(dev["humidity"][hv])) if hv.any() else None})
    return rows


def control_events(D: Data, masks: dict) -> list[dict]:
    parsed = [parse_event(e) for e in D.event_values]
    move = np.array([p[0] for p in parsed], object)[D.event_code]
    controls = [p[1] for p in parsed]
    rows = []
    for name in MAIN_SLICES + MINOR_SLICES:
        m = masks[name]
        hours = np.unique(D.ts[m] // 60).size / 60
        mv = Counter(move[m].tolist())
        n = m.sum()
        for k, c in sorted(mv.items(), key=lambda kv: -kv[1]):
            rows.append({"kind": "movement_label", "slice": name, "code": k or "(none)", "count": int(c),
                         "share_of_rows": round(c / n, 5)})
        codes_here = Counter()
        for code_idx, cnt in zip(*np.unique(D.event_code[m], return_counts=True)):
            for c in controls[code_idx]:
                codes_here[c] += int(cnt)
        for c, cnt in sorted(codes_here.items(), key=lambda kv: -kv[1]):
            rows.append({"kind": "control_code", "slice": name, "code": c, "count": cnt,
                         "per_100_recording_hours": round(100 * cnt / hours, 2)})
    # event-conditioned trajectories and context, pooled over the main slices and per slice when frequent enough
    code_rows: dict[str, list] = {}
    for idx, cs in enumerate(controls):
        for c in cs:
            code_rows.setdefault(c, []).append(idx)
    for c, idxs in sorted(code_rows.items()):
        ev_rows = np.flatnonzero(np.isin(D.event_code, idxs))
        for scope in ("all_main_slices",) + MAIN_SLICES:
            sel = ev_rows[np.isin(D.slice[ev_rows], MAIN_SLICES if scope == "all_main_slices" else (scope,))]
            if sel.size < MIN_EVENTS:
                continue
            tr_t = event_trajectory(D.ts, D.temp, D.t_ok, D.stream, sel, OFFSETS_S)
            tr_h = event_trajectory(D.ts, D.humid, D.h_ok, D.stream, sel, OFFSETS_S)
            base = {"kind": "event_conditioned", "slice": scope, "code": c, "count": int(sel.size),
                    "temperature_at_event_median": float(np.median(D.temp[sel][D.t_ok[sel]])) if D.t_ok[sel].any() else None,
                    "humidity_at_event_median": float(np.median(D.humid[sel][D.h_ok[sel]])) if D.h_ok[sel].any() else None,
                    "pressure_sum_at_event_median": float(np.median(D.pd.total[sel])),
                    "all_zero_share_at_event": round(float(D.pd.all_zero[sel].mean()), 4),
                    "hour_of_day_median": float(np.median(D.hour[sel]))}
            for o in OFFSETS_S:
                if o == 0:
                    continue
                base[f"d_temp_{o // 60:+d}min_median"] = float(np.nanmedian(tr_t[o])) if np.isfinite(tr_t[o]).any() else None
                base[f"d_humid_{o // 60:+d}min_median"] = float(np.nanmedian(tr_h[o])) if np.isfinite(tr_h[o]).any() else None
                base[f"n_{o // 60:+d}min"] = int(np.isfinite(tr_t[o]).sum())
            rows.append(base)
    return rows


def pressure_target(D: Data, masks: dict) -> list[dict]:
    rows = []
    for name in MAIN_SLICES:
        m = masks[name]
        for xname, x in (("pressure_sum", D.pd.total), ("active_channel_count", D.pd.active)):
            for yname, y, ok in (("temperature", D.temp, D.t_ok), ("humidity", D.humid, D.h_ok)):
                v = m & D.pd.loaded & ok
                un, xn = unit_stat(x[v], D.night[v])
                _, yn = unit_stat(y[v], D.night[v])
                bins = binned_trend(x[v], y[v], 10) if xname == "pressure_sum" else []
                if xname == "active_channel_count":
                    for k in range(1, 7):
                        km = v & (x == k)
                        if km.any():
                            bins.append({"bin": k, "x_low": k, "x_high": k, "n": int(km.sum()), "x_median": float(k),
                                         "y_median": float(np.median(y[km]))})
                rows.append({"kind": "summary", "slice": name, "x": xname, "y": yname, "rows": int(v.sum()),
                             "spearman_rows": spearman(x[v], y[v]), "nights": int(un.size),
                             "spearman_night_medians": spearman(xn, yn),
                             "y_median_top_minus_bottom_bin": round(bins[-1]["y_median"] - bins[0]["y_median"], 3) if bins else None})
                for bn in bins:
                    rows.append({"kind": "binned", "slice": name, "x": xname, "y": yname, **bn})
    return rows


def run_all(t: pa.Table) -> dict:
    D = Data(t)
    masks = D.masks()
    return {"data": D, "masks": masks,
            "domain_slice_summary": domain_slice_summary(D, masks),
            "pressure_distribution": pressure_distribution(D, masks),
            "target_distribution": target_distribution(D, masks),
            "domain_distance_matrix": distance_matrix(D, masks),
            "monthly_distribution": temporal_distribution(D, masks),
            "time_of_night_summary": time_of_night(D, masks),
            "control_event_summary": control_events(D, masks),
            "pressure_target_relation": pressure_target(D, masks)}
