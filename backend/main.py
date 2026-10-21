from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.core.config import get_settings
from backend.db.base import Base
from backend.db.session import engine
from backend.services.classifier import load_model

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        load_model()
        Base.metadata.create_all(bind=engine)
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Workplace harassment reporting with ticket-based follow-up and administrator review.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-Admin-Token"],
)

app.include_router(router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": f"{settings.app_name} API is running.",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
    }
