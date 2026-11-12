"""DataOps: carga, lectura de BETO, revisión humana y consolidación.

La API conserva el prefijo /api/v1/dataops y todas sus rutas. Cada paso vive en su módulo; este paquete
solo los une bajo un mismo router con el control de acceso por rol.
"""
from fastapi import APIRouter, Depends

from core.security import require_roles

router = APIRouter(
    prefix="/api/v1/dataops",
    tags=["DataOps & Pipeline de Ingesta"],
    dependencies=[Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))],
)

from . import ingesta, lectura, revision, consolidacion, maestros  # noqa: E402

# El orden de inclusión conserva el orden de evaluación de rutas que tenía el archivo único
for _paso in (ingesta, lectura, revision, consolidacion, maestros):
    router.include_router(_paso.router)

import threading  # noqa: E402,F401
from core.database import SessionLocal  # noqa: E402,F401
from services import cache_lectura, tareas_dataops  # noqa: E402,F401
from services.dw_loader import DWLoaderService  # noqa: E402,F401

# Nombres públicos y auxiliares que otros módulos y las pruebas importan desde routers.dataops
from ._comun import (  # noqa: E402,F401
    AprobacionEnBloqueRequest,
    AprobarGrupoRequest,
    BatchResolveRequest,
    BetoInferRequest,
    COMPUERTA_LECTURA_MODELO,
    COMPUERTA_LECTURA_MODELO_PCT,
    ConfirmDwInsertRequest,
    DeleteBatchRequest,
    NOTA_APROBACION,
    TOPE_INDICE_BONIFICADO,
    TOPE_INDICE_BONIFICADO_DEC,
    UMBRAL_INDICE_REGISTRO,
    UMBRAL_INDICE_REGISTRO_DEC,
)
from .extraccion import (  # noqa: E402,F401
    _ENCABEZADOS_NO_ESTUDIANTE,
    _MEMO_CATALOGOS,
    _MEMO_LOCK,
    _MEMO_MAX_CATALOGOS,
    _STOP_TOKENS_EST,
    _docentes_con_contexto,
    _es_encabezado_no_estudiante,
    _mejor_docente,
    _mejor_estudiante,
    _mejor_modulo,
    _memo_catalogo,
    _personas_memo,
    _resolver_persona_cascada,
    extract_entities_from_line,
)
from .evaluacion import (  # noqa: E402,F401
    TTL_EVALUACION_LECTURA_SEG,
    _asegurar_lote_editable,
    _cerrar_transaccion_lectura,
    _estado_flujo_lote,
    _evaluacion_lectura,
    _evaluar_documentos_lote,
    _evaluar_lote_en_segundo_plano,
    _huella_evaluacion,
    _lote_consolidado_en_dw,
    _resolver_documentos_lote,
    _serializar_archivos_lote,
    _superponer_resoluciones,
)
from .ingesta import (  # noqa: E402,F401
    BASE_PROJ_DIR,
    LANDING_DIR,
    UPLOAD_DIR,
    clear_all_sources,
    delete_batch_sources,
    delete_source,
    eliminar_lote_fallido,
    export_logs,
    get_historial_lotes,
    get_logs,
    get_normalization_matrix,
    get_pipeline_logs,
    get_source_detail,
    get_sources,
    process_batch,
    purge_staging_cache,
    reprocess_document,
    upload_batch,
    upload_file,
)
from .lectura import (  # noqa: E402,F401
    get_lote_beto_reading,
    get_lote_context,
    get_lote_integridad,
    get_lote_plain_text_alias,
    get_lote_raw_vs_text,
    get_lote_resumen,
    get_plain_text_records,
    get_tarea,
    get_tarea_lote,
    get_tareas_activas,
    iniciar_lectura_lote,
    reintentar_lectura_lote,
    revelar_ci_registro,
)
from .revision import (  # noqa: E402,F401
    _aprobar_grupo,
    _bloquear_documentos_editables,
    _notificar_revision,
    approve_review_group,
    aprobar_casos_un_clic,
    batch_resolve_review_items,
    export_review_tray,
    get_review_tray,
    get_review_tray_groups,
    lock_review_item,
    resolve_review_item,
    unlock_review_item,
)
from .consolidacion import (  # noqa: E402,F401
    _consolidar,
    _registrar_descarte_ruido,
    confirm_dw_insert,
)
from .maestros import (  # noqa: E402,F401
    CATALOG_BUSINESS_LABELS,
    _build_fallback_embeddings_768,
    compare_rapidfuzz_strings,
    get_master_catalogs,
    get_telemetry_summary,
    infer_beto_text,
    link_entity_to_catalog,
)
