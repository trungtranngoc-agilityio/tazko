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


def test_production_ignores_a_dotenv_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # given the service environment says production and someone left a .env in the folder
    production(monkeypatch)
    (tmp_path / ".env").write_text(
        "TAZKO_PORT=9100\nTAZKO_DATA_DIR=/tmp/elsewhere\nTAZKO_SMTP_HOST=smtp.evil.example\n"
    )
    # then none of it is read
    settings = load_settings()
    assert settings.port == 8791
    assert settings.data_dir == Path("./data")
    assert not settings.email_enabled


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


def production(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    base = {
        "TAZKO_ENV": "production",
        "TAZKO_PUBLIC_URL": "https://api.example.com",
        "TAZKO_WEB_ORIGIN": "https://web.example.com",
        "TAZKO_GOOGLE_CLIENT_ID": "client-id",
        "TAZKO_GOOGLE_CLIENT_SECRET": "client-secret",
    }
    base.update(values)
    for key, value in base.items():
        monkeypatch.setenv(key, value)


def test_production_settings_load_when_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    production(monkeypatch)
    settings = load_settings()
    assert settings.is_production
    assert settings.google_client_secret.get_secret_value() == "client-secret"


def test_environment_defaults_to_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAZKO_ENV")
    with pytest.raises(ConfigError, match="TAZKO_GOOGLE_CLIENT_ID"):
        load_settings()


@pytest.mark.parametrize("missing", ["TAZKO_GOOGLE_CLIENT_ID", "TAZKO_GOOGLE_CLIENT_SECRET"])
def test_production_requires_google_client(monkeypatch: pytest.MonkeyPatch, missing: str) -> None:
    production(monkeypatch, **{missing: ""})
    with pytest.raises(ConfigError, match=missing):
        load_settings()


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("TAZKO_PUBLIC_URL", "http://api.example.com"),
        ("TAZKO_PUBLIC_URL", ""),
        ("TAZKO_WEB_ORIGIN", "http://web.example.com"),
    ],
)
def test_production_requires_https_urls(
    monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    production(monkeypatch, **{variable: value})
    with pytest.raises(ConfigError, match=variable):
        load_settings()


def test_development_needs_no_google_client() -> None:
    settings = load_settings(env="development")
    assert not settings.is_production
    assert settings.google_client_id == ""


def test_short_secret_is_refused() -> None:
    with pytest.raises(ConfigError, match="TAZKO_SECRET"):
        load_settings(env="development", secret="too-short")


def test_public_url_must_be_a_url() -> None:
    with pytest.raises(ConfigError, match="TAZKO_PUBLIC_URL"):
        load_settings(env="development", public_url="api.example.com")


def test_smtp_needs_mail_from() -> None:
    with pytest.raises(ConfigError, match="TAZKO_MAIL_FROM"):
        load_settings(env="development", smtp_host="smtp.example.com")


def test_email_is_off_without_smtp_host() -> None:
    assert not load_settings(env="development").email_enabled


def test_secrets_are_hidden_in_repr() -> None:
    settings = load_settings(env="development", google_client_secret="hunter2-hunter2")
    assert "hunter2" not in repr(settings)


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.86.49", "::"])  # noqa: S104  # refused on purpose
def test_host_must_be_loopback(host: str) -> None:
    # The server trusts CF-Connecting-IP only because nothing but the tunnel reaches it.
    with pytest.raises(ConfigError, match="TAZKO_HOST"):
        load_settings(host=host)


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1"])
def test_loopback_hosts_are_accepted(host: str) -> None:
    assert str(load_settings(host=host).host) == host
