"""Cliente REAL para Vast.ai - API publica de bundles.
Extrae precios spot GPU (GSPI) y ratio de ocupacion (UOR).
"""
from datetime import datetime
from typing import List, Dict, Optional
import requests
import logging

logger = logging.getLogger(__name__)

# GPU models que nos interesan para el indice
TARGET_GPUS = [
    "RTX 4090", "RTX 3090", "RTX 3080", "RTX 3090Ti",
    "RTX 5080", "RTX 5070 Ti", "RTX 5090",
    "A100", "H100", "A6000", "A5000", "A4000",
    "RTX A6000", "RTX A5000", "RTX A4000",
]

class VastAIClient:
    """Cliente para datos reales de Vast.ai marketplace."""

    BASE_URL = "https://vast.ai/api/v0"

    def fetch_bundles(self, gpu_name: Optional[str] = None) -> List[Dict]:
        """Obtiene bundles activos del marketplace.
        
        Si gpu_name es None, trae TODOS los bundles disponibles.
        """
        url = f"{self.BASE_URL}/bundles"
        params = {}
        if gpu_name:
            # El endpoint no tiene filtro directo por GPU,
            # filtramos post-request
            pass

        try:
            response = requests.get(url, timeout=30, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Data Research)"
            })
            response.raise_for_status()
            data = response.json()
            offers = data.get("offers", [])

            if gpu_name:
                offers = [
                    o for o in offers
                    if gpu_name.lower() in o.get("gpu_name", "").lower()
                ]

            return offers
        except Exception as e:
            logger.error(f"Error fetching Vast.ai bundles: {e}")
            return []

    def compute_gspi(self) -> Optional[float]:
        """
        Calcula GSPI: indice de precio spot GPU ($/hora promedio ponderado).
        Usa GPUs high-end como proxy del mercado.
        Retorna: precio promedio por hora en USD (0-100 escalado internamente).
        """
        all_offers = self.fetch_bundles()
        if not all_offers:
            return None

        # Filtrar solo offers rentables/relevantes
        gpu_prices = []
        for offer in all_offers:
            gpu_name = offer.get("gpu_name", "")
            dph = offer.get("dph_total", 0)
            num_gpus = offer.get("num_gpus", 1)
            rentable = offer.get("rentable", False)

            if not rentable or dph <= 0:
                continue

            # Precio por GPU individual
            price_per_gpu = dph / num_gpus
            gpu_prices.append(price_per_gpu)

        if not gpu_prices:
            return None

        # Usamos percentil 50 como benchmark del mercado
        gpu_prices.sort()
        median_price = gpu_prices[len(gpu_prices) // 2]
        avg_price = sum(gpu_prices) / len(gpu_prices)

        # Para GSPI, queremos un indice que refleje deflacion.
        # Normalizamos: asumimos que $5/hora es 100% (max) y $0.10/hora es 0%
        # Invertimos: precio BAJO = deflacion ALTA = riesgo ALTO
        # Pero en nuestro normalizador, queremos que mayor valor crudo = mayor riesgo
        # Asi que precio bajo (deflacion) deberia dar score alto.
        # Retornamos un valor proxy: usamos el inverso del precio relativo a un baseline.
        
        # Baseline historico aproximado para GPU spot high-end: ~$2.00/hora
        baseline = 2.00
        if avg_price >= baseline:
            # Precio normal o alto = deflacion baja = riesgo bajo
            deflation_pct = 0.0
        else:
            # Precio bajo = deflacion
            deflation_pct = ((baseline - avg_price) / baseline) * 100

        logger.info(f"[Vast.ai GSPI] avg_price=${avg_price:.4f}/h, median=${median_price:.4f}/h, "
                    f"deflation_proxy={deflation_pct:.2f}% (baseline=${baseline})")

        return round(deflation_pct, 2)

    def compute_uor(self) -> Optional[float]:
        """
        Calcula UOR: Underutilization/Overcapacity Ratio.
        
        CORRECCION v2: La API publica de Vast.ai devuelve 'rented=false' 
        para TODOS los bundles (limitacion de la API). 
        
        Nuevo approach: Usamos precio como proxy inverso de demanda.
        - Demanda alta -> precios altos -> UOR bajo
        - Demanda baja -> precios bajos -> UOR alto
        
        Retorna: porcentaje de infrautilizacion (0-100).
        """
        all_offers = self.fetch_bundles()
        if not all_offers:
            return None

        # Calcular precio promedio de GPUs rentables
        gpu_prices = []
        for offer in all_offers:
            dph = offer.get("dph_total", 0)
            num_gpus = offer.get("num_gpus", 1)
            rentable = offer.get("rentable", False)
            if rentable and dph > 0:
                gpu_prices.append(dph / num_gpus)

        if not gpu_prices:
            return None

        avg_price = sum(gpu_prices) / len(gpu_prices)
        
        # Baseline: precio "saludable" de GPU spot high-end
        baseline = 2.00
        
        # Si precio = baseline -> UOR = 0% (capacidad totalmente utilizada)
        # Si precio = 0 -> UOR = 100% (capacidad sin utilizar)
        if avg_price >= baseline:
            uor = 0.0
        else:
            uor = ((baseline - avg_price) / baseline) * 100
        
        uor = max(0.0, min(100.0, uor))

        logger.info(f"[Vast.ai UOR v2] avg_price=${avg_price:.4f}/h, baseline=${baseline}, "
                    f"uor={uor:.2f}% (precio como proxy de demanda)")

        return round(uor, 2)

    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para GSPI y UOR."""
        records = []
        ts = datetime.utcnow()

        gspi = self.compute_gspi()
        if gspi is not None:
            records.append({
                "kpi_code": "GSPI",
                "raw_value": gspi,
                "timestamp": ts,
                "data_source": "VAST_AI_LIVE",
            })

        uor = self.compute_uor()
        if uor is not None:
            records.append({
                "kpi_code": "UOR",
                "raw_value": uor,
                "timestamp": ts,
                "data_source": "VAST_AI_LIVE",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = VastAIClient()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
