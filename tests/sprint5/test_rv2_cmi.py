"""
Pruebas de RV2 (L3, L4, L7):
- GET /api/v1/cmi/resumen (visibilidad por rol)
- GET /api/v1/cmi/perspectivas/{codigo}/detalle (403 por rol, 404 desconocida)
- L7: RBAC de configuración por perspectiva, lista blanca sin PII, máscara < 5 y timeout 504
"""

from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from main import app
from core.database import get_db
from core.security import get_current_user
from services.cmi_personalizacion_service import ejecutar_consulta_medida


def test_migracion_021_sin_pii():
    lines = (
        Path(__file__).resolve().parents[2]
        / "backend"
        / "scripts"
        / "migrations"
        / "021_esquema_app_personalizacion.sql"
    ).read_text(encoding="utf-8").splitlines()
    sql = "\n".join(l for l in lines if not l.lstrip().startswith("--")).lower()
    assert "dim_estudiante" not in sql
    assert "nombre_completo" not in sql
    assert "correo" not in sql
    assert "telefono" not in sql


def test_l4_detalle_perspectiva_403_por_rol():
    class DummyDB:
        def execute(self, *a, **kw):
            return SimpleNamespace(mappings=lambda: [], scalar=lambda: None, all=lambda: [])

    app.dependency_overrides[get_db] = lambda: DummyDB()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, username="fin", role="ANALISTA_FINANCIERO", is_active=True)
    client = TestClient(app)
    try:
        r_forbidden = client.get("/api/v1/cmi/perspectivas/CLIENTES/detalle")
        assert r_forbidden.status_code == 403

        r_not_found = client.get("/api/v1/cmi/perspectivas/INEXISTENTE/detalle")
        assert r_not_found.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_l7_rbac_config_por_rol():
    class FakeResult:
        def __init__(self, first_val=None, mappings_val=None, rowcount=1):
            self._first = first_val
            self._mappings = mappings_val or []
            self.rowcount = rowcount

        def first(self):
            return self._first

        def scalar(self):
            return self._first[0] if isinstance(self._first, tuple) else self._first

        def mappings(self):
            return self._mappings

    class FakeDB:
        def execute(self, stmt, params=None):
            s = str(stmt)
            if "SELECT sentido, perspectiva FROM bi.ref_kpi" in s:
                c = (params or {}).get("c")
                if c == "KPI-01":
                    return FakeResult(("MAX", "FINANCIERA"))
                if c == "KPI-07":
                    return FakeResult(("MAX", "CLIENTES"))
                return FakeResult(None)
            return FakeResult(None, [])

        def commit(self):
            pass

        def rollback(self):
            pass

    app.dependency_overrides[get_db] = lambda: FakeDB()
    client = TestClient(app)
    payload_kpi = {"nombre": "Margen Neto", "peso": 10, "activo": True}
    payload_persp = {"nombre": "Financiera", "objetivo": "Sostenibilidad financiera", "pregunta": "¿Cómo vamos?", "peso": 30, "activa": True}

    try:
        # ANALISTA_FINANCIERO: KPI-01 (FINANCIERA) -> 200; KPI-07 (CLIENTES) -> 403; PUT perspectiva -> 403
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, username="fin", role="ANALISTA_FINANCIERO", is_active=True)
        assert client.put("/api/v1/cmi/config/kpis/KPI-01", json=payload_kpi).status_code == 200
        assert client.put("/api/v1/cmi/config/kpis/KPI-07", json=payload_kpi).status_code == 403
        assert client.put("/api/v1/cmi/config/perspectivas/FINANCIERA", json=payload_persp).status_code == 403

        # ANALISTA_MARKETING: KPI-07 (CLIENTES) -> 200; KPI-01 (FINANCIERA) -> 403
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=3, username="mkt", role="ANALISTA_MARKETING", is_active=True)
        assert client.put("/api/v1/cmi/config/kpis/KPI-07", json=payload_kpi).status_code == 200
        assert client.put("/api/v1/cmi/config/kpis/KPI-01", json=payload_kpi).status_code == 403

        # DIRECTOR_ACADEMICO: 403 en todo PUT / POST
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=4, username="dir", role="DIRECTOR_ACADEMICO", is_active=True)
        assert client.put("/api/v1/cmi/config/kpis/KPI-07", json=payload_kpi).status_code == 403
        assert client.put("/api/v1/cmi/config/perspectivas/CLIENTES", json=payload_persp).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_l7_grupo_menor_a_5_oculto_y_timeout_504():
    medida = {
        "codigo": "MED_TEST",
        "origen_schema": "bi",
        "origen_tabla": "vw_metas_mensual",
        "columna_medida": "ejecutado",
        "agregaciones_permitidas": ["SUM"],
        "dimensiones_permitidas": [{"codigo": "categoria", "label": "Cat", "expr": "categoria"}],
        "unidad": "BS",
    }

    class SmallGroupDB:
        def execute(self, stmt, params=None):
            if "SELECT" in str(stmt):
                return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: [
                    {"etiqueta": "Grande", "valor": 5000, "n_registros": 12},
                    {"etiqueta": "Pequeño", "valor": 100, "n_registros": 3},
                ]))
            return SimpleNamespace()

    res = ejecutar_consulta_medida(SmallGroupDB(), medida, "categoria", "SUM")
    assert res["filas"][0]["oculto"] is False
    assert res["filas"][0]["valor"] == 5000
    assert res["filas"][1]["oculto"] is True
    assert res["filas"][1]["valor"] is None
    assert res["filas"][1]["n_registros"] == "< 5"

    class TimeoutDB:
        def execute(self, stmt, params=None):
            if "SELECT" in str(stmt):
                raise OperationalError("stmt", {}, Exception("canceling statement due to statement timeout"))
            return SimpleNamespace()

        def rollback(self):
            pass

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        ejecutar_consulta_medida(TimeoutDB(), medida, "categoria", "SUM")
    assert exc.value.status_code == 504


def test_l3_resumen_visibilidad_por_rol():
    class ResumenDB:
        def execute(self, stmt, params=None):
            s = str(stmt)
            if "FROM bi.vw_cmi_gestiones" in s:
                return SimpleNamespace(mappings=lambda: [{"gestion": 2026}])
            if "FROM bi.vw_cmi_perspectiva" in s:
                permitidas = (params or {}).get("p", [])
                todas = [
                    {"gestion": 2026, "codigo": "FINANCIERA", "nombre": "Financiera", "peso": 30, "orden": 1, "indicadores": 6, "verdes": 4, "ambar": 1, "rojos": 1, "sin_evaluar": 0, "indice": 83},
                    {"gestion": 2026, "codigo": "CLIENTES", "nombre": "Clientes", "peso": 25, "orden": 2, "indicadores": 6, "verdes": 3, "ambar": 2, "rojos": 1, "sin_evaluar": 0, "indice": 75},
                    {"gestion": 2026, "codigo": "PROCESOS_INTERNOS", "nombre": "Procesos", "peso": 25, "orden": 3, "indicadores": 6, "verdes": 2, "ambar": 1, "rojos": 0, "sin_evaluar": 3, "indice": 86},
                    {"gestion": 2026, "codigo": "APRENDIZAJE", "nombre": "Aprendizaje", "peso": 20, "orden": 4, "indicadores": 5, "verdes": 1, "ambar": 0, "rojos": 0, "sin_evaluar": 4, "indice": 100},
                ]
                return SimpleNamespace(mappings=lambda: [r for r in todas if r["codigo"] in permitidas])
            if "FROM bi.vw_cmi_global" in s:
                return SimpleNamespace(mappings=lambda: [{"gestion": 2026, "indice": 84.5, "verdes": 10, "ambar": 4, "rojos": 2, "sin_evaluar": 7}])
            return SimpleNamespace(mappings=lambda: [])

    app.dependency_overrides[get_db] = lambda: ResumenDB()
    client = TestClient(app)
    try:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, username="adm", role="ADMIN", is_active=True)
        r_adm = client.get("/api/v1/cmi/resumen")
        assert r_adm.status_code == 200
        assert len(r_adm.json()["perspectivas_por_gestion"]) == 4

        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, username="fin", role="ANALISTA_FINANCIERO", is_active=True)
        r_fin = client.get("/api/v1/cmi/resumen")
        assert r_fin.status_code == 200
        assert len(r_fin.json()["perspectivas_por_gestion"]) == 1
        assert r_fin.json()["perspectivas_por_gestion"][0]["codigo"] == "FINANCIERA"
    finally:
        app.dependency_overrides.clear()


def test_l7_post_grafico_cierra_transaccion_readonly_y_valida_umbrales_kpp():
    class TxTrackingDB:
        def __init__(self):
            self.read_only = False

        def execute(self, stmt, params=None):
            s = str(stmt)
            if "SET LOCAL TRANSACTION READ ONLY" in s:
                self.read_only = True
                return SimpleNamespace()
            if "INSERT INTO app.grafico_personalizado" in s:
                assert not self.read_only, "INSERT ejecutado dentro de transacción READ ONLY"
                return SimpleNamespace(rowcount=1)
            if "FROM app.medida_catalogo" in s:
                return SimpleNamespace(mappings=lambda: [{
                    "codigo": "MED_TEST",
                    "nombre": "Medida",
                    "perspectiva": "FINANCIERA",
                    "origen_schema": "bi",
                    "origen_tabla": "vw_metas_mensual",
                    "columna_medida": "ejecutado",
                    "agregaciones_permitidas": ["SUM"],
                    "dimensiones_permitidas": [{"codigo": "mes", "label": "Mes", "expr": "nombre_mes"}],
                    "unidad": "BS",
                    "descripcion": "Test",
                }])
            if "SELECT (nombre_mes)" in s:
                return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: []))
            return SimpleNamespace(mappings=lambda: [], scalars=lambda: SimpleNamespace(all=lambda: []), first=lambda: None, scalar=lambda: None)

        def commit(self):
            self.read_only = False

        def rollback(self):
            self.read_only = False

    app.dependency_overrides[get_db] = lambda: TxTrackingDB()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, username="adm", role="ADMIN", is_active=True)
    client = TestClient(app)
    try:
        r_ok = client.post("/api/v1/cmi/config/graficos", json={
            "perspectiva": "FINANCIERA",
            "titulo": "Recaudación por mes",
            "medida_codigo": "MED_TEST",
            "dimension_codigo": "mes",
            "agregacion": "SUM",
            "tipo_grafico": "area",
        })
        assert r_ok.status_code == 200

        r_bad_kpp = client.post("/api/v1/cmi/config/kpis-personalizados", json={
            "perspectiva": "FINANCIERA",
            "nombre": "KPP inválido",
            "medida_codigo": "MED_TEST",
            "agregacion": "SUM",
            "sentido": "MAX",
            "umbral_verde": 50,
            "umbral_ambar": 80,
        })
        assert r_bad_kpp.status_code == 422
    finally:
        app.dependency_overrides.clear()
