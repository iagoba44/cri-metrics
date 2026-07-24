"""Tests para pipeline de ingesta."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.services.ingestion import IngestionPipeline

engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

class TestIngestion:
    def test_ingest_batch(self, db):
        pipeline = IngestionPipeline(db)
        records = [
            {"kpi_code": "GSPI", "raw_value": 25.5, "timestamp": datetime.now(timezone.utc), "data_source": "SEC"},
            {"kpi_code": "CFBR", "raw_value": 75.0, "timestamp": datetime.now(timezone.utc), "data_source": "VAST"},
        ]
        count = pipeline.ingest_batch(records)
        assert count == 2

    def test_ingest_batch_partial_failure(self, db):
        """Un registro malformado no debe bloquear el resto."""
        pipeline = IngestionPipeline(db)
        records = [
            {"kpi_code": "GSPI", "raw_value": 25.5},
            {"kpi_code": "INVALID", "raw_value": "not_a_number"},  # fallará
            {"kpi_code": "UOR", "raw_value": 40.0},
        ]
        count = pipeline.ingest_batch(records)
        assert count == 2  # 2 válidos
