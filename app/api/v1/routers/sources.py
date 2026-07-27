from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TelemetryRecord
from app.scenarios import get_mode_state, SCENARIOS
from app.services.source_weights import DEFAULT_SOURCE_WEIGHTS
from datetime import datetime, timedelta, timezone
import numpy as np

router = APIRouter()


@router.get("/sources")
def get_sources_status(db: Session = Depends(get_db)):
    mode_state = get_mode_state()
    now = datetime.now(timezone.utc)

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


@router.get("/source-weights")
def get_source_weights():
    return {
        "status": "success",
        "weights": DEFAULT_SOURCE_WEIGHTS,
        "description": "Pesos de confianza por fuente (0-1). Mayor peso = más influencia en el promedio ponderado.",
    }


@router.get("/explanations")
def get_kpi_explanations():
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


@router.get("/correlations")
def get_kpi_correlations(db: Session = Depends(get_db)):
    """Matriz de correlacion entre KPIs usando los ultimos 90 dias."""
    kpis = ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    records = {}
    for kpi in kpis:
        rows = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.kpi_code == kpi, TelemetryRecord.timestamp >= cutoff)
            .order_by(TelemetryRecord.timestamp.asc())
            .all()
        )
        by_day = {}
        for r in rows:
            day = r.timestamp.strftime("%Y-%m-%d")
            if r.normalized_score is not None:
                by_day[day] = float(r.normalized_score)
        records[kpi] = by_day

    days = sorted(set().union(*[r.keys() for r in records.values()]))
    matrix = []
    for day in days:
        matrix.append([records[k].get(day) for k in kpis])

    corr_data = np.array(matrix).T
    corr_matrix = []
    for i, k1 in enumerate(kpis):
        for j, k2 in enumerate(kpis):
            if j <= i:
                mask = ~np.isnan(corr_data[i]) & ~np.isnan(corr_data[j])
                if mask.sum() > 2:
                    c = float(np.corrcoef(corr_data[i][mask], corr_data[j][mask])[0, 1])
                else:
                    c = 0.0
                corr_matrix.append({"kpi1": k1, "kpi2": k2, "correlation": round(c, 3)})

    return {"status": "success", "kpis": kpis, "correlations": corr_matrix}


@router.get("/news-pipeline")
def run_news_pipeline():
    try:
        from app.external.rss_feeder import RSSFeeder
        from app.services.news_validator import NewsValidator
        from app.services.sentiment_extractor import SentimentExtractor

        feeder = RSSFeeder()
        raw_articles = feeder.fetch_all(max_per_feed=10)
        validator = NewsValidator()
        validated = validator.validate_batch(raw_articles)
        extractor = SentimentExtractor()
        sentiment = extractor.extract(validated)
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
