"""
tests/test_reportes_export.py
-----------------------------
Pruebas para el endpoint de exportación institucional (HU-12):
GET /api/v1/reportes/export?tipo={kpis|alertas|cierre}&formato={xlsx|pdf}

1. Autenticación obligatoria (401 sin token).
2. Validación de parámetros (400 en tipo o formato inválido).
3. RBAC granular por rol (PoLP).
4. Exportación en XLSX y PDF con validación de cabeceras y bytes binarios.
5. Inserción obligatoria de auditoría en log_pipeline_ingesta con etapa='EXPORT'.
"""

import io
import sys
from pathlib import Path
import pytest
import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from core.security import get_current_user
from core.database import Base, get_db
from models.user import User
from models.log_pipeline import LogPipelineIngesta

# ── Base de datos de pruebas en memoria (SQLite) con esquema public ─────────
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

@event.listens_for(test_engine, "connect")
def do_connect(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("ATTACH DATABASE ':memory:' AS public")
    cursor.close()

Base.metadata.create_all(bind=test_engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def mock_user(rol: str, username: str = "test_user") -> User:
    return User(
        id=99,
        username=username,
        email=f"{username}@giragroup.bo",
        role=rol,
        is_active=True
    )


class TestExportReportesRBAC:
    def test_export_sin_token_retorna_401(self, client):
        """Petición anónima debe ser rechazada con HTTP 401."""
        res = client.get("/api/v1/reportes/export?tipo=kpis&formato=xlsx")
        assert res.status_code == 401

    def test_export_parametros_invalidos_retorna_400(self, client):
        """Parámetros tipo o formato no soportados retornan HTTP 400."""
        app.dependency_overrides[get_current_user] = lambda: mock_user("ADMIN")
        try:
            # Tipo inválido
            res1 = client.get("/api/v1/reportes/export?tipo=invalido&formato=xlsx")
            assert res1.status_code == 400
            assert "Tipo de reporte inválido" in res1.json()["detail"]

            # Formato inválido
            res2 = client.get("/api/v1/reportes/export?tipo=kpis&formato=csv_raw")
            assert res2.status_code == 400
            assert "Formato de exportación no soportado" in res2.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_export_rol_no_autorizado_retorna_403(self, client):
        """Un rol ajeno a la gestión directiva/analítica no puede exportar (HTTP 403)."""
        app.dependency_overrides[get_current_user] = lambda: mock_user("INVITADO_EXTERNO")
        try:
            res = client.get("/api/v1/reportes/export?tipo=kpis&formato=xlsx")
            assert res.status_code == 403
            assert "No tiene permisos suficientes" in res.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_export_kpis_xlsx_admin_con_auditoria_log(self, client):
        """ADMIN puede exportar KPIs en XLSX; se registra en log_pipeline_ingesta con etapa='EXPORT'."""
        app.dependency_overrides[get_current_user] = lambda: mock_user("ADMIN", username="superadmin")
        try:
            res = client.get("/api/v1/reportes/export?tipo=kpis&formato=xlsx")
            assert res.status_code == 200
            assert "spreadsheetml" in res.headers["content-type"]
            assert "attachment; filename=" in res.headers["content-disposition"]
            assert res.headers["content-disposition"].endswith('.xlsx"')

            # Verificar que sea un archivo Excel válido
            wb = openpyxl.load_workbook(io.BytesIO(res.content))
            assert len(wb.sheetnames) > 0
            ws = wb.active
            assert "GIRAGROUP BI SYSTEM" in str(ws["A1"].value)

            # Verificar inserción de auditoría en log_pipeline_ingesta
            db = TestingSessionLocal()
            log_entry = db.query(LogPipelineIngesta).filter(
                LogPipelineIngesta.etapa == "EXPORT"
            ).order_by(LogPipelineIngesta.id.desc()).first()
            assert log_entry is not None
            assert log_entry.nivel == "SUCCESS"
            assert log_entry.modulo == "REPORTES_EXPORT"
            assert "superadmin" in log_entry.mensaje
            assert log_entry.metadata_json["formato"] == "xlsx"
            assert log_entry.metadata_json["tipo"] == "kpis"
            db.close()
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_export_alertas_pdf_director_academico(self, client):
        """DIRECTOR_ACADEMICO exporta alertas en formato PDF (verificando firma de archivo PDF)."""
        app.dependency_overrides[get_current_user] = lambda: mock_user("DIRECTOR_ACADEMICO", username="director_aca")
        try:
            res = client.get("/api/v1/reportes/export?tipo=alertas&formato=pdf")
            assert res.status_code == 200
            assert res.headers["content-type"] == "application/pdf"
            assert "attachment; filename=" in res.headers["content-disposition"]
            assert res.headers["content-disposition"].endswith('.pdf"')

            # Verificar firma de archivo PDF (%PDF)
            assert res.content.startswith(b"%PDF")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_export_cierre_polp_segregacion(self, client):
        """
        DIRECTOR_ACADEMICO y AUDITOR_CALIDAD exportando Cierre reciben montos financieros restringidos [RESTRINGIDO PoLP],
        mientras ANALISTA_FINANCIERO recibe montos expresados en Bs.
        """
        # 1. DIRECTOR_ACADEMICO
        app.dependency_overrides[get_current_user] = lambda: mock_user("DIRECTOR_ACADEMICO", username="director_aca")
        try:
            res_aca = client.get("/api/v1/reportes/export?tipo=cierre&formato=xlsx")
            assert res_aca.status_code == 200
            wb_aca = openpyxl.load_workbook(io.BytesIO(res_aca.content))
            ws_aca = wb_aca.active
            # Buscar en las celdas de recaudación
            valores_aca = [str(cell.value) for row in ws_aca.iter_rows() for cell in row]
            assert any("[RESTRINGIDO PoLP]" in v for v in valores_aca)
            assert not any("Bs." in v for v in valores_aca)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # 2. AUDITOR_CALIDAD (también debe tener montos restringidos)
        app.dependency_overrides[get_current_user] = lambda: mock_user("AUDITOR_CALIDAD", username="auditor_cal")
        try:
            res_aud = client.get("/api/v1/reportes/export?tipo=cierre&formato=xlsx")
            assert res_aud.status_code == 200
            wb_aud = openpyxl.load_workbook(io.BytesIO(res_aud.content))
            ws_aud = wb_aud.active
            valores_aud = [str(cell.value) for row in ws_aud.iter_rows() for cell in row]
            assert any("[RESTRINGIDO PoLP]" in v for v in valores_aud)
            assert not any("Bs." in v for v in valores_aud)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # 3. ANALISTA_FINANCIERO (ve montos en Bs.)
        app.dependency_overrides[get_current_user] = lambda: mock_user("ANALISTA_FINANCIERO", username="analista_fin")
        try:
            res_fin = client.get("/api/v1/reportes/export?tipo=cierre&formato=xlsx")
            assert res_fin.status_code == 200
            wb_fin = openpyxl.load_workbook(io.BytesIO(res_fin.content))
            ws_fin = wb_fin.active
            valores_fin = [str(cell.value) for row in ws_fin.iter_rows() for cell in row]
            assert any("Bs." in v for v in valores_fin)
            assert not any("[RESTRINGIDO PoLP]" in v for v in valores_fin)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_export_kpis_polp_segregacion(self, client):
        """
        DIRECTOR_ACADEMICO exportando KPIs recibe montos financieros restringidos [RESTRINGIDO PoLP],
        mientras ANALISTA_FINANCIERO ve cifras en Bs.
        """
        # DIRECTOR_ACADEMICO
        app.dependency_overrides[get_current_user] = lambda: mock_user("DIRECTOR_ACADEMICO", username="director_aca")
        try:
            res = client.get("/api/v1/reportes/export?tipo=kpis&formato=xlsx")
            assert res.status_code == 200
            wb = openpyxl.load_workbook(io.BytesIO(res.content))
            ws = wb.active
            valores = [str(cell.value) for row in ws.iter_rows() for cell in row]
            assert any("[RESTRINGIDO PoLP]" in v for v in valores)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # ANALISTA_FINANCIERO
        app.dependency_overrides[get_current_user] = lambda: mock_user("ANALISTA_FINANCIERO", username="analista_fin")
        try:
            res = client.get("/api/v1/reportes/export?tipo=kpis&formato=xlsx")
            assert res.status_code == 200
            wb = openpyxl.load_workbook(io.BytesIO(res.content))
            ws = wb.active
            valores = [str(cell.value) for row in ws.iter_rows() for cell in row]
            assert any("Bs." in v for v in valores)
            assert not any("[RESTRINGIDO PoLP]" in v for v in valores)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_historial_exportaciones_endpoint_rbac(self, client):
        """El endpoint /api/v1/reportes/historial retorna los registros de auditoría según RBAC."""
        # 1. ADMIN consulta historial
        app.dependency_overrides[get_current_user] = lambda: mock_user("ADMIN", username="superadmin")
        try:
            res = client.get("/api/v1/reportes/historial?limit=10")
            assert res.status_code == 200
            data = res.json()
            assert "historial" in data
            assert isinstance(data["historial"], list)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        # 2. Rol no autorizado recibe 403
        app.dependency_overrides[get_current_user] = lambda: mock_user("INVITADO_EXTERNO")
        try:
            res_inv = client.get("/api/v1/reportes/historial")
            assert res_inv.status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)

