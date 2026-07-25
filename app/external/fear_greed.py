"""Cliente REAL para Alternative.me Fear & Greed Index.
API pública gratuita, sin autenticación.
https://alternative.me/crypto/fear-and-greed-index/
"""
from datetime import datetime, timezone
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)

class FearGreedClient:
    """Cliente para Fear & Greed Index de Alternative.me."""

    BASE_URL = "https://api.alternative.me/fng"

    def get_index(self, limit: int = 1) -> Optional[dict]:
        """Obtiene el índice Fear & Greed actual.
        
        Retorna dict con: value (0-100), value_classification (Extreme Fear/Fear/Neutral/Greed/Extreme Greed)
        """
        try:
            response = requests.get(
                f"{self.BASE_URL}/",
                params={"limit": limit},
                timeout=15,
                headers={"User-Agent": "CRI-Metrics-Bot/1.0"}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("data"):
                return data["data"][0]
            return None
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            return None

    def compute_tmi_component(self) -> Optional[float]:
        """
        Componente TMI: invertir Fear & Greed.
        
        Lógica:
        - Fear & Greed = 0 (Extreme Fear) -> TMI frío (bajo)
        - Fear & Greed = 100 (Extreme Greed) -> TMI caliente (alto)
        
        Invertimos para que coincida con temperatura:
        - Mercado con miedo = frío = TMI bajo
        - Mercado con codicia = caliente = TMI alto
        
        Retorna: 0-100 donde mayor = mercado más caliente.
        """
        data = self.get_index()
        if not data:
            return None
        
        try:
            value = float(data.get("value", 0))
            # El índice ya es 0-100 donde 100 = codicia extrema
            # Esto mapea directamente a temperatura
            return round(value, 2)
        except Exception as e:
            logger.error(f"Error parsing Fear & Greed: {e}")
            return None
