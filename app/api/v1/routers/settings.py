from fastapi import APIRouter, Depends, HTTPException
from app.services.settings_store import load_settings, save_settings
from app.services.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("")
def get_settings(username: str = Depends(get_current_user)):
    return {
        "status": "success",
        "settings": load_settings()
    }

@router.post("")
def update_settings(payload: dict, username: str = Depends(get_current_user)):
    # Validate payload
    if "alert_threshold" not in payload or "channels" not in payload:
        raise HTTPException(status_code=400, detail="Estructura de configuración inválida")
    
    try:
        payload["alert_threshold"] = float(payload["alert_threshold"])
        if not (0 <= payload["alert_threshold"] <= 100):
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=400, detail="alert_threshold debe ser un número entre 0 y 100")
        
    save_settings(payload)
    
    # Update the global alert service configuration if active
    from app.services.alerts import get_alert_service
    get_alert_service().reload_settings()
    
    return {
        "status": "success",
        "message": "Configuración guardada exitosamente"
    }
