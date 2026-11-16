"""Settings from the environment (`TAZKO_*`), validated once at startup.

Production values live in /etc/tazko/tazko.env (set by the owner); in
development a `.env` file in the working directory is read too. See
.env.example for the list.

`TAZKO_ENV` defaults to production, which requires https URLs and the Google
client (D16). Development (local runs, tests, e2e) relaxes those checks.
Every error names the environment variable to fix.
"""

from __future__ import annotations

from functools import cached_property
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Port = Annotated[int, Field(ge=1, le=65535)]


class ConfigError(ValueError):
    """A setting is missing or malformed. The message names the variable."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TAZKO_", env_file=".env", extra="ignore", frozen=True
    )

    env: Literal["production", "development"] = "production"
    host: IPv4Address | IPv6Address = IPv4Address("127.0.0.1")
    port: Port = 8791
    # Public base URL of this API; OAuth redirect addresses start with it.
    # Empty means http://<host>:<port>.
    public_url: str = ""
    # Origin of the separately deployed web app (D13). The only origin allowed
    # by CORS and by the Origin check on writes and WebSockets.
    web_origin: str = "http://localhost:5173"
    data_dir: Path = Path("./data")
    log: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Google OIDC web client (P0-2). Required in production.
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")
    # Signs cookies and state. Empty means a random `secret` file in the data
    # folder, made on first start (tazko.core.secret).
    secret: SecretStr = SecretStr("")

    # Email (optional, M6). Off unless TAZKO_SMTP_HOST is set.
    smtp_host: str = ""
    smtp_port: Port = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    mail_from: str = ""

    @field_validator("public_url")
    @classmethod
    def _public_url(cls, value: str) -> str:
        value = value.rstrip("/")
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("must be a URL like https://tazko-api.example.com")
        return value

    @field_validator("secret")
    @classmethod
    def _secret(cls, value: SecretStr) -> SecretStr:
        if 0 < len(value.get_secret_value()) < 32:
            raise ValueError("must be at least 32 characters, or empty to use the secret file")
        return value

    @field_validator("smtp_port", mode="before")
    @classmethod
    def _empty_port(cls, value: object) -> object:
        return 587 if value == "" else value

    @model_validator(mode="after")
    def _complete(self) -> Self:
        if self.smtp_host and not self.mail_from:
            raise ValueError("TAZKO_MAIL_FROM: required when TAZKO_SMTP_HOST is set")
        if not self.is_production:
            return self
        if not self.google_client_id:
            raise ValueError("TAZKO_GOOGLE_CLIENT_ID: required in production (TAZKO_ENV)")
        if not self.google_client_secret.get_secret_value():
            raise ValueError("TAZKO_GOOGLE_CLIENT_SECRET: required in production (TAZKO_ENV)")
        if not self.public_url.startswith("https://"):
            raise ValueError("TAZKO_PUBLIC_URL: must be an https URL in production")
        if not self.web_origin.startswith("https://"):
            raise ValueError("TAZKO_WEB_ORIGIN: must be an https origin in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host)

    @field_validator("web_origin")
    @classmethod
    def _origin(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value.startswith(("https://", "http://")) or "/" in value.split("://", 1)[1]:
            raise ValueError("must be an origin like https://tazko.example.com")
        return value

    @field_validator("log", mode="before")
    @classmethod
    def _log_upper(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @cached_property
    def addr(self) -> str:
        return f"{self.host}:{self.port}"

    @cached_property
    def api_url(self) -> str:
        return self.public_url.rstrip("/") or f"http://{self.addr}"


def load_settings(**overrides: object) -> Settings:
    """Build Settings, turning validation errors into one ConfigError that
    names the environment variables (TAZKO_PORT, not `port`)."""
    try:
        return Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as err:
        problems = "; ".join(
            f"TAZKO_{str(e['loc'][0]).upper()}: {e['msg']}"
            if e["loc"]
            else str(e["msg"]).removeprefix("Value error, ")
            for e in err.errors()
        )
        raise ConfigError(problems) from None
