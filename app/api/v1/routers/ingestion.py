from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import IngestRequest, IngestResponse
from app.services.ingestion import IngestionPipeline

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest_data(payload: IngestRequest, db: Session = Depends(get_db)):
    pipeline = IngestionPipeline(db)
    inserted = pipeline.ingest_batch(payload.records)
    return IngestResponse(
        status="success",
        inserted=inserted,
        message=f"{inserted} registros ingestados correctamente",
    )


@router.post("/run-ingestion", response_model=IngestResponse)
def run_scheduled_ingestion(
    background_tasks: BackgroundTasks,
    use_real: bool = True,
    db: Session = Depends(get_db)
):
    pipeline = IngestionPipeline(db)
    total = pipeline.run_scheduled_ingestion(use_real_sources=use_real)
    source_type = "reales" if use_real else "simulados"
    return IngestResponse(
        status="success",
        inserted=total,
        message=f"Ingesta completada: {total} registros desde fuentes {source_type}",
    )


@router.post("/backfill")
def run_backfill(db: Session = Depends(get_db)):
    try:
        from app.services.backfill import HistoricalBackfill
        pipeline = HistoricalBackfill(db)
        results = pipeline.run_full()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en backfill: {str(e)}")


@router.post("/enhanced-backfill")
def run_enhanced_backfill(db: Session = Depends(get_db)):
    """Genera 6 meses de datos sinteticos realistas con eventos de mercado."""
    try:
        from app.services.enhanced_backfill import EnhancedBackfill
        pipeline = EnhancedBackfill(db)
        results = pipeline.generate()
        return {"status": "success", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
