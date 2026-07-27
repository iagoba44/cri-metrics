"""Cliente REAL para CoinGecko API (gratuita).
Usa capitalizacion y volumen crypto como proxy de CFBR (Cloud Free-Burn Rate).
La salud del mercado crypto esta altamente correlacionada con la demanda de GPU cloud.
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
import logging
from app.services.cache import cached

logger = logging.getLogger(__name__)

class CoinGeckoClient:
    """Cliente para CoinGecko Demo API (sin auth, rate limit 10-30 req/min)."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    def get_market_data(self) -> Optional[Dict]:
        """Obtiene datos globales del mercado crypto."""
        url = f"{self.BASE_URL}/global"
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching CoinGecko global data: {e}")
            return None

    def get_coin_data(self, coin_id: str = "bitcoin") -> Optional[Dict]:
        """Obtiene datos de una moneda especifica."""
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {"localization": "false", "tickers": "false", "community_data": "false", "developer_data": "false"}
        try:
            response = requests.get(url, timeout=15, params=params, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching CoinGecko coin data: {e}")
            return None

    def compute_cfbr_proxy(self) -> Optional[float]:
        """
        Calcula proxy de CFBR (Cloud Free-Burn Rate).
        
        Logica:
        - El mercado crypto es un proxy fuerte de demanda GPU.
        - Si BTC/ETH suben mucho, los neoclouds queman capital para comprar GPUs.
        - Si caen fuerte, los neoclouds estan en distress (free-burn extremo).
        - Usamos volatilidad + market cap change como proxy.
        
        Retorna: indice 0-100 donde 100 = maxima quema/distress.
        """
        global_data = self.get_market_data()
        if not global_data:
            return None

        try:
            data = global_data.get("data", {})
            market_cap_change = data.get("market_cap_change_percentage_24h_usd", 0)
            
            # Si el market cap cae >10% en 24h, asumimos distress alto = CFBR alto
            # Si sube >10%, asumimos expansion agresiva = quema de capital
            # Volatilidad extrema en cualquier direccion = riesgo operativo
            
            cfbr = abs(market_cap_change) * 2  # Amplificamos
            # Cap a 0-100
            cfbr = max(0.0, min(100.0, cfbr))
            
            logger.info(f"[CoinGecko CFBR] market_cap_change_24h={market_cap_change:.2f}%, "
                        f"cfbr_proxy={cfbr:.2f}")
            return round(cfbr, 2)
        except Exception as e:
            logger.error(f"Error computing CFBR proxy: {e}")
            return None

    @cached(ttl=120)
    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para CFBR."""
        records = []
        ts = datetime.now(timezone.utc)

        cfbr = self.compute_cfbr_proxy()
        if cfbr is not None:
            records.append({
                "kpi_code": "CFBR",
                "raw_value": cfbr,
                "timestamp": ts,
                "data_source": "COINGECKO",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = CoinGeckoClient()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
