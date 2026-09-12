"""Cross-file duplicate and temporal-overlap analysis within one subject/device (P0 analysis A5).

Read-only and descriptive: nothing is deleted, merged, re-timed or written by this module.
Duplicate-removal policies are only *simulated* as row counts.

Row relations are kept apart and never lumped into one "duplicate":
  R1 exact duplicate            same timestamp, sensor/target values (P1..P6, temp, humid) AND event text
  R2 metadata-only difference   same timestamp and sensor/target values, different event text
  R3 conflicting timestamp      same timestamp, different sensor/target values
  R4 repeated sequence          a contiguous block of rows occurs in the same order in two files
  R5 time overlap only          two files' time ranges overlap, but their rows differ

Comparisons run inside one (subject_id, device_id) group. Devices of the same subject are
different groups; equality across devices is reported separately as a diagnostic only.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.data.provenance import (
    CHANNELS, SourceData, aligned_runs, code_text, fingerprints, first_positions, mix64,
)

GAP_BINS_S = (0, 10, 60, 300, 1800, 7200)          # descriptive bins, not a session rule
CONTROL_TOKENS = ("EVENT:", "AHON", "AHOF", "BHSDOWN", "BHNTSDOWN", "BCSUP", "FON", "FOF", "FOH", "STEMP",
                  "SLIMIT", "SMINLIMIT", "SCHATIDS", "AMODE", "AIHON", "AIHOFF", "AIDONE", "MMODE", "MON", "MOF",
                  "WSTOP")


# ---------------------------------------------------------------------------------------------
# Fingerprints
# ---------------------------------------------------------------------------------------------

@dataclass
class RowKeys:
    st: np.ndarray    # sensor-target fingerprint: timestamp + P1..P6 + temp + humid
    full: np.ndarray  # full-row fingerprint: sensor-target + event text


def row_keys(src: SourceData) -> RowKeys:
    """Reuses the provenance fingerprint (mode A: exact timestamp + values) as the sensor-target key."""
    st, _, _ = fingerprints(src, "A_exact_ts_values", src.channels_present() or CHANNELS)
    ev = src.event_code if src.event_code is not None else np.zeros(src.n, np.uint64)
    return RowKeys(st=st, full=mix64(st ^ mix64(ev)))


def _file_scoped(key: np.ndarray, file_idx: np.ndarray) -> np.ndarray:
    return mix64(key ^ mix64(file_idx.astype(np.uint64) + np.uint64(0x5bd1e995)))


# ---------------------------------------------------------------------------------------------
# Group-level counts and hypothetical policy impact
# ---------------------------------------------------------------------------------------------

def duplicate_counts(src: SourceData, keys: RowKeys) -> dict:
    n = src.n
    if n == 0:
        return {"raw_rows": 0}
    u_full = np.unique(keys.full).size
    u_st, st_first = np.unique(keys.st, return_index=True)
    u_ts = np.unique(src.ts).size
    u_full_file = np.unique(_file_scoped(keys.full, src.file_idx)).size
    # timestamps shared by >1 row, and those with >1 distinct sensor-target value
    _, ts_counts = np.unique(src.ts, return_counts=True)
    _, st_per_ts = np.unique(src.ts[st_first], return_counts=True)
    # sensor-target groups whose rows differ only in event text
    _, full_first = np.unique(keys.full, return_index=True)
    _, full_per_st = np.unique(keys.st[full_first], return_counts=True)
    within_extra = n - u_full_file
    within_adjacent = _adjacent_exact_duplicates(src, keys)
    return {
        "raw_rows": n,
        "unique_full_rows": int(u_full),
        "unique_sensor_target_rows": int(u_st.size),
        "unique_timestamps": int(u_ts),
        "exact_duplicate_rows": int(n - u_full),                      # R1 extra copies
        "exact_duplicate_ratio": round((n - u_full) / n, 6),
        "exact_duplicates_across_files": int(u_full_file - u_full),
        "exact_duplicates_within_file": int(within_extra),
        "exact_duplicates_within_file_adjacent": int(within_adjacent),
        "metadata_only_extra_rows": int(u_full - u_st.size),         # R2
        "metadata_only_groups": int((full_per_st > 1).sum()),
        "timestamps_with_multiple_rows": int((ts_counts > 1).sum()),
        "conflicting_timestamps": int((st_per_ts > 1).sum()),        # R3
        "conflicting_extra_rows": int(u_st.size - u_ts),
    }


def _adjacent_exact_duplicates(src: SourceData, keys: RowKeys) -> int:
    """Exact duplicates that directly follow their twin in the same file (same second logged twice)."""
    if src.n < 2:
        return 0
    same = (keys.full[1:] == keys.full[:-1]) & (src.file_idx[1:] == src.file_idx[:-1])
    return int(same.sum())


def policy_impact(counts: dict, minute_resolution: bool) -> list[dict]:
    """Row counts under hypothetical policies. Nothing is removed."""
    n = counts["raw_rows"]
    rows = [
        ("raw", n, "", "no change"),
        ("A1_exact_duplicates_across_files", n - counts["exact_duplicates_across_files"], "",
         "remove extra copies of fully identical rows that also occur in another file"),
        ("A_all_exact_duplicates", counts["unique_full_rows"], "",
         "remove every extra copy of a fully identical row (incl. within-file repeats)"),
        ("B_same_timestamp_same_values", counts["unique_sensor_target_rows"],
         counts["metadata_only_groups"], "one row per timestamp+values; event text must be chosen where it differs"),
        ("C_one_row_per_timestamp", counts["unique_timestamps"], counts["conflicting_timestamps"],
         "one representative per timestamp; conflicting timestamps need a rule"),
    ]
    out = []
    for name, kept, unresolved, desc in rows:
        status = "simulated"
        if minute_resolution and name != "raw":
            status = "not_applicable_minute_resolution"
        elif name == "C_one_row_per_timestamp" and counts["conflicting_timestamps"]:
            status = "requires_decision"
        elif name == "B_same_timestamp_same_values" and counts["metadata_only_groups"]:
            status = "requires_decision_metadata"
        out.append({"policy": name, "raw_rows": n, "rows_after": int(kept), "rows_removed": int(n - kept),
                    "pct_removed": round(100 * (n - kept) / n, 4) if n else None,
                    "unresolved_items": unresolved, "status": status, "description": desc})
    return out


# ---------------------------------------------------------------------------------------------
# Files, file pairs and repeated sequences
# ---------------------------------------------------------------------------------------------

def file_ranges(src: SourceData) -> list[dict]:
    out = []
    for f in range(len(src.files)):
        idx = np.flatnonzero(src.file_idx == f)
        if idx.size == 0:
            out.append({"file": src.files[f], "rows": 0})
            continue
        ts = np.sort(src.ts[idx])
        gaps = np.diff(ts)
        chunks = src.chunk_idx[idx] if src.chunk_idx is not None else np.array([-1])
        out.append({
            "file": src.files[f], "rows": int(idx.size), "first_ts": int(ts[0]), "last_ts": int(ts[-1]),
            "duration_h": round(float(ts[-1] - ts[0]) / 3600, 3), "unique_timestamps": int(np.unique(ts).size),
            "upload_chunks": int(np.unique(chunks[chunks >= 0]).size),
            "internal_gaps_gt_5min": int((gaps > 300).sum()), "internal_gaps_gt_30min": int((gaps > 1800).sum()),
            "internal_gaps_gt_2h": int((gaps > 7200).sum()),
            "max_internal_gap_h": round(float(gaps.max()) / 3600, 3) if gaps.size else 0.0,
        })
    return out


def overlapping_file_pairs(src: SourceData, keys: RowKeys) -> list[dict]:
    """Every pair of files in the group whose time ranges intersect (not only adjacent dates)."""
    spans = []
    for f in range(len(src.files)):
        idx = np.flatnonzero(src.file_idx == f)
        if idx.size:
            spans.append((int(src.ts[idx].min()), int(src.ts[idx].max()), f, idx))
    spans.sort()
    out = []
    for i, (a0, a1, fa, ia) in enumerate(spans):
        for b0, b1, fb, ib in spans[i + 1:]:
            if b0 > a1:
                break
            w0, w1 = max(a0, b0), min(a1, b1)
            ta, tb = src.ts[ia], src.ts[ib]
            in_a = (ta >= w0) & (ta <= w1)
            in_b = (tb >= w0) & (tb <= w1)
            common_ts = np.intersect1d(ta[in_a], tb[in_b])
            shared_st_a = np.isin(keys.st[ia], keys.st[ib])
            shared_full_a = np.isin(keys.full[ia], keys.full[ib])
            shared_ts_with_same_values = np.unique(ta[shared_st_a]).size
            n_win = min(int(in_a.sum()), int(in_b.sum()))
            shared = int(shared_st_a.sum())
            relation = ("time_overlap_only" if shared == 0 else
                        "duplicate_block" if n_win and shared >= 0.95 * n_win else "partial_duplicate")
            out.append({
                "file_a": src.files[fa], "file_b": src.files[fb], "overlap_start": w0, "overlap_end": w1,
                "overlap_h": round((w1 - w0) / 3600, 3), "rows_a_in_overlap": int(in_a.sum()),
                "rows_b_in_overlap": int(in_b.sum()), "overlapping_timestamps": int(common_ts.size),
                "shared_sensor_target_rows": shared, "shared_full_rows": int(shared_full_a.sum()),
                "conflicting_timestamps_between_files": int(common_ts.size - shared_ts_with_same_values),
                "relation": relation, "_fa": fa, "_fb": fb,
            })
    return out


def pair_runs(src: SourceData, keys: RowKeys, pair: dict) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int, int]]]:
    """Row indices of the two files of an overlapping pair and their aligned runs (a_start, b_start, length)."""
    ia = np.flatnonzero(src.file_idx == pair["_fa"])
    ib = np.flatnonzero(src.file_idx == pair["_fb"])
    pos = first_positions(keys.st[ia], keys.st[ib])
    return ia, ib, aligned_runs(keys.st[ia], keys.st[ib], pos, np.zeros(ia.size, np.int32))


def within_file_runs(src: SourceData, keys: RowKeys, f: int) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int, int]]]:
    """For one file: row indices, positions of later copies, and runs (copy_start, original_start, length)."""
    idx = np.flatnonzero(src.file_idx == f)
    full = keys.full[idx]
    pos = first_positions(full, full)                  # earliest identical row in the same file
    rep = np.flatnonzero(pos != np.arange(idx.size))   # rows that are later copies
    return idx, rep, aligned_runs(full[rep], full, pos[rep], np.zeros(rep.size, np.int32))


def _block_rows(src: SourceData, keys: RowKeys, pairs: list[dict], min_len: int):
    """Yield (original_rows, copy_rows) of every repeated block of >= min_len fully identical rows."""
    for p in pairs:
        if not p["shared_sensor_target_rows"]:
            continue
        ia, ib, runs = pair_runs(src, keys, p)
        for a0, b0, length in runs:
            if length >= min_len:
                ra, rb = ia[a0:a0 + length], ib[b0:b0 + length]
                same = keys.full[rb] == keys.full[ra]
                yield ra[same], rb[same]
    for f in range(len(src.files)):
        idx, rep, runs = within_file_runs(src, keys, f)
        for a0, b0, length in runs:
            if length >= min_len:
                yield idx[b0:b0 + length], idx[rep[a0:a0 + length]]


def upload_copy_mask(src: SourceData, keys: RowKeys, pairs: list[dict], min_len: int = 10) -> np.ndarray:
    """Audit-only view: rows that are later, fully identical copies of a repeated block (>= min_len rows).

    Between files, the copy in the later-starting file of each overlapping pair is marked; inside one
    file, the later occurrence of a repeated block is marked. Same-second rows with different values,
    isolated identical rows and anything outside a repeated block are never marked. Nothing is removed.
    """
    mask = np.zeros(src.n, bool)
    for _, copies in _block_rows(src, keys, pairs, min_len):
        mask[copies] = True
    return mask


def repeated_block_members(src: SourceData, keys: RowKeys, pairs: list[dict], min_len: int = 10) -> np.ndarray:
    """Rows that belong to a repeated block, as original or as copy (for gap-context flags)."""
    mask = np.zeros(src.n, bool)
    for orig, copies in _block_rows(src, keys, pairs, min_len):
        mask[orig] = True
        mask[copies] = True
    return mask


def subject_device_groups(manifest_rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Sensor sources grouped by (subject_id, device_id) with their format families and dataset roles."""
    groups: dict[tuple[str, str], dict] = {}
    for r in manifest_rows:
        if str(r["is_sensor_data"]) != "True":
            continue
        g = groups.setdefault((r["subject_id"], r["device_id"]), {"sources": set(), "families": set(), "roles": set()})
        g["sources"].add(r["source_id"])
        g["families"].add(r["format_family"])
        g["roles"].add(r["dataset_role"])
    return groups


def repeated_sequences(src: SourceData, keys: RowKeys, pairs: list[dict], min_len: int = 10) -> list[dict]:
    """Contiguous blocks (row order in each file) shared by two files of the group."""
    out = []
    for p in pairs:
        if not p["shared_sensor_target_rows"]:
            continue
        ia, ib, runs = pair_runs(src, keys, p)
        in_runs = 0
        for a0, b0, length in runs:
            if length < min_len:
                continue
            in_runs += length
            ra, rb = ia[a0:a0 + length], ib[b0:b0 + length]
            out.append({
                "file_a": p["file_a"], "file_b": p["file_b"],
                "first_matching_ts": int(src.ts[ra].min()), "last_matching_ts": int(src.ts[ra].max()),
                "matched_rows": int(length), "duration_h": round(float(src.ts[ra].max() - src.ts[ra].min()) / 3600, 3),
                "a_line_start": _line(src, ra[0]), "a_line_end": _line(src, ra[-1]),
                "b_line_start": _line(src, rb[0]), "b_line_end": _line(src, rb[-1]),
                "exact_sequence": True,
                "identical_incl_event": bool(np.array_equal(keys.full[ra], keys.full[rb])),
                "at_end_of_a": bool(a0 + length == ia.size), "at_start_of_b": bool(b0 == 0),
                "at_start_of_a": bool(a0 == 0), "at_end_of_b": bool(b0 + length == ib.size),
                "scope": "between_files",
            })
        p["rows_in_sequences"] = in_runs
        p["longest_sequence_rows"] = max((r[2] for r in runs), default=0)
    return out


def within_file_repeated_blocks(src: SourceData, keys: RowKeys, min_len: int = 10) -> list[dict]:
    """Contiguous blocks that occur twice inside the same file (e.g. an upload chunk written again)."""
    out = []
    for f in range(len(src.files)):
        idx, rep, runs = within_file_runs(src, keys, f)
        if rep.size < min_len:
            continue
        for a0, b0, length in runs:
            if length < min_len:
                continue
            copy, orig = idx[rep[a0:a0 + length]], idx[b0:b0 + length]
            out.append({
                "file_a": src.files[f], "file_b": src.files[f],
                "first_matching_ts": int(src.ts[copy].min()), "last_matching_ts": int(src.ts[copy].max()),
                "matched_rows": int(length), "duration_h": round(float(src.ts[copy].max() - src.ts[copy].min()) / 3600, 3),
                "a_line_start": _line(src, copy[0]), "a_line_end": _line(src, copy[-1]),
                "b_line_start": _line(src, orig[0]), "b_line_end": _line(src, orig[-1]),
                "exact_sequence": True, "identical_incl_event": True,
                "at_end_of_a": False, "at_start_of_b": False, "at_start_of_a": False, "at_end_of_b": False,
                "scope": "within_file",
            })
    return out


def _line(src: SourceData, i: int) -> int:
    return int(src.line_no[i]) if src.line_no is not None else -1


def repeated_chunk_keys(src: SourceData, keys: RowKeys) -> list[dict]:
    """JSON upload-chunk keys that occur in more than one file, and whether their rows are the same."""
    if src.chunk_idx is None or not src.chunk_keys:
        return []
    by_key: dict[str, list[int]] = {}
    for ci, k in enumerate(src.chunk_keys):
        by_key.setdefault(k, []).append(ci)
    out = []
    for k, cis in by_key.items():
        if len(cis) < 2:
            continue
        sets = [np.unique(keys.st[src.chunk_idx == ci]) for ci in cis]
        files = sorted({src.files[int(src.file_idx[np.flatnonzero(src.chunk_idx == ci)[0]])] for ci in cis})
        if all(np.array_equal(sets[0], s) for s in sets[1:]):
            relation = "identical"
        elif all(np.isin(x, y).all() or np.isin(y, x).all() for i, x in enumerate(sets) for y in sets[i + 1:]):
            relation = "one_copy_is_subset"
        else:
            relation = "different"
        out.append({"chunk_key": k, "n_files": len(files), "files": " | ".join(files),
                    "rows_per_copy": ",".join(str(s.size) for s in sets), "relation": relation})
    return out


# ---------------------------------------------------------------------------------------------
# Conflicting timestamps (R3) and metadata-only differences (R2)
# ---------------------------------------------------------------------------------------------

def _has_control(code) -> bool:
    text = code_text(int(code)) or ""
    return any(t in text for t in CONTROL_TOKENS)


def timestamp_conflicts(src: SourceData, keys: RowKeys) -> list[dict]:
    """One record per timestamp that carries two or more different sensor/target value sets."""
    u_st, first = np.unique(keys.st, return_index=True)
    ts_u = src.ts[first]
    ts_vals, counts = np.unique(ts_u, return_counts=True)
    conflict_ts = ts_vals[counts > 1]
    if conflict_ts.size == 0:
        return []
    sel = np.flatnonzero(np.isin(src.ts, conflict_ts))
    sel = sel[np.lexsort((sel, src.ts[sel]))]
    out = []
    bounds = np.flatnonzero(np.diff(src.ts[sel])) + 1
    for grp in np.split(sel, bounds):
        _, rep = np.unique(keys.st[grp], return_index=True)
        reps = grp[np.sort(rep)]                      # one row per distinct value set, file order
        v = src.values[reps].astype(np.int64)
        p, t, h = v[:, :6], v[:, 6], v[:, 7]
        pdiff = int((p.max(axis=0) - p.min(axis=0)).max())
        tdiff, hdiff = int(t.max() - t.min()), int(h.max() - h.min())
        files = sorted({src.files[int(src.file_idx[i])] for i in grp})
        same_file = len(files) == 1
        # origin: if one file holds every distinct value set, the conflict arises inside that file (and may be
        # copied along with its upload chunk into other files); otherwise the files disagree with each other
        per_file = {}
        for i in grp:
            per_file.setdefault(int(src.file_idx[i]), set()).add(int(keys.st[i]))
        full_file = next((f for f, s in per_file.items() if len(s) == reps.size), None)
        origin = "within_file" if full_file is not None else "between_files"
        adjacent = False
        if full_file is not None and src.line_no is not None:
            lines = np.sort(src.line_no[[i for i in grp if int(src.file_idx[i]) == full_file]])
            adjacent = bool(np.all(np.diff(lines) == 1))
        sentinel = bool(((t == 0) & (h == 0)).any())
        control = src.event_code is not None and any(_has_control(c) for c in src.event_code[grp])
        kind = ("sensor_and_target_conflict" if pdiff and (tdiff or hdiff) else
                "target_conflict" if (tdiff or hdiff) else "sensor_conflict")
        ts0 = int(src.ts[grp[0]])
        out.append({
            "ts": ts0, "date": ts0 // 86400, "n_rows": int(grp.size),
            "n_distinct_values": int(reps.size), "kind": kind, "max_pressure_diff": pdiff,
            "temp_diff": tdiff, "humid_diff": hdiff, "involves_th_sentinel": sentinel,
            "involves_control_event": bool(control), "same_file": same_file, "origin": origin,
            "adjacent_lines": adjacent, "files": " | ".join(files),
        })
    return out


def metadata_only_differences(src: SourceData, keys: RowKeys, limit: int = 20) -> list[dict]:
    """Most frequent event-text pairs among rows that are identical in timestamp and sensor/target values."""
    if src.event_code is None:
        return []
    order = np.lexsort((src.event_code, keys.st))
    st_s, ev_s = keys.st[order], src.event_code[order]
    new_st = np.concatenate([[True], st_s[1:] != st_s[:-1]])
    grp_id = np.cumsum(new_st) - 1
    diff_ev = np.concatenate([[False], (ev_s[1:] != ev_s[:-1]) & ~new_st[1:]])
    pairs: dict[tuple[str, str], int] = {}
    for j in np.flatnonzero(diff_ev):
        a, b = code_text(int(ev_s[j - 1])) or "?", code_text(int(ev_s[j])) or "?"
        if grp_id[j] == grp_id[j - 1]:
            key = tuple(sorted((a, b)))
            pairs[key] = pairs.get(key, 0) + 1
    return [{"event_a": a, "event_b": b, "count": c}
            for (a, b), c in sorted(pairs.items(), key=lambda kv: -kv[1])[:limit]]


# ---------------------------------------------------------------------------------------------
# File boundaries vs recording continuity (evidence for "source file != session")
# ---------------------------------------------------------------------------------------------

def file_boundaries(src: SourceData, pairs: list[dict]) -> list[dict]:
    """For consecutive files in time order: gap or overlap at the boundary, and whether rows are shared."""
    spans = []
    for f in range(len(src.files)):
        idx = np.flatnonzero(src.file_idx == f)
        if idx.size:
            spans.append((int(src.ts[idx].min()), int(src.ts[idx].max()), f))
    spans.sort()
    shared = {(p["_fa"], p["_fb"]): p["shared_sensor_target_rows"] for p in pairs}
    shared.update({(b, a): v for (a, b), v in list(shared.items())})
    out = []
    for (a0, a1, fa), (b0, b1, fb) in zip(spans, spans[1:]):
        delta = b0 - a1
        s = shared.get((fa, fb), 0)
        if delta < 0:
            kind = "overlap_with_repeated_rows" if s else "overlap_distinct_rows"
        else:
            kind = "gap"
        out.append({"file_a": src.files[fa], "file_b": src.files[fb], "delta_s": int(delta), "shared_rows": int(s),
                    "boundary_kind": kind, "gap_bin": gap_bin(delta)})
    return out


def gap_bin(delta_s: int) -> str:
    if delta_s < 0:
        return "overlap"
    for lo, hi in zip(GAP_BINS_S, GAP_BINS_S[1:]):
        if delta_s <= hi:
            return f"{lo}-{hi}s"
    return f">{GAP_BINS_S[-1]}s"


# ---------------------------------------------------------------------------------------------
# Cross-device diagnostic (never a dedup candidate)
# ---------------------------------------------------------------------------------------------

def cross_device_equality(a: SourceData, ka: RowKeys, b: SourceData, kb: RowKeys) -> dict:
    return {
        "device_a": a.device_id, "device_b": b.device_id, "subject_a": a.subject_id, "subject_b": b.subject_id,
        "shared_timestamps": int(np.intersect1d(a.ts, b.ts).size),
        "shared_sensor_target_rows": int(np.isin(ka.st, kb.st).sum()),
        "shared_full_rows": int(np.isin(ka.full, kb.full).sum()),
        "note": "same timestamps across devices are expected (simultaneous recording) and are not duplicates",
    }
