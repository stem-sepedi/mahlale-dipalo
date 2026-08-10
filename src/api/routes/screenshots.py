"""Screenshot API routes — /screenshots/health, /screenshots/capture."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.screenshot import ScreenshotService, ScreenshotError

router = APIRouter(prefix="/screenshots", tags=["screenshots"])

_service: ScreenshotService | None = None


def get_service() -> ScreenshotService:
    global _service
    if _service is None:
        _service = ScreenshotService()
    return _service


class CaptureRequest(BaseModel):
    url: str
    full_page: bool = True


@router.get("/health")
async def screenshot_health():
    svc = get_service()
    return {"status": "ok" if svc.is_ready else "not_started", "browser": "chromium"}


@router.post("/capture")
async def screenshot_capture(req: CaptureRequest):
    svc = get_service()
    if not svc.is_ready:
        await svc.start()
    try:
        result = await svc.capture_url(req.url, full_page=req.full_page)
        return {"path": result["path"]}
    except ScreenshotError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
