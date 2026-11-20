"""deploy/backend/release.sh as a dry run (M1-08): a temp folder stands in for
/opt/tazko, fake `systemctl` and `python3.12` record what they are asked, and
the health check reads a file that the fake systemctl writes on restart.

A release is healthy unless its bundle holds a file named BROKEN. When the
data is "migrated" by a release that holds CONTRACT, older releases are
unhealthy until the fake restore unit runs (D36 path 2)."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "deploy" / "backend" / "release.sh"
BASH = shutil.which("bash") or "/bin/bash"

pytestmark = pytest.mark.skipif(
    os.name != "posix" or shutil.which("bash") is None or shutil.which("curl") is None,
    reason="release.sh runs on Linux (needs real symlinks, bash and curl)",
)

FAKE_SYSTEMCTL = """#!/usr/bin/env bash
# records calls; on (re)start of tazko.service decides health from the current release
echo "$*" >> "$WORK/calls"
unit="${@: -1}"
case "$1 $unit" in
  "restart tazko.service"|"start tazko.service")
    rel="$(readlink "$WORK/opt/current" || true)"
    rm -f "$WORK/health"
    if [ -n "$rel" ] && [ ! -e "$rel/BROKEN" ]; then
      if [ ! -e "$WORK/contracted" ] || [ -e "$rel/CONTRACT" ]; then
        echo ok > "$WORK/health"
      fi
    fi
    [ -n "$rel" ] && [ -e "$rel/CONTRACT" ] && touch "$WORK/contracted"
    ;;
  "stop tazko.service") rm -f "$WORK/health" ;;
  "start tazko-pre-release-backup.service")
    [ -e "$WORK/backup-fails" ] && exit 1
    touch "$WORK/backed-up" ;;
  "start tazko-restore.service") rm -f "$WORK/contracted" ;;
esac
exit 0
"""

FAKE_PYTHON = """#!/usr/bin/env bash
# python3.12 -m venv DIR: a venv whose pip records its arguments
[ "$1 $2" = "-m venv" ] || exit 9
mkdir -p "$3/bin"
printf '#!/usr/bin/env bash\\necho "pip $*" >> "%s/calls"\\n[ -e "%s/pip-fails" ] && exit 1\\nexit 0\\n' \
  "$WORK" "$WORK" > "$3/bin/pip"
chmod +x "$3/bin/pip"
"""


@pytest.fixture
def work(tmp_path: Path) -> Path:
    for name, body in (("systemctl", FAKE_SYSTEMCTL), ("python3.12", FAKE_PYTHON)):
        path = tmp_path / "bin" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(body)
        path.chmod(0o755)
    (tmp_path / "opt" / "releases").mkdir(parents=True)
    (tmp_path / "incoming").mkdir()
    (tmp_path / "calls").touch()
    return tmp_path


def bundle(work: Path, stamp: str, *, marks: tuple[str, ...] = ()) -> Path:
    path = work / "incoming" / f"tazko-{stamp}-abc1234.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for name in ("VERSION", "requirements.txt", "tazko-0.1.0-py3-none-any.whl", *marks):
            data = b"x\n"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def release(work: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": f"{work / 'bin'}:/usr/bin:/bin",
        "WORK": str(work),
        "TAZKO_RELEASE_ROOT": str(work / "opt"),
        "TAZKO_INCOMING": str(work / "incoming"),
        "TAZKO_HEALTH_URL": f"file://{work / 'health'}",
        "TAZKO_HEALTH_SECONDS": "2",
        "TAZKO_PYTHON": str(work / "bin" / "python3.12"),
        "TAZKO_SYSTEMCTL": str(work / "bin" / "systemctl"),
    }
    return subprocess.run(  # noqa: S603 (our own script, fixed arguments from the tests)
        [BASH, str(SCRIPT), *args], env=env, capture_output=True, text=True, check=False
    )


def current(work: Path) -> str:
    return Path(os.readlink(work / "opt" / "current")).name


def calls(work: Path) -> list[str]:
    return (work / "calls").read_text().splitlines()


def test_a_healthy_release_becomes_current(work: Path) -> None:
    done = release(work, str(bundle(work, "20261120T100000Z")))

    assert done.returncode == 0, done.stderr
    assert current(work) == "20261120T100000Z-abc1234"
    pip = [c for c in calls(work) if c.startswith("pip")]
    assert "--require-hashes" in pip[0] and "--only-binary :all:" in pip[0]
    assert "restart tazko.service" in calls(work)


def test_the_first_release_needs_no_pre_release_backup(work: Path) -> None:
    release(work, str(bundle(work, "20261120T100000Z")))

    assert "start tazko-pre-release-backup.service" not in calls(work)


def test_a_later_release_backs_up_before_switching(work: Path) -> None:
    release(work, str(bundle(work, "20261120T100000Z")))

    release(work, str(bundle(work, "20261120T110000Z")))

    log = calls(work)
    assert log.index("start tazko-pre-release-backup.service") < len(log) - 1
    assert current(work) == "20261120T110000Z-abc1234"


def test_a_broken_release_rolls_back_by_itself(work: Path) -> None:
    release(work, str(bundle(work, "20261120T100000Z")))

    done = release(work, str(bundle(work, "20261120T110000Z", marks=("BROKEN",))))

    assert done.returncode == 1
    assert "rolled back to 20261120T100000Z-abc1234" in done.stderr
    assert current(work) == "20261120T100000Z-abc1234"
    assert (work / "health").exists()  # the previous release answers again
    assert (work / "opt" / "releases" / "20261120T110000Z-abc1234" / "FAILED").exists()


def test_a_rollback_the_data_refuses_restores_the_pre_release_backup(work: Path) -> None:
    # given the new release migrates the data so the old one cannot use it, then fails
    release(work, str(bundle(work, "20261120T100000Z")))

    done = release(work, str(bundle(work, "20261120T110000Z", marks=("CONTRACT", "BROKEN"))))

    # then the old release fails on the data too, so the backup is restored
    assert done.returncode == 1
    log = calls(work)
    assert log[-3:] == [
        "stop tazko.service",
        "start tazko-restore.service",
        "start tazko.service",
    ]
    assert "restored the pre-release backup" in done.stderr
    assert current(work) == "20261120T100000Z-abc1234"
    assert (work / "health").exists()


def test_a_failed_pre_release_backup_stops_the_release(work: Path) -> None:
    release(work, str(bundle(work, "20261120T100000Z")))
    (work / "backup-fails").touch()

    done = release(work, str(bundle(work, "20261120T110000Z")))

    assert done.returncode == 1
    assert current(work) == "20261120T100000Z-abc1234"
    assert not (work / "opt" / "releases" / "20261120T110000Z-abc1234").exists()


def test_a_failed_install_leaves_nothing_behind(work: Path) -> None:
    release(work, str(bundle(work, "20261120T100000Z")))
    (work / "pip-fails").touch()

    done = release(work, str(bundle(work, "20261120T110000Z")))

    assert done.returncode == 1
    assert current(work) == "20261120T100000Z-abc1234"
    assert sorted(p.name for p in (work / "opt" / "releases").iterdir()) == [
        "20261120T100000Z-abc1234"
    ]


def test_rollback_goes_back_one_healthy_release(work: Path) -> None:
    for stamp in ("20261120T100000Z", "20261120T110000Z"):
        release(work, str(bundle(work, stamp)))

    done = release(work, "--rollback")

    assert done.returncode == 0, done.stderr
    assert current(work) == "20261120T100000Z-abc1234"


def test_rollback_skips_a_release_that_failed(work: Path) -> None:
    release(work, str(bundle(work, "20261120T090000Z")))
    release(work, str(bundle(work, "20261120T100000Z", marks=("BROKEN",))))  # failed, rolled back
    release(work, str(bundle(work, "20261120T110000Z")))

    release(work, "--rollback")

    assert current(work) == "20261120T090000Z-abc1234"


def test_list_marks_the_current_release(work: Path) -> None:
    for stamp in ("20261120T100000Z", "20261120T110000Z"):
        release(work, str(bundle(work, stamp)))

    listed = release(work, "--list").stdout.splitlines()

    assert listed == ["  20261120T100000Z-abc1234", "* 20261120T110000Z-abc1234"]


def test_only_the_last_five_releases_are_kept(work: Path) -> None:
    for hour in range(10, 17):
        release(work, str(bundle(work, f"20261120T{hour}0000Z")))

    kept = sorted(p.name for p in (work / "opt" / "releases").iterdir())

    assert kept == [f"20261120T{hour}0000Z-abc1234" for hour in range(12, 17)]


@pytest.mark.parametrize(
    "name", ["evil.tar.gz", "tazko-20261120T100000Z-abc1234.tar.gz/../../x", "tazko-now-abc.tar.gz"]
)
def test_a_bundle_with_an_unexpected_name_is_refused(work: Path, name: str) -> None:
    done = release(work, str(work / "incoming" / name))

    assert done.returncode == 2
    assert list((work / "opt" / "releases").iterdir()) == []


def test_a_bundle_outside_the_incoming_folder_is_refused(work: Path, tmp_path: Path) -> None:
    made = bundle(work, "20261120T100000Z")
    elsewhere = tmp_path / made.name
    made.rename(elsewhere)

    assert release(work, str(elsewhere)).returncode == 2
