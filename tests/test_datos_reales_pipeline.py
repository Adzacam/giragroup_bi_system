"""
tests/test_datos_reales_pipeline.py
-----------------------------------
Regresión de los cuatro cambios para que los flujos /pipeline/process y /dataops/confirm-dw-insert
produzcan datos reales:
1. Bandas por índice real (>= 0.85 hecho, [0.60, 0.85) hecho en revisión, < 0.60 staging), sin 0.88 fijo.
2. nota_final real por módulo del acta (escala 10 -> base 100); sin nota: null + requiere_revision.
3. id_tiempo derivado de la fila; sin fecha: None + requiere_revision (antes 20260501).
4. 'POS - ACTAS: …' es metadato del programa, no el estudiante.
"""

import io
import json
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from pipeline.semantic.indice_confianza import (
    BANDA_CONSOLIDADO, BANDA_REVISION, BANDA_STAGING, clasificar_banda, texto_para_indice,
)
from services import confianza_service
from services.extraccion_por_encabezado import campos_por_encabezado, fecha_de_fila, registros_academicos
from routers.pipeline import _resolver_fila_sin_encabezados
from routers.dataops import extract_entities_from_line

LINEA_ACTA = (
    "N°: 1 | POS - ACTAS: POS-011 | CÉDULA DE IDENTIDAD: 13727801 | MES INICIO: Febrero | AÑO INICIO: 2024 | "
    "APELLIDO PATERNO: Torrez | APELLIDO MATERNO: Salinas | NOMBRES: Ana Lucía | MÓDULO 1: 78 | MÓDULO 2: 91"
)


def _campos(linea: str):
    return campos_por_encabezado([c.strip() for c in linea.split("|")])


# ── 1. Bandas de confianza ─────────────────────────────────────────────────────
class TestBandasConfianza:
    @pytest.mark.parametrize("indice,banda", [
        (0.99, BANDA_CONSOLIDADO), (0.85, BANDA_CONSOLIDADO),
        (0.8499, BANDA_REVISION), (0.60, BANDA_REVISION),
        (0.5999, BANDA_STAGING), (0.0, BANDA_STAGING),
    ])
    def test_umbrales(self, indice, banda):
        assert clasificar_banda(indice) == banda

    def test_sin_indice_va_a_revision_no_a_consolidado(self):
        assert confianza_service.banda_de(None) == BANDA_REVISION

    def test_texto_evaluado_son_las_primeras_8_celdas(self):
        linea = " | ".join(f"C{i}: {i}" for i in range(12))
        assert texto_para_indice(linea) == " | ".join(f"C{i}: {i}" for i in range(8))

    def test_obtener_indices_usa_el_servicio_beto(self):
        respuesta = io.BytesIO(json.dumps({"indices": [0.91, 0.7, 0.4]}).encode("utf-8"))
        with patch.object(confianza_service.urllib.request, "urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = respuesta
            indices = confianza_service.obtener_indices(["a: 1", "b: 2", "c: 3"])
        assert indices == [0.91, 0.7, 0.4]
        assert [confianza_service.banda_de(i) for i in indices] == [BANDA_CONSOLIDADO, BANDA_REVISION, BANDA_STAGING]

    def test_servicio_caido_no_inventa_indices(self):
        with patch.object(confianza_service.urllib.request, "urlopen", side_effect=OSError("sin red")):
            assert confianza_service.obtener_indices(["a: 1", "b: 2"]) == [None, None]


# ── 2. nota_final real ─────────────────────────────────────────────────────────
class TestNotaFinal:
    def test_un_hecho_por_modulo_con_su_nota(self):
        regs = registros_academicos(_campos(LINEA_ACTA))
        assert [r["nota_final"] for r in regs] == [78.0, 91.0]
        assert [r["programa"]["metadata"]["pos_canonico"] for r in regs] == ["POS-011-M01", "POS-011-M02"]
        assert all(r["requiere_revision"] is False for r in regs)

    def test_escala_10_se_lleva_a_base_100(self):
        regs = registros_academicos(_campos("CI: 123456 | NOMBRES: ANA | MES: 3 | AÑO: 2025 | MÓDULO 1: 7.5 | MÓDULO 2: 9"))
        assert [r["nota_final"] for r in regs] == [75.0, 90.0]

    def test_acta_sin_notas_queda_null_y_en_revision(self):
        regs = registros_academicos(_campos("POS - ACTAS: 5381 | CI: 123456 | NOMBRES: ANA | ESTADO ACADEMICO: En curso | MÓDULO 1: nan"))
        assert len(regs) == 1
        assert regs[0]["nota_final"] is None
        assert regs[0]["requiere_revision"] is True

    def test_dataops_ya_no_rellena_con_80(self):
        import inspect
        import routers.dataops as dataops
        assert "else 80.0" not in inspect.getsource(dataops.confirm_dw_insert)


# ── 3. id_tiempo derivado de la fila ───────────────────────────────────────────
class TestFechaDeFila:
    def test_acta_con_mes_y_gestion_usa_primer_dia_del_mes(self):
        assert fecha_de_fila(_campos(LINEA_ACTA), "academico") == date(2024, 2, 1)

    def test_cobranza_usa_fecha_de_pago(self):
        campos = _campos("CI: 1 | FECHA DE LA PRIMERA FACTURA: 2024-01-10 00:00:00 | FECHA ULTIMA FACTURA: 2024-04-03 00:00:00")
        assert fecha_de_fila(campos, "financiero") == date(2024, 4, 3)

    def test_sin_fecha_retorna_none(self):
        assert fecha_de_fila(_campos("CI: 1 | NOMBRES: ANA"), "academico") is None


@pytest.fixture
def dw():
    from core.database import Base
    import models  # noqa: F401  registra todas las tablas
    from services.dw_loader import DWLoaderService

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def do_connect(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("ATTACH DATABASE ':memory:' AS public")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield DWLoaderService(session), session
    finally:
        session.close()


def _registro_academico(nota, fecha):
    return {
        "categoria": "academico",
        "resoluciones": {
            "estudiante": {"valor_extraido": "ANA TORREZ", "fk_resolucion": {"ci": "13727801", "nombre_resuelto": "ANA TORREZ"}},
            "modulo": {"valor_extraido": "POS-011 · Módulo 1"},
            "programa": {"valor_extraido": "POS-011", "metadata": {"pos_canonico": "POS-011-M01"}},
            "nota_final": nota,
            "nota_ya_normalizada": True,
            "fecha": fecha,
            "nivel_confianza_ia": 0.9,
        },
        "calidad": {"requiere_revision": False},
    }


class TestLoaderSinValoresPorDefecto:
    def test_fecha_de_fila_crea_dim_tiempo_completo(self, dw):
        from models.dim_tiempo import DimTiempo
        from models.fact_rendimiento import FactRendimientoAcademico
        loader, db = dw
        assert loader.cargar_registro(_registro_academico(78.0, date(2024, 2, 1)))["status"] == "loaded"
        hecho = db.query(FactRendimientoAcademico).one()
        assert hecho.id_tiempo == 20240201
        assert float(hecho.nota_final) == 78.0 and hecho.requiere_revision is False
        t = db.query(DimTiempo).get(20240201)
        assert t.fecha == date(2024, 2, 1) and t.gestion == 2024 and t.trimestre == 1

    def test_sin_fecha_ni_nota_queda_null_y_en_revision(self, dw):
        from models.fact_rendimiento import FactRendimientoAcademico
        loader, db = dw
        loader.cargar_registro(_registro_academico(None, None))
        hecho = db.query(FactRendimientoAcademico).one()
        assert hecho.id_tiempo is None
        assert hecho.nota_final is None
        assert hecho.requiere_revision is True


# ── 4. Metadato POS no es estudiante ───────────────────────────────────────────
class TestMetadatoPos:
    def test_pipeline_sin_encabezados_ignora_celda_pos(self):
        base = {"estudiante": None, "nota_final": None, "monto_deuda": None}
        res = _resolver_fila_sin_encabezados(["POS - ACTAS: POS-011", "Ana Lucía Torrez", "78"], "academico", base, [])
        assert res["estudiante"]["valor_extraido"] == "Ana Lucía Torrez"

    def test_extractor_dataops_no_toma_pos_como_estudiante(self):
        ents, _, _ = extract_entities_from_line("POS - ACTAS: POS-011 | MES INICIO: Febrero | MÓDULO 1: 78", [], [], [])
        est = next((e["token"] for e in ents if e.get("label") == "ESTUDIANTE"), None)
        assert est is None or "POS" not in est

    def test_acta_resuelve_estudiante_por_nombre_y_ci(self):
        est = registros_academicos(_campos(LINEA_ACTA))[0]["estudiante"]
        assert est["fk_resolucion"]["ci"] == "13727801"
        assert est["fk_resolucion"]["nombre_resuelto"] == "Ana Lucía Torrez Salinas"


# ── Serialización y fuentes encontradas al recargar el DW ──────────────────────
class TestSerializacionYFuentes:
    def test_fecha_con_hora_conserva_su_encabezado(self):
        import pandas as pd
        from services.ingestion_service import IngestionService
        b = pd.DataFrame([["CI", "FECHA ULTIMA FACTURA"], ["13441152", "2024-04-03 00:00:00"]])
        linea = IngestionService.serializar_bloque_con_encabezados(b)
        assert "FECHA ULTIMA FACTURA: 2024-04-03 00:00:00" in linea
        assert fecha_de_fila(_campos(linea), "financiero") == date(2024, 4, 3)

    def test_csv_con_columnas_nombradas_no_consume_la_primera_fila(self):
        import pandas as pd
        from services.ingestion_service import IngestionService
        b = pd.DataFrame({"First name": ["Carlos", "Lucia"], "Surname": ["Mendoza", "Vargas"]})
        lineas = IngestionService.serializar_bloque_con_encabezados(b).split("\n")
        assert lineas == ["First name: Carlos | Surname: Mendoza", "First name: Lucia | Surname: Vargas"]

    def test_fila_moodle(self):
        linea = ("First name: Carlos | Surname: Mendoza Ruiz | ID number: CI-1029384 | "
                 "Course: POS-5376 - Maestría en Ciberseguridad | Grade/100.00: 88.50")
        reg = registros_academicos(_campos(linea))[0]
        assert reg["estudiante"]["fk_resolucion"]["nombre_resuelto"] == "Carlos Mendoza Ruiz"
        assert reg["programa"]["valor_extraido"] == "POS-5376"
        assert reg["nota_final"] == 88.5
        assert reg["requiere_revision"] is True  # Moodle no trae fecha de evaluación

    def test_hoja_sin_estudiante_no_genera_hechos(self):
        assert registros_academicos(_campos("N°: 1 | POS - MODULO: POS-006 | DOCENTE: Dr. María Huanca | MODULO N°: 1")) == []
