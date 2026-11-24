"""ADW L7: pipeline y BETO.

C1  las tareas «del lote 1» en ERROR eran contaminación de pytest sobre la DW (el seguimiento de tareas usa su propia sesión).
B5  la caché de entidades de BETO se crea en el primer uso. a3 sigue activo y el rescate académico requiere un flag.
C3  cada fila de origen deja dos claves de idempotencia (posición y contenido).
"""
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

TMPFS_URL = os.environ.get("ADW_DB_URL", "")
requiere_tmpfs = pytest.mark.skipif("55433" not in TMPFS_URL, reason="Requiere ADW_DB_URL apuntando a la copia tmpfs (puerto 55433)")


# ── C1 ────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_pruebas_que_suben_o_leen_lotes_aislan_el_seguimiento_de_tareas():
    """Una prueba que llama a upload_batch / iniciar_lectura_lote / _evaluar_lote_en_segundo_plano debe parchear
    tareas_dataops; si no, deja tareas INGESTA y LECTURA_BETO del «lote 1» en la base real."""
    llamadas = re.compile(r"\b(upload_batch|iniciar_lectura_lote|_evaluar_lote_en_segundo_plano)\s*\(")
    sin_aislar = []
    for f in (ROOT / "tests").rglob("test_*.py"):
        if f.name == Path(__file__).name:
            continue
        src = f.read_text(encoding="utf-8", errors="ignore")
        if llamadas.search(src) and "tareas_dataops" not in src:
            sin_aislar.append(str(f.relative_to(ROOT)))
    assert not sin_aislar, f"Pruebas que pueden escribir tareas en la DW sin aislarlas: {sin_aislar}"


@requiere_tmpfs
def test_la_prueba_de_upload_batch_no_deja_tareas_en_la_base():
    """Ejecuta la prueba contra la copia tmpfs y comprueba que dataops_tarea no cambia (antes dejaba +2 filas)."""
    engine = create_engine(TMPFS_URL)

    def n():
        with engine.connect() as c:
            return c.execute(text("SELECT count(*), coalesce(max(id), 0) FROM public.dataops_tarea")).one()

    antes = n()
    env = {**os.environ, "DATABASE_URL": TMPFS_URL}
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/sprint5/test_ingesta_sin_timeout.py::test_upload_batch_no_evalua_antes_de_responder",
         "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=240)
    assert "1 passed" in r.stdout, r.stdout[-400:]
    assert tuple(n()) == tuple(antes), "la prueba escribió tareas en la base"


# ── B5 ────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_cache_beto_no_es_migracion_y_los_flags_a3_activos(monkeypatch):
    from core.migraciones import MIGRACIONES_EN_ARRANQUE
    from pipeline import config as cfg
    from services import beto_integracion

    assert not any("cache_beto" in m or m.startswith("015") for m in MIGRACIONES_EN_ARRANQUE)
    assert "CREATE TABLE IF NOT EXISTS public.cache_beto_entidades" in beto_integracion.DDL_CACHE
    assert cfg.BETO_FLAGS_POR_DEFECTO == {
        "BETO_CASCADA_FINAL": True,
        "BETO_ACUERDO_QC": True,
        "BETO_SUGERENCIA_HITL": True,
        "BETO_RESCATE_ACADEMICO": True,
        "BETO_VENTANA": False,
    }
    monkeypatch.delenv("BETO_RESCATE_ACADEMICO", raising=False)
    assert beto_integracion.activo("BETO_RESCATE_ACADEMICO")
    monkeypatch.setenv("BETO_RESCATE_ACADEMICO", "0")
    assert not beto_integracion.activo("BETO_RESCATE_ACADEMICO")
    assert "migración 015" not in (beto_integracion.__doc__ or "").replace("No existe una «migración 015»", "")


def test_la_segunda_lectura_de_los_mismos_textos_sale_de_la_cache():
    from services.beto_integracion import CacheMemoria, ClienteBeto, EntidadBeto

    llamadas = []

    def post(lote):
        llamadas.append(list(lote))
        return [[EntidadBeto("ESTUDIANTE", t, 0, len(t), 0.9)] for t in lote]

    cli = ClienteBeto(cache=CacheMemoria(), post=post, configuracion="prueba")
    textos = ["Ana Pérez 123", "Luis Gómez 456"]
    primera = cli.entidades(textos)
    segunda = cli.entidades(textos)
    assert len(llamadas) == 1, "el segundo pase volvió a inferir"
    assert cli.contadores.textos_inferidos == 2 and cli.contadores.textos_en_cache == 2
    assert [e[0].texto if hasattr(e[0], "texto") else e[0].a_dict() for e in primera.values()] == \
           [e[0].texto if hasattr(e[0], "texto") else e[0].a_dict() for e in segunda.values()]


# ── C3 ────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_cada_fila_de_origen_registra_dos_claves():
    """La clave por posición y la clave por contenido: por eso `claves / 2` son las filas reclamadas."""
    from services.dw_loader import DWLoaderService

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as c:
        c.execute(text("CREATE TABLE carga_fila_origen (clave VARCHAR(64) PRIMARY KEY, id_documento INTEGER, tabla VARCHAR(40), creado_en TIMESTAMP)"))
    db = sessionmaker(bind=engine)()
    falso = SimpleNamespace(db=db, diferir_eval=False, _cfo_existentes=None, _cfo_pendientes={})

    assert DWLoaderService._reclamar_fila_origen(falso, "A" * 64, 7, "fact_x", "B" * 64) is True
    assert db.execute(text("SELECT count(*) FROM carga_fila_origen")).scalar() == 2
    # la misma fila (misma posición) y un re-export con otra posición pero el mismo contenido no vuelven a sumar
    assert DWLoaderService._reclamar_fila_origen(falso, "A" * 64, 7, "fact_x", "B" * 64) is False
    assert DWLoaderService._reclamar_fila_origen(falso, "C" * 64, 7, "fact_x", "B" * 64) is False
    db.close()
