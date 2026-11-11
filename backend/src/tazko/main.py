"""App factory: middleware, error handlers and the module routers.

API only: the web app is deployed separately (D13) and calls this server
cross-origin with credentials. Listens on loopback only; TLS and the public
hostname belong to the tunnel.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tazko import __version__
from tazko.core import errors
from tazko.core.config import Settings, load_settings
from tazko.modules import health


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    # Interactive docs stay off; the public OpenAPI document arrives with /api/v1 (M6-01).
    app = FastAPI(title="Tazko", version=__version__, docs_url=None, redoc_url=None)
    app.state.settings = settings
    # TODO(M1-03): open control.db and the per-company tenant cache in a lifespan handler.
    # TODO(M3-01): realtime hub.

    # CORS for exactly one origin, with cookies. Other origins get no CORS
    # headers at all. CORS only tells browsers what they may read; the server
    # still checks Origin on every write (M1-05).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["content-type"],
    )
    errors.install(app)

    app.include_router(health.router)
    # Module routers are included here as milestones land:
    # app.include_router(auth.router, prefix="/auth")              M1-04
    # app.include_router(admin.router, prefix="/admin/api")        M1-06
    # app.include_router(realtime.router, prefix="/ws")            M3-01
    # app.include_router(public_api.router, prefix="/api/v1")      M6-01
    return app
