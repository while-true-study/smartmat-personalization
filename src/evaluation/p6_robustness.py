"""P6 robustness and uncertainty analysis of the frozen P5 results (analysis-only; D-041, D-047).

Nothing here trains, selects or evaluates a model, and no P3/P4/P5 artifact is changed. Inputs:
- `paper/tables/p5_per_night.csv` (committed P5 per-night metrics): bootstrap (A) and drift sensitivity (B);
- canonical_v1 through the P5 windows (targets only; no model): temporal level trajectory (B);
- the P5 run predictions (`outputs/runs/p5/`, reproducible bitwise from `bce5e06`) and canonical control codes
  (test-time stratification only, never an input): User02 device / heater-context strata.
A = pre-declared by protocol v1.0; B = post-hoc secondary / robustness (D-047).
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from src.data import paths
from src.evaluation.domain_shift import parse_event
from src.evaluation.metrics import TARGETS
from src.evaluation.protocol import load_protocol

PRIMARY_SEED = 0
ADAPT_BUDGETS = (1, 3, 7, 14)
DRIFT_STARTS = (12, 14, 16, 18, 21)
MIN_NIGHTS = 10
ROLLING_NIGHTS = 7
HEATER_WINDOW_S = 3600
HEATER_CODES = ("AHON", "AHOF")
METRICS = ("mae", "rmse", "abs_bias")


class P6Error(RuntimeError):
    pass


def bootstrap_settings() -> tuple[int, int, float]:
    """(resamples, seed, level) frozen in protocol.yaml metrics.bootstrap (D-041)."""
    b = load_protocol()["metrics"]["bootstrap"]
    if b["unit"] != "night" or (b["resamples"], b["seed"], b["level"]) != (2000, 0, 0.95):
        raise P6Error(f"bootstrap settings differ from protocol v1.0: {b}")
    return int(b["resamples"]), int(b["seed"]), float(b["level"])


# -------------------------------------------------------------------------------------------------- inputs

def tables_dir() -> Path:
    return paths.PROJECT_ROOT / "paper" / "tables"


def metrics_dir() -> Path:
    return paths.PROJECT_ROOT / "outputs" / "metrics" / "p6"


def read_csv(p: Path) -> list[dict]:
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_per_night(path: Path | None = None) -> list[dict]:
    rows = read_csv(tables_dir() / "p5_per_night.csv" if path is None else path)
    out = []
    for r in rows:
        out.append({"subject_id": r["subject_id"], "budget_nights": int(r["budget_nights"]), "seed": int(r["seed"]),
                    "night_id": r["night_id"], "night_ordinal": int(r["night_ordinal"]),
                    "primary_test": int(r["primary_test"]), "target": r["target"], "mae": float(r["mae"]),
                    "rmse": float(r["rmse"]), "bias": float(r["bias"]), "n_windows": int(r["n_windows"])})
    return out


def night_arrays(rows: list[dict], subject: str, budget: int, seed: int, target: str, *,
                 primary_only: bool = True, start: int | None = None) -> dict[str, np.ndarray]:
    """Per-night arrays of one subject x budget x seed x target, sorted by night id."""
    sel = [r for r in rows if r["subject_id"] == subject and r["budget_nights"] == budget and r["seed"] == seed
           and r["target"] == target and (not primary_only or r["primary_test"] == 1)
           and (start is None or r["night_ordinal"] >= start)]
    sel.sort(key=lambda r: r["night_id"])
    ids = [r["night_id"] for r in sel]
    if len(ids) != len(set(ids)):
        raise P6Error(f"{subject} b={budget} seed {seed} {target}: duplicate nights")
    return {"night": np.array(ids), "ordinal": np.array([r["night_ordinal"] for r in sel]),
            "n": np.array([r["n_windows"] for r in sel], np.float64),
            "mae": np.array([r["mae"] for r in sel]), "rmse": np.array([r["rmse"] for r in sel]),
            "bias": np.array([r["bias"] for r in sel])}


def pair(base: dict, adapted: dict) -> None:
    """Paired nights: identical night sets in the same order and identical window counts per night."""
    if base["night"].size == 0 or not np.array_equal(base["night"], adapted["night"]):
        raise P6Error("base and adapted nights differ: the night pairing is broken")
    if not np.array_equal(base["n"], adapted["n"]):
        raise P6Error("base and adapted window counts differ on a night: the pairing is broken")


# ----------------------------------------------------------------------------------------------- bootstrap core

def resample_counts(n_nights: int, resamples: int, seed: int) -> np.ndarray:
    """(resamples, n_nights) counts of each night in each resample (nights drawn with replacement)."""
    idx = np.random.default_rng(seed).integers(0, n_nights, size=(resamples, n_nights))
    counts = np.zeros((resamples, n_nights))
    np.add.at(counts, (np.repeat(np.arange(resamples), n_nights), idx.ravel()), 1)
    return counts


def weighted(counts: np.ndarray, arr: dict) -> dict[str, np.ndarray]:
    """Subject-level metrics over the resampled windows (every window of a drawn night kept; window-weighted)."""
    w = counts * arr["n"]
    s = w.sum(axis=1)
    return {"mae": (w * arr["mae"]).sum(1) / s, "rmse": np.sqrt((w * arr["rmse"] ** 2).sum(1) / s),
            "bias": (w * arr["bias"]).sum(1) / s}


def paired_effects(counts: np.ndarray, base: dict, adapted: dict) -> dict[str, np.ndarray]:
    """Adaptation effect per resample: base − adapted for MAE/RMSE, |bias_base| − |bias_adapted|. Positive = better."""
    b, a = weighted(counts, base), weighted(counts, adapted)
    return {"mae": b["mae"] - a["mae"], "rmse": b["rmse"] - a["rmse"],
            "abs_bias": np.abs(b["bias"]) - np.abs(a["bias"])}


def per_night_effects(base: dict, adapted: dict) -> dict[str, np.ndarray]:
    return {"mae": base["mae"] - adapted["mae"], "rmse": base["rmse"] - adapted["rmse"],
            "abs_bias": np.abs(base["bias"]) - np.abs(adapted["bias"])}


def interval(stat: np.ndarray, level: float) -> tuple[float, float]:
    a = (1 - level) / 2 * 100
    lo, hi = np.percentile(stat, [a, 100 - a])
    return float(lo), float(hi)


def side(lo: float, hi: float) -> str:
    return "above_zero" if lo > 0 else "below_zero" if hi < 0 else "includes_zero"


def bootstrap_rows(rows: list[dict], seeds: tuple[int, ...] = (PRIMARY_SEED,), subjects: tuple[str, ...] | None = None,
                   resamples: int | None = None, rng_seed: int | None = None, level: float | None = None
                   ) -> list[dict]:
    """Night-level paired cluster bootstrap of the adaptation effect, per subject x target x budget x metric x seed."""
    r_def, s_def, l_def = bootstrap_settings()
    resamples = r_def if resamples is None else resamples
    rng_seed = s_def if rng_seed is None else rng_seed
    level = l_def if level is None else level
    subjects = tuple(sorted({r["subject_id"] for r in rows})) if subjects is None else subjects
    out = []
    for subject in subjects:
        ref = night_arrays(rows, subject, 0, seeds[0], TARGETS[0])
        counts = resample_counts(ref["night"].size, resamples, rng_seed)     # the same nights for every comparison
        full = np.ones((1, ref["night"].size))
        for seed in seeds:
            for t in TARGETS:
                base = night_arrays(rows, subject, 0, seed, t)
                pair(ref, base)
                for b in ADAPT_BUDGETS:
                    adapted = night_arrays(rows, subject, b, seed, t)
                    pair(base, adapted)
                    boot = paired_effects(counts, base, adapted)
                    point = paired_effects(full, base, adapted)
                    pn = per_night_effects(base, adapted)
                    wb, wa = weighted(full, base), weighted(full, adapted)
                    for m in METRICS:
                        lo, hi = interval(boot[m], level)
                        bv = abs(wb["bias"][0]) if m == "abs_bias" else wb[m][0]
                        av = abs(wa["bias"][0]) if m == "abs_bias" else wa[m][0]
                        out.append({"subject_id": subject, "target": t, "budget_nights": b, "metric": m,
                                    "seed": seed, "n_nights": int(base["night"].size),
                                    "n_windows": int(base["n"].sum()), "base_value": float(bv),
                                    "adapted_value": float(av), "point_estimate": float(point[m][0]),
                                    "ci_lower": lo, "ci_upper": hi, "interval": side(lo, hi),
                                    "night_mean_delta": float(pn[m].mean()),
                                    "night_median_delta": float(np.median(pn[m])),
                                    "proportion_nights_improved": float((pn[m] > 0).mean()),
                                    "n_resamples": resamples, "rng_seed": rng_seed, "level": level})
    return out


def consistency_with_p5(rows: list[dict], p5_by_seed: list[dict]) -> float:
    """Largest |difference| between window-weighted per-night aggregates and the P5 primary per-seed metrics."""
    worst = 0.0
    for r in p5_by_seed:
        if r["span"] != "primary":
            continue
        arr = night_arrays(rows, r["subject_id"], int(r["budget_nights"]), int(r["seed"]), r["target"])
        w = weighted(np.ones((1, arr["night"].size)), arr)
        for m in ("mae", "rmse", "bias"):
            worst = max(worst, abs(float(w[m][0]) - float(r[m])))
    return worst


# ------------------------------------------------------------------------------------------ drift sensitivity

def drift_rows(rows: list[dict], seeds: tuple[int, ...] = (0, 1, 2)) -> list[dict]:
    """Post-hoc: MAE and gain vs b = 0 on the span of nights >= s, for every s in DRIFT_STARTS (D-047 B.4)."""
    out = []
    subjects = sorted({r["subject_id"] for r in rows})
    for s in DRIFT_STARTS:
        for subject in subjects:
            for t in TARGETS:
                for b in (0, *ADAPT_BUDGETS):
                    base_row = {"start_night": s, "subject_id": subject, "target": t, "budget_nights": b}
                    if b > 0 and not b + 1 < s:
                        out.append({**base_row, "status": "excluded: span overlaps adaptation/buffer nights"})
                        continue
                    maes, maes0, n_n, n_w = [], [], None, None
                    for seed in seeds:
                        a = night_arrays(rows, subject, b, seed, t, primary_only=False, start=s)
                        z = night_arrays(rows, subject, 0, seed, t, primary_only=False, start=s)
                        pair(z, a)
                        if a["night"].size < MIN_NIGHTS:
                            raise P6Error(f"{subject} s={s}: {a['night'].size} nights < {MIN_NIGHTS}")
                        one = np.ones((1, a["night"].size))
                        maes.append(float(weighted(one, a)["mae"][0]))
                        maes0.append(float(weighted(one, z)["mae"][0]))
                        n_n, n_w = int(a["night"].size), int(a["n"].sum())
                    e0, eb = float(np.mean(maes0)), float(np.mean(maes))
                    g = [(m0 - mb) / m0 * 100 for m0, mb in zip(maes0, maes)]
                    out.append({**base_row, "status": "evaluated", "n_nights": n_n, "n_windows": n_w,
                                "E0_mae": e0, "Eb_mae": eb, "delta_E": e0 - eb, "G_pct": (e0 - eb) / e0 * 100,
                                "direction": "better" if eb < e0 else "worse" if eb > e0 else "equal",
                                "seeds_improved": int(sum(x > 0 for x in g)), "n_seeds": len(seeds),
                                "seed_G_min": min(g), "seed_G_max": max(g)})
    return out


# --------------------------------------------------------------------------------------- level trajectory

def rolling_centred(values: np.ndarray, width: int = ROLLING_NIGHTS) -> np.ndarray:
    """Centred mean over `width` consecutive recorded nights, truncated at the ends of the series."""
    half = width // 2
    return np.array([values[max(0, i - half):i + half + 1].mean() for i in range(len(values))])


def level_rows(sess, pool_means: dict[str, list[float]], primary_from: int = 16) -> tuple[list[dict], list[dict]]:
    """Post-hoc descriptive (no model): per-night target means, rolling means and span means per subject x target."""
    nights_out, spans_out = [], []
    for subject in sorted(pool_means):
        sw0 = sess.windows(subject, 0)
        m = sw0.mask("test")                                   # b = 0: every night is test
        nid, ordn, y = sw0.prov["night_id"][m], sw0.prov["night_ordinal"][m], sw0.targets[m]
        uniq, inv = np.unique(nid, return_inverse=True)
        order = np.argsort([int(ordn[inv == i][0]) for i in range(len(uniq))])
        cnt = np.bincount(inv)
        for ti, t in enumerate(TARGETS):
            means = np.bincount(inv, weights=y[:, ti]) / cnt
            ordinal = np.array([int(ordn[inv == i][0]) for i in range(len(uniq))])
            prim = ordinal >= primary_from
            prim_mean = float(y[np.isin(nid, uniq[prim]), ti].mean())
            roll = rolling_centred(means[order])
            for k, i in enumerate(order):
                nights_out.append({"subject_id": subject, "target": t, "night_id": uniq[i],
                                   "night_ordinal": int(ordinal[i]), "primary_test": int(prim[i]),
                                   "night_mean": float(means[i]), "rolling_mean_7": float(roll[k]),
                                   "n_windows": int(cnt[i]), "minus_primary_mean": float(means[i] - prim_mean),
                                   "training_pool_mean": pool_means[subject][ti]})
            spans = [("primary", f"nights >= {primary_from}", float(prim_mean))]
            for b in ADAPT_BUDGETS:
                swb = sess.windows(subject, b)
                a = swb.mask("adaptation")
                spans.append((f"adaptation_b{b}", f"nights 1-{b}", float(swb.targets[a, ti].mean())))
            for s in DRIFT_STARTS:
                spans.append((f"future_from_{s}", f"nights >= {s}",
                              float(y[np.isin(nid, uniq[ordinal >= s]), ti].mean())))
            spans.append(("training_pool", "base model outer training pool", float(pool_means[subject][ti])))
            for name, desc, v in spans:
                spans_out.append({"subject_id": subject, "target": t, "span": name, "description": desc,
                                  "mean": v, "minus_primary_mean": v - prim_mean})
    return nights_out, spans_out


def mismatch_consistency(spans: list[dict], bias0: dict[tuple[str, str], float],
                         gain: dict[tuple[str, str, int], float]) -> list[dict]:
    """Descriptive check (D-047 B.5): expected improvement if |adaptation − primary| < |bias_0|; compared with P5 G."""
    out = []
    for (subject, t), b0 in sorted(bias0.items()):
        for b in ADAPT_BUDGETS:
            d = next(r["minus_primary_mean"] for r in spans if r["subject_id"] == subject and r["target"] == t
                     and r["span"] == f"adaptation_b{b}")
            expected = "better" if abs(d) < abs(b0) else "worse"
            g = gain[(subject, t, b)]
            observed = "better" if g > 0 else "worse" if g < 0 else "equal"
            out.append({"subject_id": subject, "target": t, "budget_nights": b, "adaptation_minus_primary": d,
                        "abs_base_bias": abs(b0), "expected_direction": expected, "p5_G_pct": g,
                        "observed_direction": observed, "consistent": expected == observed})
    return out


# ------------------------------------------------------------------------------------ User02 device / context

def heater_events(subject: str = "User02") -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Device -> (sorted timestamps, code) of AHON/AHOF control codes in canonical event_raw (never a model input)."""
    import pyarrow as pa
    import pyarrow.compute as pc
    from src.evaluation.canonical_input import load_primary
    t = load_primary(["subject_id", "device_id", "timestamp", "event_raw"])
    t = t.filter(pc.equal(t["subject_id"].cast(pa.string()), subject))
    t = t.filter(pc.fill_null(pc.match_substring_regex(t["event_raw"].cast(pa.string()), "|".join(HEATER_CODES)),
                              False))
    dev = t["device_id"].cast(pa.string()).to_numpy(zero_copy_only=False).astype(str)
    ts = t["timestamp"].cast(pa.timestamp("s")).cast(pa.int64()).to_numpy()
    ev = t["event_raw"].cast(pa.string()).to_numpy(zero_copy_only=False)
    out = {}
    for d in np.unique(dev):
        rows = []
        for i in np.flatnonzero(dev == d):
            if ev[i] is None or not any(c in str(ev[i]) for c in HEATER_CODES):
                continue
            codes = [c for c in parse_event(ev[i])[1] if c in HEATER_CODES]
            if codes:
                rows.append((int(ts[i]), codes[-1]))           # several codes in one row: the last one wins
        rows.sort()
        out[str(d)] = (np.array([r[0] for r in rows], np.int64), np.array([r[1] for r in rows], dtype=object))
    return out


def heater_context(device: np.ndarray, target_ts: np.ndarray, events: dict, window_s: int = HEATER_WINDOW_S
                   ) -> np.ndarray:
    """Most recent AHON/AHOF on the same device within `window_s` before the target timestamp (D-047 A.2)."""
    out = np.full(len(device), "no_AHON_AHOF_60min", dtype=object)
    for d, (ets, codes) in events.items():
        m = device == d
        if not m.any() or ets.size == 0:
            continue
        k = np.searchsorted(ets, target_ts[m], side="right") - 1
        ok = (k >= 0) & (target_ts[m] - ets[np.maximum(k, 0)] <= window_s)
        lab = np.where(ok, np.array([f"after_{c}_60min" for c in codes], dtype=object)[np.maximum(k, 0)],
                       "no_AHON_AHOF_60min")
        out[m] = lab
    return out


def device_strata(prov: dict, heater: np.ndarray) -> list[tuple[str, str, np.ndarray]]:
    """(stratum type, name, mask) over the primary-span windows of User02 (D-047 A.2, B.6)."""
    dev, cq = prov["device_id"], prov["channel_quality_phase"]
    out = []
    for d in ("22480", "22482"):
        md = dev == d
        out.append(("device", d, md))
        for h in ("after_AHON_60min", "after_AHOF_60min", "no_AHON_AHOF_60min"):
            out.append(("device_x_heater", f"{d}/{h}", md & (heater == h)))
    for q in ("normal", "p1_response_shift", "p1_transition"):
        mq = (dev == "22482") & (cq == q)
        out.append(("22482_quality_phase", f"22482/{q}", mq))
        for h in ("after_AHON_60min", "after_AHOF_60min", "no_AHON_AHOF_60min"):
            out.append(("22482_quality_phase_x_heater", f"22482/{q}/{h}", mq & (heater == h)))
    return out


def device_context_rows(preds: dict[tuple[int, int], tuple], events: dict, budgets: tuple[int, ...],
                        seeds: tuple[int, ...]) -> tuple[list[dict], list[dict]]:
    """User02 primary-span strata: metrics per budget x seed (+ seed mean) and seed-0 bootstrap for b0 vs b14.

    preds[(budget, seed)] = (y, p, prov) of the primary-span windows, in the same window order for every key.
    """
    resamples, rng_seed, level = bootstrap_settings()
    y_ref, _, prov_ref = preds[(0, seeds[0])]
    heater = heater_context(prov_ref["device_id"], prov_ref["target_ts"], events)
    strata = device_strata(prov_ref, heater)
    metric_rows, boot_rows = [], []
    for kind, name, mask in strata:
        n_w = int(mask.sum())
        n_n = int(np.unique(prov_ref["night_id"][mask]).size) if n_w else 0
        for b in budgets:
            vals = {"mae": [], "rmse": [], "bias": []}
            for s in seeds:
                y, p, prov = preds[(b, s)]
                if not (np.array_equal(prov["night_id"], prov_ref["night_id"])
                        and np.array_equal(prov["target_ts"], prov_ref["target_ts"])
                        and np.array_equal(prov["device_id"], prov_ref["device_id"])):
                    raise P6Error(f"b={b} seed {s}: windows differ from the reference order")
                if not n_w:
                    continue
                for i, t in enumerate(TARGETS):
                    e = p[mask, i] - y[mask, i]
                    rec = {"mae": float(np.abs(e).mean()), "rmse": float(np.sqrt((e ** 2).mean())),
                           "bias": float(e.mean())}
                    for k, v in rec.items():
                        metric_rows.append({"stratum_type": kind, "stratum": name, "budget_nights": b, "seed": s,
                                            "target": t, "metric": k, "value": v, "n_windows": n_w,
                                            "n_nights": n_n})
        if n_w == 0:
            metric_rows.append({"stratum_type": kind, "stratum": name, "budget_nights": "", "seed": "",
                                "target": "", "metric": "", "value": "", "n_windows": 0, "n_nights": 0})
            continue
        for i, t in enumerate(TARGETS):
            if n_n < MIN_NIGHTS or 0 not in budgets or 14 not in budgets:
                boot_rows.append({"stratum_type": kind, "stratum": name, "target": t, "seed": PRIMARY_SEED,
                                  "quantity": "", "n_nights": n_n, "n_windows": n_w,
                                  "note": f"descriptive only (< {MIN_NIGHTS} nights)"})
                continue
            y0, p0, _ = preds[(0, PRIMARY_SEED)]
            _, p14, _ = preds[(14, PRIMARY_SEED)]
            res = stratum_bootstrap(p0[mask, i] - y0[mask, i], p14[mask, i] - y0[mask, i],
                                    prov_ref["night_id"][mask], resamples, rng_seed, level)
            for q, r in res.items():
                boot_rows.append({"stratum_type": kind, "stratum": name, "target": t, "seed": PRIMARY_SEED,
                                  "quantity": q, "point_estimate": r["point"], "ci_lower": r["ci_lower"],
                                  "ci_upper": r["ci_upper"], "interval": r["interval"], "n_nights": n_n,
                                  "n_windows": n_w, "n_resamples": resamples, "rng_seed": rng_seed, "note": ""})
    means = {}
    for r in metric_rows:
        if r["value"] != "":
            means.setdefault((r["stratum_type"], r["stratum"], r["budget_nights"], r["target"], r["metric"]),
                             []).append(r)
    for (kind, name, b, t, k), rs in means.items():
        v = np.array([r["value"] for r in rs])
        metric_rows.append({"stratum_type": kind, "stratum": name, "budget_nights": b, "seed": "mean", "target": t,
                            "metric": k, "value": float(v.mean()), "seed_sd": float(v.std(ddof=1)) if len(v) > 1
                            else 0.0, "n_windows": rs[0]["n_windows"], "n_nights": rs[0]["n_nights"]})
    return metric_rows, boot_rows


def night_sums(err: np.ndarray, nights: np.ndarray, uniq: np.ndarray) -> dict[str, np.ndarray]:
    idx = np.searchsorted(uniq, nights)
    n = np.bincount(idx, minlength=len(uniq)).astype(np.float64)
    return {"n": n, "abs": np.bincount(idx, np.abs(err), len(uniq)), "sq": np.bincount(idx, err ** 2, len(uniq)),
            "sum": np.bincount(idx, err, len(uniq))}


def stratum_bootstrap(e0: np.ndarray, e14: np.ndarray, nights: np.ndarray, resamples: int, seed: int, level: float
                      ) -> dict:
    """Night-cluster paired bootstrap inside one stratum: ΔMAE (b0 − b14) and the b14 / b0 bias."""
    uniq = np.unique(nights)
    s0, s14 = night_sums(e0, nights, uniq), night_sums(e14, nights, uniq)
    counts = resample_counts(len(uniq), resamples, seed)
    w = counts * s0["n"]
    tot = w.sum(1)
    mae0 = (counts * s0["abs"]).sum(1) / tot
    mae14 = (counts * s14["abs"]).sum(1) / tot
    b0 = (counts * s0["sum"]).sum(1) / tot
    b14 = (counts * s14["sum"]).sum(1) / tot
    res = {}
    for name, stat, point in (("delta_mae_b0_minus_b14", mae0 - mae14,
                               s0["abs"].sum() / s0["n"].sum() - s14["abs"].sum() / s14["n"].sum()),
                              ("bias_b14", b14, s14["sum"].sum() / s14["n"].sum()),
                              ("bias_b0", b0, s0["sum"].sum() / s0["n"].sum())):
        lo, hi = interval(stat, level)
        res[name] = {"point": float(point), "ci_lower": lo, "ci_upper": hi, "interval": side(lo, hi)}
    return res
