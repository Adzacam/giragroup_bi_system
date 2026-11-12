from types import SimpleNamespace
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.database import get_db, get_catalog_db
from core.security import get_current_user
from models.catalogos import CatInstitucion
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.dim_estudiante import DimEstudiante
from models.dim_docente import DimDocente
from models.log_pipeline import LogPipelineIngesta
from models.staging_registro import StagingRegistroCrudo
from models.fact_rendimiento import FactRendimientoAcademico
from routers import dataops, catalogs
from services import bitacora_dataops


@pytest.fixture
def datos(dw_sqlite, monkeypatch):
    db = dw_sqlite
    CatInstitucion.__table__.create(db.get_bind(), checkfirst=True)
    for i in range(1, 8):
        db.add(CatInstitucion(id_institucion=i, nombre_institucion=f'Institución {i:02}', sigla=f'I{i}'))
    db.commit()
    for i in range(1, 13):
        db.add(DimModulo(id_modulo=i, nombre_modulo=f'Módulo {i:02}', pos_code=f'POS-{i}', nombre_institucion='Institución 01'))
    db.add(DimEstudiante(id_estudiante=1, nombre_completo='Persona Privada', ci='7391044', codigo_estudiante='EST-7391044'))
    db.add(DimDocente(id_docente=1, nombre_completo='Docente Privado'))
    db.add_all([DimOrigenDocumental(id_documento=1, nombre_archivo='acta.csv', tipo_fuente='ACTA'),
                DimOrigenDocumental(id_documento=2, nombre_archivo='otro.csv', tipo_fuente='ACTA')])
    db.add_all([StagingRegistroCrudo(id_documento=1, n_filas=11, texto_plano='Nombre: Persona Privada | CI: 7391044'),
                StagingRegistroCrudo(id_documento=1, n_filas=4, texto_plano='datos')])
    matriz = [{'cabecera_original': f'Columna {i}', 'cabecera_normalizada': f'campo_{i}',
               'regla': 'Regla registrada', 'valor_ejemplo': 'Persona Privada, 7391044'} for i in range(12)]
    for i in range(1, 13):
        db.add(LogPipelineIngesta(id=i, id_documento=1, etapa='NORMALIZE' if i == 1 else 'VALIDATE',
            nivel='INFO', mensaje='SQL: Persona Privada, CI 7391044, privado@example.com',
            tiempo_ms=0 if i == 1 else None, metadata_json={'matriz': matriz} if i == 1 else {}))
    db.add(LogPipelineIngesta(id=100, id_documento=2, etapa='UPLOAD', nivel='ERROR', mensaje='Solo de otro documento'))
    db.commit()
    monkeypatch.setattr(dataops, '_evaluar_documentos_lote', lambda *a, **kw: pytest.fail('No debe ejecutar BETO'))
    yield db, db


def cliente(datos, role='ADMIN'):
    db, cat = datos
    app = FastAPI()
    app.include_router(dataops.router)
    app.include_router(catalogs.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_catalog_db] = lambda: cat
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=None, username='prueba', role=role, is_active=True)
    return TestClient(app)


def test_catalogo_solo_referencia_paginado_y_busqueda_global(datos):
    with cliente(datos) as c:
        ruta = '/api/v1/dataops/catalogs'
        paginas = [c.get(ruta, params={'page': p}).json() for p in (1, 2, 3)]
        assert [len(p['data']) for p in paginas] == [5, 5, 2]
        assert all(p['pagination']['total_items'] == 12 for p in paginas)
        assert c.get(ruta, params={'search': 'POS-12'}).json()['data'][0]['id'] == 12
        assert 'Persona Privada' not in json.dumps(paginas) and 'Docente Privado' not in json.dumps(paginas)
        assert c.get(ruta, params={'page': 0}).status_code == 422
        assert c.get(ruta, params={'tipo': 'estudiantes'}).status_code == 422
        assert c.get(ruta, params={'tipo': 'docentes'}).status_code == 422


def test_identificadores_mal_clasificados_no_se_publican_completos(datos):
    db, _ = datos
    modulo = db.get(DimModulo, 1)
    modulo.nombre_modulo = '7391044'
    modulo.programa = 'Correo: privado@example.com'
    db.commit()
    with cliente(datos) as c:
        r = c.get('/api/v1/dataops/catalogs', params={'search': '7391044'})
    assert r.status_code == 200
    assert '7391044' not in r.text and 'privado@example.com' not in r.text


def test_instituciones_provienen_del_catalogo_sin_ejemplos(datos):
    with cliente(datos) as c:
        r = c.get('/api/v1/dataops/catalogs', params={'tipo': 'instituciones', 'page': 2}).json()
    assert r['pagination']['total_items'] == 7 and len(r['data']) == 2
    assert {fila['id'] for fila in r['data']} == {6, 7}
    assert all('estado' not in f and 'tipo' not in f for f in r['data'])


def test_endpoint_antiguo_de_personas_no_existe(datos):
    with cliente(datos) as c:
        assert c.get('/api/v1/dataops/entities/unresolved').status_code == 404


@pytest.mark.parametrize('role', ['DIRECTOR_ACADEMICO', 'ANALISTA_FINANCIERO'])
def test_roles_no_autorizados_no_acceden_a_dataops(datos, role):
    with cliente(datos, role) as c:
        assert c.get('/api/v1/dataops/catalogs').status_code == 403
        assert c.get('/api/v1/dataops/logs/1').status_code == 403
        assert c.post('/api/v1/modulos', json={'nombre_modulo': 'Nuevo', 'nombre_institucion': 'Institución 01'}).status_code == 403


def test_alta_real_sin_relleno_y_sin_duplicado(datos):
    db, _ = datos
    with cliente(datos) as c:
        payload = {'nombre_modulo': ' Nuevo módulo ', 'nombre_institucion': 'Institución 01'}
        r = c.post('/api/v1/modulos', json=payload)
        assert r.status_code == 200
        registro = db.get(DimModulo, r.json()['data']['id_modulo'])
        assert registro.nombre_modulo == 'Nuevo módulo'
        assert registro.programa is None and registro.pos_code is None
        assert c.post('/api/v1/modulos', json=payload).status_code == 409
        assert db.query(DimModulo).count() == 13


@pytest.mark.parametrize('payload', [{'nombre_modulo': 'Nuevo'}, {'nombre_modulo': '  ', 'nombre_institucion': 'Institución'}, {'nombre_modulo': 'Nuevo', 'nombre_institucion': ''}])
def test_alta_invalida_no_escribe(datos, payload):
    with cliente(datos) as c:
        assert c.post('/api/v1/modulos', json=payload).status_code == 422
    assert datos[0].query(DimModulo).count() == 12


def test_baja_con_vinculos_conserva_modulo_e_historial(datos):
    db, _ = datos
    db.add(FactRendimientoAcademico(id_hecho_aca=1, id_modulo=1, nota_final=80))
    db.commit()
    with cliente(datos) as c:
        assert c.delete('/api/v1/modulos/1').status_code == 409
    assert db.get(DimModulo, 1) is not None and db.get(FactRendimientoAcademico, 1) is not None


def test_baja_sin_vinculos_y_avisos_por_rol(datos):
    from models.notification import Notification
    db, _ = datos
    with cliente(datos) as c:
        assert c.delete('/api/v1/modulos/12').status_code == 200
        assert c.delete('/api/v1/modulos/12').status_code == 404
    assert db.get(DimModulo, 12) is None
    avisos = db.query(Notification).all()
    assert {n.role_target for n in avisos} == {'ADMIN', 'AUDITOR_CALIDAD'}


def test_bitacora_pagina_eventos_y_mapeos_reales_sin_pii(datos):
    db, _ = datos
    r = bitacora_dataops.consultar(db, 1, page=2, map_page=3)
    assert len(r['data']) == 5 and r['pagination']['total_items'] == 12
    assert len(r['normalization_matrix']) == 2 and r['matrix_pagination']['total_items'] == 12
    assert r['summary_metrics']['total_registros'] == 15
    texto = json.dumps(r)
    assert all(p not in texto for p in ('Persona Privada', '7391044', 'privado@example.com', 'SQL:', 'valor_ejemplo', 'PASS'))
    assert r['document_meta']['hash_sha256'] is None
    assert db.query(LogPipelineIngesta).count() == 13


def test_bitacora_ausente_no_usa_otro_archivo_ni_inventa_eventos(datos):
    db, _ = datos
    db.add(DimOrigenDocumental(id_documento=3, nombre_archivo='sin-logs.csv'))
    db.commit()
    r = bitacora_dataops.consultar(db, 3)
    assert r['data'] == [] and r['normalization_matrix'] == []
    assert r['summary_metrics']['total_registros'] is None
    with cliente(datos) as c:
        assert c.get('/api/v1/dataops/logs/999').status_code == 404
        assert c.get('/api/v1/dataops/logs/999/export').status_code == 404
        assert c.get('/api/v1/dataops/normalization-matrix/999').status_code == 404


def test_duracion_cero_y_conteos_desconocidos_se_respetan(datos):
    db, _ = datos
    assert bitacora_dataops.consultar(db, 1)['data'][0]['tiempo_ms'] == 0
    bloque = db.query(StagingRegistroCrudo).first()
    bloque.n_filas = None
    db.commit()
    assert bitacora_dataops.consultar(db, 1)['summary_metrics']['total_registros'] is None


def test_exportacion_incluye_todas_las_paginas_sin_mensajes_internos(datos):
    with cliente(datos) as c:
        r = c.get('/api/v1/dataops/logs/1/export')
        assert r.status_code == 200
        assert r.text.count('Validación de datos') == 11
        assert r.text.count('Regla registrada') == 12
        assert '7391044' not in r.text and 'Persona Privada' not in r.text and 'SQL:' not in r.text
        assert '185 ms' not in r.text and 'Verificada' not in r.text
        assert c.get('/api/v1/dataops/logs/1', params={'page': 0}).status_code == 422


def test_matriz_no_se_infiere_de_una_fila_personal(datos):
    db, _ = datos
    evento = db.get(LogPipelineIngesta, 1)
    evento.metadata_json = {}
    db.commit()
    assert bitacora_dataops.consultar(db, 1)['normalization_matrix'] == []
