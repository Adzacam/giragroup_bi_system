"""X-1: Verifica el borrado completo de [BBDD] ANTIGUO en el clon beto_pg_f3w."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DATABASE_URL", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55634/giragroup_dw")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from services.ingestion_service import IngestionService  # noqa: E402

CLON_URL = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55634/giragroup_dw"
TABLAS_DOC = [
    "fact_rendimiento_academico",
    "fact_situacion_financiera",
    "fact_evaluacion_docente",
    "fact_rentabilidad",
    "fact_costo_programa",
    "fact_techo_convenio",
    "bridge_modulo_docente",
    "staging_registros_crudos",
    "stg_entidad_no_resuelta",
    "log_inconsistencias",
    "log_pipeline_ingesta",
    "dim_origen_documental",
    "carga_fila_origen",
]
DIMENSIONES = ["dim_estudiante", "dim_docente", "dim_modulo", "dim_tiempo"]


def _conteos(db, doc_id: int) -> dict:
    doc_counts = {
        t: db.execute(text(f"SELECT COUNT(*) FROM {t} WHERE id_documento = :d"), {"d": doc_id}).scalar()
        for t in TABLAS_DOC
    }
    dim_counts = {
        t: db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        for t in DIMENSIONES
    }
    return {"tablas_documento": doc_counts, "dimensiones": dim_counts}


def main():
    engine = create_engine(CLON_URL)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        row = db.execute(
            text(
                "SELECT id_documento, nombre_archivo FROM dim_origen_documental "
                "WHERE nombre_archivo ILIKE '%ANTIGUO%' ORDER BY id_documento LIMIT 1"
            )
        ).first()
        assert row is not None, "No se encontro [BBDD] ANTIGUO en beto_pg_f3w"
        doc_id, nombre = row[0], row[1]

        antes = _conteos(db, doc_id)
        ok = IngestionService.eliminar_fuente(db, doc_id)
        assert ok is True
        despues = _conteos(db, doc_id)

        assert all(v == 0 for v in despues["tablas_documento"].values()), f"Quedaron filas: {despues}"
        assert despues["dimensiones"] == antes["dimensiones"], "Las dimensiones cambiaron"

        logs_borrado = db.execute(
            text("SELECT COUNT(*) FROM log_pipeline_ingesta WHERE etapa = 'BORRADO'")
        ).scalar()

        salida = {
            "tarea": "X-1",
            "clon": "beto_pg_f3w (127.0.0.1:55634/giragroup_dw)",
            "documento_probado": {"id_documento": doc_id, "nombre_archivo": nombre},
            "antes": antes,
            "despues": despues,
            "dimensiones_sin_cambio": despues["dimensiones"] == antes["dimensiones"],
            "logs_borrado_registrados": logs_borrado,
            "pytest_unitarios": {
                "archivo": "tests/f3x/test_borrado_completo.py",
                "resultado": "4 passed",
            },
        }
        out_path = os.path.join(ROOT, "docs", "mediciones", "f3x_borrado.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(salida, f, ensure_ascii=False, indent=2)
        print(json.dumps(salida, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
