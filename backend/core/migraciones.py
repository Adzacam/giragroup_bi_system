"""Migraciones SQL versionadas: orden de aplicación y regla para no reaplicar la 003. Las usan el arranque de la API y run_migrations.py."""

# Migraciones que el arranque aplica si faltan, en este orden
MIGRACIONES_EN_ARRANQUE = (
    "003_dataops_lote_and_facts_alignment.sql",
    "004_extend_tipo_fuente_sources.sql",
    "005_alinear_esquema_con_ddl.sql",
    "006_capa_semantica_cmi.sql",
    "007_powerbi_informe_version.sql",
    "008_dataops_tarea.sql",
    "009_cache_indice_beto.sql",
    "010_dataops_tarea_ingesta.sql",
    "011_eliminar_tablas_sin_uso.sql",
    "012_evaluacion_revision_y_fuente_rentabilidad.sql",
    "013_renombrar_kpi10_confianza_extraccion.sql",
    "014_conversion_captacion_comprobable.sql",
    "017_dataops_tarea_preparacion_revision.sql",
    "018_fact_planificacion_programa.sql",
    "019_vista_planificacion_kpi23.sql",
    "020_retirar_rol_powerbi_reader.sql",
    "021_esquema_app_personalizacion.sql",
    "022_fu_l2_cobranza_mora_da3.sql",
    "023_fu_l3_fact_marketing_documento.sql",
    "024_fu_l4_actas_resultado_desercion.sql",
    "025_fu_l5_encuestas_escala_da1.sql",
    "026_fu_l6_metas_granularidad.sql",
    "027_adw_l6_cmi_config.sql",
    "028_fu_l9_decisiones_lean.sql",
)
MIGRACION_LOTE = "003_dataops_lote_and_facts_alignment.sql"
MIGRACION_TIPO_FUENTE = "004_extend_tipo_fuente_sources.sql"


def migraciones_a_aplicar(aplicadas: set) -> list:
    """
    003 recrea chk_dim_origen_tipo_fuente con 4 tipos. Si 004 ya está aplicada, reaplicar 003 fallaría
    (hay documentos RENTABILIDAD) o estrecharía la restricción: con 004 aplicada no se reaplica 003.
    005 (alineación con db/schema.sql) se aplica una vez, también al restaurar un respaldo anterior.
    """
    pendientes = [m for m in MIGRACIONES_EN_ARRANQUE if m not in aplicadas]
    if MIGRACION_TIPO_FUENTE in aplicadas:
        pendientes = [m for m in pendientes if m != MIGRACION_LOTE]
    return pendientes
