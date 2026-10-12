"""
backend/scripts/run_migrations.py
---------------------------------
Ejecutor determinista de migraciones versionadas para PostgreSQL 16.
Mantiene la tabla schema_migrations y aplica scripts SQL incrementales en orden.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
sys.path.insert(0, str(BASE_DIR))

from core.database import SQLALCHEMY_DATABASE_URL


def run_migrations():
    print(f"[*] Conectando a la base de datos...")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                version VARCHAR(150) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """))

    with engine.connect() as conn:
        result = conn.execute(text("SELECT version FROM public.schema_migrations;"))
        applied = {row[0] for row in result.fetchall()}

    sql_files = sorted(list(MIGRATIONS_DIR.glob("*.sql")))
    if not sql_files:
        print("[!] No se encontraron archivos de migración en backend/scripts/migrations.")
        return

    print(f"[*] Verificando {len(sql_files)} script(s) de migración...")
    unapplied_count = 0

    for sql_path in sql_files:
        version_name = sql_path.name
        if version_name in applied:
            continue

        unapplied_count += 1
        print(f"  [>] Aplicando migración: {version_name}...")
        sql_content = sql_path.read_text(encoding="utf-8")

        with engine.begin() as conn:
            conn.execute(text(sql_content))
            conn.execute(
                text("INSERT INTO public.schema_migrations (version) VALUES (:ver);"),
                {"ver": version_name}
            )
        print(f"  [✔] {version_name} aplicada con éxito.")

    if unapplied_count == 0:
        print("[✔] La base de datos se encuentra completamente actualizada al día.")
    else:
        print(f"[✔] Se aplicaron exitosamente {unapplied_count} migración(es).")


if __name__ == "__main__":
    run_migrations()
