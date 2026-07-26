"""Motor Predictivo para CRI Metrics v3.0.
Detecta signos de colapso y proyecta Time To Danger (TTD).
Usa:
- Early Warning System (Critical Slowing Down): autocorrelacion lag-1, varianza movil
- Regresion tendencial para proyeccion 30-90 dias
- Aceleracion del riesgo (2ª derivada)
"""
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from scipy import stats
from collections import deque

logger = logging.getLogger(__name__)


class EarlyWarningSystem:
    """
    Detecta transiciones de fase (Critical Slowing Down)
    en sistemas complejos como mercados financieros.
    
    Antes de un colapso:
    - Aumenta la autocorrelacion lag-1 (el sistema tarda mas en recuperarse)
    - Aumenta la varianza movil (oscilaciones mas amplias)
    - La 2ª derivada se hace positiva (aceleracion del riesgo)
    """

    def __init__(self, window: int = 30):
        self.window = window

    def compute(self, history: List[float]) -> Dict:
        """
        Calcula todos los indicadores EWS a partir de una serie historica.
        Retorna dict con autocorrelacion, varianza, aceleracion, y alerta.
        """
        if len(history) < self.window:
            return {
                "status": "insufficient_data",
                "autocorrelation": None,
                "variance": None,
                "acceleration": None,
                "ew_signal": "INSUFFICIENT",
                "days_to_collapse": None,
            }

        window_vals = history[-self.window:]

        # Autocorrelacion lag-1
        acf1 = self._autocorrelation_lag1(window_vals)

        # Varianza movil normalizada
        variance = np.var(window_vals)

        # 2ª derivada (aceleracion)
        acceleration = self._compute_acceleration(history)

        # Time To Danger estimado
        ttd = self._estimate_ttd(history)

        # Senal combinada de Early Warning
        ew_score = self._compute_ew_score(acf1, variance, acceleration)
        signal = "NORMAL" if ew_score < 0.5 else "PRE_ALERT" if ew_score < 0.75 else "CRITICAL"

        return {
            "status": "ok",
            "autocorrelation": round(acf1, 4),
            "variance": round(variance, 4),
            "acceleration": round(acceleration, 4),
            "ew_score": round(ew_score, 4),
            "ew_signal": signal,
            "days_to_collapse": ttd,
            "window": self.window,
        }

    def _autocorrelation_lag1(self, values: List[float]) -> float:
        """Autocorrelacion de lag 1 (Pearson)."""
        if len(values) < 2:
            return 0.0
        x = values[:-1]
        y = values[1:]
        return float(np.corrcoef(x, y)[0, 1])

    def _compute_acceleration(self, history: List[float]) -> float:
        """2ª derivada del CRI: aceleracion del riesgo."""
        if len(history) < 3:
            return 0.0
        # Derivada central: f''(t) ~ f(t+1) - 2*f(t) + f(t-1)
        a1 = history[-1] - 2 * history[-2] + history[-3]
        a2 = history[-2] - 2 * history[-3] + history[-4] if len(history) >= 4 else 0.0
        return float((a1 + a2) / 2.0)

    def _estimate_ttd(self, history: List[float]) -> Optional[int]:
        """
        Estima Time To Danger (TTD): dias hasta que CRI cruce 65.
        Usa regresion lineal simple de los ultimos N puntos.
        """
        if len(history) < 14:
            return None

        window = min(len(history), 30)
        subset = history[-window:]
        x = np.arange(len(subset))
        y = np.array(subset)

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Si la tendencia no es de riesgo (slope negativo o cercano a 0), no hay colapso inminente
        if slope <= 0:
            return None

        current = y[-1]
        gap = 65.0 - current  # Umbral critico

        if gap <= 0:
            return 0  # Ya esta en zona critica

        steps_to_critical = int(gap / slope)
        return max(0, steps_to_critical)

    def _compute_ew_score(
        self, acf1: float, variance: float, acceleration: float
    ) -> float:
        """
        Score combinado de Early Warning (0-1).
        0 = normal, 1 = colapso inminente.
        """
        # Normalizar cada indicador a [0, 1]
        acf_norm = min(1.0, max(0.0, (acf1 - 0.3) / 0.7))  # <0.3 normal, >1 alta
        var_norm = min(1.0, max(0.0, variance / 500.0))     # Escala empirica
        acc_norm = min(1.0, max(0.0, (acceleration + 5) / 10.0))

        return round((acf_norm * 0.4 + var_norm * 0.3 + acc_norm * 0.3), 4)


class TrendProjector:
    """Proyecta el CRI a 30, 60 y 90 dias usando regresion tendencial."""

    def project(self, history: List[float]) -> Dict:
        """
        Genera proyecciones a futuro.
        Retorna dict con valor estimado y probabilidad de colapso.
        """
        if len(history) < 14:
            return {"status": "insufficient_data"}

        window = min(len(history), 60)
        subset = history[-window:]
        x = np.arange(len(subset))
        y = np.array(subset)

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        projections = {}
        for days in [30, 60, 90]:
            future_x = len(subset) + days
            projected_value = intercept + slope * future_x
            projected_value = max(0.0, min(100.0, projected_value))

            # Probabilidad de colapso: basado en cuantos puntos de la
            # banda de confianza > 65
            se = std_err * np.sqrt(future_x)
            z = (65.0 - projected_value) / se if se > 0 else 0
            collapse_prob = round((1 - stats.norm.cdf(z)) * 100, 1)

            projections[str(days)] = {
                "projected_cri": round(projected_value, 2),
                "collapse_probability_pct": collapse_prob,
                "band": {
                    "upper": round(min(100, projected_value + 1.96 * se), 2),
                    "lower": round(max(0, projected_value - 1.96 * se), 2),
                },
            }

        return {
            "status": "ok",
            "slope": round(slope, 4),
            "r_squared": round(r_value ** 2, 4),
            "p_value": round(p_value, 6),
            "std_error": round(std_err, 4),
            "projections": projections,
        }


class PredictiveEngine:
    """Orquesta Early Warning System + Trend Projector."""

    def __init__(self):
        self.ews = EarlyWarningSystem(window=30)
        self.projector = TrendProjector()

    def analyze(self, history: List[float]) -> Dict:
        """
        Analisis completo: EWS + Proyeccion + Resumen ejecutivo.
        """
        if not history or len(history) < 7:
            return {"status": "insufficient_data", "message": "Se necesitan al menos 7 puntos de historial"}

        ews = self.ews.compute(history)
        proj = self.projector.project(history)

        # Resumen ejecutivo
        ttd = ews.get("days_to_collapse")
        coll_pct = proj.get("projections", {}).get("30", {}).get("collapse_probability_pct", 0)
        signal = ews.get("ew_signal", "NORMAL")

        summary = self._build_summary(ttd, coll_pct, signal, history)

        return {
            "status": "ok",
            "current_cri": history[-1],
            "history_points": len(history),
            "early_warning": ews,
            "projections": proj,
            "summary": summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _build_summary(self, ttd: Optional[int], coll_pct: float, signal: str, history: List[float]) -> str:
        if signal == "CRITICAL":
            return f"ALERTA CRITICA: Signos de colapso inminente. Probabilidad {coll_pct}% a 30 dias."
        elif signal == "PRE_ALERT":
            if ttd:
                return f"PRE-ALERTA: Aceleracion de riesgo detectada. ~{ttd} dias al umbral critico si la tendencia continua."
            return f"PRE-ALERTA: Varianza y autocorrelacion elevadas. Monitorear de cerca."
        else:
            if ttd:
                return f"Sistema estable. ~{ttd} dias proyectados al umbral critico con tendencia actual."
            return f"Sistema estable. Sin signos de transicion de fase. CRI={history[-1]:.1f}."


# Singleton
_engine = None

def get_predictive_engine() -> PredictiveEngine:
    global _engine
    if _engine is None:
        _engine = PredictiveEngine()
    return _engine
