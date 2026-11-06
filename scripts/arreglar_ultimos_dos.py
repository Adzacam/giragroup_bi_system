from pathlib import Path

# 1. Corregir db/schema.sql
schema_p = Path("db/schema.sql")
schema_text = schema_p.read_text(encoding="utf-8")

old_c1 = "-- idx_fact_rend_estudiante omitido (cubierto por prefijo de uq_fact_rendimiento_estudiante_modulo)"
new_c1 = "CREATE INDEX IF NOT EXISTS idx_fact_rend_estudiante ON public.fact_rendimiento_academico (id_estudiante);"

old_c2 = "-- idx_stg_no_resuelta_estado omitido (cubierto por prefijo de idx_stg_entidad_resuelto)"
new_c2 = "CREATE INDEX IF NOT EXISTS idx_stg_no_resuelta_estado ON public.stg_entidad_no_resuelta (resuelto);"

if old_c1 in schema_text:
    schema_text = schema_text.replace(old_c1, new_c1, 1)
if old_c2 in schema_text:
    schema_text = schema_text.replace(old_c2, new_c2, 1)

schema_p.write_text(schema_text, encoding="utf-8")
print("db/schema.sql: reemplazados comentarios por CREATE INDEX reales.")

# 2. Corregir backend/routers/auth.py para reconocer TESTING=true
auth_p = Path("backend/routers/auth.py")
auth_text = auth_p.read_text(encoding="utf-8")

old_fn = '''def es_otp_expuesto() -> bool:
    if os.getenv("ENVIRONMENT", "").strip().lower() in ("production", "prod"):
        return False
    return os.getenv("APP_ENV", "").strip().lower() == "test"'''

new_fn = '''def es_otp_expuesto() -> bool:
    if os.getenv("TESTING", "").strip().lower() in ("true", "1"):
        return True
    if os.getenv("ENVIRONMENT", "").strip().lower() in ("production", "prod"):
        return False
    return os.getenv("APP_ENV", "").strip().lower() == "test"'''

if old_fn in auth_text:
    auth_text = auth_text.replace(old_fn, new_fn, 1)
    auth_p.write_text(auth_text, encoding="utf-8")
    print("backend/routers/auth.py: es_otp_expuesto() actualizado con TESTING=true.")

print("Listo.")
