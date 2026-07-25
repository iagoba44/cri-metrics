"""Aplicacion principal FastAPI con scheduler de ingesta."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.database import engine, Base
from app.api.v1 import router as api_v1_router
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
    version="2.5.0",
    lifespan=lifespan,
)

app.include_router(api_v1_router)

# Servir archivos estaticos (dashboard)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")
