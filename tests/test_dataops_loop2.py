import json

import pytest
from fastapi import HTTPException
from models.dim_origen import DimOrigenDocumental
from models.lote import Lote
from models.staging_registro import StagingRegistroCrudo
from routers.dataops import get_lote_raw_vs_text, get_lote_plain_text_alias
from services.texto_preparado_service import texto_publico


@pytest.fixture
def texto_lote(dw_sqlite):
    lote = Lote(institucion='Prueba', periodo='2026')
    dw_sqlite.add(lote)
    dw_sqlite.flush()
    docs = []
    for i in range(2):
        doc = DimOrigenDocumental(id_lote=lote.id_lote, nombre_archivo=f'archivo-{i}.csv', tipo_fuente='ADMISION', periodo='2026')
        dw_sqlite.add(doc)
        dw_sqlite.flush()
        docs.append(doc)
        for bloque in range(2):
            lineas = [f'Nombre Completo: Persona Prueba | PATERNO: ApellidoPrueba | ASESOR: AsesorPrivado | CI: 7391044 LP | ID ACADEMICO: 4403|7391044 | POS-CI INCRITOS: 4403-7391044 | Celular: +591 71234567 | NIT: 1029384756 | Correo: persona@example.com | Dirección: Calle Privada 123, casa 4 | Fecha de nacimiento: 01/02/1990 | Nota: {70 + n}' for n in range(4)]
            dw_sqlite.add(StagingRegistroCrudo(id_documento=doc.id_documento, texto_plano='\n'.join(lineas), n_filas=4,
                payload_json={'diagnostico_estructural': {'mini_grid': [['7391044', 'persona@example.com']], 'fila_cabecera': 2}, 'chips_catalogo': {'programa_cat': 'Programa Prueba', 'modulo_cat': 'Referencia 7391044 de Persona Prueba', 'correo': 'persona@example.com'}}))
    dw_sqlite.commit()
    return dw_sqlite, lote, docs


def leer(db, lote, page=1, doc_id=None):
    return get_lote_raw_vs_text(str(lote.id_lote), doc_id=doc_id, db=db, page=page, page_size=5)


def test_paginacion_cruza_bloques_y_documentos_sin_repetir(texto_lote):
    db, lote, docs = texto_lote
    paginas = [leer(db, lote, p) for p in range(1, 5)]
    assert [len(p['registros']) for p in paginas] == [5, 5, 5, 1]
    assert [r['line_number'] for p in paginas for r in p['registros']] == list(range(1, 17))
    assert all(p['total'] == 16 and p['total_pages'] == 4 for p in paginas)
    assert paginas[0]['registros'][4]['stg_id'] != paginas[0]['registros'][0]['stg_id']
    assert {r['id_documento'] for r in paginas[1]['registros']} == {d.id_documento for d in docs}


def test_censura_en_todos_los_campos_de_la_respuesta(texto_lote):
    db, lote, _ = texto_lote
    respuesta = json.dumps(leer(db, lote), ensure_ascii=False)
    for privado in ('7391044', '71234567', '1029384756', 'persona@example.com', 'Calle Privada', '01/02/1990', 'Persona Prueba', 'ApellidoPrueba', 'AsesorPrivado'):
        assert privado not in respuesta
    assert '••••044' in respuesta and 'Programa Prueba' in respuesta
    assert 'mini_grid' not in respuesta


def test_filtro_y_alias_respetan_la_pagina(texto_lote):
    db, lote, docs = texto_lote
    resultado = get_lote_plain_text_alias(str(lote.id_lote), doc_id=docs[1].id_documento, db=db, page=2, page_size=5)
    assert resultado['total'] == 8
    assert len(resultado['registros']) == 3
    assert {r['id_documento'] for r in resultado['registros']} == {docs[1].id_documento}


def test_archivo_de_otro_lote_no_se_puede_consultar(texto_lote):
    db, lote, _ = texto_lote
    otro = DimOrigenDocumental(nombre_archivo='otro.csv')
    db.add(otro)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        leer(db, lote, doc_id=otro.id_documento)
    assert exc.value.status_code == 404


def test_pagina_fuera_de_rango_y_archivo_sin_filas(texto_lote):
    db, lote, docs = texto_lote
    assert leer(db, lote, page=999)['registros'] == []
    db.query(StagingRegistroCrudo).filter_by(id_documento=docs[0].id_documento).delete()
    db.commit()
    resultado = leer(db, lote, doc_id=docs[0].id_documento)
    assert resultado['registros'] == [] and resultado['total'] == 0
    assert resultado['kpis']['columnas_detectadas'] is None


def test_lectura_no_inicia_beto_ni_escribe(texto_lote, monkeypatch):
    from routers import dataops
    db, lote, _ = texto_lote
    monkeypatch.setattr(dataops, '_evaluar_documentos_lote', lambda *a, **kw: pytest.fail('El paso ② no ejecuta BETO'))
    antes = db.query(StagingRegistroCrudo).count()
    leer(db, lote)
    assert db.query(StagingRegistroCrudo).count() == antes
    assert not db.dirty and not db.new and not db.deleted


@pytest.mark.parametrize('texto,privado', [
    ('CI 7391044 LP, nota 80', '7391044'),
    ('telefono_contacto: +591 71234567', '71234567'),
    ('C.I.: 7391044, Dirección: Avenida Privada', 'Avenida Privada'),
    ('correo_institucional: persona@example.com', 'persona@example.com'),
    ('Fecha de nacimiento: 01/02/1990 | Fecha: 01/03/2026', '01/02/1990'),
])
def test_variantes_de_campos_personales(texto, privado):
    assert privado not in texto_publico(texto)


def test_preserva_notas_montos_y_fechas_academicas():
    assert texto_publico('Nota: 85 | Monto: 7391044 | Fecha: 01/03/2026') == 'Nota: 85 | Monto: 7391044 | Fecha: 01/03/2026'


def test_preguntas_de_encuesta_no_son_alertas(texto_lote):
    db, lote, docs = texto_lote
    db.query(StagingRegistroCrudo).delete()
    db.add(StagingRegistroCrudo(id_documento=docs[0].id_documento,
        texto_plano='¿El docente explicó con claridad?: 5 | Nota: 85\n¿El docente explicó con claridad?: ? | Nota: 80', n_filas=2))
    db.commit()
    resultado = leer(db, lote)
    assert resultado['kpis']['total_alertas'] == 1
    assert resultado['registros'][0]['alerta'] is None
    assert resultado['registros'][1]['alerta']


def test_filas_extensas_y_muestras_no_producen_respuestas_gigantes(texto_lote):
    db, lote, docs = texto_lote
    db.query(StagingRegistroCrudo).delete()
    db.add(StagingRegistroCrudo(id_documento=docs[0].id_documento, texto_plano='Campo: ' + 'x' * 100000, n_filas=1))
    db.commit()
    resultado = leer(db, lote)
    assert resultado['registros'][0]['vista_abreviada']
    assert len(json.dumps(resultado)) < 18000


def test_api_rechaza_paginas_invalidas_y_mas_de_cinco_filas(texto_lote):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from core.database import get_db
    from core.security import get_current_user
    from models.user import User
    from routers.dataops import router
    db, lote, _ = texto_lote
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: User(id=1, username='prueba', role='ADMIN')
    cliente = TestClient(app)
    ruta = f'/api/v1/dataops/lote/{lote.id_lote}/raw-vs-text'
    for params in ({'page': 0}, {'page_size': 6}, {'page_size': 0}):
        assert cliente.get(ruta, params=params).status_code == 422
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 200
    assert len(respuesta.json()['registros']) == 5
