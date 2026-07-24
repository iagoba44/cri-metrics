"""Endpoints de la API v1 con panel de fuentes en tiempo real."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
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
from app.models import RiskIndex, TelemetryRecord
from datetime import datetime

router = APIRouter(prefix="/api/v1")

@router.post("/calculate-cri", response_model=CalculateCRIResponse)
def calculate_cri(db: Session = Depends(get_db)):
    """
    Dispara el proceso de normalizacion de telemetria pendiente
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
    Ingesta manual de datos de telemetria.
    Util para testing y backfills.
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
    """Verificacion de salud del servicio."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
    )

@router.get("/latest-cri", response_model=RiskIndexSchema)
def get_latest_cri(db: Session = Depends(get_db)):
    """Obtiene el calculo CRI mas reciente."""
    latest = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No hay calculos CRI disponibles")

    return RiskIndexSchema(
        index_id=str(latest.index_id),
        timestamp=latest.timestamp,
        cri_score=latest.cri_score,
        risk_zone=latest.risk_zone,
        alerts_triggered=latest.alerts_triggered == "true",
        component_scores=None,
    )

@router.get("/sources")
def get_sources_status(db: Session = Depends(get_db)):
    """
    Panel en tiempo real: estado de cada fuente de datos
    y ultimo delta recuperado.
    """
    now = datetime.utcnow()
    
    # Para cada KPI, obtener el registro mas reciente
    kpis = ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]
    sources_data = []
    
    for kpi in kpis:
        latest = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.kpi_code == kpi)
            .order_by(TelemetryRecord.timestamp.desc())
            .first()
        )
        
        if latest:
            delta_seconds = (now - latest.timestamp).total_seconds() if latest.timestamp else 999999
            sources_data.append({
                "kpi": kpi,
                "raw_value": float(latest.raw_value),
                "normalized_score": float(latest.normalized_score) if latest.normalized_score else None,
                "data_source": latest.data_source,
                "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
                "delta_seconds": round(delta_seconds, 1),
                "freshness": latest.freshness_flag,
                "status": "ACTIVE" if delta_seconds < 3600 else "STALE",
            })
        else:
            sources_data.append({
                "kpi": kpi,
                "raw_value": None,
                "normalized_score": None,
                "data_source": "N/A",
                "timestamp": None,
                "delta_seconds": None,
                "freshness": "MISSING",
                "status": "OFFLINE",
            })
    
    return {
        "status": "success",
        "timestamp": now.isoformat(),
        "total_kpis": len(kpis),
        "active_kpis": sum(1 for s in sources_data if s["status"] == "ACTIVE"),
        "stale_kpis": sum(1 for s in sources_data if s["status"] == "STALE"),
        "offline_kpis": sum(1 for s in sources_data if s["status"] == "OFFLINE"),
        "sources": sources_data,
    }

@router.get("/explanations")
def get_kpi_explanations():
    """
    Devuelve la explicacion detallada de cada KPI y metrica.
    """
    explanations = {
        "cri_score": {
            "name": "Composite Risk Index (CRI)",
            "description": "Indice compuesto de riesgo de ajuste en el mercado de infraestructura de Inteligencia Artificial. Varia de 0 (minimo riesgo) a 100 (maximo riesgo).",
            "formula": "CRI = GSPI*0.25 + SHPD*0.15 + LTCR*0.20 + CFBR*0.20 + UOR*0.20",
            "zones": {
                "LOW": {"range": "0-30", "meaning": "Mercado estable. Precios y capacidad en equilibrio."},
                "MODERATE": {"range": "31-65", "meaning": "Presion en precios detectada. Monitorizar de cerca."},
                "CRITICAL": {"range": "66-100", "meaning": "Sobreoferta o compresion extrema. Alerta automatica activada."},
            },
            "update_frequency": "Cada vez que se invoca POST /calculate-cri o por scheduler",
        },
        "GSPI": {
            "name": "GPU Spot Price Index",
            "description": "Indice de deflacion de precios spot GPU en marketplaces (Vast.ai). Mide cuanto han caido los precios por hora de GPU frente a un baseline historico.",
            "baseline": "$2.00/hora para GPU high-end (A100, H100, RTX 4090)",
            "unit": "% deflacion (0-100)",
            "source": "Vast.ai API publica",
            "formula": "((baseline - avg_price) / baseline) * 100",
            "interpretation": {
                "0%": "Precios normales. Sin deflacion.",
                "50%": "Precios caidos a la mitad. Sobreoferta moderada.",
                "80%": "Deflacion extrema. Mercado inundado de GPU.",
                "100%": "Colapso total. Precios proximos a cero.",
            },
            "weight": "0.25 (25% del CRI)",
            "update_frequency": "Tiempo real (on-demand) o cada 1-6 horas",
        },
        "SHPD": {
            "name": "Server Hardware Price Deflation",
            "description": "Deflacion en precios de hardware servidor y GPU cloud. Combina rentabilidad minera (WhatToMine) con precios cloud oficiales (Lambda Labs).",
            "baseline": "Rentabilidad minera = 1000% (WhatToMine); Precio cloud = $3.50/h (Lambda Labs)",
            "unit": "% deflacion (0-100)",
            "sources": "WhatToMine (scraper) + Lambda Labs (scraper)",
            "formula": "Combinacion ponderada de: (1 - rentabilidad_actual/rentabilidad_baseline) * 100 + (1 - precio_cloud_actual/precio_baseline) * 100",
            "interpretation": {
                "0%": "Precios hardware estables. Demanda saludable.",
                "50%": "Presion a la baja. Menor demanda de hardware.",
                "90%": "Colapso de demanda. Rentabilidad minera caida drastica.",
                "100%": "Mercado hardware en crisis total.",
            },
            "weight": "0.15 (15% del CRI)",
            "update_frequency": "Tiempo real (on-demand) o cada 6-24 horas",
        },
        "LTCR": {
            "name": "Long-Term Contract Ratio",
            "description": "Proxy de compresion/extincion de contratos a largo plazo en infraestructura IA. Usa volatilidad de acciones de empresas clave (NVDA, SMCI, DELL, AMD, INTC) como indicador de confianza del mercado en contratos futuros.",
            "companies": "NVIDIA (NVDA), Supermicro (SMCI), Dell (DELL), AMD (AMD), Intel (INTC)",
            "unit": "Indice 0-100 (volatilidad escalada)",
            "source": "Yahoo Finance API publica",
            "formula": "(volatilidad_absoluta_promedio / 10%) * 100",
            "interpretation": {
                "0%": "Mercado estable. Confianza total en contratos IA.",
                "30%": "Inestabilidad moderada. Reevaluacion de contratos.",
                "60%": "Volatilidad alta. Riesgo de cancelaciones.",
                "100%": "Crisis de confianza. Contratos a largo plazo en peligro.",
            },
            "weight": "0.20 (20% del CRI)",
            "update_frequency": "Tiempo real (on-demand) o cada 1-4 horas",
        },
        "CFBR": {
            "name": "Cloud Free-Burn Rate",
            "description": "Tasa de quema/distress de capital operativo en neoclouds. Usa volatilidad del mercado crypto (ETH, BTC) como proxy: las empresas de infra IA dependen de la demanda de computo para crypto e IA.",
            "unit": "% volatilidad escalada (0-100)",
            "sources": "CoinGecko API + Binance API (ambas publicas)",
            "formula": "max(abs(ETH_change_24h) * 5, abs(BTC_change_24h) * 3, market_cap_change * 2)",
            "interpretation": {
                "0%": "Mercado crypto estable. Capital operativo seguro.",
                "20%": "Volatilidad moderada. Presion en margenes.",
                "50%": "Alta volatilidad. Quema de capital significativa.",
                "100%": "Distress extremo. Posible quiebra de neoclouds.",
            },
            "weight": "0.20 (20% del CRI)",
            "update_frequency": "Tiempo real (on-demand) o cada 15-60 minutos",
        },
        "UOR": {
            "name": "Underutilization / Overcapacity Ratio",
            "description": "Ratio de infrautilizacion y sobreoferta de capacidad GPU. Mide el porcentaje de GPUs disponibles en marketplaces que no estan siendo alquiladas (proxy de demanda real).",
            "unit": "% infrautilizacion (0-100)",
            "source": "Vast.ai API publica (estado de rentabilidad/occupancy)",
            "formula": "((total_gpus_rentable - total_gpus_rented) / total_gpus_rentable) * 100",
            "interpretation": {
                "0%": "Capacidad totalmente utilizada. Mercado ajustado.",
                "30%": "Sobreoferta leve. Algunas GPUs sin alquilar.",
                "60%": "Sobreoferta significativa. Presion en precios.",
                "100%": "Infrautilizacion total. Colapso de demanda.",
            },
            "weight": "0.20 (20% del CRI)",
            "update_frequency": "Tiempo real (on-demand) o cada 1-6 horas",
        },
    }
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "explanations": explanations,
    }
