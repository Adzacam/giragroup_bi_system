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
