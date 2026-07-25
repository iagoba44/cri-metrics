"""Motor de cálculo del Índice de Riesgo Compuesto (CRI)."""
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import TelemetryRecord, RiskIndex
from app.config import get_settings
from app.services.normalizer import Normalizer
from app.services.alerts import get_alert_service
import json
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

class CRICalculator:
    """Calcula el CRI a partir de telemetría reciente."""

    def __init__(self, db: Session):
        self.db = db

    def get_latest_telemetry(self) -> Dict[str, TelemetryRecord]:
        """
        Obtiene la lectura más reciente por KPI.
        Si no hay datos frescos (< 24h), usa el último disponible (MISSING_DATA).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.DATA_FRESHNESS_HOURS)
        latest_by_kpi: Dict[str, TelemetryRecord] = {}

        for kpi in settings.KPI_WEIGHTS.keys():
            # Buscar registro fresco
            record = (
                self.db.query(TelemetryRecord)
                .filter(TelemetryRecord.kpi_code == kpi)
                .filter(TelemetryRecord.timestamp >= cutoff)
                .order_by(TelemetryRecord.timestamp.desc())
                .first()
            )

            if record:
                record.freshness_flag = "FRESH"
            else:
                # MISSING_DATA: usar último registro válido disponible
                record = (
                    self.db.query(TelemetryRecord)
                    .filter(TelemetryRecord.kpi_code == kpi)
                    .order_by(TelemetryRecord.timestamp.desc())
                    .first()
                )
                if record:
                    record.freshness_flag = "STALE"
                    logger.warning(f"MISSING_DATA para {kpi}. Usando último registro de {record.timestamp}")
                else:
                    logger.error(f"No hay datos históricos para {kpi}. KPI omitido.")
                    continue

            latest_by_kpi[kpi] = record

        return latest_by_kpi

    def calculate(self) -> Tuple[RiskIndex, Dict]:
        """
        Ejecuta el pipeline completo de cálculo CRI.
        Retorna: (RiskIndex, metadata)
        """
        latest = self.get_latest_telemetry()

        if not latest:
            raise ValueError("No hay telemetría disponible para calcular CRI")

        # Normalizar cada KPI
        normalized_scores: Dict[str, Decimal] = {}
        component_details = {}

        for kpi, record in latest.items():
            raw = Decimal(str(record.raw_value))
            score = Normalizer.normalize(kpi, raw)
            normalized_scores[kpi] = score

            # Actualizar registro con score normalizado
            record.normalized_score = score
            self.db.add(record)

            component_details[kpi] = {
                "raw_value": float(raw),
                "normalized_score": float(score),
                "weight": settings.KPI_WEIGHTS[kpi],
                "freshness": record.freshness_flag,
            }

        # Calcular CRI ponderado
        cri_score = Decimal("0.00")
        for kpi, score in normalized_scores.items():
            weight = Decimal(str(settings.KPI_WEIGHTS[kpi]))
            cri_score += score * weight

        cri_score = cri_score.quantize(Decimal("0.01"))
        cri_score = Decimal(str(min(max(cri_score, Decimal("0.00")), Decimal("100.00"))))

        # Determinar zona de riesgo
        cri_float = float(cri_score)
        if cri_float <= 30:
            risk_zone = "LOW"
        elif cri_float <= 65:
            risk_zone = "MODERATE"
        else:
            risk_zone = "CRITICAL"

        alerts_triggered = risk_zone == "CRITICAL"

        # Crear registro RiskIndex
        risk_index = RiskIndex(
            cri_score=cri_score,
            risk_zone=risk_zone,
            alerts_triggered=str(alerts_triggered).lower(),
            component_scores=json.dumps(component_details),
        )

        self.db.add(risk_index)
        self.db.commit()
        self.db.refresh(risk_index)

        # Disparar alertas si aplica
        if alerts_triggered:
            get_alert_service().check_and_alert(cri_float)

        metadata = {
            "component_details": component_details,
            "missing_kpis": [k for k in settings.KPI_WEIGHTS if k not in latest],
            "alerts_triggered": alerts_triggered,
        }

        return risk_index, metadata
