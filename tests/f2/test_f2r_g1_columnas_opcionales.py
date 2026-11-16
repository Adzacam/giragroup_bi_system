"""F2R G-1 (H-2): la carga funciona con y sin las columnas de la migración 016 (id_homonimo, regla_origen)."""

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core import esquema_opcional
from core.esquema_opcional import valores_si_existen
from models.staging_entidad import StagingEntidadNoResuelta, generar_id_homonimo

AMBAS = frozenset({("stg_entidad_no_resuelta", "id_homonimo"), ("log_inconsistencias", "regla_origen")})


@pytest.fixture(autouse=True)
def _limpiar_cache():
    esquema_opcional._presentes.cache_clear()
    yield
    esquema_opcional._presentes.cache_clear()


def _db_con_columnas(columnas):
    """Session simulada cuyo engine responde a information_schema con `columnas`."""
    con = MagicMock()
    con.execute.return_value.fetchall.return_value = list(columnas)
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = con
    db = MagicMock()
    db.get_bind.return_value = engine
    return db, con


def test_con_columnas_conserva_los_valores():
    db, _ = _db_con_columnas(AMBAS)
    assert valores_si_existen(db, "stg_entidad_no_resuelta", id_homonimo="HOM-1") == {"id_homonimo": "HOM-1"}
    assert valores_si_existen(db, "log_inconsistencias", regla_origen="X") == {"regla_origen": "X"}


def test_sin_columnas_omite_valores_y_avisa_una_vez(caplog):
    db, con = _db_con_columnas([])
    with caplog.at_level(logging.WARNING, logger="esquema_opcional"):
        assert valores_si_existen(db, "stg_entidad_no_resuelta", id_homonimo="HOM-1") == {}
        assert valores_si_existen(db, "log_inconsistencias", regla_origen="X") == {}
    avisos = [r for r in caplog.records if "016" in r.getMessage()]
    assert len(avisos) == 1
    assert "stg_entidad_no_resuelta.id_homonimo" in avisos[0].getMessage()
    assert con.execute.call_count == 1  # detección única, cacheada


def test_solo_una_de_las_columnas():
    db, _ = _db_con_columnas([("log_inconsistencias", "regla_origen")])
    assert valores_si_existen(db, "stg_entidad_no_resuelta", id_homonimo="HOM-1") == {}
    assert valores_si_existen(db, "log_inconsistencias", regla_origen="X") == {"regla_origen": "X"}


def _homonimia(monkeypatch, presentes):
    from services.dw_loader import DWLoaderService

    monkeypatch.setattr(esquema_opcional, "_presentes", lambda engine: presentes)
    db = MagicMock()
    loader = DWLoaderService(db)
    cand = [(MagicMock(id_estudiante=i, nombre_completo="Juan Perez", ci_numero=None), 95.0) for i in (10, 11)]
    loader._candidatos_estudiante_fuzzy = MagicMock(return_value=cand)
    loader._desempatar_homonimos = MagicMock(return_value=None)
    loader._extra_sugerencias = MagicMock(return_value={})
    est_id, estado = loader.resolver_o_crear_estudiante(
        ci="TEMP-CI-abcd1234", nombre="Juan Perez", doc_id=1, confianza_ia=0.92, programa="Diplomado X")
    assert (est_id, estado) == (None, "C")
    return db.add.call_args[0][0]


def test_loader_con_columnas_asigna_id_homonimo(monkeypatch):
    stg = _homonimia(monkeypatch, AMBAS)
    assert isinstance(stg, StagingEntidadNoResuelta)
    assert stg.id_homonimo == generar_id_homonimo("Juan Perez", "TEMP-CI-abcd1234", "Diplomado X")


def test_loader_sin_columnas_carga_sin_id_homonimo(monkeypatch):
    stg = _homonimia(monkeypatch, frozenset())
    assert stg.fk_estado == "C" and stg.motivo == "HOMONIMIA"
    assert stg.id_homonimo is None


def test_columnas_b9_son_deferred_en_los_modelos():
    from models.log_inconsistencia import LogInconsistencia

    for col in (StagingEntidadNoResuelta.id_homonimo, LogInconsistencia.regla_origen):
        assert col.property.deferred


def test_migracion_016_existe_y_015_b9_no():
    base = Path("backend/scripts/migrations")
    assert (base / "016_b9_descartes_y_homonimos.sql").exists()
    assert not (base / "015_b9_descartes_y_homonimos.sql").exists()
