import sqlite3
from pathlib import Path

import pytest

from tazko.cli import main


def query(data: Path, sql: str) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(data / "control.db")
    try:
        return [tuple(row) for row in conn.execute(sql)]
    finally:
        conn.close()


def test_admin_creates_a_super_admin(tmp_path: Path) -> None:
    assert main(["admin", "--data", str(tmp_path), "--email", "Boss@Example.com"]) == 0
    assert query(tmp_path, "SELECT email, is_super_admin FROM users") == [("boss@example.com", 1)]
    assert query(tmp_path, "SELECT action FROM audit_log") == [("super_admin.granted",)]


def test_admin_names_the_database_it_wrote(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["admin", "--data", str(tmp_path), "--email", "boss@example.com"])
    assert str((tmp_path / "control.db").resolve()) in capsys.readouterr().out


def test_admin_refuses_a_missing_data_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # given no TAZKO_DATA_DIR in this shell, so the default ./data does not exist
    assert main(["admin", "--email", "boss@example.com"]) == 1
    err = capsys.readouterr().err
    assert "TAZKO_DATA_DIR" in err
    assert "--data" in err
    assert not (tmp_path / "data").exists()


def test_admin_promotes_an_existing_person(tmp_path: Path) -> None:
    main(["admin", "--data", str(tmp_path), "--email", "boss@example.com"])
    assert main(["admin", "--data", str(tmp_path), "--email", "boss@example.com"]) == 0
    assert query(tmp_path, "SELECT email, is_super_admin FROM users") == [("boss@example.com", 1)]


def test_admin_refuses_an_invalid_email(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["admin", "--data", str(tmp_path), "--email", "not-an-email"]) == 1
    assert "email" in capsys.readouterr().err


def test_admin_needs_no_google_client_in_production(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("TAZKO_ENV", "production")
    assert main(["admin", "--data", str(tmp_path), "--email", "boss@example.com"]) == 0


def test_unfinished_commands_fail_with_the_task_id(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check"]) == 1
    assert "M1-08" in capsys.readouterr().err


def test_bad_settings_fail_before_serving(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TAZKO_PORT", "0")
    assert main(["serve"]) == 1
    assert "TAZKO_PORT" in capsys.readouterr().err


def test_wrong_usage_exits_with_2() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["no-such-command"])
    assert exit_info.value.code == 2


def test_serve_turns_off_the_access_log(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The access log would write `/auth/google/callback?code=...` to the journal."""
    import uvicorn

    seen: dict[str, object] = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: seen.update(kwargs))
    monkeypatch.setenv("TAZKO_DATA_DIR", str(tmp_path))

    assert main(["serve"]) == 0
    assert seen["access_log"] is False


def test_serve_ignores_forwarded_headers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """cloudflared connects from loopback, which uvicorn trusts for X-Forwarded-For
    by default; a visitor could then set the address the app falls back to."""
    import uvicorn

    seen: dict[str, object] = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: seen.update(kwargs))
    monkeypatch.setenv("TAZKO_DATA_DIR", str(tmp_path))

    assert main(["serve"]) == 0
    assert seen["proxy_headers"] is False
