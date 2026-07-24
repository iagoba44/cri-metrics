"""Cliente REAL basado en Yahoo Finance (datos publicos).
Extrae volatilidad de acciones de infraestructura IA como proxy de LTCR.

Logica:
- Si NVDA, SMCI, DELL caen fuerte = mercado desconfia de contratos a largo plazo = LTCR alto (riesgo)
- Si suben estable = confianza en contratos = LTCR bajo

Empresas proxy:
- NVDA: GPUs / data center
- SMCI: Servidores AI
- DELL: Infraestructura empresarial
- AMD: CPUs/GPUs
"""
from datetime import datetime
from typing import List, Dict, Optional
import requests
import logging
import time

logger = logging.getLogger(__name__)

TICKERS = ["NVDA", "SMCI", "DELL", "AMD", "INTC"]

class YahooFinanceClient:
    """Cliente para datos de mercado de acciones IA."""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def get_stock_change(self, ticker: str) -> Optional[float]:
        """Obtiene cambio porcentual del dia para un ticker."""
        url = f"{self.BASE_URL}/{ticker}"
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            })
            response.raise_for_status()
            data = response.json()

            chart = data.get("chart", {})
            result = chart.get("result", [])
            if not result:
                return None

            meta = result[0].get("meta", {})
            prev_close = meta.get("previousClose") or meta.get("chartPreviousClose", 0)
            curr_price = meta.get("regularMarketPrice", 0)

            if prev_close and curr_price:
                change = ((curr_price - prev_close) / prev_close) * 100
                return change
            return None
        except Exception as e:
            logger.warning(f"Error fetching Yahoo Finance for {ticker}: {e}")
            return None

    def compute_ltcr_proxy(self) -> Optional[float]:
        """
        Calcula proxy de LTCR (Long-Term Contract Ratio).
        
        Logica inversa:
        - Si las acciones de infra IA caen fuerte = compresion de contratos = LTCR alto (riesgo)
        - Si suben fuerte = expansion = tambien puede ser riesgo de sobrecontratacion
        - Usamos volatilidad absoluta como proxy de inestabilidad en contratos
        """
        changes = []
        for ticker in TICKERS:
            change = self.get_stock_change(ticker)
            if change is not None:
                changes.append(change)
                logger.info(f"[Yahoo Finance] {ticker}: {change:+.2f}%")
            time.sleep(1.5)  # respetar rate limits de Yahoo

        if not changes:
            return None

        avg_change = sum(changes) / len(changes)
        # Volatilidad = desviacion del 0
        volatility = abs(avg_change)
        
        # Escalar a 0-100: 0% diario = 0, 5% diario = 50, 10%+ = 100
        ltcr = (volatility / 10.0) * 100
        ltcr = max(0.0, min(100.0, ltcr))

        logger.info(f"[Yahoo Finance LTCR] avg_change={avg_change:.2f}%, "
                    f"volatility={volatility:.2f}%, ltcr_proxy={ltcr:.2f}")

        return round(ltcr, 2)

    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para LTCR."""
        records = []
        ts = datetime.utcnow()

        ltcr = self.compute_ltcr_proxy()
        if ltcr is not None:
            records.append({
                "kpi_code": "LTCR",
                "raw_value": ltcr,
                "timestamp": ts,
                "data_source": "YAHOO_FINANCE",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = YahooFinanceClient()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
