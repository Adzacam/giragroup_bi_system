"""F3S S-3 (D-A8a): las filas de metas (EJECUTADO VS META) que la regla de rentabilidad ya resuelve no llegan a BETO."""
import pandas as pd

from models.dim_origen import DimOrigenDocumental
from models.fact_rentabilidad import FactRentabilidad
from models.lote import Lote
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from routers import dataops
from services import cache_consultas
from services.extraccion_por_encabezado import campos_por_encabezado, fila_resuelta_por_regla
from tests.dataops_parches import parchear

FILAS = [("PROGRAMAS", "JUNIO", 6), ("TECHOS/CERRADOS", "FEBRERO", 2),
         ("TECHOS/CERRADOS", "ABRIL", 4), ("TECHOS/CERRADOS", "OCTUBRE", 10)]


def _df():
    return pd.DataFrame([{"CATEGORIA": c, "MES": m, "MES NUMERICO": n, "EJECUTADO 2024": 1000.0 + n,
                          "META POR CATEGORIA 2024": 900.0 + n} for c, m, n in FILAS])


def test_la_regla_de_rentabilidad_resuelve_las_4_filas():
    for c, m, n in FILAS:
        campos = campos_por_encabezado(["CATEGORIA: " + c, "MES: " + m, f"MES NUMERICO: {n}", "EJECUTADO 2024: 1000"])
        assert fila_resuelta_por_regla(campos, "rentabilidad")
        assert not fila_resuelta_por_regla(campos, "academico")


def test_las_filas_de_metas_no_llegan_a_beto_ni_a_staging(dw_sqlite, monkeypatch, tmp_path):
    from services import cache_lectura, ingestion_service
    from services.ingestion_service import IngestionService

    db = dw_sqlite
    cache_consultas.invalidar()
    monkeypatch.setattr(cache_lectura, "DIR", tmp_path)
    monkeypatch.setattr(ingestion_service, "AsymmetricFlattener", None)
    enviadas = []

    def beto_bajo(lineas, **kw):
        enviadas.extend(lineas)
        return [0.10] * len(lineas)   # BETO lee estas filas como ESTUDIANTE de baja confianza: antes caían a staging

    parchear(monkeypatch, "obtener_indices", beto_bajo)
    monkeypatch.setattr("services.confianza_service.indices_en_cache", lambda lineas: [None] * len(lineas))  # sin DB real
    lote = Lote(institucion="Prueba", periodo="2024")
    db.add(lote); db.flush()
    archivo = tmp_path / "EJECUTADO VS META.xlsx"
    with pd.ExcelWriter(archivo) as w:
        _df().to_excel(w, sheet_name="EJECUTADO", index=False)
    IngestionService.procesar_archivo(db, str(archivo), archivo.name, id_lote=lote.id_lote, tipo_fuente="RENTABILIDAD",
                                      institucion="Prueba", tipo_escala="CENTESIMAL_100")
    doc = db.query(DimOrigenDocumental).filter_by(id_lote=lote.id_lote).one()
    doc.tipo_fuente = "RENTABILIDAD"
    db.commit()
    assert db.query(StagingRegistroCrudo).filter_by(id_documento=doc.id_documento).count() >= 1

    dataops._consolidar(dataops.ConfirmDwInsertRequest(id_lote=lote.id_lote), db, None)

    assert not enviadas, f"BETO recibió filas que una regla ya resolvió: {enviadas}"
    assert db.query(StagingEntidadNoResuelta).filter_by(tipo_entidad="ESTUDIANTE").count() == 0
    assert db.query(FactRentabilidad).count() == 4   # un hecho por fila (categoría + mes) con 2024
    cache_consultas.invalidar()
