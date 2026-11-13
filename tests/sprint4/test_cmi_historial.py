"""Detalle por indicador del CMI: GET /api/v1/cmi/kpis/{codigo}/historial."""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from main import app
from models.user import User
from routers.cmi import VISIBILIDAD


def _fila(gestion, valor, semaforo="VERDE"):
    return {
        "gestion": gestion, "perspectiva": "FINANCIERA", "nombre": "Ticket promedio por estudiante",
        "descripcion": "Recaudación entre matrícula.", "unidad": "BS", "sentido": "MAX",
        "valor": valor, "meta": None, "umbral_verde": None, "umbral_ambar": None, "semaforo": semaforo,
    }


@pytest.fixture
def api():
    db = MagicMock(spec=Session)
    estado = {"filas": [], "rol": "ADMIN"}
    capturado = {}

    def execute(sql, params=None):
        capturado["params"] = params
        return MagicMock(mappings=lambda: estado["filas"])

    db.execute.side_effect = execute
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, username="u", email="u@giragroup.bo", role=estado["rol"], is_active=True)
    yield TestClient(app), estado, capturado
    app.dependency_overrides.clear()


def test_devuelve_serie_ordenada_con_valores_numericos(api):
    client, estado, _ = api
    estado["filas"] = [_fila(2025, Decimal("3773.91")), _fila(2026, Decimal("2956.21"))]
    r = client.get("/api/v1/cmi/kpis/KPI-01/historial")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["nombre"] == "Ticket promedio por estudiante"
    assert [s["gestion"] for s in cuerpo["serie"]] == [2025, 2026]
    assert cuerpo["serie"][1]["valor"] == pytest.approx(2956.21)


def test_indicador_inexistente_o_sin_acceso_responde_404(api):
    client, estado, _ = api
    estado["filas"] = []
    assert client.get("/api/v1/cmi/kpis/KPI-99/historial").status_code == 404


def test_consulta_se_limita_a_las_perspectivas_del_rol(api):
    client, estado, capturado = api
    estado["filas"] = [_fila(2026, 1.0)]
    client.get("/api/v1/cmi/kpis/KPI-01/historial")
    assert capturado["params"]["p"] == sorted(VISIBILIDAD["ADMIN"])
    assert capturado["params"]["c"] == "KPI-01"
