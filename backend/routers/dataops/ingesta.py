"""Paso ①: carga de archivos, procesamiento por lote, historial y bitácora."""
import json
import logging
import os
import re
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from typing import Any, Dict, List, Optional
from schemas.dataops_schemas import BatchUploadItem, BatchUploadResponse, FileUploadResponse, PipelineResult, SourceListResponse
from models.dim_origen import DimOrigenDocumental
from services.ingestion_service import IngestionService
from models.log_pipeline import LogPipelineIngesta
from models.lote import Lote
from sqlalchemy.orm import Session
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from services.revision_hechos import contar_hechos_en_revision
from sqlalchemy import func
from core.database import get_db
from services import tareas_dataops
from ._comun import DeleteBatchRequest
from .evaluacion import _estado_flujo_lote, _evaluar_documentos_lote, _evaluar_lote_en_segundo_plano

logger = logging.getLogger(__name__)
router = APIRouter()


BASE_PROJ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


LANDING_DIR = os.environ.get(
    "LANDING_DIR",
    os.path.join(BASE_PROJ_DIR, "data", "landing", "batches")
)


os.makedirs(LANDING_DIR, exist_ok=True)


UPLOAD_DIR = LANDING_DIR


# =============================================================================
# ENDPOINTS DE GESTIÓN DE FUENTES E INGESTA MULTI-ARCHIVO (#15, #16, #17, #18)
# =============================================================================

@router.get("/sources", response_model=SourceListResponse)
def get_sources(db: Session = Depends(get_db)):
    """Obtiene la lista de fuentes documentales cargadas en el sistema y sus KPIs."""
    return IngestionService.obtener_fuentes(db)


@router.get("/historial-lotes")
def get_historial_lotes(
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Historial por lote, paginado y sin ejecutar inferencia ni cargar textos."""
    consulta = db.query(Lote)
    total = consulta.count()
    lotes = consulta.order_by(Lote.id_lote.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for lote in lotes:
        docs = db.query(DimOrigenDocumental).filter_by(id_lote=lote.id_lote).order_by(DimOrigenDocumental.id_documento).all()
        ids = [d.id_documento for d in docs]
        pendientes = db.query(func.count(StagingEntidadNoResuelta.id_staging)).filter(
            StagingEntidadNoResuelta.id_documento.in_(ids), StagingEntidadNoResuelta.resuelto == False,
        ).scalar() if ids else 0
        registros = db.query(func.sum(StagingRegistroCrudo.n_filas)).filter(
            StagingRegistroCrudo.id_documento.in_(ids), StagingRegistroCrudo.es_ruido == False,
        ).scalar() if ids else None
        lectura = tareas_dataops.ultima(lote.id_lote, "LECTURA_BETO")
        if _estado_flujo_lote(db, ids, pendientes) == "CONSOLIDADO":
            estado = "CONSOLIDADO"
        elif lote.estado == "CON_ERRORES" or (lectura and lectura["estado"] == "ERROR"):
            estado = "ERROR"
        elif pendientes or (ids and contar_hechos_en_revision(db, ids)):
            estado = "EN_REVISION"
        elif lectura and lectura["estado"] == "COMPLETADA":
            estado = "LEIDO_BETO"
        elif ids:
            estado = "TEXTO_LISTO"
        else:
            estado = "CARGADO"
        items.append({
            "id_lote": lote.id_lote,
            "id_documento": ids[0] if ids else None,
            "name": docs[0].nombre_archivo if len(docs) == 1 else f"Lote #{lote.id_lote}",
            "total_archivos": len(docs),
            "tipo_fuente": docs[0].tipo_fuente if len({d.tipo_fuente for d in docs}) == 1 else None,
            "records": int(registros) if registros is not None else None,
            "date": lote.creado_en.isoformat() if lote.creado_en else None,
            "status": estado,
            "puede_reintentar_lectura": bool(ids and lectura and lectura["estado"] == "ERROR"),
            "puede_eliminar": lote.estado == "CON_ERRORES" and not ids,
            "puede_reiniciar": estado != "CONSOLIDADO",
        })
    return {"data": items, "total": total, "page": page, "page_size": page_size}


@router.delete("/lote/{id_lote}/fallido")
def eliminar_lote_fallido(id_lote: int, db: Session = Depends(get_db)):
    lote = db.query(Lote).filter_by(id_lote=id_lote).first()
    if not lote:
        raise HTTPException(status_code=404, detail="El lote no existe.")
    if lote.estado != "CON_ERRORES" or db.query(DimOrigenDocumental).filter_by(id_lote=id_lote).first():
        raise HTTPException(status_code=409, detail="Solo se pueden eliminar desde aquí los lotes fallidos sin archivos procesados.")
    db.delete(lote)
    db.commit()
    return {"status": "success"}


@router.delete("/lote/{id_lote}")
def reiniciar_lote(id_lote: int, db: Session = Depends(get_db)):
    """
    Elimina y reinicia un lote no consolidado (incluyendo sus archivos en staging,
    logs y copias en landing), cancelando cualquier tarea EN_CURSO asociada.
    Protegido por el router DataOps (ADMIN / AUDITOR_CALIDAD).
    """
    import shutil
    from .evaluacion import _asegurar_lote_editable

    lote = db.query(Lote).filter_by(id_lote=id_lote).first()
    if not lote:
        raise HTTPException(status_code=404, detail="El lote no existe.")

    _asegurar_lote_editable(db, id_lote)
    tareas_dataops.cancelar_por_lote(id_lote, "Cancelada por reinicio de lote.")

    docs = db.query(DimOrigenDocumental).filter_by(id_lote=id_lote).all()
    doc_ids = [d.id_documento for d in docs]
    eliminados = 0
    if doc_ids:
        eliminados = IngestionService._eliminar_documentos_transaccion(db, doc_ids)

    db.query(Lote).filter_by(id_lote=id_lote).delete(synchronize_session=False)
    db.commit()

    batch_landing_dir = os.path.join(LANDING_DIR, str(id_lote))
    if os.path.isdir(batch_landing_dir):
        shutil.rmtree(batch_landing_dir, ignore_errors=True)

    return {
        "status": "success",
        "id_lote": id_lote,
        "archivos_eliminados": eliminados,
        "message": f"Lote #{id_lote} reiniciado correctamente.",
    }


@router.delete("/sources/clear-completed")
def clear_all_sources(db: Session = Depends(get_db)):
    """Elimina todas las fuentes procesadas de la cola activa."""
    deleted = IngestionService.limpiar_todas_las_fuentes(db)
    return {"status": "success", "message": f"{deleted} fuente(s) eliminada(s) exitosamente.", "deleted_count": deleted}


@router.post("/purge-staging-cache")
@router.delete("/purge-staging-cache")
def purge_staging_cache(db: Session = Depends(get_db)):
    """
    Purga completamente todos los lotes de staging, archivos en cola,
    registros crudos y logs temporales, dejando el sistema DataOps en estado limpio.
    """
    deleted = IngestionService.limpiar_todas_las_fuentes(db)
    return {
        "status": "success",
        "message": f"Se han purgado {deleted} documentos y todos los lotes de staging.",
        "deleted_count": deleted
    }


@router.post("/sources/delete-batch")
def delete_batch_sources(payload: DeleteBatchRequest, db: Session = Depends(get_db)):
    """Elimina un lote de fuentes documentales por sus IDs."""
    deleted = IngestionService.eliminar_lote_fuentes(db, payload.ids)
    return {"status": "success", "message": f"{deleted} fuente(s) eliminada(s) con éxito.", "deleted_count": deleted}


@router.delete("/sources/{doc_id}")
def delete_source(doc_id: int, db: Session = Depends(get_db)):
    """Elimina una fuente documental individual por su ID."""
    ok = IngestionService.eliminar_fuente(db, doc_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fuente documental con ID {doc_id} no encontrada.",
        )
    return {"status": "success", "message": f"Fuente {doc_id} eliminada exitosamente."}


@router.get("/sources/{doc_id}")
def get_source_detail(doc_id: int, db: Session = Depends(get_db)):
    """Obtiene el detalle y estado de una fuente documental específica."""
    fuentes = IngestionService.obtener_fuentes(db)
    for f in fuentes["data"]:
        if f["id"] == doc_id:
            return {"status": "success", "data": f}
    raise HTTPException(status_code=404, detail=f"Fuente documental con ID {doc_id} no encontrada.")


@router.post("/upload", response_model=FileUploadResponse)
def upload_file(
    file: UploadFile = File(...),
    source_type: Optional[str] = Form(None),
    tipo_fuente: Optional[str] = Form(None),
    tipo_escala: Optional[str] = Form(None),
    institucion: Optional[str] = Form("GiraGroup Posgrado"),
    periodo: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Sube un archivo individual (.xlsx, .csv), valida seguridad (#18),
    crea su registro en `lote` (#17) con reconocimiento automático de fechas multi-gestión
    y ejecuta las 6 etapas del pipeline en el threadpool de FastAPI.
    """
    content = file.file.read()
    err_sec = IngestionService.validar_seguridad_archivo(file.filename or "", content)
    if err_sec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_sec)

    safe_name = IngestionService.sanitizar_nombre_archivo(file.filename or "archivo.xlsx")
    sha256_full = IngestionService.calcular_sha256_completo(content)
    if db.query(DimOrigenDocumental).filter(
        DimOrigenDocumental.hash_sha256 == sha256_full,
        DimOrigenDocumental.institucion == (institucion or "GiraGroup Posgrado").strip(),
    ).first():
        raise HTTPException(status_code=409, detail="Este archivo ya fue cargado para esta institución. Revisa el historial.")

    # Crear lote para el archivo
    nuevo_lote = Lote(
        institucion=(institucion or "GiraGroup Posgrado").strip(),
        periodo=(periodo or "Auto").strip(),
        estado="PROCESADO",
        total_archivos=1,
    )
    db.add(nuevo_lote)
    db.flush()

    batch_landing_dir = os.path.join(LANDING_DIR, str(nuevo_lote.id_lote))
    os.makedirs(batch_landing_dir, exist_ok=True)

    try:
        dest_path = os.path.join(batch_landing_dir, safe_name)
        with open(dest_path, "wb") as f_out:
            f_out.write(content)
    except Exception as e_save:
        logger.warning("No se pudo guardar copia física de '%s' en '%s': %s", safe_name, batch_landing_dir, e_save)

    resultado = IngestionService.procesar_archivo_ingesta(
        db=db,
        file_bytes=content,
        filename=safe_name,
        source_type=source_type or "",
        id_lote=nuevo_lote.id_lote,
        tipo_fuente=tipo_fuente,
        tipo_escala=tipo_escala,
        institucion=(institucion or "GiraGroup Posgrado").strip(),
        periodo=(periodo or "Auto").strip(),
        hash_sha256=sha256_full,
    )

    if resultado.get("rango_fechas"):
        nuevo_lote.periodo = resultado.get("rango_fechas")
        db.commit()

    try:
        from models.log_pipeline import LogPipelineIngesta
        audit_log = LogPipelineIngesta(
            id_documento=resultado.get("id_documento"),
            etapa="INGESTA",
            nivel="SUCCESS",
            modulo="DataOps: Ingesta",
            mensaje=f"Lote #{nuevo_lote.id_lote} ({safe_name}): Ingesta, aplanamiento asimétrico y hash SHA-256 completado.",
            metadata_json={
                "id_lote": nuevo_lote.id_lote,
                "nombre_archivo": safe_name,
                "sha256": sha256_full,
                "registros": resultado.get("kpis", {}).get("total_registros_procesados", 0)
            }
        )
        db.add(audit_log)
        db.commit()
    except Exception as e_audit:
        logger.warning("No se pudo registrar log de auditoría: %s", e_audit)

    try:
        doc_obj = db.query(DimOrigenDocumental).filter_by(id_documento=resultado["id_documento"]).first()
        if doc_obj:
            _evaluar_documentos_lote(db, [doc_obj], persistir_staging=True)
    except Exception as e_eval_single:
        logger.warning("No se pudo evaluar documento %s post-ingesta: %s", resultado.get("id_documento"), e_eval_single)

    return {
        "status": "success",
        "message": f"Archivo '{safe_name}' procesado y normalizado con éxito.",
        "id_documento": resultado["id_documento"],
        "id_lote": nuevo_lote.id_lote,
        "nombre_archivo": safe_name,
        "tipo_fuente": resultado.get("tipo_fuente"),
        "fuera_de_alcance_cmi": int(resultado.get("fuera_de_alcance_cmi", 0)),
        "tipo_escala": resultado.get("tipo_escala"),
        "registros_detectados": resultado["kpis"]["total_registros_procesados"],
        "pipeline_result": resultado,
    }


@router.post("/upload-batch", response_model=BatchUploadResponse)
def upload_batch(
    files: List[UploadFile] = File(...),
    source_types: Optional[List[str]] = Form(None),
    tipos_fuente: Optional[List[str]] = Form(None),
    tipos_escala: Optional[List[str]] = Form(None),
    archivos_meta: Optional[str] = Form(None),
    institucion: Optional[str] = Form("GiraGroup Posgrado"),
    periodo: Optional[str] = Form(None),
    tipo_escala_global: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Sube y procesa un lote de 1 a 30 archivos simultáneos (#15, #16, #17, #18):
    - Máximo 30 archivos por lote, máximo 100 MB por archivo.
    - Solo permite .xlsx, .csv (rechaza .xls, .xml y otros).
    - Valida firma binaria (magic bytes), sanitiza nombres y verifica hash_sha256 duplicado.
    - Crea entidad `Lote` en PostgreSQL y vincula cada `dim_origen_documental.id_lote`.
    - Devuelve respuesta granular por archivo (`archivos_procesados`) sin abortar los válidos si uno falla.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se enviaron archivos para procesamiento por lote.",
        )

    if len(files) > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se enviaron {len(files)} archivos. El límite máximo permitido es de 30 archivos por lote.",
        )

    def _parse_form_list(raw_list: Optional[List[str]]) -> List[str]:
        if not raw_list:
            return []
        if len(raw_list) == 1 and (raw_list[0].startswith("[") or "," in raw_list[0]):
            try:
                parsed = json.loads(raw_list[0])
                if isinstance(parsed, list):
                    return [str(x or "") for x in parsed]
            except Exception:
                return [s.strip() for s in raw_list[0].split(",")]
        return [str(x or "") for x in raw_list]

    parsed_source_types = _parse_form_list(source_types)
    parsed_tipos_fuente = _parse_form_list(tipos_fuente)
    parsed_tipos_escala = _parse_form_list(tipos_escala)

    meta_list: List[Dict[str, Any]] = []
    if archivos_meta:
        try:
            loaded_meta = json.loads(archivos_meta)
            if isinstance(loaded_meta, list):
                meta_list = loaded_meta
        except Exception:
            meta_list = []

    inst_clean = (institucion or "GiraGroup Posgrado").strip()
    per_clean = (periodo or "Auto").strip()

    nuevo_lote = Lote(
        institucion=inst_clean,
        periodo=per_clean,
        estado="PROCESADO",
        total_archivos=0,
    )
    db.add(nuevo_lote)
    db.flush()
    db.commit()  # el lote existe ya para el seguimiento de la ingesta desde otras páginas
    tarea_ingesta = tareas_dataops.crear("INGESTA", nuevo_lote.id_lote, total=len(files))

    batch_landing_dir = os.path.join(LANDING_DIR, str(nuevo_lote.id_lote))
    os.makedirs(batch_landing_dir, exist_ok=True)

    resultados: List[BatchUploadItem] = []
    archivos_procesados: List[Dict[str, Any]] = []
    errores: List[Dict[str, str]] = []
    total_registros = 0
    hashes_en_lote = set()
    docs_creados_ids: List[int] = []

    def _cancelar_upload_lote() -> BatchUploadResponse:
        import shutil
        if docs_creados_ids:
            IngestionService._eliminar_documentos_transaccion(db, docs_creados_ids)
        db.query(Lote).filter_by(id_lote=nuevo_lote.id_lote).delete(synchronize_session=False)
        db.commit()
        if os.path.isdir(batch_landing_dir):
            shutil.rmtree(batch_landing_dir, ignore_errors=True)
        return BatchUploadResponse(
            status="cancelled",
            message=f"Carga del Lote #{nuevo_lote.id_lote} cancelada por el usuario.",
            id_lote=None,
            total_archivos=len(files),
            archivos_exitosos=0,
            files_processed=0,
            archivos_fallidos=len(files),
            total_registros_detectados=0,
            resultados=[],
            archivos_procesados=[],
            errores=[],
        )

    for idx, f in enumerate(files):
        if tareas_dataops.esta_cancelada(tarea_ingesta):
            return _cancelar_upload_lote()
        tareas_dataops.avanzar(tarea_ingesta, idx, forzar=True)
        raw_name = f.filename or f"archivo_{idx + 1}.xlsx"
        safe_name = IngestionService.sanitizar_nombre_archivo(raw_name)

        try:
            content = f.file.read()
        except Exception as e_read:
            msg = f"Error al leer bytes del archivo '{safe_name}': {e_read}"
            errores.append({"filename": safe_name, "error": msg})
            archivos_procesados.append({
                "nombre_archivo": safe_name,
                "status": "error_validacion",
                "estado": "error_validacion",
                "doc_id": None,
                "mensaje": msg,
                "detalle": msg,
            })
            resultados.append(BatchUploadItem(
                nombre_archivo=safe_name,
                tipo_fuente="ERROR",
                registros_detectados=0,
                status="error_validacion",
                mensaje=msg,
            ))
            continue

        # 1. Validación de seguridad (#18: extensión, tamaño <= 100MB, magic bytes)
        err_sec = IngestionService.validar_seguridad_archivo(raw_name, content)
        if err_sec:
            errores.append({"filename": safe_name, "error": err_sec})
            archivos_procesados.append({
                "nombre_archivo": safe_name,
                "status": "error_validacion",
                "estado": "error_validacion",
                "doc_id": None,
                "mensaje": err_sec,
                "detalle": err_sec,
            })
            resultados.append(BatchUploadItem(
                nombre_archivo=safe_name,
                tipo_fuente="RECHAZADO",
                registros_detectados=0,
                status="error_validacion",
                mensaje=err_sec,
            ))
            continue

        # 2. Detección de duplicados por hash_sha256 dentro de la misma institución/periodo (#18)
        sha256_full = IngestionService.calcular_sha256_completo(content)
        dup_db = db.query(DimOrigenDocumental).filter(
            DimOrigenDocumental.hash_sha256 == sha256_full,
            DimOrigenDocumental.institucion == inst_clean,
        ).first()

        if sha256_full in hashes_en_lote or dup_db is not None:
            dup_msg = (
                f"El archivo '{safe_name}' ya fue cargado para esta institución. "
                "Revisa el historial antes de volver a cargarlo."
            )
            existing_doc_id = dup_db.id_documento if dup_db else None
            archivos_procesados.append({
                "nombre_archivo": safe_name,
                "status": "duplicado",
                "estado": "duplicado",
                "doc_id": existing_doc_id,
                "tipo_fuente": dup_db.tipo_fuente if dup_db else None,
                "tipo_escala": dup_db.tipo_escala if dup_db else None,
                "hash_sha256": sha256_full,
                "mensaje": dup_msg,
                "detalle": dup_msg,
            })
            resultados.append(BatchUploadItem(
                id_documento=existing_doc_id,
                doc_id=existing_doc_id,
                nombre_archivo=safe_name,
                tipo_fuente=(dup_db.tipo_fuente if dup_db else "DUPLICADO"),
                tipo_escala=(dup_db.tipo_escala if dup_db else None),
                registros_detectados=0,
                status="duplicado",
                mensaje=dup_msg,
            ))
            continue

        # Extraer metadatos individuales del archivo (tipo_fuente y tipo_escala)
        meta_item = meta_list[idx] if idx < len(meta_list) and isinstance(meta_list[idx], dict) else {}
        req_fuente = (
            meta_item.get("tipo_fuente")
            or meta_item.get("tipoFuente")
            or (parsed_tipos_fuente[idx] if idx < len(parsed_tipos_fuente) else None)
            or (parsed_source_types[idx] if idx < len(parsed_source_types) else None)
        )
        req_escala = (
            meta_item.get("tipo_escala")
            or meta_item.get("escalaNotas")
            or (parsed_tipos_escala[idx] if idx < len(parsed_tipos_escala) else None)
            or tipo_escala_global
        )

        try:
            dest_path = os.path.join(batch_landing_dir, safe_name)
            with open(dest_path, "wb") as f_out:
                f_out.write(content)
        except Exception as e_save:
            logger.warning("No se pudo guardar copia física de '%s' en '%s': %s", safe_name, batch_landing_dir, e_save)

        try:
            resultado = IngestionService.procesar_archivo_ingesta(
                db=db,
                file_bytes=content,
                filename=safe_name,
                source_type=req_fuente or "",
                id_lote=nuevo_lote.id_lote,
                tipo_fuente=req_fuente,
                tipo_escala=req_escala,
                institucion=inst_clean,
                periodo=per_clean,
                hash_sha256=sha256_full,
            )

            hashes_en_lote.add(sha256_full)
            n_regs = resultado.get("kpis", {}).get("total_registros_procesados", 0)
            total_registros += n_regs
            doc_id_created = resultado.get("id_documento")
            if doc_id_created:
                docs_creados_ids.append(doc_id_created)
            fuente_final = resultado.get("tipo_fuente")
            escala_final = resultado.get("tipo_escala")
            ok_msg = f"Archivo '{safe_name}' procesado exitosamente ({n_regs} registros)."
            diag_item = resultado.get("diagnostico_estructural")
            chips_item = resultado.get("chips_catalogo")
            origen_det = resultado.get("origen_detectado")
            rango_det = resultado.get("rango_fechas")
            fechas_det = resultado.get("fechas_reconocidas")
            if rango_det and (nuevo_lote.periodo == "Auto" or not nuevo_lote.periodo):
                nuevo_lote.periodo = rango_det
                db.commit()

            archivos_procesados.append({
                "nombre_archivo": safe_name,
                "status": "procesado",
                "estado": "procesado",
                "doc_id": doc_id_created,
                "id_documento": doc_id_created,
                "tipo_fuente": fuente_final,
                "tipo_escala": escala_final,
                "registros_detectados": n_regs,
                "hash_sha256": sha256_full,
                "mensaje": ok_msg,
                "detalle": ok_msg,
                "diagnostico_estructural": diag_item,
                "chips_catalogo": chips_item,
                "origen_detectado": origen_det,
                "rango_fechas": rango_det,
                "fechas_reconocidas": fechas_det,
            })
            resultados.append(BatchUploadItem(
                id_documento=doc_id_created,
                doc_id=doc_id_created,
                nombre_archivo=safe_name,
                tipo_fuente=fuente_final or "SIN_RECONOCER",
                tipo_escala=escala_final,
                registros_detectados=n_regs,
                status="procesado",
                mensaje=f"Archivo '{safe_name}' procesado y normalizado con éxito.",
                pipeline_result=resultado,
                diagnostico_estructural=diag_item,
                chips_catalogo=chips_item,
                origen_detectado=origen_det,
                rango_fechas=rango_det,
                fechas_reconocidas=fechas_det,
            ))
        except Exception as e_proc:
            err_str = str(e_proc.detail) if hasattr(e_proc, "detail") else str(e_proc)
            err_msg = f"Falla al procesar: {err_str}"
            errores.append({"filename": safe_name, "error": err_str})
            archivos_procesados.append({
                "nombre_archivo": safe_name,
                "status": "error_validacion",
                "estado": "error_validacion",
                "doc_id": None,
                "mensaje": err_msg,
                "detalle": err_msg,
            })
            resultados.append(BatchUploadItem(
                nombre_archivo=safe_name,
                tipo_fuente="ERROR",
                registros_detectados=0,
                status="error_validacion",
                mensaje=err_msg,
            ))

    if tareas_dataops.esta_cancelada(tarea_ingesta):
        return _cancelar_upload_lote()

    exitosos = [r for r in resultados if r.status == "procesado"]
    nuevo_lote.total_archivos = len(exitosos)
    if not exitosos:
        nuevo_lote.estado = "CON_ERRORES"
    db.commit()
    if exitosos:
        tareas_dataops.terminar(tarea_ingesta, {
            "exitosos": len(exitosos), "fallidos": len(files) - len(exitosos), "total_registros": total_registros,
        })
    else:
        tareas_dataops.fallar(tarea_ingesta, "No se procesó ningún archivo. Revisa los mensajes de cada archivo.")

    try:
        from models.log_pipeline import LogPipelineIngesta
        audit_batch_log = LogPipelineIngesta(
            id_documento=docs_creados_ids[0] if docs_creados_ids else None,
            etapa="INGESTA",
            nivel="SUCCESS" if exitosos else "ERROR",
            modulo="DataOps: Ingesta",
            mensaje=f"Lote #{nuevo_lote.id_lote}: Carga de {len(exitosos)} archivo(s) procesados exitosamente ({total_registros} registros), aplanamiento asimétrico y hashes SHA-256 verificados.",
            metadata_json={
                "id_lote": nuevo_lote.id_lote,
                "total_archivos": len(files),
                "exitosos": len(exitosos),
                "fallidos": len(errores),
                "total_registros": total_registros,
                "archivos": [a.get("nombre_archivo") for a in archivos_procesados],
            }
        )
        db.add(audit_batch_log)
        db.commit()
    except Exception as e_audit_batch:
        logger.warning("No se pudo registrar log de auditoría del lote: %s", e_audit_batch)

    if docs_creados_ids:
        # La evaluación línea a línea de un lote grande tarda minutos: se hace después de responder.
        # Antes se hacía aquí y el gateway cortaba la subida con 504 aunque la ingesta ya estuviera completa.
        tarea_lectura = tareas_dataops.crear("LECTURA_BETO", nuevo_lote.id_lote)
        if background_tasks is not None:
            background_tasks.add_task(_evaluar_lote_en_segundo_plano, list(docs_creados_ids), nuevo_lote.id_lote, tarea_lectura)
        else:
            _evaluar_lote_en_segundo_plano(list(docs_creados_ids), nuevo_lote.id_lote, tarea_lectura)

    return BatchUploadResponse(
        status=("partial" if len(exitosos) < len(files) else "success") if exitosos else "error",
        message=f"{len(exitosos)} de {len(files)} archivo(s) procesados exitosamente en el Lote #{nuevo_lote.id_lote}.",
        id_lote=nuevo_lote.id_lote,
        total_archivos=len(files),
        archivos_exitosos=len(exitosos),
        files_processed=len(exitosos),
        archivos_fallidos=len(files) - len(exitosos),
        total_registros_detectados=total_registros,
        resultados=resultados,
        archivos_procesados=archivos_procesados,
        errores=errores,
    )


@router.post("/process-batch", response_model=PipelineResult)
def process_batch(
    doc_id: Optional[int] = Query(None),
    doc_id_form: Optional[int] = Form(None, alias="doc_id"),
    db: Session = Depends(get_db),
):
    """Procesa o re-procesa el documento/lote activo con datos reales de PostgreSQL."""
    effective_id = doc_id if doc_id is not None else doc_id_form
    target_doc = None
    if effective_id:
        target_doc = db.query(DimOrigenDocumental).filter_by(id_documento=effective_id).first()
    else:
        target_doc = db.query(DimOrigenDocumental).order_by(DimOrigenDocumental.id_documento.desc()).first()

    if not target_doc:
        return {
            "status": "success",
            "id_documento": 0,
            "id_lote": None,
            "nombre_archivo": "Sin archivo cargado",
            "tipo_fuente": "Pendiente de Carga",
            "tipo_escala": None,
            "stages": [
                {"id": 1, "name": "Archivo Origen", "time": "0ms", "desc": "En espera de archivo", "status": "completed"},
                {"id": 2, "name": "Dispatcher", "time": "0ms", "desc": "En espera", "status": "completed"},
                {"id": 3, "name": "Limpieza", "time": "0ms", "desc": "En espera", "status": "completed"},
                {"id": 4, "name": "Cabeceras", "time": "0ms", "desc": "0 Columnas", "status": "completed"},
                {"id": 5, "name": "Esquema", "time": "0ms", "desc": "0% Validez", "status": "completed"},
                {"id": 6, "name": "A Staging", "time": "0ms", "desc": "0 Bloques", "status": "completed"},
            ],
            "kpis": {
                "total_registros_procesados": 0,
                "registros_normalizados": 0,
                "inconsistencias_detectadas": 0,
                "tasa_limpieza": 0.0,
            },
            "normalization_matrix": [],
            "logs": [],
        }

    target_id = target_doc.id_documento
    stg_records = db.query(StagingRegistroCrudo).filter_by(id_documento=target_id).all()
    logs_db = IngestionService.obtener_logs_documento(db, target_id)
    matrix_db = IngestionService.obtener_matriz_normalizacion(db, target_id)

    total_filas = sum(r.n_filas or 0 for r in stg_records) or len(stg_records)
    inconsistencias = sum(1 for r in stg_records if r.requiere_revision)
    normalizadas = max(0, total_filas - inconsistencias)
    tasa_limpieza = round((normalizadas / (total_filas or 1)) * 100, 1) if total_filas > 0 else 100.0

    stages_map = [
        ("UPLOAD", "Archivo Origen", "Parseo UTF-8"),
        ("DISPATCH", "Dispatcher", (target_doc.tipo_fuente or target_doc.tipo_documento or "TABULAR")[:15]),
        ("CLEAN", "Limpieza", "Sanitizado"),
        ("NORMALIZE", "Cabeceras", f"{len(matrix_db)} Columnas"),
        ("VALIDATE", "Esquema", f"{tasa_limpieza}% Validez"),
        ("STAGE", "A Staging", f"{len(stg_records)} Bloques"),
    ]
    stages = []
    for idx, (etapa_key, name, desc_default) in enumerate(stages_map):
        matching_log = next((l for l in logs_db if l.get("etapa") == etapa_key), None)
        tiempo_ms = matching_log.get("tiempo_ms", 45) if matching_log else 45
        stages.append({
            "id": idx + 1,
            "name": name,
            "time": f"{tiempo_ms}ms",
            "desc": desc_default,
            "status": "completed",
        })

    return {
        "status": "success",
        "id_documento": target_id,
        "id_lote": target_doc.id_lote,
        "nombre_archivo": target_doc.nombre_archivo,
        "tipo_fuente": target_doc.tipo_fuente or target_doc.tipo_documento,
        "tipo_escala": target_doc.tipo_escala,
        "stages": stages,
        "kpis": {
            "total_registros_procesados": total_filas,
            "registros_normalizados": normalizadas,
            "inconsistencias_detectadas": inconsistencias,
            "tasa_limpieza": tasa_limpieza,
        },
        "normalization_matrix": matrix_db,
        "logs": logs_db,
    }


@router.post("/process/{doc_id}", response_model=PipelineResult)
def reprocess_document(doc_id: int, db: Session = Depends(get_db)):
    return process_batch(doc_id=doc_id, db=db)


@router.get("/logs/{doc_id}")
def get_logs(doc_id: int, page: int = Query(1, ge=1), map_page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    from services.bitacora_dataops import consultar
    return consultar(db, doc_id, page if isinstance(page, int) else 1, map_page if isinstance(map_page, int) else 1)


get_pipeline_logs = get_logs


@router.get("/logs/{doc_id}/export")
def export_logs(doc_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    from services.bitacora_dataops import documento, reporte
    doc = documento(db, doc_id)
    return StreamingResponse(reporte(db, doc), media_type='text/markdown; charset=utf-8',
                             headers={'Content-Disposition': f'attachment; filename="bitacora_documento_{doc_id}.md"'})


@router.get("/normalization-matrix/{doc_id}")
def get_normalization_matrix(doc_id: int, page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    from services.bitacora_dataops import documento, matriz_registrada, paginacion
    documento(db, doc_id)
    matriz = matriz_registrada(db, doc_id)
    page = page if isinstance(page, int) else 1
    return {'status': 'success', 'data': matriz[(page - 1) * 5:page * 5], 'pagination': paginacion(page, len(matriz))}


_SINONIMOS_PREVIEW = {
    "ci": ("CEDULA DE IDENTIDAD", "CI", "C.I.", "DOC_IDENTIDAD/CI", "CI_ESTUDIANTE", "IDNUMBER", "ID NUMBER", "CEDULA"),
    "nombre_completo": ("NOMBRE COMPLETO", "NOMBRES Y APELLIDOS", "APELLIDOS Y NOMBRES", "ESTUDIANTE", "ALUMNO", "PARTICIPANTE"),
    "programa": ("PROGRAMA", "NOMBRE DEL PROGRAMA", "DIPLOMADO", "CURSO", "POS", "CODIGO POS", "POS - ACTAS"),
    "modulo": ("MODULO", "NOMBRE DEL MODULO", "MATERIA", "ASIGNATURA"),
    "docente": ("DOCENTE", "PROFESOR", "FACILITADOR", "INSTRUCTOR"),
    "nota_final": ("NOTA FINAL", "NOTA", "CALIFICACION", "GRADE/100.00", "GRADE/100", "PROMEDIO FINAL"),
    "estado_academico": ("ESTADO ACADEMICO", "ESTADO", "ESTADO ARCA", "ESTADO TUTORIA"),
    "estado_cartera_fuente": ("TIPO DE CARTERA", "ESTADO CARTERA", "CARTERA"),
    "cuotas_impagas": ("TOTAL CUOTAS EN MORA", "CUOTAS EN MORA", "CUOTAS IMPAGAS"),
    "dias_mora": ("DIAS DE MORA", "DIAS MORA"),
    "monto_deuda": ("DEUDA TOTAL", "MONTO DEUDA", "SALDO"),
    "monto_pagado": ("TOTAL PAGADO", "MONTO PAGADO", "PAGADO"),
    "leads_captacion": ("LEADS", "INTERESADOS", "PROSPECTOS"),
    "inscritos_captacion": ("N° INSCRITOS", "NRO INSCRITOS", "INSCRITOS"),
    "puntuacion": ("PUNTUACION", "CALIFICACION DOCENTE", "SATISFACCION"),
    "fecha": ("FECHA", "FECHA INICIO", "FECHA DE PAGO", "FECHA EVALUACION", "MARCA TEMPORAL"),
    "gestion": ("GESTION", "ANO", "ANO INICIO"),
    "mes": ("MES", "MES INICIO"),
}

_CAMPOS_CANONICOS_DISPONIBLES = sorted(list(_SINONIMOS_PREVIEW.keys()) + ["correo_institucional", "celular", "institucion", "categoria_financiera", "monto_meta", "monto_ejecutado", "ignorar"])


_RE_PREGUNTA_ENCUESTA = re.compile(r"^\s*\d+\s*[\.\)\-]\s+\S")


def _es_pregunta_encuesta(nombre_col: str, norm: str) -> bool:
    crudo = (nombre_col or "").strip()
    if not crudo:
        return True
    if "¿" in crudo or "?" in crudo or _RE_PREGUNTA_ENCUESTA.match(crudo):
        return True
    if len(norm) > 45 or len(norm.split()) > 5:
        return True
    return False


def _inferir_campo_canonico(nombre_col: str) -> str:
    from services.extraccion_por_encabezado import normalizar_encabezado
    norm = normalizar_encabezado(nombre_col)
    if not norm:
        return ""
    for campo, sinonimos in _SINONIMOS_PREVIEW.items():
        if norm in sinonimos:
            return campo
    if _es_pregunta_encuesta(nombre_col, norm):
        return ""
    for campo, sinonimos in _SINONIMOS_PREVIEW.items():
        if any(s in norm for s in sinonimos if len(s) >= 5):
            return campo
    return ""


@router.post("/preview-workbook")
def preview_workbook(
    file: UploadFile = File(...),
    tipo_fuente: Optional[str] = Form(None),
):
    """
    FU-L8: Vista previa sin escritura en DW ni PII.
    Devuelve hojas (usada / ignorada / oculta + motivo + filas estimadas) y mapeo editable columna -> campo canónico.
    """
    import io
    import tempfile
    import pandas as pd
    from pipeline.ingesta import leer_archivo_con_metadatos
    from pipeline.lector_hojas import resumen_publico
    from services.dataops_privacy import texto_publico
    from services.ingestion_service import detectar_tipo_fuente_por_cabeceras, normalizar_codigo_tipo_fuente

    filename = os.path.basename(file.filename or "archivo.xlsx")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".xlsx", ".xlsm", ".csv"):
        raise HTTPException(status_code=400, detail="Solo se admiten archivos .xlsx, .xlsm o .csv para vista previa.")

    raw_bytes = file.file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    hojas_out: List[Dict[str, Any]] = []
    lectura_dfs: Dict[str, Any] = {}
    columnas_vistas: Dict[str, Dict[str, Any]] = {}

    if ext == ".csv":
        try:
            df_csv = pd.read_csv(io.BytesIO(raw_bytes))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"No se pudo leer el CSV: {exc}")
        lectura_dfs["CSV"] = df_csv
        hojas_out.append({
            "hoja": "CSV",
            "estado_visibilidad": "visible",
            "decision": "usada",
            "regla": "tabla_de_datos",
            "motivo": "Archivo tabular CSV",
            "filas_estimadas": int(len(df_csv)),
            "filas_fantasma_cortadas": 0,
            "subtotales_cortados": 0,
            "formulas_sin_valor": 0,
        })
        for col in df_csv.columns:
            c_str = str(col).strip()
            if c_str and not c_str.lower().startswith("unnamed"):
                columnas_vistas.setdefault(c_str, {
                    "columna_origen": c_str,
                    "campo_canonico": _inferir_campo_canonico(c_str),
                    "hoja": "CSV",
                })
    else:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name
            libro = leer_archivo_con_metadatos(tmp_path)
            resumen = resumen_publico(libro)
            for item in resumen:
                nombre_h = item.get("hoja")
                h_obj = libro.get(nombre_h)
                vis = "oculta" if item.get("estado") == "hidden" else "visible"
                dec = "usada" if item.get("decision") == "usar" else "ignorada"
                est_filas = int(item.get("filas_leidas") or 0)
                if dec == "usada" and est_filas == 0 and h_obj is not None:
                    est_filas = max(0, int(len(h_obj.df_recortado())) - 1)
                hojas_out.append({
                    "hoja": nombre_h,
                    "estado_visibilidad": vis,
                    "decision": dec,
                    "regla": item.get("regla"),
                    "motivo": item.get("motivo"),
                    "filas_estimadas": est_filas,
                    "filas_fantasma_cortadas": int(item.get("filas_fantasma_cortadas") or 0),
                    "subtotales_cortados": int(item.get("subtotales_cortados") or 0),
                    "formulas_sin_valor": int(item.get("formulas_sin_valor") or 0),
                })
            for nombre, h in libro.items():
                if not h.usada:
                    continue
                df_rec = h.df_recortado()
                lectura_dfs[nombre] = df_rec
                if len(df_rec) > 0:
                    # Primera fila no vacía como cabecera si las columnas son numéricas
                    cols = list(df_rec.columns)
                    if all(isinstance(c, int) or str(c).startswith("Unnamed") for c in cols):
                        vals = [str(v).strip() for v in df_rec.iloc[0].tolist() if pd.notna(v) and str(v).strip()]
                    else:
                        vals = [str(c).strip() for c in cols if str(c).strip() and not str(c).startswith("Unnamed")]
                    for c_str in vals:
                        c_pub = texto_publico(c_str)
                        columnas_vistas.setdefault(c_pub, {
                            "columna_origen": c_pub,
                            "campo_canonico": _inferir_campo_canonico(c_str),
                            "hoja": nombre,
                        })
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    tipo_detectado = detectar_tipo_fuente_por_cabeceras(lectura_dfs, filename) if lectura_dfs else None
    tipo_sugerido = normalizar_codigo_tipo_fuente(tipo_fuente) if tipo_fuente else None
    n_usadas = sum(1 for h in hojas_out if h["decision"] == "usada")
    n_ocultas = sum(1 for h in hojas_out if h["estado_visibilidad"] == "oculta")

    return {
        "status": "success",
        "nombre_archivo": filename,
        "tipo_fuente_detectado": tipo_detectado or tipo_sugerido,
        "resumen_hojas": {
            "total": len(hojas_out),
            "usadas": n_usadas,
            "ignoradas": len(hojas_out) - n_usadas,
            "ocultas": n_ocultas,
        },
        "hojas": hojas_out,
        "mapeo_columnas": list(columnas_vistas.values()),
        "campos_canonicos_disponibles": _CAMPOS_CANONICOS_DISPONIBLES,
    }
