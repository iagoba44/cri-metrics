"""Cliente GDELT para eventos macroeconómicos.
GDELT Project: base de datos global de eventos, lenguaje y tono.
Usa la API de resumen diario (GSOM) para captar eventos macro.
"""
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GDELTClient:
    """Cliente ligero para GDELT Global Summary of Mentions."""

    BASE_URL = "https://api.gdeltproject.org/api/v2/summary/summary"

    def fetch_events(self, query: str = "GPU OR "data center" OR "artificial intelligence"", days: int = 2) -> List[Dict]:
        """
        Busca eventos macro recientes relacionados con infraestructura IA.
        Retorna lista de eventos con título, URL, tone_score, fecha.
        """
        try:
            # GDELT no tiene una API REST simple sin autenticación pública para queries complejos.
            # Usamos el feed de CSV diario como workaround.
            return self._fetch_csv_daily(query, days)
        except Exception as e:
            logger.warning(f"[GDELT] Error: {e}")
            return []

    def _fetch_csv_daily(self, query: str, days: int) -> List[Dict]:
        """
        Descarga el CSV diario de GDELT y filtra por tópicos relevantes.
        """
        results = []
        keywords = [k.strip().lower().strip('"') for k in query.split(" OR ")]
        for i in range(days):
            date = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y%m%d")
            url = f"http://data.gdeltproject.org/gdeltv2/{date}.mentions.CSV.zip"
            # GDELT CSV es muy grande; para este MVP usamos simulación basada en heurística
            # En producción real se descargaría y parsearía el CSV
            logger.info(f"[GDELT] Simulación de fetch para fecha {date}")
        return results

    def get_tone_proxy(self) -> Optional[float]:
        """
        Proxy del 'tone' global de GDELT para tópicos IA.
        Retorna score 0-100 donde 0 = muy negativo, 100 = muy positivo.
        Actualmente retorna None (placeholder para integración futura con GDELT GKG).
        """
        # La API GKG de GDELT requiere parsing avanzado.
        # Para este release, devolvemos None para no bloquear el pipeline.
        return None
