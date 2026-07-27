from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import CalculateCRIResponse, RiskIndexSchema
from app.services.calculator import CRICalculator
from app.models import RiskIndex, TMISnapshot
from app.scenarios import get_mode_state, SCENARIOS, get_zone
from app.services.alerts import get_alert_service
from app.services.repository import RiskIndexRepository, TMIRepository
from datetime import datetime, timezone

router = APIRouter()


@router.post("/calculate-cri", response_model=CalculateCRIResponse)
def calculate_cri(db: Session = Depends(get_db)):
    mode_state = get_mode_state()

    try:
        if mode_state.mode == mode_state.MODE_SIMULATION and mode_state.active_scenario:
            scenario = SCENARIOS[mode_state.active_scenario]
            params = scenario["params"]

            weights = {"GSPI": 0.25, "SHPD": 0.15, "LTCR": 0.20, "CFBR": 0.20, "UOR": 0.20}
            cri_score = round(sum(params[k] * weights[k] for k in weights), 2)
            risk_zone = get_zone(cri_score)
            alerts_triggered = risk_zone == "CRITICAL"

            component_details = {}
            colors = {"GSPI": "#f85149", "SHPD": "#d29922", "LTCR": "#58a6ff", "CFBR": "#a371f7", "UOR": "#3fb950"}
            for kpi, raw_val in params.items():
                component_details[kpi] = {
                    "normalized_score": raw_val,
                    "raw_value": raw_val,
                    "weight": weights[kpi],
                    "color": colors.get(kpi),
                }

            risk_index = RiskIndex(
                cri_score=cri_score,
                risk_zone=risk_zone,
                alerts_triggered="true" if alerts_triggered else "false",
                timestamp=datetime.now(timezone.utc),
            )
            repo = RiskIndexRepository(db)
            risk_index = repo.add(risk_index)

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
            calculator = CRICalculator(db)
            risk_index, metadata = calculator.calculate()

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


@router.get("/latest-cri", response_model=RiskIndexSchema)
def get_latest_cri(db: Session = Depends(get_db)):
    repo = RiskIndexRepository(db)
    latest = repo.get_latest()
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


@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    try:
        cri_repo = RiskIndexRepository(db)
        tmi_repo = TMIRepository(db)

        cri_history = cri_repo.get_history(24, hours=True)
        tmi_history = tmi_repo.get_history(hours=24)

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


@router.get("/alert-log")
def get_alert_log(db: Session = Depends(get_db)):
    """Ultimos 20 eventos de alerta desde risk_indices."""
    alerts = (
        db.query(RiskIndex)
        .filter(RiskIndex.alerts_triggered == "true")
        .order_by(RiskIndex.timestamp.desc())
        .limit(20)
        .all()
    )
    return {
        "status": "success",
        "alerts": [
            {
                "timestamp": a.timestamp.isoformat(),
                "cri_score": float(a.cri_score),
                "zone": a.risk_zone,
            }
            for a in alerts
        ]
    }
