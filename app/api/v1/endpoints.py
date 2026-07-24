"""Endpoints de la API v1."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    CalculateCRIResponse,
    RiskIndexSchema,
    IngestRequest,
    IngestResponse,
    HealthResponse,
)
from app.services.calculator import CRICalculator
from app.services.ingestion import IngestionPipeline
from app.models import RiskIndex
from datetime import datetime

router = APIRouter(prefix="/api/v1")

@router.post("/calculate-cri", response_model=CalculateCRIResponse)
def calculate_cri(db: Session = Depends(get_db)):
    """
    Dispara el proceso de normalización de telemetría pendiente
    y genera un nuevo registro CRI.
    """
    try:
        calculator = CRICalculator(db)
        risk_index, metadata = calculator.calculate()

        return CalculateCRIResponse(
            status="success",
            data=RiskIndexSchema(
                index_id=str(risk_index.index_id),
                timestamp=risk_index.timestamp,
                cri_score=risk_index.cri_score,
                risk_zone=risk_index.risk_zone,
                alerts_triggered=risk_index.alerts_triggered == "true",
                component_scores=metadata.get("component_details"),
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/ingest", response_model=IngestResponse)
def ingest_data(payload: IngestRequest, db: Session = Depends(get_db)):
    """
    Ingesta manual de datos de telemetría.
    Útil para testing y backfills.
    """
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
    """
    Ejecuta la ingesta programada desde fuentes externas.
    
    Args:
        use_real: True = Vast.ai, CoinGecko, WhatToMine, Yahoo Finance.
                  False = simuladores (para testing).
    """
    pipeline = IngestionPipeline(db)
    total = pipeline.run_scheduled_ingestion(use_real_sources=use_real)
    source_type = "reales" if use_real else "simulados"
    return IngestResponse(
        status="success",
        inserted=total,
        message=f"Ingesta completada: {total} registros desde fuentes {source_type}",
    )

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Verificación de salud del servicio."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
    )

@router.get("/latest-cri", response_model=RiskIndexSchema)
def get_latest_cri(db: Session = Depends(get_db)):
    """Obtiene el cálculo CRI más reciente."""
    latest = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No hay cálculos CRI disponibles")

    return RiskIndexSchema(
        index_id=str(latest.index_id),
        timestamp=latest.timestamp,
        cri_score=latest.cri_score,
        risk_zone=latest.risk_zone,
        alerts_triggered=latest.alerts_triggered == "true",
        component_scores=None,
    )
