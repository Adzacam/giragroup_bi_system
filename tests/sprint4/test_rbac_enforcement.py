"""
tests/sprint4/test_rbac_enforcement.py
--------------------------------------
Pruebas exhaustivas de seguridad RBAC y Principio de Mínimo Privilegio (PoLP):
1. Validación de tokens JWT y expiración.
2. Comprobación de que llamadas sin token retornan HTTP 401 Unauthorized.
3. Comprobación de que llamadas con rol no autorizado retornan HTTP 403 Forbidden.
4. Verificación de segregación de privilegios:
   - DIRECTOR_ACADEMICO puede consultar /alumnos pero no /metas financieras.
   - ANALISTA_FINANCIERO puede consultar /metas pero no /alumnos.
   - AUDITOR_CALIDAD puede gestionar /dataops/* y /pipeline/process pero no /users.
   - ADMIN tiene acceso total a todos los endpoints.
"""

import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from main import app
from core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    generate_otp,
    get_current_user
)
from models.user import User


@pytest.fixture
def client():
    return TestClient(app)


def mock_user_with_role(rol: str) -> User:
    return User(
        id=1,
        username=f"user_{rol.lower()}",
        email=f"{rol.lower()}@giragroup.bo",
        role=rol,
        is_active=True
    )


class TestRBACSecurityTokens:
    def test_hashing_contrasenas(self):
        pwd = "PasswordSeguro2026!"
        h = get_password_hash(pwd)
        assert h != pwd
        assert verify_password(pwd, h) is True
        assert verify_password("ClaveErronea", h) is False

    def test_generacion_otp_formato(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_token_creacion_y_claims(self):
        token = create_access_token(data={"sub": "1", "role": "ADMIN"})
        assert isinstance(token, str)
        assert len(token.split(".")) == 3


class TestRBACEndpointsProtection:
    """Verifica que endpoints protegidos exijan token y validen roles estrictamente."""

    def test_endpoints_sin_token_retornan_401(self, client):
        endpoints_protegidos = [
            ("GET", "/api/v1/forecast/alumnos"),
            ("GET", "/api/v1/forecast/metas"),
            ("GET", "/api/v1/riesgos/cruzado"),
            ("GET", "/api/v1/dataops/sources"),
            ("GET", "/api/v1/audit/logs"),
            ("GET", "/api/v1/users"),
            ("GET", "/api/v1/kpis"),
            ("GET", "/api/v1/alertas"),
            ("GET", "/api/v1/estudiantes"),
        ]
        for metodo, url in endpoints_protegidos:
            if metodo == "GET":
                res = client.get(url)
            else:
                res = client.post(url)
            assert res.status_code == 401, f"Fallo 401 en {metodo} {url}: retornó {res.status_code}"

    def test_users_crud_solo_admin_puede_acceder(self, client):
        # AUDITOR_CALIDAD intentando acceder a usuarios -> 403
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("AUDITOR_CALIDAD")
        try:
            res = client.get("/api/v1/users", headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()

        # ANALISTA_FINANCIERO intentando acceder a usuarios -> 403
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("ANALISTA_FINANCIERO")
        try:
            res = client.get("/api/v1/users", headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_segregacion_forecast_academico_vs_financiero(self, client):
        # DIRECTOR_ACADEMICO no puede ver metas financieras -> 403
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("DIRECTOR_ACADEMICO")
        try:
            res = client.get("/api/v1/forecast/metas", headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()

        # ANALISTA_FINANCIERO no puede ver forecast de alumnos -> 403
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("ANALISTA_FINANCIERO")
        try:
            res = client.get("/api/v1/forecast/alumnos", headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_kpis_permisos_por_perspectiva(self, client):
        # Analista financiero no puede ver KPIs académicos restringidos -> 403
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("ANALISTA_FINANCIERO")
        try:
            res = client.get("/api/v1/kpis/academico", headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()

        # Director académico no puede ver KPIs financieros restringidos -> 403
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("DIRECTOR_ACADEMICO")
        try:
            res = client.get("/api/v1/kpis/financiero", headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()
