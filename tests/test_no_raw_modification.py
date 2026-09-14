"""Raw data must never be modified, deleted or overwritten (docs/DATA_POLICY.md)."""
from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from src.data import paths
from src.data.io_guard import RawWriteError, assert_writable, is_protected, open_for_write, remove_file, write_text
from src.data.manifest import read_manifest, sha256_file
from src.data.raw_parser import parse_file

CODE_DIRS = [paths.PROJECT_ROOT / "src", paths.PROJECT_ROOT / "scripts"]
GUARD_MODULE = paths.PROJECT_ROOT / "src" / "data" / "io_guard.py"

# Direct write / delete / move primitives. All writes must go through src/data/io_guard.py.
FORBIDDEN = {
    "open() in write/append mode": re.compile(r"""\bopen\([^)]*,\s*(?:mode\s*=\s*)?['"][^'"]*[wax+]"""),
    "Path.write_text/write_bytes": re.compile(r"\.write_(?:text|bytes)\((?!.*io_guard)"),
    "Path.open in write mode": re.compile(r"""\.open\(\s*['"][^'"]*[wax+]"""),
    "delete": re.compile(r"\bos\.(?:remove|unlink|rmdir|removedirs)\(|\.unlink\(|\.rmdir\("),
    "move/rename": re.compile(r"\bos\.(?:rename|replace)\(|\bshutil\.(?:move|rmtree|copy\w*)\(|\.rename\(|\.replace\(\s*[A-Za-z_]\w*\s*\)"),
    "permission change": re.compile(r"\bos\.(?:chmod|chown)\(|\.chmod\("),
    "pandas/numpy writers": re.compile(r"\.to_(?:csv|parquet|pickle|excel|json|feather|hdf)\(|\bnp\.save\w*\("),
}


def _code_files():
    for d in CODE_DIRS:
        for p in d.rglob("*.py"):
            if p.resolve() != GUARD_MODULE.resolve():
                yield p


def test_no_direct_write_primitives_outside_io_guard():
    offenders = []
    for p in _code_files():
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
            code = line.split("#", 1)[0]
            for label, rx in FORBIDDEN.items():
                if rx.search(code):
                    offenders.append(f"{p.relative_to(paths.PROJECT_ROOT)}:{n}: {label}: {line.strip()}")
    assert not offenders, "Writes must go through src/data/io_guard.py:\n" + "\n".join(offenders)


def test_no_hardcoded_raw_paths_in_code():
    raw_literals = [paths.path_config()["raw_package_root"], "data/raw", "data\\\\raw"]
    offenders = [
        f"{p.relative_to(paths.PROJECT_ROOT)}: {lit}"
        for p in _code_files()
        for lit in raw_literals
        if lit in p.read_text(encoding="utf-8")
    ]
    assert not offenders, "Raw locations must come from configs/paths.yaml:\n" + "\n".join(offenders)


# --- runtime guard ---------------------------------------------------------------------------

def test_guard_blocks_every_protected_root():
    for root in paths.protected_roots():
        assert is_protected(root)
        with pytest.raises(RawWriteError):
            assert_writable(root / "any_new_file.txt")
        with pytest.raises(RawWriteError):
            assert_writable(root / "sub" / "dir" / "file.csv")


def test_guard_blocks_path_traversal_into_raw():
    sneaky = paths.PROJECT_ROOT / "outputs" / ".." / paths.path_config()["raw_root"] / "x.txt"
    with pytest.raises(RawWriteError):
        assert_writable(sneaky)


def test_guard_blocks_case_variants_on_windows():
    import os
    if os.name != "nt":
        pytest.skip("case-insensitive filesystem check is Windows-specific")
    with pytest.raises(RawWriteError):
        assert_writable(str(paths.raw_root()).upper() + "\\x.txt")


def test_guard_allows_outputs_and_interim():
    assert_writable(paths.PROJECT_ROOT / "outputs" / "qa" / "x.txt")
    assert_writable(paths.PROJECT_ROOT / "data" / "interim" / "x.csv")


def test_write_helpers_refuse_raw():
    with pytest.raises(RawWriteError):
        open_for_write(paths.raw_root() / "should_not_exist.txt")
    with pytest.raises(RawWriteError):
        write_text(paths.raw_root() / "should_not_exist.txt", "x")
    assert not (paths.raw_root() / "should_not_exist.txt").exists()
    for root in paths.protected_roots():
        with pytest.raises(RawWriteError):
            remove_file(root / "README.md")


def test_remove_file_deletes_only_regular_files_outside_raw(tmp_path):
    p = write_text(tmp_path / "stale.json", "{}")
    remove_file(p)
    assert not p.exists()
    remove_file(p)                                              # missing: no error
    remove_file(tmp_path)                                       # a directory is left alone
    assert tmp_path.is_dir()


# --- integrity against the manifest -----------------------------------------------------------

raw_present = paths.raw_root().is_dir() and paths.manifest_path().exists()


@pytest.mark.skipif(not raw_present, reason="raw data or manifest not present")
def test_raw_files_match_manifest_checksums():
    root = paths.raw_root()
    rows = read_manifest(paths.manifest_path())
    changed = [r["source_relpath"] for r in rows if sha256_file(root / r["source_relpath"]) != r["sha256"]]
    on_disk = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    listed = {r["source_relpath"] for r in rows}
    assert not changed, f"raw files modified: {changed[:10]}"
    assert not (listed - on_disk), f"raw files missing: {sorted(listed - on_disk)[:10]}"
    assert not (on_disk - listed), f"raw files not in manifest: {sorted(on_disk - listed)[:10]}"


@pytest.mark.skipif(not raw_present, reason="raw data or manifest not present")
def test_parsing_does_not_touch_raw_file():
    root = paths.raw_root()
    target = next(p for p in sorted(root.rglob("*.txt")))
    before = (sha256_file(target), target.stat().st_mtime_ns)
    parse_file(target)
    assert (sha256_file(target), target.stat().st_mtime_ns) == before


# --- version control ----------------------------------------------------------------------------

def _git(*args):
    return subprocess.run(["git", *args], cwd=paths.PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8")


git_ok = shutil.which("git") is not None and (paths.PROJECT_ROOT / ".git").exists()


@pytest.mark.skipif(not git_ok, reason="not a git repository")
def test_raw_data_is_git_ignored():
    root = paths.raw_root()
    sample = next((p for p in root.rglob("*") if p.is_file()), None) if root.exists() else None
    if sample is None:
        pytest.skip("raw data not present (e.g. a clean checkout)")
    res = _git("check-ignore", "-q", str(sample.relative_to(paths.PROJECT_ROOT)))
    assert res.returncode == 0, f"raw file is not ignored by .gitignore: {sample}"


@pytest.mark.skipif(not git_ok, reason="not a git repository")
def test_no_raw_file_is_tracked():
    tracked = _git("ls-files", "-z").stdout.split("\0")
    prefixes = [paths.path_config()["raw_package_root"] + "/", "data/raw/"]
    bad = [t for t in tracked if any(t.startswith(p) for p in prefixes) and t != "data/raw/README.md"]
    assert not bad, f"raw files tracked by git: {bad[:10]}"
