"""App factory: middleware, error handlers and the module routers.

API only: the web app is deployed separately (D13) and calls this server
cross-origin with credentials. Listens on loopback only; TLS and the public
hostname belong to the tunnel.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tazko import __version__
from tazko.core import errors
from tazko.core.config import Settings, load_settings
from tazko.core.deps import require_same_origin
from tazko.core.secret import load_secret
from tazko.db import Database
from tazko.db.tenant import Tenants
from tazko.modules import auth, health
from tazko.modules.auth.google import GoogleProvider
from tazko.modules.invites import router as invites_router
from tazko.modules.orgs import router as orgs_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open control.db (migrating it) before the first request; company files
    open on first use. Everything is closed after the last request."""
    settings: Settings = app.state.settings
    # Private to the service user: company data, sessions and the secret live here.
    settings.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    app.state.secret = load_secret(settings)
    app.state.control = Database(settings.data_dir / "control.db", "control", readers=4)
    app.state.tenants = Tenants(settings.data_dir)
    try:
        yield
    finally:
        app.state.tenants.close()
        app.state.control.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    # The internal API is not published: no docs pages and no /openapi.json.
    # The public document arrives with /api/v1 (M6-01).
    app = FastAPI(
        title="Tazko",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
        # Every write route checks Origin, including routes added later (M1-05).
        dependencies=[Depends(require_same_origin)],
    )
    app.state.settings = settings
    app.state.identity_provider = GoogleProvider(
        settings.google_client_id, settings.google_client_secret.get_secret_value()
    )
    # TODO(M3-01): realtime hub.

    # CORS for exactly one origin, with cookies. Other origins get no CORS
    # headers at all. CORS only tells browsers what they may read; the server
    # still checks Origin on every write (the app dependency above).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["content-type"],
    )
    errors.install(app)

    app.include_router(health.router)
    app.include_router(auth.router)  # /auth/... and /api/me
    # Imported as modules: core/deps.py imports the orgs service, so the orgs
    # package cannot import its router when it is first loaded.
    app.include_router(orgs_router.router)  # /api/orgs, members
    app.include_router(invites_router.router)  # /api/orgs/{slug}/invites
    # Module routers are included here as milestones land:
    # app.include_router(admin.router, prefix="/admin/api")        M1-06
    # app.include_router(realtime.router, prefix="/ws")            M3-01
    # app.include_router(public_api.router, prefix="/api/v1")      M6-01
    return app
