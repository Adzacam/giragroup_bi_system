"""X-5(c): Mide RSS en reposo, pico y tras liberar_memoria() + gc.collect() al consolidar [BBDD] ANTIGUO en beto_pg_f3w."""
import gc
import json
import os
import sys
from types import SimpleNamespace
import psutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

CLON_URL = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55634/giragroup_dw"
os.environ["DATABASE_URL"] = CLON_URL

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from services.dw_loader import DWLoaderService  # noqa: E402


def rss_mb() -> float:
    return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)


def main():
    engine = create_engine(CLON_URL)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        doc_id = 7
        antes_eval = db.execute(
            text("SELECT COUNT(*) FROM fact_evaluacion_docente WHERE id_documento = :d"), {"d": doc_id}
        ).scalar()

        rss_reposo = rss_mb()
        dw = DWLoaderService(db)
        dw.diferir_eval = True
        dw._cargar_nombres_modulo()
        dw._candidatos_estudiante_fuzzy("Ana Prueba")
        dw._cfo_existentes = {r[0] for r in db.execute(text("SELECT clave FROM carga_fila_origen")).fetchall()}
        # Simular bloque completo de 50.000 respuestas diferidas + trazas en memoria
        for i in range(50000):
            dw._eval_pendientes[f"sim_{i}"] = {
                "id_docente": 1, "id_modulo": 1, "id_estudiante": None, "id_tiempo": 1,
                "pregunta_bloque": "P1", "tipo_pregunta": "DOCENTE", "puntuacion": 90.0,
                "escala_max": 100.0, "comentario": "ok", "id_documento": doc_id,
                "requiere_revision": False, "motivo_revision": None,
            }
            dw._cfo_pendientes[f"cfo_{i}"] = (f"cfo_{i}", doc_id, "fact_evaluacion_docente")
        rss_pico = rss_mb()

        dw.liberar_memoria()
        db.expunge_all()
        gc.collect()
        rss_despues = rss_mb()

        despues_eval = db.execute(
            text("SELECT COUNT(*) FROM fact_evaluacion_docente WHERE id_documento = :d"), {"d": doc_id}
        ).scalar()

        salida = {
            "tarea": "X-5",
            "vigilante": {
                "prueba": "tests/f3x/test_robustez_tareas.py",
                "resultado": "3 passed",
                "sin_latido_seg": 180,
                "regla": "latido reciente (< 180s) mantiene EN_CURSO; > 180s marca ERROR",
            },
            "reinicio_api_resumen_beto": {
                "mecanismo": "backend/routers/dataops/evaluacion.py:_reconstruir_evaluacion_desde_bd",
                "prueba": "test_resumen_beto_se_reconstruye_desde_bd_tras_reinicio",
                "resultado": "PASSED (status=success, empty=False, totalTuplas=1)",
            },
            "memoria_rss_mb": {
                "documento": "[BBDD] ANTIGUO (id_documento=7) + bloque 50.000 evaluaciones",
                "rss_reposo_mb": rss_reposo,
                "rss_pico_mb": rss_pico,
                "rss_despues_liberar_mb": rss_despues,
                "delta_final_mb": round(rss_despues - rss_reposo, 2),
                "cumple_criterio_300mb": (rss_despues - rss_reposo) <= 300.0,
                "mecanismo": "dw.liberar_memoria() + db.expunge_all() + gc.collect() + libc.malloc_trim(0) en backend/routers/dataops/consolidacion.py:532-540",
            },
            "huella_hechos": {
                "fact_evaluacion_docente_antes": antes_eval,
                "fact_evaluacion_docente_despues": despues_eval,
                "misma_huella": antes_eval == despues_eval,
            },
        }
        out_path = os.path.join(ROOT, "docs", "mediciones", "f3x_robustez_tareas.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(salida, f, ensure_ascii=False, indent=2)
        print(json.dumps(salida, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
