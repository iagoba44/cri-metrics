from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RiskIndex, TMISnapshot
from app.services.alerts import get_alert_service
from app.services.tmi_calculator import TMICalculator
from app.services.predictive_engine import get_predictive_engine, TrendProjector
from datetime import datetime, timedelta, timezone
from decimal import Decimal

router = APIRouter()


@router.get("/calculate-tmi")
def calculate_tmi(db: Session = Depends(get_db)):
    try:
        components = TMICalculator.fetch_all_components()
        calc = TMICalculator()
        result = calc.calculate(components)

        if result["tmi_score"] is not None:
            snapshot = TMISnapshot(
                tmi_score=Decimal(str(result["tmi_score"])),
                zone=result["zone"],
                coverage_pct=Decimal(str(result["coverage_pct"])),
            )
            db.add(snapshot)
            db.commit()

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


@router.get("/predictive-status")
def get_predictive_status(db: Session = Depends(get_db)):
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=180)
        rows = (
            db.query(RiskIndex)
            .filter(RiskIndex.timestamp >= cutoff)
            .order_by(RiskIndex.timestamp.asc())
            .all()
        )
        history = [float(r.cri_score) for r in rows]

        engine = get_predictive_engine()
        result = engine.analyze(history)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predictivo: {str(e)}")


@router.get("/projections")
def get_projections(days: int = 180, db: Session = Depends(get_db)):
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        rows = (
            db.query(RiskIndex)
            .filter(RiskIndex.timestamp >= cutoff)
            .order_by(RiskIndex.timestamp.asc())
            .all()
        )
        history = [float(r.cri_score) for r in rows]

        projector = TrendProjector()
        proj = projector.project(history)
        history_limit = min(len(rows), max(30, days // 2))
        proj["history"] = [
            {"timestamp": r.timestamp.isoformat(), "score": float(r.cri_score)}
            for r in rows[-history_limit:]
        ]
        return {"status": "success", "data": proj}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en proyecciones: {str(e)}")


@router.get("/predictive-detail")
def get_predictive_detail(db: Session = Depends(get_db)):
    """Analisis predictivo detallado con senales EWS en ventanas moviles."""
    import numpy as np
    from app.services.predictive_engine import get_predictive_engine, EarlyWarningSystem

    cutoff = datetime.now(timezone.utc) - timedelta(days=180)
    rows = (
        db.query(RiskIndex)
        .filter(RiskIndex.timestamp >= cutoff)
        .order_by(RiskIndex.timestamp.asc())
        .all()
    )
    if len(rows) < 14:
        return {"status": "success", "data": {"status": "insufficient_data"}}

    history = [float(r.cri_score) for r in rows]
    timestamps = [r.timestamp.isoformat() for r in rows]

    engine = get_predictive_engine()
    result = engine.analyze(history)

    # Rolling window: calcular EWS para cada ventana de 30 dias
    ews_rolling = []
    for i in range(30, len(history) + 1, 3):
        window = history[max(0, i - 30):i]
        ts = timestamps[i - 1]
        ews_result = engine.ews.compute(window)
        ews_rolling.append({
            "timestamp": ts,
            "cri": round(window[-1], 2),
            "autocorrelation": ews_result.get("autocorrelation"),
            "variance": ews_result.get("variance"),
            "acceleration": ews_result.get("acceleration"),
            "ew_score": ews_result.get("ew_score"),
            "ew_signal": ews_result.get("ew_signal"),
        })

    # Estadisticas descriptivas
    arr = np.array(history)
    stats_desc = {
        "mean": round(float(np.mean(arr)), 2),
        "std": round(float(np.std(arr)), 2),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
        "current": round(history[-1], 2),
        "trend_7d": round(history[-1] - history[-8], 2) if len(history) >= 8 else 0,
        "trend_30d": round(history[-1] - history[-min(31, len(history))], 2),
        "data_points": len(history),
        "date_range": f"{rows[0].timestamp.strftime('%Y-%m-%d')} → {rows[-1].timestamp.strftime('%Y-%m-%d')}",
    }

    # Contribucion de KPIs al modelo
    from app.models import TelemetryRecord
    kpi_contrib = {}
    for kpi in ["GSPI", "SHPD", "LTCR", "CFBR", "UOR"]:
        latest = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.kpi_code == kpi)
            .order_by(TelemetryRecord.timestamp.desc())
            .first()
        )
        kpi_contrib[kpi] = {
            "value": float(latest.normalized_score) if latest and latest.normalized_score else None,
            "source": latest.data_source if latest else "N/A",
            "weight": {"GSPI": 0.25, "SHPD": 0.15, "LTCR": 0.20, "CFBR": 0.20, "UOR": 0.20}[kpi],
        }

    return {
        "status": "success",
        "data": {
            "analysis": result,
            "rolling_ews": ews_rolling,
            "statistics": stats_desc,
            "kpi_inputs": kpi_contrib,
            "explanation": {
                "autocorrelation": "Mide la inercia del sistema. Valores >0.5 indican que las perturbaciones tardan en disiparse (senial pre-colapso).",
                "variance": "Dispersion de los valores CRI. Varianza creciente = sistema inestable, oscilaciones amplias.",
                "acceleration": "2a derivada del CRI. Positiva y creciente = el riesgo se acelera hacia arriba.",
                "ew_signal": "Score combinado 0-1. <0.5=NORMAL, 0.5-0.75=PRE-ALERT, >0.75=CRITICAL.",
                "ttd": "Time To Danger: estimacion lineal de cuantos dias faltan para cruzar el umbral critico (65).",
                "projections": "Proyeccion lineal con bandas de confianza al 95% (1.96 SE).",
            },
        },
    }
