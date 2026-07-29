"""Configuración de pytest y overrides de dependencias."""
import pytest
from app.main import app
from app.services.auth import get_current_user

@pytest.fixture(autouse=True)
def override_auth():
    # Override de get_current_user para evitar 401 en los tests
    app.dependency_overrides[get_current_user] = lambda: "admin"
    yield
    # Limpiar overrides después del test
    app.dependency_overrides.clear()
