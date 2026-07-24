"""Tests para el motor de calculo CRI.
Valida Regla 3 (Ponderacion) y Escenarios de Aceptacion.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import TelemetryRecord, RiskIndex
from app.services.calculator import CRICalculator

# Base de datos en memoria para tests
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

class TestCRICalculator:
    """Valida Regla 3 (Ponderacion) y Escenarios de Aceptacion."""

    def _insert_telemetry(self, db, kpi, raw, ts=None):
        rec = TelemetryRecord(
            kpi_code=kpi,
            timestamp=ts or datetime.now(timezone.utc),
            raw_value=Decimal(str(raw)),
            data_source="TEST",
        )
        db.add(rec)
        db.commit()
        return rec

    def test_weighted_calculation_moderate(self, db):
        """Escenario 1: Valores equilibrados -> CRI moderado."""
        # Con bounds actualizados (SHPD max=100), para score=50 en cada KPI:
        self._insert_telemetry(db, "GSPI", 50.0)
        self._insert_telemetry(db, "SHPD", 50.0)  # score 50 con max=100
        self._insert_telemetry(db, "LTCR", 50.0)
        self._insert_telemetry(db, "CFBR", 50.0)
        self._insert_telemetry(db, "UOR", 50.0)

        calc = CRICalculator(db)
        risk_index, meta = calc.calculate()

        # CRI esperado = 50.0 -> MODERATE
        assert float(risk_index.cri_score) == pytest.approx(50.0, abs=0.5)
        assert risk_index.risk_zone == "MODERATE"
        assert risk_index.alerts_triggered == "false"

    def test_critical_alert_scenario(self, db):
        """Escenario 2: Valores altos de riesgo -> CRITICAL."""
        # GSPI=90 -> score 90 (alta deflacion)
        self._insert_telemetry(db, "GSPI", 90.0)
        # CFBR=90 -> score 90
        self._insert_telemetry(db, "CFBR", 90.0)
        # Rellenar el resto con valores altos
        self._insert_telemetry(db, "SHPD", 80.0)  # score 80
        self._insert_telemetry(db, "LTCR", 80.0)  # score 80
        self._insert_telemetry(db, "UOR", 80.0)   # score 80

        calc = CRICalculator(db)
        risk_index, meta = calc.calculate()

        # CRI = 90*0.25 + 80*0.15 + 80*0.20 + 90*0.20 + 80*0.20 = 22.5+12+16+18+16 = 84.5
        assert float(risk_index.cri_score) > 65.0
        assert risk_index.risk_zone == "CRITICAL"
        assert risk_index.alerts_triggered == "true"

    def test_missing_data_uses_last_valid(self, db):
        """MISSING_DATA: usa ultimo registro valido si no hay datos frescos."""
        old_ts = datetime.now(timezone.utc) - timedelta(hours=48)
        self._insert_telemetry(db, "GSPI", 50.0, old_ts)
        self._insert_telemetry(db, "SHPD", 50.0, old_ts)
        self._insert_telemetry(db, "LTCR", 50.0, old_ts)
        self._insert_telemetry(db, "CFBR", 50.0, old_ts)
        self._insert_telemetry(db, "UOR", 50.0, old_ts)

        calc = CRICalculator(db)
        risk_index, meta = calc.calculate()

        # Debe completar el calculo aunque todos esten stale
        assert risk_index is not None
        assert "component_details" in meta
        for k, v in meta["component_details"].items():
            assert v["freshness"] == "STALE"
