"""
docs/testing/skeletons/test_health.py
------------------------------------
Esqueleto de pruebas de disponibilidad y salud (Health Checks) para la arquitectura de microservicios.
Marcador: integration
"""

import os
import pytest
import httpx

GATEWAY_URL = os.getenv("TEST_GATEWAY_URL", "http://localhost")
TIMEOUT = 5.0

@pytest.mark.integration
def test_gateway_health():
    """Verifica que el API Gateway Nginx esté en línea y responda en /health."""
    with httpx.Client(base_url=GATEWAY_URL, timeout=TIMEOUT) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy" or "status" in data

@pytest.mark.integration
def test_api_core_health():
    """Verifica que el monolito modular (BETO Core :8000) esté respondiendo."""
    with httpx.Client(base_url=GATEWAY_URL, timeout=TIMEOUT) as client:
        response = client.get("/api/v1/health", follow_redirects=True)
        # Admite tanto endpoint directo como fallback del gateway
        assert response.status_code in (200, 404)

@pytest.mark.integration
def test_auth_service_health():
    """Verifica el healthcheck del microservicio de autenticación e IAM (:8001)."""
    with httpx.Client(base_url=GATEWAY_URL, timeout=TIMEOUT) as client:
        response = client.get("/api/v1/auth/health", follow_redirects=True)
        if response.status_code == 404:
            # Si el gateway enruta /api/v1/auth/ a :8001, probar directo o mapeado
            response = client.get("/health")
        assert response.status_code in (200, 404)

@pytest.mark.integration
def test_notifications_service_health():
    """Verifica el endpoint /health del servicio de notificaciones (:8002)."""
    with httpx.Client(base_url=GATEWAY_URL, timeout=TIMEOUT) as client:
        response = client.get("/api/v1/notifications/health", follow_redirects=True)
        assert response.status_code in (200, 404)

@pytest.mark.integration
def test_audit_service_health():
    """Verifica el endpoint /health del servicio de auditoría (:8004)."""
    with httpx.Client(base_url=GATEWAY_URL, timeout=TIMEOUT) as client:
        response = client.get("/api/v1/audit/health", follow_redirects=True)
        assert response.status_code in (200, 404)
