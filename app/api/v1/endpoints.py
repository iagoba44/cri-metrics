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
from app.scenarios import get_mode_state, SCENARIOS, get_scenario_list, get_zone
from app.services.alerts import get_alert_service
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/api/v1")

@router.post("/calculate-cri", response_model=CalculateCRIResponse)
def calculate_cri(db: Session = Depends(get_db)):
    """
    Dispara el proceso de normalizacion de telemetria pendiente
    y genera un nuevo registro CRI.
    
    Si el sistema esta en modo SIMULATION, usa los datos del escenario activo.
    Si esta en modo REAL, usa datos reales del mercado.
    """
    mode_state = get_mode_state()
    
    try:
        if mode_state.mode == mode_state.MODE_SIMULATION and mode_state.active_scenario:
            # Modo simulacion: usar escenario predefinido
            scenario = SCENARIOS[mode_state.active_scenario]
            params = scenario["params"]
            
            # Calcular CRI manualmente
            weights = {"GSPI": 0.25, "SHPD": 0.15, "LTCR": 0.20, "CFBR": 0.20, "UOR": 0.20}
            cri_score = round(sum(params[k] * weights[k] for k in weights), 2)
            risk_zone = get_zone(cri_score)
            alerts_triggered = risk_zone == "CRITICAL"
            
            # Construir component_scores como espera el frontend
            component_details = {}
            colors = {"GSPI": "#f85149", "SHPD": "#d29922", "LTCR": "#58a6ff", "CFBR": "#a371f7", "UOR": "#3fb950"}
            for kpi, raw_val in params.items():
                component_details[kpi] = {
                    "normalized_score": raw_val,
                    "raw_value": raw_val,
                    "weight": weights[kpi],
                    "color": colors.get(kpi),
                }
            
            # Guardar en DB para historial
            risk_index = RiskIndex(
                cri_score=cri_score,
                risk_zone=risk_zone,
                alerts_triggered="true" if alerts_triggered else "false",
                timestamp=datetime.now(timezone.utc),
            )
            db.add(risk_index)
            db.commit()
            db.refresh(risk_index)
            
            return CalculateCRIResponse(
                status="success",
                data=RiskIndexSchema(
                    index_id=str(risk_index.index_id),
                    timestamp=risk_index.timestamp,
                    cri_score=cri_score,
                    risk_zone=risk_zone,
                    alerts_triggered=alerts_triggered,
                    component_scores=component_details,
                ),
            )
        else:
            # Modo real: calculo normal
            calculator = CRICalculator(db)
            risk_index, metadata = calculator.calculate()

            # Alertas
            alerts = get_alert_service().check_and_alert(risk_index.cri_score)
            
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
        timestamp=datetime.now(timezone.utc),
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
    
    Si el sistema esta en modo SIMULATION, muestra los parametros
    del escenario activo como fuentes 'SIMULATED'.
    """
    mode_state = get_mode_state()
    now = datetime.now(timezone.utc)
    
    # Si esta en modo SIMULATION, generar datos del escenario
    if mode_state.mode == mode_state.MODE_SIMULATION and mode_state.active_scenario:
        scenario = SCENARIOS[mode_state.active_scenario]
        params = scenario["params"]
        
        sources_data = []
        for kpi, raw_val in params.items():
            sources_data.append({
                "kpi": kpi,
                "raw_value": raw_val,
                "normalized_score": raw_val,
                "data_source": f"SIMULATION({scenario['id']})",
                "timestamp": now.isoformat(),
                "delta_seconds": 0.0,
                "freshness": "SIMULATED",
                "status": "SIMULATED",
            })
        
        return {
            "status": "success",
            "mode": "SIMULATION",
            "scenario": scenario["name"],
            "timestamp": now.isoformat(),
            "total_kpis": len(sources_data),
            "active_kpis": 0,
            "stale_kpis": 0,
            "offline_kpis": 0,
            "simulated_kpis": len(sources_data),
            "sources": sources_data,
        }
    
    # Modo REAL: obtener datos de la DB
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
            ts = latest.timestamp
            if ts:
                # SQLite devuelve naive; now es aware. Hacemos compatible.
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                delta_seconds = (now - ts).total_seconds()
            else:
                delta_seconds = 999999
            sources_data.append({
                "kpi": kpi,
                "raw_value": float(latest.raw_value),
                "normalized_score": float(latest.normalized_score) if latest.normalized_score else None,
                "data_source": latest.data_source,
                "timestamp": ts.isoformat() if ts else None,
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
        "mode": "REAL",
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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "explanations": explanations,
    }

@router.post("/simulate-critical")
def simulate_critical(db: Session = Depends(get_db)):
    """
    DEPRECATED: Usar /simulate-scenario con id='supply_crisis' o 'crypto_crash'.
    Mantiene compatibilidad hacia atras.
    """
    mode_state = get_mode_state()
    mode_state.set_scenario("supply_crisis")
    
    # Forzar calculo con escenario
    return calculate_cri(db)


@router.get("/mode")
def get_mode():
    """
    Obtiene el estado actual del modo (REAL vs SIMULATION)
    y el escenario activo si aplica.
    """
    mode_state = get_mode_state()
    return {
        "status": "success",
        **mode_state.get_status(),
    }

@router.post("/mode")
def set_mode(payload: dict):
    """
    Cambia el modo del sistema.
    
    Payload: {"mode": "REAL" | "SIMULATION", "scenario_id": "optional"}
    """
    mode_state = get_mode_state()
    new_mode = payload.get("mode", "REAL")
    scenario_id = payload.get("scenario_id")
    
    if new_mode not in (mode_state.MODE_REAL, mode_state.MODE_SIMULATION):
        raise HTTPException(status_code=400, detail="Modo debe ser REAL o SIMULATION")
    
    mode_state.set_mode(new_mode)
    
    if scenario_id and new_mode == mode_state.MODE_SIMULATION:
        if scenario_id not in SCENARIOS:
            raise HTTPException(status_code=400, detail=f"Escenario invalido: {scenario_id}")
        mode_state.set_scenario(scenario_id)
    
    return {
        "status": "success",
        "message": f"Modo cambiado a {new_mode}",
        **mode_state.get_status(),
    }

@router.get("/source-weights")
def get_source_weights():
    """
    Retorna los pesos actuales de cada fuente para el cálculo de consenso.
    """
    from app.services.source_weights import DEFAULT_SOURCE_WEIGHTS
    return {
        "status": "success",
        "weights": DEFAULT_SOURCE_WEIGHTS,
        "description": "Pesos de confianza por fuente (0-1). Mayor peso = más influencia en el promedio ponderado.",
    }

@router.get("/calculate-tmi")
def calculate_tmi(db: Session = Depends(get_db)):
    """
    Calcula el Temperature Market Index (TMI).
    Guarda snapshot en DB para historial.
    """
    try:
        from app.services.tmi_calculator import TMICalculator
        from app.models import TMISnapshot
        from decimal import Decimal
        
        components = TMICalculator.fetch_all_components()
        calc = TMICalculator()
        result = calc.calculate(components)
        
        # Guardar snapshot
        if result["tmi_score"] is not None:
            snapshot = TMISnapshot(
                tmi_score=Decimal(str(result["tmi_score"])),
                zone=result["zone"],
                coverage_pct=Decimal(str(result["coverage_pct"])),
            )
            db.add(snapshot)
            db.commit()
        
        # Alertas: verificar divergencia con CRI más reciente
        latest_cri = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
        if latest_cri and result["tmi_score"] is not None:
            get_alert_service().check_and_alert(
                float(latest_cri.cri_score),
                result["tmi_score"]
            )
        
        return {
            "status": "success",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando TMI: {str(e)}")

@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    """
    Obtiene historial de CRI y TMI de las últimas 24h para sparklines.
    """
    try:
        from datetime import timedelta
        from app.models import RiskIndex, TMISnapshot
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        cri_history = (
            db.query(RiskIndex)
            .filter(RiskIndex.timestamp >= cutoff)
            .order_by(RiskIndex.timestamp.asc())
            .all()
        )
        
        tmi_history = (
            db.query(TMISnapshot)
            .filter(TMISnapshot.timestamp >= cutoff)
            .order_by(TMISnapshot.timestamp.asc())
            .all()
        )
        
        return {
            "status": "success",
            "cri": [
                {"timestamp": r.timestamp.isoformat(), "score": float(r.cri_score), "zone": r.risk_zone}
                for r in cri_history
            ],
            "tmi": [
                {"timestamp": s.timestamp.isoformat(), "score": float(s.tmi_score), "zone": s.zone}
                for s in tmi_history
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/scenarios")
def list_scenarios():
    """
    Lista todos los escenarios predefinidos disponibles para simulacion.
    """
    return {
        "status": "success",
        "count": len(SCENARIOS),
        "scenarios": get_scenario_list(),
    }

@router.post("/simulate-scenario")
def simulate_scenario(payload: dict, db: Session = Depends(get_db)):
    """
    Activa un escenario de simulacion y calcula el CRI resultante.
    
    Payload: {"scenario_id": "gpu_shortage"}
    
    Escenarios disponibles:
    - normal: Mercado Normal
    - gpu_shortage: Escasez GPU
    - crypto_crash: Crash Crypto
    - bear_market: Bear Market
    - bull_run: Bull Run
    - supply_crisis: Crisis de Suministro
    - regulatory_shock: Shock Regulatorio
    - infrastructure_boom: Boom Infraestructura
    - ai_winter: Invierno IA
    - energy_crisis: Crisis Energetica
    """
    scenario_id = payload.get("scenario_id")
    if not scenario_id:
        raise HTTPException(status_code=400, detail="scenario_id requerido")
    
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Escenario invalido: {scenario_id}")
    
    mode_state = get_mode_state()
    mode_state.set_scenario(scenario_id)
    
    # Calcular CRI con escenario
    return calculate_cri(db)


@router.get("/news-pipeline")
def run_news_pipeline():
    """
    Ejecuta el pipeline completo de validación de noticias:
    1. RSS feeds (Reuters, HN, TechCrunch)
    2. Validación semántica (embeddings all-MiniLM-L6-v2)
    3. Extracción de sentimiento estructurado (Capex, Demanda, Regulatorio)
    """
    try:
        from app.external.rss_feeder import RSSFeeder
        from app.services.news_validator import NewsValidator
        from app.services.sentiment_extractor import SentimentExtractor

        # 1. RSS
        feeder = RSSFeeder()
        raw_articles = feeder.fetch_all(max_per_feed=10)
        
        # 2. Validación semántica
        validator = NewsValidator()
        validated = validator.validate_batch(raw_articles)

        # 3. Sentimiento estructurado
        extractor = SentimentExtractor()
        sentiment = extractor.extract(validated)

        # 4. Score para TMI
        relevance = validator.compute_relevance_score(validated)

        return {
            "status": "success",
            "total_raw": len(raw_articles),
            "validated": len(validated),
            "articles": validated[:20],
            "sentiment": sentiment,
            "tmi_news_score": relevance,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en news-pipeline: {str(e)}")


@router.get("/consensus-diff")
async def get_consensus_diff(db: Session = Depends(get_db)):
    """
    Ejecuta el Comité de Riesgo (Consensus Diff).
    Toma snapshot de CRI, TMI, noticias validadas y consulta LLMs.
    Retorna el score promedio de los LLMs y el diferencial con CRI algorítmico.
    """
    try:
        from app.services.consensus_diff import get_consensus_diff
        from app.models import RiskIndex, TMISnapshot

        # Obtener última data disponible
        latest_cri = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
        latest_tmi = db.query(TMISnapshot).order_by(TMISnapshot.timestamp.desc()).first()

        # Calcular delta 24h
        cri_delta = 0.0
        if latest_cri:
            historic = (
                db.query(RiskIndex)
                .filter(RiskIndex.timestamp >= (datetime.now(timezone.utc) - timedelta(hours=24)))
                .order_by(RiskIndex.timestamp.asc())
                .all()
            )
            if len(historic) >= 2:
                cri_delta = float(historic[-1].cri_score) - float(historic[0].cri_score)

        # Obtener noticias validadadas
        mode_state = get_mode_state()
        news = []
        try:
            from app.external.rss_feeder import RSSFeeder
            from app.services.news_validator import NewsValidator
            feeder = RSSFeeder()
            raw = feeder.fetch_all(max_per_feed=5)
            validator = NewsValidator()
            news = validator.validate_batch(raw)
        except Exception as e:
            logger.warning(f"[Consensus] Falló fetch de noticias: {e}")

        snapshot = {
            "cri_score": float(latest_cri.cri_score) if latest_cri else None,
            "cri_zone": latest_cri.risk_zone if latest_cri else "UNKNOWN",
            "tmi_score": float(latest_tmi.tmi_score) if latest_tmi else None,
            "cri_delta_24h": round(cri_delta, 2),
            "mode": mode_state.mode,
            "validated_news": news[:10],
        }

        consensus = get_consensus_diff()
        result = await consensus.run_committee(snapshot)

        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en consensus-diff: {str(e)}")


@router.get("/algorithmic-status")
def get_algorithmic_status(db: Session = Depends(get_db)):
    """
    Reporta el estado de las mejoras algorítmicas:
    - Z-Score de CRI
    - Pesos dinámicos por confianza (Data Decay)
    - EMA del CRI
    """
    try:
        from app.services.algorithmic_enhancements import (
            get_zscore, get_decay_weights, get_cri_ema
        )
        from app.models import RiskIndex

        history = (
            db.query(RiskIndex)
            .filter(RiskIndex.timestamp >= (datetime.now(timezone.utc) - timedelta(hours=24)))
            .order_by(RiskIndex.timestamp.asc())
            .all()
        )

        cri_values = [float(r.cri_score) for r in history]

        # Z-Score
        zscore_engine = get_zscore()
        zscore_result = zscore_engine.compute(cri_values)

        # EMA
        ema_engine = get_cri_ema()
        ema_engine.reset()
        ema_values = [ema_engine.smooth(v) for v in cri_values]

        # Decay
        decay_engine = get_decay_weights()
        for r in history[-5:]:  # últimas actualizaciones
            decay_engine.record_update("GSPI")
        decay_report = decay_engine.get_decay_report()
        effective_weights = decay_engine.get_effective_weights()

        return {
            "status": "success",
            "z_score": zscore_result,
            "ema": {
                "current": ema_values[-1] if ema_values else None,
                "last_24h": ema_values,
                "alpha": 0.3,
            },
            "decay": {
                "report": decay_report,
                "effective_weights": effective_weights,
                "rate_per_hour": "5%",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
