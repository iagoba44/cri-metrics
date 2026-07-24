"""Fuente de datos: SEC EDGAR API."""
from datetime import datetime, timezone
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class SECDataSource:
    """Cliente simulado para SEC EDGAR API.
    En producción, reemplazar por requests a www.sec.gov/cgi-bin/browse-edgar
    """

    def fetch(self) -> List[Dict]:
        """Simula extracción de métricas financieras de empresas de infraestructura IA."""
        logger.info("[SEC EDGAR] Extrayendo métricas financieras...")

        # Simulación: GSPI y LTCR derivados de datos financieros
        return [
            {
                "kpi_code": "GSPI",
                "raw_value": 35.0,  # Deflación del 35% en precios GPU spot
                "timestamp": datetime.now(timezone.utc),
                "data_source": "SEC_EDGAR",
            },
            {
                "kpi_code": "LTCR",
                "raw_value": 72.0,  # 72% de ingresos en contratos largos
                "timestamp": datetime.now(timezone.utc),
                "data_source": "SEC_EDGAR",
            },
        ]
