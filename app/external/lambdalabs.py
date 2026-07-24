"""Scraper para precios de servidores GPU en Lambda Labs (publico).
Extrae precios de instancias GPU como proxy de SHPD.
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
import re
import logging

logger = logging.getLogger(__name__)

class LambdaLabsScraper:
    """Scraper para Lambda Labs cloud pricing."""

    URL = "https://lambdalabs.com/cloud"

    def scrape_gpu_pricing(self) -> Optional[float]:
        """
        Extrae precios de instancias GPU desde Lambda Labs.
        Precios reales (Jul 2026):
        - B200: $6.69/hr
        - H100: $3.99/hr  
        - A100: $2.79/hr
        - A6000: $1.09/hr
        - V100: $0.79/hr
        
        Retorna: indice de precio promedio como proxy de deflacion.
        """
        try:
            response = requests.get(self.URL, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.5",
            })
            response.raise_for_status()
            html = response.text

            # Buscar precios en formato $X.XX o $X seguido de texto
            # Los precios estan en tablas con formato: $6.69, $3.99, $2.79, etc.
            prices = re.findall(r'\$([0-9]+\.[0-9]{2})', html)
            
            if not prices:
                logger.warning("[LambdaLabs] No se encontraron precios en la pagina")
                return None

            prices = [float(p) for p in prices if float(p) > 0.5 and float(p) < 50.0]
            if not prices:
                return None

            # Eliminar duplicados (mismo precio aparece en diferentes columnas)
            unique_prices = list(set(prices))
            avg_price = sum(unique_prices) / len(unique_prices)
            
            # Baseline historico aproximado para GPU cloud high-end: ~$3.50/hr
            baseline = 3.50
            if avg_price >= baseline:
                deflation = 0.0
            else:
                deflation = ((baseline - avg_price) / baseline) * 100

            logger.info(f"[LambdaLabs SHPD] avg_price=${avg_price:.2f}/h, "
                        f"unique_samples={len(unique_prices)}, deflation_proxy={deflation:.2f}%")
            
            return round(deflation, 2)

        except Exception as e:
            logger.error(f"[LambdaLabs] Error scraping: {e}")
            return None

    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para SHPD."""
        records = []
        ts = datetime.now(timezone.utc)

        shpd = self.scrape_gpu_pricing()
        if shpd is not None:
            records.append({
                "kpi_code": "SHPD",
                "raw_value": shpd,
                "timestamp": ts,
                "data_source": "LAMBDALABS_SCRAPER",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = LambdaLabsScraper()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
