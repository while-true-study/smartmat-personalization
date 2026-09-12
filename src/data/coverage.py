"""Subject / device / temporal coverage and confounding (P0 analysis A11). Read-only and descriptive.

Builds a coverage view of who was recorded when, on which device, sensor phase, schema and sampling regime,
and measures how far subject identity is confounded with calendar time, season and device. Nothing here
creates a canonical dataset, removes rows, resamples, builds splits or runs a model.

Conventions
  recording minute   a clock minute with at least one row; active recording hours = recording minutes / 60,
                     so the same definition works for 3 s logs, minute-resolution legacy rows and unions of
                     concurrent devices
  recording day      calendar date with at least one row
  usable day         calendar date with at least USABLE_DAY_MIN audit-valid recording minutes (descriptive)
  audit-valid row    audit view (identical upload-chunk copies excluded) with a schema/encoding-valid pressure
                     frame (D-018, proposed) and both targets valid (A8 / D-016, proposed) - applied in memory
  season             meteorological, northern hemisphere: DJF winter, MAM spring, JJA summer, SON autumn
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Sequence

import numpy as np

DAY_S = 86400
USABLE_DAY_MIN = 60                      # audit-valid recording minutes for a "usable" day (descriptive)
SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
           6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
ELIGIBILITY = ("eligible", "eligible_with_caveat", "not_eligible")
EVENT_STATUSES = ("confirmed_metadata_boundary", "documented_metadata_event", "observed_schema_boundary",
                  "observed_sampling_regime_change", "observed_distribution_shift", "unresolved_anomaly",
                  "target_quality_episode")
_EPOCH = date(1970, 1, 1)


# ---------------------------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------------------------

def day_of(day_idx: int) -> date:
    return _EPOCH + timedelta(days=int(day_idx))


def month_of(day_idx: int) -> str:
    return day_of(day_idx).isoformat()[:7]


def iso_week_of(day_idx: int) -> str:
    y, w, _ = day_of(day_idx).isocalendar()
    return f"{y}-W{w:02d}"


def quarter_of(day_idx: int) -> str:
    d = day_of(day_idx)
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def season_of(day_idx: int) -> str:
    d = day_of(day_idx)
    s = SEASONS[d.month]
    year = d.year - 1 if d.month in (1, 2) else d.year       # a winter is named after its December
    return f"{year}-{s}"


def month_range(first: str, last: str) -> list[str]:
    """All months from 'YYYY-MM' to 'YYYY-MM' inclusive."""
    y, m = int(first[:4]), int(first[5:7])
    out = []
    while f"{y}-{m:02d}" <= last:
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


# ---------------------------------------------------------------------------------------------
# Coverage of one domain (a set of rows of one subject, device, phase or union)
# ---------------------------------------------------------------------------------------------

def minutes(ts: np.ndarray) -> np.ndarray:
    return np.unique(np.asarray(ts) // 60)


def days(ts: np.ndarray) -> np.ndarray:
    return np.unique(np.asarray(ts) // DAY_S)


def dominant_step(ts: np.ndarray, max_step_s: int = 60) -> str:
    """Most frequent positive step within recordings ('minute_resolution' for HH:MM timestamps)."""
    dt = np.diff(np.sort(np.asarray(ts)))
    pos = dt[(dt > 0) & (dt <= max_step_s)]
    if pos.size == 0:
        return "unknown"
    vals, cnt = np.unique(pos, return_counts=True)
    mode = int(vals[np.argmax(cnt)])
    if mode == 60 and (dt == 0).mean() > 0.5:
        return "minute_resolution"
    return f"{mode}s"


def coverage_summary(ts: np.ndarray, audit_valid: np.ndarray, t_valid: np.ndarray, h_valid: np.ndarray,
                     raw_rows: int | None = None, usable_min: int = USABLE_DAY_MIN) -> dict:
    """Coverage statistics of one domain. ts: audit-view timestamps (any order)."""
    ts = np.asarray(ts)
    if ts.size == 0:
        return {"raw_rows": raw_rows, "audit_view_rows": 0}
    order = np.argsort(ts, kind="stable")
    ts, audit_valid, t_valid, h_valid = ts[order], audit_valid[order], t_valid[order], h_valid[order]
    vm = ts[audit_valid] // 60
    per_day = np.bincount((np.unique(vm) * 60 // DAY_S - ts[0] // DAY_S).astype(np.int64)) if vm.size else np.array([])
    return {
        "first_timestamp": int(ts[0]), "last_timestamp": int(ts[-1]),
        "span_days": round((int(ts[-1]) - int(ts[0])) / DAY_S, 2),
        "recording_days": int(days(ts).size), "usable_recording_days": int((per_day >= usable_min).sum()),
        "recording_nights": int(np.unique((ts - DAY_S // 2) // DAY_S).size),
        "raw_rows": raw_rows, "audit_view_rows": int(ts.size), "audit_valid_rows": int(audit_valid.sum()),
        "active_recording_hours": round(minutes(ts).size / 60, 2),
        "audit_valid_hours": round(np.unique(vm).size / 60, 2),
        "dominant_sampling_interval": dominant_step(ts),
        "temperature_coverage": round(float(t_valid.mean()), 5), "humidity_coverage": round(float(h_valid.mean()), 5),
    }


def monthly_coverage(ts: np.ndarray, valid_target: np.ndarray, months: Sequence[str]) -> list[dict]:
    """Per month: recording days, active recording hours and rows with both targets valid."""
    ts = np.asarray(ts)
    d = ts // DAY_S
    mon = np.array([month_of(x) for x in np.unique(d)])
    day_month = dict(zip(np.unique(d).tolist(), mon.tolist()))
    row_month = np.array([day_month[x] for x in d.tolist()]) if ts.size else np.array([], dtype=object)
    out = []
    for m in months:
        sel = row_month == m
        out.append({"month": m, "recording_days": int(np.unique(d[sel]).size),
                    "active_recording_hours": round(minutes(ts[sel]).size / 60, 2),
                    "valid_target_rows": int(valid_target[sel].sum())})
    return out


def overlap(ts_a: np.ndarray, ts_b: np.ndarray) -> dict:
    """Overlap of two domains on actually recorded days, ISO weeks, months and recording minutes."""
    da, db = set(days(ts_a).tolist()), set(days(ts_b).tolist())
    wa, wb = {iso_week_of(x) for x in da}, {iso_week_of(x) for x in db}
    ma, mb = {month_of(x) for x in da}, {month_of(x) for x in db}
    shared_min = np.intersect1d(minutes(ts_a), minutes(ts_b), assume_unique=True)
    out = {"overlap_days": len(da & db), "overlap_weeks": len(wa & wb), "overlap_months": len(ma & mb),
           "overlap_recording_hours": round(shared_min.size / 60, 2),
           "days_only_a": len(da - db), "days_only_b": len(db - da),
           "shared_months": ";".join(sorted(ma & mb)), "shared_weeks": ";".join(sorted(wa & wb))}
    if da and db:
        a0, a1, b0, b1 = int(np.min(ts_a)), int(np.max(ts_a)), int(np.min(ts_b)), int(np.max(ts_b))
        gap = max(b0 - a1, a0 - b1, 0)
        out["gap_between_ranges_h"] = round(gap / 3600, 2)        # 0 when the date ranges intersect
    return out


def season_hours(ts: np.ndarray) -> dict[str, float]:
    """Active recording hours per season label."""
    m = minutes(ts)
    lab = np.array([season_of(int(x) * 60 // DAY_S) for x in m]) if m.size else np.array([])
    return {s: round(float((lab == s).sum()) / 60, 2) for s in sorted(set(lab.tolist()))}


def regime_runs(labels: Sequence[str], dates: Sequence[str]) -> list[tuple[str, str, str]]:
    """(label, first_date, last_date) for runs of equal consecutive labels (e.g. per-day sampling regime)."""
    out: list[tuple[str, str, str]] = []
    for lab, d in zip(labels, dates):
        if out and out[-1][0] == lab:
            out[-1] = (lab, out[-1][1], d)
        else:
            out.append((lab, d, d))
    return out


def daily_labels(ts: np.ndarray, label_rows: np.ndarray) -> tuple[list[str], list[str]]:
    """Majority label per recording day (for regime / container periods)."""
    d = np.asarray(ts) // DAY_S
    dates, labs = [], []
    for x in np.unique(d):
        sel = d == x
        vals, cnt = np.unique(label_rows[sel], return_counts=True)
        dates.append(day_of(int(x)).isoformat())
        labs.append(str(vals[np.argmax(cnt)]))
    return labs, dates


def daily_step_regime(ts: np.ndarray) -> tuple[list[str], list[str]]:
    """Per recording day: dominant positive step (e.g. '2s', '3s')."""
    ts = np.sort(np.asarray(ts))
    d = ts // DAY_S
    dates, labs = [], []
    for x in np.unique(d):
        dates.append(day_of(int(x)).isoformat())
        labs.append(dominant_step(ts[d == x]))
    return labs, dates


# ---------------------------------------------------------------------------------------------
# Cohort eligibility (structure only, no model)
# ---------------------------------------------------------------------------------------------

def check(value: float | None, threshold: float) -> str:
    return "unknown" if value is None else ("pass" if value >= threshold else "fail")


def eligibility(checks: dict[str, str], caveats: Iterable[str] = ()) -> str:
    """not_eligible if any check fails or is unknown; eligible_with_caveat if any caveat; else eligible."""
    if any(v in ("fail", "unknown") for v in checks.values()):
        return "not_eligible"
    return "eligible_with_caveat" if any(True for _ in caveats) else "eligible"


def chronological_capacity(night_idx: np.ndarray, min_nights: int) -> dict:
    """Whether the recorded nights allow an earlier adaptation span, a buffer and a later test span."""
    n = np.unique(np.asarray(night_idx))
    if n.size == 0:
        return {"nights": 0, "can_split": False}
    half = n.size // 2
    return {"nights": int(n.size), "span_nights": int(n[-1] - n[0] + 1),
            "first_half_nights": int(half), "second_half_nights": int(n.size - half),
            "can_split": bool(n.size >= 2 * min_nights + 1)}
