"""News Validator: Pipeline semántico de validación de noticias.
Usa embeddings locales (all-MiniLM-L6-v2) para filtrar ruido de PR
y retener solo noticias con impacto real en infraestructura IA.
"""
import logging
import numpy as np
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Frases de control (anchor vectors) para filtrar relevancia
CONTROL_PHRASES = [
    "oversupply of GPUs flooding the market",
    "data center cancellation or shutdown",
    "falling demand for AI inference",
    "GPU price crash and deflation",
    "cloud provider capital expenditure cut",
    "AI infrastructure overcapacity",
    "mining profitability collapse",
    "server hardware price decline",
    "layoffs in AI infrastructure sector",
    "regulatory ban on AI chip exports",
    "massive investment in AI data centers",
    "shortage of AI compute capacity",
    "surge in GPU rental demand",
    "rising AI token prices",
]

class NewsValidator:
    """
    Valida noticias mediante similitud coseno contra frases de control.
    Elimina PR sin impacto real en infraestructura.
    """

    _model: Optional[SentenceTransformer] = None
    _control_embeddings: Optional[np.ndarray] = None

    def __init__(self, similarity_threshold: float = 0.35):
        self.threshold = similarity_threshold
        self._load_model()

    def _load_model(self):
        if NewsValidator._model is None:
            logger.info("[NewsValidator] Cargando modelo all-MiniLM-L6-v2...")
            NewsValidator._model = SentenceTransformer("all-MiniLM-L6-v2")
            NewsValidator._control_embeddings = NewsValidator._model.encode(CONTROL_PHRASES, convert_to_numpy=True)
            logger.info("[NewsValidator] Modelo cargado.")
        self.model = NewsValidator._model
        self.control_embeddings = NewsValidator._control_embeddings

    def validate_batch(self, articles: List[Dict]) -> List[Dict]:
        """
        Filtra lista de artículos por relevancia semántica.
        Retorna solo artículos con similitud > threshold.
        Además añade 'semantic_score' y 'matched_anchor'.
        """
        if not articles:
            return []

        texts = [self._extract_text(a) for a in articles]
        article_embeddings = self.model.encode(texts, convert_to_numpy=True)

        # Similitud coseno contra cada frase de control
        similarities = cosine_similarity(article_embeddings, self.control_embeddings)
        max_sims = similarities.max(axis=1)
        best_anchor_idx = similarities.argmax(axis=1)

        validated = []
        for i, article in enumerate(articles):
            score = float(max_sims[i])
            if score >= self.threshold:
                article["semantic_score"] = round(score, 3)
                article["matched_anchor"] = CONTROL_PHRASES[best_anchor_idx[i]]
                validated.append(article)
            else:
                logger.debug(f"[NewsValidator] Descartado (score={score:.3f}): {article.get('title', '')[:60]}")

        logger.info(f"[NewsValidator] {len(validated)}/{len(articles)} artículos validados")
        return validated

    def _extract_text(self, article: Dict) -> str:
        """Concatena título y resumen para el embedding."""
        title = article.get("title", "")
        summary = article.get("summary", "")
        return f"{title}. {summary}".strip()

    def compute_relevance_score(self, articles: List[Dict]) -> Optional[float]:
        """
        Calcula un score agregado de relevancia (0-100) basado en
        la media de similitudes de artículos validados.
        """
        if not articles:
            return None
        scores = [a.get("semantic_score", 0.0) for a in articles]
        avg = np.mean(scores)
        # Escalar 0.35-0.80 -> 0-100
        normalized = (avg - 0.35) / (0.80 - 0.35) * 100.0
        return round(max(0.0, min(100.0, normalized)), 2)
