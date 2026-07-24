"""Cliente para datos macroeconomicos de la FRED API (Federal Reserve).
Usa datos de produccion industrial y capacidad utilizada como proxy macro.
FRED API key gratuita disponible en https://fred.stlouisfed.org/docs/api/api_key.html
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
import logging

logger = logging.getLogger(__name__)

class FREDClient:
    """Cliente para FRED API - datos macroeconomicos."""

    BASE_URL = "https://api.stlouisfed.org/fred"
    # API key demo (limitada). Reemplazar con tu propia key en produccion.
    API_KEY = "your_fred_api_key_here"

    def get_latest_observation(self, series_id: str) -> Optional[float]:
        """Obtiene la observacion mas reciente de una serie FRED."""
        url = f"{self.BASE_URL}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }
        try:
            response = requests.get(url, timeout=15, params=params)
            response.raise_for_status()
            data = response.json()
            obs = data.get("observations", [])
            if obs:
                val = obs[0].get("value")
                if val and val != ".":
                    return float(val)
            return None
        except Exception as e:
            logger.error(f"Error fetching FRED series {series_id}: {e}")
            return None

    def compute_macro_proxy(self) -> Optional[float]:
        """
        Usa capacidad de utilizacion industrial (TCU) como proxy macro.
        
        TCU < 75% = recesion / sobreoferta = riesgo alto
        TCU > 80% = expansion / demanda alta = riesgo bajo
        
        Retorna: indice 0-100 invertido de capacidad utilizada.
        """
        tcu = self.get_latest_observation("TCU")  # Total Capacity Utilization
        if tcu is None:
            return None

        # Invertir: menor capacidad = mayor riesgo
        # TCU 100% = score 0, TCU 70% = score 100
        score = ((100.0 - tcu) / 30.0) * 100
        score = max(0.0, min(100.0, score))

        logger.info(f"[FRED Macro] TCU={tcu:.2f}%, ltcr_proxy={score:.2f}")
        return round(score, 2)

    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para LTCR (macro proxy)."""
        records = []
        ts = datetime.now(timezone.utc)

        macro = self.compute_macro_proxy()
        if macro is not None:
            records.append({
                "kpi_code": "LTCR",
                "raw_value": macro,
                "timestamp": ts,
                "data_source": "FRED_MACRO",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = FREDClient()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
