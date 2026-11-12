import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from core.database import get_db
from core.security import get_current_user
from models.dim_origen import DimOrigenDocumental
from models.lote import Lote
from models.staging_entidad import StagingEntidadNoResuelta
from models.fact_rendimiento import FactRendimientoAcademico
from routers import dataops
from services import revision_consulta as revision


@pytest.fixture
def revision_db(dw_sqlite, monkeypatch):
    db = dw_sqlite
    db.add_all([Lote(id_lote=1, institucion='Prueba', periodo='2026'), Lote(id_lote=2, institucion='Otro', periodo='2026')])
    db.add_all([DimOrigenDocumental(id_documento=1, id_lote=1, nombre_archivo='acta.csv', tipo_fuente='ACTA'),
                DimOrigenDocumental(id_documento=2, id_lote=2, nombre_archivo='otro.csv', tipo_fuente='ACTA')])
    for i in range(14):
        nombre = f'Persona Prueba {i}'
        db.add(StagingEntidadNoResuelta(id_staging=i+1, id_documento=1, tipo_entidad='ESTUDIANTE',
            motivo='CI_NOMBRE_DISCORDANTE', texto_original=f'CI: {7391000+i} | Nombre: {nombre}',
            ci_temporal=str(7391000+i), mejor_candidato=nombre, score_fuzzy=0 if i == 0 else None,
            payload_json={'raw_line': f'CI: {7391000+i} | Nombres: {nombre}', 'estudiante': nombre,
                          'modulo': f'Minería {i}', 'area': 'academica'}))
    for i in range(7):
        db.add(StagingEntidadNoResuelta(id_staging=100+i, id_documento=1, tipo_entidad='ESTUDIANTE',
            texto_original=f'CI: {8401000+i} | Nombre: Resuelto {i}', motivo='REVISION_GENERAL',
            ci_temporal=str(8401000+i), resuelto=True, estado_resolucion='RESUELTO_HUMANO'))
    db.add(StagingEntidadNoResuelta(id_staging=200, id_documento=2, tipo_entidad='ESTUDIANTE', texto_original='Caso ajeno'))
    db.commit()
    monkeypatch.setattr(dataops, '_evaluar_documentos_lote', lambda *a, **kw: pytest.fail('Un GET no ejecuta BETO'))
    monkeypatch.setattr(dataops, 'extract_entities_from_line', lambda *a, **kw: pytest.fail('No se infiere al consultar'))
    return db


def cliente(db, role='ADMIN'):
    app = FastAPI()
    app.include_router(dataops.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, username='prueba', role=role, is_active=True)
    return TestClient(app)


def test_paginacion_global_y_busqueda_sin_inferencia(revision_db):
    db = revision_db
    docs = revision.documentos(db, 1)
    paginas = [revision.consultar(db, docs, page=p) for p in (1, 2, 3)]
    assert [len(p['items']) for p in paginas] == [5, 5, 4]
    assert all(p['total'] == 14 for p in paginas)
    assert paginas[0]['items'][0]['indice_registro'] == 0
    assert paginas[0]['items'][1]['indice_registro'] is None
    assert revision.consultar(db, docs, search='mineria 13')['items'][0]['id'] == 14
    assert db.query(StagingEntidadNoResuelta).filter_by(resuelto=False).count() == 15


def test_resueltos_tambien_paginados_y_protegidos(revision_db):
    docs = revision.documentos(revision_db, 1)
    r = revision.consultar(revision_db, docs, vista='RESUELTOS', page=2)
    assert r['total'] == 7 and len(r['items']) == 2
    assert '8401005' not in json.dumps(r)


def test_grupos_cinco_opacos_y_detalle_acotado(revision_db):
    docs = revision.documentos(revision_db, 1)
    r = revision.grupos_publicos(revision_db, docs, page=2)
    assert r['total_grupos'] == 14 and len(r['grupos']) == 5
    assert all(g['clave'].startswith('grupo-') for g in r['grupos'])
    assert '7391005' not in json.dumps(r)
    detalle = revision.consultar(revision_db, docs, grupo=r['grupos'][0]['clave'])
    assert detalle['total'] == 1
    assert '7391005' not in json.dumps(detalle)
    assert 'CI: 123' not in revision.proteger_ci('CI: 123 | Nombre: Persona')


def test_documento_ajeno_o_lote_inexistente_no_amplia_alcance(revision_db):
    for lote, doc in ((1, 2), (999, None)):
        with pytest.raises(HTTPException) as exc:
            revision.documentos(revision_db, lote, doc)
        assert exc.value.status_code == 404


def test_limites_http_roles_y_exportacion_completa(revision_db):
    with cliente(revision_db) as c:
        base = '/api/v1/dataops/review-tray'
        assert c.get(base, params={'id_lote': 1, 'page_size': 6}).status_code == 422
        assert c.get(base, params={'id_lote': 1, 'page': 0}).status_code == 422
        assert len(c.get(base, params={'id_lote': 1}).json()['items']) == 5
        exported = c.get(base + '/export', params={'id_lote': 1})
        assert exported.status_code == 200
        assert len(exported.text.splitlines()) == 15
        assert '7391000' not in exported.text and '7391013' not in exported.text
        assert 'Persona Prueba 13' in exported.text
    with cliente(revision_db, 'DIRECTOR') as c:
        assert c.get(base + '/export', params={'id_lote': 1}).status_code == 403


def test_presupuesto_permanece_manual_y_no_se_aprueba_en_bloque(revision_db, monkeypatch):
    ent = revision_db.get(StagingEntidadNoResuelta, 1)
    ent.payload_json = {**ent.payload_json, 'raw_line': 'Presupuesto | CI: 7391000 | Nombre: Persona Prueba 0'}
    revision_db.commit()
    assert revision.consultar(revision_db, revision.documentos(revision_db, 1))['items'][0]['manual_presupuesto']
    with pytest.raises(HTTPException) as exc:
        dataops.resolve_review_item('1', {'accion': 'APROBAR'}, db=revision_db, current_user=None)
    assert exc.value.status_code == 422
    llamados = []
    monkeypatch.setattr(dataops, 'resolve_review_item', lambda item_id, *a, **kw: llamados.append(item_id) or {'status': 'success'})
    dataops.aprobar_casos_un_clic(dataops.AprobacionEnBloqueRequest(id_lote='1', confirmar=True), db=revision_db, current_user=None)
    assert '1' not in llamados and len(llamados) == 13
    doc = revision_db.get(DimOrigenDocumental, 1)
    assert not revision.presupuesto_manual(doc, 'NOMBRE DEL PROGRAMA: Diplomado en Presupuesto Público | NOMBRES: Persona Prueba')


def test_fallo_de_guardado_no_resuelve_el_caso(revision_db, monkeypatch):
    def fallar(*a, **kw):
        raise RuntimeError('No se pudo insertar')
    monkeypatch.setattr(dataops.DWLoaderService, 'cargar_registro', fallar)
    with pytest.raises(HTTPException) as exc:
        dataops.resolve_review_item('1', {'accion': 'APROBAR', 'estudiante_resuelto': 'Persona Prueba'}, db=revision_db, current_user=None)
    assert exc.value.status_code == 503
    assert revision_db.get(StagingEntidadNoResuelta, 1).resuelto is False


def test_lote_cerrado_rechaza_escrituras_y_permanece_consultable(revision_db):
    db = revision_db
    db.add(Lote(id_lote=3, institucion='Cerrado', periodo='2026'))
    db.add(DimOrigenDocumental(id_documento=3, id_lote=3, nombre_archivo='cerrado.csv', tipo_fuente='ACTA'))
    db.add(FactRendimientoAcademico(id_hecho_aca=10, id_documento=3, requiere_revision=False))
    db.commit()
    with pytest.raises(HTTPException) as exc:
        dataops.resolve_review_item('HECHO-ACA-10', {'accion': 'DESCARTAR'}, db=db, current_user=None)
    assert exc.value.status_code == 409
    assert db.get(FactRendimientoAcademico, 10) is not None
    assert revision.consultar(db, revision.documentos(db, 3))['total'] == 0


def test_consolidacion_reserva_una_sola_tarea(revision_db, monkeypatch):
    estado = {}
    inicios = []
    monkeypatch.setattr(dataops.tareas_dataops, 'ultima_en_sesion', lambda db, lote, tipo: estado.get(tipo))
    def reservar(*a):
        estado['CONSOLIDACION'] = {'id': 99, 'estado': 'EN_CURSO'}
        return 99
    monkeypatch.setattr(dataops.tareas_dataops, 'crear_en_sesion', reservar)
    monkeypatch.setattr(dataops.tareas_dataops, 'obtener', lambda *a: estado['CONSOLIDACION'])
    monkeypatch.setattr(dataops.threading, 'Thread', lambda **kw: SimpleNamespace(start=lambda: inicios.append(kw)))
    usuario = SimpleNamespace(id=1, username='Prueba')
    payload = dataops.ConfirmDwInsertRequest(id_lote=1, en_segundo_plano=True)
    a = dataops.confirm_dw_insert(payload, db=revision_db, current_user=usuario)
    b = dataops.confirm_dw_insert(payload, db=revision_db, current_user=usuario)
    assert a['tarea_id'] == b['tarea_id'] == 99 and len(inicios) == 1


@pytest.mark.parametrize('payload', [{'nota_final': 101}, {'nota_final': float('nan')}, {'cuotas_impagas': -1}, {'gestion': 1999}])
def test_correcciones_invalidas_no_escriben(revision_db, payload):
    with pytest.raises(HTTPException) as exc:
        dataops.resolve_review_item('1', payload, db=revision_db, current_user=None)
    assert exc.value.status_code == 422
    assert not revision_db.get(StagingEntidadNoResuelta, 1).resuelto


def test_respuesta_sin_incorporacion_no_anuncia_aprobacion(revision_db, monkeypatch):
    monkeypatch.setattr(dataops.DWLoaderService, 'cargar_registro', lambda *a, **kw: {'status': 'staged'})
    with pytest.raises(HTTPException) as exc:
        dataops.resolve_review_item('1', {'accion': 'APROBAR'}, db=revision_db, current_user=None)
    assert exc.value.status_code == 503
    assert not revision_db.get(StagingEntidadNoResuelta, 1).resuelto


def test_avisos_por_rol_sin_datos_personales(revision_db, monkeypatch):
    from models.notification import Notification
    monkeypatch.setattr(dataops.DWLoaderService, 'cargar_registro', lambda *a, **kw: {'status': 'loaded'})
    dataops.resolve_review_item('1', {'accion': 'APROBAR', 'estudiante_resuelto': 'Persona Prueba 0'}, db=revision_db, current_user=None)
    avisos = revision_db.query(Notification).all()
    assert {n.role_target for n in avisos} == {'ADMIN', 'AUDITOR_CALIDAD'}
    assert len(avisos) == 2
    assert all('Persona Prueba' not in n.message and '7391000' not in n.message for n in avisos)


def test_csv_filtra_todo_el_conjunto_y_evitar_formulas(revision_db):
    e = revision_db.get(StagingEntidadNoResuelta, 14)
    e.payload_json = {**e.payload_json, 'estudiante': '=1+2', 'modulo': 'Minería 13'}
    revision_db.commit()
    with cliente(revision_db) as c:
        r = c.get('/api/v1/dataops/review-tray/export', params={'id_lote': 1, 'search': 'mineria 13'})
    assert len(r.text.splitlines()) == 2
    assert "'=1+2" in r.text and '7391013' not in r.text


def test_correos_y_programas_no_se_presentan_como_nombres(revision_db):
    ent = revision_db.get(StagingEntidadNoResuelta, 1)
    ent.payload_json = {'estudiante': 'DIPLOMADO EN FINANZAS'}
    doc = revision_db.get(DimOrigenDocumental, 1)
    assert revision.caso_guardado(ent, doc)['estudiante'] is None
    ent.payload_json = {'estudiante': 'privado@example.com'}
    assert revision.caso_guardado(ent, doc)['estudiante'] is None


def test_busqueda_por_la_definicion_visible_del_motivo(revision_db):
    ent = revision_db.get(StagingEntidadNoResuelta, 1)
    ent.motivo = 'POS_NO_EN_DIM_MODULO'
    revision_db.commit()
    r = revision.consultar(revision_db, revision.documentos(revision_db, 1), search='programa sin coincidencia')
    assert r['total'] == 1 and r['items'][0]['id'] == 1


def test_grupo_de_hechos_abre_solo_sus_casos_y_exporta(revision_db):
    db = revision_db
    db.add_all([FactRendimientoAcademico(id_hecho_aca=i, id_documento=1, requiere_revision=True) for i in (30, 31)])
    db.commit()
    docs = revision.documentos(db, 1)
    grupo = next(g for g in revision.grupos_publicos(db, docs)['grupos'] if g['motivo'] == 'HECHO_EN_REVISION')
    r = revision.consultar(db, docs, grupo=grupo['clave'])
    assert {it['id'] for it in r['items']} == {'HECHO-ACA-30', 'HECHO-ACA-31'}
    with cliente(db) as c:
        exportado = c.get('/api/v1/dataops/review-tray/export', params={'id_lote': 1, 'grupo': grupo['clave']})
    assert len(exportado.text.splitlines()) == 3


def test_hecho_incompleto_sigue_pendiente(revision_db):
    db = revision_db
    db.add(FactRendimientoAcademico(id_hecho_aca=30, id_documento=1, requiere_revision=True))
    db.commit()
    with pytest.raises(HTTPException) as exc:
        dataops.resolve_review_item('HECHO-ACA-30', {'accion': 'APROBAR'}, db=db, current_user=None)
    assert exc.value.status_code == 422
    assert db.get(FactRendimientoAcademico, 30).requiere_revision
