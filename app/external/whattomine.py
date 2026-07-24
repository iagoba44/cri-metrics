"""Scraper REAL para WhatToMine.com.
Extrae rentabilidad de GPUs como proxy de demanda hardware (SHPD).
Si la rentabilidad minera cae = demanda GPU baja = deflacion de precios.
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional
import requests
import re
import logging

logger = logging.getLogger(__name__)

class WhatToMineScraper:
    """Scraper para datos de rentabilidad GPU de WhatToMine."""

    URL = "https://whattomine.com/gpus"

    def scrape_gpu_profitability(self) -> Optional[float]:
        """
        Extrae rentabilidad promedio de GPUs desde WhatToMine.
        Retorna: indice de deflacion (0-100) donde mayor = mayor caida de demanda.
        
        VALIDACION v2:
        - Verifica que los numeros extraidos esten en rango razonable (5% - 5000%)
        - Si el promedio es < 5% o > 5000%, descarta como ruido/anomalia
        - Si falla, retorna None para que el pipeline use Lambda Labs como fallback
        """
        try:
            response = requests.get(self.URL, timeout=20, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            response.raise_for_status()
            html = response.text

            # Buscar patrones de rentabilidad en la tabla
            # Ejemplo: "1472% | 1354%" o similares
            matches = re.findall(r'(\d+)%\s*\|\s*(\d+)%', html)
            if not matches:
                # Fallback: buscar cualquier numero seguido de %
                matches = re.findall(r'(\d+)%', html)
                profits = [int(m) for m in matches if 10 < int(m) < 10000]
            else:
                profits = []
                for m in matches:
                    profits.append(int(m[0]))
                    profits.append(int(m[1]))

            if not profits:
                logger.warning("[WTM] No se encontraron datos de rentabilidad")
                return None

            # VALIDACION: descartar outliers
            valid_profits = [p for p in profits if 5 < p < 5000]
            if len(valid_profits) < 3:
                logger.warning(f"[WTM] Insuficientes datos validos ({len(valid_profits)}). Posible bloqueo/cambio HTML.")
                return None

            avg_profit = sum(valid_profits) / len(valid_profits)
            
            # SHPD proxy: si rentabilidad promedio < 500%, demanda baja = deflacion
            # Baseline de rentabilidad "saludable" = 1000%
            baseline = 1000.0
            if avg_profit >= baseline:
                deflation = 0.0
            else:
                deflation = ((baseline - avg_profit) / baseline) * 100

            logger.info(f"[WhatToMine SHPD] avg_profitability={avg_profit:.0f}%, samples={len(valid_profits)}, "
                        f"deflation_proxy={deflation:.2f}% (baseline={baseline})")
            
            return round(deflation, 2)

        except Exception as e:
            logger.error(f"[WhatToMine] Error scraping: {e}")
            return None

    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para SHPD."""
        records = []
        ts = datetime.now(timezone.utc)

        shpd = self.scrape_gpu_profitability()
        if shpd is not None:
            records.append({
                "kpi_code": "SHPD",
                "raw_value": shpd,
                "timestamp": ts,
                "data_source": "WHATTOMINE_SCRAPER",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = WhatToMineScraper()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
