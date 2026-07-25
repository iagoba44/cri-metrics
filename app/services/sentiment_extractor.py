"""Structured Sentiment Extractor para noticias de infraestructura IA.
Clasifica noticias validadas en 3 vectores:
- capex_impact: Impacto en gasto de capital (data centers, chips)
- demand_impact: Impacto en demanda de inferencia/entrenamiento
- regulatory_risk: Riesgo regulatorio
"""
import logging
import re
from typing import List, Dict, Tuple
from collections import Counter

logger = logging.getLogger(__name__)

# Diccionarios de sentimiento por categoría
CAPEX_POSITIVE = {
    "invest", "investment", "build", "expand", "ramp up", "capex", "infrastructure spending",
    "new data center", "purchase", "order", "contract", "allocate", "commit",
    "inversión", "construir", "expandir", "gasto de capital", "nuevo centro de datos",
}
CAPEX_NEGATIVE = {
    "cut", "freeze", "delay", "cancel", "halt", "suspend", "scale back", "reduce spending",
    "close", "shut down", "divest", "layoff", "restructure",
    "recortar", "congelar", "cancelar", "cerrar", "despido", "reestructurar",
}
DEMAND_POSITIVE = {
    "surge", "boom", "soar", "strong demand", "rampant", "insatiable", "growth",
    "adoption", "deploy", "usage", "utilization", "booked", "sold out",
    "auge", "fuerte demanda", "crecimiento", "adopción", "despliegue", "agotado",
}
DEMAND_NEGATIVE = {
    "slump", "plunge", "collapse", "weak demand", "slowdown", "cooling",
    "decline", "drop", "fall", "excess", "oversupply", "glut", "idle", "unused",
    "caída", "débil demanda", "desaceleración", "exceso", "sobreoferta", "ocioso",
}
REGULATORY_POSITIVE = {
    "deregulate", "ease", "permit", "approve", "green light", "exemption",
    "liberalize", "supportive policy", "subsidy", "tax credit",
    "desregular", "facilitar", "aprobar", "subsidio", "crédito fiscal",
}
REGULATORY_NEGATIVE = {
    "ban", "restrict", "export control", "sanction", "tariff", "probe",
    "investigation", "antitrust", "fine", "compliance", "audit",
    "vetar", "restringir", "control de exportación", "sanción", "multa",
    "prohibir", "regular", "auditoría", "cumplimiento",
}

class SentimentExtractor:
    """Extrae sentimiento estructurado de noticias usando análisis léxico."""

    def extract(self, articles: List[Dict]) -> Dict:
        """
        Procesa una lista de artículos validados y retorna un dict con:
        - capex_score: 0-100 (50 = neutral)
        - demand_score: 0-100
        - regulatory_score: 0-100
        - summary: resumen de los drivers principales
        """
        if not articles:
            return {
                "capex_score": 50.0,
                "demand_score": 50.0,
                "regulatory_score": 50.0,
                "article_count": 0,
                "summary": "No hay noticias validadas disponibles.",
            }

        capex_scores = []
        demand_scores = []
        regulatory_scores = []
        drivers = Counter()

        for article in articles:
            text = self._normalize_text(article)
            c_pos, c_neg = self._count_matches(text, CAPEX_POSITIVE, CAPEX_NEGATIVE)
            d_pos, d_neg = self._count_matches(text, DEMAND_POSITIVE, DEMAND_NEGATIVE)
            r_pos, r_neg = self._count_matches(text, REGULATORY_POSITIVE, REGULATORY_NEGATIVE)

            capex_scores.append(self._to_score(c_pos, c_neg))
            demand_scores.append(self._to_score(d_pos, d_neg))
            regulatory_scores.append(self._to_score(r_pos, r_neg))

            # Track drivers
            if c_pos > c_neg:
                drivers["capex_up"] += 1
            elif c_neg > c_pos:
                drivers["capex_down"] += 1
            if d_pos > d_neg:
                drivers["demand_up"] += 1
            elif d_neg > d_pos:
                drivers["demand_down"] += 1
            if r_pos > r_neg:
                drivers["regulatory_up"] += 1
            elif r_neg > r_pos:
                drivers["regulatory_down"] += 1

        # Promedios ponderados por semantic_score si existe
        weights = [a.get("semantic_score", 0.5) + 0.1 for a in articles]
        capex = self._weighted_avg(capex_scores, weights)
        demand = self._weighted_avg(demand_scores, weights)
        regulatory = self._weighted_avg(regulatory_scores, weights)

        summary = self._build_summary(drivers, len(articles))

        return {
            "capex_score": round(capex, 2),
            "demand_score": round(demand, 2),
            "regulatory_score": round(regulatory, 2),
            "article_count": len(articles),
            "summary": summary,
        }

    def _normalize_text(self, article: Dict) -> str:
        title = article.get("title", "")
        summary = article.get("summary", "")
        return f"{title} {summary}".lower()

    def _count_matches(self, text: str, pos_set: set, neg_set: set) -> Tuple[int, int]:
        pos = sum(1 for kw in pos_set if kw in text)
        neg = sum(1 for kw in neg_set if kw in text)
        return pos, neg

    def _to_score(self, pos: int, neg: int) -> float:
        """Mapea conteos a score 0-100. 50 = neutral."""
        total = pos + neg
        if total == 0:
            return 50.0
        # Ratio normalizado: si pos > neg, score > 50
        ratio = (pos - neg) / total
        return 50.0 + ratio * 50.0

    def _weighted_avg(self, values: List[float], weights: List[float]) -> float:
        if not values:
            return 50.0
        total_w = sum(weights)
        if total_w == 0:
            return sum(values) / len(values)
        return sum(v * w for v, w in zip(values, weights)) / total_w

    def _build_summary(self, drivers: Counter, total: int) -> str:
        parts = []
        if drivers["capex_up"] > drivers["capex_down"]:
            parts.append(f"Capex positivo ({drivers['capex_up']} noticias)")
        elif drivers["capex_down"] > drivers["capex_up"]:
            parts.append(f"Capex negativo ({drivers['capex_down']} noticias)")
        if drivers["demand_up"] > drivers["demand_down"]:
            parts.append(f"Demanda alta ({drivers['demand_up']} noticias)")
        elif drivers["demand_down"] > drivers["demand_up"]:
            parts.append(f"Demanda débil ({drivers['demand_down']} noticias)")
        if drivers["regulatory_down"] > 0:
            parts.append(f"Riesgo regulatorio ({drivers['regulatory_down']} noticias)")
        if not parts:
            return f"Sentimiento neutral en {total} noticias."
        return "; ".join(parts)
