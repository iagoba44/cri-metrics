"""Mejoras Algorítmicas al cálculo CRI/TMI.
Incluye:
- Z-Score para detección de volatilidad
- Pesos dinámicos por confianza (Data Decay)
- Suavizado Exponencial (EMA)
"""
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import deque
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class ZScoreVolatility:
    """
    Detecta picos de volatilidad usando Z-Score sobre media móvil de 7 días.
    Si CRI salta de 20 a 50 en 2 horas, el Z-Score > 3 activa alerta temprana.
    """

    def __init__(self, window: int = 7, z_threshold: float = 2.5):
        self.window = window
        self.z_threshold = z_threshold

    def compute(self, history: List[float]) -> Dict:
        """
        Calcula Z-Score para el último valor en la serie histórica.
        Retorna dict con z_score, mean, std, alert, severity.
        """
        if len(history) < self.window:
            return {
                "z_score": 0.0,
                "mean": float(np.mean(history)) if history else 0,
                "std": float(np.std(history)) if history else 0,
                "alert": False,
                "severity": "INSUFFICIENT_DATA",
            }

        window_values = history[-self.window:]
        mean = float(np.mean(window_values))
        std = float(np.std(window_values))

        if std < 0.01:
            return {"z_score": 0.0, "mean": mean, "std": std, "alert": False, "severity": "STABLE"}

        latest = history[-1]
        z_score = (latest - mean) / std

        if abs(z_score) > self.z_threshold:
            severity = "HIGH" if abs(z_score) > 3.5 else "MODERATE"
            logger.warning(f"[ZScore] Z={z_score:.2f} | mean={mean:.1f} | latest={latest:.1f} | {severity}")
            return {
                "z_score": round(z_score, 2),
                "mean": round(mean, 2),
                "std": round(std, 2),
                "alert": True,
                "severity": severity,
            }

        return {
            "z_score": round(z_score, 2),
            "mean": round(mean, 2),
            "std": round(std, 2),
            "alert": False,
            "severity": "NORMAL",
        }


class DynamicWeightDecay:
    """
    Pesos dinámicos por confianza (Data Decay).
    Si una fuente deja de responder, reduce su peso en 5% por hora sin update.
    Redistribuye el peso perdido entre las fuentes activas.
    """

    def __init__(self, base_weights: Dict[str, float], decay_rate: float = 0.05):
        self.base_weights = base_weights
        self.decay_rate = decay_rate
        self.last_seen: Dict[str, Optional[datetime]] = {
            k: datetime.now(timezone.utc) for k in base_weights
        }

    def record_update(self, kpi: str):
        """Registra que una fuente acaba de actualizarse."""
        self.last_seen[kpi] = datetime.now(timezone.utc)

    def get_effective_weights(self) -> Dict[str, float]:
        """
        Calcula pesos efectivos basados en frescura.
        Retorna dict {kpi: weight_efectivo}.
        """
        now = datetime.now(timezone.utc)
        effective = {}
        total_decay = 0.0

        for kpi, base in self.base_weights.items():
            last = self.last_seen.get(kpi)
            if last is None:
                decay_factor = 0.0
            else:
                hours_stale = max(0.0, (now - last).total_seconds() / 3600)
                decay_factor = max(0.0, 1.0 - self.decay_rate * hours_stale)

            effective[kpi] = base * decay_factor
            total_decay += base * (1.0 - decay_factor)

        # Redistribuir peso perdido entre fuentes con decay_factor > 0
        active_bases = sum(
            self.base_weights[k] for k, v in effective.items() if v > 0
        )
        if active_bases > 0 and total_decay > 0:
            for kpi in effective:
                if effective[kpi] > 0:
                    effective[kpi] += total_decay * (
                        self.base_weights[kpi] / active_bases
                    )

        return {k: round(v, 4) for k, v in effective.items()}

    def get_decay_report(self) -> Dict:
        """Retorna reporte de decaimiento para el frontend."""
        now = datetime.now(timezone.utc)
        report = {}
        for kpi, base in self.base_weights.items():
            last = self.last_seen.get(kpi)
            hours_since = (now - last).total_seconds() / 3600 if last else 999
            report[kpi] = {
                "base_weight": base,
                "hours_since_update": round(hours_since, 1),
                "effective_weight": self.get_effective_weights().get(kpi, 0),
                "confidence": max(0, 100 - int(hours_since * 5)),
            }
        return report


class ExponentiallyWeightedMA:
    """
    Suavizado Exponencial (EMA) para indicadores erráticos.
    Alpha más alto = más peso a datos recientes.
    """

    def __init__(self, alpha: float = 0.3):
        """
        Args:
            alpha: Factor de suavizado (0-1). Default 0.3.
                   Mayor valor = más sensible a cambios recientes.
        """
        self.alpha = alpha
        self._ema: Optional[float] = None

    def smooth(self, value: float) -> float:
        """Aplica EMA a un nuevo valor. Retorna el valor suavizado."""
        v = float(value)
        if self._ema is None:
            self._ema = v
        else:
            self._ema = self.alpha * v + (1.0 - self.alpha) * self._ema
        return round(float(self._ema), 2)

    def reset(self):
        self._ema = None


# Singleton para decay weights
_decay_weights = None


def get_decay_weights():
    global _decay_weights
    if _decay_weights is None:
        _decay_weights = DynamicWeightDecay(settings.KPI_WEIGHTS)
    return _decay_weights


# Instancia global EMA para CRI
_cri_ema = None


def get_cri_ema():
    global _cri_ema
    if _cri_ema is None:
        _cri_ema = ExponentiallyWeightedMA(alpha=0.3)
    return _cri_ema


# Instancia Z-Score
_zscore = None


def get_zscore():
    global _zscore
    if _zscore is None:
        _zscore = ZScoreVolatility()
    return _zscore
