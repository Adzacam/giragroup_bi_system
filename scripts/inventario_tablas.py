"""Tarea 4 (ronda 4): inventario de las tablas de giragroup_db: capa, filas exactas y archivos del repo que las referencian.
DDL/migraciones/reset/evidencias no cuentan como uso. Escribe docs/evidencias/inventario_tablas.json.
Uso: DATABASE_URL=postgresql://...@localhost:5434/giragroup_db python scripts/inventario_tablas.py"""
import json, os, re, subprocess
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
URL = os.environ["DATABASE_URL"]
CAPAS = [("hechos", r"^fact_"), ("dimensiones", r"^(dim_|bridge_)"), ("staging", r"^(stg_|staging_|cache_indice)"),
         ("auditoria", r"^(log_|audit|powerbi_informe)"), ("seguridad", r"^(users|notifications|roles|permis|token|sesion|api_key)"),
         ("control", r"^(carga_fila|dataops_|lote|schema_migrations)"), ("catalogos", r"^(cat_|ref_)")]
EXCL = re.compile(r"(^|/)(db/schema.*\.sql|db/migrations/|backend/scripts/migrations/|db/scripts/|docs/|node_modules/|scripts/inventario_tablas\.py|scripts/eliminar_tablas)")


def capa(t):
    for n, rx in CAPAS:
        if re.search(rx, t):
            return n
    return "otras"


def refs(t):
    p = subprocess.run(["git", "grep", "-l", "-w", "-I", t], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return sorted(f for f in p.stdout.split("\n") if f and not EXCL.search(f))


def main():
    eng = create_engine(URL)
    out = []
    with eng.connect() as c:
        tablas = [r[0] for r in c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1"))]
        fk_in = {r[0]: r[1] for r in c.execute(text(
            "SELECT ccu.table_name, count(*) FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage ccu "
            "ON tc.constraint_name=ccu.constraint_name WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='public' GROUP BY 1"))}
        for t in tablas:
            n = c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar()
            r = refs(t)
            out.append({"tabla": t, "capa": capa(t), "filas": n, "fk_entrantes": fk_in.get(t, 0), "n_archivos": len(r), "archivos": r})
    por_capa = {}
    for o in out:
        por_capa.setdefault(o["capa"], []).append(o["tabla"])
    cand = [o["tabla"] for o in out if o["filas"] == 0 and o["n_archivos"] == 0 and o["fk_entrantes"] == 0]
    cero_filas_con_uso = [o["tabla"] for o in out if o["filas"] == 0 and (o["n_archivos"] or o["fk_entrantes"])]
    res = {"total": len(out), "por_capa": {k: {"n": len(v), "tablas": v} for k, v in por_capa.items()},
           "candidatas_a_eliminar": cand, "cero_filas_con_referencias": cero_filas_con_uso, "tablas": out}
    (ROOT / "docs" / "evidencias" / "inventario_tablas.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    for o in out:
        print(f'{o["capa"]:12} {o["tabla"]:34} filas={o["filas"]:<8} fk_in={o["fk_entrantes"]} archivos={o["n_archivos"]}')
    print("candidatas:", cand); print("0 filas con referencias:", cero_filas_con_uso)


if __name__ == "__main__":
    main()
