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
    
    # API Keys para fuentes opcionales
    NEWSAPI_KEY: str = ""
    ALPHAVANTAGE_KEY: str = ""
    EIA_API_KEY: str = ""
    
    # API Keys para Consensus Diff (comité de IA)
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    
    # Umbral para alerta por divergencia semántica
    CONSENSUS_DIFF_THRESHOLD: float = 20.0
    
    # Configuración de news validator
    NEWS_SIMILARITY_THRESHOLD: float = 0.35
    
    # Base de datos
    DB_ENGINE: str = "sqlite"  # sqlite | postgres
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "cri_metrics"
    POSTGRES_USER: str = "cri"
    POSTGRES_PASSWORD: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth configuration
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    SECRET_KEY: str = "supersecretkeychangeinproduction"

    model_config = SettingsConfigDict(env_file=".env")

@lru_cache()
def get_settings() -> Settings:
    return Settings()
