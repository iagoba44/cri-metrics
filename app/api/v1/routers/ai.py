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
    """Prompt enriquecido con TODOS los datos del sistema para Gemini."""
    from app.models import RiskIndex, TMISnapshot, TelemetryRecord
    from app.services.algorithmic_enhancements import get_zscore, get_decay_weights, get_cri_ema
    from app.services.predictive_engine import get_predictive_engine
    from app.services.tmi_calculator import TMICalculator
    from datetime import datetime, timedelta, timezone
    import numpy as np
    
    # ── 1. CRI + TMI actual ──
    latest_cri = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
    latest_tmi = db.query(TMISnapshot).order_by(TMISnapshot.timestamp.desc()).first()
    
    cri_score = float(latest_cri.cri_score) if latest_cri else None
    cri_zone = latest_cri.risk_zone if latest_cri else "UNKNOWN"
    tmi_score = float(latest_tmi.tmi_score) if latest_tmi else None
    tmi_zone = latest_tmi.zone if latest_tmi else "UNKNOWN"
    
    # Delta 24h CRI
    cri_delta_24h = 0.0
    if latest_cri:
        hist_24h = db.query(RiskIndex).filter(
            RiskIndex.timestamp >= (datetime.now(timezone.utc) - timedelta(hours=24))
        ).order_by(RiskIndex.timestamp.asc()).all()
        if len(hist_24h) >= 2:
            cri_delta_24h = float(hist_24h[-1].cri_score) - float(hist_24h[0].cri_score)
    
    # ── 2. KPIs con fuente, peso, y frescura ──
    now = datetime.now(timezone.utc)
    all_kpis = {}
    for kpi_code in ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]:
        latest = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.kpi_code == kpi_code)
            .order_by(TelemetryRecord.timestamp.desc())
            .first()
        )
        historical = (
            db.query(TelemetryRecord).filter(TelemetryRecord.kpi_code == kpi_code)
            .order_by(TelemetryRecord.timestamp.desc()).limit(50).all()
        )
        val = None
        if latest:
            val = float(latest.normalized_score) if latest and latest.normalized_score is not None else (
                float(latest.raw_value) if latest and latest.raw_value is not None else None)
        ts = latest.timestamp if latest else None
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        freshness_h = round((now - ts).total_seconds() / 3600, 1) if ts else None
        
        all_kpis[kpi_code] = {
            "name": {"GSPI":"GPU Spot Price Index","SHPD":"Server Hardware Price Deflation",
                     "LTCR":"Long-Term Contract Ratio","CFBR":"Cloud Free-Burn Rate",
                     "UOR":"Underutilization/Overcapacity Ratio"}[kpi_code],
            "value": val,
            "source": latest.data_source if latest else "N/A",
            "weight": {"GSPI":0.25,"SHPD":0.15,"LTCR":0.20,"CFBR":0.20,"UOR":0.20}[kpi_code],
            "freshness_h": freshness_h,
            "sample_size": len(historical),
        }
    
    # ── 3. Early Warning System + Predictivo ──
    cutoff_180d = datetime.now(timezone.utc) - timedelta(days=180)
    cri_history = (
        db.query(RiskIndex).filter(RiskIndex.timestamp >= cutoff_180d)
        .order_by(RiskIndex.timestamp.asc()).all()
    )
    cri_vals = [float(r.cri_score) for r in cri_history]
    
    predictive = {}
    if len(cri_vals) >= 14:
        engine = get_predictive_engine()
        analysis = engine.analyze(cri_vals)
        ews = analysis.get("early_warning", {})
        proj = analysis.get("projections", {}).get("projections", {})
        predictive = {
            "ew_signal": ews.get("ew_signal"),
            "ew_score": ews.get("ew_score"),
            "autocorrelation": ews.get("autocorrelation"),
            "variance": ews.get("variance"),
            "acceleration": ews.get("acceleration"),
            "ttd_days": ews.get("days_to_collapse"),
            "projection_30d_cri": proj.get("30", {}).get("projected_cri"),
            "projection_60d_cri": proj.get("60", {}).get("projected_cri"),
            "projection_90d_cri": proj.get("90", {}).get("projected_cri"),
            "collapse_prob_30d_pct": proj.get("30", {}).get("collapse_probability_pct"),
            "collapse_prob_60d_pct": proj.get("60", {}).get("collapse_probability_pct"),
            "collapse_prob_90d_pct": proj.get("90", {}).get("collapse_probability_pct"),
        }
    
    # ── 4. TMI Components ──
    tmi_components = {}
    try:
        comps = TMICalculator.fetch_all_components()
        tmi_components = {k: round(v, 1) if isinstance(v, (int, float)) else v for k, v in comps.items()}
    except Exception:
        pass
    
    # ── 5. Algoritmico: Z-Score, EMA, Decay ──
    zs = get_zscore().compute(cri_vals) if len(cri_vals) >= 2 else {}
    ema_eng = get_cri_ema()
    ema_val = None
    if cri_vals:
        ema_eng.reset()
        ema_val = ema_eng.smooth(cri_vals[-1]) if len(cri_vals) >= 1 else None
    decay = get_decay_weights().get_effective_weights()
    
    # ── 6. Historico 6 meses ──
    hist_stats = {}
    if cri_vals:
        arr = np.array(cri_vals)
        hist_stats = {
            "cri_min_180d": round(float(np.min(arr)), 1),
            "cri_max_180d": round(float(np.max(arr)), 1),
            "cri_mean_180d": round(float(np.mean(arr)), 1),
            "cri_std_180d": round(float(np.std(arr)), 1),
            "trend_7d": round(cri_vals[-1] - cri_vals[-8], 2) if len(cri_vals) >= 8 else None,
            "trend_30d": round(cri_vals[-1] - cri_vals[-min(31, len(cri_vals))], 2),
            "trend_90d": round(cri_vals[-1] - cri_vals[-min(91, len(cri_vals))], 2) if len(cri_vals) >= 91 else None,
            "data_points": len(cri_vals),
            "zone_low_days": sum(1 for v in cri_vals if v <= 30),
            "zone_moderate_days": sum(1 for v in cri_vals if 30 < v <= 65),
            "zone_critical_days": sum(1 for v in cri_vals if v > 65),
            "alerts_triggered": sum(1 for r in cri_history if r.alerts_triggered == "true"),
        }
    
    # ── 7. News & Sentiment ──
    news_articles = []
    sentiment_data = {}
    try:
        from app.external.rss_feeder import RSSFeeder
        from app.services.news_validator import NewsValidator
        from app.services.sentiment_extractor import SentimentExtractor
        feeder = RSSFeeder()
        raw = feeder.fetch_all(max_per_feed=5)
        validator = NewsValidator()
        validated = validator.validate_batch(raw)
        news_articles = [{"title": n.get("title", ""), "score": n.get("semantic_score", 0)} for n in validated[:10]]
        sentiment_data = SentimentExtractor().extract(validated)
    except Exception:
        pass
    
    # ── 8. Salud de fuentes ──
    active_sources = set()
    for kpi in all_kpis.values():
        if kpi["source"] and kpi["source"] != "N/A":
            active_sources.add(kpi["source"])
    sources_stale = sum(1 for v in all_kpis.values() if v["freshness_h"] and v["freshness_h"] > 6)
    sources_offline = sum(1 for v in all_kpis.values() if v["value"] is None)
    
    # ── 9. Eventos de backfill ──
    events = [
        {"day": -170, "name": "NVIDIA earnings beat", "impact": "CRI -12 (bullish)"},
        {"day": -140, "name": "EU AI Act approved", "impact": "CRI +8 (regulatory uncertainty)"},
        {"day": -105, "name": "Crypto flash crash (ETH -30%)", "impact": "CRI +18 (capital flight)"},
        {"day": -70, "name": "TSMC wafer price hike", "impact": "CRI +10 (supply chain)"},
        {"day": -35, "name": "Data center building boom", "impact": "CRI -15 (bullish)"},
        {"day": -14, "name": "AI winter fears", "impact": "CRI +8 (sentiment shift)"},
    ]
    
    # ═══════════════════════════════════════════════════
    # CONSTRUIR PROMPT ENRIQUECIDO
    # ═══════════════════════════════════════════════════
    gemini_prompt = f"""ERES UN ANALISTA SENIOR DE INFRAESTRUCTURA DE INTELIGENCIA ARTIFICIAL.
Genera un reporte ejecutivo profesional basado en los siguientes datos del sistema CRI Metrics.

═══════════════════════════════════════════════
SECCION 1: RESUMEN EJECUTIVO
═══════════════════════════════════════════════
• CRI (Composite Risk Index): {cri_score}/100 — Zona: {cri_zone}
• TMI (Temperature Market Index): {tmi_score}/100 — Zona: {tmi_zone}
• Variacion CRI 24h: {cri_delta_24h:+.1f} puntos
• Alertas disparadas (180d): {hist_stats.get('alerts_triggered', '?')}
• CRI 6 meses: min={hist_stats.get('cri_min_180d')} max={hist_stats.get('cri_max_180d')} mean={hist_stats.get('cri_mean_180d')}

═══════════════════════════════════════════════
SECCION 2: KPIs DE ENTRADA (Componentes del CRI)
═══════════════════════════════════════════════
"""
    for k, v in all_kpis.items():
        freshness_str = f"{v['freshness_h']}h" if v['freshness_h'] else "N/A"
        gemini_prompt += f"• {v['name']} ({k}): {v['value']}/100 | Peso: {int(v['weight']*100)}% | Fuente: {v['source']} | Frescura: {freshness_str} | Muestras: {v['sample_size']}\n"
    
    gemini_prompt += f"""
═══════════════════════════════════════════════
SECCION 3: SISTEMA PREDICTIVO (Early Warning)
═══════════════════════════════════════════════
• EW Signal: {predictive.get('ew_signal', 'N/A')} (Score combinado: {predictive.get('ew_score', 'N/A')})
• Autocorrelacion lag-1: {predictive.get('autocorrelation', 'N/A')} ({'>0.5 = Critical Slowing Down' if predictive.get('autocorrelation') and predictive['autocorrelation'] > 0.5 else '<0.5 = sistema estable'})
• Varianza movil (30d): {predictive.get('variance', 'N/A')}
• Aceleracion (2a derivada CRI): {predictive.get('acceleration', 'N/A')} ({'>0 = riesgo acelerando' if predictive.get('acceleration') and predictive['acceleration'] > 0 else '<0 = riesgo desacelerando'})
• TTD (Time To Danger): {predictive.get('ttd_days', 'N/A')} dias hasta umbral critico (65)

Proyecciones (regresion lineal con bandas 95% confianza):
• 30 dias: CRI={predictive.get('projection_30d_cri', 'N/A')} | Prob. colapso: {predictive.get('collapse_prob_30d_pct', 'N/A')}%
• 60 dias: CRI={predictive.get('projection_60d_cri', 'N/A')} | Prob. colapso: {predictive.get('collapse_prob_60d_pct', 'N/A')}%
• 90 dias: CRI={predictive.get('projection_90d_cri', 'N/A')} | Prob. colapso: {predictive.get('collapse_prob_90d_pct', 'N/A')}%

═══════════════════════════════════════════════
SECCION 4: COMPONENTES TMI (7 sub-indices)
═══════════════════════════════════════════════
"""
    tmi_labels = {
        "fear_greed": "Fear & Greed Index (sentimiento mercado)",
        "arxiv_velocity": "arXiv paper velocity (investigacion IA)",
        "hn_activity": "HackerNews actividad (comunidad tech)",
        "hashrate": "Hashrate global (mineria GPU)",
        "ai_tokens": "AI tokens performance (NEAR, RENDER, FET, TAO)",
        "news_coverage": "News coverage score (prensa IA)",
        "ai_revenue": "AI revenue proxy (NVIDIA earnings)",
    }
    for key, label in tmi_labels.items():
        val = tmi_components.get(key, "N/A")
        gemini_prompt += f"• {label}: {val}\n"
    
    gemini_prompt += f"""
═══════════════════════════════════════════════
SECCION 5: INDICADORES TECNICOS
═══════════════════════════════════════════════
• Z-Score volatilidad: {zs.get('z_score', 'N/A')} ({'>2.5 = volatilidad anomala' if isinstance(zs.get('z_score'), (int,float)) and zs['z_score'] > 2.5 else 'normal'})
• EMA suavizado CRI: {ema_val if ema_val else 'N/A'}
• Pesos dinamicos (decay por confianza): {', '.join([f'{k}={round(v,2)}' for k,v in (decay.items() if decay else [])]) if decay else 'N/A'}

═══════════════════════════════════════════════
SECCION 6: HISTORICO 6 MESES
═══════════════════════════════════════════════
• Datapoints: {hist_stats.get('data_points', '?')}
• Min CRI: {hist_stats.get('cri_min_180d')} | Max CRI: {hist_stats.get('cri_max_180d')} | Media: {hist_stats.get('cri_mean_180d')} | Desviacion: {hist_stats.get('cri_std_180d')}
• Tendencia 7d: {hist_stats.get('trend_7d', 'N/A'):+.1f} | 30d: {hist_stats.get('trend_30d', 'N/A'):+.1f} | 90d: {hist_stats.get('trend_90d', 'N/A'):+.1f}
• Dias en zona LOW: {hist_stats.get('zone_low_days')} | MODERATE: {hist_stats.get('zone_moderate_days')} | CRITICAL: {hist_stats.get('zone_critical_days')}

Eventos de mercado detectados:
"""
    for evt in events:
        gemini_prompt += f"• {evt['name']} ({evt['impact']})\n"
    
    gemini_prompt += f"""
═══════════════════════════════════════════════
SECCION 7: NOTICIAS Y SENTIMIENTO
═══════════════════════════════════════════════
Sentimiento estructurado:
• Capex (inversion infra): {sentiment_data.get('capex_score', 'N/A')}/100
• Demanda computacional: {sentiment_data.get('demand_score', 'N/A')}/100
• Riesgo regulatorio: {sentiment_data.get('regulatory_score', 'N/A')}/100
• Resumen: {sentiment_data.get('summary', 'No disponible')}

Titulares validados (top 5):
"""
    for art in news_articles[:5]:
        gemini_prompt += f"• [{art['score']}] {art['title']}\n"
    
    gemini_prompt += f"""
═══════════════════════════════════════════════
SECCION 8: SALUD DE FUENTES DE DATOS
═══════════════════════════════════════════════
• Fuentes activas: {len(active_sources)} ({', '.join(sorted(active_sources))})
• Fuentes stale (>6h): {sources_stale}
• Fuentes offline (sin datos): {sources_offline}

═══════════════════════════════════════════════
INSTRUCCIONES PARA EL ANALISIS
═══════════════════════════════════════════════
Basado en TODOS los datos anteriores, genera un reporte ejecutivo estructurado:

1. RESUMEN DE MERCADO (2-3 frases):
   - Estado general del ecosistema IA
   - Tendencia direccional (mejorando/empeorando/estable)
   - Nivel de alerta justificado

2. DRIVERS PRINCIPALES (3-5 factores):
   - Que KPIs estan moviendo el CRI
   - Que eventos recientes impactan
   - Senales tempranas del EWS

3. EVALUACION DE RIESGO:
   - Probabilidad de deterioro a 30/60/90 dias
   - Escenario mas probable vs peor escenario
   - Confianza en la evaluacion (ALTA/MEDIA/BAJA) justificada por frescura de datos

4. RECOMENDACIONES ACCIONABLES (3-5):
   - Acciones concretas para operadores de infraestructura IA
   - Priorizadas por urgencia

5. OUTLOOK 30-90 DIAS:
   - Proyeccion fundamentada en tendencias y eventos
   - Catalizadores a vigilar

Formato: Texto claro, profesional, sin markdown. Usa los datos numericos como evidencia.
"""
    
    # ── Llamar a Gemini ──
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
                "cri_score": cri_score,
                "cri_zone": cri_zone,
                "tmi_score": tmi_score,
                "tmi_zone": tmi_zone,
                "cri_delta_24h": cri_delta_24h,
                "kpis": all_kpis,
                "predictive": predictive,
                "tmi_components": tmi_components,
                "algorithmic": {
                    "z_score": zs.get("z_score"),
                    "ema": ema_val,
                    "decay": {k: round(v, 2) for k, v in decay.items()} if decay else {},
                },
                "historical_stats": hist_stats,
                "events": events,
                "sentiment": sentiment_data,
                "news": news_articles[:10],
                "source_health": {
                    "active_count": len(active_sources),
                    "active_names": sorted(active_sources),
                    "stale_count": sources_stale,
                    "offline_count": sources_offline,
                },
            },
            "prompts": {
                "gemini_full": gemini_prompt,
            },
            "gemini_response": gemini_response,
            "gemini_error": gemini_error,
            "data_lineage": {
                "description": "Prompt enriquecido con 8 secciones: CRI+TMI, KPIs, Predictivo, TMI Components, Tecnicos, Historico, Noticias, Salud Fuentes",
                "total_sections": 8,
                "total_kpis": len(all_kpis),
                "prompt_length_chars": len(gemini_prompt),
            },
        },
    }


@router.get("/download-report")
async def download_report(db: Session = Depends(get_db)):
    """Genera y descarga un reporte ejecutivo HTML/PDF."""
    from fastapi.responses import HTMLResponse
    
    feed = await get_ai_data_feed(db)
    if feed["status"] != "success":
        raise HTTPException(status_code=500, detail="Error recopilando métricas")
        
    data = feed["data"]
    gemini_resp = data.get("gemini_response") or "El análisis de Gemini no está disponible. Verifique su API key."
    snapshot = data["snapshot"]
    
    # Formatear la respuesta de Gemini en párrafos legibles
    gemini_html = gemini_resp.replace("\n", "<br>")
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Reporte Ejecutivo de Salud del Mercado CRI</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #2d3748;
            background-color: #f7fafc;
            margin: 0;
            padding: 40px;
        }}
        .container {{
            max-width: 850px;
            margin: 0 auto;
            background: #fff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
        }}
        .header {{
            border-bottom: 3px solid #3182ce;
            padding-bottom: 20px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .logo {{
            font-size: 22px;
            font-weight: 800;
            color: #2b6cb0;
            letter-spacing: 0.05em;
        }}
        .date {{
            font-size: 13px;
            color: #718096;
            font-weight: 600;
        }}
        h1 {{
            font-size: 28px;
            color: #1a202c;
            margin-top: 0;
        }}
        h2 {{
            font-size: 18px;
            color: #2b6cb0;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
            margin-top: 30px;
        }}
        .overview-grid {{
            display: grid;
            grid-template-cols: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-top: 4px solid #3182ce;
            padding: 20px;
            border-radius: 4px;
            text-align: center;
        }}
        .metric-card.critical {{
            border-top: 4px solid #e53e3e;
            background: #fff5f5;
        }}
        .metric-card.success {{
            border-top: 4px solid #48bb78;
            background: #f0fff4;
        }}
        .metric-title {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #718096;
            margin-bottom: 8px;
            font-weight: 700;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: 800;
            color: #1a202c;
        }}
        .metric-subtitle {{
            font-size: 12px;
            color: #4a5568;
            margin-top: 5px;
            font-weight: 600;
        }}
        .kpi-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .kpi-table th, .kpi-table td {{
            border: 1px solid #e2e8f0;
            padding: 12px;
            text-align: left;
            font-size: 14px;
        }}
        .kpi-table th {{
            background-color: #f7fafc;
            color: #4a5568;
            font-weight: 700;
        }}
        .analysis-box {{
            line-height: 1.7;
            font-size: 15px;
            background: #fff;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            white-space: pre-line;
            color: #2d3748;
        }}
        .footer {{
            margin-top: 50px;
            border-top: 1px solid #e2e8f0;
            padding-top: 20px;
            font-size: 11px;
            color: #a0aec0;
            text-align: center;
        }}
        @media print {{
            body {{
                background: none;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                border: none;
                padding: 0;
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">CRI INFRASTRUCTURE INTELLIGENCE</div>
            <div class="date">{datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")} UTC</div>
        </div>
        
        <h1>Reporte Ejecutivo de Salud del Mercado</h1>
        
        <div class="overview-grid">
            <div class="metric-card {"critical" if snapshot['cri_score'] > 65 else "success" if snapshot['cri_score'] <= 30 else ""}">
                <div class="metric-title">Composite Risk Index (CRI)</div>
                <div class="metric-value">{snapshot['cri_score']:.2f}</div>
                <div class="metric-subtitle">ZONA: {snapshot['cri_zone']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Temperature Market Index (TMI)</div>
                <div class="metric-value">{snapshot['tmi_score']:.2f}</div>
                <div class="metric-subtitle">ESTADO: {snapshot['tmi_zone']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Variación CRI 24h</div>
                <div class="metric-value">{snapshot['cri_delta_24h']:+.2f}</div>
                <div class="metric-subtitle">Tendencia actual</div>
            </div>
        </div>
        
        <h2>Indicadores de Telemetría Clave (KPIs)</h2>
        <table class="kpi-table">
            <thead>
                <tr>
                    <th>KPI</th>
                    <th>Nombre Comercial</th>
                    <th>Puntuación</th>
                    <th>Origen de Datos</th>
                    <th>Frescura</th>
                </tr>
            </thead>
            <tbody>
    """
    for code, info in snapshot["kpis"].items():
        fresh = f"Hace {info['freshness_h']}h" if info['freshness_h'] is not None else "N/A"
        html_content += f"""
                <tr>
                    <td><strong>{code}</strong></td>
                    <td>{info['name']}</td>
                    <td>{info['value']:.1f}/100</td>
                    <td>{info['source']}</td>
                    <td>{fresh}</td>
                </tr>
        """
        
    html_content += f"""
            </tbody>
        </table>
        
        <h2>Alertas y Análisis Predictivo</h2>
        <table class="kpi-table">
            <tr>
                <td><strong>Señal de Alerta Temprana (EWS):</strong></td>
                <td>{snapshot['predictive'].get('ew_signal', 'NORMAL')}</td>
            </tr>
            <tr>
                <td><strong>Time To Danger (TTD):</strong></td>
                <td>{snapshot['predictive'].get('ttd_days', 'N/A')} días (hasta CRI > 65)</td>
            </tr>
            <tr>
                <td><strong>Probabilidad de Corrección (30d):</strong></td>
                <td>{snapshot['predictive'].get('collapse_prob_30d_pct', 0)}%</td>
            </tr>
        </table>

        <h2>Análisis Inteligente por IA (Gemini 2.5 Flash)</h2>
        <div class="analysis-box">
            {gemini_resp}
        </div>
        
        <div class="footer">
            Este reporte ejecutivo fue auto-generado por la plataforma CRI Metrics v3.0 mediante recolección de telemetría distribuida y síntesis cognitiva generativa.
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
