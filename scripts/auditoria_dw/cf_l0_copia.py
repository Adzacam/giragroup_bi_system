"""Copiar solo columnas institucionales a cf_l0_tmpfs; ejecutar desde repo.

Requiere contenedor PostgreSQL 16 cf_l0_tmpfs con bases cf_dw y cf_catalog.
No modifica las bases origen. La copia temporal no contiene personas.
"""
import subprocess

TABLES = [
    ("giragroup_db", "giragroup_db", "cf_dw", "dim_modulo", "id_modulo integer, nombre_modulo text, programa text, pos_code text, id_cat_modulo integer", "id_modulo,nombre_modulo,programa,pos_code,id_cat_modulo"),
    ("giragroup_db", "giragroup_db", "cf_dw", "cat_modulo", "id_modulo integer, codigo_modulo text, nombre_canonico text, nombre_modulo text", "id_modulo,codigo_modulo,nombre_canonico,nombre_modulo"),
    ("giragroup_catalog_db", "giragroup_catalog_db", "cf_catalog", "cat_programa", "id_programa integer, pos_code text, nombre_programa text, version integer, nombre_completo_raw text", "id_programa,pos_code,nombre_programa,version,nombre_completo_raw"),
    ("giragroup_catalog_db", "giragroup_catalog_db", "cf_catalog", "cat_modulo", "id_modulo integer, id_programa integer, nro_modulo integer, nombre_modulo text", "id_modulo,id_programa,nro_modulo,nombre_modulo"),
]

for container, database, dest, table, definition, columns in TABLES:
    subprocess.run(["docker", "exec", "cf_l0_tmpfs", "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", dest, "-c", f"CREATE TABLE {table} ({definition})"], check=True)
    source = subprocess.run(["docker", "exec", container, "psql", "-v", "ON_ERROR_STOP=1", "-U", "giragroup_user", "-d", database, "-c", f"COPY (SELECT {columns} FROM {table}) TO STDOUT WITH CSV"], check=True, stdout=subprocess.PIPE).stdout
    subprocess.run(["docker", "exec", "-i", "cf_l0_tmpfs", "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", dest, "-c", f"COPY {table} ({columns}) FROM STDIN WITH CSV"], input=source, check=True)
