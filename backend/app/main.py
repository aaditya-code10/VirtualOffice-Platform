"""FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import text
from app.api import api_router
from app.config import settings
from app.database import SessionLocal, engine
from app.models import Base
from app.schemas import SystemStatus
from app.services import llm
from app.services.seed import bootstrap

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("app")

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Alembic owns the schema in production; create_all keeps local/dev and the
    # test suite working without a migration step.
    Base.metadata.create_all(bind=engine)

    # Ensure backward-compatible columns exist on existing databases
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE work_orders ADD COLUMN document_id VARCHAR(40)"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE work_orders ADD COLUMN category VARCHAR(80)"))
            conn.commit()
        except Exception:
            pass

    db = SessionLocal()
    try:
        bootstrap(db)
    finally:
        db.close()

    logger.info(
        "%s v%s ready | db=%s | engine=%s",
        settings.app_name,
        VERSION,
        engine.url.get_backend_name(),
        "gemini:" + settings.llm_model if llm.is_available() else "deterministic",
    )
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    version=VERSION,
    description=(
        "Backend for an AI digital workforce: multi-agent orchestration over a "
        "company's own documents and metrics, with human approval gates."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "ai-virtual-office-api", "version": VERSION}


@app.get("/api/system/status", response_model=SystemStatus, tags=["system"])
def system_status() -> SystemStatus:
    """What the running instance is actually configured with."""
    available = llm.is_available()
    return SystemStatus(
        status="ok",
        version=VERSION,
        environment=settings.environment,
        database=engine.url.get_backend_name(),
        llm_enabled=available,
        llm_model=settings.llm_model if available else None,
        engine="gemini" if available else "deterministic",
    )
