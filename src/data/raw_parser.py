"""Read-only, line-based parser for the raw smart-mat log families.

This module only *describes* raw files for inventory/audit purposes. It performs no
cleaning, resampling, interpolation or deduplication and never writes anything.

Known line families (see docs/initial_dataset_inventory.md):
  - plain CSV rows with full timestamps          2025-08-25 22:21:51,P1..P6,temp,humid,event
  - legacy CSV rows with minute timestamps       2025-10-05 0:50,FSR1..FSR6,Temp,Hum,Event
  - MM-DD rows (year missing)                    07-19 19:54:06,P1..P6,temp,humid,event
  - MM-DD rows with a device column              08-29 21:00:01,22480,P1..P6,temp,humid,event
  - quasi-JSON wrappers: {"<log key>": {"csvData": "<multi-line CSV>"}}, not valid JSON
  - device/serial log lines ([NVS], Firebase upload messages, ESP32 crash dumps)
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.data.io_guard import read_bytes

MOVEMENT_TOKENS = {
    # compressed firmware codes (legend: raw/user01/metadata, sheet "로그압축용어")
    "UM": "up", "DM": "down", "RM": "right", "LM": "left", "NM": "absent",
    # older firmware, Korean labels
    "위로이동": "up", "아래로이동": "down", "우로이동": "right", "좌로이동": "left", "자리비움": "absent",
}

_CSVDATA_PREFIX = re.compile(r'^\s*"csvData"\s*:\s*"')
_RE_YMD_HMS = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{1,2}):(\d{2}):(\d{2})(?=[,.])")
_RE_YMD_HM = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{1,2}):(\d{2})(?=,)")
_RE_MD_HMS = re.compile(r"^(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})(?=[,.])")
_RE_NUMS_EVENT = re.compile(r"^(?P<sep>[,.])(?P<nums>-?\d+(?:\.\d+)?(?:,-?\d+(?:\.\d+)?)*)(?:,(?P<event>.*))?$")
_RE_HEADER = re.compile(r"^\ufeff?(?:timestamp,|TS\()")
_RE_CHUNK_KEY = re.compile(r'^\s*"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"\s*:\s*\{')
_RE_ROOT_KEY = re.compile(r'^\s*"(smartmat(?:_(\d+))?|logs)"\s*:\s*\{')
_RE_MALFORMED_TS = re.compile(r"^\d{2,4}-\d{2}")
_JSON_STRUCT = {"{", "}", "},", '"', '",'}
_CRASH_MARKERS = ("Guru Meditation", "Backtrace", "register dump", "EXCVADDR", "EXCCAUSE",
                  "PC      :", "ELF file SHA256", "Rebooting", "rst:0x", "LBEG", "SAR     :")
_RE_REGISTER = re.compile(r"^A\d+\s+:")


@dataclass
class DataRow:
    line_no: int
    ts_raw: str
    ts_format: str             # ymd_hms | ymd_hm | md_hms
    ts: datetime | None
    year_source: str           # explicit | json_key | json_key_lookahead | config_hint | unresolved | invalid
    sep: str                   # separator between timestamp and first value ("," expected)
    n_values: int
    schema: str                # p6_t_h | dev_p6_t_h | nonstandard_<n>
    device_id: str | None
    pressure: tuple[float, ...]
    temp: float | None
    humid: float | None
    event_raw: str
    movement: str | None
    control: str | None
    chunk_key: str | None
    has_decimal: bool

    def fingerprint(self) -> tuple:
        """Content identity of a row, independent of file wrapper and line endings."""
        ts = self.ts.isoformat() if self.ts else f"raw:{self.ts_raw}"
        return (ts, self.pressure, self.temp, self.humid, self.event_raw)


@dataclass
class ParsedFile:
    encoding: str
    has_bom: bool
    line_endings: Counter
    n_lines: int
    line_types: Counter
    rows: list[DataRow]
    headers: Counter
    chunk_keys: list[str]
    root_keys: Counter
    samples: dict[str, list[str]] = field(default_factory=dict)


def decode(raw: bytes) -> tuple[str, str, bool]:
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    for enc in ("utf-8-sig", "cp949"):
        try:
            return raw.decode(enc), enc, has_bom
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace", has_bom


_RE_LONG_DIGITS = re.compile(r"\d{8,}")


def redact(text: str) -> str:
    """Mask long digit runs (e.g. messenger chat IDs in device logs) before text leaves the raw layer."""
    return _RE_LONG_DIGITS.sub("<redacted>", text)


def _infer_year(month: int, anchor: datetime) -> int:
    if month - anchor.month > 6:
        return anchor.year - 1
    if anchor.month - month > 6:
        return anchor.year + 1
    return anchor.year


def _to_num(s: str) -> float | int:
    return float(s) if "." in s else int(s)


def split_event(event_raw: str) -> tuple[str | None, str | None]:
    tokens = event_raw.split()
    movement = None
    if tokens and tokens[-1] in MOVEMENT_TOKENS:
        movement = MOVEMENT_TOKENS[tokens[-1]]
        tokens = tokens[:-1]
    control = " ".join(tokens) or None
    return movement, control


def classify_nondata(line: str) -> str:
    s = line.strip()
    if not s:
        return "blank"
    if set(s) == {","}:
        return "empty_csv_row"
    if s in _JSON_STRUCT:
        return "json_struct"
    if _RE_CHUNK_KEY.match(line):
        return "json_chunk_key"
    if _RE_ROOT_KEY.match(line):
        return "json_root_key"
    if s.startswith("[NVS]"):
        return "nvs_log"
    if any(m in s for m in _CRASH_MARKERS) or _RE_REGISTER.match(s):
        return "crash_dump"
    if _RE_MALFORMED_TS.match(_CSVDATA_PREFIX.sub("", s)):
        return "malformed_data"
    return "device_log"


def _parse_ts(body: str) -> tuple[str, str, tuple[int, ...], int] | None:
    for fmt, rx in (("ymd_hms", _RE_YMD_HMS), ("ymd_hm", _RE_YMD_HM), ("md_hms", _RE_MD_HMS)):
        m = rx.match(body)
        if m:
            return fmt, m.group(0), tuple(int(g) for g in m.groups()), m.end()
    return None


def parse_text(text: str, year_hint: int | None = None) -> tuple[Counter, list[DataRow], Counter, list[str], Counter, dict]:
    lines = text.splitlines()
    chunk_keys_all = [m.group(1) for m in map(_RE_CHUNK_KEY.match, lines) if m]
    first_key_dt = datetime.strptime(chunk_keys_all[0], "%Y-%m-%d_%H-%M-%S") if chunk_keys_all else None

    line_types: Counter = Counter()
    headers: Counter = Counter()
    root_keys: Counter = Counter()
    samples: dict[str, list[str]] = {}
    rows: list[DataRow] = []
    chunk_key: str | None = None
    chunk_dt: datetime | None = None

    for i, line in enumerate(lines, start=1):
        body = _CSVDATA_PREFIX.sub("", line).strip()
        if body.endswith('"'):
            body = body[:-1].rstrip()

        if _RE_HEADER.match(body):
            line_types["header"] += 1
            headers[body.lstrip("\ufeff")] += 1
            continue

        parsed = _parse_ts(body)
        rest = _RE_NUMS_EVENT.match(body[parsed[3]:]) if parsed else None
        if not parsed or not rest:
            kind = classify_nondata(line)
            line_types[kind] += 1
            if kind == "json_chunk_key":
                chunk_key = _RE_CHUNK_KEY.match(line).group(1)
                chunk_dt = datetime.strptime(chunk_key, "%Y-%m-%d_%H-%M-%S")
            elif kind == "json_root_key":
                root_keys[_RE_ROOT_KEY.match(line).group(1)] += 1
            if kind not in ("blank", "json_struct", "json_chunk_key", "json_root_key"):
                bucket = samples.setdefault(kind, [])
                if len(bucket) < 3:
                    bucket.append(redact(line.strip())[:160])
            continue

        fmt, ts_raw, parts, _ = parsed
        ts: datetime | None = None
        try:
            if fmt == "ymd_hms":
                ts, ysrc = datetime(*parts), "explicit"
            elif fmt == "ymd_hm":
                ts, ysrc = datetime(*parts), "explicit"
            else:
                month, day, hh, mm, ss = parts
                if chunk_dt is not None:
                    year, ysrc = _infer_year(month, chunk_dt), "json_key"
                elif first_key_dt is not None:
                    year, ysrc = _infer_year(month, first_key_dt), "json_key_lookahead"
                elif year_hint is not None:
                    year, ysrc = int(year_hint), "config_hint"
                else:
                    year, ysrc = None, "unresolved"
                if year is not None:
                    ts = datetime(year, month, day, hh, mm, ss)
        except ValueError:
            ts, ysrc = None, "invalid"

        nums_s = rest.group("nums").split(",")
        nums = [_to_num(x) for x in nums_s]
        event_raw = (rest.group("event") or "").strip()
        device_id = None
        if len(nums) == 8:
            schema, vals = "p6_t_h", nums
        elif len(nums) == 9:
            schema, device_id, vals = "dev_p6_t_h", str(nums[0]), nums[1:]
        else:
            schema, vals = f"nonstandard_{len(nums)}", nums
        pressure = tuple(vals[:6]) if len(vals) >= 8 else tuple(vals)
        temp = vals[6] if len(vals) >= 8 else None
        humid = vals[7] if len(vals) >= 8 else None
        movement, control = split_event(event_raw)

        line_types["data"] += 1
        rows.append(DataRow(
            line_no=i, ts_raw=ts_raw, ts_format=fmt, ts=ts, year_source=ysrc,
            sep=rest.group("sep"), n_values=len(nums), schema=schema, device_id=device_id,
            pressure=pressure, temp=temp, humid=humid, event_raw=event_raw,
            movement=movement, control=control, chunk_key=chunk_key,
            has_decimal=any("." in x for x in nums_s),
        ))
    return line_types, rows, headers, chunk_keys_all, root_keys, samples


def parse_file(path: str | Path, year_hint: int | None = None) -> ParsedFile:
    raw = read_bytes(path)
    text, enc, has_bom = decode(raw)
    crlf = raw.count(b"\r\n")
    endings = Counter({"crlf": crlf, "lf": raw.count(b"\n") - crlf, "cr": raw.count(b"\r") - crlf})
    line_types, rows, headers, keys, roots, samples = parse_text(text, year_hint)
    return ParsedFile(
        encoding=enc, has_bom=has_bom, line_endings=endings, n_lines=sum(line_types.values()),
        line_types=line_types, rows=rows, headers=headers, chunk_keys=keys, root_keys=roots,
        samples=samples,
    )
