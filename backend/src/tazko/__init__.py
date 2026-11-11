"""Tazko backend: one Python service that is the JSON/WebSocket API, the super
admin API and (from M6) the command-line client. The web app lives in
`frontend/` and is deployed on its own (docs/decisions.md D13, D14, D15).

Layers, each importing only from the ones above it:

| Package / module   | Responsibility                                                   |
|--------------------|------------------------------------------------------------------|
| `core`             | Settings, errors, logging, shared FastAPI dependencies           |
| `db`               | SQLite connections, migrations by `user_version`, tenant handles |
| `migrations`       | `control/` and `tenant/` SQL files (shipped inside the wheel)    |
| `modules/<name>`   | One feature each: router, schemas, service, repository           |
| `main`             | App factory: middleware, error handlers, module routers          |
| `cli`              | `serve`, `admin`, `backup`, `check`; later the client verbs      |

The module list and their shape are in `tazko/modules/__init__.py`.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tazko")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"
