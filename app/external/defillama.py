"""Cliente REAL para DeFiLlama API pública.
Usa TVL (Total Value Locked) de protocols crypto como proxy adicional de CFBR.
Menor TVL = menos capital disponible para infraestructura = mayor riesgo.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict
import requests
import logging

logger = logging.getLogger(__name__)

class DeFiLlamaClient:
    """Cliente para DeFiLlama public API (sin auth, sin rate limit)."""

    BASE_URL = "https://api.llama.fi"

    def get_global_tvl(self) -> Optional[float]:
        """Obtiene TVL global total en USD sumando todas las chains."""
        url = f"{self.BASE_URL}/v2/chains"
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                total = sum(c.get("tvl", 0) for c in data)
                return float(total) if total > 0 else None
            return None
        except Exception as e:
            logger.error(f"Error fetching DeFiLlama TVL: {e}")
            return None

    def get_chains(self) -> Optional[list]:
        """Obtiene datos de TVL por cadena."""
        url = f"{self.BASE_URL}/chains"
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            # La respuesta puede ser muy grande, tomar solo top chains
            data = response.json()
            if isinstance(data, list):
                return data[:10]
            return None
        except Exception as e:
            logger.error(f"Error fetching DeFiLlama chains: {e}")
            return None

    def compute_cfbr_proxy(self) -> Optional[float]:
        """
        Proxy de CFBR usando TVL global de DeFi.
        
        Lógica:
        - TVL alto = mucho capital en crypto = capital disponible para infraestructura = CFBR bajo
        - TVL bajo = capital huyendo = menos inversión en infra = CFBR alto
        
        Retorna: 0-100 donde mayor = mayor riesgo de quema de capital.
        """
        tvl = self.get_global_tvl()
        if tvl is None:
            return None

        # Baseline TVL: $50B (ajustado por mercado 2024-2026)
        # En bull market 2021 fue $180B, en bear 2022 fue $25B
        baseline = 50_000_000_000
        
        ratio = tvl / baseline
        
        if ratio >= 2.0:
            cfbr = 10.0
        elif ratio <= 0.2:
            cfbr = 95.0
        else:
            cfbr = 95.0 - ((ratio - 0.2) / (2.0 - 0.2)) * (95.0 - 10.0)
        
        return round(max(0.0, min(100.0, cfbr)), 2)

    def compute_cfbr_chain_volatility(self) -> Optional[float]:
        """
        Proxy adicional usando volatilidad entre chains.
        Si una chain pierde mucho TVL rápidamente = inestabilidad = riesgo.
        """
        chains = self.get_chains()
        if not chains:
            return None

        # Calcular cambios porcentuales de TVL en top chains
        changes = []
        for chain in chains:
            tvl = chain.get("tvl", 0)
            tvl_prev_day = chain.get("tvlPrevDay", tvl)
            if tvl_prev_day and tvl_prev_day > 0:
                change = abs((tvl - tvl_prev_day) / tvl_prev_day) * 100
                changes.append(change)

        if not changes:
            return None

        avg_change = sum(changes) / len(changes)
        
        # Baseline: 2% cambio diario promedio = normal
        # >10% = volátil = alto riesgo
        baseline_change = 2.0
        
        if avg_change <= baseline_change:
            cfbr = 10.0
        elif avg_change >= 15.0:
            cfbr = 90.0
        else:
            cfbr = 10.0 + ((avg_change - baseline_change) / (15.0 - baseline_change)) * (90.0 - 10.0)
        
        return round(max(0.0, min(100.0, cfbr)), 2)

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
                "data_source": "DEFILLAMA",
            })

        cfbr_vol = self.compute_cfbr_chain_volatility()
        if cfbr_vol is not None:
            records.append({
                "kpi_code": "CFBR",
                "raw_value": cfbr_vol,
                "timestamp": ts,
                "data_source": "DEFILLAMA_VOL",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = DeFiLlamaClient()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
