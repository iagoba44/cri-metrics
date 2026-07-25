"""Tests para mejoras algorítmicas (Z-Score, EMA, Dynamic Weight Decay)."""
import pytest
from app.services.algorithmic_enhancements import (
    ZScoreVolatility, ExponentiallyWeightedMA, DynamicWeightDecay
)

def test_zscore_normal():
    zs = ZScoreVolatility(window=5, z_threshold=2.5)
    history = [40, 41, 39, 42, 40]  # Estable
    result = zs.compute(history)
    assert result["alert"] is False
    assert result["severity"] == "NORMAL"

def test_zscore_spike():
    zs = ZScoreVolatility(window=5, z_threshold=1.5)
    history = [40, 41, 39, 42, 80]
    result = zs.compute(history)
    assert result["alert"] is True
    assert result["z_score"] > 1.5

def test_zscore_insufficient_data():
    zs = ZScoreVolatility(window=7)
    history = [40, 41]
    result = zs.compute(history)
    assert result["alert"] is False
    assert result["severity"] == "INSUFFICIENT_DATA"

def test_ema_smoothing():
    ema = ExponentiallyWeightedMA(alpha=0.3)
    values = [50, 55, 53, 58, 52]
    smoothed = [ema.smooth(v) for v in values]
    assert len(smoothed) == len(values)
    assert all(isinstance(v, float) for v in smoothed)
    # EMA must lag behind sudden changes
    assert smoothed[1] < 55  # 55 becomes ~51.5 with alpha=0.3

def test_ema_reset():
    ema = ExponentiallyWeightedMA(alpha=0.3)
    ema.smooth(50)
    ema.reset()
    assert ema._ema is None

def test_dynamic_weight_initial():
    base = {"GSPI": 0.25, "SHPD": 0.15}
    dw = DynamicWeightDecay(base)
    effective = dw.get_effective_weights()
    # Initially all weights should be full (just recorded now)
    assert abs(effective["GSPI"] - 0.25) < 0.01
    assert abs(effective["SHPD"] - 0.15) < 0.01

def test_dynamic_weight_decay_report():
    base = {"GSPI": 0.25, "SHPD": 0.15}
    dw = DynamicWeightDecay(base)
    report = dw.get_decay_report()
    assert "GSPI" in report
    assert "SHPD" in report
    assert report["GSPI"]["base_weight"] == 0.25
    assert report["GSPI"]["confidence"] >= 0
