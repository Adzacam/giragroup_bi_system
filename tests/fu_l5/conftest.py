"""FU-L5: reutiliza la DW SQLite en memoria y el entorno aislado de FU-L2 a FU-L4 (recorrido real: ingesta + consolidación)."""

import pytest

from tests.fu_l2.conftest import dw_a, dw_b, nueva_dw  # noqa: F401
from tests.fu_l2.conftest import entorno as entorno_base


def _execute_values_sqlite(cur, sql, filas, template=None, page_size=100, fetch=False):
    """`psycopg2.extras.execute_values` para SQLite: la carga de evaluación escribe sus respuestas diferidas en bloque (PostgreSQL);
    aquí se expande `VALUES %s` a marcas de SQLite para que el recorrido real termine en la tabla."""
    if not filas:
        return None
    marcas = "(" + ",".join("?" * len(filas[0])) + ")"
    cur.execute(sql.replace("VALUES %s", "VALUES " + ",".join([marcas] * len(filas))), [v for f in filas for v in f])
    return None


@pytest.fixture
def entorno(entorno_base, monkeypatch):
    """El entorno de FU-L2 (caché aislado, sin aplanador asimétrico, BETO parcheado) con la escritura en bloque de SQLite."""
    monkeypatch.setattr("psycopg2.extras.execute_values", _execute_values_sqlite)
    return entorno_base


def cargar_encuesta(db, ruta, tipo_fuente="ACTA", tipo_escala="CENTESIMAL_100"):
    """Ingesta + consolidación de un libro de encuestas en `db`. El tipo sugerido es deliberadamente el equivocado (ACTA, como el
    selector de la SPA): el sistema debe corregirlo por contenido. Devuelve (id_lote, id_documento)."""
    from routers import dataops
    from models.lote import Lote
    from services import ingestion_service

    lote = Lote(institucion="Prueba", periodo="2027")
    db.add(lote)
    db.commit()
    res = ingestion_service.IngestionService.procesar_archivo(
        db, str(ruta), ruta.name, id_lote=lote.id_lote, institucion="Prueba", tipo_fuente=tipo_fuente, tipo_escala=tipo_escala)
    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)
    db.commit()
    return lote.id_lote, res["id_documento"]
