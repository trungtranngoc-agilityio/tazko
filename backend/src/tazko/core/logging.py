"""One logging setup for the server and the CLI. Logs go to stderr; under
systemd they end up in the journal."""

from __future__ import annotations

import logging

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format=FORMAT, force=True)
