"""Tests de integración para endpoints API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

class TestAPI:
    def test_health_check(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_calculate_cri_no_data(self):
        """Debe fallar si no hay telemetría."""
        response = client.post("/api/v1/calculate-cri")
        assert response.status_code == 400
        assert "telemetría" in response.json()["detail"].lower() or "datos" in response.json()["detail"].lower()

    def test_ingest_and_calculate(self):
        """Flujo completo: ingestar → calcular → verificar respuesta."""
        payload = {
            "records": [
                {"kpi_code": "GSPI", "raw_value": 30.0, "data_source": "TEST"},
                {"kpi_code": "SHPD", "raw_value": 20.0, "data_source": "TEST"},
                {"kpi_code": "LTCR", "raw_value": 40.0, "data_source": "TEST"},
                {"kpi_code": "CFBR", "raw_value": 60.0, "data_source": "TEST"},
                {"kpi_code": "UOR", "raw_value": 50.0, "data_source": "TEST"},
            ]
        }
        r1 = client.post("/api/v1/ingest", json=payload)
        assert r1.status_code == 200
        assert r1.json()["inserted"] == 5

        r2 = client.post("/api/v1/calculate-cri")
        assert r2.status_code == 200
        data = r2.json()["data"]
        assert "cri_score" in data
        assert "risk_zone" in data
        assert data["risk_zone"] in ["LOW", "MODERATE", "CRITICAL"]

    def test_latest_cri(self):
        """Obtener último CRI calculado."""
        # Primero ingestar y calcular
        payload = {
            "records": [
                {"kpi_code": "GSPI", "raw_value": 10.0, "data_source": "TEST"},
                {"kpi_code": "SHPD", "raw_value": 10.0, "data_source": "TEST"},
                {"kpi_code": "LTCR", "raw_value": 10.0, "data_source": "TEST"},
                {"kpi_code": "CFBR", "raw_value": 10.0, "data_source": "TEST"},
                {"kpi_code": "UOR", "raw_value": 10.0, "data_source": "TEST"},
            ]
        }
        client.post("/api/v1/ingest", json=payload)
        client.post("/api/v1/calculate-cri")

        response = client.get("/api/v1/latest-cri")
        assert response.status_code == 200
        assert response.json()["risk_zone"] == "LOW"
