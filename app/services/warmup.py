"""Pre-carga modelos pesados al iniciar el servidor."""
import logging
logger = logging.getLogger(__name__)

def preload_models():
    """Carga sentence-transformers antes de la primera request."""
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("[Warmup] Cargando all-MiniLM-L6-v2 (~80MB)...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("[Warmup] Modelo cargado OK")
        return model
    except Exception as e:
        logger.warning(f"[Warmup] Fallo carga modelo: {e}")
        return None
