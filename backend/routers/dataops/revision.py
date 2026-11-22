"""Paso ④: bandeja de revisión humana, grupos, resoluciones y bloqueos."""
import logging
import math
from fastapi import APIRouter, Depends, HTTPException, Query, status
from services.dw_loader import DWLoaderService
from models.dim_origen import DimOrigenDocumental
from models.log_auditoria_nlp import LogAuditoriaNlp
from models.log_pipeline import LogPipelineIngesta
from models.lote import Lote
from services.notification_service import NotificationService
from typing import Optional
from sqlalchemy.orm import Session
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from models.user import User
from services.cronometraje import ahora, registrar_aprobacion
from services import cache_consultas, encuesta_canonica
from services.extraccion_por_encabezado import (
    campos_por_encabezado,
    fecha_de_fila,
    metricas_captacion,
    registros_academicos,
    registros_costo_programa,
    registros_evaluacion,
    registros_rentabilidad,
    registros_techo_convenio,
)
from datetime import date, datetime, timedelta
from services.revision_formularios import validar_payload_correccion
from services.revision_hechos import es_caso_hecho, resolver_caso_hecho
from core.database import get_db
from services.bandeja_grupos import ids_del_grupo, mapear_estado_grupo
from sqlalchemy import or_
from core.security import require_roles
from ._comun import AprobacionEnBloqueRequest, AprobarGrupoRequest, BatchResolveRequest, categoria_ruteo as resolver_categoria_ruteo
from .evaluacion import _asegurar_lote_editable

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# BANDEJA DE REVISIÓN HUMANA (PASO ④) CON FUENTE ÚNICA Y CI ENMASCARADO (#12, #13)
# =============================================================================

@router.get("/review-tray")
def get_review_tray(
    doc_id: Optional[int] = Query(None), id_lote: Optional[str] = Query(None),
    motivo: Optional[str] = Query(None), estado: Optional[str] = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50),
    search: Optional[str] = Query(None, max_length=200), area: Optional[str] = Query(None),
    vista: str = Query("PENDIENTES", pattern="^(PENDIENTES|RESUELTOS)$"),
    grupo: Optional[str] = Query(None, max_length=80),
    rol: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    from services import revision_consulta as revision
    valor = lambda v, tipo, defecto=None: v if isinstance(v, tipo) else defecto
    docs = revision.documentos(db, valor(id_lote, (str, int)), valor(doc_id, int))
    return revision.consultar(db, docs, valor(page, int, 1), valor(page_size, int, 20),
        valor(search, str, ''), valor(area, str), valor(motivo, str), valor(estado, str),
        valor(vista, str, 'PENDIENTES'), valor(grupo, str), rol_usuario=valor(rol, str) or "AUDITOR_CALIDAD")


@router.get("/review-tray/avisos")
def get_review_tray_avisos(
    doc_id: Optional[int] = Query(None),
    id_lote: Optional[str] = Query(None),
    estado: str = Query("PENDIENTE", pattern="^(PENDIENTE|RESUELTO_HUMANO|DESCARTADO|TODOS)$"),
    rol: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Expone los avisos de `log_inconsistencias` para revisión accionable en la bandeja (DF-L2 c)."""
    from services import revision_consulta as revision
    from services.revision_acciones_ejecutor import consultar_avisos
    docs = revision.documentos(db, id_lote, doc_id) if (id_lote is not None or doc_id is not None) else []
    doc_ids = [d.id_documento for d in docs]
    return consultar_avisos(db, doc_ids, estado=estado, rol_usuario=rol or "AUDITOR_CALIDAD")


@router.post("/review-tray/avisos/{aviso_id}/resolver")
def resolve_review_tray_aviso(
    aviso_id: int,
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    from services.revision_acciones_ejecutor import resolver_aviso
    user_name = getattr(current_user, "username", None) or "Auditor Calidad"
    user_role = getattr(current_user, "role", None) or "AUDITOR_CALIDAD"
    res = resolver_aviso(db, aviso_id, dict(payload or {}), user_name, user_role)
    cache_consultas.invalidar()
    return res


@router.post("/review-tray/{item_id}/reabrir")
def reopen_review_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """Reabre un caso resuelto mientras el lote no esté consolidado (DF-L2 d / DD2)."""
    from services.revision_acciones_ejecutor import reabrir_caso
    user_name = getattr(current_user, "username", None) or "Auditor Calidad"
    res = reabrir_caso(db, item_id, user_name)
    cache_consultas.invalidar()
    return res


@router.get("/review-tray/motivos")
def get_review_tray_motivos():
    """Catálogo público de motivos de revisión humana y su clasificación (accionable vs informativo)."""
    from services.bandeja_grupos import EXPLICACION_MOTIVOS, MOTIVOS_INFORMATIVOS
    from services.revision_consulta import MOTIVOS
    return {
        "motivos": [
            {
                "codigo": codigo,
                "etiqueta": etiqueta,
                "informativo": codigo in MOTIVOS_INFORMATIVOS,
                "en_bandeja_pendiente": codigo not in MOTIVOS_INFORMATIVOS,
                "regla": EXPLICACION_MOTIVOS.get(codigo, ("Regla de validación DataOps", ""))[0],
                "umbral": EXPLICACION_MOTIVOS.get(codigo, ("", "Cumplimiento de catálogo y esquema"))[1],
            }
            for codigo, etiqueta in sorted(MOTIVOS.items())
        ]
    }


@router.get("/review-tray/grupos")
def get_review_tray_groups(
    doc_id: Optional[int] = Query(None), id_lote: Optional[str] = Query(None),
    page: int = Query(1, ge=1), search: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db),
):
    from services import revision_consulta as revision
    docs = revision.documentos(db, id_lote if isinstance(id_lote, (str, int)) else None,
                               doc_id if isinstance(doc_id, int) else None)
    return revision.grupos_publicos(db, docs, page if isinstance(page, int) else 1,
                                    search if isinstance(search, str) else '')


@router.get("/review-tray/export")
def export_review_tray(id_lote: str, doc_id: Optional[int] = None,
                       search: str = Query('', max_length=200), area: Optional[str] = None,
                       vista: str = Query('PENDIENTES', pattern='^(PENDIENTES|RESUELTOS)$'),
                       grupo: Optional[str] = None, db: Session = Depends(get_db)):
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from services import revision_consulta as revision
    docs = revision.documentos(db, id_lote, doc_id)
    ids_grupo = set(str(i) for i in ids_del_grupo(db, revision.clave_interna(db, grupo, [d.id_documento for d in docs]), [d.id_documento for d in docs])) if grupo else None
    def filas():
        salida = io.StringIO()
        escritor = csv.writer(salida, delimiter=';')
        def fila(valores):
            salida.seek(0)
            salida.truncate(0)
            # Evita fórmulas al abrir el archivo en una hoja de cálculo.
            escritor.writerow([("'" + str(v)) if str(v).lstrip().startswith(('=', '+', '-', '@')) else v for v in valores])
            return salida.getvalue()
        yield '\ufeff' + fila(['Caso', 'Área', 'Motivo', 'Estudiante', 'Cédula protegida', 'Módulo', 'Archivo', 'Texto', 'Estado'])
        for caso, clave in revision.iterar_casos(db, docs, vista == 'RESUELTOS'):
            if ids_grupo is not None and str(caso['id']) not in ids_grupo:
                continue
            if revision.coincide(caso, search, area):
                yield fila([caso.get(k) if caso.get(k) is not None else '' for k in
                    ('id', 'area', 'motivo_label', 'estudiante', 'ci_enmascarado', 'modulo_detectado', 'archivo_origen', 'que_vio', 'estado_resolucion')])
    return StreamingResponse(filas(), media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="incidencias.csv"'})


@router.post("/review-tray/approve-group")
def approve_review_group(
    payload: AprobarGrupoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """Aprueba todos los casos pendientes de un grupo (misma resolución en lote que /batch-resolve)."""
    t_ini = ahora()
    res = _aprobar_grupo(payload, db, current_user)
    registrar_aprobacion("approve-group" + ("/" + payload.accion if payload.accion else ""), t_ini,
                         {"clave": payload.clave, "casos": res.get("casos_del_grupo"), "resueltos": res.get("resolved_count")},
                         getattr(current_user, "username", None))
    if res.get('resolved_count'):
        _notificar_revision(db, 'Grupo revisado', f"{res['resolved_count']} casos guardados. Abre Revisión para consultar el resultado.")
    return res


def _aprobar_grupo(payload: AprobarGrupoRequest, db: Session, current_user: User):
    from services import revision_consulta as revision
    alcance = payload.doc_ids if payload.doc_ids is not None else ([payload.doc_id] if payload.doc_id is not None else None)
    docs = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento.in_(alcance)).all() if alcance is not None else db.query(DimOrigenDocumental).all()
    _bloquear_documentos_editables(db, docs)
    payload.clave = revision.clave_interna(db, payload.clave, alcance)
    ids = ids_del_grupo(db, payload.clave, alcance)
    if not ids:
        return {"status": "success", "resolved_count": 0, "message": "El grupo no tiene casos pendientes."}
    if payload.clave.startswith("HECHO_EN_REVISION::") and (payload.accion or "").upper() == "MAPEAR_ESTADO":
        if '|falta:ninguno|' not in payload.clave:
            raise HTTPException(422, 'Completa los datos obligatorios de los casos antes de aprobar el estado del grupo.')
        res_m = mapear_estado_grupo(db, payload.clave, alcance, payload.canonico)
        return {"status": "success", "resolved_count": res_m["mapeados"], "casos_del_grupo": len(ids), "grupo": payload.clave, **res_m}
    if payload.clave.startswith("HECHO_EN_REVISION::"):
        # Hechos ya cargados: el grupo se aprueba sin cambios solo si no les falta ningún campo (si falta, se corrigen uno a uno)
        solo_fecha = "|falta:fecha" in payload.clave and payload.mes and payload.gestion
        if ("|falta:ninguno" not in payload.clave and not solo_fecha) or ("|estado:" in payload.clave and "|estado:OK" not in payload.clave):
            return {"status": "error", "resolved_count": 0, "message": "Al grupo le faltan campos: hay que corregirlo caso por caso."}
        correccion = {"mes": payload.mes, "gestion": payload.gestion} if solo_fecha else {}
        n_ok = sum(1 for i in ids if resolver_caso_hecho(db, str(i), {"accion": "APROBAR", "aprobacion_en_bloque": True, **correccion},
                   user_id=getattr(current_user, "id", None), user_name=getattr(current_user, "username", None) or "Auditor Calidad")["status"] == "success")
        return {"status": "success", "resolved_count": n_ok, "casos_del_grupo": len(ids), "grupo": payload.clave}
    res = batch_resolve_review_items(
        BatchResolveRequest(item_ids=[str(i) for i in ids], estudiante_resuelto=payload.estudiante_resuelto),
        db=db, current_user=current_user)
    res["grupo"] = payload.clave
    res["casos_del_grupo"] = len(ids)
    return res


@router.post("/review-tray/batch-resolve")
def batch_resolve_review_items(
    payload: BatchResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """Resuelve y consolida en lote múltiples casos de la bandeja de revisión humana."""
    # Una sola implementación de validación, auditoría e idempotencia por caso.
    resolved_count = 0
    for item_id in dict.fromkeys(payload.item_ids):
        datos = payload.model_dump(exclude_none=True)
        datos['accion'] = 'APROBAR'
        datos['aprobacion_en_bloque'] = True
        res = resolve_review_item(str(item_id), datos, db=db, current_user=current_user)
        if res.get('status') == 'success':
            resolved_count += 1
    if resolved_count:
        _notificar_revision(db, 'Aprobación en bloque terminada', f'{resolved_count} casos guardados. Abre Revisión para consultar el resultado.')
    return {'status': 'success', 'resolved_count': resolved_count,
            'message': f'{resolved_count} casos aprobados.'}


@router.post("/review-tray/aprobar-un-clic")
def aprobar_casos_un_clic(
    payload: AprobacionEnBloqueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """
    Aprueba en bloque los casos pendientes de un clic (candidato que coincide por nombre, token_sort >= 0,85,
    o hecho sin campos faltantes). Exige confirmar = true. Cada caso queda en la bitácora con el usuario y la
    acción "aprobación en bloque"; los casos manuales siguen en la bandeja.
    """
    if not payload.confirmar:
        raise HTTPException(status_code=400, detail="Confirme la aprobación en bloque (confirmar = true).")
    from services import revision_consulta as revision
    docs = revision.documentos(db, payload.id_lote, payload.doc_id)
    _bloquear_documentos_editables(db, docs)
    # Se recorren resultados guardados en bloques; no se obtiene una respuesta gigante ni se llama a BETO.
    casos = []
    total = 0
    for it, _ in revision.iterar_casos(db, docs):
        total += 1
        if it.get('un_clic'):
            casos.append(it)
    user_name = getattr(current_user, "username", None) or "Auditor Calidad"
    user_id = getattr(current_user, "id", None)
    aprobados, fallidos = [], []
    for it in casos:
        item_id = str(it["id"])
        try:
            if es_caso_hecho(item_id):
                res = resolver_caso_hecho(db, item_id, {"accion": "APROBAR", "aprobacion_en_bloque": True},
                                          user_id=user_id, user_name=user_name)
            else:
                nombres_campos = {c.get("name") for c in (it.get("campos_correccion") or [])}
                payload_un_clic = {"accion": "APROBAR", "aprobacion_en_bloque": True}
                if (not nombres_campos or "nombre_completo" in nombres_campos) and it.get("sugerencia"):
                    payload_un_clic["estudiante_resuelto"] = it.get("sugerencia")
                res = resolve_review_item(item_id, payload_un_clic,
                                          db=db, current_user=current_user)
                db.add(LogPipelineIngesta(
                    id_documento=it.get("id_documento"), etapa="HITL_APROBACION_EN_BLOQUE", nivel="SUCCESS",
                    modulo="Bandeja HITL", mensaje=f"{user_name} aprobó {item_id} en bloque: {it.get('sugerencia')}.",
                    metadata_json={"item_id": item_id, "accion": "APROBACION_EN_BLOQUE", "usuario": user_name},
                ))
                db.commit()
            (aprobados if (res or {}).get("status") != "error" else fallidos).append(item_id)
        except Exception as e_bloque:
            db.rollback()
            fallidos.append(item_id)
            logger.warning("Aprobación en bloque: no se pudo aprobar %s: %s", item_id, e_bloque)
    cache_consultas.invalidar()
    if aprobados:
        _notificar_revision(db, 'Aprobación en bloque terminada', f'{len(aprobados)} casos guardados; {total - len(aprobados)} siguen pendientes.')
    return {
        "status": "success",
        "aprobados": len(aprobados),
        "fallidos": fallidos,
        "manuales_pendientes": total - len(aprobados),
        "message": f"{len(aprobados)} casos aprobados; {total - len(aprobados)} siguen pendientes.",
    }


def _bloquear_documentos_editables(db, docs):
    for lote_id in sorted({getattr(d, "id_lote", None) for d in docs if getattr(d, "id_lote", None)}):
        db.query(Lote).filter_by(id_lote=lote_id).with_for_update().first()
        _asegurar_lote_editable(db, lote_id)


def _notificar_revision(db, titulo, mensaje, id_lote=None):
    try:
        for rol in ('ADMIN', 'AUDITOR_CALIDAD'):
            NotificationService.create_notification(db=db, title=titulo, message=mensaje,
                category='DataOps', severity='SUCCESS', role_target=rol,
                link=f'/dataops/lote/{id_lote}/revision' if id_lote else '/dataops/revision')
    except Exception:
        db.rollback()
        logger.exception('No se pudo guardar el aviso de revisión')


def _resolver_hecho_en_bandeja(db: Session, item_id: str, payload: dict, current_user: User) -> dict:
    from services.revision_hechos import _cargar
    if str(item_id).startswith('HECHO-EVA-'):
        doc_id, hecho = int(str(item_id).split('-')[2]), None
    else:
        hecho, _ = _cargar(db, item_id)
        doc_id = hecho.id_documento if hecho else None
    if doc_id:
        _bloquear_documentos_editables(db, db.query(DimOrigenDocumental).filter_by(id_documento=doc_id).all())
    pendiente_antes = bool(hecho.requiere_revision) if not str(item_id).startswith('HECHO-EVA-') and hecho else True
    resultado = resolver_caso_hecho(
        db, str(item_id), payload,
        user_id=getattr(current_user, "id", None),
        user_name=getattr(current_user, "username", None) or "Auditor Calidad",
    )
    if pendiente_antes and resultado.get('status') == 'success' and not payload.get('aprobacion_en_bloque'):
        _notificar_revision(db, 'Caso revisado', 'La corrección quedó guardada. Abre Revisión para consultar el resultado.')
    cache_consultas.invalidar()
    return resultado


@router.patch("/review-tray/{item_id}/resolve")
@router.post("/review-tray/{item_id}/resolve")
def resolve_review_item(
    item_id: str,
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """Aprueba y consolida un registro individual en la bandeja de revisión humana."""
    from services.revision_acciones_ejecutor import (
        ejecutar_accion_contextual,
        resolver_entidad_legacy,
        validar_numericos_payload,
    )
    payload = validar_numericos_payload(dict(payload or {}))
    if es_caso_hecho(item_id):
        return _resolver_hecho_en_bandeja(db, item_id, payload, current_user)
    clean_id = str(item_id).replace("REV-", "").strip()
    if not clean_id.isdigit():
        raise HTTPException(404, 'El caso no existe.')
    previo = db.get(StagingEntidadNoResuelta, int(clean_id))
    if previo:
        _bloquear_documentos_editables(db, db.query(DimOrigenDocumental).filter_by(id_documento=previo.id_documento).all())
    ent = (
        db.query(StagingEntidadNoResuelta)
        .filter(StagingEntidadNoResuelta.id_staging == int(clean_id))
        .with_for_update()
        .first()
    )
    if not ent:
        raise HTTPException(404, 'El caso no existe.')
    if ent.resuelto:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"El registro {item_id} ya fue resuelto.")
    if ent.lock_usuario_id and ent.lock_usuario_id != getattr(current_user, "id", None) and ent.lock_expira and ent.lock_expira > datetime.utcnow():
        db.rollback()
        raise HTTPException(status_code=409, detail="El registro está bloqueado por otro auditor.")
    user_name = getattr(current_user, "username", None) or "Auditor Calidad"
    user_role = getattr(current_user, "role", None) or "AUDITOR_CALIDAD"
    accion = (payload.get("accion") or "APROBAR").upper()
    if accion not in ('APROBAR', 'DESCARTAR'):
        res_ctx = ejecutar_accion_contextual(db, ent, payload, user_name, user_role)
        cache_consultas.invalidar()
        return res_ctx
    return resolver_entidad_legacy(
        db, ent, item_id, payload, current_user,
        dw_loader_cls=DWLoaderService, notificar_cb=_notificar_revision,
    )


@router.post("/review-tray/{item_id}/lock")
def lock_review_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"])),
):
    ahora = datetime.utcnow()
    expira = ahora + timedelta(minutes=5)
    # Comprobar y tomar el bloqueo en un único UPDATE condicional: dos auditores simultáneos
    # no pueden ganar ambos (la lectura previa + escritura permitía la carrera).
    tomado = (
        db.query(StagingEntidadNoResuelta)
        .filter(
            StagingEntidadNoResuelta.id_staging == item_id,
            or_(
                StagingEntidadNoResuelta.lock_usuario_id.is_(None),
                StagingEntidadNoResuelta.lock_usuario_id == current_user.id,
                StagingEntidadNoResuelta.lock_expira.is_(None),
                StagingEntidadNoResuelta.lock_expira <= ahora,
            ),
        )
        .update({"lock_usuario_id": current_user.id, "lock_expira": expira}, synchronize_session=False)
    )
    db.commit()

    if not tomado:
        item = db.query(StagingEntidadNoResuelta).filter(StagingEntidadNoResuelta.id_staging == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Registro no encontrado.")
        usuario_bloqueador = db.query(User).filter(User.id == item.lock_usuario_id).first()
        nombre_u = usuario_bloqueador.username if usuario_bloqueador else f"Usuario #{item.lock_usuario_id}"
        segundos = max(0, int((item.lock_expira - ahora).total_seconds())) if item.lock_expira else 0
        raise HTTPException(
            status_code=409,
            detail=f"El registro está siendo revisado por {nombre_u}. Bloqueo expira en {segundos}s.",
        )

    return {
        "status": "success",
        "message": "Bloqueo pesimista adquirido correctamente (5 min)",
        "item_id": item_id,
        "lock_expira": expira.isoformat(),
    }


@router.post("/review-tray/{item_id}/unlock")
def unlock_review_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"])),
):
    item = db.query(StagingEntidadNoResuelta).filter(StagingEntidadNoResuelta.id_staging == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")

    if item.lock_usuario_id == current_user.id or (current_user.role or "").upper() == "ADMIN":
        item.lock_usuario_id = None
        item.lock_expira = None
        db.commit()

    return {"status": "success", "message": "Bloqueo liberado."}
