import pytest

from tazko.cli import main


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
