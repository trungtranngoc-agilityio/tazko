"""FastAPI dependencies shared by every module. Routers ask for what they need
through these annotations instead of reaching into `request.app.state`.

TODO(M1-03): ControlDb, TenantDb (the caller's company database).
TODO(M1-04): CurrentUser (session cookie), RequireOrigin (write guard).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from tazko.core.config import Settings


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


SettingsDep = Annotated[Settings, Depends(get_settings)]
