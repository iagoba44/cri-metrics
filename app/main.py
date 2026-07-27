"""Aplicacion principal FastAPI con scheduler de ingesta."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.api.v1.routers.cri import router as router_cri
from app.api.v1.routers.tmi import router as router_tmi
from app.api.v1.routers.sources import router as router_sources
from app.api.v1.routers.simulation import router as router_simulation
from app.api.v1.routers.ai import router as router_ai
from app.api.v1.routers.ingestion import router as router_ingestion
from app.api.v1.routers.health import router as router_health
from app.api.v1.routers.algorithmic import router as router_algorithmic
from app.config import get_settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Scheduler global (se inicia en lifespan)
_scheduler = None

def _run_scheduled_ingestion():
    """Callback ejecutado por el scheduler cada hora."""
    try:
        from sqlalchemy.orm import sessionmaker
        from app.services.ingestion import IngestionPipeline
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        try:
            pipeline = IngestionPipeline(db)
            total = pipeline.run_scheduled_ingestion(use_real_sources=True)
            logging.info(f"[SCHEDULER] Ingesta automatica completada: {total} registros")
        finally:
            db.close()
    except Exception as e:
        logging.error(f"[SCHEDULER] Error en ingesta automatica: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)

    # Pre-cargar modelos pesados en thread separado (bloqueante)
    import asyncio
    from app.services.warmup import preload_models
    loop = asyncio.get_running_loop()
    preloaded_model = await loop.run_in_executor(None, preload_models)
    if preloaded_model is not None:
        from app.services.news_validator import set_preloaded_model
        set_preloaded_model(preloaded_model)

    # Iniciar scheduler
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(_run_scheduled_ingestion, 'interval', hours=1, id='ingestion_hourly', replace_existing=True)
        _scheduler.start()
        logging.info("[SCHEDULER] Ingesta automatica configurada cada 1h")
    except Exception as e:
        logging.warning(f"[SCHEDULER] No se pudo iniciar: {e}")

    logging.info("CRI Metrics System iniciado - Dashboard en /static/index.html")
    yield

    # Shutdown
    if _scheduler:
        _scheduler.shutdown()
        logging.info("[SCHEDULER] Detenido")
    logging.info("CRI Metrics System detenido")

app = FastAPI(
    title="CRI Metrics System",
    description="Sistema de KPIs para la Medicion del Riesgo de Ajuste en IA",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS para Cloud Run / publicacion
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_cri, prefix="/api/v1")
app.include_router(router_tmi, prefix="/api/v1")
app.include_router(router_sources, prefix="/api/v1")
app.include_router(router_simulation, prefix="/api/v1")
app.include_router(router_ai, prefix="/api/v1")
app.include_router(router_ingestion, prefix="/api/v1")
app.include_router(router_health, prefix="/api/v1")
app.include_router(router_algorithmic, prefix="/api/v1")

# Servir archivos estaticos (dashboard)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")
