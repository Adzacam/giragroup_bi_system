"""Pasos ② y ③: texto preparado, resultados de la lectura de BETO, tareas y revelado auditado de la cédula."""
import json
import logging
import math
import re
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.log_auditoria_nlp import LogAuditoriaNlp
from models.lote import Lote
from typing import Optional
from sqlalchemy.orm import Session
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from models.user import User
from services.revision_hechos import contar_hechos_en_revision
from datetime import datetime
from services.dataops_evaluation_service import enmascarar_ci, strip_accents
from core.security import get_current_user, require_roles
from core.database import get_db
from services import tareas_dataops
from ._comun import COMPUERTA_LECTURA_MODELO_PCT, TOPE_INDICE_BONIFICADO, UMBRAL_INDICE_REGISTRO, UMBRAL_INDICE_REGISTRO_DEC
from .evaluacion import _asegurar_lote_editable, _estado_flujo_lote, _evaluacion_lectura, _evaluar_lote_en_segundo_plano, _lote_consolidado_en_dw, _resolver_documentos_lote, _serializar_archivos_lote
from .extraccion import _docentes_con_contexto, extract_entities_from_line

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/lote/{id_lote}/iniciar-lectura")
def iniciar_lectura_lote(id_lote: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    lote = db.query(Lote).filter_by(id_lote=id_lote).with_for_update().first()
    if not lote:
        raise HTTPException(status_code=404, detail="El lote no existe.")
    _asegurar_lote_editable(db, id_lote)
    docs = db.query(DimOrigenDocumental).filter_by(id_lote=id_lote).all()
    if not docs:
        raise HTTPException(status_code=409, detail="Carga archivos antes de iniciar la lectura.")
    previa = tareas_dataops.ultima_en_sesion(db, id_lote, "LECTURA_BETO")
    if previa and previa["estado"] == "EN_CURSO":
        return {"status": "processing", "tarea": previa}
    if _evaluacion_lectura(db, docs) is not None:
        return {"status": "ready"}
    try:
        tarea_id = tareas_dataops.crear_en_sesion(db, "LECTURA_BETO", id_lote)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=503, detail="No se pudo iniciar la lectura. Inténtalo de nuevo.")
    background_tasks.add_task(_evaluar_lote_en_segundo_plano, [d.id_documento for d in docs], id_lote, tarea_id)
    return {"status": "processing", "tarea_id": tarea_id, "tarea": tareas_dataops.obtener(tarea_id)}


@router.post("/lote/{id_lote}/reintentar-lectura")
def reintentar_lectura_lote(id_lote: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    tarea = tareas_dataops.ultima(id_lote, "LECTURA_BETO")
    if not tarea or tarea["estado"] != "ERROR":
        raise HTTPException(status_code=409, detail="Solo se puede reintentar una lectura interrumpida. Actualiza el historial.")
    return iniciar_lectura_lote(id_lote, background_tasks, db)


@router.get("/lote/{id_lote}/integridad")
def get_lote_integridad(id_lote: str, page: int = Query(1, ge=1),
                       db: Session = Depends(get_db),
                       user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"]))):
    from services.integridad_dataops import consultar
    _, docs, _ = _resolver_documentos_lote(db, id_lote)
    lectura = _evaluacion_lectura(db, docs)
    pagina = docs[(page - 1) * 5:page * 5]
    resultado = consultar(db, pagina, lectura)
    resultado['pagination'] = {'page': page, 'page_size': 5, 'total_items': len(docs),
                               'total_pages': max(1, math.ceil(len(docs) / 5))}
    return resultado


@router.get("/lote/{id_lote}/resumen")
def get_lote_resumen(
    id_lote: str,
    doc_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Calcula en el servidor los KPIs e Índice Medio sobre todos los registros del lote (#1, #2).
    - Aplica redondeo por Mayor Residuo garantizando que autoPct + auditPct + inconsistenciasPct == 100.0%.
    - Con lote vacío (totalTuplas == 0), retorna '—' en los indicadores y 0.0% en la barra de distribución.
    """
    if hasattr(doc_id, "default"):
        doc_id = None
    lote_obj, docs_lote, docs_filtrados = _resolver_documentos_lote(db, id_lote, doc_id_filter=doc_id)
    # Lectura pura: si los registros ya tienen payload_json evaluado, no persistir ni hacer commit en GET
    from services.lectura_beto_service import seleccionar_documento
    eval_res = _evaluacion_lectura(db, docs_lote)
    if eval_res is None:
        return {"status": "pending", "empty": False, "mensaje_vacio": "La lectura de BETO aún no está disponible. Ábrela en el paso ③.", "id_lote": lote_obj.id_lote if lote_obj else None}
    eval_res = seleccionar_documento(eval_res, doc_id)
    archivos_tabs = _serializar_archivos_lote(db, docs_lote)

    total_tuplas = eval_res["totalTuplas"]
    if total_tuplas == 0:
        return {
            "status": "success",
            "empty": True,
            "id_lote": lote_obj.id_lote if lote_obj else None,
            "totalDocumentos": "—",
            "totalTuplas": "—",
            "totalEntidades": "—",
            "autoCount": "—",
            "auditCount": "—",
            "inconsistenciasCount": "—",
            "indiceMedio": "—",
            "autoPct": 0.0,
            "auditPct": 0.0,
            "inconsistenciasPct": 0.0,
            "mensaje_vacio": "Sin registros en el lote activo — Suba un archivo en ① Ingesta para visualizar la distribución",
            "archivos": archivos_tabs,
            "umbrales": {
                "compuerta_lectura_modelo": COMPUERTA_LECTURA_MODELO_PCT,
                "umbral_indice_registro": UMBRAL_INDICE_REGISTRO,
                "tope_indice_bonificado": TOPE_INDICE_BONIFICADO,
            },
        }

    return {
        "status": "success",
        "empty": False,
        "id_lote": lote_obj.id_lote if lote_obj else (docs_lote[0].id_lote if docs_lote else None),
        "institucion": lote_obj.institucion if lote_obj else (docs_lote[0].institucion if docs_lote else "GiraGroup Posgrado"),
        "periodo": lote_obj.periodo if lote_obj else (docs_lote[0].periodo if docs_lote else "2026-1"),
        "totalDocumentos": len(docs_lote),
        "totalTuplas": total_tuplas,
        "totalEntidades": eval_res["totalEntidades"],
        "autoCount": eval_res["autoCount"],
        "auditCount": eval_res["auditCount"],
        "inconsistenciasCount": eval_res["inconsistenciasCount"],
        "indiceMedio": eval_res["indiceMedio"],
        "autoPct": eval_res["autoPct"],
        "auditPct": eval_res["auditPct"],
        "inconsistenciasPct": eval_res["inconsistenciasPct"],
        "archivos": archivos_tabs,
        "umbrales": {
            "compuerta_lectura_modelo": COMPUERTA_LECTURA_MODELO_PCT,
            "umbral_indice_registro": UMBRAL_INDICE_REGISTRO,
            "tope_indice_bonificado": TOPE_INDICE_BONIFICADO,
        },
    }


@router.get("/lote/{id_lote}/context")
def get_lote_context(
    id_lote: str,
    doc_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Paso común: Información de cabecera y contexto del lote multi-archivo siempre visible (#17)."""
    lote_obj, docs_lote, docs_filtrados = _resolver_documentos_lote(db, id_lote, doc_id_filter=doc_id)
    if not docs_lote and not lote_obj:
        # Fallback defensivo a 'latest' si el ID específico de lote quedó obsoleto en el cliente
        lote_obj, docs_lote, docs_filtrados = _resolver_documentos_lote(db, "latest", doc_id_filter=doc_id)
        if not docs_lote and not lote_obj:
            raise HTTPException(status_code=404, detail=f"Lote o documento con ID {id_lote} no encontrado.")

    archivos_tabs = _serializar_archivos_lote(db, docs_lote)
    active_doc = docs_filtrados[0] if docs_filtrados else (docs_lote[0] if docs_lote else None)

    doc_ids = [d.id_documento for d in docs_lote]
    total_tuplas = sum(a["total_registros"] for a in archivos_tabs)
    total_hitl = (
        db.query(StagingEntidadNoResuelta)
        .filter(
            StagingEntidadNoResuelta.id_documento.in_(doc_ids),
            StagingEntidadNoResuelta.resuelto == False,
        )
        .count()
        if doc_ids
        else 0
    )

    escala_map = {
        "CENTESIMAL_100": "Sobre 100",
        "DECIMAL_10": "Sobre 10",
        "VIGESIMAL_20": "Sobre 20",
    }
    fuente_label_map = {
        "ACTA": "Acta de calificaciones",
        "MOODLE": "Reporte Aula Moodle",
        "COBRANZA": "Cobranza y pagos",
        "ADMISION": "Admisiones y matriculación",
        "EVALUACION_DOCENTE": "Evaluación docente",
        "EGRESOS": "Egresos",
        "TECHOS": "Techos de convenio",
        "RENTABILIDAD": "Rentabilidad",
        "MARKETING": "Marketing",
        "PLANIFICACION": "Planificación",
    }

    institucion = (
        (lote_obj.institucion if lote_obj else None)
        or (active_doc.institucion if active_doc else None)
        or "GiraGroup Posgrado"
    )
    periodo = (
        (lote_obj.periodo if lote_obj else None)
        or (active_doc.periodo if active_doc else None)
        or "2026-1"
    )

    tipos_fuentes_unicos = list({d.tipo_fuente for d in docs_lote if d.tipo_fuente})
    if len(docs_lote) > 1:
        nombre_display = f"Lote #{lote_obj.id_lote if lote_obj else id_lote} ({len(docs_lote)} archivos)"
        tipo_fuente_display = (
            fuente_label_map.get(tipos_fuentes_unicos[0], tipos_fuentes_unicos[0])
            if len(tipos_fuentes_unicos) == 1
            else f"Multi-fuente ({', '.join(tipos_fuentes_unicos)})"
        )
    else:
        nombre_display = active_doc.nombre_archivo if active_doc else f"Lote_{id_lote}"
        tf_code = active_doc.tipo_fuente if active_doc else "ACTA"
        tipo_fuente_display = fuente_label_map.get(tf_code, tf_code or "Acta de calificaciones")

    escala_activa = active_doc.tipo_escala if active_doc else None
    escala_label = escala_map.get(escala_activa, "No aplica (Finanzas/Admisión)" if not escala_activa else escala_activa)

    estado_flujo = _estado_flujo_lote(db, doc_ids, total_hitl)
    if estado_flujo == "CONSOLIDADO" or total_hitl > 0 or (doc_ids and contar_hechos_en_revision(db, doc_ids) > 0):
        ultimo_paso = 4
    else:
        ultimo_paso = 3 if total_tuplas > 0 else 1

    return {
        "status": "success",
        "id_lote": lote_obj.id_lote if lote_obj else (active_doc.id_lote if active_doc else None),
        "id_documento": active_doc.id_documento if active_doc else None,
        "nombre_archivo": nombre_display,
        "institucion": institucion,
        "tipo_fuente": active_doc.tipo_fuente if active_doc else None,
        "tipo_fuente_label": tipo_fuente_display,
        "tipo_escala": escala_activa,
        "escala_label": escala_label,
        "periodo": periodo,
        "fecha_procesamiento": active_doc.fecha_procesamiento.isoformat() if (active_doc and active_doc.fecha_procesamiento) else None,
        "total_archivos": len(docs_lote),
        "total_registros": total_tuplas,
        "pendientes_revision": total_hitl,
        "archivos": archivos_tabs,
        "paso_sugerido": 4 if total_hitl > 0 else 3,
        "estado_flujo": estado_flujo,
        "ultimo_paso": ultimo_paso,
    }


@router.get("/lote/{id_lote}/raw-vs-text")
def get_lote_raw_vs_text(
    id_lote: str,
    doc_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=5),
):
    """Paso ②: cinco filas protegidas por página, sin ejecutar inferencia."""
    from services.texto_preparado_service import obtener_texto_preparado
    lote, docs, filtrados = _resolver_documentos_lote(db, id_lote, doc_id_filter=doc_id)
    if not docs or (doc_id is not None and doc_id not in {d.id_documento for d in docs}):
        raise HTTPException(status_code=404, detail="El lote o el archivo seleccionado no existe en este lote.")
    resultado = obtener_texto_preparado(db, filtrados, page=page, page_size=page_size)
    resultado.update({"id_lote": lote.id_lote if lote else None, "id_documento": doc_id})
    return resultado


@router.get("/PlainText/{id_lote}")
def get_lote_plain_text_alias(
    id_lote: str,
    doc_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=5),
):
    """Alias del paso ②: conserva la misma paginación y protección."""
    return get_lote_raw_vs_text(id_lote=id_lote, doc_id=doc_id, db=db, page=page, page_size=page_size)


@router.get("/lote/{id_lote}/beto-reading")
def get_lote_beto_reading(
    id_lote: str,
    doc_id: Optional[int] = Query(None),
    area: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    motivo: Optional[str] = Query(None),
    filtro_global: Optional[str] = Query(None),
    tipo_entidad: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=5),
    search: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db),
):
    """
    Paso ③: Vista principal de lectura de BETO con Capa A, B y C (#1, #2, #3, #12, #13, #17).
    - El campo `ci` se entrega siempre enmascarado por defecto (`••••019 LP`).
    - Clasifica registros en las 4 Áreas de Trabajo: Académica, Financiera, Comercial y Calidad.
    - Soporta filtros globales persistentes, corroboración multifuente y desglose relacional Cero-PII.
    """
    if not isinstance(doc_id, int):
        doc_id = None
    if not isinstance(area, str):
        area = None
    if not isinstance(estado, str):
        estado = None
    if not isinstance(motivo, str):
        motivo = None
    if not isinstance(filtro_global, str):
        filtro_global = None
    if not isinstance(tipo_entidad, str):
        tipo_entidad = None
    if not isinstance(page, int):
        page = 1
    if not isinstance(page_size, int):
        page_size = 5

    lote_obj, docs_lote, docs_filtrados = _resolver_documentos_lote(db, id_lote, doc_id_filter=doc_id)
    if not docs_lote or (doc_id is not None and doc_id not in {d.id_documento for d in docs_lote}):
        raise HTTPException(status_code=404, detail="El lote o el archivo seleccionado no existe en este lote.")
    from services.lectura_beto_service import seleccionar_documento, coincide_entidad
    from services.dataops_privacy import registro_beto_publico
    eval_res = _evaluacion_lectura(db, docs_lote)
    if eval_res is None:
        tarea = tareas_dataops.ultima(lote_obj.id_lote, "LECTURA_BETO") if lote_obj else None
        return {"status": "processing" if tarea and tarea["estado"] == "EN_CURSO" else "pending",
                "id_lote": lote_obj.id_lote if lote_obj else None, "tarea": tarea,
                "registros": [], "pagination": {"page": page, "page_size": page_size, "total_items": 0, "total_pages": 1}}
    eval_res = seleccionar_documento(eval_res, doc_id)
    detalles_all = eval_res["detalles"]

    # 1. Filtro por Área de Trabajo
    filtrados = detalles_all
    if area and area.upper() not in ("ALL", "TODAS", "TODOS"):
        area_clean = area.lower()
        if area_clean == "calidad":
            filtrados = [r for r in filtrados if r.get("en_calidad")]
        else:
            filtrados = [r for r in filtrados if r.get("area") == area_clean]

    # 2. Filtros Globales Persistentes
    if filtro_global and filtro_global.upper() not in ("ALL", "TODOS"):
        fg = filtro_global.upper()
        if "CONFIANZA" in fg or "< 85" in fg or "BAJA" in fg:
            filtrados = [r for r in filtrados if isinstance(r.get("indice_registro"), (int, float)) and r["indice_registro"] < 85]
        elif "CONFLICTO" in fg or "INCIDENCIA" in fg:
            filtrados = [r for r in filtrados if r.get("estado") in ("INCONSISTENCIA", "REVISION")]
        elif "CATALOGO" in fg or "SUGERENCIA" in fg:
            filtrados = [r for r in filtrados if r.get("es_nuevo_catalogo")]
        elif "ABANDONO" in fg or "DESERCION" in fg:
            filtrados = [r for r in filtrados if r.get("alerta_abandono")]

    # 3. Filtro por Tipo de Entidad
    if tipo_entidad and tipo_entidad.upper() not in ("ALL", "TODAS", "TODOS"):
        te_up = tipo_entidad.upper()
        filtrados = [r for r in filtrados if coincide_entidad(r, te_up)]

    # 4. Filtrado server-side por estado o motivo (#12, #13)
    if estado and estado.upper() not in ("ALL", "TODOS"):
        est_up = estado.upper()
        if est_up == "REVISION":
            filtrados = [r for r in filtrados if r["estado"] != "AUTOMATICO"]
        else:
            filtrados = [r for r in filtrados if r["estado"] == est_up or r["categoria_particion"] == est_up]

    if motivo and motivo.upper() not in ("ALL", "TODOS"):
        mot_up = motivo.upper()
        filtrados = [r for r in filtrados if (r.get("motivo") or "").upper() == mot_up]

    if isinstance(search, str) and search.strip():
        q = strip_accents(search.strip()).lower()
        filtrados = [r for r in filtrados if q in strip_accents(" ".join(str(r.get(k) or '') for k in ('modulo', 'nombre_archivo', 'ci_enmascarado', 'raw_text'))).lower()]
    total_filtrados = len(filtrados)
    start_idx = (page - 1) * page_size
    paginados = filtrados[start_idx : start_idx + page_size]

    total_analizados = eval_res["totalTuplas"]
    directo_dw = eval_res["autoCount"]
    a_revision = eval_res["auditCount"] + eval_res["inconsistenciasCount"]

    capa_resumen = {
        "total_analizados": total_analizados,
        "directo_dw": directo_dw,
        "a_revision": a_revision,
        "audit_count": eval_res["auditCount"],
        "inconsistencias_count": eval_res["inconsistenciasCount"],
        "indice_medio": eval_res["indiceMedio"],
        "porcentaje_automatico": eval_res["autoPct"],
        "porcentaje_revision": round(eval_res["auditPct"] + eval_res["inconsistenciasPct"], 1),
        "auto_pct": eval_res["autoPct"],
        "audit_pct": eval_res["auditPct"],
        "inconsistencias_pct": eval_res["inconsistenciasPct"],
    }

    # Conteo por las 4 Áreas de Trabajo
    count_acad = len([r for r in detalles_all if r.get("area") == "academica"])
    auto_acad = len([r for r in detalles_all if r.get("area") == "academica" and r.get("estado") == "AUTOMATICO"])
    rev_acad = len([r for r in detalles_all if r.get("area") == "academica" and r.get("estado") == "REVISION"])
    inc_acad = len([r for r in detalles_all if r.get("area") == "academica" and r.get("estado") == "INCONSISTENCIA"])

    count_fin = len([r for r in detalles_all if r.get("area") == "financiera"])
    auto_fin = len([r for r in detalles_all if r.get("area") == "financiera" and r.get("estado") == "AUTOMATICO"])
    rev_fin = len([r for r in detalles_all if r.get("area") == "financiera" and r.get("estado") == "REVISION"])
    inc_fin = len([r for r in detalles_all if r.get("area") == "financiera" and r.get("estado") == "INCONSISTENCIA"])

    count_com = len([r for r in detalles_all if r.get("area") == "comercial"])
    auto_com = len([r for r in detalles_all if r.get("area") == "comercial" and r.get("estado") == "AUTOMATICO"])
    rev_com = len([r for r in detalles_all if r.get("area") == "comercial" and r.get("estado") == "REVISION"])
    inc_com = len([r for r in detalles_all if r.get("area") == "comercial" and r.get("estado") == "INCONSISTENCIA"])

    count_cal = len([r for r in detalles_all if r.get("en_calidad")])
    rev_cal = len([r for r in detalles_all if r.get("en_calidad") and r.get("estado") == "REVISION"])
    inc_cal = len([r for r in detalles_all if r.get("en_calidad") and r.get("estado") == "INCONSISTENCIA"])

    areas_dict = {
        "academica": {
            "key": "academica",
            "titulo": "Académica",
            "total": count_acad,
            "auto": auto_acad,
            "revision": rev_acad,
            "incidencias": inc_acad,
            "descripcion": "Notas, módulos, asistencia (umbral de abandono) y validación contra oferta curricular.",
        },
        "financiera": {
            "key": "financiera",
            "titulo": "Financiera",
            "total": count_fin,
            "auto": auto_fin,
            "revision": rev_fin,
            "incidencias": inc_fin,
            "descripcion": "Pagos, cuotas impagas, importes y vencimientos conciliados con aranceles del catálogo.",
        },
        "comercial": {
            "key": "comercial",
            "titulo": "Comercial",
            "total": count_com,
            "auto": auto_com,
            "revision": rev_com,
            "incidencias": inc_com,
            "descripcion": "Inscripciones individuales vs demanda agregada, canales de captación y metas por programa.",
        },
        "calidad": {
            "key": "calidad",
            "titulo": "Calidad (Capa Transversal)",
            "total": count_cal,
            "auto": 0,
            "revision": rev_cal,
            "incidencias": count_cal,
            "descripcion": "Duplicados, faltantes, valores fuera de rango, cruce de abandono y nuevos ítems para el Catálogo Guía.",
        },
    }

    resumen_ejecutivo = {
        "total_procesados": total_analizados,
        "aceptados_automaticamente": directo_dw,
        "por_revisar": eval_res["auditCount"],
        "con_incidencias": eval_res["inconsistenciasCount"],
        "avance_porcentaje": round((directo_dw / total_analizados * 100), 1) if total_analizados > 0 else 0.0,
        "estado_lote": "Listo para consolidar" if (eval_res["auditCount"] + eval_res["inconsistenciasCount"] == 0) else "Revisión en curso",
        "alerta_abandono_count": len([r for r in detalles_all if r.get("alerta_abandono")]),
        "sugerencias_catalogo_count": len([r for r in detalles_all if r.get("es_nuevo_catalogo")]),
    }

    # El lote ya pasó por la consolidación si alguno de sus documentos tiene hechos en el DW:
    # la SPA lo usa para marcar el paso ③ como hecho y destacar la bandeja ④ como siguiente acción
    ids_docs = [d.id_documento for d in docs_lote]
    consolidado = _lote_consolidado_en_dw(db, ids_docs)
    resumen_ejecutivo["consolidado"] = consolidado

    archivos_tabs = _serializar_archivos_lote(db, docs_lote)
    return {
        "status": "success",
        "id_lote": lote_obj.id_lote if lote_obj else (docs_lote[0].id_lote if docs_lote else None),
        "id_documento": doc_id or (docs_filtrados[0].id_documento if docs_filtrados else None),
        "archivos": archivos_tabs,
        "capaA": capa_resumen,
        "capa_a_resumen": capa_resumen,
        "resumen_ejecutivo": resumen_ejecutivo,
        "areas": areas_dict,
        "pendientes_revision": a_revision,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_filtrados,
            "total_pages": max(1, math.ceil(total_filtrados / page_size)),
        },
        "registros": [registro_beto_publico(r) for r in paginados],
        "modelo_info": {
            "nombre": "BETO",
            "compuerta_lectura_modelo": COMPUERTA_LECTURA_MODELO_PCT,
            "umbral_vigente": UMBRAL_INDICE_REGISTRO,
        },
    }


def _extraer_campo_de_linea(line_txt: str, campo: str) -> Optional[str]:
    from services.dataops_privacy import EMAIL, _sensible, _columnas
    if not line_txt:
        return None
    if campo == "ci":
        m_ci = re.search(r"\b([0-9]{5,9}\b(?:\s*(?:LP|SC|CB|OR|PT|TJ|CH|BE|PA)\b)?\??)", line_txt, re.IGNORECASE)
        return m_ci.group(1).strip() if m_ci else None
    if campo == "correo":
        m_em = EMAIL.search(line_txt)
        return m_em.group(0).strip() if m_em else None
    if campo == "nombre":
        for parte in re.split(r"\||;|,(?=\s*[^,:|;]{1,45}:)", line_txt):
            rotulo, sep, valor = parte.partition(":")
            if sep and _sensible(rotulo) == "privado" and valor.strip():
                r_low = rotulo.lower()
                if any(k in r_low for k in ("nombre", "estudiante", "alumno", "participante", "docente", "razon")):
                    return valor.strip()
        cols = _columnas(line_txt)
        if cols and ":" not in line_txt and re.fullmatch(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+(?:\s+[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+)+", cols[0]):
            return cols[0].strip()
    return None


@router.get("/registro/{registro_id}/revelar-ci")
def revelar_ci_registro(
    registro_id: str,
    campo: str = Query("ci", pattern="^(ci|nombre|correo)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """
    Endpoint protegido por JWT y rol (`ADMIN` o `AUDITOR_CALIDAD`) que revela el dato sensible
    (`ci`, `nombre` o `correo`) de un registro específico y deja constancia en auditoría (#13, W-12).
    """
    val_real = None
    contexto_audit = f"Revelación de {campo.upper()} para registro {registro_id}"

    # 1. Formato REG_{stg_id}_{line_num} o {stg_id}_{line_num}
    m_reg = re.match(r"^(?:(?:REG|STG)_)?(\d+)_(\d+)$", str(registro_id).strip(), re.IGNORECASE)
    if m_reg:
        stg_id = int(m_reg.group(1))
        line_num = int(m_reg.group(2))
        stg = db.query(StagingRegistroCrudo).filter(StagingRegistroCrudo.id == stg_id).first()
        if stg:
            payload = stg.payload_json if isinstance(stg.payload_json, dict) else {}
            for tup in payload.get("tuplas") or []:
                if tup.get("line_number") == line_num or tup.get("id") in (registro_id, f"REG_{stg_id}_{line_num}"):
                    if campo == "ci":
                        val_real = tup.get("ci_real")
                    elif campo == "nombre":
                        val_real = tup.get("nombre_real") or tup.get("nombre")
                    elif campo == "correo":
                        val_real = tup.get("correo_real") or tup.get("correo")
                    break
            if not val_real and stg.texto_plano:
                lines = [l.strip() for l in stg.texto_plano.split("\n") if l.strip()]
                if 1 <= line_num <= len(lines):
                    val_real = _extraer_campo_de_linea(lines[line_num - 1], campo)

    # 2. ID numérico de StagingEntidadNoResuelta o StagingRegistroCrudo
    if not val_real:
        clean_num = str(registro_id).replace("REV-", "").strip()
        if clean_num.isdigit():
            num_id = int(clean_num)
            ent = db.query(StagingEntidadNoResuelta).filter(StagingEntidadNoResuelta.id_staging == num_id).first()
            if ent:
                p = ent.payload_json if isinstance(ent.payload_json, dict) else {}
                if campo == "ci":
                    val_real = ent.ci_temporal or p.get("ci_real") or p.get("ci")
                elif campo == "nombre":
                    val_real = p.get("nombre_real") or p.get("nombre") or ent.mejor_candidato
                elif campo == "correo":
                    val_real = p.get("correo_real") or p.get("correo")
                if not val_real:
                    raw_src = p.get("raw_line") or ent.texto_original or ""
                    val_real = _extraer_campo_de_linea(raw_src, campo)
            if not val_real:
                stg = db.query(StagingRegistroCrudo).filter(StagingRegistroCrudo.id == num_id).first()
                if stg and stg.texto_plano:
                    val_real = _extraer_campo_de_linea(stg.texto_plano, campo)

    if not val_real:
        raise HTTPException(status_code=404, detail=f"No se encontró {campo} para el registro '{registro_id}'.")

    val_enmascarado = (
        enmascarar_ci(val_real) if campo == "ci"
        else ("••••@••••" if campo == "correo" else "••••")
    )

    # Registrar evento de auditoría de acceso a dato sensible (#13, W-12)
    try:
        audit_entry = LogAuditoriaNlp(
            texto_original=contexto_audit[:500],
            prediccion_beto=val_enmascarado,
            confianza_ia=1.0,
            correccion_humana=f"REVELAR_{campo.upper()}_AUTORIZADO ({current_user.username})",
            usuario_auditor=current_user.id,
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e_aud:
        db.rollback()
        logger.warning("No se pudo persistir auditoría de revelación (%s): %s", campo, e_aud)

    resp = {
        "status": "success",
        "id": registro_id,
        "campo": campo,
        "valor": val_real,
        "valor_enmascarado": val_enmascarado,
        "auditado_por": current_user.username,
        "timestamp": datetime.utcnow().isoformat(),
    }
    if campo == "ci":
        resp["ci"] = val_real
        resp["ci_real"] = val_real
        resp["ci_enmascarado"] = val_enmascarado
    return resp


@router.get("/tareas/{tarea_id}")
def get_tarea(tarea_id: int, _: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"]))):
    tarea = tareas_dataops.obtener(tarea_id)
    if not tarea:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No existe la tarea {tarea_id}.")
    return tarea


@router.get("/tareas")
def get_tareas_activas(_: User = Depends(get_current_user)):
    """Tareas largas en curso (y las terminadas hace menos de 2 min) para el panel global de la SPA."""
    return tareas_dataops.activas()


@router.get("/lote/{id_lote}/tarea")
def get_tarea_lote(id_lote: int, tipo: str = Query("CONSOLIDACION", pattern="^(INGESTA|CONSOLIDACION|LECTURA_BETO|PREPARACION_REVISION)$")):
    """Última tarea del lote de ese tipo (en curso o terminada), o null."""
    return tareas_dataops.ultima(id_lote, tipo)


@router.get("/plain-text-records")
def get_plain_text_records(
    doc_ids: Optional[str] = None,
    id_lote: Optional[str] = None,
    db: Session = Depends(get_db),
):
    # Sanitización defensiva de parámetros
    if hasattr(doc_ids, "default"):
        doc_ids = None
    if hasattr(id_lote, "default"):
        id_lote = None

    ids_list = []
    if doc_ids:
        ids_list = [int(x.strip()) for x in str(doc_ids).split(",") if x.strip().isdigit()]

    estudiantes = db.query(DimEstudiante).filter(DimEstudiante.deprecado == False).all()
    docentes = _docentes_con_contexto(db)
    modulos = db.query(DimModulo).all()

    query = db.query(StagingRegistroCrudo, DimOrigenDocumental).outerjoin(
        DimOrigenDocumental, StagingRegistroCrudo.id_documento == DimOrigenDocumental.id_documento
    )

    if ids_list and id_lote:
        _, docs_lote, _ = _resolver_documentos_lote(db, id_lote)
        if docs_lote:
            lote_doc_ids = {d.id_documento for d in docs_lote}
            filtered_ids = [d_id for d_id in ids_list if d_id in lote_doc_ids]
            if not filtered_ids:
                return {"status": "success", "total": 0, "data": []}
            query = query.filter(StagingRegistroCrudo.id_documento.in_(filtered_ids))
        else:
            return {"status": "success", "total": 0, "data": []}
    elif ids_list:
        query = query.filter(StagingRegistroCrudo.id_documento.in_(ids_list))
    elif doc_ids and not ids_list:
        return {"status": "success", "total": 0, "data": []}
    elif id_lote:
        _, docs_lote, _ = _resolver_documentos_lote(db, id_lote)
        if docs_lote:
            query = query.filter(StagingRegistroCrudo.id_documento.in_([d.id_documento for d in docs_lote]))
        else:
            return {"status": "success", "total": 0, "data": []}
    else:
        # Default fallback a lote más reciente para evitar escaneo completo de 3.1M registros
        _, docs_lote, _ = _resolver_documentos_lote(db, "latest")
        if docs_lote:
            query = query.filter(StagingRegistroCrudo.id_documento.in_([d.id_documento for d in docs_lote]))
        else:
            return {"status": "success", "total": 0, "data": []}

    records_db = query.all()
    if not records_db:
        return {"status": "success", "total": 0, "data": []}

    items = []
    for stg, orig in records_db:
        fname = orig.nombre_archivo if orig else f"Documento_{stg.id_documento}.xlsx"
        doc_fuente = (orig.tipo_fuente if orig and orig.tipo_fuente else "ACTA").upper()
        doc_escala = orig.tipo_escala if orig else "CENTESIMAL_100"
        if doc_fuente in ("COBRANZA", "ADMISION"):
            doc_escala = None
        elif not doc_escala:
            doc_escala = "CENTESIMAL_100"

        raw_text = (stg.texto_plano or "").strip()
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        if not lines and raw_text:
            lines = [raw_text]

        payload = stg.payload_json or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        stg_diag = payload.get("diagnostico_estructural") or {}
        stg_chips = payload.get("chips_catalogo") or {}
        stg_rango = payload.get("rango_fechas") or (orig.periodo if orig else "2024–2026 (Auto)")

        for line_idx, line in enumerate(lines):
            ents, score, req_rev = extract_entities_from_line(
                line, estudiantes, docentes, modulos, tipo_escala=doc_escala, tipo_fuente=doc_fuente
            )
            ci_tok = next((e["token"] for e in ents if e.get("label") == "DOCUMENTO / CI"), None)
            ci_masked = enmascarar_ci(ci_tok)

            items.append({
                "id": f"STG_{stg.id}_{line_idx + 1}",
                "db_id": stg.id,
                "id_documento": stg.id_documento,
                "sourceFile": fname,
                "sourceType": doc_fuente,
                "tipo_fuente": doc_fuente,
                "tipo_escala": doc_escala,
                "line_number": line_idx + 1,
                "rawText": line,
                "texto_plano": raw_text,
                "score_confianza": score,
                "indice_registro": int(round(score * 100)),
                "requiere_revision": req_rev,
                "entities": ents,
                "chips_catalogo": stg_chips,
                "diagnostico_estructural": stg_diag,
                "rango_fechas": stg_rango,
                "relacion_semantica": {
                    "estudiante": {
                        "nombre": next((e["token"] for e in ents if e.get("label") == "ESTUDIANTE"), "No especificado"),
                        "ci": ci_masked,
                        "origen": "ALTA_DOCUMENTAL",
                    },
                    "modulo": {
                        "nombre": next((e["matchedCanonical"] or e["token"] for e in ents if e.get("label") == "MÓDULO"), "Módulo Académico"),
                        "codigo": next((e.get("canonicalId") for e in ents if e.get("label") == "MÓDULO"), "MOD-GEN"),
                        "evidencia": "CATALOGO" if any(e.get("catalogTable") in ("dim_modulo", "Catálogo de Módulos") and not e.get("es_nuevo_perfil") for e in ents) else "RECURRENCIA_LOTE",
                    },
                    "calificacion": {
                        "nota": next((e.get("notaNormalizada") for e in ents if e.get("label") == "CALIFICACIÓN"), None),
                        "estado": "Aprobado" if next((True for e in ents if e.get("label") == "CALIFICACIÓN" and "APROBADO" in str(e.get("canonicalId"))), True) else "Reprobado",
                    },
                    "docente": {
                        "nombre": next((e["matchedCanonical"] or e["token"] for e in ents if e.get("label") == "DOCENTE"), None)
                    },
                    "financiero": {
                        "monto_bs": next((e["token"] for e in ents if e.get("label") == "MONTO"), None),
                        "concepto": next((e["token"] for e in ents if e.get("label") == "CONCEPTO_FINANCIERO"), None),
                    },
                    "aprobado_dw": not req_rev and score >= UMBRAL_INDICE_REGISTRO_DEC,
                },
            })

    return {"status": "success", "total": len(items), "data": items}
