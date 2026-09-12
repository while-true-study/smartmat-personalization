"""Line-family recognition in the read-only audit parser (no cleaning semantics are tested)."""
from __future__ import annotations

from datetime import datetime

from src.data.raw_parser import parse_text, redact


def rows_of(text, year_hint=None):
    line_types, rows, headers, keys, roots, samples = parse_text(text, year_hint)
    return line_types, rows


def test_plain_full_timestamp_row():
    lt, rows = rows_of("2025-08-25 22:21:51,0,0,0,0,0,0,28,68, 자리비움\r\n")
    r = rows[0]
    assert r.ts == datetime(2025, 8, 25, 22, 21, 51) and r.year_source == "explicit"
    assert r.schema == "p6_t_h" and r.temp == 28 and r.humid == 68 and r.movement == "absent"


def test_legacy_minute_timestamp_and_header():
    text = "TS(YYYY-MM-DD HH:MM),FSR1(A0),FSR2(A1),FSR3(A2),FSR4(A3),FSR5(A4),FSR6(A5),Temp(℃),Hum(%),Event\n" \
           "2025-10-05 0:50,0,0,0,170,77,6,25,67, 우로이동\n,,,,,,,,,\n"
    lt, rows = rows_of(text)
    assert lt["header"] == 1 and lt["empty_csv_row"] == 1
    assert rows[0].ts_format == "ymd_hm" and rows[0].ts == datetime(2025, 10, 5, 0, 50)


def test_dot_separator_before_p1_is_detected():
    lt, rows = rows_of("2025-10-03 19:40:10.4012,0,0,2,0,0,28,53, 좌로이동\n")
    r = rows[0]
    assert r.sep == "." and r.pressure[0] == 4012 and r.temp == 28 and r.humid == 53


def test_md_rows_take_year_from_json_key_across_new_year():
    text = '{\n "2026-01-01_00-06-51": {\n  "csvData": "12-31 23:40:00,1,0,0,0,0,0,29,18, LM\n' \
           '01-01 00:00:02,1,0,0,0,0,0,29,18, LM\n"\n }\n}\n'
    lt, rows = rows_of(text)
    assert [r.ts.year for r in rows] == [2025, 2026]
    assert {r.year_source for r in rows} == {"json_key"}


def test_md_rows_before_first_key_use_lookahead():
    text = "\n01-01 00:00:52,247,479,95,0,0,0,29,18, RM\n\"\n },\n \"2026-01-01_00-36-51\": {\n" \
           '  "csvData": "01-01 00:06:46,0,0,12,0,0,0,29,18, NM\n"\n }\n'
    lt, rows = rows_of(text)
    assert rows[0].year_source == "json_key_lookahead" and rows[0].ts.year == 2026
    assert rows[1].year_source == "json_key"


def test_md_rows_without_key_use_hint_or_stay_unresolved():
    line = "11-05 19:23:17,0,0,0,0,4008,0,26,30, DM\n"
    assert rows_of(line, year_hint=2025)[1][0].year_source == "config_hint"
    unresolved = rows_of(line)[1][0]
    assert unresolved.year_source == "unresolved" and unresolved.ts is None


def test_device_column_schema():
    lt, rows = rows_of("08-29 21:00:01,22480,0,0,1229,0,0,5,28,52,AHON LM\n", year_hint=2026)
    r = rows[0]
    assert r.schema == "dev_p6_t_h" and r.device_id == "22480" and r.pressure == (0, 0, 1229, 0, 0, 5)
    assert r.control == "AHON" and r.movement == "left"


def test_device_log_lines_are_not_data():
    text = "[NVS] 저장: targetTemperature=28.00\nGuru Meditation Error: Core  1 panic'ed\n" \
           "⏫ Firebase 업로드 시작\nBacktrace: 0x400d1234:0x3ffb1f00\n"
    lt, rows = rows_of(text)
    assert not rows
    assert lt["nvs_log"] == 1 and lt["crash_dump"] == 2 and lt["device_log"] == 1


def test_long_digit_identifiers_are_redacted():
    assert redact("chatIDs=1234567890") == "chatIDs=<redacted>"
    assert redact("07-19 19:54:06,0,0,1229") == "07-19 19:54:06,0,0,1229"
