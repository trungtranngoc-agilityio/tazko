"""FastAPI dependencies shared by every module. Routers ask for what they need
through these annotations instead of reaching into `request.app.state`.

Database work blocks, so routes that use ControlDep are plain
`def` routes (FastAPI runs them in its thread pool), never `async def`.

TODO(M1-04): CurrentUser (session cookie), CompanyDep (open_company for the path's
slug), RequireOrigin (write guard).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from tazko.core.config import Settings
from tazko.db import Database


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_control(request: Request) -> Database:
    control: Database = request.app.state.control
    return control


SettingsDep = Annotated[Settings, Depends(get_settings)]
ControlDep = Annotated[Database, Depends(get_control)]
# There is deliberately no dependency for the company cache: a route reaches a company only through
# CompanyDep (M1-04), which calls tazko.modules.orgs.service.open_company with
# the signed-in person. tests/unit/test_architecture.py guards this.
