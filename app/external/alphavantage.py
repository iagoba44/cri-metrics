"""Cliente REAL para Alpha Vantage API.
Obtiene earnings/income statement de NVIDIA como proxy
de salud financiera del sector IA.
Requiere API key gratuita: https://www.alphavantage.co/support/#api-key
"""
from datetime import datetime, timezone
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)

class AlphaVantageClient:
    """Cliente para Alpha Vantage (gratuito: 25 requests/día)."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        from app.config import get_settings
        self.api_key = get_settings().ALPHAVANTAGE_KEY

    def get_earnings(self, symbol: str = "NVDA") -> Optional[dict]:
        """Obtiene último earnings report."""
        if not self.api_key:
            logger.warning("[AlphaVantage] No API key. Set ALPHAVANTAGE_KEY env var.")
            return None
        
        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "function": "INCOME_STATEMENT",
                    "symbol": symbol,
                    "apikey": self.api_key,
                },
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"[AlphaVantage] Error: {e}")
            return None

    def compute_ltcr_proxy(self) -> Optional[float]:
        """
        Proxy de LTCR usando crecimiento revenue de NVDA.
        
        Si revenue crece >20% QoQ = confianza alta = LTCR bajo
        Si revenue cae = desconfianza = LTCR alto
        """
        data = self.get_earnings("NVDA")
        if not data or "quarterlyReports" not in data:
            return None
        
        reports = data["quarterlyReports"]
        if len(reports) < 2:
            return None
        
        try:
            latest = float(reports[0].get("totalRevenue", 0))
            previous = float(reports[1].get("totalRevenue", 0))
            if previous <= 0:
                return None
            
            growth = ((latest - previous) / previous) * 100
            
            # Mapear growth a LTCR (inverso: más crecimiento = menos riesgo)
            if growth >= 20:
                return 10.0
            elif growth <= -20:
                return 90.0
            else:
                return round(90.0 - ((growth + 20) / 40) * 80.0, 2)
        except Exception as e:
            logger.error(f"[AlphaVantage] Parse error: {e}")
            return None
    
    def compute_tmi_component(self) -> Optional[float]:
        """
        Componente TMI: AI Infrastructure Revenue.
        Usa crecimiento revenue NVDA como proxy de temperatura del sector IA.
        
        Revenue creciendo fuerte = mercado caliente (score alto)
        Revenue estancado/cayendo = mercado frio (score bajo)
        """
        data = self.get_earnings("NVDA")
        if not data or "quarterlyReports" not in data:
            return None
        
        reports = data["quarterlyReports"]
        if len(reports) < 2:
            return None
        
        try:
            latest = float(reports[0].get("totalRevenue", 0))
            previous = float(reports[1].get("totalRevenue", 0))
            if previous <= 0:
                return None
            
            growth = ((latest - previous) / previous) * 100
            
            # Mapear growth a score 0-100
            # -20% -> 0, 0% -> 50, +50% -> 100
            score = 50.0 + (growth * 2.5)
            return round(max(0.0, min(100.0, score)), 2)
        except Exception as e:
            logger.error(f"[AlphaVantage] TMI parse error: {e}")
            return None
