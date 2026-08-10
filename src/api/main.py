"""FastAPI application factory for Polelo STEM Sepedi Translation Layer."""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes.admin import router as admin_router
from src.api.routes.archive import router as archive_router
from src.api.routes.auth import router as auth_router
from src.api.routes.concepts import router as concepts_router
from src.api.routes.embed import router as embed_router
from src.api.routes.explanations import router as explanations_router
from src.api.routes.metrics import router as metrics_router
from src.api.routes.moderation import router as moderation_router
from src.api.routes.moodle import router as moodle_router
from src.api.routes.moodle_webhooks import router as moodle_webhooks_router
from src.api.routes.questions import router as questions_router
from src.api.routes.queue import router as queue_router
from src.api.routes.quiz import router as quiz_router
from src.api.routes.reviews import router as reviews_router
from src.api.routes.screenshots import router as screenshots_router
from src.api.routes.search import router as search_router
from src.api.routes.translations import router as translations_router
from src.api.routes.users import router as users_router
from src.api.routes.versions import router as versions_router
from src.config import settings
from src.middleware.logging import RequestIDMiddleware, setup_logging
from src.middleware.rate_limit import RateLimitMiddleware
from src.web.widgets import WIDGETS_DIR

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="STEM Sepedi Translation Layer",
)

app.state.start_time = time.time()

# Middleware (order matters: outermost first)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIDMiddleware)

# Routes
app.include_router(auth_router)
app.include_router(concepts_router)
app.include_router(translations_router)
app.include_router(explanations_router)
app.include_router(quiz_router)
app.include_router(reviews_router)
app.include_router(versions_router)
app.include_router(moderation_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(queue_router)
app.include_router(archive_router)
app.include_router(search_router)
app.include_router(screenshots_router)
app.include_router(metrics_router)
app.include_router(moodle_router)
app.include_router(moodle_webhooks_router)
app.include_router(questions_router)
app.include_router(embed_router)

# Static widget assets (/widgets/translation-widget.js etc.)
app.mount("/widgets", StaticFiles(directory=WIDGETS_DIR), name="widgets")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "uptime_seconds": int(time.time() - app.state.start_time),
    }


def create_app() -> FastAPI:
    return app
