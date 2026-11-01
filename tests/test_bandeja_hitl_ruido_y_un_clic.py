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
    # Hoja 'Resumen por Programa' de cobranzas: sin estudiante no hay hecho financiero
    ("POS: POS-5478 | NOMBRE DEL PROGRAMA: CURSO EN MARKETING DIGITAL 15ª Versión | INSCRITOS: 41 | "
     "TIPO CARTERA: CARTERA CERRADA | OBSERVACIÓN CARTERA: EN PROCESO DE COBRO", "financiero", "FILA_FINANCIERA_SIN_ESTUDIANTE"),
])
def test_lineas_sin_entidad_se_descartan_con_motivo(linea, categoria, motivo):
    assert _motivo(linea, categoria) == motivo


@pytest.mark.parametrize("linea, categoria", [
    ("N°: 6 | POS - ACTAS: POS-030 | CÉDULA DE IDENTIDAD: 6744854 | APELLIDO PATERNO: Flores | "
     "APELLIDO MATERNO: Rojas | NOMBRES: Juan Carlos | MÓDULO 1: 53", "academico"),
    ("POS: POS-5478 | NOMBRE DEL PROGRAMA: CURSO EN MARKETING DIGITAL 15ª Versión | INSCRITOS: 41", "marketing"),
    ("POS: POS-5059 | CI: 2560728 | NOMBRES: PEDRO PABLO | PATERNO: CONDORI | DEUDA TOTAL: 750", "financiero"),
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


# ── Un clic: nombre extraído vs nombre del candidato (casos reales de la bandeja del lote) ──
LINEA_STAGING_EDGAR = ("N°: 2 | POS - ACTAS: 5314 | CÉDULA DE IDENTIDAD: 9008158 | MES INICO: 11 | AÑO INCIO: 2024 | "
                       "APELLIDO MATERNO: CAYO | NOMBRES: EDGAR | MÓDULO 1: 83 | MÓDULO 2: 70")
DISCORDANTE = "CI: 6702954 | Nombre: SAMANTHA STEFANY ALIAGA RAMIREZ (Discordante con: PAOLA GABRIELA RAMOS LORA)"


def test_nombre_extraido_de_cada_tipo_de_caso():
    from services.sugerencia_hitl import nombre_extraido
    assert nombre_extraido(LINEA_STAGING_EDGAR) == "EDGAR CAYO"
    assert nombre_extraido(DISCORDANTE) == "SAMANTHA STEFANY ALIAGA RAMIREZ"
    assert nombre_extraido("JUAN PEREZ (Programa entrante: POS-5295)") == "JUAN PEREZ"


def test_un_clic_compara_nombre_extraido_y_no_la_linea_completa(sqlite_dw, monkeypatch):
    from models.dim_origen import DimOrigenDocumental
    from models.staging_entidad import StagingEntidadNoResuelta
    from routers import dataops

    monkeypatch.setattr(dataops, "_evaluar_documentos_lote", lambda *a, **k: None)
    sqlite_dw.add(DimOrigenDocumental(id_documento=1, nombre_archivo="ARCA_lote1387_860_filas.xlsx", tipo_fuente="ACTA"))
    sqlite_dw.add_all([
        StagingEntidadNoResuelta(id_staging=1, id_documento=1, tipo_entidad="ESTUDIANTE", texto_original=LINEA_STAGING_EDGAR[:250],
                                 mejor_candidato="EDGAR CAYO", motivo="BAJA_CONFIANZA_IA", resuelto=False,
                                 payload_json={"raw_line": LINEA_STAGING_EDGAR}),
        StagingEntidadNoResuelta(id_staging=2, id_documento=1, tipo_entidad="ESTUDIANTE", texto_original=DISCORDANTE,
                                 mejor_candidato="PAOLA GABRIELA RAMOS LORA", motivo="CI_NOMBRE_DISCORDANTE", resuelto=False),
    ])
    sqlite_dw.commit()

    items = {i["id"]: i for i in dataops.get_review_tray(doc_id=1, id_lote=None, motivo=None, estado=None,
                                                          page=1, page_size=100, db=sqlite_dw)["items"]}
    assert items[1]["un_clic"] is True and items[1]["similitud_nombre_completo"] == 100.0  # antes: línea completa -> 7,7
    assert items[2]["un_clic"] is False  # la CI es de otra persona: se resuelve a mano
