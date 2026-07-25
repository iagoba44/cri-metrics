"""Calculador del Temperature Market Index (TMI).
Mide la 'temperatura' del mercado IA combinando 5 componentes:
- Fear & Greed Index (sentimiento crypto)
- arXiv velocity (actividad R&D)
- HN activity (interés técnico)
- Hashrate global (infraestructura activa)
- AI tokens performance (inversión en IA)
"""
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Pesos de cada componente en el TMI
TMI_WEIGHTS = {
        "fear_greed": 0.20,      # Sentimiento del mercado crypto
        "arxiv_velocity": 0.15,  # Velocidad de investigación ML
        "hn_activity": 0.15,     # Interés técnico developer
        "hashrate": 0.15,        # Infraestructura activa (GPUs trabajando)
        "ai_tokens": 0.10,       # Inversión en tokens IA
        "news_coverage": 0.10,   # Cobertura mediática IA
        "ai_revenue": 0.15,      # Ingresos empresas IA (AlphaVantage)
    }

class TMICalculator:
    """Calcula el Temperature Market Index."""

    def __init__(self):
        self.weights = TMI_WEIGHTS

    def calculate(self, components: Dict[str, Optional[float]]) -> Dict:
        """
        Calcula TMI a partir de componentes individuales.
        
        Args:
            components: Dict con keys fear_greed, arxiv_velocity, hn_activity, hashrate, ai_tokens
                       Valores pueden ser None si la fuente falló.
        
        Returns:
            Dict con tmi_score, zone, component_details, coverage_pct
        """
        total_weight = 0.0
        weighted_sum = 0.0
        details = {}
        missing = []

        for key, weight in self.weights.items():
            val = components.get(key)
            if val is not None:
                weighted_sum += val * weight
                total_weight += weight
                details[key] = {
                    "value": val,
                    "weight": weight,
                    "contribution": round(val * weight, 2),
                }
            else:
                missing.append(key)
                details[key] = {
                    "value": None,
                    "weight": weight,
                    "contribution": None,
                }

        coverage_pct = round((total_weight / sum(self.weights.values())) * 100, 1)
        
        if total_weight == 0:
            logger.warning("[TMI] Ningún componente disponible. No se puede calcular TMI.")
            return {
                "tmi_score": None,
                "zone": "UNKNOWN",
                "component_details": details,
                "coverage_pct": 0.0,
                "missing_components": missing,
            }

        # Normalizar por pesos disponibles
        tmi = weighted_sum / total_weight
        
        # Ajustar escala si coverage < 100% (penalizar ligeramente)
        if coverage_pct < 80:
            # Si faltan componentes clave, añadir incertidumbre
            tmi = tmi * (0.9 + coverage_pct / 1000)  # Escala 0.9-1.0
        
        tmi = round(max(0.0, min(100.0, tmi)), 2)
        
        zone = self._get_zone(tmi)
        
        logger.info(f"[TMI] Score={tmi} ({zone}) | Coverage={coverage_pct}% | Missing={missing}")
        
        return {
            "tmi_score": tmi,
            "zone": zone,
            "component_details": details,
            "coverage_pct": coverage_pct,
            "missing_components": missing,
        }

    def _get_zone(self, tmi: float) -> str:
        if tmi <= 30:
            return "COLD"
        elif tmi <= 70:
            return "WARM"
        else:
            return "HOT"

    @classmethod
    def fetch_all_components(cls) -> Dict[str, Optional[float]]:
        """
        Consulta todas las fuentes externas y retorna componentes.
        """
        components = {}
        
        # 1. Fear & Greed
        try:
            from app.external.fear_greed import FearGreedClient
            fg = FearGreedClient()
            components["fear_greed"] = fg.compute_tmi_component()
        except Exception as e:
            logger.error(f"[TMI] FearGreed falló: {e}")
            components["fear_greed"] = None
        
        # 2. arXiv velocity
        try:
            from app.external.arxiv_trend import ArxivTrendClient
            ax = ArxivTrendClient()
            components["arxiv_velocity"] = ax.compute_tmi_component()
        except Exception as e:
            logger.error(f"[TMI] arXiv falló: {e}")
            components["arxiv_velocity"] = None
        
        # 3. HN Activity
        try:
            from app.external.hackernews import HackerNewsClient
            hn = HackerNewsClient()
            components["hn_activity"] = hn.compute_tmi_component()
        except Exception as e:
            logger.error(f"[TMI] HN falló: {e}")
            components["hn_activity"] = None
        
        # 4. Hashrate (NiceHash UOR proxy inverted)
        try:
            from app.external.nicehash import NiceHashClient
            nh = NiceHashClient()
            # UOR NiceHash = infrautilización. Invertir para obtener ocupación/temperatura
            uor = nh.compute_uor_proxy()
            if uor is not None:
                components["hashrate"] = round(max(0.0, min(100.0, 100.0 - uor)), 2)
            else:
                components["hashrate"] = None
        except Exception as e:
            logger.error(f"[TMI] NiceHash hashrate falló: {e}")
            components["hashrate"] = None
        
        # 5. AI Tokens
        try:
            from app.external.coingecko_ai import CoinGeckoAIClient
            cg = CoinGeckoAIClient()
            components["ai_tokens"] = cg.compute_tmi_component()
        except Exception as e:
            logger.error(f"[TMI] CoinGecko AI falló: {e}")
            components["ai_tokens"] = None

        # 6. News Coverage (opcional, requiere API key)
        try:
            from app.external.newsapi import NewsAPIClient
            nw = NewsAPIClient()
            components["news_coverage"] = nw.compute_tmi_component()
        except Exception as e:
            logger.error(f"[TMI] NewsAPI falló: {e}")
            components["news_coverage"] = None
        
        # 7. AI Revenue (AlphaVantage - opcional, requiere API key)
        try:
            from app.external.alphavantage import AlphaVantageClient
            av = AlphaVantageClient()
            components["ai_revenue"] = av.compute_tmi_component()
        except Exception as e:
            logger.error(f"[TMI] AlphaVantage revenue falló: {e}")
            components["ai_revenue"] = None
        
        return components
