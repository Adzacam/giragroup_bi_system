"""Integridad con archivos y bases aislados: sin uploads, inferencias o cambios reales."""
import io
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest
from sqlalchemy import text
from models.dim_origen import DimOrigenDocumental
from models.dim_modulo import DimModulo
from models.dim_estudiante import DimEstudiante
from models.lote import Lote
from models.staging_registro import StagingRegistroCrudo
from models.fact_marketing import FactMarketing
from models.fact_rendimiento import FactRendimientoAcademico
from routers import dataops
from services import integridad_dataops, cache_consultas
from services.dw_loader import DWLoaderService
from services.kpi_service import KPIService
from services.extraccion_por_encabezado import metricas_captacion, parsear_fecha


def registro(tipo='MARKETING', **metricas):
    return {'tipo_fuente': tipo, 'categoria': 'marketing', 'resoluciones': {
        'programa': {'valor_extraido': 'Programa de prueba', 'metadata': {'pos_canonico': 'POS-9876'}},
        'fecha': date(2026, 3, 1), 'nivel_confianza_ia': .92, **metricas}}


def test_conversion_no_acredita_el_cien_por_ciento_historico(dw_sqlite):
    db = dw_sqlite
    loader = DWLoaderService(db)
    loader.cargar_registro(registro(leads=40, inscritos=10))
    fila = db.query(FactMarketing).one()
    # Simula contadores históricos cuyo origen no acredita captación.
    fila.leads_captacion = fila.inscritos_captacion = None
    db.flush()
    resultado = KPIService(db).obtener_perspectivas_cmi_completo(gestion=2026)
    assert resultado['kpis']['6_tasa_conversion_admisiones'] is None


def test_admisiones_conservan_inscritos_sin_inflar_captacion(dw_sqlite):
    db = dw_sqlite
    loader = DWLoaderService(db)
    loader.cargar_registro(registro(leads=40, inscritos=10))
    loader.cargar_registro(registro('ADMISION'))
    loader.cargar_registro(registro('ADMISION'))
    fila = db.query(FactMarketing).one()
    assert (fila.leads, fila.inscritos) == (40, 12)
    assert (fila.leads_captacion, fila.inscritos_captacion) == (40, 10)
    resultado = KPIService(db).obtener_perspectivas_cmi_completo(gestion=2026)
    assert resultado['kpis']['6_tasa_conversion_admisiones'] == 25


@pytest.mark.parametrize('metricas', [{}, {'inscritos': 5}, {'leads': 0, 'inscritos': 0}, {'leads': 2, 'inscritos': 5}])
def test_sin_pareja_valida_no_se_inventa_conversion(dw_sqlite, metricas):
    DWLoaderService(dw_sqlite).cargar_registro(registro(**metricas))
    assert dw_sqlite.query(FactMarketing).one().leads_captacion is None
    assert KPIService(dw_sqlite).obtener_perspectivas_cmi_completo(gestion=2026)['kpis']['6_tasa_conversion_admisiones'] is None


def test_cero_inscritos_es_una_conversion_real_de_cero(dw_sqlite):
    DWLoaderService(dw_sqlite).cargar_registro(registro(leads=40, inscritos=0))
    assert KPIService(dw_sqlite).obtener_perspectivas_cmi_completo(gestion=2026)['kpis']['6_tasa_conversion_admisiones'] == 0


def test_reintentar_misma_fila_no_duplica_captacion(dw_sqlite):
    db = dw_sqlite
    db.execute(text('CREATE TABLE carga_fila_origen (clave TEXT PRIMARY KEY, id_documento INTEGER, tabla TEXT)'))
    loader = DWLoaderService(db)
    fila = {**registro(leads=40, inscritos=10), 'clave_origen': 'archivo-hoja-fila'}
    assert loader.cargar_registro(fila)['status'] == 'loaded'
    assert loader.cargar_registro(fila)['status'] == 'skipped'
    assert db.query(FactMarketing).one().leads_captacion == 40


def test_extrae_solo_contadores_explicitos_enteros():
    assert metricas_captacion({'LEADS': '40', 'INSCRITOS': '0'}) == {'leads': 40, 'inscritos': 0}
    assert metricas_captacion({'CI': '123456', 'NOMBRES': 'Persona Prueba', 'EDAD': '127'}) == {}
    assert metricas_captacion({'INTERESADOS': '-1', 'INSCRITOS': '2.5'}) == {}


@pytest.mark.parametrize('nombre', ['.', '......', '---'])
def test_no_crea_nuevos_modulos_solo_con_puntuacion(dw_sqlite, nombre):
    assert DWLoaderService(dw_sqlite).resolver_o_crear_modulo(nombre) is None
    assert dw_sqlite.query(DimModulo).count() == 0


def test_catalogo_no_admite_nombres_solo_con_puntos(dw_sqlite):
    from fastapi import HTTPException
    from services.catalog_service import CatalogService
    with pytest.raises(HTTPException) as error:
        CatalogService(dw_sqlite).crear_modulo({'nombre_modulo': '......', 'nombre_institucion': 'Prueba'})
    assert error.value.status_code == 422
    assert dw_sqlite.query(DimModulo).count() == 0


@pytest.mark.parametrize('fecha', ['0005-01-01', '1928-11-22', '2205-01-01', '31/02/2026'])
def test_fechas_invalidas_no_crean_gestiones(fecha):
    assert parsear_fecha(fecha) is None


def test_integridad_no_confunde_ausencia_de_lectura_con_cero(dw_sqlite):
    db = dw_sqlite
    doc = DimOrigenDocumental(nombre_archivo='aislado.csv', tipo_fuente='ACTA')
    db.add(doc); db.flush()
    db.add(StagingRegistroCrudo(id_documento=doc.id_documento, n_filas=2, texto_plano='Dato: 1\n\nDato: 2\nDato: 3'))
    db.add(StagingRegistroCrudo(id_documento=doc.id_documento, n_filas=2, registro_origen_id=1))
    db.flush()
    fila = integridad_dataops.consultar(db, [doc])['data'][0]
    assert fila['filas_origen'] == 2  # las copias de revisión no duplican el archivo
    assert fila['filas_texto'] == 3
    assert dataops._serializar_archivos_lote(db, [doc])[0]['total_registros'] == 3
    assert fila['filas_lectura'] is None and fila['filas_directas'] is None


def test_archivo_lectura_consolidacion_dw_y_kpi(dw_sqlite, monkeypatch, tmp_path):
    from services import ingestion_service, cache_lectura
    from services.ingestion_service import IngestionService
    db = dw_sqlite
    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, 'DIR', tmp_path)
    # Solo sustituye el servicio externo del modelo y el diagnóstico opcional que consulta catálogos externos.
    monkeypatch.setattr(ingestion_service, 'AsymmetricFlattener', None)
    monkeypatch.setattr(dataops, 'obtener_indices', lambda lineas, **kw: [.95] * len(lineas))
    lote = Lote(institucion='Prueba', periodo='2025')
    db.add(lote); db.flush()
    alumnos = [('ANA TORREZ SALINAS', '13727801', 90, 80), ('LUIS PEREZ ROJAS', '13727802', 60, 70)]
    for nombre, ci, _, _ in alumnos:
        db.add(DimEstudiante(nombre_completo=nombre, ci=ci, fk_estado='A'))
    for n in (1, 2):
        db.add(DimModulo(nombre_modulo=f'POS-9876 · Módulo {n}', pos_code=f'POS-9876-M0{n}', programa='Programa de prueba'))
    db.commit()
    buffer = io.BytesIO()
    pd.DataFrame([{'POS - ACTAS': 'POS-9876', 'CI': ci, 'NOMBRE COMPLETO': nombre,
        'MES INICIO': 'Marzo', 'AÑO INICIO': 2025, 'MÓDULO 1': n1, 'MÓDULO 2': n2}
        for nombre, ci, n1, n2 in alumnos]).to_excel(buffer, index=False)
    archivo = tmp_path / 'acta_prueba.xlsx'
    archivo.write_bytes(buffer.getvalue())
    ingesta = IngestionService.procesar_archivo(db, str(archivo), archivo.name,
        id_lote=lote.id_lote, tipo_fuente='ACTA', institucion='Prueba', tipo_escala='CENTESIMAL_100')
    docs = db.query(DimOrigenDocumental).filter_by(id_lote=lote.id_lote).all()
    assert len(docs) == 1 and ingesta['id_documento'] == docs[0].id_documento
    lectura = dataops._evaluar_documentos_lote(db, docs)
    assert lectura['totalTuplas'] == 2
    assert lectura['autoCount'] == 2
    assert lectura['autoCount'] + lectura['auditCount'] + lectura['inconsistenciasCount'] == 2
    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)
    conteos = integridad_dataops.consultar(db, docs, lectura)['data'][0]
    assert conteos['filas_origen'] == conteos['filas_lectura'] == 2
    assert conteos['filas_texto'] == 2
    assert conteos['filas_directas'] == 2
    assert conteos['hechos']['academicos'] == 4
    assert db.query(FactRendimientoAcademico).count() == 4
    cmi = KPIService(db).obtener_perspectivas_cmi_completo(gestion=2025)
    assert cmi['kpis']['7_promedio_acumulado_por_programa']['general'] == 75
    assert cmi['kpis']['8_tasa_aprobacion_reprobacion_por_modulo']['aprobacion_global_pct'] == 75
    cmi_sin_archivo = KPIService(db).obtener_perspectivas_cmi_completo(gestion=2026)
    assert cmi_sin_archivo['kpis']['7_promedio_acumulado_por_programa']['general'] is None
    cache_consultas.invalidar()


def test_integridad_pagina_cinco_y_es_lectura_pura(dw_sqlite, monkeypatch):
    db = dw_sqlite
    lote = Lote(institucion='Prueba', periodo='2026')
    db.add(lote); db.flush()
    for i in range(7):
        db.add(DimOrigenDocumental(id_lote=lote.id_lote, nombre_archivo=f'archivo-{i}.csv', tipo_fuente='ACTA'))
    db.commit()
    monkeypatch.setattr(dataops, '_evaluacion_lectura', lambda *a: None)
    monkeypatch.setattr(dataops, '_evaluar_documentos_lote', lambda *a, **kw: pytest.fail('Un GET no ejecuta el modelo'))
    monkeypatch.setattr(db, 'commit', lambda: pytest.fail('Un GET no guarda datos'))
    primero = dataops.get_lote_integridad(str(lote.id_lote), page=1, db=db, user=None)
    segundo = dataops.get_lote_integridad(str(lote.id_lote), page=2, db=db, user=None)
    assert len(primero['data']) == 5 and len(segundo['data']) == 2
    assert primero['pagination']['total_items'] == 7
    assert all(row['filas_lectura'] is None for row in primero['data'])


@pytest.mark.parametrize('role,esperado', [('ADMIN', 200), ('AUDITOR_CALIDAD', 200), ('ANALISTA_MARKETING', 403), ('DIRECTOR_ACADEMICO', 403)])
def test_integridad_respeta_roles(dw_sqlite, monkeypatch, role, esperado):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from core.database import get_db
    from core.security import get_current_user
    db = dw_sqlite
    lote = Lote(institucion='Prueba', periodo='2026')
    db.add(lote); db.flush()
    db.add(DimOrigenDocumental(id_lote=lote.id_lote, nombre_archivo='prueba.csv', tipo_fuente='ACTA'))
    db.commit()
    monkeypatch.setattr(dataops, '_evaluacion_lectura', lambda *a: None)
    app = FastAPI(); app.include_router(dataops.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role=role, is_active=True)
    assert TestClient(app).get(f'/api/v1/dataops/lote/{lote.id_lote}/integridad').status_code == esperado
