"""
tests/sprint4/test_cmi_y_laboratorio_predictivo.py
--------------------------------------------------------------
Pruebas de verificación automatizada para Vista 4:
- Cuadro de Mando Integral (Perspectivas Estratégicas Institucionales)
- Analítica Predictiva Macro (4 Casos de Negocio: Holt-Winters y OLS)
- Matriz de Viabilidad de Programas (Foco Marketing)
"""

from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


from main import app
from core.security import get_current_user
from core.database import get_db
from models.user import User
from services.forecast_service import (
    obtener_analitica_macro_completa,
    obtener_matriz_viabilidad_programas,
    obtener_pronostico_alumnos,
    obtener_pronostico_metas
)
from services import forecast_service
from services.kpi_service import KPIService

ANIO = pd.Timestamp.now().year


def _serie_alumnos() -> pd.Series:
    """33 meses (sep-2023 a may-2026) con estacionalidad anual y tendencia suave."""
    idx = pd.period_range("2023-09", periods=33, freq="M")
    vals = [60 + 0.8 * i + 12 * np.sin(2 * np.pi * i / 12) for i in range(33)]
    return pd.Series(vals, index=idx)


def _serie_meta_mensual() -> pd.Series:
    idx = pd.period_range(f"{ANIO - 2}-01", periods=30, freq="M")
    return pd.Series([260_000 + 3_000 * i + 25_000 * np.sin(2 * np.pi * i / 12) for i in range(30)], index=idx)


def _serie_meta_anual() -> pd.Series:
    return pd.Series([2_900_000.0, 3_300_000.0, 3_600_000.0], index=[ANIO - 3, ANIO - 2, ANIO - 1])


def _inscritos() -> pd.DataFrame:
    filas = []
    for prog, base in (("DIPLOMADO EN GESTIÓN PÚBLICA", 40), ("MAESTRÍA EN FINANZAS", 30),
                       ("CURSO DE EXCEL AVANZADO", 15), ("PROGRAMA EXPERTO EN DATOS", 22)):
        for k, g in enumerate((ANIO - 3, ANIO - 2, ANIO - 1, ANIO)):
            filas.append({"programa": prog, "gestion": g, "inscritos": base + 4 * k})
    return pd.DataFrame(filas)


def _meta_vs_ejecutado() -> pd.DataFrame:
    filas = [{"gestion": g, "mes": m, "meta": 300_000.0, "ejecutado": 250_000.0 + 8_000 * m}
             for g in (ANIO - 1, ANIO) for m in range(1, 13)]
    return pd.DataFrame(filas)


@pytest.fixture
def dw_controlado(monkeypatch):
    """Sustituye las lecturas al DW por datos deterministas (el servicio es solo-DW)."""
    def serie(caso, engine=None):
        if caso.startswith("ALUMNOS"):
            return _serie_alumnos()
        return _serie_meta_mensual() if caso == "META_MENSUAL_PROGRAMAS" else _serie_meta_anual()
    monkeypatch.setattr(forecast_service, "extraer_serie_temporal", serie)
    monkeypatch.setattr(forecast_service, "_inscritos_por_programa", lambda db: _inscritos())
    monkeypatch.setattr(forecast_service, "_meta_vs_ejecutado", lambda db: _meta_vs_ejecutado())


@pytest.fixture(autouse=True)
def setup_overrides():
    mock_admin = User(
        id=1,
        username="admin",
        email="admin.general@giragroup.bo",
        role="ADMIN",
        is_active=True
    )
    mock_db = MagicMock(spec=Session)
    mock_db.execute.side_effect = Exception("DB offline in mock test")
    mock_db.get_bind.return_value = None

    app.dependency_overrides[get_current_user] = lambda: mock_admin
    app.dependency_overrides[get_db] = lambda: mock_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer test_token"
    return c


# ─────────────────────────────────────────────────────────────────────────────
# 1. PRUEBAS DE SERVICIO: MATRIZ DE VIABILIDAD Y NO NEGATIVIDAD
# ─────────────────────────────────────────────────────────────────────────────

def test_matriz_viabilidad_programas_estructura_y_reglas(dw_controlado):
    """Valida que la Matriz de Viabilidad clasifique correctamente con chips válidos."""
    datos = obtener_matriz_viabilidad_programas()
    assert len(datos) > 0, "La matriz de viabilidad debe retornar programas evaluados"

    decisiones_validas = {"ABRIR NUEVA VERSIÓN", "CONTINUAR", "DESCARTAR / REESTRUCTURAR"}
    colores_validos = {"emerald", "amber", "rose"}

    for item in datos:
        assert "programa" in item
        assert "tipo" in item
        assert "total_historico" in item
        assert item["total_historico"] >= 0
        assert "cagr_pct" in item
        assert "proyeccion_6m" in item
        assert item["proyeccion_6m"] >= 0, "La proyección semestral no puede ser negativa"
        assert item["decision_sugerida"] in decisiones_validas
        assert item["badge_color"] in colores_validos
        assert len(item["justificacion"]) > 10


def test_analitica_macro_4_casos_completitud(dw_controlado):
    """Valida que el servicio consolide los 4 Casos Predictivos Macro con invariantes matemáticas."""
    res = obtener_analitica_macro_completa(horizonte=6)

    assert res["status"] == "success"
    assert res["horizonte_meses"] == 6

    # Caso 1: Demanda Global de Alumnos
    c1 = res["caso1_demanda_global"]
    assert c1["n_observaciones"] == 33
    assert len(c1["periodos_historicos"]) == 33
    assert len(c1["valores_historicos"]) == 33
    assert "Amortiguado" in c1["modelo"]
    assert len(c1["forecast_hw"]) == 6
    assert len(c1["ic_lower_95"]) == 6
    assert len(c1["ic_upper_95"]) == 6
    for f, l, u in zip(c1["forecast_hw"], c1["ic_lower_95"], c1["ic_upper_95"]):
        assert f >= 0.0, "Forecast alumnos no puede ser negativo"
        assert l >= 0.0, "Banda inferior no puede ser negativa"
        assert l <= f <= u, "Invariante de bandas: lower <= forecast <= upper"
    # Sin statsmodels (entorno mínimo) el MAPE de hold-out no se calcula y llega como None
    assert c1["mape_pct"] is None or c1["mape_pct"] >= 0.0
    assert c1["rmse"] >= 0.0
    assert "pendiente_ols_mes" in c1

    # Caso 2: Demanda por Programa y Matriz de Viabilidad
    c2 = res["caso2_demanda_programa"]
    assert "matriz_viabilidad" in c2
    assert len(c2["matriz_viabilidad"]) > 0
    assert "resumen_cartera" in c2
    assert "DIPLOMADO" in c2["resumen_cartera"]
    assert res["sin_datos"] == {}

    # Caso 3: Cumplimiento de Metas / Ingresos Mensuales
    c3 = res["caso3_metas_mensuales"]
    assert len(c3["meses_etiquetas"]) > 0
    assert len(c3["meta_catalogo_bs"]) == len(c3["meses_etiquetas"])
    assert len(c3["ejecutado_real_bs"]) == len(c3["meses_etiquetas"])
    assert c3["mes_actual"]["meta_mes_bs"] > 0
    assert c3["mes_actual"]["cierre_proyectado_hw_bs"] > 0

    # Caso 4: Cumplimiento de Metas / Ingresos Anuales
    c4 = res["caso4_metas_anuales"]
    assert c4["meta_anual_institucional_bs"] == 3_600_000.0
    assert c4["recaudado_acumulado_bs"] > 0
    assert len(c4["anios_historicos"]) == 3
    assert c4["cierre_anual_proyectado_ols_bs"] > 0


@pytest.fixture
def dw_vacio():
    """DW SQLite en memoria sin datos: el CMI debe responder con estructura y listas vacías."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from core.database import Base
    import models.dim_modulo, models.dim_tiempo, models.fact_marketing  # noqa: F401

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def adjuntar_public(conn, _):
        cur = conn.cursor()
        cur.execute("ATTACH DATABASE ':memory:' AS public")
        cur.close()

    Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(bind=engine)()
    yield sesion
    sesion.close()


def test_perspectivas_cmi_completo_estructura(dw_vacio):
    """Valida que KPIService retorne las 4 Perspectivas Estratégicas con sus drilldowns (vacíos sin datos)."""
    service = KPIService(db=dw_vacio)
    res = service.obtener_perspectivas_cmi_completo()

    assert res["status"] == "success"
    p = res["perspectivas"]
    assert "financiera" in p
    assert "cliente_mercado" in p
    assert "procesos_internos" in p
    assert "aprendizaje_crecimiento" in p

    # Sin datos ingestados no se inventan cifras: los valores son None/0 y la cartera una lista vacía
    assert p["financiera"]["drilldown_cartera"] == []
    assert p["financiera"]["ticket_promedio_bs"] is None
    assert p["cliente_mercado"]["total_matricula_acumulada"] in (None, 0)
    assert p["aprendizaje_crecimiento"]["promedio_general_notas"] is None
    for clave in ("confianza_media_beto_pct", "tasa_automatizacion_pct", "documentos_procesados"):
        assert clave in p["procesos_internos"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. PRUEBAS DE INTEGRACIÓN DE ENDPOINTS REST
# ─────────────────────────────────────────────────────────────────────────────

def test_endpoint_analitica_macro(client, dw_controlado):
    """Valida endpoint GET /api/v1/forecast/analitica-macro."""
    resp = client.get("/api/v1/forecast/analitica-macro?horizonte=4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["horizonte_meses"] == 4
    assert "caso1_demanda_global" in data
    assert "caso2_demanda_programa" in data
    assert "caso3_metas_mensuales" in data
    assert "caso4_metas_anuales" in data


def test_endpoint_viabilidad_programas(client, dw_controlado):
    """Valida endpoint GET /api/v1/forecast/viabilidad-programas."""
    resp = client.get("/api/v1/forecast/viabilidad-programas?tipo=DIPLOMADO")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["total_programas"] > 0
    for prog in data["data"]:
        assert "DIPLOMADO" in prog["tipo"].upper()


def test_endpoint_kpis_cmi_completo(client, dw_vacio):
    app.dependency_overrides[get_db] = lambda: dw_vacio
    """Valida endpoint GET /api/v1/kpis/cmi-completo."""
    resp = client.get("/api/v1/kpis/cmi-completo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "perspectivas" in data
    assert "financiera" in data["perspectivas"]
    assert "cliente_mercado" in data["perspectivas"]


def test_endpoint_analitica_macro_frontera_horizonte_invalido(client):
    """Valida que horizontes fuera de [1, 6] retornen HTTP 422 Unprocessable Entity."""
    # Frontera inferior inválida
    resp_cero = client.get("/api/v1/forecast/analitica-macro?horizonte=0")
    assert resp_cero.status_code == 422

    # Frontera superior inválida
    resp_siete = client.get("/api/v1/forecast/analitica-macro?horizonte=7")
    assert resp_siete.status_code == 422

    # Tipo no entero
    resp_str = client.get("/api/v1/forecast/analitica-macro?horizonte=invalido")
    assert resp_str.status_code == 422


def test_endpoint_viabilidad_programas_normalizacion_acentos(client, dw_controlado):
    """Valida que la consulta maneje diacríticos y acentos URI encoded de forma insensible."""
    # Con tilde explícita
    resp_tilde = client.get("/api/v1/forecast/viabilidad-programas?tipo=MAESTR%C3%8DA")
    assert resp_tilde.status_code == 200
    data_tilde = resp_tilde.json()
    assert data_tilde["total_programas"] > 0
    for item in data_tilde["data"]:
        assert "MAESTR" in item["tipo"].upper()

    # Sin tilde
    resp_sin_tilde = client.get("/api/v1/forecast/viabilidad-programas?tipo=MAESTRIA")
    assert resp_sin_tilde.status_code == 200
    data_sin_tilde = resp_sin_tilde.json()
    assert data_sin_tilde["total_programas"] > 0
    assert len(data_sin_tilde["data"]) == len(data_tilde["data"])

    # En minúsculas
    resp_min = client.get("/api/v1/forecast/viabilidad-programas?tipo=diplomado")
    assert resp_min.status_code == 200
    data_min = resp_min.json()
    assert data_min["total_programas"] > 0


def test_servicio_horizonte_boundary_safe(dw_controlado):
    """Valida que invocar el servicio directamente con horizontes extremos se acote con seguridad."""
    res_cero = obtener_analitica_macro_completa(horizonte=0)
    assert res_cero["status"] == "success"
    assert len(res_cero["caso1_demanda_global"]["forecast_hw"]) == 1

    res_diez = obtener_analitica_macro_completa(horizonte=10)
    assert res_diez["status"] == "success"
    assert len(res_diez["caso1_demanda_global"]["forecast_hw"]) == 6

