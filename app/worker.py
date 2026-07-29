"""Celery worker para ejecutar tareas pesadas en background."""
from celery import Celery
from celery.schedules import crontab
from app.config import get_settings
from sqlalchemy.orm import sessionmaker
from app.database import engine

settings = get_settings()

celery_app = Celery(
    "cri_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.timezone = "UTC"

@celery_app.task(name="tasks.run_ingestion")
def run_ingestion():
    """Ejecuta la ingesta periódica de telemetría y cálculos del índice."""
    from app.services.ingestion import IngestionPipeline
    from app.services.calculator import CRICalculator
    from app.services.alerts import get_alert_service
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        pipeline = IngestionPipeline(db)
        total = pipeline.run_scheduled_ingestion(use_real_sources=True)
        
        # Calcular CRI y disparar alertas
        calculator = CRICalculator(db)
        risk_index, metadata = calculator.calculate()
        
        # Enviar alertas
        get_alert_service().check_and_alert(risk_index.cri_score)
        
        return {
            "status": "success", 
            "records_ingested": total, 
            "cri_score": float(risk_index.cri_score)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

# Configurar la tarea periódica (cada 1h)
celery_app.conf.beat_schedule = {
    "hourly-ingestion": {
        "task": "tasks.run_ingestion",
        "schedule": crontab(minute=0),  # ejecuta cada hora en punto
    }
}
