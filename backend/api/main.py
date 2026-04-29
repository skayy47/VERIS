from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import bench as bench_route
from api.routes import health, metrics, prometheus, research
from ops.otel import init_tracer
from utils.config import get_settings
from utils.helpers import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_tracer(endpoint=settings.otel_exporter_endpoint)  # also calls _init_prometheus

    try:
        from orchestrator.memory.episodic import EpisodicMemory

        episodic = EpisodicMemory(dsn=settings.database_url)
        await episodic.init()
        app.state.episodic = episodic
    except Exception as exc:
        logger.warning("EpisodicMemory unavailable (non-fatal): %s", exc)
        app.state.episodic = None

    try:
        from orchestrator.memory.semantic import SemanticMemory

        semantic = SemanticMemory(dsn=settings.database_url)
        await semantic.init()
        app.state.semantic = semantic
    except Exception as exc:
        logger.warning("SemanticMemory unavailable (non-fatal): %s", exc)
        app.state.semantic = None

    logger.info("VERIS backend ready")
    yield

    if getattr(app.state, "episodic", None):
        await app.state.episodic.close()
    if getattr(app.state, "semantic", None):
        await app.state.semantic.close()
    logger.info("VERIS backend shut down")


app = FastAPI(
    title="VERIS",
    version="0.1.0",
    description="Production Research Agent",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(prometheus.router)          # GET /metrics — no prefix, for Prometheus scrape
app.include_router(research.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(bench_route.router, prefix="/api")
