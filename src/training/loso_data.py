"""P3 fold data: protocol v1.0 windows built inside the committed LOSO split partitions (L1; D-031, D-032).

The split files are the source of truth: every row's partition comes from `data/splits/v1.0_loso/outer_folds.csv`
(and `inner_folds.csv` for the inner splits); nothing is recomputed. Windows are built with the frozen rule
(`src/evaluation/windowing.py`) with the partition as a boundary label. Canonical input only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pyarrow as pa

from src.evaluation import splits as S
from src.evaluation.canonical_input import load_primary
from src.evaluation.p2_protocol import split_root
from src.evaluation.protocol import load_protocol, night_id, window_spec
from src.evaluation.windowing import build_windows, group_key, labelled
from src.features.pressure_features import PRESSURE_COLUMNS

ROW_COLUMNS = ["subject_id", "device_id", "session_id", "sensor_phase", "channel_quality_phase", "timestamp",
               *PRESSURE_COLUMNS, "temperature", "humidity", "target_temp_valid", "target_humidity_valid"]


class FoldDataError(ValueError):
    pass


@dataclass
class Rows:
    subject: np.ndarray
    device: np.ndarray
    session: np.ndarray
    sensor_phase: np.ndarray
    cq_phase: np.ndarray
    ts: np.ndarray
    pressure: np.ndarray          # (n, 6) raw integers 0..4095 (4095 kept)
    targets: np.ndarray           # (n, 2) temperature, humidity (NaN where absent; only labelled rows are used)
    temp_ok: np.ndarray
    humid_ok: np.ndarray

    @property
    def night(self) -> np.ndarray:
        return night_id(self.ts)


def rows_from_table(t: pa.Table) -> Rows:
    s = lambda c: t[c].cast(pa.string()).to_numpy(zero_copy_only=False).astype(str)  # noqa: E731
    num = lambda c: t[c].cast(pa.float64()).fill_null(np.nan).to_numpy()  # noqa: E731
    p = np.stack([t[c].cast(pa.int32()).fill_null(-1).to_numpy() for c in PRESSURE_COLUMNS], axis=1)
    if np.any(p < 0) or np.any(p > 4095):
        raise FoldDataError("pressure outside 0..4095 or missing in primary rows")
    return Rows(s("subject_id"), s("device_id"), s("session_id"), s("sensor_phase"), s("channel_quality_phase"),
                t["timestamp"].cast(pa.timestamp("s")).cast(pa.int64()).to_numpy(), p.astype(np.int16),
                np.stack([num("temperature"), num("humidity")], axis=1),
                t["target_temp_valid"].to_numpy(zero_copy_only=False),
                t["target_humidity_valid"].to_numpy(zero_copy_only=False))


def load_rows() -> Rows:
    return rows_from_table(load_primary(ROW_COLUMNS))


@dataclass
class FoldData:
    fold: int
    held_out: str
    train_subjects: list[str]
    pressure: np.ndarray                  # (n_windows, 8, 6) raw integers at the step rows
    targets: np.ndarray                   # (n_windows, 2) at the target row, original units
    labelled: np.ndarray
    partition: np.ndarray                 # outer partition of each window: train / test
    inner: dict[str, np.ndarray]          # inner split A/B -> inner_train / inner_val / '' (held-out)
    prov: dict[str, np.ndarray]           # provenance per window
    first_labels: np.ndarray = field(repr=False, default=None)   # (partition, session, phases) of first step
    last_labels: np.ndarray = field(repr=False, default=None)    # same for the last step (target row)

    def window_groups(self, mask: np.ndarray, inner: str | None = None) -> list[tuple[tuple, tuple]]:
        """Unique (first-step, last-step) boundary labels of the selected windows, for the leakage gate."""
        part = self.partition if inner is None else self.inner[inner]
        first = np.stack([part, self.first_labels[:, 0], self.first_labels[:, 1], self.first_labels[:, 2]], 1)
        last = np.stack([part, self.last_labels[:, 0], self.last_labels[:, 1], self.last_labels[:, 2]], 1)
        pairs = np.unique(np.concatenate([first[mask], last[mask]], axis=1), axis=0)
        return [(tuple(r[:4]), tuple(r[4:])) for r in pairs]


def _partition_map(rows: Rows, records: list[dict], key: str = "partition") -> np.ndarray:
    lookup = {r["session_id"]: r[key] for r in records}
    uniq, inv = np.unique(rows.session, return_inverse=True)
    missing = [u for u in uniq if u not in lookup]
    if missing:
        raise FoldDataError(f"{len(missing)} canonical sessions have no split assignment")
    return np.array([lookup[u] for u in uniq], dtype=object)[inv].astype(str)


def fold_data(rows: Rows, fold: int, split_dir=None) -> FoldData:
    split_dir = split_root() if split_dir is None else split_dir
    outer = [r for r in S.read_split(split_dir / S.LOSO_OUTER) if int(r["fold"]) == fold]
    inner_rows = [r for r in S.read_split(split_dir / S.LOSO_INNER) if int(r["fold"]) == fold]
    if not outer:
        raise FoldDataError(f"fold {fold} not in the committed outer split")
    held = {r["held_out_subject"] for r in outer}
    if len(held) != 1:
        raise FoldDataError("a fold must hold out exactly one subject")
    held_out = held.pop()
    train_subjects = sorted({r["subject_id"] for r in outer if r["partition"] == "train"})
    part_rows = _partition_map(rows, outer)
    spec = window_spec()
    group = group_key(rows.subject, rows.device, rows.session, rows.sensor_phase, rows.cq_phase, part_rows)
    w = build_windows(rows.ts, group, spec)                      # validates bins, gaps and boundaries
    first, last = w.step_rows[:, 0], w.target_row
    partition = part_rows[last]
    if np.any(part_rows[first] != partition):
        raise FoldDataError("a window crosses an outer partition")
    inner = {}
    for name in sorted({r["inner_split"] for r in inner_rows}):
        lookup = {r["session_id"]: r["partition"] for r in inner_rows if r["inner_split"] == name}
        sess = rows.session[last]
        inner[name] = np.array([lookup.get(s, "") for s in sess])
        if np.any(inner[name][partition == "test"] != ""):
            raise FoldDataError("held-out windows appear in an inner split")
        if np.any(inner[name][partition == "train"] == ""):
            raise FoldDataError("a training window has no inner assignment")
    lab = labelled(w, rows.temp_ok, rows.humid_ok)
    labels = lambda r: np.stack([rows.session[r], rows.sensor_phase[r], rows.cq_phase[r]], axis=1)  # noqa: E731
    prov = {"subject_id": rows.subject[last], "device_id": rows.device[last], "session_id": rows.session[last],
            "sensor_phase": rows.sensor_phase[last], "channel_quality_phase": rows.cq_phase[last],
            "night_id": rows.night[last], "window_start": w.t0,
            "window_end": w.t0 + spec.duration_s, "target_timestamp": rows.ts[last]}
    return FoldData(fold, held_out, train_subjects, rows.pressure[w.step_rows], rows.targets[last], lab, partition,
                    inner, prov, labels(first), labels(last))


def p3_folds() -> dict[int, str]:
    return {int(k): v for k, v in load_protocol()["loso"]["outer_folds"].items()}
