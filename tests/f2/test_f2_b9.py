"""Pruebas F2 B-9: bitácora individual de descartes e id_homonimo determinista en Estado C."""

from pathlib import Path
from unittest.mock import MagicMock

from models.log_inconsistencia import LogInconsistencia
from models.staging_entidad import StagingEntidadNoResuelta, generar_id_homonimo


def test_b9_id_homonimo_determinista_y_contextual():
    id1 = generar_id_homonimo("María López", "123456", "Maestría A")
    id2 = generar_id_homonimo("  maria   lopez ", "123456", "maestria a")
    id_otro_prog = generar_id_homonimo("María López", "123456", "Maestría B")
    id_otro_ci = generar_id_homonimo("María López", "999999", "Maestría A")

    assert id1.startswith("HOM-")
    assert len(id1) == 20
    assert id1 == id2
    assert id1 != id_otro_prog
    assert id1 != id_otro_ci


def test_b9_modelos_tienen_columnas_nuevas():
    assert hasattr(LogInconsistencia, "regla_origen")
    assert hasattr(StagingEntidadNoResuelta, "id_homonimo")


def test_b9_migracion_sin_tablas_nuevas():
    sql = Path("backend/scripts/migrations/015_b9_descartes_y_homonimos.sql").read_text(encoding="utf-8").upper()
    assert "CREATE TABLE" not in sql
    assert "ALTER TABLE LOG_INCONSISTENCIAS" in sql
    assert "ALTER TABLE STG_ENTIDAD_NO_RESUELTA" in sql


def test_b9_homonimia_en_dw_loader_mantiene_estado_c():
    from services.dw_loader import DWLoaderService

    db = MagicMock()
    loader = DWLoaderService(db)

    cand1 = MagicMock(id_estudiante=10, nombre_completo="Juan Perez", ci_numero=None)
    cand2 = MagicMock(id_estudiante=11, nombre_completo="Juan Perez", ci_numero=None)
    loader._candidatos_estudiante_fuzzy = MagicMock(return_value=[(cand1, 95.0), (cand2, 94.0)])
    loader._desempatar_homonimos = MagicMock(return_value=None)
    loader._extra_sugerencias = MagicMock(return_value={})

    est_id, estado = loader.resolver_o_crear_estudiante(
        ci="TEMP-CI-abcd1234",
        nombre="Juan Perez",
        doc_id=1,
        confianza_ia=0.92,
        programa="Diplomado X",
    )

    assert est_id is None
    assert estado == "C"
    db.add.assert_called_once()
    stg_obj = db.add.call_args[0][0]
    assert isinstance(stg_obj, StagingEntidadNoResuelta)
    assert stg_obj.fk_estado == "C"
    assert stg_obj.motivo == "HOMONIMIA"
    assert stg_obj.id_homonimo == generar_id_homonimo("Juan Perez", "TEMP-CI-abcd1234", "Diplomado X")
