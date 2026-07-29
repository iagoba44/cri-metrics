"""Cliente REAL para la API de la EIA (U.S. Energy Information Administration).
Obtiene los precios de la electricidad para data centers (sector comercial/industrial).
Requiere API key gratuita: https://www.eia.gov/opendata/register.php
"""
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class EIAClient:
    BASE_URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"

    def __init__(self):
        from app.config import get_settings
        settings = get_settings()
        self.api_key = getattr(settings, "EIA_API_KEY", "")

    def get_electricity_price(self) -> Optional[float]:
        """Obtiene el precio promedio de la electricidad industrial reciente en US."""
        if not self.api_key:
            logger.warning("[EIA] No API key configured. Set EIA_API_KEY env var.")
            return None
        
        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "api_key": self.api_key,
                    "frequency": "monthly",
                    "data[0]": "price",
                    "facets[sectorid][]": "IND", # Sector Industrial
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length": 1
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("response", {}).get("data", [])
            if results:
                price = float(results[0].get("price", 0.0)) # en centavos por kWh
                logger.info(f"[EIA] Recent industrial electricity price: {price} cents/kWh")
                return price
            return None
        except Exception as e:
            logger.error(f"[EIA] Error fetching electricity price: {e}")
            return None

    def compute_cfbr_factor(self) -> Optional[float]:
        """
        Calcula un factor de riesgo (0-100) basado en el precio de la electricidad.
        Baseline histórico: 7.5 centavos/kWh = riesgo medio (50)
        >10 centavos/kWh = alto riesgo de burn-rate por energía (100)
        <5 centavos/kWh = bajo riesgo (0)
        """
        price = self.get_electricity_price()
        if price is None:
            return None
        
        if price >= 10.0:
            return 100.0
        elif price <= 5.0:
            return 0.0
        else:
            return round(((price - 5.0) / 5.0) * 100.0, 2)

    def fetch(self) -> list:
        """Pipeline de ingesta: retorna registros para CFBR."""
        from datetime import datetime, timezone
        records = []
        ts = datetime.now(timezone.utc)
        
        cfbr = self.compute_cfbr_factor()
        if cfbr is not None:
            records.append({
                "kpi_code": "CFBR",
                "raw_value": cfbr,
                "timestamp": ts,
                "data_source": "EIA_GOV",
            })
        return records
