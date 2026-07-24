"""Modelos SQLAlchemy para TelemetryRecord y RiskIndex."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Numeric, Uuid
from app.database import Base

class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    record_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_code = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    raw_value = Column(Numeric(14, 4), nullable=False)
    normalized_score = Column(Numeric(5, 2), nullable=True)
    data_source = Column(String(50), nullable=True)  # 'SEC', 'RunPod', 'Vast.ai', 'Scraper'
    freshness_flag = Column(String(20), nullable=True, default="FRESH")  # FRESH, STALE

class RiskIndex(Base):
    __tablename__ = "risk_indices"

    index_id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    cri_score = Column(Numeric(5, 2), nullable=False)
    risk_zone = Column(String(20), nullable=False)  # LOW, MODERATE, CRITICAL
    alerts_triggered = Column(String(5), nullable=False, default="false")
    component_scores = Column(String(500), nullable=True)  # JSON string
