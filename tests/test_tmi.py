"""Tests para TMI Calculator."""
import pytest
from app.services.tmi_calculator import TMICalculator, TMI_WEIGHTS

def test_tmi_weights_sum():
    total = sum(TMI_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001

def test_tmi_calculate_full_coverage():
    calc = TMICalculator()
    components = {
        "fear_greed": 50.0,
        "arxiv_velocity": 50.0,
        "hn_activity": 50.0,
        "hashrate": 50.0,
        "ai_tokens": 50.0,
        "news_coverage": 50.0,
        "ai_revenue": 50.0,
    }
    result = calc.calculate(components)
    assert result["tmi_score"] == 50.0
    assert result["zone"] == "WARM"
    assert result["coverage_pct"] == 100.0

def test_tmi_calculate_partial_coverage():
    calc = TMICalculator()
    components = {
        "fear_greed": 80.0,
        "arxiv_velocity": None,
        "hn_activity": None,
        "hashrate": None,
        "ai_tokens": None,
        "news_coverage": None,
        "ai_revenue": None,
    }
    result = calc.calculate(components)
    # With 20% coverage, penalty applies: 80 * (0.9 + 20/1000) = 73.6
    assert result["tmi_score"] == 73.6
    assert result["zone"] == "HOT"
    assert result["coverage_pct"] == round((0.20 / 1.0) * 100, 1)

def test_tmi_zones():
    calc = TMICalculator()
    assert calc._get_zone(20) == "COLD"
    assert calc._get_zone(50) == "WARM"
    assert calc._get_zone(80) == "HOT"

def test_tmi_all_missing():
    calc = TMICalculator()
    components = {k: None for k in TMI_WEIGHTS}
    result = calc.calculate(components)
    assert result["tmi_score"] is None
    assert result["zone"] == "UNKNOWN"
    assert result["coverage_pct"] == 0.0
