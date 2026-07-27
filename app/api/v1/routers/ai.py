import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RiskIndex, TMISnapshot, TelemetryRecord
from app.scenarios import get_mode_state
from app.config import get_settings
from app.services.algorithmic_enhancements import get_zscore, get_decay_weights
from app.services.tmi_calculator import TMICalculator
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_sources_counts(db: Session):
    kpis = ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]
    now = datetime.now(timezone.utc)
    active = 0

    for kpi in kpis:
        latest = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.kpi_code == kpi)
            .order_by(TelemetryRecord.timestamp.desc())
            .first()
        )
        if latest and latest.timestamp:
            ts = latest.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if (now - ts).total_seconds() < 3600:
                active += 1

    return active, len(kpis)


@router.get("/consensus-diff")
async def get_consensus_diff(db: Session = Depends(get_db)):
    try:
        from app.services.consensus_diff import get_consensus_diff
        from app.models import RiskIndex, TMISnapshot

        latest_cri = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
        latest_tmi = db.query(TMISnapshot).order_by(TMISnapshot.timestamp.desc()).first()

        cri_delta = 0.0
        if latest_cri:
            historic = db.query(RiskIndex).filter(
                RiskIndex.timestamp >= (datetime.now(timezone.utc) - timedelta(hours=24))
            ).order_by(RiskIndex.timestamp.asc()).all()
            if len(historic) >= 2:
                cri_delta = float(historic[-1].cri_score) - float(historic[0].cri_score)

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
            logger.warning(f"[Consensus] Fallo fetch de noticias: {e}")

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


@router.get("/gemini-analysis")
async def get_gemini_analysis(custom_prompt: str = "", db: Session = Depends(get_db)):
    try:
        from app.services.gemini_analysis import get_gemini_analysis
        from app.models import RiskIndex, TMISnapshot
        from app.services.algorithmic_enhancements import get_zscore, get_decay_weights
        from app.services.tmi_calculator import TMICalculator

        latest_cri = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
        latest_tmi = db.query(TMISnapshot).order_by(TMISnapshot.timestamp.desc()).first()

        cri_delta_24h = 0.0
        if latest_cri:
            historic = db.query(RiskIndex).filter(
                RiskIndex.timestamp >= (datetime.now(timezone.utc) - timedelta(hours=24))
            ).order_by(RiskIndex.timestamp.asc()).all()
            if len(historic) >= 2:
                cri_delta_24h = float(historic[-1].cri_score) - float(historic[0].cri_score)

        tmi_str = []
        try:
            comps = TMICalculator.fetch_all_components()
            for k, v in comps.items():
                tmi_str.append(f"  - {k}: {v}")
        except Exception:
            pass
        tmi_components_text = "\n".join(tmi_str) if tmi_str else "No disponible"

        news_context, sentiment_data = "No hay noticias recientes.", {"capex_score": 50, "demand_score": 50, "regulatory_score": 50, "summary": "Neutral"}
        try:
            from app.external.rss_feeder import RSSFeeder
            from app.services.news_validator import NewsValidator
            from app.services.sentiment_extractor import SentimentExtractor
            feeder = RSSFeeder()
            raw = feeder.fetch_all(max_per_feed=5)
            validator = NewsValidator()
            validated = validator.validate_batch(raw)
            news_str = [f"- [{n.get('semantic_score',0)}] {n.get('title','')}" for n in validated[:8]]
            if news_str:
                news_context = "\n".join(news_str)
            sentiment_data = SentimentExtractor().extract(validated)
        except Exception as e:
            logger.warning(f"[GeminiAnalysis] News: {e}")

        cri_vals = [float(r.cri_score) for r in db.query(RiskIndex).filter(
            RiskIndex.timestamp >= (datetime.now(timezone.utc) - timedelta(hours=24))
        ).order_by(RiskIndex.timestamp.asc()).all()]
        zs = get_zscore().compute(cri_vals) if cri_vals else {}
        decay = get_decay_weights().get_effective_weights()

        active, total = _get_sources_counts(db)

        snapshot = {
            "cri_score": float(latest_cri.cri_score) if latest_cri else None,
            "cri_zone": latest_cri.risk_zone if latest_cri else "UNKNOWN",
            "tmi_score": float(latest_tmi.tmi_score) if latest_tmi else None,
            "tmi_zone": latest_tmi.zone if latest_tmi else "UNKNOWN",
            "cri_delta_24h": round(cri_delta_24h, 2),
            "mode": get_mode_state().mode,
            "active_sources": active,
            "total_sources": total,
            "tmi_components_text": tmi_components_text,
            "news_context": news_context,
            "sentiment": sentiment_data,
            "zscore": zs.get("z_score", "N/A"),
            "ema": cri_vals[-1] if cri_vals else "N/A",
            "decay_text": str({k: round(v, 2) for k, v in decay.items()}) if decay else "N/A",
        }

        analysis = get_gemini_analysis()
        report = await analysis.generate(snapshot, custom_prompt)
        report["snapshot"] = snapshot
        return {"status": "success", "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en gemini-analysis: {str(e)}")


@router.get("/ai-data-feed")
async def get_ai_data_feed(db: Session = Depends(get_db)):
    """Muestra el prompt, la respuesta de Gemini, y el data lineage completo."""
    from app.models import RiskIndex, TMISnapshot, TelemetryRecord
    from app.services.algorithmic_enhancements import get_zscore, get_decay_weights
    from datetime import datetime, timedelta, timezone
    
    # Datos actuales
    latest_cri = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
    latest_tmi = db.query(TMISnapshot).order_by(TMISnapshot.timestamp.desc()).first()
    
    # KPIs actuales con fuente
    kpis = {}
    for kpi_code in ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]:
        latest = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.kpi_code == kpi_code)
            .order_by(TelemetryRecord.timestamp.desc())
            .first()
        )
        historical = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.kpi_code == kpi_code)
            .order_by(TelemetryRecord.timestamp.desc())
            .limit(50).all()
        )
        kpis[kpi_code] = {
            "name": {"GSPI": "GPU Spot Price Index", "SHPD": "Server Hardware Price Deflation",
                     "LTCR": "Long-Term Contract Ratio", "CFBR": "Cloud Free-Burn Rate",
                     "UOR": "Underutilization / Overcapacity Ratio"}[kpi_code],
            "current_value": float(latest.normalized_score) if latest and latest.normalized_score else None,
            "source": latest.data_source if latest else "N/A",
            "last_updated": latest.timestamp.isoformat() if latest and latest.timestamp else None,
            "sample_size": len(historical),
            "weight": {"GSPI": 0.25, "SHPD": 0.15, "LTCR": 0.20, "CFBR": 0.20, "UOR": 0.20}[kpi_code],
            "unit": {"GSPI": "% deflacion GPU spot", "SHPD": "% deflacion hardware",
                     "LTCR": "indice volatilidad 0-100", "CFBR": "% volatilidad escalada",
                     "UOR": "% infrautilizacion"}[kpi_code],
        }
    
    # CRI historico 30d
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    cri_30d = (
        db.query(RiskIndex)
        .filter(RiskIndex.timestamp >= cutoff_30d)
        .order_by(RiskIndex.timestamp.asc())
        .all()
    )
    cri_trend = [float(r.cri_score) for r in cri_30d]
    
    # Fuentes activas
    active_sources = set()
    for kpi in kpis.values():
        if kpi["source"] and kpi["source"] != "N/A":
            active_sources.add(kpi["source"])
    
    # Prompt para Gemini
    gemini_prompt = f"""**CONTEXTO DE MERCADO IA - INFRAESTRUCTURA**

**Composite Risk Index (CRI):** {float(latest_cri.cri_score) if latest_cri else 'N/A'}/100 [{latest_cri.risk_zone if latest_cri else 'UNKNOWN'}]
**Temperature Market Index (TMI):** {float(latest_tmi.tmi_score) if latest_tmi else 'N/A'}/100 [{latest_tmi.zone if latest_tmi else 'UNKNOWN'}]

**KPIs de Entrada:**
"""
    for k, v in kpis.items():
        gemini_prompt += f"- {v['name']} ({k}): {v['current_value']}/100 | Fuente: {v['source']} | Peso: {int(v['weight']*100)}%\n"
    
    gemini_prompt += f"""
**Tendencia CRI 30d:** {', '.join([str(round(x,1)) for x in cri_trend[-7:]])} (ultimos 7 dias)

**Fuentes de datos activas:** {len(active_sources)} ({', '.join(sorted(active_sources))})

**Instruccion:**
Genera un reporte ejecutivo con:
1. Resumen de la situacion actual del mercado de infraestructura IA
2. Drivers principales (2-3 factores)
3. Recomendaciones (2-3 acciones concretas)
4. Outlook a 30-90 dias
5. Nivel de confianza del analisis (BAJO/MEDIO/ALTO)
"""
    
    # Llamar a Gemini
    gemini_response = None
    gemini_error = None
    try:
        import google.generativeai as genai
        settings = get_settings()
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: model.generate_content(gemini_prompt)
            )
            gemini_response = resp.text if resp else None
        else:
            gemini_error = "GEMINI_API_KEY no configurada"
    except Exception as e:
        gemini_error = str(e)
        logger.warning(f"[AI-Data-Feed] Gemini error: {e}")
    
    return {
        "status": "success",
        "data": {
            "snapshot": {
                "cri_score": float(latest_cri.cri_score) if latest_cri else None,
                "cri_zone": latest_cri.risk_zone if latest_cri else "UNKNOWN",
                "tmi_score": float(latest_tmi.tmi_score) if latest_tmi else None,
                "tmi_zone": latest_tmi.zone if latest_tmi else "UNKNOWN",
                "kpis": kpis,
                "active_sources": sorted(active_sources),
                "active_sources_count": len(active_sources),
                "cri_trend_30d": cri_trend,
            },
            "prompts": {
                "gemini_full": gemini_prompt,
            },
            "gemini_response": gemini_response,
            "gemini_error": gemini_error,
            "data_lineage": {
                "description": "Cada KPI se obtiene de fuentes externas, se normaliza (0-100), y se pondera para calcular el CRI.",
                "sources_accessed": sorted(active_sources),
                "total_kpis": len(kpis),
                "total_datapoints_30d": sum(v["sample_size"] for v in kpis.values()),
            },
        },
    }
