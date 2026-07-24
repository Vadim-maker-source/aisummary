from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, dashboard, events, health, imports, scenarios
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Agent Analytics API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for api_router in (
    health.router,
    events.router,
    imports.router,
    analysis.router,
    dashboard.router,
    scenarios.router,
):
    app.include_router(api_router, prefix="/api/v1")
