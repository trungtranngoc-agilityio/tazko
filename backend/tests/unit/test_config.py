from pathlib import Path

import pytest

from tazko.core.config import ConfigError, load_settings


def test_defaults_listen_on_loopback_8791() -> None:
    settings = load_settings()
    assert settings.addr == "127.0.0.1:8791"
    assert settings.api_url == "http://127.0.0.1:8791"


def test_reads_tazko_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAZKO_PORT", "9000")
    monkeypatch.setenv("TAZKO_LOG", "debug")
    settings = load_settings()
    assert settings.port == 9000
    assert settings.log == "DEBUG"


def test_reads_a_dotenv_file_in_the_working_directory(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("TAZKO_PORT=9100\n")
    assert load_settings().port == 9100


def test_bad_port_names_the_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAZKO_PORT", "abc")
    with pytest.raises(ConfigError, match="TAZKO_PORT"):
        load_settings()


@pytest.mark.parametrize("origin", ["tazko.example", "https://tazko.example.com/app"])
def test_web_origin_must_be_an_origin(monkeypatch: pytest.MonkeyPatch, origin: str) -> None:
    monkeypatch.setenv("TAZKO_WEB_ORIGIN", origin)
    with pytest.raises(ConfigError, match="TAZKO_WEB_ORIGIN"):
        load_settings()


def test_web_origin_drops_the_trailing_slash() -> None:
    settings = load_settings(web_origin="https://tazko.example.com/")
    assert settings.web_origin == "https://tazko.example.com"
