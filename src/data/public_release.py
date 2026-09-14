"""Public release v1 (D-049, D-050): deterministic builder, public loader, privacy validator, equivalence gate.

Private side (canonical_v1 available): `build_release` derives the release from canonical rows, the committed v1.0
split files and the frozen P5 plan / reference runs. It then runs the privacy validator and the private/public
equivalence gate before it writes the manifest; any failure stops the build.

Public side (release only): `PublicRelease` verifies every artifact against the manifest and rebuilds the exact fold
(`FoldData`) and subject (`SubjectWindows`) window arrays that the P3/P4/P5 code consumes.

Time (D-049): per subject, integer seconds since local midnight of the calendar date of the subject's first night.
Night keys are `D####` relative day indices; readable times are `D#### HH:MM:SS`. No calendar date is written.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from src.data.io_guard import remove_file, write_csv, write_json, write_parquet, write_text
from src.evaluation.p5_personalization import SubjectWindows

RELEASE_VERSION = "public_release_v1"
DAY_S, NOON_S = 86400, 43200
N_STEPS, N_CH = 8, 6
PRESSURE_COLS = [f"s{k}_p{c}" for k in range(N_STEPS) for c in range(1, N_CH + 1)]
WINDOW_COLUMNS = ["window_index", "subject_id", "device_id", "session_id", "sensor_phase", "channel_quality_phase",
                  "night_id", "night_ordinal", "window_start_time_s", "target_time_s", "in_loso", "in_rq2",
                  *PRESSURE_COLS, "temperature", "humidity", "target_temp_valid", "target_humidity_valid"]
ALLOWED_SUBJECTS = ("User01", "User02", "User07")
ALLOWED_DEVICES = {"User01": ("unknown",), "User02": ("22480", "22482"), "User07": ("unknown",)}
ALLOWED_SENSOR_PHASES = ("s1", "s2", "not_applicable")
ALLOWED_CQ_PHASES = ("normal", "p1_transition", "p1_response_shift")
HEATER_CODES = ("AHON", "AHOF")
SPLIT_RELS = ("v1.0_loso/outer_folds.csv", "v1.0_loso/inner_folds.csv", "v1.0_personalization/chronological.csv")
DATA_ARTIFACTS = ("windows.parquet", *(f"splits/{r}" for r in SPLIT_RELS), "control_events.csv",
                  "p5_plan_public.yaml", "reference_digests.json", "schema.json")
ARTIFACTS = (*DATA_ARTIFACTS, "excluded_sources.csv", "README.md")
ROW_GROUP = 131072


class ReleaseError(RuntimeError):
    pass


# -------------------------------------------------------------------------------------------------- D-049 time

def anchor_of(first_ts: int) -> int:
    """Local midnight (naive seconds) of the calendar date of the night holding `first_ts` (night = date(t − 12 h))."""
    return int((int(first_ts) - NOON_S) // DAY_S * DAY_S)


def subject_anchors(subject: np.ndarray, ts: np.ndarray) -> dict[str, int]:
    return {str(s): anchor_of(int(ts[subject == s].min())) for s in np.unique(subject)}


def night_key_ts(ts, anchor: int) -> np.ndarray:
    """`D####` relative night day of absolute naive timestamps (same noon boundary as protocol.night_id)."""
    day = (np.asarray(ts, np.int64) - NOON_S - anchor) // DAY_S + 1
    if np.any(day < 1):
        raise ReleaseError("a timestamp precedes the subject's first night")
    return np.char.add("D", np.char.zfill(day.astype(str), 4))


def night_key_date(date_str: str, anchor: int) -> str:
    day = int(np.datetime64(date_str, "D").astype(np.int64)) - anchor // DAY_S + 1
    if day < 1:
        raise ReleaseError("a night precedes the subject's first night")
    return f"D{day:04d}"


def parse_abs(text: str) -> int:
    return int(np.datetime64(text.replace(" ", "T"), "s").astype(np.int64))


def rel_str(rel_s: int) -> str:
    rel_s = int(rel_s)
    if rel_s < 0:
        raise ReleaseError("negative relative time")
    day, sec = rel_s // DAY_S + 1, rel_s % DAY_S
    return f"D{day:04d} {sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def parse_rel(text: str) -> int:
    m = re.fullmatch(r"D(\d{4}) (\d{2}):(\d{2}):(\d{2})", text)
    if not m:
        raise ReleaseError(f"not a relative time: {text!r}")
    d, h, mi, s = (int(x) for x in m.groups())
    return (d - 1) * DAY_S + h * 3600 + mi * 60 + s


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_array(a: np.ndarray) -> str:
    a = np.ascontiguousarray(a)
    if a.dtype.kind in "US":
        return hashlib.sha256("\n".join(a.ravel().tolist()).encode()).hexdigest()
    return hashlib.sha256(a.tobytes()).hexdigest()


# ------------------------------------------------------------------------------------------ private window sets

def loso_window_set(rows, split_dir: Path):
    """(step_rows, t0) of the D-032 LOSO windows exactly as `loso_data.fold_data` builds them (fold 1 partitions;
    LOSO partitions are whole subjects, so every fold has these windows; the equivalence gate checks all folds)."""
    from src.evaluation import splits as S
    from src.evaluation.protocol import window_spec
    from src.evaluation.windowing import build_windows
    from src.training.loso_data import _partition_map, coded_key
    outer = [r for r in S.read_split(split_dir / S.LOSO_OUTER) if int(r["fold"]) == 1]
    part = _partition_map(rows, outer)
    group = coded_key(rows.subject, rows.device, rows.session, rows.sensor_phase, rows.cq_phase, part)
    w = build_windows(rows.ts, group, window_spec())
    return w.step_rows, w.t0


def rq2_window_set(rows, subject: str, pers: list[dict]):
    """(global step_rows, t0) of one subject's D-037 windows as `p5_personalization.subject_windows` builds them
    (b = 0: every night test; partitions are night-level, so the windows are the same for every budget)."""
    from src.evaluation.p5_personalization import budget_nights
    from src.evaluation.protocol import night_id, window_spec
    from src.evaluation.windowing import build_windows
    from src.training.loso_data import coded_key
    plan = budget_nights(pers, subject, 0)
    idx = np.flatnonzero(rows.subject == subject)
    ts = rows.ts[idx]
    nights = night_id(ts)
    sess = rows.session[idx]
    piece = coded_key(sess, nights)
    _, first_row, inv = np.unique(piece, return_index=True, return_inverse=True)
    part_u = [plan["pieces"][(str(sess[i]), str(nights[i]))] for i in first_row]
    part_rows = np.array(part_u, dtype=object)[inv.reshape(-1)].astype(str)
    group = coded_key(rows.device[idx], sess, rows.sensor_phase[idx], rows.cq_phase[idx], nights, part_rows)
    w = build_windows(ts, group, window_spec())
    return idx[w.step_rows], w.t0


def union_windows(sets: dict[str, tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray, dict]:
    """Union of window sets keyed by (step rows, t0), in canonical first-row order; membership flags per set."""
    keys, owner = [], []
    for name, (steps, t0) in sets.items():
        first = steps[:, 0]
        if first.size > 1 and not np.all(np.diff(first) > 0):
            raise ReleaseError(f"{name}: windows are not in strictly increasing first-row order")
        keys.append(np.column_stack([steps, t0]))
        owner += [name] * len(t0)
    allk = np.concatenate(keys)
    uniq, inv = np.unique(allk, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    owner = np.array(owner)
    flags = {name: np.zeros(len(uniq), bool) for name in sets}
    for name in sets:
        flags[name][inv[owner == name]] = True
    for name, (steps, t0) in sets.items():                  # each set keeps its own order inside the union
        sel = uniq[flags[name]]
        if not (np.array_equal(sel[:, :N_STEPS], steps) and np.array_equal(sel[:, N_STEPS], t0)):
            raise ReleaseError(f"{name}: order changes in the union")
    return uniq[:, :N_STEPS].astype(np.int64), uniq[:, N_STEPS].astype(np.int64), flags


# -------------------------------------------------------------------------------------------------- builder

def window_table(rows, pers: list[dict], split_dir: Path, anchors: dict[str, int]):
    import pyarrow as pa
    from src.evaluation.protocol import night_id
    sets = {"loso": loso_window_set(rows, split_dir)}
    rq2 = [rq2_window_set(rows, s, pers) for s in ALLOWED_SUBJECTS]
    order = np.argsort([st[0][0, 0] for st in rq2])
    steps = np.concatenate([rq2[i][0] for i in order])
    t0 = np.concatenate([rq2[i][1] for i in order])
    o = np.argsort(steps[:, 0], kind="stable")
    sets["rq2"] = (steps[o], t0[o])
    steps, t0, flags = union_windows(sets)
    last = steps[:, -1]
    subj = rows.subject[last]
    if not set(np.unique(subj)) <= set(ALLOWED_SUBJECTS):
        raise ReleaseError("a window belongs to a subject outside the cohort")
    anchor = np.array([anchors[s] for s in subj], np.int64)
    nights_abs = night_id(rows.ts[last])
    ordinal = {(r["subject_id"], r["night_id"]): int(r["night_ordinal"]) for r in pers if r["budget_nights"] == "0"}
    nkey = np.empty(len(last), dtype=object)
    for s in ALLOWED_SUBJECTS:
        m = subj == s
        nkey[m] = night_key_ts(rows.ts[last][m], anchors[s])
    p = rows.pressure[steps]                                                  # (n, 8, 6) int16
    cols = {"window_index": pa.array(np.arange(len(last), dtype=np.int64)),
            "subject_id": pa.array(subj.astype(str)), "device_id": pa.array(rows.device[last].astype(str)),
            "session_id": pa.array(rows.session[last].astype(str)),
            "sensor_phase": pa.array(rows.sensor_phase[last].astype(str)),
            "channel_quality_phase": pa.array(rows.cq_phase[last].astype(str)),
            "night_id": pa.array(nkey.astype(str)),
            "night_ordinal": pa.array(np.array([ordinal[(s, n)] for s, n in zip(subj, nights_abs)], np.int16)),
            "window_start_time_s": pa.array(t0 - anchor), "target_time_s": pa.array(rows.ts[last] - anchor),
            "in_loso": pa.array(flags["loso"]), "in_rq2": pa.array(flags["rq2"])}
    for k in range(N_STEPS):
        for c in range(N_CH):
            cols[f"s{k}_p{c + 1}"] = pa.array(p[:, k, c].astype(np.int16))
    cols.update({"temperature": pa.array(rows.targets[last, 0]), "humidity": pa.array(rows.targets[last, 1]),
                 "target_temp_valid": pa.array(rows.temp_ok[last].astype(bool)),
                 "target_humidity_valid": pa.array(rows.humid_ok[last].astype(bool))})
    table = pa.table(cols)
    if table.column_names != WINDOW_COLUMNS:
        raise ReleaseError("window table columns differ from the frozen schema")
    return table


def public_split_rows(split_dir: Path, anchors: dict[str, int]) -> dict[str, tuple[list[dict], list[str]]]:
    """The three committed v1.0 split files with D-049 relative times and night keys; all other fields unchanged."""
    from src.evaluation import splits as S
    cols = {S.LOSO_OUTER: S.OUTER_COLUMNS, S.LOSO_INNER: S.INNER_COLUMNS, S.PERSONALIZATION: S.PERS_COLUMNS}
    out = {}
    for rel, columns in cols.items():
        rows = []
        for r in S.read_split(split_dir / rel):
            a = anchors[r["subject_id"]]
            q = dict(r)
            q["start_timestamp"] = rel_str(parse_abs(r["start_timestamp"]) - a)
            q["end_timestamp"] = rel_str(parse_abs(r["end_timestamp"]) - a)
            if "night_id" in q:
                q["night_id"] = night_key_date(r["night_id"], a)
            rows.append(q)
        out[rel] = (rows, columns)
    return out


def public_plan(plan: dict, anchors: dict[str, int]) -> dict:
    """The committed P5 plan with every night id mapped to its D-049 key and the P3 run ids / local run paths removed;
    every other value is unchanged (keys keep their types: budgets and seeds stay integers)."""
    doc = copy.deepcopy(plan)
    for s, rec in doc["subjects"].items():
        a = anchors[s]
        for ck in rec["base_checkpoints"].values():            # run ids and local run paths are not needed publicly
            ck.pop("p3_run_id", None)
            ck.pop("p3_run_dir", None)
        rec["primary_test"]["nights"] = [night_key_date(n, a) for n in rec["primary_test"]["nights"]]
        for b in rec["budgets"].values():
            b["adaptation_nights"] = [night_key_date(n, a) for n in b["adaptation_nights"]]
            b["buffer_nights"] = [night_key_date(n, a) for n in b["buffer_nights"]]
            b["later_test_first"] = night_key_date(b["later_test_first"], a)
            b["later_test_last"] = night_key_date(b["later_test_last"], a)
    doc["description"] = ("Public copy of configs/experiments/v1.0/p5_personalization_plan.yaml (public_release_v1; "
                          "night ids mapped to D-049 relative night days; P3 run ids and local run paths removed; "
                          "every other value unchanged)")
    doc["night_id_representation"] = "D#### relative night day (D-049)"
    return doc


PLAN_REMOVED = ("p3_run_id", "p3_run_dir")
PLAN_NIGHT_FIELDS = ("nights", "adaptation_nights", "buffer_nights", "later_test_first", "later_test_last")


def plan_differences(private, public, anchors: dict[str, int], path: tuple = ()) -> list[str]:
    """Where `public` differs from the private plan other than by the D-049 night mapping, the removed run ids, the
    description and the added night-id note. Keys are compared with their order and types."""
    where = "/".join(map(str, path)) or "<root>"
    if isinstance(private, dict):
        if not isinstance(public, dict):
            return [f"{where}: not a mapping"]
        want = [k for k in private if k not in PLAN_REMOVED]
        added = ("night_id_representation", *(() if "description" in private else ("description",)))
        got = [k for k in public if not (path == () and k in added)]
        if got != want:
            return [f"{where}: keys {got!r} != {want!r}"]
        out = []
        for k in want:
            if not (path == () and k == "description"):
                out += plan_differences(private[k], public[k], anchors, path + (k,))
        return out
    if path and path[-1] in PLAN_NIGHT_FIELDS and len(path) > 1 and path[0] == "subjects":
        a = anchors[path[1]]
        want = [night_key_date(n, a) for n in private] if isinstance(private, list) else night_key_date(private, a)
        return [] if public == want else [f"{where}: night ids not mapped by D-049"]
    if isinstance(private, list):
        if not isinstance(public, list) or len(public) != len(private):
            return [f"{where}: list differs"]
        return [d for i, (x, y) in enumerate(zip(private, public)) for d in plan_differences(x, y, anchors, path + (i,))]
    return [] if type(private) is type(public) and private == public else [f"{where}: value differs"]


def control_event_rows(events: list[tuple[str, str, int, str]], anchors: dict[str, int]) -> list[dict]:
    out = [{"subject_id": s, "device_id": d, "time_s": int(t - anchors[s]), "time": rel_str(t - anchors[s]),
            "code": c} for s, d, t, c in events if c in HEATER_CODES]
    return sorted(out, key=lambda r: (r["subject_id"], r["device_id"], r["time_s"], r["code"]))


def write_windows(path: Path, table) -> None:
    write_parquet(path, [table.slice(i, ROW_GROUP) for i in range(0, table.num_rows, ROW_GROUP)] or [table],
                  table.schema)


# --------------------------------------------------------------------------------------------- public loader

@dataclass
class ReleaseArrays:
    subject: np.ndarray
    device: np.ndarray
    session: np.ndarray
    sensor_phase: np.ndarray
    cq_phase: np.ndarray
    night: np.ndarray
    ordinal: np.ndarray
    start: np.ndarray
    target_time: np.ndarray
    in_loso: np.ndarray
    in_rq2: np.ndarray
    pressure: np.ndarray        # (n, 8, 6) int16
    targets: np.ndarray         # (n, 2) float64 (NaN where absent)
    temp_ok: np.ndarray
    humid_ok: np.ndarray


def read_windows(path: Path) -> ReleaseArrays:
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    if t.column_names != WINDOW_COLUMNS:
        raise ReleaseError("windows.parquet columns differ from the frozen schema")
    s = lambda c: t[c].to_numpy(zero_copy_only=False).astype(str)  # noqa: E731
    p = np.stack([t[c].to_numpy() for c in PRESSURE_COLS], axis=1).astype(np.int16).reshape(-1, N_STEPS, N_CH)
    return ReleaseArrays(s("subject_id"), s("device_id"), s("session_id"), s("sensor_phase"),
                         s("channel_quality_phase"), s("night_id"), t["night_ordinal"].to_numpy().astype(np.int16),
                         t["window_start_time_s"].to_numpy().astype(np.int64),
                         t["target_time_s"].to_numpy().astype(np.int64), t["in_loso"].to_numpy(zero_copy_only=False),
                         t["in_rq2"].to_numpy(zero_copy_only=False), p,
                         np.stack([t["temperature"].to_numpy(), t["humidity"].to_numpy()], axis=1).astype(np.float64),
                         t["target_temp_valid"].to_numpy(zero_copy_only=False),
                         t["target_humidity_valid"].to_numpy(zero_copy_only=False))


class PublicRelease:
    """A verified public release: fold and subject window arrays for the P3/P4/P5 code, without canonical_v1."""

    def __init__(self, root: Path, verify: bool = True):
        self.root = Path(root)
        mpath = self.root / "manifest.json"
        self.manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else None
        if verify:
            if self.manifest is None:
                raise ReleaseError("manifest.json missing")
            bad = [a for a, h in self.manifest["artifacts_sha256"].items() if sha256_file(self.root / a) != h]
            if bad:
                raise ReleaseError(f"artifacts differ from the manifest: {bad}")
        self.verify = verify
        self.w = read_windows(self.root / "windows.parquet")
        self._splits: dict[str, list[dict]] = {}

    def split(self, rel: str) -> list[dict]:
        from src.evaluation import splits as S
        if rel not in self._splits:
            p = self.root / "splits" / rel
            if self.verify and sha256_file(p) != self.manifest["artifacts_sha256"][f"splits/{rel}"]:
                raise ReleaseError(f"splits/{rel} differs from the manifest")
            self._splits[rel] = S.read_split(p)
        return self._splits[rel]

    def split_dir(self) -> Path:
        return self.root / "splits"

    def pers(self) -> list[dict]:
        return self.split(SPLIT_RELS[2])

    def fold_data(self, fold: int):
        from src.evaluation.protocol import window_spec
        from src.training.loso_data import FoldData
        w, m = self.w, self.w.in_loso
        outer = [r for r in self.split(SPLIT_RELS[0]) if int(r["fold"]) == fold]
        inner_rows = [r for r in self.split(SPLIT_RELS[1]) if int(r["fold"]) == fold]
        if not outer:
            raise ReleaseError(f"fold {fold} not in the public outer split")
        held = {r["held_out_subject"] for r in outer}
        if len(held) != 1:
            raise ReleaseError("a fold must hold out exactly one subject")
        lookup = {r["session_id"]: r["partition"] for r in outer}
        sess = w.session[m]
        missing = sorted(set(sess) - set(lookup))
        if missing:
            raise ReleaseError(f"{len(missing)} window sessions have no split assignment")
        partition = np.array([lookup[s] for s in sess])
        inner = {}
        for name in sorted({r["inner_split"] for r in inner_rows}):
            lk = {r["session_id"]: r["partition"] for r in inner_rows if r["inner_split"] == name}
            inner[name] = np.array([lk.get(s, "") for s in sess])
            if np.any(inner[name][partition == "test"] != "") or np.any(inner[name][partition == "train"] == ""):
                raise ReleaseError("inner split inconsistent with the outer split")
        spec = window_spec()
        prov = {"subject_id": w.subject[m], "device_id": w.device[m], "session_id": sess,
                "sensor_phase": w.sensor_phase[m], "channel_quality_phase": w.cq_phase[m], "night_id": w.night[m],
                "window_start": w.start[m], "window_end": w.start[m] + spec.duration_s,
                "target_timestamp": w.target_time[m]}
        labels = np.stack([sess, w.sensor_phase[m], w.cq_phase[m]], axis=1)
        return FoldData(fold, held.pop(), sorted({r["subject_id"] for r in outer if r["partition"] == "train"}),
                        w.pressure[m], w.targets[m], w.temp_ok[m] & w.humid_ok[m], partition, inner, prov,
                        labels, labels.copy())

    def subject_windows(self, subject: str, budget: int):
        from src.evaluation.p5_personalization import budget_nights
        from src.evaluation.protocol import window_spec
        w = self.w
        m = w.in_rq2 & (w.subject == subject)
        plan = budget_nights(self.pers(), subject, budget)
        sess, night = w.session[m], w.night[m]
        try:
            partition = np.array([plan["pieces"][(s, n)] for s, n in zip(sess, night)])
        except KeyError as exc:
            raise ReleaseError(f"{subject} b={budget}: window piece {exc} has no split assignment") from None
        if not np.array_equal(np.array([plan["ordinal"][n] for n in night], np.int16), w.ordinal[m]):
            raise ReleaseError(f"{subject}: window night ordinals differ from the split")
        spec = window_spec()
        prov = {"subject_id": w.subject[m], "device_id": w.device[m], "session_id": sess,
                "sensor_phase": w.sensor_phase[m], "channel_quality_phase": w.cq_phase[m], "night_id": night,
                "night_ordinal": w.ordinal[m], "window_start": w.start[m],
                "window_end": w.start[m] + spec.duration_s, "target_timestamp": w.target_time[m]}
        labels = np.stack([partition, sess, w.sensor_phase[m], w.cq_phase[m], night], axis=1)
        recs = [r for r in self.pers() if r["subject_id"] == subject and int(r["budget_nights"]) == budget]
        row_ts = {}
        for p in sorted({r["partition"] for r in recs}):
            rr = [r for r in recs if r["partition"] == p]
            row_ts[p] = (min(parse_rel(r["start_timestamp"]) for r in rr), max(parse_rel(r["end_timestamp"])
                                                                                 for r in rr))
        adapt = partition == "adaptation"
        digests = (self.manifest or {}).get("p5_primary_windows", {}).get(subject)
        return PublicSubjectWindows(subject, budget, w.pressure[m], w.targets[m], w.temp_ok[m] & w.humid_ok[m],
                                    partition, np.isin(night, plan["primary"]), prov, labels, labels.copy(), row_ts,
                                    int(w.target_time[m][adapt].max()) if adapt.any() else None, digests)


@dataclass
class PublicSubjectWindows(SubjectWindows):
    """SubjectWindows rebuilt from the release. The primary-window digest is checked against the release manifest:
    an equal public digest stands for the private digest recorded in the frozen P5 plan (the equivalence gate proved
    the correspondence when the release was built). Any other digest is returned as is, so the P5 check fails."""
    digests: dict | None = None

    def public_digest(self) -> str:
        return SubjectWindows.primary_digest(self)

    def primary_digest(self) -> str:
        d = self.public_digest()
        if self.digests and d == self.digests["public_sha256"]:
            return self.digests["private_sha256"]
        return d


# ---------------------------------------------------------------------------------------- privacy validator

DATE_RE = re.compile(r"(?<!\d)(19|20)\d{2}[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])(?!\d)|\d{4}\s*년|"
                     r"(?<![\d])(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?![\d])")
PATH_RE = re.compile(r"[A-Za-z]:[\\/]|/Users/|/home/|\\\\[A-Za-z]|AppData|Desktop[\\/]")
MESSENGER_RE = re.compile(r"(?i)chat_?ids?\s*=|kakao|telegram|line_?id|wechat")
HASH_RE = re.compile(r"[0-9a-f]{32,}")
LONG_DIGITS_RE = re.compile(r"(?<![\d.])\d{9,}(?![\d.])")
RAW_NAME_RE = re.compile(r"\.(txt|xlsx|xls|TXT)\b|sm2248[02]_\d|phase_[abc]\b|mat_2248[02]|legacy_csv|"
                         r"\buser0\d/|스마트")
RESTRICTED_RE = re.compile(r"(?i)\b(diagnos\w*|medicat\w*|medicine|disease|illness|symptoms?|birth\w*|gender|sex|"
                           r"age|height|weight|bmi|names?|initials?|phone|address|e-?mail|conditions?)\b")
FORBIDDEN_COLUMNS = ("event_raw", "event_redacted", "source_file", "source_file_id", "source_row", "source_id",
                     "source_relpath", "file_id", "chunk_key", "timestamp", "timestamp_raw", "canonical_row_id",
                     "firmware_movement_label", "control_event", "heater_state", "log_container")


def _check(out: list, name: str, fn) -> None:
    try:
        problem = fn()
    except Exception as exc:                                                        # fail closed
        problem = f"check raised {type(exc).__name__}: {exc}"
    out.append({"check": name, "passed": problem is None, "detail": problem or "ok"})


def _text_findings(text: str, allow_excluded: bool) -> list[str]:
    """Pattern findings in a text artifact. Source ids (e.g. `user02_mat_22480_prefix_mismatch`) are allowed only
    where excluded sources are listed (DATA_POLICY §5.4)."""
    found = []
    stripped = HASH_RE.sub("#", text)
    checks = [("calendar date", DATE_RE), ("absolute path", PATH_RE), ("messenger id", MESSENGER_RE),
              ("long digit identifier", LONG_DIGITS_RE)]
    if not allow_excluded:
        checks.append(("raw filename/folder", RAW_NAME_RE))
    for label, rx in checks:
        m = rx.search(stripped)
        if m:
            found.append(f"{label}: {m.group(0)!r}")
    if not allow_excluded and re.search(r"User06|prefix_mismatch|user06|quarantin", stripped):
        found.append("excluded source mentioned in a data artifact")
    return found


def validate_release(root: Path, raw_names: list[str] | None = None, private_splits: dict | None = None
                     ) -> list[dict]:
    """Privacy / integrity checks of a release directory (D-050). Fails closed: every check must pass."""
    import pyarrow.parquet as pq
    root = Path(root)
    out: list[dict] = []
    texts = {a: (root / a).read_text(encoding="utf-8") for a in ARTIFACTS if a != "windows.parquet"}
    t = pq.read_table(root / "windows.parquet")

    def columns_ok():
        if t.column_names != WINDOW_COLUMNS:
            return "window columns differ from the frozen schema"
        bad = [c for c in t.column_names if c in FORBIDDEN_COLUMNS or RESTRICTED_RE.search(c)]
        types = [f.name for f in t.schema if str(f.type).startswith(("timestamp", "date"))]
        return f"forbidden/date-typed columns: {bad + types}" if bad or types else None
    _check(out, "window_columns_frozen_no_restricted_or_date_fields", columns_ok)

    def values_ok():
        s = lambda c: set(t[c].to_numpy(zero_copy_only=False).astype(str))  # noqa: E731
        subj = s("subject_id")
        if not subj <= set(ALLOWED_SUBJECTS):
            return f"subjects {sorted(subj - set(ALLOWED_SUBJECTS))}"
        pairs = {(a, b) for a, b in zip(t["subject_id"].to_numpy(zero_copy_only=False),
                                        t["device_id"].to_numpy(zero_copy_only=False))}
        if any(d not in ALLOWED_DEVICES[a] for a, d in pairs):
            return f"subject/device pairs {sorted(pairs)}"
        if not all(re.fullmatch(r"User0[127]\|(unknown|22480|22482)\|S\d{4}", x) for x in s("session_id")):
            return "a session id has an unexpected form"
        if not all(re.fullmatch(r"D\d{4}", x) for x in s("night_id")):
            return "a night id is not a D#### relative day"
        if not s("sensor_phase") <= set(ALLOWED_SENSOR_PHASES) or not s("channel_quality_phase") <= set(
                ALLOWED_CQ_PHASES):
            return "unexpected phase label"
        pmin = min(int(t[c].to_numpy().min()) for c in PRESSURE_COLS)
        pmax = max(int(t[c].to_numpy().max()) for c in PRESSURE_COLS)
        if pmin < 0 or pmax > 4095:
            return f"pressure outside 0..4095 ({pmin}, {pmax})"
        for c in ("window_start_time_s", "target_time_s"):
            v = t[c].to_numpy()
            if v.min() < 0 or v.max() >= 2 ** 34:
                return f"{c} outside the relative-time range"
        return None
    _check(out, "window_values_allowed_ids_ranges_relative_time", values_ok)

    def user02_one_subject():
        dev = t["device_id"].to_numpy(zero_copy_only=False).astype(str)
        subj = t["subject_id"].to_numpy(zero_copy_only=False).astype(str)
        return None if set(subj[np.isin(dev, ["22480", "22482"])]) == {"User02"} else "a User02 mat maps elsewhere"
    _check(out, "user02_mats_are_one_subject", user02_one_subject)

    for a, text in texts.items():
        free_text = a in ("README.md",)
        _check(out, f"text_scan:{a}",
               lambda text=text, a=a: "; ".join(_text_findings(text, allow_excluded=a in ("excluded_sources.csv",
                                                                                          "README.md"))) or None)
        if not free_text and a not in ("excluded_sources.csv",):
            _check(out, f"restricted_fields:{a}",
                   lambda text=text: (lambda m: f"restricted token {m.group(0)!r}" if m else None)(
                       RESTRICTED_RE.search(HASH_RE.sub("#", text))))

    def events_ok():
        from src.evaluation import splits as S
        rows = S.read_split(root / "control_events.csv")
        codes = {r["code"] for r in rows}
        return None if codes <= set(HEATER_CODES) and set(rows[0]) == {"subject_id", "device_id", "time_s", "time",
                                                                        "code"} else f"control codes {codes}"
    _check(out, "control_events_codes_only", events_ok)

    def splits_ok():
        from src.evaluation import leakage as L
        from src.evaluation import splits as S
        from src.evaluation.protocol import load_protocol
        cfg = load_protocol()
        outer, inner, pers = (S.read_split(root / "splits" / r) for r in SPLIT_RELS)
        folds = {int(k): v for k, v in cfg["loso"]["outer_folds"].items()}
        pz = cfg["personalization"]
        for fn in (lambda: L.check_outer(outer, folds, list(ALLOWED_SUBJECTS)),
                   lambda: L.check_inner(inner, folds, list(ALLOWED_SUBJECTS)),
                   lambda: L.check_personalization(pers, pz["budgets_nights"], pz["buffer_nights"],
                                                   pz["primary_test_from_ordinal"]),
                   lambda: L.check_devices_together(outer, pers)):
            p = fn()
            if p:
                return p
        sess = set(t["session_id"].to_numpy(zero_copy_only=False).astype(str))
        if not sess <= {r["session_id"] for r in outer if int(r["fold"]) == 1}:
            return "a window session is not in the split"
        if private_splits is not None:
            for rel, (rows, _) in private_splits.items():
                got = S.read_split(root / "splits" / rel)
                if got != [{k: str(v) for k, v in r.items()} for r in rows]:
                    return f"{rel}: public split differs from the D-049 mapping of the private split"
        return None
    _check(out, "public_split_semantics", splits_ok)

    if raw_names:
        def raw_absent():
            hits = [n for n in raw_names if n and any(n in x for x in texts.values())]
            return f"raw file names present: {hits[:5]}" if hits else None
        _check(out, "raw_manifest_names_absent", raw_absent)

    man = root / "manifest.json"
    if man.exists():
        def hashes_ok():
            m = json.loads(man.read_text(encoding="utf-8"))
            bad = [a for a, h in m["artifacts_sha256"].items() if sha256_file(root / a) != h]
            if set(m["artifacts_sha256"]) != set(ARTIFACTS):
                return "manifest artifact list differs"
            return f"hash mismatch {bad}" if bad else None
        _check(out, "manifest_hashes_match", hashes_ok)
        _check(out, "text_scan:manifest.json", lambda: "; ".join(_text_findings(man.read_text(encoding="utf-8"),
                                                                               True)) or None)
    return out


# ------------------------------------------------------------------------------------------ equivalence gate

def _map_prov(prov: dict, anchors: dict[str, int]) -> dict:
    subj = prov["subject_id"]
    a = np.array([anchors[s] for s in subj], np.int64)
    out = dict(prov)
    out["night_id"] = np.empty(len(subj), dtype=object)
    for s in np.unique(subj):
        m = subj == s
        out["night_id"][m] = np.array([night_key_date(n, anchors[s]) for n in prov["night_id"][m]])
    out["night_id"] = out["night_id"].astype(str)
    for c in ("window_start", "window_end", "target_timestamp"):
        out[c] = np.asarray(prov[c], np.int64) - a
    return out


def _same(a, b) -> bool:
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return False
    if a.dtype.kind == "f" or b.dtype.kind == "f":
        return bool(np.array_equal(a, b, equal_nan=True))
    return bool(np.array_equal(a.astype(str) if a.dtype.kind in "OUS" else a,
                               b.astype(str) if b.dtype.kind in "OUS" else b))


def equivalence(rows, split_dir: Path, pers_private: list[dict], release: PublicRelease, anchors: dict[str, int],
                budgets: list[int]) -> tuple[list[dict], dict]:
    """Private model-ready arrays vs arrays rebuilt from the release (bitwise under the D-049 mapping)."""
    from src.evaluation.p5_personalization import subject_windows
    from src.training.loso_data import fold_data
    checks, digests = [], {"folds": {}, "subjects": {}}
    for fold in (1, 2, 3):
        def cmp_fold(fold=fold):
            p, q = fold_data(rows, fold, split_dir), release.fold_data(fold)
            if (p.held_out, p.train_subjects) != (q.held_out, q.train_subjects):
                return "held-out / training subjects differ"
            for name in ("pressure", "targets", "labelled", "partition"):
                if not _same(getattr(p, name), getattr(q, name)):
                    return f"{name} differs"
            if sorted(p.inner) != sorted(q.inner) or not all(_same(p.inner[k], q.inner[k]) for k in p.inner):
                return "inner assignment differs"
            mp = _map_prov(p.prov, anchors)
            bad = [k for k in mp if not _same(mp[k], q.prov[k])]
            if bad:
                return f"provenance differs: {bad}"
            if not (_same(p.first_labels, q.first_labels) and _same(p.last_labels, q.last_labels)):
                return "boundary labels differ"
            digests["folds"][fold] = {"n_windows": int(len(p.labelled)), "pressure_sha256": sha256_array(p.pressure),
                                      "targets_sha256": sha256_array(p.targets)}
            return None
        _check(checks, f"fold{fold}_model_ready_windows_identical", cmp_fold)
    for s in ALLOWED_SUBJECTS:
        for b in budgets:
            def cmp_subject(s=s, b=b):
                p, q = subject_windows(rows, s, b, pers_private), release.subject_windows(s, b)
                for name in ("pressure", "targets", "labelled", "partition", "primary"):
                    if not _same(getattr(p, name), getattr(q, name)):
                        return f"{name} differs"
                mp = _map_prov(p.prov, anchors)
                bad = [k for k in mp if not _same(mp[k], q.prov[k])]
                if bad:
                    return f"provenance differs: {bad}"
                a = anchors[s]
                fl = p.first_labels.copy()
                fl[:, 4] = np.array([night_key_date(n, a) for n in fl[:, 4]])
                if not (_same(fl, q.first_labels) and _same(fl, q.last_labels)):
                    return "boundary labels differ"
                if {k: (v[0] - a, v[1] - a) for k, v in p.row_ts.items()} != q.row_ts:
                    return "partition row spans differ"
                if (p.adapt_row_max_ts is None) != (q.adapt_row_max_ts is None) or (
                        p.adapt_row_max_ts is not None and p.adapt_row_max_ts - a != q.adapt_row_max_ts):
                    return "latest adaptation row differs"
                if b == 0:
                    digests["subjects"][s] = {"private_sha256": p.primary_digest(),
                                              "public_sha256": q.public_digest(),
                                              "n_windows": int(len(p.labelled)),
                                              "pressure_sha256": sha256_array(p.pressure),
                                              "targets_sha256": sha256_array(p.targets)}
                return None
            _check(checks, f"{s}_b{b}_rq2_windows_identical", cmp_subject)
    return checks, digests


# ------------------------------------------------------------------------------------------ schema / digests

def schema_doc() -> dict:
    """Machine-readable window schema (frozen by D-050). Words describing people are avoided on purpose."""
    base = [
        ("window_index", "int64", "", "0 ... n-1", "order", "canonical first-row order; P3/P4/P5 keep this order"),
        ("subject_id", "string", "", "User01, User02, User07", "grouping", "anonymous subject (DATA_POLICY §3)"),
        ("device_id", "string", "", "unknown, 22480, 22482", "grouping",
         "mat hardware id; 22480 and 22482 are two mats of User02 (one subject)"),
        ("session_id", "string", "", "<subject>|<device>|S####", "grouping", "canonical session (D-024)"),
        ("sensor_phase", "string", "", "s1, s2, not_applicable", "stratum", "User01 sensor phase (D-019)"),
        ("channel_quality_phase", "string", "", "normal, p1_transition, p1_response_shift", "stratum",
         "22482 channel-quality phase (D-022)"),
        ("night_id", "string", "", "D####", "grouping", "relative night day of the target row (D-049)"),
        ("night_ordinal", "int16", "", "1 ... N", "grouping", "chronological subject-night number (D-037)"),
        ("window_start_time_s", "int64", "s", ">= 0", "time", "window start t0, seconds since the subject anchor"),
        ("target_time_s", "int64", "s", ">= 0", "time", "time of the target row (last step), same anchor"),
        ("in_loso", "bool", "", "", "membership", "window of the D-032 LOSO window set (P3/P4)"),
        ("in_rq2", "bool", "", "", "membership", "window of the D-037 RQ2 window set (P5/P6)")]
    cols = [dict(zip(("column", "dtype", "unit", "range", "role", "meaning"), c)) for c in base]
    for k in range(N_STEPS):
        for c in range(1, N_CH + 1):
            cols.append({"column": f"s{k}_p{c}", "dtype": "int16", "unit": "ADC count", "range": "0 ... 4095",
                         "role": "model_input", "meaning": f"channel P{c} at step {k} (last row of 5-s bin {k}); "
                                                           "model input = value / 4095 (D-033)"})
    cols += [{"column": "temperature", "dtype": "float64", "unit": "°C", "range": "as recorded (NaN if absent)",
              "role": "target", "meaning": "temperature at the target row"},
             {"column": "humidity", "dtype": "float64", "unit": "%RH", "range": "as recorded (NaN if absent)",
              "role": "target", "meaning": "relative humidity at the target row"},
             {"column": "target_temp_valid", "dtype": "bool", "unit": "", "range": "", "role": "label_flag",
              "meaning": "D-025 validity; a window is labelled only if both flags are true"},
             {"column": "target_humidity_valid", "dtype": "bool", "unit": "", "range": "", "role": "label_flag",
              "meaning": "D-025 validity"}]
    return {"release_version": RELEASE_VERSION, "file": "windows.parquet", "columns": cols,
            "model_inputs": PRESSURE_COLS, "targets": ["temperature", "humidity"],
            "time_representation": "integer seconds since local midnight of the subject's first night date (D-049)"}


def prediction_digest(pred_path: Path) -> dict:
    import pyarrow.parquet as pq
    t = pq.read_table(pred_path, columns=["target", "y_true", "y_pred"])
    y = np.ascontiguousarray(t["y_true"].to_numpy(), np.float64)
    p = np.ascontiguousarray(t["y_pred"].to_numpy(), np.float64)
    return {"n": int(len(p)), "y_true_sha256": hashlib.sha256(y.tobytes()).hexdigest(),
            "y_pred_sha256": hashlib.sha256(p.tobytes()).hexdigest()}


# --------------------------------------------------------------------------------------------------- build

def build_release(out: Path, rows, split_dir: Path, *, plan: dict, events: list[tuple[str, str, int, str]],
                  reference: dict, excluded: list[dict], budgets: list[int], identity: dict,
                  raw_names: list[str] | None = None) -> tuple[dict, list[dict]]:
    """Write the release into `out` (README.md must already be there), validate it, check private/public
    equivalence, then write the deterministic manifest. Raises ReleaseError if any check fails."""
    from src.evaluation import splits as S
    out = Path(out)
    if not (out / "README.md").exists():
        raise ReleaseError("release README.md is missing")
    remove_file(out / "manifest.json")                   # a previous build's manifest must not enter the checks
    anchors = subject_anchors(rows.subject, rows.ts)
    pers_private = S.read_split(split_dir / S.PERSONALIZATION)
    table = window_table(rows, pers_private, split_dir, anchors)
    write_windows(out / "windows.parquet", table)
    splits = public_split_rows(split_dir, anchors)
    for rel, (r, cols) in splits.items():
        S.write_split(out / "splits" / rel, r, cols)
    write_csv(out / "control_events.csv", control_event_rows(events, anchors),
              ["subject_id", "device_id", "time_s", "time", "code"])
    pplan = public_plan(plan, anchors)
    write_text(out / "p5_plan_public.yaml", yaml.safe_dump(pplan, sort_keys=False))
    write_json(out / "reference_digests.json", reference)
    write_csv(out / "excluded_sources.csv", excluded, ["source_id", "subject_id", "dataset_role", "exclusion_reason",
                                                       "exclusion_confirmed_by", "exclusion_decision"])
    write_json(out / "schema.json", schema_doc())
    checks = validate_release(out, raw_names=raw_names, private_splits=splits)
    release = PublicRelease(out, verify=False)
    eq, digests = equivalence(rows, split_dir, pers_private, release, anchors, budgets)
    checks += eq

    def plan_digests():
        bad = [s for s, d in digests["subjects"].items()
               if plan["subjects"][s]["primary_test"]["windows_sha256"] != d["private_sha256"]]
        return f"primary windows differ from the frozen P5 plan: {bad}" if bad else None
    _check(checks, "p5_plan_primary_windows_match_private", plan_digests)

    def plan_same():
        bad = plan_differences(plan, yaml.safe_load((out / "p5_plan_public.yaml").read_text(encoding="utf-8")),
                               anchors)
        return "; ".join(bad[:5]) if bad else None
    _check(checks, "p5_plan_public_equals_private_except_night_ids", plan_same)
    failed = [c for c in checks if not c["passed"]]
    if failed:
        raise ReleaseError("release gates failed: " + "; ".join(f"{c['check']}: {c['detail']}" for c in failed))
    w = release.w
    manifest = {
        "release_version": RELEASE_VERSION, **identity,
        "subjects": list(ALLOWED_SUBJECTS),
        "streams": sorted({f"{s}|{d}" for s, d in zip(w.subject, w.device)}),
        "counts": {"windows": int(len(w.subject)), "in_loso": int(w.in_loso.sum()), "in_rq2": int(w.in_rq2.sum()),
                   "labelled_in_loso": int((w.in_loso & w.temp_ok & w.humid_ok).sum()),
                   "labelled_in_rq2": int((w.in_rq2 & w.temp_ok & w.humid_ok).sum()),
                   "per_subject": {s: int((w.subject == s).sum()) for s in ALLOWED_SUBJECTS},
                   "control_events": len(control_event_rows(events, anchors))},
        "targets": {"temperature": "°C at the target row (last window step)",
                    "humidity": "%RH at the target row", "label_rule": "both D-025 validity flags true"},
        "pressure_representation": "8 steps x 6 channels raw ADC counts 0-4095 (last row per 5-s bin, D-032); "
                                   "model input = value / 4095, 4095 kept (D-033)",
        "temporal_deidentification": "D-049: per-subject whole-day anchor shift; seconds since local midnight of the "
                                     "subject's first night date; night keys D####; no calendar date",
        "split_representation": "v1.0 split files with relative times (D-049); identical rows and semantics",
        "window_sets": {"in_loso": "D-032 LOSO windows (P3, P4)", "in_rq2": "D-037 windows cut at night and "
                                                                          "partition boundaries (P5, P6)"},
        "excluded_sources": [{k: r[k] for k in ("source_id", "dataset_role", "exclusion_reason",
                                                "exclusion_confirmed_by", "exclusion_decision")} for r in excluded],
        "p5_primary_windows": digests["subjects"],
        "equivalence": {"passed": True, "folds": digests["folds"],
                        "checks": [c["check"] for c in checks if c["check"].endswith("identical")]},
        "privacy_checks_passed": len([c for c in checks if c["passed"]]),
        "artifacts_sha256": {a: sha256_file(out / a) for a in ARTIFACTS},
    }
    write_json(out / "manifest.json", manifest)
    final = validate_release(out)
    if not all(c["passed"] for c in final):
        raise ReleaseError("release failed validation after the manifest was written")
    return manifest, checks + final
