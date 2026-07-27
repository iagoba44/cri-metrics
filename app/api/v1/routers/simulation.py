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
