"""Un archivo re-exportado (otra huella, mismo contenido) no vuelve a sumar inscripciones en fact_marketing."""
from sqlalchemy import text

from models.fact_marketing import FactMarketing
from services.clave_fila import ContadorOcurrencias, clave_contenido
from services.dw_loader import DWLoaderService
from tests.sprint5.test_dataops_integridad import registro


def _loader(db):
    db.execute(text('CREATE TABLE carga_fila_origen (clave TEXT PRIMARY KEY, id_documento INTEGER, tabla TEXT)'))
    return DWLoaderService(db)


def _inscritos(db):
    return sum(f.inscritos or 0 for f in db.query(FactMarketing).all())


def test_reexportacion_con_otra_huella_no_suma_dos_veces(dw_sqlite):
    loader = _loader(dw_sqlite)
    contenido = clave_contenido('ADMISION', 'TBL_INSCRITOS', 'CI: 1234567 | PROGRAMA: X', 0)
    primera = {**registro(leads=40, inscritos=10), 'clave_origen': 'huella-A|hoja|2|fila', 'clave_contenido': contenido}
    segunda = {**registro(leads=40, inscritos=10), 'clave_origen': 'huella-B|hoja|2|fila', 'clave_contenido': contenido}
    assert loader.cargar_registro(primera)['status'] == 'loaded'
    assert loader.cargar_registro(segunda)['status'] == 'skipped'
    assert _inscritos(dw_sqlite) == 10


def test_filas_realmente_iguales_de_un_mismo_archivo_siguen_contando_dos_veces(dw_sqlite):
    loader = _loader(dw_sqlite)
    ocurrencias = ContadorOcurrencias()
    linea = 'CI: 1234567 | PROGRAMA: X'
    for posicion in (2, 3):
        fila = {**registro(leads=5, inscritos=5), 'clave_origen': f'huella-A|hoja|{posicion}|{linea}',
                'clave_contenido': clave_contenido('ADMISION', 'hoja', linea, ocurrencias.siguiente('hoja', linea))}
        assert loader.cargar_registro(fila)['status'] == 'loaded'
    assert _inscritos(dw_sqlite) == 10


def test_la_clave_por_archivo_sigue_protegiendo_sin_clave_de_contenido(dw_sqlite):
    loader = _loader(dw_sqlite)
    fila = {**registro(leads=40, inscritos=10), 'clave_origen': 'huella-A|hoja|2|fila'}
    assert loader.cargar_registro(fila)['status'] == 'loaded'
    assert loader.cargar_registro(fila)['status'] == 'skipped'
    assert _inscritos(dw_sqlite) == 10


def test_contenido_distinto_si_cambia_la_fuente_la_hoja_o_la_ocurrencia():
    base = clave_contenido('ADMISION', 'h1', 'fila', 0)
    assert len({base, clave_contenido('COBRANZA', 'h1', 'fila', 0), clave_contenido('ADMISION', 'h2', 'fila', 0),
                clave_contenido('ADMISION', 'h1', 'fila', 1), clave_contenido('ADMISION', 'h1', 'otra', 0)}) == 5
