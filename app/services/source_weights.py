"""
Sistema de ponderación de fuentes para el pipeline de ingesta.
Permite asignar pesos diferentes a cada fuente al calcular el valor consenso.
"""
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

# Pesos por defecto para cada fuente (0-1, donde 1 = máxima confianza)
# Las fuentes con peso más alto tienen más influencia en el promedio ponderado.
DEFAULT_SOURCE_WEIGHTS = {
    # GSPI - Precios spot GPU
    "VAST_AI_LIVE": 1.0,      # Fuente principal, API directa
    
    # SHPD - Hardware deflation / demanda
    "WHATTOMINE_SCRAPER": 0.8,  # Buen proxy pero scraping puede fallar
    "LAMBDALABS_SCRAPER": 0.3,  # Scraping difícil, web bloquea bots
    "NICEHASH": 0.9,            # API pública robusta, datos reales de hashrate
    "HUGGINGFACE": 0.4,         # Proxy indirecto (tamaño modelos), menos fiable
    
    # LTCR - Contratos largo plazo
    "YAHOO_FINANCE": 1.0,       # API estable, datos reales de mercado
    "FRED": 0.5,                # Requiere API key, menos prioridad
    
    # CFBR - Capital / volatilidad
    "COINGECKO": 1.0,           # API pública gratuita, datos globales crypto
    "BINANCE": 0.9,             # API pública, datos ticker precisos
    "DEFILLAMA": 0.7,           # TVL como proxy macro, buen indicador
    "DEFILLAMA_VOL": 0.4,       # Volatilidad entre chains, más ruido
    
    # UOR - Ocupación / infrautilización
    "VAST_AI_LIVE": 1.0,        # Datos directos de marketplace
    "NICEHASH": 0.7,            # Hashrate global como proxy indirecto
    "HUGGINGFACE": 0.3,         # Downloads como proxy muy indirecto
}

# Normalizar pesos por KPI: para cada KPI, los pesos deben sumar ~1.0
def compute_weighted_average(records: List[Dict], source_weights: Dict[str, float] = None) -> tuple:
    """
    Calcula promedio ponderado de múltiples fuentes para un KPI.
    
    Args:
        records: Lista de dicts con 'raw_value' y 'data_source'
        source_weights: Dict de {source_name: weight}. Si None, usa DEFAULT_SOURCE_WEIGHTS.
    
    Returns:
        (weighted_avg, used_sources, total_weight)
    """
    if source_weights is None:
        source_weights = DEFAULT_SOURCE_WEIGHTS
    
    values = []
    weights = []
    used = []
    
    for rec in records:
        source = rec.get("data_source", "UNKNOWN")
        weight = source_weights.get(source, 0.5)  # Default 0.5 si no está catalogada
        val = rec.get("raw_value")
        
        if val is None:
            continue
        
        values.append(val)
        weights.append(weight)
        used.append(source)
    
    if not values:
        return None, [], 0
    
    # Promedio ponderado
    total_weight = sum(weights)
    if total_weight == 0:
        return None, used, 0
    
    weighted_avg = sum(v * w for v, w in zip(values, weights)) / total_weight
    
    return round(weighted_avg, 2), used, round(total_weight, 2)

# Configuración de umbrales de confianza por KPI
KPI_CONFIDENCE_THRESHOLDS = {
    "GSPI": {"min_sources": 1, "min_total_weight": 0.8},
    "SHPD": {"min_sources": 2, "min_total_weight": 1.0},
    "LTCR": {"min_sources": 1, "min_total_weight": 0.8},
    "CFBR": {"min_sources": 2, "min_total_weight": 1.5},
    "UOR": {"min_sources": 2, "min_total_weight": 1.0},
}

def has_enough_confidence(kpi: str, num_sources: int, total_weight: float) -> bool:
    """Verifica si hay suficientes fuentes/confianza para un KPI."""
    thresholds = KPI_CONFIDENCE_THRESHOLDS.get(kpi, {"min_sources": 1, "min_total_weight": 0.5})
    return num_sources >= thresholds["min_sources"] and total_weight >= thresholds["min_total_weight"]
