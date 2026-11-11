"""Settings from the environment (`TAZKO_*`), validated once at startup.

Production values live in /etc/tazko/tazko.env (set by the owner); in
development a `.env` file in the working directory is read too. See
.env.example for the list.

TODO(M1-02): Google client id/secret, TAZKO_SECRET (or the generated
secret file), SMTP settings; clear error for each missing required value.
"""

from __future__ import annotations

from functools import cached_property
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Port = Annotated[int, Field(ge=1, le=65535)]


class ConfigError(ValueError):
    """A setting is missing or malformed. The message names the variable."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TAZKO_", env_file=".env", extra="ignore", frozen=True
    )

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
            f"TAZKO_{str(e['loc'][0]).upper()}: {e['msg']}" for e in err.errors() if e["loc"]
        )
        raise ConfigError(problems) from None
