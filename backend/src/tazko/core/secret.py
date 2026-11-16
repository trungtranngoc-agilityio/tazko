"""The server secret that signs cookies and OAuth state.

`TAZKO_SECRET` wins. Without it, a random secret is kept in `<data>/secret`
with mode 600, made once on first start, so restarts keep sessions valid.

The file appears complete or not at all: it is written to a private temporary
file and then hard-linked into place, so a second process starting at the same
moment, or a crash half way, never sees an empty or partial secret.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import stat
import tempfile
from pathlib import Path

from tazko.core.config import ConfigError, Settings

FILE_NAME = "secret"
MIN_LENGTH = 32


def load_secret(settings: Settings) -> bytes:
    configured = settings.secret.get_secret_value()
    if configured:
        return configured.encode()
    settings.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = settings.data_dir / FILE_NAME
    if not path.exists():
        _create(path)
    return _read(path)


def _create(path: Path) -> None:
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".secret-")  # mode 600
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(secrets.token_urlsafe(48).encode())
            file.flush()
            os.fsync(file.fileno())
        # Fails if another process won the race; its secret is the one used.
        with contextlib.suppress(FileExistsError):
            os.link(temp, path)
    finally:
        os.unlink(temp)


def _read(path: Path) -> bytes:
    info = path.stat()
    if os.name != "nt" and stat.S_IMODE(info.st_mode) & 0o077:
        raise ConfigError(
            f"{path} can be read by other users; run `chmod 600 {path}` "
            "(and rotate it if it may have been copied)"
        )
    value = path.read_bytes().strip()
    if len(value) < MIN_LENGTH:
        raise ConfigError(f"{path} is shorter than {MIN_LENGTH} bytes; delete it to make a new one")
    return value
