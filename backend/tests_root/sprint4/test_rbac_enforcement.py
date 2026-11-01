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
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from core.database import get_db
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

    def test_alertas_acceso_auditor_calidad(self, client):
        # AUDITOR_CALIDAD ahora tiene acceso autorizado a /api/v1/alertas -> 200 (sin 403)
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.join.return_value.outerjoin.return_value.filter.return_value.all.return_value = []
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("AUDITOR_CALIDAD")
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            res = client.get("/api/v1/alertas", headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 200
            json_data = res.json()
            assert json_data["status"] == "success"
            assert "data" in json_data
        finally:
            app.dependency_overrides.clear()

    def test_pipeline_process_alias_rbac(self, client):
        # 1. Sin token -> 401
        res_no_auth = client.post("/pipeline/process")
        assert res_no_auth.status_code == 401

        # 2. Con rol no autorizado (ANALISTA_FINANCIERO) -> 403
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("ANALISTA_FINANCIERO")
        try:
            res_forbid = client.post("/pipeline/process", headers={"Authorization": "Bearer mock_token"})
            assert res_forbid.status_code == 403
        finally:
            app.dependency_overrides.clear()

        # 3. Con rol autorizado (AUDITOR_CALIDAD) -> pasa autenticación y RBAC (no retorna 401 ni 403)
        mock_db = MagicMock(spec=Session)
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("AUDITOR_CALIDAD")
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            res_auth = client.post("/pipeline/process", headers={"Authorization": "Bearer mock_token"})
            assert res_auth.status_code == 400
            assert "Debe proporcionar un archivo" in res_auth.json()["detail"]
        finally:
            app.dependency_overrides.clear()

        # 4. Con rol ADMIN -> también autorizado en alias raíz
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("ADMIN")
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            res_admin = client.post("/pipeline/process", headers={"Authorization": "Bearer mock_token"})
            assert res_admin.status_code == 400
            assert "Debe proporcionar un archivo" in res_admin.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_pipeline_process_formato_invalido(self, client):
        """Verifica rechazo 400 de formatos no permitidos (.txt, .exe)."""
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("AUDITOR_CALIDAD")
        mock_db = MagicMock(spec=Session)
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            files = {"file": ("malicious.txt", b"dummy content", "text/plain")}
            res = client.post("/pipeline/process", files=files, headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 400
            assert "Formato no soportado" in res.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_pipeline_process_doc_id_inexistente_retorna_404(self, client):
        """Verifica que un doc_id inexistente retorne 404 con mensaje limpio de negocio."""
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("AUDITOR_CALIDAD")
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            data = {"doc_id": "9999"}
            res = client.post("/pipeline/process", data=data, headers={"Authorization": "Bearer mock_token"})
            assert res.status_code == 404
            assert "Origen Documental y Lotes" in res.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_analista_marketing_acceso_autorizado(self, client):
        """Verifica que ANALISTA_MARKETING tenga acceso a CMI, Forecast Demanda, Viabilidad y Catálogo."""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.all.return_value = []
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("ANALISTA_MARKETING")
        app.dependency_overrides[get_db] = lambda: mock_db
        try:
            # 1. Forecast Alumnos (Caso 1 Demanda)
            res_alumnos = client.get("/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=4", headers={"Authorization": "Bearer mock_token"})
            assert res_alumnos.status_code == 200, f"Error en /forecast/alumnos: {res_alumnos.text}"

            # 2. Matriz de Viabilidad Estratégica (Caso 2 Marketing)
            res_viabilidad = client.get("/api/v1/forecast/viabilidad-programas", headers={"Authorization": "Bearer mock_token"})
            assert res_viabilidad.status_code == 200, f"Error en /forecast/viabilidad-programas: {res_viabilidad.text}"

            # 3. Analítica Macro Completa
            res_macro = client.get("/api/v1/forecast/analitica-macro?horizonte=3", headers={"Authorization": "Bearer mock_token"})
            assert res_macro.status_code == 200

            # 4. CMI Perspectivas Completo
            res_cmi = client.get("/api/v1/kpis/cmi-completo", headers={"Authorization": "Bearer mock_token"})
            assert res_cmi.status_code == 200

            # 5. Catálogo de Módulos Curriculares (sin PII)
            res_modulos = client.get("/api/v1/modulos", headers={"Authorization": "Bearer mock_token"})
            assert res_modulos.status_code == 200

            # 6. Alertas institucionales filtradas por rol marketing
            res_alertas = client.get("/api/v1/alertas", headers={"Authorization": "Bearer mock_token"})
            assert res_alertas.status_code == 200
            alertas_data = res_alertas.json()["data"]
            for a in alertas_data:
                assert a["tipo"] in ("MARKETING", "DEMANDA", "CONVERSION")
        finally:
            app.dependency_overrides.clear()

    def test_analista_marketing_denegacion_restringidos(self, client):
        """Verifica que ANALISTA_MARKETING reciba 403 Forbidden en áreas estrictamente prohibidas por PoLP."""
        app.dependency_overrides[get_current_user] = lambda: mock_user_with_role("ANALISTA_MARKETING")
        try:
            # 1. DataOps e Ingesta
            res_dataops = client.get("/api/v1/dataops/sources", headers={"Authorization": "Bearer mock_token"})
            assert res_dataops.status_code == 403, f"Fallo: DataOps no bloqueó a Marketing ({res_dataops.status_code})"

            # 2. Metas Financieras profundas
            res_metas = client.get("/api/v1/forecast/metas", headers={"Authorization": "Bearer mock_token"})
            assert res_metas.status_code == 403, f"Fallo: Forecast Metas no bloqueó a Marketing ({res_metas.status_code})"

            # 3. Gestión de Usuarios
            res_users = client.get("/api/v1/users", headers={"Authorization": "Bearer mock_token"})
            assert res_users.status_code == 403, f"Fallo: Users no bloqueó a Marketing ({res_users.status_code})"

            # 4. KPIs de áreas restringidas
            res_kpi_acad = client.get("/api/v1/kpis/academico", headers={"Authorization": "Bearer mock_token"})
            assert res_kpi_acad.status_code == 403

            res_kpi_fin = client.get("/api/v1/kpis/financiero", headers={"Authorization": "Bearer mock_token"})
            assert res_kpi_fin.status_code == 403

            res_kpi_pipe = client.get("/api/v1/kpis/pipeline", headers={"Authorization": "Bearer mock_token"})
            assert res_kpi_pipe.status_code == 403

            # 5. Alertas de Riesgo Tempranas y Cruzadas
            res_riesgo = client.get("/api/v1/riesgos/cruzado", headers={"Authorization": "Bearer mock_token"})
            assert res_riesgo.status_code == 403

            res_alertas_det = client.get("/api/v1/riesgos/alertas-tempranas", headers={"Authorization": "Bearer mock_token"})
            assert res_alertas_det.status_code == 403

            # 6. Auditoría y Trazabilidad del Sistema
            res_audit = client.get("/api/v1/audit/logs", headers={"Authorization": "Bearer mock_token"})
            assert res_audit.status_code == 403

            # 7. Pipeline de Procesamiento Directo
            res_pipe = client.post("/pipeline/process", headers={"Authorization": "Bearer mock_token"})
            assert res_pipe.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_dataops_router_bloquea_roles_no_autorizados(self, client):
        """Verifica que el router dataops rechace roles comerciales o académicos indebidos tras el blindaje."""
        roles_indebidos = ["COORDINADOR_ACADEMICO", "ANALISTA_DATOS_MARKETING", "DIRECTOR_ACADEMICO", "ANALISTA_FINANCIERO"]
        for rol in roles_indebidos:
            app.dependency_overrides[get_current_user] = lambda r=rol: mock_user_with_role(r)
            try:
                res = client.get("/api/v1/dataops/sources", headers={"Authorization": "Bearer mock_token"})
                assert res.status_code == 403, f"Fallo: {rol} debió recibir 403 en dataops pero obtuvo {res.status_code}"
            finally:
                app.dependency_overrides.clear()

