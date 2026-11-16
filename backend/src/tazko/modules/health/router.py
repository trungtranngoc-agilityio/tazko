from fastapi import APIRouter

from tazko import __version__
from tazko.core.deps import ControlDep
from tazko.modules.health.schemas import Health

router = APIRouter(tags=["health"])


@router.get("/health")
def health(control: ControlDep) -> Health:
    # A failing read becomes the generic 500, so the release health check fails
    # without the response naming any path.
    control.read(lambda c: c.execute("SELECT 1").fetchone())
    return Health(status="ok", version=__version__)
