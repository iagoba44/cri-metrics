"""Fuentes de datos: Neoclouds (RunPod, Vast.ai)."""
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class NeocloudDataSource:
    """Cliente simulado para APIs de Neoclouds.
    En producción, integrar con:
    - RunPod API: https://rest.runpod.io/v1/
    - Vast.ai API: https://vast.ai/api/v0/
    """

    def fetch(self) -> List[Dict]:
        """Simula extracción de métricas operativas de mercado GPU."""
        logger.info("[Neoclouds] Extrayendo métricas operativas...")

        return [
            {
                "kpi_code": "CFBR",
                "raw_value": 82.5,  # Free-burn rate alto = riesgo operativo
                "timestamp": datetime.utcnow(),
                "data_source": "VAST_AI",
            },
            {
                "kpi_code": "UOR",
                "raw_value": 45.0,  # 45% de capacidad infrautilizada
                "timestamp": datetime.utcnow(),
                "data_source": "RUNPOD",
            },
        ]
