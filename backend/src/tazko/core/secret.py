"""The server secret that signs cookies and OAuth state.

`TAZKO_SECRET` wins. Without it, a random secret is kept in `<data>/secret`,
made on first start with mode 600, so restarts keep sessions valid.
"""

from __future__ import annotations

import os
import secrets

from tazko.core.config import ConfigError, Settings

FILE_NAME = "secret"


def load_secret(settings: Settings) -> bytes:
    configured = settings.secret.get_secret_value()
    if configured:
        return configured.encode()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    path = settings.data_dir / FILE_NAME
    try:
        # O_EXCL: two processes starting at once cannot both write a secret.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        value = path.read_bytes().strip()
        if len(value) < 32:
            raise ConfigError(
                f"{path} is shorter than 32 bytes; delete it to make a new one"
            ) from None
        return value
    value = secrets.token_urlsafe(48).encode()
    with os.fdopen(fd, "wb") as file:
        file.write(value)
    return value
