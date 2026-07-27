"""Repository pattern para acceso a datos."""
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import TelemetryRecord, RiskIndex, TMISnapshot

class TelemetryRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_latest_for_kpi(self, kpi_code: str) -> Optional[TelemetryRecord]:
        return (self.db.query(TelemetryRecord)
                .filter(TelemetryRecord.kpi_code == kpi_code)
                .order_by(TelemetryRecord.timestamp.desc())
                .first())
    
    def get_latest_for_all_kpis(self, kpi_codes: List[str]) -> dict:
        return {k: self.get_latest_for_kpi(k) for k in kpi_codes}
    
    def add(self, record):
        self.db.add(record)
    
    def commit(self):
        self.db.commit()

class RiskIndexRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_latest(self) -> Optional[RiskIndex]:
        return self.db.query(RiskIndex).order_by(RiskIndex.timestamp.desc()).first()
    
    def get_history(self, days: int = 24, hours: bool = False) -> List[RiskIndex]:
        delta = timedelta(hours=days) if hours else timedelta(days=days)
        cutoff = datetime.now(timezone.utc) - delta
        return (self.db.query(RiskIndex)
                .filter(RiskIndex.timestamp >= cutoff)
                .order_by(RiskIndex.timestamp.asc())
                .all())
    
    def add(self, risk_index):
        self.db.add(risk_index)
        self.db.commit()
        self.db.refresh(risk_index)
        return risk_index

class TMIRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_latest(self) -> Optional[TMISnapshot]:
        return self.db.query(TMISnapshot).order_by(TMISnapshot.timestamp.desc()).first()
    
    def get_history(self, hours: int = 24) -> List[TMISnapshot]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (self.db.query(TMISnapshot)
                .filter(TMISnapshot.timestamp >= cutoff)
                .order_by(TMISnapshot.timestamp.asc())
                .all())
    
    def add(self, snapshot):
        self.db.add(snapshot)
        self.db.commit()
