from io import BytesIO

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.datastructures import Headers, UploadFile

from models.dim_origen import DimOrigenDocumental
from models.lote import Lote
from models.staging_registro import StagingRegistroCrudo
from routers import dataops
from services.ingestion_service import IngestionService


@pytest.fixture
def ingesta_aislada(dw_sqlite, monkeypatch, tmp_path):
    monkeypatch.setattr(dataops, 'LANDING_DIR', str(tmp_path))
    for metodo in ('crear', 'avanzar', 'terminar', 'fallar', 'ultima'):
        monkeypatch.setattr(dataops.tareas_dataops, metodo, lambda *a, **kw: None)
    return dw_sqlite


def subir(db, archivos, tipo='ADMISION', escala=None):
    return dataops.upload_batch(
        files=archivos, source_types=[tipo] * len(archivos), tipos_fuente=[tipo] * len(archivos),
        tipos_escala=[escala] * len(archivos) if escala else None,
        archivos_meta=None, institucion='Institución de prueba', periodo='Auto', tipo_escala_global=None,
        background_tasks=BackgroundTasks(), db=db,
    )


def csv_archivo(nombre='inscripciones.csv', contenido=None):
    return UploadFile(filename=nombre, file=BytesIO(contenido or b'Nombre Completo,Cedula de Identidad,Ciudad\nPersona Prueba,1234567,La Paz\n'), headers=Headers({'content-type': 'text/csv'}))


def test_historial_pagina_lotes_sin_duplicarlos_por_archivo(ingesta_aislada):
    db = ingesta_aislada
    for n in range(7):
        lote = Lote(institucion='Prueba', periodo='Auto')
        db.add(lote)
        db.flush()
        for i in range(2):
            doc = DimOrigenDocumental(id_lote=lote.id_lote, nombre_archivo=f'{n}-{i}.csv', tipo_fuente='ADMISION')
            db.add(doc)
            db.flush()
            db.add(StagingRegistroCrudo(id_documento=doc.id_documento, texto_plano='contenido', n_filas=3))
    db.commit()
    primera = dataops.get_historial_lotes(page=1, page_size=5, db=db)
    segunda = dataops.get_historial_lotes(page=2, page_size=5, db=db)
    assert primera['total'] == 7
    assert len(primera['data']) == 5 and len(segunda['data']) == 2
    assert primera['data'][0]['records'] == 6
    assert primera['data'][0]['total_archivos'] == 2
    assert primera['data'][0]['status'] == 'TEXTO_LISTO'
    assert not set(r['id_lote'] for r in primera['data']) & set(r['id_lote'] for r in segunda['data'])


def test_historial_reconoce_consolidacion_de_evaluacion_docente(ingesta_aislada):
    from models.fact_evaluacion import FactEvaluacionDocente
    db = ingesta_aislada
    lote = Lote(institucion='Prueba', periodo='2026')
    db.add(lote)
    db.flush()
    doc = DimOrigenDocumental(id_lote=lote.id_lote, tipo_fuente='EVALUACION_DOCENTE')
    db.add(doc)
    db.flush()
    db.add(FactEvaluacionDocente(id_documento=doc.id_documento, requiere_revision=False))
    db.commit()
    assert dataops.get_historial_lotes(page=1, page_size=5, db=db)['data'][0]['status'] == 'CONSOLIDADO'


@pytest.mark.parametrize('nombre,contenido', [('archivo.xls', b'abc'), ('vacio.csv', b''), ('falso.xlsx', b'no es Excel'), ('binario.csv', b'\x00archivo')])
def test_rechaza_formatos_invalidos(nombre, contenido):
    assert IngestionService.validar_seguridad_archivo(nombre, contenido)


def test_limites_de_tamano_y_cantidad(ingesta_aislada):
    assert IngestionService.validar_seguridad_archivo('grande.csv', b'a' * (50 * 1024 * 1024 + 1))
    with pytest.raises(HTTPException) as exc:
        subir(ingesta_aislada, [csv_archivo()] * 31)
    assert exc.value.status_code == 400


def test_escala_es_obligatoria_en_el_servidor(ingesta_aislada):
    resultado = subir(ingesta_aislada, [csv_archivo('notas.csv', b'Nombre Completo,CI,Modulo,Nota\nPersona Prueba,1234567,Modulo 1,80\n')], tipo='ACTA')
    assert resultado.archivos_exitosos == 0
    assert 'escala' in resultado.resultados[0].mensaje.lower()


def test_csv_valido_y_duplicado_con_periodo_autodetectado(ingesta_aislada):
    db = ingesta_aislada
    primero = subir(db, [csv_archivo()])
    assert primero.archivos_exitosos == 1
    doc = db.query(DimOrigenDocumental).first()
    doc.periodo = '2026-1'
    db.commit()
    segundo = subir(db, [csv_archivo('otro_nombre.csv')])
    assert segundo.archivos_exitosos == 0
    assert segundo.resultados[0].status == 'duplicado'
    assert db.query(DimOrigenDocumental).count() == 1


def test_excel_valido_con_escala_explicita(ingesta_aislada):
    from openpyxl import Workbook
    libro = Workbook()
    libro.active.append(['Nombre Completo', 'Cedula de Identidad', 'Modulo', 'Nota'])
    libro.active.append(['Persona Prueba', '1234567', 'Modulo 1', 80])
    contenido = BytesIO()
    libro.save(contenido)
    archivo = UploadFile(filename='notas.xlsx', file=BytesIO(contenido.getvalue()))
    resultado = subir(ingesta_aislada, [archivo], tipo='ACTA', escala='CENTESIMAL_100')
    assert resultado.archivos_exitosos == 1
    assert resultado.resultados[0].tipo_escala == 'CENTESIMAL_100'


def test_reintento_rechaza_lectura_que_no_fallo(ingesta_aislada):
    db = ingesta_aislada
    resultado = subir(db, [csv_archivo()])
    tareas = BackgroundTasks()
    with pytest.raises(HTTPException) as exc:
        dataops.reintentar_lectura_lote(resultado.id_lote, tareas, db)
    assert exc.value.status_code == 409
    assert tareas.tasks == []


def test_eliminar_historial_no_permite_lotes_con_datos(ingesta_aislada):
    db = ingesta_aislada
    resultado = subir(db, [csv_archivo()])
    with pytest.raises(HTTPException) as exc:
        dataops.eliminar_lote_fallido(resultado.id_lote, db)
    assert exc.value.status_code == 409
    assert db.query(DimOrigenDocumental).count() == 1


def test_elimina_solo_entrada_fallida_sin_documentos(ingesta_aislada):
    db = ingesta_aislada
    lote = Lote(institucion='Prueba', periodo='Auto', estado='CON_ERRORES')
    db.add(lote)
    db.commit()
    assert dataops.eliminar_lote_fallido(lote.id_lote, db)['status'] == 'success'
    assert db.query(Lote).count() == 0


def test_tarea_interrumpida_persiste_el_error_para_notificar(monkeypatch):
    from types import SimpleNamespace
    from services import tareas_dataops
    avisos = []
    monkeypatch.setattr(tareas_dataops, 'fallar', lambda tid, mensaje: avisos.append((tid, mensaje)))
    fila = SimpleNamespace(_mapping={
        'id': 42, 'estado': 'EN_CURSO', 'sin_latido': tareas_dataops.SIN_LATIDO_SEG + 1,
        'transcurrido': 200, 'total': 10, 'procesados': 2,
    })
    resultado = tareas_dataops._serializar(fila)
    assert resultado['estado'] == 'ERROR'
    assert avisos == [(42, resultado['error'])]
