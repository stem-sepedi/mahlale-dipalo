"""Async Playwright screenshot service for Polelo."""

import asyncio
import logging
import time
from pathlib import Path

from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


class ScreenshotError(Exception):
    """Raised when screenshot capture fails after all retries."""


class ScreenshotService:
    """Manages a long-lived headless Chromium instance for screenshot capture.

    Usage:
        svc = ScreenshotService()
        await svc.start()
        png_bytes = await svc.capture_url("https://example.com")
        await svc.stop()
    """

    def __init__(self, viewport_width: int = 1280, viewport_height: int = 720):
        self._viewport_width = viewport_width
        self._viewport_height = viewport_height
        self._playwright = None
        self._browser: Browser | None = None

    @property
    def is_ready(self) -> bool:
        return self._browser is not None and self._browser.is_connected

    async def start(self) -> None:
        """Launch headless Chromium."""
        if self.is_ready:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        logger.info("Playwright Chromium launched")

    async def stop(self) -> None:
        """Shut down browser and Playwright."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Playwright Chromium stopped")

    async def capture_url(
        self,
        url: str,
        *,
        output_path: str | None = None,
        full_page: bool = True,
        attempts: int = 3,
    ) -> dict:
        """Navigate to *url* and return PNG bytes + metadata.

        Retries up to *attempts* times on transient failures.
        Returns {"png": bytes, "path": str, "width": int, "height": int}.
        """
        if not self.is_ready:
            raise ScreenshotError("Service not started — call start() first")

        last_exc: Exception | None = None
        for attempt in range(1, attempts + 1):
            page: Page | None = None
            try:
                page = await self._browser.new_page(  # type: ignore[union-attr]
                    viewport={"width": self._viewport_width, "height": self._viewport_height},
                )
                response = await page.goto(url, wait_until="networkidle", timeout=30_000)
                if response and response.status == 204:
                    raise ScreenshotError("empty_response")

                png = await page.screenshot(full_page=full_page, type="png")

                save_to = Path(output_path) if output_path else SCREENSHOT_DIR / f"{int(time.time())}.png"
                save_to.parent.mkdir(parents=True, exist_ok=True)
                save_to.write_bytes(png)

                return {"png": png, "path": str(save_to)}
            except ScreenshotError:
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning("attempt %d/%d failed for %s: %s", attempt, attempts, url, exc)
            finally:
                if page:
                    await page.close()

        raise ScreenshotError(f"Failed after {attempts} attempts: {last_exc}")
