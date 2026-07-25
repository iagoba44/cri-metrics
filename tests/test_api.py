"""Tests para API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_list_scenarios():
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["scenarios"]) >= 11
    ids = [s["id"] for s in data["scenarios"]]
    assert "ai_utopia" in ids
    assert "supply_crisis" in ids

def test_get_mode():
    response = client.get("/api/v1/mode")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] in ["REAL", "SIMULATION"]

def test_set_mode():
    response = client.post("/api/v1/mode", json={"mode": "REAL"})
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "REAL"

def test_explanations():
    response = client.get("/api/v1/explanations")
    assert response.status_code == 200
    data = response.json()
    assert "cri_score" in data["explanations"]
    assert "GSPI" in data["explanations"]

def test_source_weights():
    response = client.get("/api/v1/source-weights")
    assert response.status_code == 200
    data = response.json()
    assert "weights" in data

def test_root_redirect():
    response = client.get("/")
    assert response.status_code in (200, 307)
    if response.status_code == 307:
        assert response.headers["location"] == "/static/index.html"
