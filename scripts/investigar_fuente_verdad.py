"""
scripts/investigar_fuente_verdad.py
Herramienta de auditoría para la Fuente de Verdad de la Tesis.
Se conecta exclusivamente al snapshot congelado: snapshot_dw_20261110_1201.
"""
import os
import json
import psycopg2
from collections import Counter

URL_SNAPSHOT = "postgresql://giragroup_user:giragroup_secret_2026@localhost:5434/snapshot_dw_20261110_1201"
URL_CATALOG = "postgresql://giragroup_user:giragroup_secret_2026@localhost:5433/giragroup_catalog_db"

def auditar_tablas():
    conn = psycopg2.connect(URL_SNAPSHOT)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name;
    """)
    tables = cur.fetchall()
    print(f"Total tablas en DW (snapshot): {len(tables)}")
    por_esquema = Counter()
    res = []
    for s, t in tables:
        por_esquema[s] += 1
        try:
            cur.execute(f'SELECT count(*) FROM "{s}"."{t}"')
            cnt = cur.fetchone()[0]
        except Exception as e:
            cnt = f"ERROR: {e}"
            conn.rollback()
        res.append((s, t, cnt))
    print("Tablas por esquema:", dict(por_esquema))
    
    # Catalog DB
    conn_cat = psycopg2.connect(URL_CATALOG)
    cur_cat = conn_cat.cursor()
    cur_cat.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name;
    """)
    cat_tables = cur_cat.fetchall()
    print(f"Total tablas en Catalog DB: {len(cat_tables)}")
    cat_res = []
    for s, t in cat_tables:
        try:
            cur_cat.execute(f'SELECT count(*) FROM "{s}"."{t}"')
            cnt = cur_cat.fetchone()[0]
        except Exception as e:
            cnt = f"ERROR: {e}"
            conn_cat.rollback()
        cat_res.append((s, t, cnt))

    return res, cat_res

if __name__ == "__main__":
    t_dw, t_cat = auditar_tablas()
    print("\n--- Tablas DW ---")
    for s, t, c in t_dw:
        print(f"{s}.{t}: {c}")
    print("\n--- Tablas Catalog DB ---")
    for s, t, c in t_cat:
        print(f"{s}.{t}: {c}")
