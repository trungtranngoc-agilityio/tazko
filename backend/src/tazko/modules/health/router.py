from fastapi import APIRouter

from tazko import __version__
from tazko.modules.health.schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> Health:
    # TODO(M1-03): also report whether control.db opens, without leaking paths.
    return Health(status="ok", version=__version__)
