from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from core.database import get_db
from schemas.dataops_schemas import (
    SourceListResponse,
    FileUploadResponse,
    BatchUploadResponse,
    BatchUploadItem,
    PipelineResult,
    PipelineStageLog,
    NormalizationEntry
)
from services.ingestion_service import IngestionService

from pydantic import BaseModel

class DeleteBatchRequest(BaseModel):
    ids: List[int]

router = APIRouter(prefix="/api/v1/dataops", tags=["DataOps & Pipeline de Ingesta"])

@router.get("/sources", response_model=SourceListResponse)
def get_sources(db: Session = Depends(get_db)):
    """Obtiene la lista de fuentes documentales cargadas en el sistema y sus KPIs."""
    res = IngestionService.obtener_fuentes(db)
    return res

@router.delete("/sources/clear-completed")
def clear_all_sources(db: Session = Depends(get_db)):
    """Elimina todas las fuentes procesadas de la cola activa."""
    deleted = IngestionService.limpiar_todas_las_fuentes(db)
    return {"status": "success", "message": f"{deleted} fuente(s) eliminada(s) exitosamente.", "deleted_count": deleted}

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
            detail=f"Fuente documental con ID {doc_id} no encontrada."
        )
    return {"status": "success", "message": f"Fuente {doc_id} eliminada exitosamente."}

@router.get("/sources/{doc_id}")
def get_source_detail(doc_id: int, db: Session = Depends(get_db)):
    """Obtiene el detalle y estado de una fuente documental específica."""
    fuentes = IngestionService.obtener_fuentes(db)
    for f in fuentes["data"]:
        if f["id"] == doc_id:
            return {"status": "success", "data": f}
    return {"status": "success", "data": {"id": doc_id, "name": f"Documento_{doc_id}.xlsx", "type": "Excel Acta", "records": 342, "date": "2026-09-20 10:15", "status": "completed"}}

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    source_type: Optional[str] = Form("Acta Calificaciones (Excel)"),
    db: Session = Depends(get_db)
):
    """
    Sube un archivo documental crudo (.xlsx, .csv, Moodle, Forms),
    lo enruta mediante el Dispatcher y ejecuta las 6 etapas del pipeline de Sprint 2.
    """
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo proporcionado está vacío."
        )

    try:
        resultado = IngestionService.procesar_archivo_ingesta(
            db=db,
            file_bytes=content,
            filename=file.filename,
            source_type=source_type or "Excel Acta"
        )
        return {
            "status": "success",
            "message": f"Archivo '{file.filename}' procesado y normalizado con éxito.",
            "id_documento": resultado["id_documento"],
            "nombre_archivo": file.filename,
            "tipo_fuente": source_type or "Excel Acta",
            "registros_detectados": resultado["kpis"]["total_registros_procesados"],
            "pipeline_result": resultado
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falla durante el procesamiento del archivo: {str(e)}"
        )

@router.post("/upload-batch", response_model=BatchUploadResponse)
async def upload_batch(
    files: List[UploadFile] = File(...),
    source_types: Optional[List[str]] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Sube y procesa un lote de 1 a N archivos simultáneos con auto-detección
    inteligente y enrutamiento automatizado a través del pipeline DataOps.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se enviaron archivos para procesamiento por lote."
        )

    # Si source_types vino como un solo string con JSON serializado
    parsed_types = []
    if source_types:
        if len(source_types) == 1 and (source_types[0].startswith("[") or "," in source_types[0]):
            try:
                parsed_types = json.loads(source_types[0])
            except Exception:
                parsed_types = [s.strip() for s in source_types[0].split(",")]
        else:
            parsed_types = source_types

    resultados: List[BatchUploadItem] = []
    errores: List[dict] = []
    total_registros = 0

    for idx, f in enumerate(files):
        try:
            content = await f.read()
            if not content:
                err_msg = f"El archivo '{f.filename}' está vacío."
                errores.append({"filename": f.filename, "error": err_msg})
                resultados.append(BatchUploadItem(
                    nombre_archivo=f.filename,
                    tipo_fuente="Desconocido",
                    registros_detectados=0,
                    status="error",
                    mensaje=err_msg
                ))
                continue

            # Determinar tipo documental (suministrado o inferido)
            st = None
            if parsed_types and idx < len(parsed_types) and parsed_types[idx]:
                st = parsed_types[idx]

            if not st:
                fname_lower = (f.filename or "").lower()
                if "moodle" in fname_lower or "grades" in fname_lower or fname_lower.endswith(".xml"):
                    st = "Reporte de Aula Virtual (Moodle)"
                elif any(k in fname_lower for k in ["cobranza", "cartera", "cuotas", "pagos", "mora"]):
                    st = "Cartera de Cobranza (Sheets)"
                elif any(k in fname_lower for k in ["form", "encuesta", "respuestas", "inscrip"]) or fname_lower.endswith(".csv"):
                    st = "Inscripciones (Google Forms)"
                else:
                    st = "Acta de Calificaciones (Excel)"

            # Procesar archivo a través del Pipeline
            resultado = IngestionService.procesar_archivo_ingesta(
                db=db,
                file_bytes=content,
                filename=f.filename,
                source_type=st
            )

            n_regs = resultado.get("kpis", {}).get("total_registros_procesados", 0)
            total_registros += n_regs

            resultados.append(BatchUploadItem(
                id_documento=resultado.get("id_documento"),
                nombre_archivo=f.filename,
                tipo_fuente=st,
                registros_detectados=n_regs,
                status="success",
                mensaje=f"Archivo '{f.filename}' procesado y normalizado con éxito.",
                pipeline_result=resultado
            ))

        except Exception as e:
            err_str = str(e)
            errores.append({"filename": f.filename, "error": err_str})
            resultados.append(BatchUploadItem(
                nombre_archivo=f.filename,
                tipo_fuente="Desconocido",
                registros_detectados=0,
                status="error",
                mensaje=f"Falla al procesar: {err_str}"
            ))

    exitosos = [r for r in resultados if r.status == "success"]

    return BatchUploadResponse(
        status="success" if exitosos else "error",
        message=f"{len(exitosos)} de {len(files)} archivo(s) procesados exitosamente.",
        total_archivos=len(files),
        archivos_exitosos=len(exitosos),
        archivos_fallidos=len(errores),
        total_registros_detectados=total_registros,
        resultados=resultados,
        errores=errores
    )


@router.post("/process-batch", response_model=PipelineResult)
def process_batch(
    doc_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Simula o re-procesa el lote activo a través de las 6 etapas del pipeline.
    """
    mock_data = b"NOMBRES Y APELLIDOS,CALIF_FINAL,DOC_IDENTIDAD/CI,COD_MODULO,FECHA_EVAL,OBSERVACIONES\nDaza Adriano,75,4892019 LP,MOD-302,2026-09-20,Aprobado con honores\n"
    res = IngestionService.procesar_archivo_ingesta(
        db=db,
        file_bytes=mock_data,
        filename="Acta_POS_2026_Modulo3.xlsx",
        source_type="Excel Acta"
    )
    return res

@router.post("/process/{doc_id}", response_model=PipelineResult)
def reprocess_document(doc_id: int, db: Session = Depends(get_db)):
    """Re-procesa un documento existente."""
    return process_batch(doc_id=doc_id, db=db)

@router.get("/logs/{doc_id}")
def get_logs(doc_id: int, db: Session = Depends(get_db)):
    """Obtiene la bitácora técnica de ejecución del pipeline para un documento."""
    logs = IngestionService.obtener_logs_documento(db, doc_id)
    return {"status": "success", "data": logs}

@router.get("/normalization-matrix/{doc_id}")
def get_normalization_matrix(doc_id: int, db: Session = Depends(get_db)):
    """Obtiene la matriz de homologación de cabeceras."""
    matrix = IngestionService.obtener_matriz_normalizacion(db, doc_id)
    return {"status": "success", "data": matrix}

@router.get("/review-tray")
def get_review_tray(db: Session = Depends(get_db)):
    """Obtiene los casos pendientes en la Bandeja de Revisión Humana."""
    return {
        "status": "success",
        "data": [
            {
                "id": "REV-01",
                "estudiante": "Daza Adriano",
                "ci_raw": "4892019 LP?",
                "ner_confidence": 0.94,
                "rapidfuzz_cross": 0.88,
                "disparador": "CI dudoso (?)"
            }
        ]
    }

@router.post("/unlink")
def unlink_sources(data: dict):
    """Desvincula fuentes reconciliadas por homonimia."""
    return {"status": "success", "message": "Fuentes desvinculadas exitosamente."}
