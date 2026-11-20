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
# Records calls. Markers in a release: BROKEN (never healthy), CONTRACT (migrates
# control.db so older releases fail /health), TENANT_CONTRACT (migrates a company
# file: /health still passes, tazko check fails for older releases).
echo "$*" >> "$WORK/calls"
unit="${@: -1}"
rel="$(readlink "$WORK/opt/current" || true)"
case "$1 $unit" in
  "restart tazko.service"|"start tazko.service")
    rm -f "$WORK/health"
    if [ -n "$rel" ] && [ ! -e "$rel/BROKEN" ]; then
      if [ ! -e "$WORK/contracted" ] || [ -e "$rel/CONTRACT" ]; then
        echo ok > "$WORK/health"
      fi
    fi
    [ -n "$rel" ] && [ -e "$rel/CONTRACT" ] && touch "$WORK/contracted"
    [ -n "$rel" ] && [ -e "$rel/TENANT_CONTRACT" ] && touch "$WORK/tenant-contracted"
    ;;
  "stop tazko.service") rm -f "$WORK/health" ;;
  "start tazko-check.service")
    [ -e "$WORK/tenant-contracted" ] && [ ! -e "$rel/TENANT_CONTRACT" ] && exit 1 ;;
  "start tazko-pre-release-backup.service")
    echo "backup-with $(basename "$rel")" >> "$WORK/calls"
    [ -e "$WORK/backup-fails" ] && exit 1
    touch "$WORK/backed-up" ;;
  "start tazko-restore.service")
    [ -e "$WORK/restore-fails" ] && exit 1
    rm -f "$WORK/contracted" "$WORK/tenant-contracted" ;;
esac
exit 0
"""

FAKE_PYTHON = """#!/usr/bin/env bash
# python3.12 -m venv DIR: a venv whose pip records its arguments
[ "$1 $2" = "-m venv" ] || exit 9
mkdir -p "$3/bin"
cat > "$3/bin/pip" <<'EOF'
#!/usr/bin/env bash
# pip-fails: every call fails; pip-fails-first: only the requirements install fails
echo "pip $*" >> "$WORK/calls"
[ -e "$WORK/pip-fails" ] && exit 1
[ -e "$WORK/pip-fails-first" ] && [[ " $* " == *" -r "* ]] && exit 1
exit 0
EOF
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

    # then the snapshot is taken by the release still running, after the install
    log = calls(work)
    assert "backup-with 20261120T100000Z-abc1234" in log
    assert max(i for i, c in enumerate(log) if c.startswith("pip")) < log.index(
        "start tazko-pre-release-backup.service"
    )
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
    assert log[-4:] == [
        "stop tazko.service",
        "start tazko-restore.service",
        "start tazko.service",
        "start tazko-check.service",
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


def test_a_failed_requirements_install_stops_before_the_switch(work: Path) -> None:
    # bash ignores set -e inside a function used as a condition: each step must stop it
    release(work, str(bundle(work, "20261120T100000Z")))
    (work / "pip-fails-first").touch()

    done = release(work, str(bundle(work, "20261120T110000Z")))

    assert done.returncode == 1
    assert "nothing changed" in done.stderr
    assert current(work) == "20261120T100000Z-abc1234"
    assert calls(work).count("restart tazko.service") == 1  # only the first release


def test_a_company_file_the_old_release_refuses_is_restored_too(work: Path) -> None:
    # given the new release migrates a company file (health still passes) and then fails
    release(work, str(bundle(work, "20261120T100000Z")))

    done = release(work, str(bundle(work, "20261120T110000Z", marks=("TENANT_CONTRACT", "BROKEN"))))

    # then tazko check refuses the data for the old release, so the backup is restored
    assert done.returncode == 1
    assert "restored the pre-release backup" in done.stderr
    assert "start tazko-restore.service" in calls(work)


def test_a_failed_restore_says_the_service_is_stopped(work: Path) -> None:
    release(work, str(bundle(work, "20261120T100000Z")))
    (work / "restore-fails").touch()

    done = release(work, str(bundle(work, "20261120T110000Z", marks=("CONTRACT", "BROKEN"))))

    assert done.returncode == 3
    assert "tazko.service is stopped" in done.stderr


def test_a_release_that_failed_can_be_tried_again(work: Path) -> None:
    release(work, str(bundle(work, "20261120T100000Z")))
    broken = bundle(work, "20261120T110000Z", marks=("BROKEN",))
    release(work, str(broken))
    bundle(work, "20261120T110000Z")  # same name, fixed

    done = release(work, str(broken))

    assert done.returncode == 0, done.stderr
    assert current(work) == "20261120T110000Z-abc1234"
    assert not (work / "opt" / "releases" / "20261120T110000Z-abc1234" / "FAILED").exists()


def test_a_healthy_release_cannot_be_installed_twice(work: Path) -> None:
    made = bundle(work, "20261120T100000Z")
    release(work, str(made))

    done = release(work, str(made))

    assert done.returncode == 1
    assert "already installed" in done.stderr


def test_rollback_to_a_release_the_data_refuses_comes_back(work: Path) -> None:
    release(work, str(bundle(work, "20261120T100000Z")))
    release(work, str(bundle(work, "20261120T110000Z", marks=("TENANT_CONTRACT",))))

    done = release(work, "--rollback")

    assert done.returncode == 1
    assert "cannot run on this data" in done.stderr
    assert current(work) == "20261120T110000Z-abc1234"
    assert "start tazko-restore.service" not in calls(work)  # never on a manual rollback
