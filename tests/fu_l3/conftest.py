"""FU-L3: las pruebas de captación reutilizan la DW SQLite en memoria y el entorno aislado de FU-L2 y hacen el recorrido
real (ingesta + consolidación), con la escala de notas que exige un libro de actas."""

from tests.fu_l2.conftest import dw_a, dw_b, entorno, nueva_dw  # noqa: F401


def cargar_libro(db, ruta, tipo_fuente="PLANIFICACION", tipo_escala="CENTESIMAL_100"):
    """Ingesta + consolidación de un libro en `db`. Devuelve (id_lote, id_documento)."""
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
