"""
FU-L1: integración del lector con la ingesta (IngestionService) y la consolidación, en SQLite y con
libros sintéticos de datos ficticios.

- Cada hoja ignorada queda UNA vez como HOJA_IGNORADA (informativa), no como N líneas LINEA_SIN_ENTIDAD.
- Filas fantasma y subtotales no llegan a staging.
- Original y variante (otros nombres, columnas en otro orden) dejan el mismo staging.
- Una hoja de planificación dentro de un libro de actas y una encuesta por módulo con cola de filas
  fantasma ya no se descartan.
- Una cabecera con correo no llega a staging, a los logs ni a la respuesta.
"""

import importlib
import json
from collections import Counter

import pytest

from models.dim_origen import DimOrigenDocumental
from models.fact_planificacion import FactPlanificacionPrograma
from models.log_inconsistencia import LogInconsistencia
from models.log_pipeline import LogPipelineIngesta
from models.lote import Lote
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from services.extraccion_por_encabezado import campos_por_encabezado
from tests.dataops_parches import _MODULOS
from tests.fixtures.fuentes_sinteticas import constructor as ctor


@pytest.fixture
def ingesta(dw_sqlite, monkeypatch, tmp_path):
    from services import cache_lectura, ingestion_service
    monkeypatch.setattr(cache_lectura, "DIR", tmp_path)
    monkeypatch.setattr(ingestion_service, "AsymmetricFlattener", None)
    db = dw_sqlite
    lote = Lote(institucion="Prueba", periodo="2026")
    db.add(lote)
    db.commit()

    def _procesar(ruta, **kw):
        res = ingestion_service.IngestionService.procesar_archivo(
            db, str(ruta), ruta.name, id_lote=lote.id_lote, institucion="Prueba", **kw)
        return res, db.query(DimOrigenDocumental).filter_by(id_documento=res["id_documento"]).one()

    return db, lote, _procesar


def _lineas(db, doc_id):
    return [l for s in db.query(StagingRegistroCrudo).filter_by(id_documento=doc_id).all()
            for l in (s.texto_plano or "").splitlines() if l.strip()]


def _ignoradas(db, doc_id):
    return db.query(LogInconsistencia).filter_by(id_documento=doc_id, tipo_regla="HOJA_IGNORADA").all()


def test_hojas_ignoradas_una_vez_y_sin_filas_fantasma_ni_subtotales(ingesta, tmp_path):
    db, _, procesar = ingesta
    ruta = ctor.construir(ctor.ORIGINAL, tmp_path)
    res, doc = procesar(ruta, tipo_fuente="COBRANZA")

    hojas_stg = {s.hoja for s in db.query(StagingRegistroCrudo).filter_by(id_documento=doc.id_documento)}
    assert hojas_stg == {ctor.ORIGINAL.hoja_datos}
    assert len(_lineas(db, doc.id_documento)) == 6  # 6 estudiantes; sin subtotal ni cola fantasma

    ign = _ignoradas(db, doc.id_documento)
    assert len(ign) == 6 == len({i.campo_afectado for i in ign})  # una vez por hoja
    assert all(i.estado_resolucion == "REGISTRADO" and i.severidad == "BAJA" for i in ign)
    assert {i.campo_afectado for i in ign} == {
        ctor.ORIGINAL.hoja_oculta, ctor.ORIGINAL.hoja_borrador, ctor.ORIGINAL.hoja_copia,
        ctor.ORIGINAL.hoja_dinamica, ctor.ORIGINAL.hoja_numerada, ctor.ORIGINAL.hoja_resumen}
    assert db.query(LogInconsistencia).filter_by(tipo_regla="LINEA_SIN_ENTIDAD").count() == 0
    assert db.query(StagingEntidadNoResuelta).count() == 0  # nada pendiente en la bandeja

    assert len(res["hojas"]) == 7 and sum(h["decision"] == "usar" for h in res["hojas"]) == 1
    avisos = db.query(LogPipelineIngesta).filter_by(id_documento=doc.id_documento, nivel="WARN").all()
    assert any("fórmula sin valor" in a.mensaje for a in avisos)  # aviso agregado por hoja, no por celda
    assert sum("fórmula sin valor" in a.mensaje for a in avisos) == 1


def test_original_y_variante_dejan_el_mismo_staging(ingesta, tmp_path):
    db, _, procesar = ingesta
    a, b = ctor.construir_par(tmp_path)
    _, doc_a = procesar(a, tipo_fuente="COBRANZA")
    _, doc_b = procesar(b, tipo_fuente="COBRANZA")
    assert doc_a.tipo_fuente == doc_b.tipo_fuente == "COBRANZA"

    def campos(doc):
        return sorted(json.dumps(campos_por_encabezado([c.strip() for c in l.split("|")]), sort_keys=True)
                      for l in _lineas(db, doc.id_documento))

    assert campos(doc_a) == campos(doc_b)
    reglas = lambda doc: Counter(i.descripcion.split(" ignorada: ")[1] for i in _ignoradas(db, doc.id_documento))
    assert reglas(doc_a) == reglas(doc_b)


def test_cabecera_con_correo_no_llega_a_staging_logs_ni_respuesta(ingesta, tmp_path):
    db, _, procesar = ingesta
    receta = ctor.Receta(**{**ctor.ORIGINAL.__dict__, "archivo": "con_correo.xlsx", "con_correo_en_cabecera": True})
    res, doc = procesar(ctor.construir(receta, tmp_path), tipo_fuente="COBRANZA")
    textos = [s.texto_plano for s in db.query(StagingRegistroCrudo).all()]
    textos += [f"{l.mensaje} {json.dumps(l.metadata_json, ensure_ascii=False)}" for l in db.query(LogPipelineIngesta).all()]
    textos += [f"{i.campo_afectado} {i.valor_recibido} {i.descripcion}" for i in db.query(LogInconsistencia).all()]
    textos.append(json.dumps(res, ensure_ascii=False, default=str))
    assert not any(ctor.CORREO_FICTICIO in t for t in textos)
    assert any("col_13: " in t for t in textos)


def _parchear_consolidacion(monkeypatch):
    for modulo in ["services.confianza_service"] + ["routers.dataops" + suf for suf in _MODULOS]:
        mod = importlib.import_module(modulo)
        if hasattr(mod, "obtener_indices"):
            monkeypatch.setattr(mod, "obtener_indices", lambda lineas, **kw: [.95] * len(lineas))
        if hasattr(mod, "indices_en_cache"):
            monkeypatch.setattr(mod, "indices_en_cache", lambda lineas: [.95] * len(lineas))
    enviadas = []
    monkeypatch.setattr("psycopg2.extras.execute_values", lambda cur, sql, filas, page_size=None: enviadas.extend(filas))
    return enviadas


def test_hoja_de_planificacion_en_libro_de_actas_no_se_descarta(ingesta, tmp_path, monkeypatch):
    from routers import dataops
    from services import cache_consultas

    db, lote, procesar = ingesta
    cache_consultas.invalidar()
    _parchear_consolidacion(monkeypatch)
    _, doc = procesar(ctor.construir_libro_mixto(tmp_path), tipo_fuente="ACTA", tipo_escala="CENTESIMAL_100")
    assert doc.tipo_fuente == "ACTA"
    cats = {s.hoja: s.categoria for s in db.query(StagingRegistroCrudo).filter_by(id_documento=doc.id_documento)}
    assert cats["Planificación por POS"] == "planificacion"  # por sus cabeceras, no por su nombre
    assert cats["Notas"] == "academico"

    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)
    descartes = db.query(LogInconsistencia).filter_by(tipo_regla="LINEA_SIN_ENTIDAD").all()
    assert not [d for d in descartes if d.campo_afectado == "Planificación por POS"]
    assert db.query(FactPlanificacionPrograma).filter_by(id_documento=doc.id_documento).count() == 6
    cache_consultas.invalidar()


def test_encuesta_por_modulo_con_cola_fantasma_no_genera_descartes(ingesta, tmp_path, monkeypatch):
    from routers import dataops
    from services import cache_consultas

    db, lote, procesar = ingesta
    cache_consultas.invalidar()
    enviadas = _parchear_consolidacion(monkeypatch)
    _, doc = procesar(ctor.construir_encuesta_por_modulo(tmp_path), tipo_fuente="EVALUACION_DOCENTE")
    assert len(_lineas(db, doc.id_documento)) == 6  # las 40 filas con solo «N°» no son filas leídas

    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)
    assert db.query(LogInconsistencia).filter_by(tipo_regla="LINEA_SIN_ENTIDAD").count() == 0
    assert len(enviadas) == 6 * 3  # 6 respuestas x 3 preguntas
    cache_consultas.invalidar()


def _hoja_plan(ws, n, mes):
    cab = ["FECHA", "POS", "PROGRAMA", "ESTADO", "N° INSCRITOS", "LEADS"]
    for c, v in enumerate(cab, start=1):
        ws.cell(row=1, column=c, value=v)
    for r in range(2, 2 + n):
        for c, v in enumerate([f"2026-{mes:02d}-01", 9100 + r, f"DIPLOMADO FICTICIO {r}", "Inicio Confirmado", r, 10 * r], start=1):
            ws.cell(row=r, column=c, value=v)


def test_libro_de_planificacion_registra_hojas_y_avisa_conflicto_con_el_extractor(ingesta, tmp_path):
    """El extractor de planificación conserva su selección (cifras congeladas); el lector registra las hojas sin
    filas como HOJA_IGNORADA y avisa si el extractor lee una hoja que las reglas genéricas ignoran (oculta)."""
    import openpyxl
    db, _, procesar = ingesta
    wb = openpyxl.Workbook()
    _hoja_plan(wb.active, 4, 1)
    wb.active.title = "Enero-2026"
    oculta = wb.create_sheet("Diciembre-2025")
    _hoja_plan(oculta, 3, 12)
    oculta.sheet_state = "hidden"
    _hoja_plan(wb.create_sheet("Enero-2026 borrador"), 2, 1)
    wb.create_sheet("Dashboard Ficticio")
    ruta = tmp_path / "plan_ficticio.xlsx"
    wb.save(ruta)

    _, doc = procesar(ruta, tipo_fuente="PLANIFICACION")
    stg = {s.hoja: s.n_filas for s in db.query(StagingRegistroCrudo).filter_by(id_documento=doc.id_documento)}
    assert stg == {"Enero-2026": 4, "Diciembre-2025": 3}  # selección del extractor sin cambios
    ign = {i.campo_afectado: i.descripcion for i in _ignoradas(db, doc.id_documento)}
    assert set(ign) == {"Enero-2026 borrador", "Dashboard Ficticio"}
    avisos = [l.mensaje for l in db.query(LogPipelineIngesta).filter_by(id_documento=doc.id_documento, nivel="WARN")]
    assert any("Diciembre-2025" in a and "extractor de planificación" in a for a in avisos)
