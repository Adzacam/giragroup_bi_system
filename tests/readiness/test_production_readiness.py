"""
tests/readiness/test_production_readiness.py
--------------------------------------------
Puertas de salida a producción (auditoría 2026-11-01).

- Pruebas unitarias: corren sin Docker. Las que documentan un defecto conocido van con
  xfail(strict=True): pasan a fallar (XPASS) en cuanto se corrige, y obligan a quitar la marca.
- Pruebas de integración (marca `readiness_live`): necesitan la pila Docker en marcha y variables:
    READINESS_BASE_URL   (por defecto http://localhost, el gateway)
    READINESS_TOKEN      JWT de un ADMIN
    READINESS_TOKEN_2    JWT de un segundo usuario AUDITOR_CALIDAD/ADMIN (prueba de bloqueo HITL)
    READINESS_BETO_URL   URL del servidor BETO (no se publica al host: correr desde la red Docker)
    READINESS_GOLD       frases gold (por defecto data/test_gold_real.jsonl)
    READINESS_DB_URL     postgresql://... del DW (higiene de datos)
  Sin esas variables, la prueba se omite.
"""

import json
import os
import time
from pathlib import Path
import statistics
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from pipeline.analytics.forecasting_holtwinters import entrenar_y_proyectar_hw
from pipeline.analytics.forecasting_ols import estimar_tendencia_anual_ols
from pipeline.semantic.indice_confianza import clasificar_banda, UMBRAL_CONSOLIDADO, UMBRAL_REVISION
from pipeline.normalization.fk_resolver import FKResolver

BASE_URL = os.getenv("READINESS_BASE_URL", "http://localhost")
TOKEN = os.getenv("READINESS_TOKEN")
TOKEN_2 = os.getenv("READINESS_TOKEN_2")
BETO_URL = os.getenv("READINESS_BETO_URL")
DB_URL = os.getenv("READINESS_DB_URL")

UMBRAL_RESPUESTA_MS = 3000
UMBRAL_BETO_MS_ORACION = 20
UMBRAL_BETO_CONFIANZA = 0.92


def _serie_mensual(n=43, inicio="2022-11", nivel=300.0, pendiente=4.0, amplitud=80.0, ruido=15.0, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.period_range(inicio, periods=n, freq="M")
    t = np.arange(n)
    y = nivel + pendiente * t + amplitud * np.sin(2 * np.pi * (idx.month - 1) / 12) + rng.normal(0, ruido, n)
    return pd.Series(np.maximum(y, 0), index=idx)


# ── Holt-Winters ─────────────────────────────────────────────────────────────

class TestHoltWinters:
    def test_horizonte_acotado_a_6_meses(self):
        with pytest.raises(ValueError):
            entrenar_y_proyectar_hw(_serie_mensual(), "ALUMNOS_GLOBAL", horizonte=7)

    def test_exige_dos_ciclos_completos(self):
        with pytest.raises(ValueError):
            entrenar_y_proyectar_hw(_serie_mensual(n=23), "ALUMNOS_GLOBAL", horizonte=6)

    def test_cotas_no_negativas_y_banda_contiene_pronostico(self):
        serie = _serie_mensual(nivel=20.0, pendiente=-1.5, amplitud=30.0)
        res = entrenar_y_proyectar_hw(serie, "ALUMNOS_GLOBAL", horizonte=6)
        assert len(res["forecast"]) == 6
        for f, lo, hi in zip(res["forecast"], res["ic_lower"], res["ic_upper"]):
            assert f >= 0 and lo >= 0
            assert lo <= f <= hi

    @pytest.mark.xfail(strict=True, reason="Hallazgo HW-IC: banda ±1,96·RMSE constante; la varianza debe crecer con h")
    def test_banda_95_se_ensancha_con_el_horizonte(self):
        res = entrenar_y_proyectar_hw(_serie_mensual(), "ALUMNOS_GLOBAL", horizonte=6)
        anchos = [round(hi - lo, 2) for lo, hi in zip(res["ic_lower"], res["ic_upper"])]  # redondeo: el ruido de coma flotante (1e-14) daba un XPASS falso
        assert anchos[-1] > anchos[0]

    @pytest.mark.xfail(strict=True, reason="Hallazgo HW-GAP: asfreq().fillna(0) trata un mes sin carga como demanda cero")
    def test_mes_faltante_no_se_interpreta_como_demanda_cero(self):
        completa = _serie_mensual()
        con_hueco = completa.drop(completa.index[-3])
        f_ok = np.array(entrenar_y_proyectar_hw(completa, "ALUMNOS_GLOBAL", 6)["forecast"])
        f_hueco = np.array(entrenar_y_proyectar_hw(con_hueco, "ALUMNOS_GLOBAL", 6)["forecast"])
        assert np.mean(np.abs(f_hueco - f_ok) / np.maximum(f_ok, 1)) < 0.05

    # HW-PARAM resuelto: parámetros estimados correctamente en entorno con statsmodels
    def test_parametros_suavizado_estimados(self):
        res = entrenar_y_proyectar_hw(_serie_mensual(), "ALUMNOS_GLOBAL", horizonte=6)
        assert res["parametros"] != {"alpha": 0.2, "beta": 0.1, "gamma": 0.2}
        assert res["aic"] is not None


# ── OLS anual (Caso 4) ──────────────────────────────────────────────────────

class TestOLSAnual:
    SERIE = pd.Series([8035694.25, 9989730.09, 12907977.61], index=[2023, 2024, 2025])

    def test_n3_dof1_sin_ic_parametrico(self):
        res = estimar_tendencia_anual_ols(self.SERIE, horizonte_anios=2)
        assert res["n_observaciones"] == 3
        assert res["n_observaciones"] - 2 == 1  # dof de la recta
        assert res["ic_lower"] is None and res["ic_upper"] is None
        assert res["periodos"] == ["2026", "2027"]

    def test_rechaza_menos_de_tres_anios(self):
        with pytest.raises(ValueError):
            estimar_tendencia_anual_ols(self.SERIE.iloc[:2])

    def test_banda_indicativa_5pct_en_servicio(self, monkeypatch):
        from services import forecast_service
        monkeypatch.setattr(forecast_service, "extraer_serie_temporal", lambda caso, engine=None: self.SERIE)
        res = forecast_service.obtener_pronostico_metas(db=None, granularity="ANUAL", horizonte=2)
        for p in res["proyecciones"]:
            assert p["ic_lower"] == pytest.approx(p["monto_proyectado_bs"] * 0.95, abs=0.01)
            assert p["ic_upper"] == pytest.approx(p["monto_proyectado_bs"] * 1.05, abs=0.01)

    @pytest.mark.xfail(strict=True, reason="Hallazgo OLS-CAGR: se publica la media aritmética de variaciones como CAGR")
    def test_cagr_es_geometrico(self):
        serie = pd.Series([100.0, 200.0, 150.0], index=[2023, 2024, 2025])
        res = estimar_tendencia_anual_ols(serie)
        cagr = ((150.0 / 100.0) ** (1 / 2) - 1) * 100
        assert res["cagr_historico_pct"] == pytest.approx(cagr, abs=0.1)


# ── Cascada de confianza / FKResolver ───────────────────────────────────────

class TestCascadaConfianza:
    @pytest.mark.parametrize("indice,banda_esperada", [
        (None, "staging"), (0.59, "staging"), (UMBRAL_REVISION, "revision"),
        (0.849, "revision"), (UMBRAL_CONSOLIDADO, "consolidado"), (0.99, "consolidado"),
    ])
    def test_bandas(self, indice, banda_esperada):
        assert banda_esperada in clasificar_banda(indice).lower()

    def _resolver_vacio(self):
        res = FKResolver.__new__(FKResolver)
        res.padron_nombres, res.nombres_originales = {}, {}
        return res

    @pytest.mark.parametrize("ci", ["4567890", "4.567.890", "4567890-1B"])
    def test_estado_a_ci_directo(self, ci):
        out = self._resolver_vacio().resolver_estudiante(nombre="JUAN PEREZ", ci_candidato=ci)
        assert out["fk_estado"] == "A" and not out["es_sintetico"]

    @pytest.mark.xfail(strict=True, reason="Hallazgo FK-CI-EXT: el CI con extensión departamental ('4567890 LP') se rechaza y cae a Estado C sintético")
    def test_estado_a_ci_con_extension_departamental(self):
        out = self._resolver_vacio().resolver_estudiante(nombre="JUAN PEREZ", ci_candidato="4567890 LP")
        assert out["fk_estado"] == "A"

    @pytest.mark.xfail(strict=True, reason="Hallazgo FK-HASH: TEMP-CI usa MD5 truncado a 8 hex (32 bits); homónimos colisionan")
    def test_id_sintetico_con_entropia_suficiente(self):
        ci = FKResolver.generar_ci_sintetico("JUAN PEREZ MAMANI")
        assert len(ci.split("-")[-1]) >= 12

    def _loader_sin_candidatos(self):
        from services.dw_loader import DWLoaderService
        db = MagicMock()
        consulta = db.query.return_value
        for metodo in ("filter", "filter_by", "join", "order_by", "limit"):
            getattr(consulta, metodo).return_value = consulta
        consulta.first.return_value = None
        consulta.all.return_value = []
        consulta.scalar.return_value = None
        return DWLoaderService(db), db

    def test_estado_b_hash_sha256_con_confianza_alta(self):
        loader, db = self._loader_sin_candidatos()
        _, estado = loader.resolver_o_crear_estudiante(ci=None, nombre="ANA QUISPE ROJAS", confianza_ia=0.95)
        assert estado == "B"
        creado = db.add.call_args[0][0]
        assert creado.id_temporal.startswith("TEMP-") and len(creado.id_temporal) == len("TEMP-") + 12

    def test_estado_c_confianza_baja_va_a_staging(self):
        loader, db = self._loader_sin_candidatos()
        id_est, estado = loader.resolver_o_crear_estudiante(ci=None, nombre="ANA QUISPE ROJAS", confianza_ia=0.50)
        assert (id_est, estado) == (None, "C")

    @pytest.mark.xfail(strict=True, reason="Hallazgo FK-BANDA: [0.60, 0.85) y confianza None generan TEMP en DimEstudiante en vez de derivar a stg_entidad_no_resuelta")
    @pytest.mark.parametrize("confianza", [0.70, None])
    def test_banda_media_deriva_a_staging(self, confianza):
        loader, _ = self._loader_sin_candidatos()
        _, estado = loader.resolver_o_crear_estudiante(ci=None, nombre="ANA QUISPE ROJAS", confianza_ia=confianza)
        assert estado == "C"


# ── Bandeja HITL: resolver respeta el bloqueo ajeno ─────────────────────────

class TestResolverRespetaBloqueo:
    def _db_con(self, ent):
        db = MagicMock()
        consulta = db.query.return_value
        for metodo in ("filter", "filter_by", "with_for_update"):
            getattr(consulta, metodo).return_value = consulta
        consulta.first.return_value = ent
        return db

    def _ent(self, **campos):
        from datetime import datetime, timedelta
        ent = MagicMock(resuelto=False, lock_usuario_id=None, lock_expira=None)
        ent.configure_mock(**campos)
        return ent, datetime.utcnow() + timedelta(minutes=3)

    def _resolver(self, db, usuario_id=2):
        from routers.dataops import resolve_review_item
        return resolve_review_item("REV-10", {"accion": "DESCARTAR"}, db=db,
                                   current_user=MagicMock(id=usuario_id, username="auditor"))

    def test_rechaza_caso_bloqueado_por_otro_auditor(self):
        from fastapi import HTTPException
        ent, expira = self._ent()
        ent.lock_usuario_id, ent.lock_expira = 1, expira
        db = self._db_con(ent)
        with pytest.raises(HTTPException) as exc:
            self._resolver(db)
        assert exc.value.status_code == 409
        db.commit.assert_not_called()

    def test_rechaza_caso_ya_resuelto(self):
        from fastapi import HTTPException
        ent, _ = self._ent(resuelto=True)
        with pytest.raises(HTTPException) as exc:
            self._resolver(self._db_con(ent))
        assert exc.value.status_code == 409

    def test_permite_si_el_bloqueo_es_propio(self):
        ent, expira = self._ent()
        ent.lock_usuario_id, ent.lock_expira = 2, expira
        ent.registro_origen_id = None
        assert self._resolver(self._db_con(ent))["estado_resolucion"] == "DESCARTADO"


# ── Integración contra la pila en marcha ────────────────────────────────────

requests = pytest.importorskip("requests")
live = pytest.mark.readiness_live


def _carga(url, n, conc, headers=None, timeout=120):
    def una(_):
        t0 = time.perf_counter()
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            return (time.perf_counter() - t0) * 1000, r.status_code
        except requests.RequestException:
            return (time.perf_counter() - t0) * 1000, 0
    with ThreadPoolExecutor(conc) as ex:
        res = list(ex.map(una, range(n)))
    lat = sorted(x[0] for x in res)
    return lat[int(0.95 * len(lat)) - 1], [c for _, c in res]


@live
@pytest.mark.skipif(not TOKEN, reason="READINESS_TOKEN no definido")
class TestLatenciaAPI:
    def _h(self):
        return {"Authorization": f"Bearer {TOKEN}"}

    def test_cmi_50_concurrentes_p95_menor_3s(self):
        p95, codigos = _carga(f"{BASE_URL}/api/v1/kpis/cmi-completo", 50, 50, self._h())
        assert set(codigos) == {200}
        assert p95 < UMBRAL_RESPUESTA_MS, f"p95={p95:.0f} ms"

    @pytest.mark.xfail(strict=True, reason="Hallazgo PERF-FORECAST: analitica-macro calcula HW y lee Excel en cada GET")
    def test_analitica_macro_10_concurrentes_p95_menor_3s(self):
        p95, codigos = _carga(f"{BASE_URL}/api/v1/forecast/analitica-macro", 10, 10, self._h(), timeout=30)
        assert set(codigos) == {200} and p95 < UMBRAL_RESPUESTA_MS, f"p95={p95:.0f} ms"


@live
@pytest.mark.skipif(not (TOKEN and TOKEN_2), reason="READINESS_TOKEN y READINESS_TOKEN_2 requeridos")
def test_bloqueo_hitl_exclusivo_bajo_concurrencia():
    """Dos auditores piden el mismo caso a la vez: solo uno debe obtener el bloqueo."""
    h1, h2 = ({"Authorization": f"Bearer {t}"} for t in (TOKEN, TOKEN_2))
    bandeja = requests.get(f"{BASE_URL}/api/v1/dataops/review-tray", headers=h1, timeout=30).json()
    items = bandeja.get("items") or bandeja.get("queue") or bandeja.get("pendientes") or []
    if not items:
        pytest.skip("Bandeja HITL vacía")
    for item in items[:5]:
        url = f"{BASE_URL}/api/v1/dataops/review-tray/{item['id']}/lock"
        with ThreadPoolExecutor(2) as ex:
            codigos = list(ex.map(lambda h: requests.post(url, headers=h, timeout=30).status_code, (h1, h2)))
        for h in (h1, h2):
            requests.post(url.replace("/lock", "/unlock"), headers=h, timeout=30)
        assert sorted(codigos)[0] == 200 and codigos.count(200) == 1, f"item {item['id']}: {codigos}"


GOLD = Path(os.getenv("READINESS_GOLD", Path(__file__).resolve().parents[2] / "data" / "test_gold_real.jsonl"))


@pytest.fixture(scope="module")
def textos():
    if not GOLD.exists():
        pytest.skip(f"No existe {GOLD}")
    with GOLD.open(encoding="utf-8") as f:
        return [json.loads(linea)["texto"] for linea in f][:96]


@live
@pytest.mark.skipif(not BETO_URL, reason="READINESS_BETO_URL no definido")
class TestBETO:
    """Se mide sobre las frases gold reales: con frases sintéticas la confianza no es representativa."""

    def _lote(self, textos):
        return requests.post(f"{BETO_URL}/infer-batch", json={"textos": textos}, timeout=300).json()

    def test_campo_texto_vacio_o_mal_nombrado_responde_422(self):
        r = requests.post(f"{BETO_URL}/infer", json={"texto": "JUAN PEREZ"}, timeout=30)
        assert r.status_code == 422

    def test_latencia_menor_20ms_por_oracion_en_lote(self, textos):
        """En CPU (31,6 ms/oración medidos) no se alcanza: requiere docker-compose.gpu.yml."""
        self._lote(textos[:32])
        totales = [self._lote(textos[i:i + 32])["latency_ms_total"] for i in range(0, len(textos), 32)]
        por_oracion = sum(totales) / len(textos)
        assert por_oracion < UMBRAL_BETO_MS_ORACION, f"{por_oracion:.1f} ms/oración"

    def test_confianza_media_minima(self, textos):
        scores = [e["score"] for r in self._lote(textos)["resultados"] for e in r["entities"]]
        assert scores and statistics.mean(scores) >= UMBRAL_BETO_CONFIANZA


@live
@pytest.mark.skipif(not DB_URL, reason="READINESS_DB_URL no definido")
class TestHigieneDatos:
    """Cobertura de datos reales 100 %: estas puertas fallan hasta ejecutar la purga."""

    @pytest.fixture(scope="class")
    def conn(self):
        sqlalchemy = pytest.importorskip("sqlalchemy")
        with sqlalchemy.create_engine(DB_URL).connect() as c:
            yield c

    def _escalar(self, conn, sql):
        from sqlalchemy import text
        return conn.execute(text(sql)).scalar()

    def test_sin_documentos_de_prueba(self, conn):
        assert self._escalar(conn, r"SELECT count(*) FROM dim_origen_documental WHERE nombre_archivo ~* '(^|[_\-\s])(test|demo|mock|prueba)'") == 0

    def test_sin_usuarios_tecnicos_activos(self, conn):
        assert self._escalar(conn, "SELECT count(*) FROM users WHERE is_active AND username IN ('loadtest_user','qa_admin')") == 0

    def test_inscripciones_cargadas_en_dw(self, conn):
        assert self._escalar(conn, "SELECT count(*) FROM fact_marketing") > 0

    def test_una_foto_financiera_por_estudiante_y_corte(self, conn):
        assert self._escalar(conn, """
            SELECT count(*) FROM (SELECT id_estudiante, id_tiempo FROM fact_situacion_financiera
                                  GROUP BY 1, 2 HAVING count(*) > 1) d""") == 0

    def test_tablas_preservadas_por_reset(self, conn):
        for tabla in ("users", "dim_tiempo", "cat_institucion"):
            assert self._escalar(conn, f"SELECT count(*) FROM public.{tabla}") > 0
