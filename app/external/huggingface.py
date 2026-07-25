"""Cliente REAL para HuggingFace API pública.
Usa downloads de modelos trending como proxy de demanda IA (UOR/SHPD).
Más downloads = más actividad de inferencia/training = mayor demanda GPU.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict
import requests
import logging

logger = logging.getLogger(__name__)

class HuggingFaceClient:
    """Cliente para HuggingFace public API (sin auth para endpoints básicos)."""

    BASE_URL = "https://huggingface.co/api"

    def get_trending(self, limit: int = 20) -> Optional[list]:
        """Obtiene modelos/datasets trending con metadata."""
        url = f"{self.BASE_URL}/trending"
        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            return response.json().get("recentlyTrending", [])
        except Exception as e:
            logger.error(f"Error fetching HuggingFace trending: {e}")
            return None

    def get_model_stats(self, model_id: str) -> Optional[dict]:
        """Obtiene estadísticas de un modelo específico."""
        url = f"{self.BASE_URL}/models/{model_id}"
        try:
            response = requests.get(url, timeout=10, headers={
                "User-Agent": "CRI-Metrics-Bot/1.0 (Research)"
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching HuggingFace model {model_id}: {e}")
            return None

    def compute_uor_proxy(self) -> Optional[float]:
        """
        Proxy de UOR usando actividad en HuggingFace.
        
        Lógica:
        - Si hay muchos modelos trending con altos downloads = ecosistema activo
        - Ecosistema activo = demanda GPU alta = baja infrautilización = UOR bajo
        - Si trending está muerto = poca demanda = UOR alto
        
        Retorna: 0-100 donde mayor = mayor infrautilización (menos demanda).
        """
        trending = self.get_trending(limit=10)
        if not trending:
            return None

        # Calcular métricas de actividad
        total_downloads = 0
        gpu_relevant_count = 0
        
        gpu_keywords = ["llm", "transformer", "gpt", "diffusion", "vision", "audio", "multimodal"]
        
        for item in trending:
            repo = item.get("repoData", {})
            downloads = repo.get("downloads", 0)
            total_downloads += downloads
            
            tags = repo.get("tags", []) or []
            pipeline = repo.get("pipeline_tag", "") or ""
            desc = repo.get("description", "") or ""
            
            text = " ".join(tags + [pipeline, desc]).lower()
            if any(k in text for k in gpu_keywords):
                gpu_relevant_count += 1

        if total_downloads <= 0:
            return None

        # Baseline: 1M downloads diarios entre top 10 = ecosistema saludable
        baseline_downloads = 1_000_000
        
        # Ratio de actividad
        ratio = total_downloads / baseline_downloads
        
        # Muchos downloads = UOR bajo (poca infrautilización)
        # Pocos downloads = UOR alto (mucha infrautilización)
        if ratio >= 2.0:
            uor = 10.0
        elif ratio <= 0.1:
            uor = 90.0
        else:
            uor = 90.0 - ((ratio - 0.1) / (2.0 - 0.1)) * (90.0 - 10.0)
        
        return round(max(0.0, min(100.0, uor)), 2)

    def compute_shpd_proxy(self) -> Optional[float]:
        """
        Proxy de SHPD usando tamaño de modelos trending.
        
        Lógica:
        - Modelos más grandes (más parámetros) = más necesidad de GPUs potentes
        - Si trending son modelos pequeños = GPUs antiguas sirven = menos presión de compra
        - Usamos mediana de parámetros como proxy
        """
        trending = self.get_trending(limit=15)
        if not trending:
            return None

        params = []
        for item in trending:
            repo = item.get("repoData", {})
            p = repo.get("numParameters", 0)
            if p and p > 0:
                params.append(p)

        if not params:
            return None

        median_params = sorted(params)[len(params) // 2]
        
        # Baseline: 7B parámetros (modelos medianos de 2024-2026)
        # Si mediana > 20B = demanda GPU alta = SHPD bajo
        # Si mediana < 1B = demanda GPU baja = SHPD alto
        baseline = 7_000_000_000
        ratio = median_params / baseline
        
        if ratio >= 3.0:
            shpd = 10.0
        elif ratio <= 0.2:
            shpd = 90.0
        else:
            shpd = 90.0 - ((ratio - 0.2) / (3.0 - 0.2)) * (90.0 - 10.0)
        
        return round(max(0.0, min(100.0, shpd)), 2)

    def fetch(self) -> List[Dict]:
        """Pipeline de ingesta: retorna registros para UOR y SHPD."""
        records = []
        ts = datetime.now(timezone.utc)

        uor = self.compute_uor_proxy()
        if uor is not None:
            records.append({
                "kpi_code": "UOR",
                "raw_value": uor,
                "timestamp": ts,
                "data_source": "HUGGINGFACE",
            })

        shpd = self.compute_shpd_proxy()
        if shpd is not None:
            records.append({
                "kpi_code": "SHPD",
                "raw_value": shpd,
                "timestamp": ts,
                "data_source": "HUGGINGFACE",
            })

        return records

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = HuggingFaceClient()
    data = client.fetch()
    for d in data:
        print(f"{d['kpi_code']}: {d['raw_value']:.2f} (source: {d['data_source']})")
