from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import RiskIndex
from app.services.algorithmic_enhancements import get_zscore, get_decay_weights, get_cri_ema
from datetime import datetime, timedelta, timezone

router = APIRouter()


@router.get("/algorithmic-status")
def get_algorithmic_status(db: Session = Depends(get_db)):
    try:
        history = db.query(RiskIndex).filter(
            RiskIndex.timestamp >= (datetime.now(timezone.utc) - timedelta(hours=24))
        ).order_by(RiskIndex.timestamp.asc()).all()
        cri_values = [float(r.cri_score) for r in history]

        zscore_engine = get_zscore()
        zscore_result = zscore_engine.compute(cri_values)
        ema_engine = get_cri_ema()
        ema_engine.reset()
        ema_values = [ema_engine.smooth(v) for v in cri_values]
        decay_engine = get_decay_weights()
        for r in history[-5:]:
            decay_engine.record_update("GSPI")
        decay_report = decay_engine.get_decay_report()
        effective_weights = decay_engine.get_effective_weights()

        return {
            "status": "success",
            "z_score": zscore_result,
            "ema": {"current": ema_values[-1] if ema_values else None, "last_24h": ema_values, "alpha": 0.3},
            "decay": {"report": decay_report, "effective_weights": effective_weights, "rate_per_hour": "5%"},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
