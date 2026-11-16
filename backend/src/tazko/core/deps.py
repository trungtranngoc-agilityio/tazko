"""FastAPI dependencies shared by every module. Routers ask for what they need
through these annotations instead of reaching into `request.app.state`.

Database work blocks, so routes that use ControlDep or TenantsDep are plain
`def` routes (FastAPI runs them in its thread pool), never `async def`.

TODO(M1-04): CurrentUser (session cookie), RequireOrigin (write guard).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from tazko.core.config import Settings
from tazko.db import Database
from tazko.db.tenant import Tenants


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_control(request: Request) -> Database:
    control: Database = request.app.state.control
    return control


def get_tenants(request: Request) -> Tenants:
    tenants: Tenants = request.app.state.tenants
    return tenants


SettingsDep = Annotated[Settings, Depends(get_settings)]
ControlDep = Annotated[Database, Depends(get_control)]
# Only through tazko.modules.orgs.service.open_company, which checks membership.
TenantsDep = Annotated[Tenants, Depends(get_tenants)]
