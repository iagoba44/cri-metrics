"""Cliente REAL para NiceHash API pública.
Extrae rentabilidad de algoritmos de minado como proxy de SHPD.
Si los paying rates caen = menos rentable minar = menor demanda GPU = deflación.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict
import requests
import logging

logger = logging.getLogger(__name__)

class NiceHashClient:
    """Cliente para NiceHash public API. Sin autenticación requerida."""

    BASE_URL = "https://api2.nicehash.com/main/api/v2/public"

    def get_global_stats(self) -> Optional[dict]:
        """Obtiene estadísticas globales de hashrate y paying rates."""
        url = f"{self.BASE_URL}/stats/global/current"
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching NiceHash global stats: {e}")
            return None

    def get_algo_info(self) -> Optional[dict]:
        """Obtiene info de algoritmos de minado con paying rates."""
        url = f"{self.BASE_URL}/simplemultialgo/info"
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching NiceHash algo info: {e}")
            return None

    def compute_shpd_proxy(self) -> Optional[float]:
        """
        Calcula proxy de SHPD usando rentabilidad de minado GPU.
        
        Lógica:
        - DaggerHashimoto (ETH) y KawPow (RVN) son algoritmos GPU.
        - Si paying rate cae = menos rentable minar = GPUs sobran = deflación.
        - Usamos promedio de paying rates GPU-weighted.
        
        Retorna: índice 0-100 donde mayor = mayor deflación (menor demanda).
        """
        data = self.get_algo_info()
        if not data or "miningAlgorithms" not in data:
            return None

        algos = data["miningAlgorithms"]
        
        # Algoritmos GPU-relevantes
        gpu_algos = ["DAGGERHASHIMOTO", "KAWPOW", "ETCHASH", "BEAMV3", "AUTOLYKOS", "FISHHASH"]
        
        gpu_paying = []
        for algo in algos:
            if algo.get("algorithm") in gpu_algos:
                paying = float(algo.get("paying", 0))
                if paying > 0:
                    gpu_paying.append(paying)

        if not gpu_paying:
            return None

        # Usar mediana para ser robusto contra outliers (ej. BEAMV3 puede tener unidades distintas)
        sorted_paying = sorted(gpu_paying)
        median_paying = sorted_paying[len(sorted_paying) // 2]
        
        # Baseline: paying rate mediano histórico ~0.000002 (ajustado por mercado 2024-2026)
        # Si paying < baseline/2 = deflación severa (score 100)
        # Si paying > baseline*2 = demanda alta (score 0)
        baseline = 0.000002
        
        ratio = median_paying / baseline
        
        # Invertir: menor paying = mayor deflación
        if ratio <= 0.1:
            score = 95.0
        elif ratio >= 5.0:
            score = 5.0
        else:
            score = 95.0 - ((ratio - 0.1) / (5.0 - 0.1)) * (95.0 - 5.0)
        
        return round(max(0.0, min(100.0, score)), 2)

    def compute_uor_proxy(self) -> Optional[float]:
        """
        Proxy de UOR usando hashrate global de NiceHash.
        Más hashrate = más GPUs trabajando = mayor ocupación.
        """
        data = self.get_global_stats()
        if not data or "algos" not in data:
            return None
        
        # Usar hashrate total como proxy de ocupación
        total_speed = 0
        for algo in data.get("algos", []):
            s = float(algo.get("s", 0))
            total_speed += s
        
        # Baseline: ~2e8 (ajustado por observación)
        if total_speed <= 0:
            return None
            
        # Normalizar: más hashrate = mayor ocupación (score más bajo = riesgo menor)
        # Invertimos para UOR: más actividad = menor riesgo de infrautilización
        # UOR se mide como % de infrautilización, entonces:
        # Mucho hashrate = poca infrautilización = UOR bajo
        # Poco hashrate = mucha infrautilización = UOR alto
        
        # Baseline: 100M TH/s (valor de referencia)
        baseline = 1e8
        ratio = total_speed / baseline
        
        if ratio >= 2.0:
            uor = 10.0
        elif ratio <= 0.3:
            uor = 90.0
        else:
            uor = 90.0 - ((ratio - 0.3) / (2.0 - 0.3)) * (90.0 - 10.0)
        
        return round(max(0.0, min(100.0, uor)), 2)

    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para SHPD y UOR."""
        records = []
        ts = datetime.now(timezone.utc)

        shpd = self.compute_shpd_proxy()
        if shpd is not None:
            records.append({
                "kpi_code": "SHPD",
                "raw_value": shpd,
                "timestamp": ts,
                "data_source": "NICEHASH",
            })

        uor = self.compute_uor_proxy()
        if uor is not None:
            records.append({
                "kpi_code": "UOR",
                "raw_value": uor,
                "timestamp": ts,
                "data_source": "NICEHASH",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = NiceHashClient()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
