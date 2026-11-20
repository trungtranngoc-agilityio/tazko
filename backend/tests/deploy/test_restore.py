"""deploy/backend/restore-pre-release.sh on a temp folder (D36, D37): the newest
recent snapshot replaces the data, after `tazko check` accepts it; the replaced
data and its trash are kept."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "deploy" / "backend" / "restore-pre-release.sh"
BASH = shutil.which("bash") or "/bin/bash"

pytestmark = pytest.mark.skipif(
    os.name != "posix" or shutil.which("bash") is None,
    reason="restore-pre-release.sh runs on Linux (GNU find and date)",
)

FAKE_TAZKO = """#!/usr/bin/env bash
# tazko check --data DIR: fails when DIR holds a file named CORRUPT
[ "$1 $2" = "check --data" ] || exit 9
[ -e "$3/CORRUPT" ] && exit 1
exit 0
"""


def stamp(minutes_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).strftime("%Y%m%dT%H%M%SZ")


@pytest.fixture
def base(tmp_path: Path) -> Path:
    data = tmp_path / "lib" / "data"
    (data / "trash" / "gone-20261101T000000Z").mkdir(parents=True)
    (data / "control.db").write_text("live")
    (tmp_path / "snapshots").mkdir()
    fake = tmp_path / "tazko"
    fake.write_text(FAKE_TAZKO)
    fake.chmod(0o755)
    return tmp_path


def snapshot(base: Path, minutes_ago: int, content: str, *, corrupt: bool = False) -> str:
    name = stamp(minutes_ago)
    folder = base / "snapshots" / name
    folder.mkdir()
    (folder / "control.db").write_text(content)
    if corrupt:
        (folder / "CORRUPT").touch()
    return name


def restore(base: Path) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": "/usr/bin:/bin",
        "TAZKO_BASE": str(base / "lib"),
        "TAZKO_SNAPSHOTS": str(base / "snapshots"),
        "TAZKO_BIN": str(base / "tazko"),
    }
    return subprocess.run(  # noqa: S603 (our own script, fixed arguments from the tests)
        [BASH, str(SCRIPT)], env=env, capture_output=True, text=True, check=False
    )


def test_the_newest_snapshot_replaces_the_data_and_the_old_data_is_kept(base: Path) -> None:
    snapshot(base, 10, "older")
    snapshot(base, 2, "newest")

    done = restore(base)

    assert done.returncode == 0, done.stderr
    lib = base / "lib"
    assert (lib / "data" / "control.db").read_text() == "newest"
    [failed] = [p for p in lib.iterdir() if p.name.startswith("data.failed-")]
    assert (failed / "control.db").read_text() == "live"
    assert (lib / "data" / "trash" / "gone-20261101T000000Z").is_dir()  # trash moved over
    assert not (lib / "data.new").exists()


def test_a_snapshot_that_fails_the_check_leaves_the_data_alone(base: Path) -> None:
    snapshot(base, 2, "bad", corrupt=True)

    done = restore(base)

    assert done.returncode == 1
    assert "failed the check" in done.stderr
    assert (base / "lib" / "data" / "control.db").read_text() == "live"
    assert not [p for p in (base / "lib").iterdir() if p.name.startswith("data.failed-")]


def test_an_old_snapshot_is_refused(base: Path) -> None:
    # started by hand days after a release: restoring would drop everything since
    snapshot(base, 60 * 24 * 3, "three days old")

    done = restore(base)

    assert done.returncode == 1
    assert "minutes old" in done.stderr
    assert (base / "lib" / "data" / "control.db").read_text() == "live"


def test_no_snapshot_is_refused(base: Path) -> None:
    done = restore(base)

    assert done.returncode == 1
    assert "no pre-release snapshot" in done.stderr
