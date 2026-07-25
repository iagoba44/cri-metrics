"""Cliente REAL para arXiv - velocidad de publicación papers ML.
Usa el API público de arXiv para contar papers cs.LG (Machine Learning)
como proxy de actividad R&D.
"""
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)

class ArxivTrendClient:
    """Cliente para medir velocidad de papers IA en arXiv."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def get_recent_papers(self) -> int:
        """
        Cuenta papers cs.LG (Machine Learning) recientes.
        Pide los últimos 100 ordenados por fecha.
        
        Baseline: ~30-50 papers en el top 100 = normal.
        Durante boom (NeurIPS/ICML época): 100 papers.
        Durante invierno IA: <20 papers.
        """
        try:
            response = requests.get(
                self.BASE_URL,
                params={
                    "search_query": "cat:cs.LG",
                    "start": 0,
                    "max_results": 100,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
                timeout=20,
                headers={"User-Agent": "CRI-Metrics-Bot/1.0 (Research)"},
            )
            response.raise_for_status()
            
            xml = response.text
            # Contar entries totales (están ordenados por fecha descendente)
            entries = xml.count("<entry>")
            
            logger.info(f"[ArXiv] Papers cs.LG recientes: {entries}")
            return entries
            
        except Exception as e:
            logger.error(f"Error fetching arXiv: {e}")
            return 0

    def compute_tmi_component(self) -> Optional[float]:
        """
        Componente TMI: velocidad de papers IA.
        
        Baseline: 40 papers en top 100 = normal (TMI 50)
        Máximo: 100 papers = boom (TMI 100)
        Mínimo: 10 papers = invierno (TMI 0)
        """
        count = self.get_recent_papers()
        if count == 0:
            return None
        
        # Baseline = 40 papers
        baseline = 40.0
        ratio = count / baseline
        
        # Mapear a 0-100
        if ratio >= 2.5:
            tmi = 100.0
        elif ratio <= 0.25:
            tmi = 0.0
        else:
            tmi = ((ratio - 0.25) / (2.5 - 0.25)) * 100.0
        
        return round(max(0.0, min(100.0, tmi)), 2)
