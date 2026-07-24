"""Configuracion centralizada del sistema CRI."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "CRI Metrics System"
    DATABASE_URL: str = "sqlite:///./cri_metrics.db"
    
    # Umbrales de alerta
    ALERT_THRESHOLD: float = 65.0
    
    # Ventana de frescura de datos (horas)
    DATA_FRESHNESS_HOURS: int = 24
    
    # Bounds para normalizacion Min-Max
    KPI_BOUNDS: dict = {
        "GSPI": {"min": 0.0, "max": 100.0},    # GPU Spot Price Index (% deflacion)
        "SHPD": {"min": 0.0, "max": 100.0},    # Server Hardware Price Deflation (%)
        "LTCR": {"min": 0.0, "max": 100.0},    # Long-Term Contract Ratio (%)
        "CFBR": {"min": 0.0, "max": 100.0},    # Cloud Free-Burn Rate (%)
        "UOR":  {"min": 0.0, "max": 100.0},    # Underutilization/Overcapacity Ratio (%)
    }
    
    # Pesos del indice CRI
    KPI_WEIGHTS: dict = {
        "GSPI": 0.25,
        "SHPD": 0.15,
        "LTCR": 0.20,
        "CFBR": 0.20,
        "UOR":  0.20,
    }
    
    # KPIs con formula inversa (mayor valor = mayor riesgo -> score 100)
    INVERSE_KPIS: list = ["GSPI", "LTCR"]
    
    # Webhook para alertas (opcional)
    ALERT_WEBHOOK_URL: str = ""
    
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings() -> Settings:
    return Settings()
