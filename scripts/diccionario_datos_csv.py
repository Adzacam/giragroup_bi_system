"""Diccionario de datos: una fila por columna de las 48 tablas de public y las 2 tablas de bi (tabla, columna, tipo, nulo, PK/FK,
referencia, descripción). Tipo, nulo, PK/FK y referencia salen de la base; la descripción es la de la columna si está en DESC y, si no,
se deriva del nombre y queda marcada como 'derivada del nombre'.
Uso: DATABASE_URL=... python scripts/diccionario_datos_csv.py -> docs/evidencias/diccionario_datos.csv"""
import csv, os, re
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
DESC = {
    "id_documento": "Documento de origen (dim_origen_documental) del que viene el dato", "id_tiempo": "Día del calendario (dim_tiempo)",
    "id_modulo": "Módulo o programa (dim_modulo)", "id_estudiante": "Estudiante (dim_estudiante)", "id_docente": "Docente (dim_docente)",
    "id_categoria": "Categoría financiera (dim_categoria_financiera)", "fk_estado": "Estado de la llave: A CI exacta, B coincidencia aproximada, C miembro nuevo sin candidatos",
    "requiere_revision": "True si el hecho espera revisión humana", "motivo_revision": "Motivo de la marca de revisión o nota informativa (LIMITACION_FUENTE, TIEMPO_IMPUTADO, RESUELTO_HUMANO)",
    "nivel_confianza_ia": "Índice de confianza BETO del registro (nulo si las reglas resolvieron la línea sin consultar el modelo)",
    "nivel_confianza": "Índice de confianza BETO asociado al caso", "nombre_completo": "Nombre completo de la persona", "ci": "Cédula de identidad con complemento",
    "ci_numero": "Número de la cédula normalizado", "clave_respuesta": "Hash estable de la fila y la pregunta (idempotencia)", "clave_origen": "Clave de idempotencia (hash del archivo, tipo, motivo y valor)",
    "clave": "Clave de idempotencia por fila de origen", "created_at": "Fecha y hora de creación", "monto_ejecutado": "Monto ejecutado (recaudación) en Bs", "monto_meta": "Meta del mes en Bs",
    "puntuacion": "Puntaje de la respuesta", "escala_max": "Máximo de la escala de la pregunta (5 o 10)", "comentario": "Comentario libre de la respuesta", "tipo_pregunta": "DOCENTE, INSTITUCIONAL o NPS",
    "nota_final": "Nota final normalizada a base 100", "asistencia_pct": "Porcentaje de asistencia", "monto_deuda": "Deuda del estudiante en Bs", "monto_pagado": "Monto pagado en Bs", "cuotas_impagas": "Cuotas impagas",
    "estado_cartera": "Estado de la cartera (Vigente, Mora...)", "inscritos": "Inscritos del mes en el módulo", "leads": "Interesados del mes", "reservas": "Reservas del mes",
    "periodo_mes": "Período AAAA-MM", "gestion": "Año (gestión)", "mes": "Mes (1-12)", "fecha": "Fecha", "pos_code": "Código POS del programa o módulo (POS-xxxx[-Mnn])",
    "nombre_modulo": "Nombre del módulo o programa", "programa": "Programa al que pertenece", "motivo": "Motivo por el que el caso llegó a la cola", "texto_original": "Texto original del caso",
    "tipo_regla": "Regla que generó el registro del log", "estado_resolucion": "Estado de resolución del caso", "resuelto": "True si el caso ya fue resuelto", "hash_sha256": "Hash SHA-256 del archivo",
    "nombre_archivo": "Nombre del archivo subido", "tipo_fuente": "Tipo de fuente detectado (ACTA, COBRANZA, RENTABILIDAD...)", "email": "Correo electrónico", "role": "Rol del usuario", "username": "Nombre de usuario",
    "version": "Versión del registro (control optimista)", "codigo": "Código del indicador o perspectiva", "meta": "Meta del indicador", "umbral_verde": "Umbral del semáforo verde", "umbral_ambar": "Umbral del semáforo ámbar",
    "nombre": "Nombre", "descripcion": "Descripción", "orden": "Orden de presentación", "activo": "True si el registro está vigente", "applied_at": "Fecha de aplicación de la migración", "version_migracion": "Versión de la migración",
}
TABLAS_BI = ("ref_kpi", "ref_perspectiva")

eng = create_engine(os.environ["DATABASE_URL"])
filas = []
with eng.connect() as c:
    cols = c.execute(text("""
        SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.character_maximum_length, c.numeric_precision, c.numeric_scale, c.is_nullable, c.ordinal_position
        FROM information_schema.columns c JOIN information_schema.tables t ON t.table_schema=c.table_schema AND t.table_name=c.table_name
        WHERE t.table_type='BASE TABLE' AND ((c.table_schema='public') OR (c.table_schema='bi' AND c.table_name = ANY(:bi)))
        ORDER BY c.table_schema, c.table_name, c.ordinal_position"""), {"bi": list(TABLAS_BI)}).all()
    pk = {(r[0], r[1], r[2]) for r in c.execute(text(
        "SELECT kcu.table_schema, kcu.table_name, kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu "
        "ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema WHERE tc.constraint_type='PRIMARY KEY'"))}
    fk = {(r[0], r[1], r[2]): f"{r[3]}.{r[4]}" for r in c.execute(text(
        "SELECT kcu.table_schema, kcu.table_name, kcu.column_name, ccu.table_schema||'.'||ccu.table_name, ccu.column_name "
        "FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema "
        "JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name WHERE tc.constraint_type='FOREIGN KEY'"))}
    coment = {(r[0], r[1], r[2]): r[3] for r in c.execute(text(
        "SELECT n.nspname, cl.relname, a.attname, d.description FROM pg_description d JOIN pg_class cl ON cl.oid=d.objoid JOIN pg_namespace n ON n.oid=cl.relnamespace "
        "JOIN pg_attribute a ON a.attrelid=cl.oid AND a.attnum=d.objsubid WHERE d.objsubid>0"))}
for sch, tab, col, tipo, ln, prec, esc, nulo, _ in cols:
    t = tipo + (f"({ln})" if ln else f"({prec},{esc})" if tipo == "numeric" and prec else "")
    k = (sch, tab, col)
    desc = coment.get(k) or DESC.get(col)
    if not desc:
        desc = "Columna " + col.replace("_", " ") + " (derivada del nombre)"
    rol = "PK" if k in pk else ""
    if k in fk:
        rol = (rol + "+FK") if rol else "FK"
    filas.append([f"{sch}.{tab}", col, t, "SI" if nulo == "YES" else "NO", rol, fk.get(k, ""), desc])
tablas = {f[0] for f in filas}
assert sum(1 for t in tablas if t.startswith("public.")) == 48 and sum(1 for t in tablas if t.startswith("bi.")) == 2, tablas
with open(ROOT / "docs" / "evidencias" / "diccionario_datos.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["tabla", "columna", "tipo", "nulo", "pk_fk", "referencia", "descripcion"])
    w.writerows(filas)
print(len(tablas), "tablas,", len(filas), "columnas;", sum(1 for f in filas if "derivada del nombre" in f[6]), "con descripción derivada del nombre")
