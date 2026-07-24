"""Tests para el motor de normalizacion.
Valida las Reglas 1 y 2 del SDD con bounds actualizados (max=100 para SHPD).
"""
import pytest
from decimal import Decimal
from app.services.normalizer import Normalizer

class TestNormalizer:
    """Valida las Reglas 1 y 2 del SDD."""

    def test_direct_formula_shpd_mid(self):
        """SHPD a 50% del rango (max=100) -> score 50."""
        score = Normalizer.normalize("SHPD", Decimal("50.0"))
        assert score == Decimal("50.00")

    def test_direct_formula_shpd_max(self):
        """SHPD en maximo (100) -> score 100."""
        score = Normalizer.normalize("SHPD", Decimal("100.0"))
        assert score == Decimal("100.00")

    def test_direct_formula_cfbr(self):
        """CFBR alto = mayor riesgo -> score alto (directo)."""
        score = Normalizer.normalize("CFBR", Decimal("80.0"))
        assert score == Decimal("80.00")

    def test_inverse_formula_gspi_high_risk(self):
        """GSPI alto (100% deflacion) = maximo riesgo -> score 100."""
        score = Normalizer.normalize("GSPI", Decimal("100.0"))
        assert score == Decimal("100.00")

    def test_inverse_formula_gspi_low_risk(self):
        """GSPI bajo (0% deflacion) = menor riesgo -> score 0."""
        score = Normalizer.normalize("GSPI", Decimal("0.0"))
        assert score == Decimal("0.00")

    def test_inverse_formula_ltcr(self):
        """LTCR alto = mayor riesgo (compresion extrema de tiempo)."""
        score = Normalizer.normalize("LTCR", Decimal("100.0"))
        assert score == Decimal("100.00")

    def test_out_of_bounds_truncate_low(self):
        """OUT_OF_BOUNDS: valor < min se trunca a 0."""
        score = Normalizer.normalize("SHPD", Decimal("-10.0"))
        assert score == Decimal("0.00")

    def test_out_of_bounds_truncate_high(self):
        """OUT_OF_BOUNDS: valor > max se trunca a 100."""
        score = Normalizer.normalize("CFBR", Decimal("150.0"))
        assert score == Decimal("100.00")

    def test_unknown_kpi_raises(self):
        """KPI no definido debe lanzar ValueError."""
        with pytest.raises(ValueError, match="KPI desconocido"):
            Normalizer.normalize("UNKNOWN", Decimal("50.0"))
