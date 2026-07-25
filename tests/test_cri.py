"""Tests para CRI Calculator."""
import pytest
from app.services.calculator import CRICalculator
from app.config import get_settings

def test_kpi_bounds_exist():
    settings = get_settings()
    assert "GSPI" in settings.KPI_BOUNDS
    assert "SHPD" in settings.KPI_BOUNDS
    assert "LTCR" in settings.KPI_BOUNDS
    assert "CFBR" in settings.KPI_BOUNDS
    assert "UOR" in settings.KPI_BOUNDS

def test_kpi_weights_sum_to_one():
    settings = get_settings()
    total = sum(settings.KPI_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001

def test_inverse_kpis_list():
    settings = get_settings()
    assert "GSPI" in settings.INVERSE_KPIS
    assert "LTCR" in settings.INVERSE_KPIS

def test_alert_threshold():
    settings = get_settings()
    assert settings.ALERT_THRESHOLD == 65.0
