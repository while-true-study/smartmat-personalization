"""Cross-source provenance fingerprints (P0 analysis A1). Read-only and descriptive.

Question: does the same physical recording appear under more than one source/subject?

Three comparison modes (docs/P0_A1_PROVENANCE_REPORT.md):
  A  exact_ts_values   parsed timestamp (1 s) + common channel values
  B  minute_ts_values  timestamp floored to the minute + common channel values
                       (detects exports that dropped seconds, e.g. legacy CSVs)
  C  value_sequence    k consecutive rows of common channel values, no timestamp
                       (detects copies whose timestamps were shifted or re-dated)

Fingerprints are 64-bit hashes used only as analysis keys. No timestamp or value of any
dataset is modified, and nothing here writes files.

Uninformative content is handled explicitly so that independent recordings do not
"match" by coincidence: a row is *informative* when its pressure sum is > 0 (something
is on the mat); mode C only uses k-grams whose rows are all informative and not all identical.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from src.data.raw_parser import DataRow, parse_file
from src.data.subject_mapping import resolve_source

CHANNELS: tuple[str, ...] = ("p1", "p2", "p3", "p4", "p5", "p6", "temp", "humid")
PRESSURE_CHANNELS: tuple[str, ...] = CHANNELS[:6]
MISSING = np.int16(-32768)
MODES: tuple[str, ...] = ("A_exact_ts_values", "B_minute_ts_values", "C_value_sequence")
DEFAULT_K = 5
_EPOCH = datetime(1970, 1, 1)
_MODE_SEED = {m: np.uint64(((i + 1) * 0x9E3779B97F4A7C15) % 2**64) for i, m in enumerate(MODES)}


# ---------------------------------------------------------------------------------------------
# Source data (compact, in-memory)
# ---------------------------------------------------------------------------------------------

@dataclass
class SourceData:
    """Compact numeric view of one source (or a union of sources) in file/row order."""
    source_id: str
    subject_id: str
    device_id: str
    files: list[str]
    ts: np.ndarray        # int64, seconds since 1970-01-01 of the parsed naive local timestamp
    values: np.ndarray    # int16 (n, len(CHANNELS)); MISSING where a channel is absent
    file_idx: np.ndarray  # int32 index into `files`

    @property
    def n(self) -> int:
        return int(self.ts.size)

    def channels_present(self) -> tuple[str, ...]:
        return tuple(c for j, c in enumerate(CHANNELS) if self.n and (self.values[:, j] != MISSING).any())

    @classmethod
    def from_rows(cls, source_id: str, subject_id: str, device_id: str,
                  files_rows: Iterable[tuple[str, Sequence[DataRow]]]) -> "SourceData":
        files, ts, vals, fidx = [], [], [], []
        for label, rows in files_rows:
            i = len(files)
            files.append(label)
            for r in rows:
                if r.ts is None:
                    continue
                v = list(r.pressure[:6]) + [MISSING] * (6 - min(6, len(r.pressure)))
                v += [MISSING if r.temp is None else r.temp, MISSING if r.humid is None else r.humid]
                ts.append((r.ts - _EPOCH) // timedelta(seconds=1))
                vals.append(v)
                fidx.append(i)
        arr = np.array(vals, dtype=np.float64).reshape(-1, len(CHANNELS))
        present = arr != MISSING
        if np.any(arr[present] != np.round(arr[present])):
            raise ValueError(f"{source_id}: non-integer sensor values are not supported by provenance hashing")
        if np.any((arr[present] <= MISSING) | (arr[present] > np.iinfo(np.int16).max)):
            raise ValueError(f"{source_id}: sensor values outside the int16 range")
        return cls(source_id, subject_id, device_id, files,
                   np.array(ts, dtype=np.int64), arr.astype(np.int16), np.array(fidx, dtype=np.int32))

    @classmethod
    def concat(cls, parts: Sequence["SourceData"], source_id: str, subject_id: str, device_id: str) -> "SourceData":
        files, offs = [], []
        for p in parts:
            offs.append(len(files))
            files.extend(p.files)
        return cls(
            source_id, subject_id, device_id, files,
            np.concatenate([p.ts for p in parts]) if parts else np.array([], np.int64),
            np.concatenate([p.values for p in parts]) if parts else np.empty((0, len(CHANNELS)), np.int16),
            np.concatenate([p.file_idx + o for p, o in zip(parts, offs)]) if parts else np.array([], np.int32),
        )


def load_sources(root: Path, manifest_rows: Sequence[dict]) -> dict[str, SourceData]:
    """Parse every sensor file of the manifest (read-only) into one SourceData per source_id."""
    by_source: dict[str, list[dict]] = {}
    for r in manifest_rows:
        if str(r["is_sensor_data"]) in ("True", "true", "1"):
            by_source.setdefault(r["source_id"], []).append(r)
    out = {}
    for sid, recs in by_source.items():
        src = resolve_source(recs[0]["source_relpath"])
        gen = ((r["source_relpath"], parse_file(root / r["source_relpath"], year_hint=src.year_hint).rows)
               for r in recs)
        out[sid] = SourceData.from_rows(sid, recs[0]["subject_id"], recs[0]["device_id"], gen)
    return out


# ---------------------------------------------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------------------------------------------

def _mix(x: np.ndarray) -> np.ndarray:
    """splitmix64 finaliser (vectorised, wrapping uint64 arithmetic)."""
    with np.errstate(over="ignore"):
        x = x + np.uint64(0x9E3779B97F4A7C15)
        x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return x ^ (x >> np.uint64(31))


def common_channels(a: SourceData, b: SourceData) -> tuple[str, ...]:
    pa, pb = set(a.channels_present()), set(b.channels_present())
    return tuple(c for c in CHANNELS if c in pa and c in pb)


def informative_mask(src: SourceData, channels: Sequence[str]) -> np.ndarray:
    cols = [CHANNELS.index(c) for c in channels if c in PRESSURE_CHANNELS]
    if not cols:
        return np.zeros(src.n, dtype=bool)
    p = src.values[:, cols].astype(np.int64)
    return (p != MISSING).all(axis=1) & (p.sum(axis=1) > 0)


def fingerprints(src: SourceData, mode: str, channels: Sequence[str], k: int = DEFAULT_K
                 ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (hash, valid, informative) arrays of length src.n for one mode.

    Mode C returns one k-gram hash per anchor row; `valid` marks usable anchors.
    """
    if mode not in MODES:
        raise ValueError(mode)
    cols = [CHANNELS.index(c) for c in channels]
    v = src.values[:, cols]
    valid = (v != MISSING).all(axis=1) if cols else np.zeros(src.n, dtype=bool)
    h = np.full(src.n, _MODE_SEED[mode], dtype=np.uint64)
    for j in range(v.shape[1]):
        h = _mix(h ^ v[:, j].astype(np.int64).astype(np.uint64))
    info = informative_mask(src, channels)

    if mode == "A_exact_ts_values":
        return _mix(h ^ src.ts.astype(np.uint64)), valid, info & valid
    if mode == "B_minute_ts_values":
        return _mix(h ^ (src.ts // 60).astype(np.uint64)), valid, info & valid

    n = src.n
    kg = np.zeros(n, dtype=np.uint64)
    ok = np.zeros(n, dtype=bool)
    if n >= k:
        m = n - k + 1
        g = h[:m].copy()
        row_ok = valid & info
        ok[:m] = row_ok[:m]
        not_constant = np.zeros(m, dtype=bool)
        for j in range(1, k):
            with np.errstate(over="ignore"):
                shifted = h[j:j + m] + np.uint64(j)
            g = _mix(g ^ _mix(shifted))
            ok[:m] &= row_ok[j:j + m] & (src.file_idx[j:j + m] == src.file_idx[:m])
            not_constant |= h[j:j + m] != h[:m]
        ok[:m] &= not_constant
        kg[:m] = g
    return kg, ok, ok.copy()


# ---------------------------------------------------------------------------------------------
# Pairwise comparison
# ---------------------------------------------------------------------------------------------

@dataclass
class Comparison:
    mode: str
    channels: tuple[str, ...]
    comparable_a: int
    comparable_b: int
    matched_a: int
    matched_b: int
    informative_matched_a: int
    informative_matched_b: int
    co_covered_dates: int
    overlapping_dates: int
    first_overlap: str
    last_overlap: str
    longest_matched_run: int
    longest_ordered_run: int
    offset_rows: int                 # informative matches with a unique counterpart in b
    offset_s_min: float | None
    offset_s_median: float | None
    offset_s_max: float | None
    # arrays kept for by-date and file-level analysis (not serialised)
    arrays: dict = field(default_factory=dict, repr=False)

    @property
    def ratio_a(self) -> float | None:
        return self.matched_a / self.comparable_a if self.comparable_a else None

    @property
    def ratio_b(self) -> float | None:
        return self.matched_b / self.comparable_b if self.comparable_b else None


def _longest_streak(cond: np.ndarray) -> int:
    if not cond.any():
        return 0
    padded = np.concatenate([[False], cond, [False]]).astype(np.int8)
    d = np.diff(padded)
    return int((np.flatnonzero(d == -1) - np.flatnonzero(d == 1)).max())


def _first_positions(needles: np.ndarray, hay: np.ndarray) -> np.ndarray:
    """Index of the first occurrence of each needle in hay, or -1."""
    if hay.size == 0 or needles.size == 0:
        return np.full(needles.size, -1, dtype=np.int64)
    order = np.argsort(hay, kind="stable")
    srt = hay[order]
    idx = np.searchsorted(srt, needles)
    idx_c = np.minimum(idx, srt.size - 1)
    found = (idx < srt.size) & (srt[idx_c] == needles)
    return np.where(found, order[idx_c], -1)


def _ordered_run(ha_f: np.ndarray, hb_f: np.ndarray, pos: np.ndarray, file_a: np.ndarray) -> int:
    """Longest run of consecutive a-rows that also sit on consecutive b-rows.

    An alignment continues from the previous b position when possible, so repeated
    fingerprints (e.g. identical rows within one minute) do not break a genuine copy.
    Cost is proportional to the number of matched rows.
    """
    hits = np.flatnonzero(pos >= 0)
    best = run = 0
    prev_j, prev_b = -2, -2
    nb = hb_f.size
    for j in hits:
        if run and j == prev_j + 1 and file_a[j] == file_a[prev_j] and prev_b + 1 < nb and hb_f[prev_b + 1] == ha_f[j]:
            prev_b += 1
            run += 1
        else:
            prev_b = int(pos[j])
            run = 1
        prev_j = j
        if run > best:
            best = run
    return best


def _day(ts: np.ndarray) -> np.ndarray:
    return ts // 86400


def _iso(sec: int) -> str:
    return (_EPOCH + timedelta(seconds=int(sec))).isoformat(sep=" ")


def compare(a: SourceData, b: SourceData, mode: str, k: int = DEFAULT_K,
            channels: Sequence[str] | None = None) -> Comparison:
    ch = tuple(channels) if channels is not None else common_channels(a, b)
    ha, va, ia = fingerprints(a, mode, ch, k)
    hb, vb, ib = fingerprints(b, mode, ch, k)
    ma = va & np.isin(ha, hb[vb])
    mb = vb & np.isin(hb, ha[va])

    # sequence-level: longest run of consecutive a-rows (same file) that all have a match
    streak = ma[:-1] & ma[1:] & (a.file_idx[:-1] == a.file_idx[1:]) if a.n > 1 else np.array([], bool)
    longest_matched = (_longest_streak(streak) + 1) if ma.any() else 0

    # ordered run: informative rows only; consecutive in a AND consecutive in b
    fa = np.flatnonzero(ia)
    fb = np.flatnonzero(ib)
    pos = _first_positions(ha[fa], hb[fb])
    hit = pos >= 0
    longest_ordered = _ordered_run(ha[fa], hb[fb], pos, a.file_idx[fa])
    # time offset b - a, only where the fingerprint occurs exactly once in b (unambiguous mapping)
    srt = np.sort(hb[fb])
    occurrences = np.searchsorted(srt, ha[fa], "right") - np.searchsorted(srt, ha[fa], "left")
    unique_hit = hit & (occurrences == 1)
    offsets = (b.ts[fb[pos[unique_hit]]] - a.ts[fa[unique_hit]]).astype(np.float64)

    days_a, days_b = _day(a.ts), _day(b.ts)
    co = np.intersect1d(np.unique(days_a[va]), np.unique(days_b[vb]))
    matched_days = np.unique(days_a[ma])
    return Comparison(
        mode=mode, channels=ch,
        comparable_a=int(va.sum()), comparable_b=int(vb.sum()),
        matched_a=int(ma.sum()), matched_b=int(mb.sum()),
        informative_matched_a=int((ma & ia).sum()), informative_matched_b=int((mb & ib).sum()),
        co_covered_dates=int(co.size), overlapping_dates=int(matched_days.size),
        first_overlap=_iso(a.ts[ma].min()) if ma.any() else "",
        last_overlap=_iso(a.ts[ma].max()) if ma.any() else "",
        longest_matched_run=longest_matched, longest_ordered_run=longest_ordered,
        offset_rows=int(offsets.size),
        offset_s_min=float(offsets.min()) if offsets.size else None,
        offset_s_median=float(np.median(offsets)) if offsets.size else None,
        offset_s_max=float(offsets.max()) if offsets.size else None,
        arrays={"ha": ha, "va": va, "ia": ia, "ma": ma, "hb": hb, "vb": vb, "ib": ib, "mb": mb,
                "fa": fa, "fb": fb, "pos": pos},
    )


def by_date(a: SourceData, b: SourceData, res: Comparison) -> list[dict]:
    """Per calendar date: rows and matches on each side (dates with data on both sides or any match)."""
    arr = res.arrays
    da, db = _day(a.ts), _day(b.ts)
    days = np.union1d(np.unique(da[arr["va"]]), np.unique(db[arr["vb"]]))
    if days.size == 0:
        return []
    lo = int(days.min())
    size = int(days.max()) - lo + 1

    def count(d, mask):
        return np.bincount((d[mask] - lo).astype(np.int64), minlength=size)

    ca, cb = count(da, arr["va"]), count(db, arr["vb"])
    xa, xb = count(da, arr["ma"]), count(db, arr["mb"])
    ia = count(da, arr["ma"] & arr["ia"])
    out = []
    for off in np.flatnonzero(((ca > 0) & (cb > 0)) | (xa > 0) | (xb > 0)):
        out.append({
            "date": (_EPOCH + timedelta(days=int(lo + off))).date().isoformat(),
            "comparable_rows_a": int(ca[off]), "comparable_rows_b": int(cb[off]),
            "matched_rows_a": int(xa[off]), "matched_rows_b": int(xb[off]),
            "informative_matched_a": int(ia[off]),
            "match_ratio_a": round(xa[off] / ca[off], 6) if ca[off] else None,
            "match_ratio_b": round(xb[off] / cb[off], 6) if cb[off] else None,
        })
    return out


def _edge_profile(mask: np.ndarray) -> tuple[int, int, int]:
    """(leading, trailing, interior) counts of False around the True block(s)."""
    t = np.flatnonzero(mask)
    if t.size == 0:
        return int(mask.size), 0, 0
    lead, trail = int(t[0]), int(mask.size - 1 - t[-1])
    return lead, trail, int(mask.size - t.size - lead - trail)


def file_correspondence(a: SourceData, b: SourceData, res: Comparison) -> list[dict]:
    """For each file of `a` with informative matches: best-matching file of `b` and how they align."""
    arr = res.arrays
    fa, fb, pos = arr["fa"], arr["fb"], arr["pos"]
    hit = pos >= 0
    out = []
    for ia_file in np.unique(a.file_idx[fa[hit]]):
        sel = hit & (a.file_idx[fa] == ia_file)
        b_files = Counter(b.file_idx[fb[pos[sel]]].tolist())
        ib_file, _ = b_files.most_common(1)[0]
        ra = np.flatnonzero((a.file_idx == ia_file) & arr["va"])
        rb = np.flatnonzero((b.file_idx == ib_file) & arr["vb"])
        m_a = np.isin(arr["ha"][ra], arr["hb"][rb])
        m_b = np.isin(arr["hb"][rb], arr["ha"][ra])
        la, ta, ina = _edge_profile(m_a)
        lb, tb, inb = _edge_profile(m_b)
        out.append({
            "file_a": a.files[ia_file], "file_b": b.files[ib_file],
            "n_b_files_matched": len(b_files),
            "comparable_a": int(ra.size), "matched_a_in_file_b": int(m_a.sum()),
            "ratio_a": round(float(m_a.mean()), 6) if ra.size else None,
            "comparable_b": int(rb.size), "matched_b_in_file_a": int(m_b.sum()),
            "ratio_b": round(float(m_b.mean()), 6) if rb.size else None,
            "a_unmatched_leading": la, "a_unmatched_trailing": ta, "a_unmatched_interior": ina,
            "b_unmatched_leading": lb, "b_unmatched_trailing": tb, "b_unmatched_interior": inb,
            "a_first_ts": _iso(a.ts[ra].min()) if ra.size else "", "a_last_ts": _iso(a.ts[ra].max()) if ra.size else "",
            "b_first_ts": _iso(b.ts[rb].min()) if rb.size else "", "b_last_ts": _iso(b.ts[rb].max()) if rb.size else "",
        })
    return out


# ---------------------------------------------------------------------------------------------
# Interpretation helpers (flags only; no conclusions about identity)
# ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Thresholds:
    """A cross-subject pair is flagged when any of these is reached in a mode."""
    min_informative_matches: int = 10
    min_ordered_run: int = 10


def pair_scope(subject_a: str, subject_b: str) -> str:
    """Same-subject pairs (e.g. User02 devices 22480/22482) are never cross-subject conflicts."""
    return "same_subject" if subject_a == subject_b else "cross_subject"


def is_suspicious(scope: str, res: Comparison, th: Thresholds = Thresholds()) -> bool:
    if scope != "cross_subject":
        return False
    return (max(res.informative_matched_a, res.informative_matched_b) >= th.min_informative_matches
            or res.longest_ordered_run >= th.min_ordered_run)


def summary_record(a: SourceData, b: SourceData, res: Comparison, scope: str, th: Thresholds) -> dict:
    return {
        "scope": scope, "subject_a": a.subject_id, "subject_b": b.subject_id,
        "source_a": a.source_id, "source_b": b.source_id,
        "device_a": a.device_id, "device_b": b.device_id,
        "comparison_mode": res.mode, "channels_used": ",".join(res.channels),
        "comparable_rows_a": res.comparable_a, "comparable_rows_b": res.comparable_b,
        "matched_rows_a": res.matched_a, "matched_rows_b": res.matched_b,
        "match_ratio_a": None if res.ratio_a is None else round(res.ratio_a, 6),
        "match_ratio_b": None if res.ratio_b is None else round(res.ratio_b, 6),
        "informative_matched_a": res.informative_matched_a, "informative_matched_b": res.informative_matched_b,
        "co_covered_dates": res.co_covered_dates, "overlapping_dates": res.overlapping_dates,
        "first_overlap": res.first_overlap, "last_overlap": res.last_overlap,
        "longest_matched_run": res.longest_matched_run, "longest_ordered_run": res.longest_ordered_run,
        "ts_offset_rows": res.offset_rows,
        "ts_offset_s_min": res.offset_s_min, "ts_offset_s_median": res.offset_s_median,
        "ts_offset_s_max": res.offset_s_max,
        "suspicious": is_suspicious(scope, res, th),
    }
