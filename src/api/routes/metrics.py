"""Prometheus-format metrics endpoint — /metrics."""

import time
from fastapi import APIRouter, Response

from src.config import settings

router = APIRouter(tags=["metrics"])

_start_time = time.time()


@router.get("/metrics")
async def metrics():
    """Return Prometheus-format metrics."""
    uptime = time.time() - _start_time
    lines = [
        "# HELP polelo_uptime_seconds Application uptime in seconds",
        "# TYPE polelo_uptime_seconds gauge",
        f"polelo_uptime_seconds {uptime:.1f}",
        "# HELP polelo_info Application info",
        "# TYPE polelo_info gauge",
        f'polelo_info{{version="{settings.APP_VERSION}"}} 1',
    ]
    return Response(content="\n".join(lines) + "\n", media_type="text/plain")
