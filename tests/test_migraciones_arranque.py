"""
tests/test_migraciones_arranque.py
----------------------------------
El arranque de la API reaplica migraciones idempotentes. La última que define chk_dim_origen_tipo_fuente
debe admitir los tipos que el ingestor detecta (RENTABILIDAD para EJECUTADO VS META, MARKETING...):
antes solo se reaplicaba la 003 (4 tipos) y cada reinicio rechazaba esos libros en upload-batch.
"""

import re
from pathlib import Path

from main import MIGRACIONES_EN_ARRANQUE

DIR_MIGRACIONES = Path(__file__).resolve().parent.parent / "backend" / "scripts" / "migrations"
RE_CHECK = re.compile(r"ADD CONSTRAINT chk_dim_origen_tipo_fuente\s+CHECK \((.*?)\);", re.S)


def _tipos_permitidos_tras_arranque():
    tipos = None
    for nombre in MIGRACIONES_EN_ARRANQUE:
        m = RE_CHECK.search((DIR_MIGRACIONES / nombre).read_text(encoding="utf-8"))
        if m:
            tipos = set(re.findall(r"'([A-Z_]+)'", m.group(1)))
    return tipos


def test_migraciones_de_arranque_existen_en_orden():
    assert all((DIR_MIGRACIONES / n).exists() for n in MIGRACIONES_EN_ARRANQUE)
    assert list(MIGRACIONES_EN_ARRANQUE) == sorted(MIGRACIONES_EN_ARRANQUE)


def test_restriccion_final_admite_los_tipos_que_detecta_el_ingestor():
    tipos = _tipos_permitidos_tras_arranque()
    assert {"ACTA", "COBRANZA", "ADMISION", "MOODLE"} <= tipos
    assert {"RENTABILIDAD", "MARKETING", "EGRESOS", "TECHOS", "EVALUACION_DOCENTE", "PLANIFICACION"} <= tipos


def test_con_004_aplicada_no_se_reaplica_003():
    """Reaplicar 003 con documentos RENTABILIDAD fallaba en cada arranque (CheckViolation) y abortaba la 004."""
    from main import MIGRACION_TIPO_FUENTE, migraciones_a_aplicar
    alineacion = "005_alinear_esquema_con_ddl.sql"
    cmi = "006_capa_semantica_cmi.sql"
    pbi = "007_powerbi_informe_version.sql"
    assert migraciones_a_aplicar({MIGRACION_TIPO_FUENTE}) == [alineacion, cmi, pbi]
    assert migraciones_a_aplicar({"001_initial_constellation_baseline.sql", MIGRACION_TIPO_FUENTE}) == [alineacion, cmi, pbi]
    assert migraciones_a_aplicar({MIGRACION_TIPO_FUENTE, alineacion, cmi, pbi}) == []


def test_capa_cmi_no_pisa_la_configuracion_editada():
    """Se reaplica en cada arranque si falta su registro: las semillas no deben sobrescribir metas editadas."""
    sql = (DIR_MIGRACIONES / "006_capa_semantica_cmi.sql").read_text(encoding="utf-8")
    assert "ON CONFLICT (codigo) DO UPDATE" not in sql
    assert sql.count("ON CONFLICT (codigo) DO NOTHING") == 2
    assert "INSERT INTO public.schema_migrations" in sql


def test_base_nueva_aplica_003_y_luego_004():
    from main import migraciones_a_aplicar
    assert migraciones_a_aplicar(set()) == list(MIGRACIONES_EN_ARRANQUE)


def test_arranque_serializa_los_workers_con_advisory_lock():
    import inspect
    import main
    fuente = inspect.getsource(main.on_startup)
    assert "pg_advisory_lock" in fuente and "pg_advisory_unlock" in fuente
    assert fuente.index("pg_advisory_lock") < fuente.index("migraciones_a_aplicar")
