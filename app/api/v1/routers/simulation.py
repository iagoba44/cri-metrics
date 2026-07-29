from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.scenarios import get_mode_state, SCENARIOS, get_scenario_list
from .cri import calculate_cri

router = APIRouter()


@router.get("/scenarios")
def list_scenarios():
    return {
        "status": "success",
        "count": len(SCENARIOS),
        "scenarios": get_scenario_list(),
    }


@router.post("/simulate-scenario")
def simulate_scenario(payload: dict, db: Session = Depends(get_db)):
    scenario_id = payload.get("scenario_id")
    if not scenario_id:
        raise HTTPException(status_code=400, detail="scenario_id requerido")
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=400, detail=f"Escenario invalido: {scenario_id}")

    mode_state = get_mode_state()
    mode_state.set_scenario(scenario_id)
    return calculate_cri(db)


@router.post("/simulate-custom")
def simulate_custom(payload: dict, db: Session = Depends(get_db)):
    """Simula un escenario con parámetros KPI personalizados (What-If)."""
    params = payload.get("params")
    if not params:
        raise HTTPException(status_code=400, detail="Parámetros 'params' requeridos")

    weights = {"GSPI": 0.25, "SHPD": 0.15, "LTCR": 0.20, "CFBR": 0.20, "UOR": 0.20}
    validated_params = {}
    for k in weights:
        if k not in params:
            raise HTTPException(status_code=400, detail=f"Falta el parámetro KPI: {k}")
        try:
            val = float(params[k])
            if not (0 <= val <= 100):
                raise ValueError()
            validated_params[k] = val
        except ValueError:
            raise HTTPException(status_code=400, detail=f"El valor de {k} debe ser un número entre 0 y 100")

    SCENARIOS["custom"] = {
        "id": "custom",
        "name": "Personalizado",
        "description": "Escenario interactivo con parámetros personalizados",
        "icon": "🎛️",
        "color": "#a2c9ff",
        "params": validated_params
    }

    mode_state = get_mode_state()
    mode_state.set_scenario("custom")
    return calculate_cri(db)


@router.post("/simulate-critical")
def simulate_critical(db: Session = Depends(get_db)):
    mode_state = get_mode_state()
    mode_state.set_scenario("supply_crisis")

    return calculate_cri(db)


@router.get("/mode")
def get_mode():
    mode_state = get_mode_state()
    return {
        "status": "success",
        **mode_state.get_status(),
    }


@router.post("/mode")
def set_mode(payload: dict):
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


@router.get("/simulation-compare")
def compare_scenarios(scenario_a: str = "crypto_crash", scenario_b: str = "ai_utopia"):
    """Comparativa lado a lado de dos escenarios con todos sus KPIs."""
    from app.scenarios import get_zone, _preview_cri

    scenarios = {}
    for sid in [scenario_a, scenario_b]:
        s = SCENARIOS.get(sid)
        if not s:
            raise HTTPException(status_code=400, detail=f"Escenario no encontrado: {sid}")
        cri = _preview_cri(s["params"])
        kpi_detail = {}
        for kpi, val in s["params"].items():
            kpi_detail[kpi] = {
                "value": val,
                "bar_pct": val,  # % para barra visual
                "impact": "high" if abs(val - 50) > 30 else "medium" if abs(val - 50) > 15 else "low",
            }
        scenarios[sid] = {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "icon": s["icon"],
            "color": s["color"],
            "cri": cri,
            "zone": get_zone(cri),
            "kpis": kpi_detail,
        }

    return {"status": "success", "data": scenarios}
