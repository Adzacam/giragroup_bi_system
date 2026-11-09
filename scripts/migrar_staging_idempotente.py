"""
Migración 011: clave única de idempotencia en stg_entidad_no_resuelta.
clave_origen = md5(hash del archivo | tipo | motivo | valor normalizado). Deduplica la cola actual (conserva por clave
la fila resuelta si la hay, si no la de menor id_staging) y crea el índice único. Reporta pendientes antes/después.
Uso: DATABASE_URL=postgresql://... python scripts/migrar_staging_idempotente.py  (escribe docs/evidencias/migracion_staging_idempotente.json)
"""
import json, os, sys
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from models.staging_entidad import clave_staging

URL = os.environ.get("DATABASE_URL") or "postgresql://giragroup_user:giragroup_secret_2026@localhost:5434/giragroup_db"
SQL_CONTEOS = """SELECT count(*) total, count(*) FILTER (WHERE NOT resuelto AND estado_resolucion='PENDIENTE') pendientes,
 count(DISTINCT (SELECT COALESCE(d.hash_sha256,'doc'||s.id_documento) FROM dim_origen_documental d WHERE d.id_documento=s.id_documento)) archivos
 FROM stg_entidad_no_resuelta s"""


def main():
    eng = create_engine(URL)
    with eng.begin() as c:
        c.execute(text("ALTER TABLE stg_entidad_no_resuelta ADD COLUMN IF NOT EXISTS clave_origen VARCHAR(32)"))
        antes = dict(c.execute(text(SQL_CONTEOS)).mappings().one())
        antes["por_motivo"] = {f"{r[0]}/{r[1]}": r[2] for r in c.execute(text(
            "SELECT tipo_entidad, motivo, count(*) FROM stg_entidad_no_resuelta WHERE NOT resuelto AND estado_resolucion='PENDIENTE' GROUP BY 1,2 ORDER BY 3 DESC"))}
        hashes = {r[0]: r[1] for r in c.execute(text("SELECT id_documento, hash_sha256 FROM dim_origen_documental"))}
        filas = c.execute(text("SELECT id_staging, id_documento, tipo_entidad, motivo, texto_original, resuelto FROM stg_entidad_no_resuelta ORDER BY resuelto DESC, id_staging")).all()
        vistas, borrar, asignar = set(), [], []
        for i, doc, tipo, motivo, texto, _res in filas:
            k = clave_staging(hashes.get(doc) or (f"doc{doc}" if doc is not None else ""), tipo, motivo, texto)
            if k in vistas:
                borrar.append(i)
            else:
                vistas.add(k); asignar.append({"i": i, "k": k})
        c.execute(text("DROP INDEX IF EXISTS uq_stg_entidad_clave_origen"))
        for j in range(0, len(borrar), 5000):
            c.execute(text("DELETE FROM stg_entidad_no_resuelta WHERE id_staging = ANY(:b)"), {"b": borrar[j:j + 5000]})
        c.execute(text("UPDATE stg_entidad_no_resuelta SET clave_origen=:k WHERE id_staging=:i"), asignar)
        c.execute(text("CREATE UNIQUE INDEX uq_stg_entidad_clave_origen ON stg_entidad_no_resuelta (clave_origen)"))
        despues = dict(c.execute(text(SQL_CONTEOS)).mappings().one())
        despues["por_motivo"] = {f"{r[0]}/{r[1]}": r[2] for r in c.execute(text(
            "SELECT tipo_entidad, motivo, count(*) FROM stg_entidad_no_resuelta WHERE NOT resuelto AND estado_resolucion='PENDIENTE' GROUP BY 1,2 ORDER BY 3 DESC"))}
    res = {"antes": antes, "despues": despues, "filas_duplicadas_eliminadas": len(borrar)}
    out = ROOT / "docs" / "evidencias" / "migracion_staging_idempotente.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
