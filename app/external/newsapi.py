"""Cliente REAL para NewsAPI.
Busca noticias sobre data centers, GPUs, NVIDIA para medir
actividad/cobertura mediática del sector IA.
Requiere API key gratuita: https://newsapi.org/register
"""
from datetime import datetime, timezone
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)

class NewsAPIClient:
    """Cliente para NewsAPI (gratuito: 100 requests/día)."""

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self):
        from app.config import get_settings
        self.api_key = get_settings().NEWSAPI_KEY

    def get_news_count(self, query: str = "NVIDIA GPU data center", hours: int = 24) -> Optional[int]:
        """Cuenta noticias recientes sobre el tema."""
        if not self.api_key:
            logger.warning("[NewsAPI] No API key configured. Set NEWSAPI_KEY env var.")
            return None
        
        from datetime import timedelta
        from_date = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d")
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/everything",
                params={
                    "q": query,
                    "from": from_date,
                    "sortBy": "publishedAt",
                    "pageSize": 100,
                    "apiKey": self.api_key,
                },
                timeout=15,
                headers={"User-Agent": "CRI-Metrics-Bot/1.0"},
            )
            response.raise_for_status()
            data = response.json()
            count = data.get("totalResults", 0)
            logger.info(f"[NewsAPI] Articles found: {count}")
            return count
        except Exception as e:
            logger.error(f"[NewsAPI] Error: {e}")
            return None

    def compute_tmi_component(self) -> Optional[float]:
        """
        Componente TMI: cobertura mediática IA.
        
        Baseline: 50 artículos/24h = normal (TMI 50)
        >200 artículos = hype/boom (TMI 100)
        <10 artículos = frío (TMI 0)
        """
        count = self.get_news_count()
        if count is None:
            return None
        
        baseline = 50.0
        ratio = count / baseline
        
        if ratio >= 4.0:
            return 100.0
        elif ratio <= 0.2:
            return 0.0
        else:
            return round(((ratio - 0.2) / (4.0 - 0.2)) * 100.0, 2)
