"""Motor de normalización Min-Max con manejo de OUT_OF_BOUNDS."""
from decimal import Decimal
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class Normalizer:
    """Aplica normalización Min-Max con fórmula directa o inversa."""

    @staticmethod
    def normalize(kpi_code: str, raw_value: Decimal) -> Decimal:
        bounds = settings.KPI_BOUNDS.get(kpi_code)
        if not bounds:
            raise ValueError(f"KPI desconocido: {kpi_code}")

        min_val = Decimal(str(bounds["min"]))
        max_val = Decimal(str(bounds["max"]))
        value = Decimal(str(raw_value))

        # Manejo OUT_OF_BOUNDS: truncar a 0 o 100
        if value < min_val:
            logger.warning(f"OUT_OF_BOUNDS: {kpi_code}={value} < min={min_val}. Truncando a min.")
            value = min_val
        elif value > max_val:
            logger.warning(f"OUT_OF_BOUNDS: {kpi_code}={value} > max={max_val}. Truncando a max.")
            value = max_val

        # Evitar división por cero
        range_val = max_val - min_val
        if range_val == 0:
            return Decimal("50.00")

        # Fórmula directa: (valor - min) / (max - min) * 100
        direct_score = ((value - min_val) / range_val) * Decimal("100")

        # Fórmula inversa: 100 - direct_score
        if kpi_code in settings.INVERSE_KPIS:
            # Regla 1: Mayor riesgo en extremo de deficiencia/compresión
            # Para GSPI y LTCR, mayor valor crudo = mayor riesgo
            # Pero el documento dice 'asignando 100 al extremo de mayor riesgo'
            # Si GSPI es deflación del 35%, eso es alto riesgo → score 100
            normalized = direct_score
        else:
            # Regla 2: Escalado directo
            normalized = direct_score

        # Redondear a 2 decimales
        normalized = normalized.quantize(Decimal("0.01"))
        return Decimal(str(min(max(normalized, Decimal("0.00")), Decimal("100.00"))))
