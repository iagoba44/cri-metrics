"""Cliente REAL para Binance API (publica, sin auth).
Extrae datos de mercado crypto como proxy adicional de CFBR (volatilidad)
y como proxy de demanda GPU (volumen ETH = demanda de GPUs para minado/IA).
"""
from datetime import datetime
from typing import List, Dict, Optional
import requests
import logging

logger = logging.getLogger(__name__)

class BinanceClient:
    """Cliente para Binance public API (rate limit 1200 req/min)."""

    BASE_URL = "https://api.binance.com/api/v3"

    def get_ticker(self, symbol: str = "ETHUSDT") -> Optional[Dict]:
        """Obtiene ticker de 24h para un par crypto."""
        url = f"{self.BASE_URL}/ticker/24hr"
        params = {"symbol": symbol}
        try:
            response = requests.get(url, timeout=10, params=params, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Binance ticker: {e}")
            return None

    def compute_cfbr_volatility(self) -> Optional[float]:
        """
        Calcula CFBR proxy usando volatilidad ETH/USDT.
        
        Logica:
        - ETH es la moneda minada con GPU. Su volatilidad refleja
          la salud del mercado de GPUs.
        - priceChangePercent alto en cualquier direccion = riesgo operativo.
        """
        data = self.get_ticker("ETHUSDT")
        if not data:
            return None

        try:
            change_pct = float(data.get("priceChangePercent", 0))
            volume = float(data.get("volume", 0))
            
            # Normalizar volatilidad a escala 0-100
            # |change| > 10% = score 100, |change| = 0% = score 0
            cfbr = abs(change_pct) * 5  # multiplicador para escalar
            cfbr = max(0.0, min(100.0, cfbr))
            
            logger.info(f"[Binance CFBR] ETH 24h change={change_pct:.2f}%, "
                        f"volume={volume:.0f}, cfbr_proxy={cfbr:.2f}")
            return round(cfbr, 2)
        except Exception as e:
            logger.error(f"Error computing Binance CFBR: {e}")
            return None

    def compute_gpu_demand_proxy(self) -> Optional[float]:
        """
        Proxy de demanda GPU: volumen de trading ETH en 24h.
        
        Logica:
        - Alto volumen = alta actividad minera/comercial = alta demanda GPU
        - Bajo volumen = baja demanda = sobreoferta = deflacion
        
        Retorna: indice 0-100 de sobreoferta (inverso del volumen).
        """
        data = self.get_ticker("ETHUSDT")
        if not data:
            return None

        try:
            volume = float(data.get("volume", 0))
            # Baseline: 500,000 ETH/24h = demanda normal
            baseline = 500000.0
            if volume >= baseline:
                overcapacity = 0.0
            else:
                overcapacity = ((baseline - volume) / baseline) * 100

            logger.info(f"[Binance Demand] ETH volume={volume:.0f}/24h, "
                        f"overcapacity_proxy={overcapacity:.2f}%")
            return round(overcapacity, 2)
        except Exception as e:
            logger.error(f"Error computing GPU demand proxy: {e}")
            return None

    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para CFBR."""
        records = []
        ts = datetime.utcnow()

        cfbr = self.compute_cfbr_volatility()
        if cfbr is not None:
            records.append({
                "kpi_code": "CFBR",
                "raw_value": cfbr,
                "timestamp": ts,
                "data_source": "BINANCE",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = BinanceClient()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
