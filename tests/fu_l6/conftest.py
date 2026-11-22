"""
FU-L6: utilidades comunes de las pruebas de metas (SQLite en memoria, libros sintéticos con datos ficticios).

Reutiliza el entorno aislado de FU-L2 (caché de lectura en un directorio temporal, BETO parcheado) y el recorrido real:
ingesta (`IngestionService.procesar_archivo`) y consolidación (`routers.dataops._consolidar`).
"""

import pytest
from sqlalchemy import text

from tests.fu_l2.conftest import cargar_libro, dw_a, dw_b, entorno, nueva_dw  # noqa: F401


def filas_rentabilidad(db):
    """{(categoría, año, mes): (ejecutado, meta, granularidad)} de fact_rentabilidad."""
    filas = db.execute(text(
        "SELECT dc.nombre_categoria, dt.gestion, dt.mes, fr.monto_ejecutado, fr.monto_meta, fr.granularidad_meta "
        "FROM fact_rentabilidad fr JOIN dim_tiempo dt ON dt.id_tiempo = fr.id_tiempo "
        "JOIN dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria")).fetchall()
    return {(c, int(g), int(m)): (None if e is None else float(e), None if mt is None else float(mt), gr) for c, g, m, e, mt, gr in filas}


def conflictos(db, estado=None):
    """Registros CONFLICTO_FUENTES del log (opcionalmente de un estado)."""
    from models.log_inconsistencia import LogInconsistencia
    q = db.query(LogInconsistencia).filter(LogInconsistencia.tipo_regla == "CONFLICTO_FUENTES")
    if estado:
        q = q.filter(LogInconsistencia.estado_resolucion == estado)
    return q.all()


def conflictos_resueltos(db):
    """{(campo, categoría, mes): (elegida, descartada, elegido, descartado, múltiplo)} de los conflictos resueltos por regla, leídos del texto."""
    from services import metas_canonica
    from models.dim_tiempo import DimTiempo
    res = {}
    for log in conflictos(db, "RESUELTO_REGLA"):
        d = metas_canonica.leer_conflicto(log.descripcion)
        assert d is not None, log.descripcion
        mes = db.query(DimTiempo.mes).filter(DimTiempo.id_tiempo == int(d["id_tiempo"])).scalar()
        res[(d["campo"], d["categoria"], int(mes))] = (d["elegida"], d["descartada"], float(d["elegido"]), float(d["descartado"]),
                                                        d["multiplo_100000"])
    return res
