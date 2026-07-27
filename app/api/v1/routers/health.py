from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import HealthResponse
from app.models import RiskIndex, TelemetryRecord
from datetime import datetime, timedelta, timezone
import asyncio
import json

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/events")
async def event_stream(db: Session = Depends(get_db)):
    """SSE stream con actualizaciones de CRI cada 5 segundos."""
    async def generate():
        while True:
            try:
                latest = db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
                if latest:
                    data = {
                        "cri_score": float(latest.cri_score),
                        "zone": latest.risk_zone,
                        "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(5)
            except Exception:
                await asyncio.sleep(5)
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/source-metrics")
def get_source_metrics(db: Session = Depends(get_db)):
    """Metricas de salud por fuente: tasa de exito, latencia, ultima actualizacion."""
    sources = {}
    rows = db.query(TelemetryRecord).all()
    for r in rows:
        source = r.data_source or "UNKNOWN"
        if source not in sources:
            sources[source] = {"count": 0, "last_ts": None}
        sources[source]["count"] += 1
        if sources[source]["last_ts"] is None or r.timestamp > sources[source]["last_ts"]:
            sources[source]["last_ts"] = r.timestamp

    now = datetime.now(timezone.utc)
    result = []
    for name, data in sorted(sources.items(), key=lambda x: -x[1]["count"]):
        ts = data["last_ts"]
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_seconds = (now - ts).total_seconds() if ts else 999999
        result.append({
            "source": name,
            "records": data["count"],
            "last_update": ts.isoformat() if ts else None,
            "age_seconds": round(age_seconds, 0),
            "status": "ACTIVE" if age_seconds < 3600 else "STALE" if age_seconds < 86400 else "OFFLINE",
        })

    return {"status": "success", "metrics": result}


@router.get("/db-status")
def get_db_status():
    """Estado de la conexion a base de datos."""
    from app.database import check_db_connection
    result = check_db_connection()
    return {"status": "success", "data": result}
