"""Tarea 7 (ronda 5): CSV de las tablas de giragroup_db (esquema public) con capa, filas, PK, descripción y archivo que las alimenta.
Filas, PK y capa salen de la base; la descripción, el alimentador y el motivo de las vacías están escritos aquí tras revisar el código.
Uso: DATABASE_URL=... python scripts/inventario_tablas_csv.py  -> docs/evidencias/inventario_tablas_48.csv"""
import csv, json, os
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent
DW, CAT, SEED = "backend/services/dw_loader.py", "giragroup_catalog_db (catalogs.py / catalog_repository.py)", "db/seeds/seed_catalogos.sql"
INFO = {
    "bridge_modulo_docente": ("Asignación de docentes a módulos (titular/tutor)", f"{DW} (_cargar_asignacion_docente; hoja MODULOS de ARCA)", ""),
    "cache_indice_beto": ("Caché del índice de confianza BETO por línea", "pipeline/semantic/indice_confianza.py", ""),
    "carga_fila_origen": ("Claves de idempotencia por fila de origen", f"{DW} (_reclamar_fila_origen)", ""),
    "cat_categoria_financiera": ("Catálogo de categorías financieras", SEED, ""),
    "cat_combinacion_estado": ("Combinaciones válidas de estado académico/tutoría/ARCA", "backend/services/catalogo_estados.py", f"Sin filas aquí: las reglas se leen de {CAT}; esta copia no se consulta"),
    "cat_concepto_financiero": ("Conceptos financieros canónicos", "backend/scripts/seed_financial_catalogs.py", f"Sin filas aquí: financial_catalog_service lee {CAT}"),
    "cat_escuela": ("Escuelas académicas", SEED, f"Sin filas aquí: routers/catalogs.py consulta {CAT}"),
    "cat_estado_academico": ("Estados académicos válidos", SEED, f"Sin filas aquí: catalog_repository lee el SQL semilla y {CAT}"),
    "cat_estado_arca": ("Estados ARCA válidos", SEED, f"Sin filas aquí: se lee de {CAT}; FK de cat_combinacion_estado impide eliminarla"),
    "cat_estado_reprobado": ("Estados de reprobación válidos", SEED, f"Sin filas aquí: se lee de {CAT}; FK de cat_combinacion_estado impide eliminarla"),
    "cat_etiqueta_clasificacion": ("Etiquetas para clasificar hojas por contenido", SEED, f"Sin filas aquí: pipeline/semantic/formatter.py usa {CAT}"),
    "cat_guia_texto_plano": ("Guías de texto plano para el formateador semántico", SEED, f"Sin filas aquí: pipeline/semantic/formatter.py usa {CAT}"),
    "cat_historico_equivalencia": ("Sinónimos de cabeceras financieras aprendidos", "backend/services/conceptos_financieros.py", f"Sin filas aquí: se lee y escribe en {CAT}"),
    "cat_institucion": ("Instituciones (catálogo maestro)", SEED, ""),
    "cat_institucion_convenio": ("Instituciones con convenio (variantes de nombre)", "backend/services/instituciones_convenio.py", f"Sin filas aquí: se consulta en {CAT}"),
    "cat_mapeo_columna": ("Mapeo de columnas de origen a campos canónicos", SEED, f"Sin filas aquí: pipeline/semantic/formatter.py usa {CAT}"),
    "cat_modalidad": ("Modalidades de programa", SEED, f"Sin filas aquí: routers/catalogs.py consulta {CAT}"),
    "cat_modulo": ("Catálogo canónico de módulos (FK de dim_modulo)", SEED, f"Sin filas aquí: routers/catalogs.py consulta {CAT}; dim_modulo.id_cat_modulo la referencia"),
    "cat_programa": ("Catálogo de programas", SEED, ""),
    "cat_tipo_programa": ("Tipos de programa", SEED, f"Sin filas aquí: routers/catalogs.py consulta {CAT}"),
    "dataops_tarea": ("Tareas de ingesta/lectura BETO/consolidación de DataOps", "backend/routers/dataops.py", ""),
    "dim_categoria_financiera": ("Categorías de ingreso/egreso (PROGRAMAS, TECHOS_CERRADOS...)", f"{DW} (rama rentabilidad)", ""),
    "dim_docente": ("Docentes (con fk_estado A/B/C)", f"{DW} (resolver_o_crear_docente)", ""),
    "dim_estudiante": ("Estudiantes (con fk_estado A/B/C)", f"{DW} (resolver_o_crear_estudiante)", ""),
    "dim_meta": ("Metas por indicador (modelo previo)", "backend/models/dim_meta.py", "Sin filas: ningún cargador la escribe; las metas viven en fact_rentabilidad.monto_meta y bi.ref_kpi"),
    "dim_modulo": ("Módulos y programas (POS)", f"{DW} (resolver_o_crear_modulo)", ""),
    "dim_origen_documental": ("Un registro por archivo subido (hash, tipo de fuente)", "backend/services/ingestion_service.py", ""),
    "dim_tiempo": ("Calendario diario (gestión, mes, periodo_mes)", f"{DW} (resolver_o_crear_tiempo)", ""),
    "fact_cobranzas_proyectadas": ("Cobranzas proyectadas por estudiante y mes", "ninguno (solo scripts/reset_dw.py y fix_sequences.sql la nombran)", "Sin filas: ningún cargador escribe en ella; se conserva porque tests/test_agnostic_classifier_and_dw_reset.py exige que reset_dw la trunque"),
    "fact_costo_programa": ("Egreso, ingreso y rentabilidad por POS", f"{DW} (_cargar costo; hoja egresos de BD Egresos)", ""),
    "fact_evaluacion_docente": ("Una fila por respuesta de encuesta docente/institucional", f"{DW} (rama evaluación) con backend/services/extraccion_por_encabezado.py", ""),
    "fact_forecast": ("Pronósticos guardados (Holt-Winters/OLS)", "backend/services/forecast_service.py", ""),
    "fact_marketing": ("Inscritos, reservas y leads por módulo y mes", f"{DW} (rama admisión/marketing; TBL_INSCRITOS)", ""),
    "fact_rendimiento_academico": ("Notas y estados de acta por estudiante y módulo", f"{DW} (rama académico; ACTAS DE NOTAS)", ""),
    "fact_rentabilidad": ("Recaudación mensual ejecutada y meta por categoría", f"{DW} (rama rentabilidad; EJECUTADO VS META)", ""),
    "fact_situacion_financiera": ("Deuda, pagos y cuotas por estudiante", f"{DW} (rama financiero; BD Cobranzas)", ""),
    "fact_techo_convenio": ("Techos y convenios por institución", f"{DW} (_cargar_techo_convenio; BD Techos)", ""),
    "log_auditoria_nlp": ("Bitácora de decisiones humanas sobre predicciones BETO", "backend/routers/dataops.py y services/revision_hechos.py", ""),
    "log_inconsistencias": ("Inconsistencias detectadas (conflictos de fuentes, descartes de personas)", f"{DW}, scripts/reejecutar_lote_1387_uploads_data.py", ""),
    "log_pipeline_ingesta": ("Bitácora de etapas del pipeline por documento", "backend/services/ingestion_service.py", ""),
    "lote": ("Lotes de carga", "backend/routers/dataops.py", ""),
    "notifications": ("Notificaciones a usuarios", "services/notifications-service", ""),
    "powerbi_informe_version": ("Versiones del informe de Power BI", "backend/scripts/migrations/007_powerbi_informe_version.sql", ""),
    "ref_metas_gestion": ("Metas anuales por gestión (catálogo)", SEED, f"Sin filas aquí: routers/catalogs.py consulta {CAT}"),
    "schema_migrations": ("Migraciones aplicadas", "backend/main.py (arranque)", ""),
    "staging_registros_crudos": ("Líneas leídas antes de la carga (staging)", "backend/routers/dataops.py", ""),
    "stg_entidad_no_resuelta": ("Cola HITL de entidades sin resolver (clave_origen única)", f"{DW}, backend/routers/pipeline.py", ""),
    "users": ("Usuarios y roles", "backend/seed_users.py", ""),
}

inv = json.loads((ROOT / "docs" / "evidencias" / "inventario_tablas.json").read_text(encoding="utf-8"))
eng = create_engine(os.environ["DATABASE_URL"])
with eng.connect() as c:
    pks = {r[0]: r[1] for r in c.execute(text(
        "SELECT tc.table_name, string_agg(kcu.column_name, ',' ORDER BY kcu.ordinal_position) FROM information_schema.table_constraints tc "
        "JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema "
        "WHERE tc.constraint_type='PRIMARY KEY' AND tc.table_schema='public' GROUP BY 1"))}
filas = []
for t in inv["tablas"]:
    d, alimenta, motivo = INFO[t["tabla"]]
    filas.append([t["tabla"], t["capa"], t["filas"], pks.get(t["tabla"], ""), d, alimenta, motivo if t["filas"] == 0 else ""])
assert len(filas) == 48 and all(f[5] for f in filas) and all(f[6] for f in filas if f[2] == 0)
with open(ROOT / "docs" / "evidencias" / "inventario_tablas_48.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["tabla", "capa", "filas", "pk", "descripcion", "archivo_que_la_alimenta", "motivo_si_vacia"])
    w.writerows(filas)
print(len(filas), "tablas;", sum(1 for f in filas if f[2] == 0), "vacías")
