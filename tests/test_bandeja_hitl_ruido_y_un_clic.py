"""
tests/test_bandeja_hitl_ruido_y_un_clic.py
------------------------------------------
Bandeja HITL:
a) Las líneas sin entidad que enlazar (hoja de estados académicos, catálogo de módulos sin estudiante,
   filas agregadas sin categoría/mes) se descartan como ruido con su motivo; no entran a revisión.
b) Un candidato solo se ofrece con un clic si coincide como nombre completo (token_sort >= 85), no por WRatio.
Los textos son líneas reales que la plataforma derivó a revisión en el lote de 1.387.
"""

import pytest
from rapidfuzz import fuzz

from services.extraccion_por_encabezado import campos_por_encabezado, motivo_fila_sin_entidad
from services.sugerencia_hitl import es_sugerencia_un_clic


def _motivo(linea, categoria):
    return motivo_fila_sin_entidad(campos_por_encabezado(linea.split(" | ")), categoria)


@pytest.mark.parametrize("linea, categoria, motivo", [
    ("Estado académico: Aprobado | Estado reprobado: Aprobado | Estado ARCA: Titulado", "financiero", "FILA_SIN_ENTIDAD"),
    ("Estado académico: Participó | Estado reprobado: Tutoria", "financiero", "FILA_SIN_ENTIDAD"),
    ("N°: 1 | POS - MODULO: POS-006 | N° POS: 6 | TIPO DE PROGRAMA: ESPECIALIDAD | DOCENTE: Dr. María Huanca",
     "academico", "FILA_ACADEMICA_SIN_ESTUDIANTE"),
    ("MES: JULIO | EJECUTADO 2025: 188464.8", "rentabilidad", "FILA_AGREGADA_SIN_CATEGORIA_MES"),
    ("solo texto sin cabeceras", "academico", "FILA_SIN_CABECERAS"),
])
def test_lineas_sin_entidad_se_descartan_con_motivo(linea, categoria, motivo):
    assert _motivo(linea, categoria) == motivo


@pytest.mark.parametrize("linea, categoria", [
    ("N°: 6 | POS - ACTAS: POS-030 | CÉDULA DE IDENTIDAD: 6744854 | APELLIDO PATERNO: Flores | "
     "APELLIDO MATERNO: Rojas | NOMBRES: Juan Carlos | MÓDULO 1: 53", "academico"),
    ("POS: POS-5478 | NOMBRE DEL PROGRAMA: CURSO EN MARKETING DIGITAL 15ª Versión | INSCRITOS: 41", "financiero"),
    ("Nombre Completo: Fernando Torrico Morales | Cédula de Identidad: CI-6294817 | Ciudad: Potosí", "admision"),
    ("CATEGORIA: TECHOS/CERRADOS | MES: JULIO | MES NUMERICO: 7 | EJECUTADO 2025: 188464.8", "rentabilidad"),
])
def test_lineas_con_entidad_siguen_el_flujo_normal(linea, categoria):
    assert _motivo(linea, categoria) is None


@pytest.mark.parametrize("texto, candidato", [
    ("Maestría en Finanzas", "INDICA QUE SE RETIRO DEL DIPLOMADO SIN EMBARGO EN ACTAS SALE"),
    ("Diplomado TIC", "DIPLOMADO"),
    ("MBA Gestión Empresarial", "CURSO INTELIGENCIA EMPRESARIAL CON MICROSOFT EXCEL 5ª Versión"),
    ("CURSO EN MARKETING DIGITAL 15ª Versión", "CURSO INTELIGENCIA EMPRESARIAL CON MICROSOFT EXCEL 5ª Versión"),
])
def test_coincidencia_parcial_wratio_no_es_un_clic(texto, candidato):
    wratio = max(fuzz.ratio(texto.lower(), candidato.lower()), fuzz.WRatio(texto.lower(), candidato.lower()))
    assert wratio >= 85  # la regla anterior las ofrecía con un clic
    assert es_sugerencia_un_clic(texto, candidato) is False


@pytest.mark.parametrize("texto, candidato", [
    ("NATALY CAERO FORONDA", "Nataly Caero Foronda"),
    ("Caero Foronda Nataly", "NATALY CAERO FORONDA"),
    ("Ana Lucia Torrez Rojas", "Ana Lucía Torrez Rojas"),
])
def test_mismo_nombre_completo_es_un_clic(texto, candidato):
    assert es_sugerencia_un_clic(texto, candidato) is True


def test_sin_candidato_no_hay_un_clic():
    assert es_sugerencia_un_clic("Juan Perez", None) is False
    assert es_sugerencia_un_clic(None, "Juan Perez") is False


@pytest.fixture
def sqlite_dw():
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from core.database import Base
    import models  # noqa: F401

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _public(dbapi_connection, _):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_confirm_descarta_fila_de_estados_y_no_la_manda_a_revision(sqlite_dw, monkeypatch):
    from models.dim_origen import DimOrigenDocumental
    from models.staging_entidad import StagingEntidadNoResuelta
    from models.staging_registro import StagingRegistroCrudo
    from routers import dataops

    monkeypatch.setattr(dataops, "obtener_indices", lambda lineas: [0.80] * len(lineas))  # banda de revisión
    sqlite_dw.add(DimOrigenDocumental(id_documento=1, nombre_archivo="BD_Cobranzas_giraGroup.xlsx", tipo_fuente="COBRANZA"))
    sqlite_dw.add(StagingRegistroCrudo(id=1, id_documento=1, hoja="ESTADOS", bloque_id=1, categoria="financiero", es_ruido=False,
                                       texto_plano="Estado académico: Aprobado | Estado reprobado: Aprobado | Estado ARCA: Titulado"))
    sqlite_dw.commit()

    res = dataops.confirm_dw_insert(dataops.ConfirmDwInsertRequest(doc_id=1), db=sqlite_dw, current_user=None)

    assert res["descartados_ruido"] == 1
    assert res["inserted_revision"] == 0 and res["inserted_dw"] == 0
    registro = sqlite_dw.query(StagingEntidadNoResuelta).one()
    assert (registro.motivo, registro.estado_resolucion, registro.resuelto) == ("FILA_SIN_ENTIDAD", "DESCARTADO", True)
    pendientes = sqlite_dw.query(StagingEntidadNoResuelta).filter(StagingEntidadNoResuelta.resuelto == False).count()
    assert pendientes == 0  # la bandeja (resuelto = False) no la muestra
