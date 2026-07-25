"""Cliente REAL para HackerNews Algolia API.
Cuenta stories sobre IA/GPU en las últimas 24h como proxy
de interés técnico de la comunidad developer.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)

class HackerNewsClient:
    """Cliente para HN Algolia search API."""

    BASE_URL = "https://hn.algolia.com/api/v1/search_by_date"

    def get_stories(self, query: str = "AI GPU", hours: int = 24) -> int:
        """
        Cuenta stories HN que mencionan IA/GPU en las últimas N horas.
        
        Baseline observado: ~50-100 stories/24h en interés normal.
        Durante boom (ChatGPT launch): 500+/24h.
        """
        # Timestamp Unix de hace N horas
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_ts = int(cutoff.timestamp())
        
        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "query": query,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff_ts}",
                    "hitsPerPage": 100,
                },
                timeout=15,
                headers={"User-Agent": "CRI-Metrics-Bot/1.0"},
            )
            response.raise_for_status()
            data = response.json()
            count = data.get("nbHits", 0)
            logger.info(f"[HN] Stories '{query}' últimas {hours}h: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Error fetching HN: {e}")
            return 0

    def compute_tmi_component(self) -> Optional[float]:
        """
        Componente TMI: actividad HN sobre IA/GPU.
        
        Baseline: 60 stories/24h = normal (TMI 50)
        Máximo: 400 stories/24h = boom (TMI 100)
        Mínimo: 10 stories/24h = invierno (TMI 0)
        """
        count = self.get_stories("AI GPU", hours=24)
        if count == 0:
            return None
        
        baseline = 60.0
        ratio = count / baseline
        
        if ratio >= 6.67:
            tmi = 100.0
        elif ratio <= 0.167:
            tmi = 0.0
        else:
            tmi = ((ratio - 0.167) / (6.67 - 0.167)) * 100.0
        
        return round(max(0.0, min(100.0, tmi)), 2)
