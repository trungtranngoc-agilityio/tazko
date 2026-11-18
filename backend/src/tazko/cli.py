"""Command line. Server commands now; the client commands (`auth`, `project`,
`board`, `card`, `my`, `search`, `token`, `webhook`, `api`, `config`,
`completion`, `update`) are added in M6-04.

Exit codes (build plan): 0 success, 1 failure, 2 wrong usage, 4 not signed in.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from tazko import __version__
from tazko.core.config import ConfigError, Settings, load_settings
from tazko.core.errors import AppError
from tazko.core.logging import setup_logging
from tazko.db import MigrationError

log = logging.getLogger(__name__)


class NotYet(Exception):
    def __init__(self, command: str, task: str) -> None:
        super().__init__(f"`tazko {command}` is not implemented yet (task {task})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tazko", description="Tazko API server and command-line client"
    )
    parser.add_argument("--version", action="version", version=f"tazko {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    commands.add_parser(
        "serve", help="Run the API server (settings from TAZKO_* environment variables)."
    )

    admin = commands.add_parser(
        "admin", help="Create a person with the super admin flag, or grant it to an existing one."
    )
    admin.add_argument("--data", type=Path, help="Data folder; defaults to TAZKO_DATA_DIR.")
    admin.add_argument("--email", required=True, help="Google account email of the person.")

    backup = commands.add_parser(
        "backup", help="Copy every database (online backup API) and file folder into a snapshot."
    )
    backup.add_argument("--data", type=Path)
    backup.add_argument("--to", type=Path, required=True)
    backup.add_argument("--keep-days", type=int, default=30)

    check = commands.add_parser(
        "check", help="Open every database, run integrity_check and verify attachment hashes."
    )
    check.add_argument("--data", type=Path)
    return parser


def serve(settings: Settings) -> None:
    """Run until SIGINT/SIGTERM; uvicorn drains open requests before exiting."""
    import uvicorn  # keeps the web stack out of the other commands

    from tazko.main import create_app

    log.info("listening on %s", settings.addr)
    uvicorn.run(
        create_app(settings),
        host=str(settings.host),
        port=settings.port,
        log_config=None,  # keep the logging set up in main()
        server_header=False,
        # The access log would record query strings, such as the OAuth code on
        # /auth/google/callback. Requests that fail are logged by the app.
        access_log=False,
        # cloudflared connects from loopback, which uvicorn would trust for
        # X-Forwarded-For; the visitor's address comes from CF-Connecting-IP.
        proxy_headers=False,
    )


def grant_admin(data_dir: Path, email: str) -> None:
    """Promote one person. The data folder must exist: a shell without
    TAZKO_DATA_DIR would otherwise make a fresh ./data that the server never
    reads, and report success."""
    from tazko.db import Database
    from tazko.modules.users import service as users

    if not data_dir.is_dir():
        raise ConfigError(
            f"data folder {data_dir.resolve()} does not exist; pass --data or set "
            "TAZKO_DATA_DIR to the server's folder (production: --data /var/lib/tazko/data)"
        )
    path = (data_dir / "control.db").resolve()
    control = Database(path, "control", readers=1)
    try:
        user, created = users.grant_super_admin(control, email, actor_id=None)
    finally:
        control.close()
    state = "created as" if created else "is now"
    print(f"{user.email} {state} a super admin in {path}")
    print("They can sign in with Google and open /admin.")


def run(args: argparse.Namespace, settings: Settings) -> None:
    match args.command:
        case "serve":
            serve(settings)
        case "admin":
            grant_admin(args.data or settings.data_dir, args.email)
        case "backup":
            raise NotYet("backup", "M1-08")
        case "check":
            raise NotYet("check", "M1-08")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)  # wrong usage exits with 2
    try:
        # Only `serve` needs the Google client and public URLs (D16).
        settings = load_settings(serving=args.command == "serve")
        setup_logging(settings.log)
        run(args, settings)
    except AppError as err:
        print(f"error: {err.message}", file=sys.stderr)
        return 1
    except (ConfigError, MigrationError, NotYet) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1
    return 0
