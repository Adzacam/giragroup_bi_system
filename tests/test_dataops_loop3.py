import copy
import json

import pytest
from fastapi import BackgroundTasks, HTTPException, FastAPI
from models.dim_origen import DimOrigenDocumental
from models.lote import Lote
from models.staging_registro import StagingRegistroCrudo
from routers import dataops
from services import cache_consultas, cache_lectura


@pytest.fixture
def lectura(dw_sqlite, monkeypatch, tmp_path):
    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, 'DIR', tmp_path)
    monkeypatch.setattr(dataops.tareas_dataops, 'ultima', lambda *a, **kw: None)
    monkeypatch.setattr(dataops, '_evaluar_documentos_lote', lambda *a, **kw: pytest.fail('Un GET no ejecuta BETO'))
    db = dw_sqlite
    lote = Lote(institucion='Prueba', periodo='2026')
    db.add(lote)
    db.flush()
    docs = []
    for i in range(2):
        doc = DimOrigenDocumental(id_lote=lote.id_lote, nombre_archivo=f'archivo-{i}.csv', tipo_fuente='ACTA')
        db.add(doc)
        db.flush()
        docs.append(doc)
        db.add(StagingRegistroCrudo(id_documento=doc.id_documento, texto_plano='contenido', n_filas=7))
    db.commit()
    detalles = []
    for i, indice in enumerate([0, 59, 60, 84.9, 85, 99, 90] * 2):
        estado = 'AUTOMATICO' if indice >= 85 else 'REVISION' if indice >= 60 else 'INCONSISTENCIA'
        texto = f'Nombre Completo: Persona Privada | CI: 7391044 | ID ACADEMICO: POS-7391044 | Celular: 71234567 | Correo: privado@example.com | NIT: 1029384756 | Dirección: Calle Privada 123 | Fecha nacimiento: 01/02/1990 | Módulo: Minería {i} | Nota: 80'
        detalles.append({'id': f'REG_{i+1}_1', 'stg_id': i + 1, 'id_documento': docs[i // 7].id_documento,
            'line_number': i + 1, 'nombre_archivo': docs[i // 7].nombre_archivo,
            'tipo_fuente': 'ACTA', 'estado': estado, 'categoria_particion': estado,
            'indice_registro': indice, 'raw_text': texto, 'estudiante': 'Persona Privada',
            'ci': '7391044', 'ci_enmascarado': '7391044', 'ci_real': '7391044',
            'modulo': f'Minería {i}', 'nota_normalizada': 80,
            'area': 'academica' if i % 2 else 'financiera', 'en_calidad': estado != 'AUTOMATICO',
            'decision': {'motivo_llano': f'Revisar a Persona Privada (7391044)'},
            'lectura': {'texto': texto, 'tokens': [{'text': 'Persona'}, {'text': 'Privada'}],
                'entidades': [{'label': 'ESTUDIANTE', 'token': 'Persona Privada', 'matchedCanonical': 'Persona Privada'},
                              {'label': 'DOCUMENTO / CI', 'token': '7391044'}, {'label': 'CALIFICACIÓN', 'token': '80'}]}})
    base = {'totalTuplas': 14, 'totalEntidades': 42, 'autoCount': 6, 'auditCount': 4,
            'inconsistenciasCount': 4, 'autoPct': 42.9, 'auditPct': 28.6, 'inconsistenciasPct': 28.5,
            'indiceMedio': 68.27, 'detalles': detalles}
    clave = ('evaluacion_lectura', tuple(d.id_documento for d in docs), dataops._huella_evaluacion(db, [d.id_documento for d in docs]))
    cache_lectura.guardar(clave, base)
    yield db, lote, docs, base, clave
    cache_consultas.invalidar()


def leer(fixture, **kwargs):
    db, lote, *_ = fixture
    return dataops.get_lote_beto_reading(str(lote.id_lote), db=db, page=kwargs.pop('page', 1), page_size=5, **kwargs)


def test_pagina_cinco_registros_y_conteo_global(lectura):
    paginas = [leer(lectura, page=p) for p in range(1, 4)]
    assert [len(p['registros']) for p in paginas] == [5, 5, 4]
    assert len({r['id'] for p in paginas for r in p['registros']}) == 14
    assert all(p['pagination']['total_items'] == 14 for p in paginas)
    assert paginas[0]['registros'][0]['indice_registro'] == 0
    assert paginas[0]['resumen_ejecutivo']['total_procesados'] == 14


def test_filtros_son_globales_y_la_busqueda_ignora_acentos(lectura):
    assert leer(lectura, search='mineria 13')['pagination']['total_items'] == 1
    assert leer(lectura, area='academica')['pagination']['total_items'] == 7
    assert leer(lectura, tipo_entidad='CALIFICACION')['pagination']['total_items'] == 14
    assert leer(lectura, filtro_global='BAJA_CONFIANZA')['pagination']['total_items'] == 8
    assert leer(lectura, estado='AUTOMATICO')['pagination']['total_items'] == 6


def test_indice_ausente_no_se_sustituye_por_un_valor_inventado(lectura):
    *_, base, clave = lectura
    base['detalles'][0]['indice_registro'] = None
    cache_lectura.guardar(clave, base)
    assert leer(lectura)['registros'][0]['indice_registro'] is None
    assert leer(lectura, filtro_global='BAJA_CONFIANZA')['pagination']['total_items'] == 7


def test_no_inventa_cedula_protegida_si_no_existe():
    from services.dataops_privacy import registro_beto_publico
    publico = registro_beto_publico({'id': 'REG_1_1', 'ci': 'No provisto', 'ci_enmascarado': 'No provisto', 'raw_text': 'Nota: 80', 'lectura': {'entidades': []}})
    assert publico['ci'] is None and publico['ci_enmascarado'] is None


def test_programa_del_archivo_no_se_oculta_por_una_etiqueta_erronea_del_modelo():
    from services.dataops_privacy import registro_beto_publico
    texto = 'NOMBRE DEL PROGRAMA: Gestión Pública | NOMBRES: Persona Privada | CI: 7391044'
    publico = registro_beto_publico({'raw_text': texto, 'estudiante': 'Gestión Pública',
        'lectura': {'texto': texto, 'entidades': [{'label': 'ESTUDIANTE', 'token': 'Gestión Pública'}]}})
    assert 'Gestión Pública' in publico['raw_text']
    assert publico['lectura']['texto'] == publico['raw_text']
    assert 'Persona Privada' not in publico['raw_text'] and '7391044' not in publico['raw_text']
    assert publico['lectura']['entidades'][0]['token'] == '••••'


def test_filtro_de_archivo_reutiliza_lectura_completa(lectura):
    _, _, docs, *_ = lectura
    res = leer(lectura, doc_id=docs[1].id_documento, page=2)
    assert res['pagination']['total_items'] == 7
    assert res['resumen_ejecutivo']['total_procesados'] == 7
    assert len(res['registros']) == 2
    assert {r['id_documento'] for r in res['registros']} == {docs[1].id_documento}


def test_privacidad_sobre_cache_antigua_sin_modificarla(lectura):
    *_, base, clave = lectura
    antes = copy.deepcopy(cache_lectura.leer(clave))
    res = leer(lectura)
    texto = json.dumps(res, ensure_ascii=False)
    for secreto in ('7391044', 'Persona Privada', '71234567', 'privado@example.com', '1029384756', 'Calle Privada', '01/02/1990'):
        assert secreto not in texto
    assert '••••044' in texto
    assert cache_lectura.leer(clave) == antes
    assert 'tokens' not in res['registros'][0]['lectura']


def test_get_sin_cache_no_calcula_no_espera_ni_crea_tareas(lectura, monkeypatch):
    _, _, _, _, clave = lectura
    cache_lectura._ruta(clave).unlink()
    monkeypatch.setattr(dataops.tareas_dataops, 'crear', lambda *a, **kw: pytest.fail('El GET no crea tareas'))
    monkeypatch.setattr(dataops, '_cerrar_transaccion_lectura', lambda *a: pytest.fail('El GET no espera un cálculo'))
    assert leer(lectura)['status'] == 'pending'
    db, lote, *_ = lectura
    assert dataops.get_lote_resumen(str(lote.id_lote), doc_id=None, db=db)['status'] == 'pending'


def test_get_devuelve_progreso_existente_sin_esperar(lectura, monkeypatch):
    *_, clave = lectura
    cache_lectura._ruta(clave).unlink()
    monkeypatch.setattr(dataops.tareas_dataops, 'ultima', lambda *a: {'id': 77, 'estado': 'EN_CURSO', 'total': 100, 'procesados': 20, 'porcentaje': 20})
    res = leer(lectura)
    assert res['status'] == 'processing' and res['tarea']['procesados'] == 20


def test_archivo_ajeno_y_pagina_fuera_de_rango(lectura):
    db, *_ = lectura
    doc = DimOrigenDocumental(nombre_archivo='ajeno.csv')
    db.add(doc)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        leer(lectura, doc_id=doc.id_documento)
    assert exc.value.status_code == 404
    assert leer(lectura, page=99)['registros'] == []


def test_inicio_es_explicito_y_no_programa_duplicados(lectura, monkeypatch):
    db, lote, _, _, clave = lectura
    cache_lectura._ruta(clave).unlink()
    tareas = {}
    reservas = []
    monkeypatch.setattr(dataops.tareas_dataops, 'ultima_en_sesion', lambda *a: tareas.get('actual'))
    def reservar(*args):
        reservas.append(1)
        tareas['actual'] = {'id': 77, 'estado': 'EN_CURSO'}
        return 77
    monkeypatch.setattr(dataops.tareas_dataops, 'crear_en_sesion', reservar)
    monkeypatch.setattr(dataops.tareas_dataops, 'obtener', lambda *a: tareas['actual'])
    primera, segunda = BackgroundTasks(), BackgroundTasks()
    assert dataops.iniciar_lectura_lote(lote.id_lote, primera, db)['tarea_id'] == 77
    assert dataops.iniciar_lectura_lote(lote.id_lote, segunda, db)['tarea']['id'] == 77
    assert reservas == [1] and len(primera.tasks) == 1 and segunda.tasks == []
    assert primera.tasks[0].args[-1] == 77


def test_no_recalcula_lectura_ya_disponible(lectura, monkeypatch):
    db, lote, *_ = lectura
    monkeypatch.setattr(dataops.tareas_dataops, 'ultima_en_sesion', lambda *a: None)
    tareas = BackgroundTasks()
    assert dataops.iniciar_lectura_lote(lote.id_lote, tareas, db)['status'] == 'ready'
    assert tareas.tasks == []


def test_lote_cerrado_no_permite_iniciar_otra_lectura(lectura):
    from models.log_pipeline import LogPipelineIngesta
    db, lote, docs, *_ = lectura
    db.add(LogPipelineIngesta(id_documento=docs[0].id_documento, etapa='DW_CONSOLIDACION', nivel='SUCCESS', mensaje='Consolidado'))
    db.commit()
    with pytest.raises(HTTPException) as exc:
        dataops.iniciar_lectura_lote(lote.id_lote, BackgroundTasks(), db)
    assert exc.value.status_code == 409
    assert leer(lectura)['status'] == 'success'


def test_api_no_admite_mas_de_cinco_y_aplica_roles(lectura):
    from fastapi.testclient import TestClient
    from core.database import get_db
    from core.security import get_current_user
    from models.user import User
    db, lote, *_ = lectura
    app = FastAPI()
    app.include_router(dataops.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username='prueba', role='ADMIN')
    cliente = TestClient(app)
    url = f'/api/v1/dataops/lote/{lote.id_lote}/beto-reading'
    assert cliente.get(url, params={'page_size': 6}).status_code == 422
    assert cliente.get(url, params={'page': 0}).status_code == 422
    assert len(cliente.get(url).json()['registros']) == 5
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username='prueba', role='ANALISTA_FINANCIERO')
    assert cliente.get(url).status_code == 403


def test_worker_reutiliza_reserva_guarda_resultado_y_finaliza(lectura, monkeypatch):
    db, lote, docs, base, clave = lectura
    terminadas = []
    ids = [d.id_documento for d in docs]
    lote_id = lote.id_lote
    monkeypatch.setattr(dataops, 'SessionLocal', lambda: db)
    monkeypatch.setattr(dataops.tareas_dataops, 'crear', lambda *a, **kw: pytest.fail('La tarea ya está reservada'))
    monkeypatch.setattr(dataops.tareas_dataops, 'terminar', lambda tid, r: terminadas.append((tid, r)))
    monkeypatch.setattr(dataops.tareas_dataops, 'fallar', lambda *a: pytest.fail('El worker no debe fallar'))
    def evaluar(db_worker, docs_worker, persistir_staging, tarea_id):
        assert persistir_staging and tarea_id == 77
        assert [d.id_documento for d in docs_worker] == ids
        return base
    monkeypatch.setattr(dataops, '_evaluar_documentos_lote', evaluar)
    dataops._evaluar_lote_en_segundo_plano(ids, lote_id, 77)
    assert terminadas == [(77, {'total_tuplas': 14})]
    assert cache_lectura.leer(clave)['totalTuplas'] == 14


def test_fallo_al_reservar_no_programa_analisis(lectura, monkeypatch):
    db, lote, _, _, clave = lectura
    cache_lectura._ruta(clave).unlink()
    monkeypatch.setattr(dataops.tareas_dataops, 'ultima_en_sesion', lambda *a: None)
    def fallar(*a):
        raise RuntimeError('Base no disponible')
    monkeypatch.setattr(dataops.tareas_dataops, 'crear_en_sesion', fallar)
    tareas = BackgroundTasks()
    with pytest.raises(HTTPException) as exc:
        dataops.iniciar_lectura_lote(lote.id_lote, tareas, db)
    assert exc.value.status_code == 503
    assert tareas.tasks == []


def test_no_notifica_exito_si_no_se_pueden_guardar_resultados(lectura, monkeypatch):
    db, lote, docs, base, _ = lectura
    errores = []
    ids, lote_id = [d.id_documento for d in docs], lote.id_lote
    monkeypatch.setattr(dataops, 'SessionLocal', lambda: db)
    monkeypatch.setattr(dataops, '_evaluar_documentos_lote', lambda *a, **kw: base)
    monkeypatch.setattr(cache_lectura, 'guardar', lambda *a: False)
    monkeypatch.setattr(dataops.tareas_dataops, 'terminar', lambda *a: pytest.fail('No se deben anunciar resultados que no se guardaron'))
    monkeypatch.setattr(dataops.tareas_dataops, 'fallar', lambda tid, mensaje: errores.append((tid, mensaje)))
    dataops._evaluar_lote_en_segundo_plano(ids, lote_id, 77)
    assert errores and errores[0][0] == 77


def test_error_de_tarea_no_publica_parametros_personales():
    from types import SimpleNamespace
    from services import tareas_dataops
    fila = SimpleNamespace(_mapping={'id': 1, 'estado': 'ERROR', 'sin_latido': 0,
        'transcurrido': 5, 'total': 10, 'procesados': 2, 'error': 'SQL: Persona Privada, CI 7391044'})
    resultado = tareas_dataops._serializar(fila)
    assert '7391044' not in resultado['error'] and 'SQL' not in resultado['error']
    assert fila._mapping['error'] == 'SQL: Persona Privada, CI 7391044'
