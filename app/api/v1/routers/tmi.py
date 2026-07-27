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
