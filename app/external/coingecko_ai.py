"""Cliente REAL para CoinGecko - AI tokens performance.
Extiende CoinGecko para obtener rendimiento de tokens
de la categoría "artificial-intelligence" como proxy
de inversión/optimismo en proyectos IA.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict
import requests
import logging

logger = logging.getLogger(__name__)

class CoinGeckoAIClient:
    """Cliente para AI tokens en CoinGecko."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    def get_ai_tokens(self, limit: int = 10) -> Optional[List[Dict]]:
        """Obtiene tokens de la categoría AI ordenados por market cap."""
        url = f"{self.BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "category": "artificial-intelligence",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false",
        }
        try:
            response = requests.get(url, params=params, timeout=15, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching AI tokens: {e}")
            return None

    def compute_tmi_component(self) -> Optional[float]:
        """
        Componente TMI: performance promedio de AI tokens.
        
        Mide el optimismo/inversión en proyectos IA en crypto.
        
        Baseline: change_24h promedio = 0% -> TMI 50
        Todos subiendo +20% -> TMI 100 (euforia)
        Todos cayendo -20% -> TMI 0 (pánico)
        """
        tokens = self.get_ai_tokens(limit=10)
        if not tokens:
            return None

        changes = []
        for t in tokens:
            ch = t.get("price_change_percentage_24h")
            if ch is not None:
                changes.append(float(ch))

        if not changes:
            return None

        avg_change = sum(changes) / len(changes)
        
        # Mapear change promedio a TMI
        # +20% -> 100, 0% -> 50, -20% -> 0
        if avg_change >= 20.0:
            tmi = 100.0
        elif avg_change <= -20.0:
            tmi = 0.0
        else:
            tmi = 50.0 + (avg_change / 20.0) * 50.0
        
        return round(max(0.0, min(100.0, tmi)), 2)
