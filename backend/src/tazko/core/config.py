"""Settings from the environment (`TAZKO_*`), validated once at startup.

Production values live in /etc/tazko/tazko.env (set by the owner), which must
say TAZKO_ENV=production; then no `.env` file is read. Otherwise a `.env` in
the working directory is read too (real environment variables win). See
.env.example for the list.

`TAZKO_ENV` defaults to production, which requires https URLs and the Google
client (D16). Development (local runs, tests, e2e) relaxes those checks.
Every error names the environment variable to fix.
"""

from __future__ import annotations

import os
from functools import cached_property
from ipaddress import IPv4Address, IPv6Address, ip_address
from pathlib import Path
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

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
    # A stand-in Google on this machine for end-to-end tests (D32): its
    # /authorize, /token and /certs replace Google's, and only its issuer is
    # accepted. Empty means Google. Refused in production.
    google_url: str = ""
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

    @field_validator("google_url")
    @classmethod
    def _google_url(cls, value: str) -> str:
        value = value.rstrip("/")
        if not value:
            return value
        parts = urlsplit(value)
        host = parts.hostname or ""
        try:
            loopback = host == "localhost" or ip_address(host).is_loopback
        except ValueError:
            loopback = False
        if parts.scheme not in ("http", "https") or not loopback or parts.path:
            raise ValueError("must be a loopback URL like http://127.0.0.1:8792, or empty")
        return value

    @field_validator("host")
    @classmethod
    def _loopback(cls, value: IPv4Address | IPv6Address) -> IPv4Address | IPv6Address:
        # The tunnel is the only way in, which is why CF-Connecting-IP is trusted.
        if not value.is_loopback:
            raise ValueError(
                "must be a loopback address (127.0.0.1 or ::1); the tunnel serves the public"
            )
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
        return self

    def serving_problems(self) -> list[str]:
        """What stops this server from serving in production. Commands that do
        not serve (admin, backup, check) skip these checks."""
        if not self.is_production:
            return []
        problems = []
        if not self.google_client_id:
            problems.append("TAZKO_GOOGLE_CLIENT_ID: required in production (TAZKO_ENV)")
        if not self.google_client_secret.get_secret_value():
            problems.append("TAZKO_GOOGLE_CLIENT_SECRET: required in production (TAZKO_ENV)")
        if self.google_url:
            problems.append("TAZKO_GOOGLE_URL: must be empty in production (it is for e2e tests)")
        if not self.public_url.startswith("https://"):
            problems.append("TAZKO_PUBLIC_URL: must be an https URL in production")
        if not self.web_origin.startswith("https://"):
            problems.append("TAZKO_WEB_ORIGIN: must be an https origin in production")
        return problems

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


def load_settings(*, serving: bool = True, **overrides: object) -> Settings:
    """Build Settings, turning validation errors into one ConfigError that
    names the environment variables (TAZKO_PORT, not `port`).

    `serving=False` is for commands that never answer requests; they do not
    need the Google client or public URLs."""
    # A production service reads only its real environment (/etc/tazko/tazko.env
    # through systemd). A stray .env in the working folder must not change it.
    env_file = None if os.environ.get("TAZKO_ENV", "").lower() == "production" else ".env"
    try:
        settings = Settings(_env_file=env_file, **overrides)  # type: ignore[arg-type]
    except ValidationError as err:
        problems = [
            f"TAZKO_{str(e['loc'][0]).upper()}: {e['msg']}"
            if e["loc"]
            else str(e["msg"]).removeprefix("Value error, ")
            for e in err.errors()
        ]
        raise ConfigError("; ".join(problems)) from None
    if serving and (problems := settings.serving_problems()):
        raise ConfigError("; ".join(problems))
    return settings
