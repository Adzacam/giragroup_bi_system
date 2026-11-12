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
from services import cache_consultas
from services.extraccion_por_encabezado import campos_por_encabezado, registros_academicos
from datetime import datetime, timedelta
from services.revision_hechos import es_caso_hecho, resolver_caso_hecho
from core.database import get_db
from services.bandeja_grupos import ids_del_grupo, mapear_estado_grupo
from sqlalchemy import or_
from core.security import require_roles
from ._comun import AprobacionEnBloqueRequest, AprobarGrupoRequest, BatchResolveRequest
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
    page: int = Query(1, ge=1), page_size: int = Query(5, ge=1, le=5),
    search: Optional[str] = Query(None, max_length=200), area: Optional[str] = Query(None),
    vista: str = Query("PENDIENTES", pattern="^(PENDIENTES|RESUELTOS)$"),
    grupo: Optional[str] = Query(None, max_length=80), db: Session = Depends(get_db),
):
    from services import revision_consulta as revision
    valor = lambda v, tipo, defecto=None: v if isinstance(v, tipo) else defecto
    docs = revision.documentos(db, valor(id_lote, (str, int)), valor(doc_id, int))
    return revision.consultar(db, docs, valor(page, int, 1), valor(page_size, int, 5),
        valor(search, str, ''), valor(area, str), valor(motivo, str), valor(estado, str),
        valor(vista, str, 'PENDIENTES'), valor(grupo, str))


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
                res = resolve_review_item(item_id, {"accion": "APROBAR", "estudiante_resuelto": it.get("sugerencia"), 'aprobacion_en_bloque': True},
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
    for lote_id in sorted({d.id_lote for d in docs if d.id_lote}):
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


@router.patch("/review-tray/{item_id}/resolve")
@router.post("/review-tray/{item_id}/resolve")
def resolve_review_item(
    item_id: str,
    payload: Optional[dict] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """Aprueba y consolida un registro individual en la bandeja de revisión humana."""
    payload = dict(payload or {})
    for campo, minimo, maximo in (('nota_final', 0, 100), ('monto_deuda', 0, None), ('cuotas_impagas', 0, None), ('mes', 1, 12), ('gestion', 2000, 2100)):
        valor = payload.get(campo)
        if valor not in (None, ''):
            try:
                numero = float(valor)
                if not math.isfinite(numero) or numero < minimo or (maximo is not None and numero > maximo) or (campo in ('cuotas_impagas', 'mes', 'gestion') and not numero.is_integer()):
                    raise ValueError()
            except (ValueError, TypeError):
                raise HTTPException(422, 'Revisa los valores numéricos y la fecha de la corrección.')
            payload[campo] = int(numero) if campo in ('cuotas_impagas', 'mes', 'gestion') else numero
    if es_caso_hecho(item_id):
        from services.revision_hechos import _cargar
        if str(item_id).startswith('HECHO-EVA-'):
            doc_id = int(str(item_id).split('-')[2])
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
    clean_id = str(item_id).replace("REV-", "").strip()
    if clean_id.isdigit():
        previo = db.get(StagingEntidadNoResuelta, int(clean_id))
        if previo:
            _bloquear_documentos_editables(db, db.query(DimOrigenDocumental).filter_by(id_documento=previo.id_documento).all())
        # FOR UPDATE serializa dos resoluciones simultáneas del mismo caso hasta el commit de la primera
        ent = (
            db.query(StagingEntidadNoResuelta)
            .filter(StagingEntidadNoResuelta.id_staging == int(clean_id))
            .with_for_update()
            .first()
        )
        if ent:
            if ent.resuelto:
                db.rollback()
                raise HTTPException(status_code=409, detail=f"El registro {item_id} ya fue resuelto.")
            if (
                ent.lock_usuario_id
                and ent.lock_usuario_id != getattr(current_user, "id", None)
                and ent.lock_expira
                and ent.lock_expira > datetime.utcnow()
            ):
                db.rollback()
                raise HTTPException(status_code=409, detail="El registro está bloqueado por otro auditor.")
            from services.revision_consulta import presupuesto_manual, datos_payload
            doc_caso = db.query(DimOrigenDocumental).filter_by(id_documento=ent.id_documento).first()
            fila_presupuesto = presupuesto_manual(doc_caso, ent.texto_original) or presupuesto_manual(doc_caso, datos_payload(ent).get('raw_line'))
            if (payload.get('accion') or 'APROBAR').upper() != 'DESCARTAR' and fila_presupuesto:
                raise HTTPException(422, 'Esta fila de presupuesto requiere corregir su clasificación antes de aprobarla como persona.')
            user_name = current_user.username if (current_user and hasattr(current_user, "username")) else "Auditor Calidad"
            user_id = current_user.id if (current_user and hasattr(current_user, "id")) else None
            accion = (payload.get("accion") or "APROBAR").upper()
            if accion not in ('APROBAR', 'DESCARTAR'):
                raise HTTPException(422, 'Selecciona aprobar o descartar.')

            if "DESCARTAR" in accion:
                if not str(payload.get('motivo_descarte') or '').strip():
                    raise HTTPException(422, 'Escribe el motivo del descarte.')
                ent.resuelto = True
                ent.estado_resolucion = "DESCARTADO"
                ent.resuelto_en = datetime.now()
                if ent.registro_origen_id:
                    stg_parent = db.query(StagingRegistroCrudo).filter_by(id=ent.registro_origen_id).first()
                    if stg_parent:
                        stg_parent.resuelto = True
                        stg_parent.estado_resolucion = "DESCARTADO"
                db.commit()

                # Auditoría de descarte
                try:
                    audit_nlp = LogAuditoriaNlp(
                        texto_original=(ent.texto_original or "")[:500],
                        prediccion_beto=(ent.mejor_candidato or ent.tipo_entidad or "")[:200],
                        confianza_ia=float(ent.nivel_confianza or 0.70),
                        correccion_humana="Descartado",
                        usuario_auditor=user_id,
                    )
                    db.add(audit_nlp)
                    audit_pipe = LogPipelineIngesta(
                        id_documento=ent.id_documento,
                        etapa="HITL_RESOLUCION_INDIVIDUAL",
                        nivel="WARNING",
                        modulo="DataOps HITL",
                        mensaje=f"Registro {item_id} descartado por {user_name}.",
                        metadata_json={"item_id": item_id, "accion": "DESCARTAR", "usuario": user_name, "motivo": payload.get("motivo_descarte")}
                    )
                    db.add(audit_pipe)
                    db.commit()
                except Exception as e_desc_aud:
                    logger.warning("No se pudo auditar descarte de item %s: %s", item_id, e_desc_aud)

                if not payload.get('aprobacion_en_bloque'):
                    _notificar_revision(db, 'Caso descartado', 'El descarte y su motivo quedaron guardados en Revisión.')
                cache_consultas.invalidar()
                return {
                    "status": "success",
                    "message": f"Registro {item_id} descartado.",
                    "id": item_id,
                    "estado_resolucion": "DESCARTADO",
                }

            orig_doc = db.query(DimOrigenDocumental).filter_by(id_documento=ent.id_documento).first() if ent.id_documento else None
            doc_fuente = (orig_doc.tipo_fuente if orig_doc and orig_doc.tipo_fuente else "ACTA").upper()
            doc_escala = orig_doc.tipo_escala if orig_doc else "CENTESIMAL_100"
            p_json = ent.payload_json if isinstance(ent.payload_json, dict) else {}

            ci_corregida = payload.get("ci_corregida")
            if ci_corregida and '•' in str(ci_corregida):
                ci_corregida = None  # La máscara nunca debe guardarse como una cédula real.
            est_resuelto = payload.get("estudiante_resuelto") or payload.get("texto_editado") or p_json.get("estudiante")

            ci_raw = ci_corregida or ent.ci_temporal or p_json.get("ci_real")
            if not ci_raw or str(ci_raw).strip().lower() in ("no especificado", "no provisto", "none", "null", ""):
                ci_clean = f"TEMP-{ent.id_staging}"
            else:
                ci_clean = str(ci_raw).replace("?", "").strip()

            nom_clean = (est_resuelto or ent.texto_original or '').strip()
            if not nom_clean:
                raise HTTPException(422, 'Indica el nombre del estudiante antes de aprobar.')
            if len(nom_clean) > 200:  # el caso trae la línea completa como "nombre": el auditor debe escribir el nombre (antes: 500 por VARCHAR(200))
                db.rollback()
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="El caso trae la línea completa; indique el nombre del estudiante en texto_editado.")
            categoria_ruteo = (
                "financiero" if doc_fuente == "COBRANZA" else ("admision" if doc_fuente == "ADMISION" else "academico")
            )

            try:
                dw = DWLoaderService(db)
                base_registro = {
                    "categoria": categoria_ruteo,
                    "tipo_fuente": doc_fuente,
                    "tipo_escala": doc_escala,
                    "doc_id": ent.id_documento,
                    "calidad": {"requiere_revision": False, "resuelto_por_humano": True},
                }
                estudiante_res = {
                    "fk_resolucion": {"ci": ci_clean, "nombre_resuelto": nom_clean},
                    "valor_extraido": nom_clean,
                }
                # Acta con su línea original: un hecho por módulo con la nota real de la fila (como confirm-dw-insert).
                # Antes se cargaba un solo hecho "Módulo Académico" y, sin nota, se inventaba 75.
                linea_origen = p_json.get("raw_line") or (ent.texto_original if "|" in (ent.texto_original or "") else None)
                registros_acta = []
                if categoria_ruteo == "academico" and linea_origen and payload.get("nota_final") is None:
                    registros_acta = registros_academicos(campos_por_encabezado([c.strip() for c in linea_origen.split("|")]))
                if registros_acta:
                    res_load = {}
                    for reg_aca in registros_acta:
                        reg_aca.pop("requiere_revision", None)
                        res_load = dw.cargar_registro({**base_registro, "resoluciones": {
                            **{k: v for k, v in reg_aca.items() if v is not None or k in ("nota_final", "fecha")},
                            "estudiante": estudiante_res, "nivel_confianza_ia": 0.99,
                        }})
                        if res_load.get('status') != 'loaded':
                            raise RuntimeError('La corrección no pudo incorporarse.')
                else:
                    nota_payload = payload.get("nota_final")
                    res_load = dw.cargar_registro({**base_registro, "resoluciones": {
                        "estudiante": estudiante_res,
                        "modulo": {
                            "valor_extraido": payload.get("modulo_resuelto") or p_json.get("modulo") or "Módulo Académico"
                        },
                        "nota_final": nota_payload if nota_payload not in (None, "") else p_json.get("nota_normalizada"),
                        "monto_deuda": payload.get("monto_deuda") if payload.get("monto_deuda") is not None else p_json.get("monto_deuda"),
                        "cuotas_impagas": payload.get("cuotas_impagas") if payload.get("cuotas_impagas") is not None else (p_json.get("cuotas_impagas") or 0),
                        "nivel_confianza_ia": 0.99,
                    }})
                    if res_load.get('status') != 'loaded':
                        raise RuntimeError('La corrección no pudo incorporarse.')
                ent.id_dimension_resuelta = res_load.get("id_estudiante")
            except Exception as e_res:
                db.rollback()
                logger.exception("No se pudo guardar el caso %s", item_id)
                raise HTTPException(503, 'No se pudo guardar el caso. Continúa pendiente; inténtalo de nuevo.') from e_res

            ent.resuelto = True
            ent.estado_resolucion = "RESUELTO_HUMANO"
            ent.resuelto_en = datetime.now()
            if ent.registro_origen_id:
                stg_parent = db.query(StagingRegistroCrudo).filter_by(id=ent.registro_origen_id).first()
                if stg_parent:
                    stg_parent.resuelto = True
                    stg_parent.estado_resolucion = "RESUELTO_HUMANO"
                    stg_parent.resuelto_en = datetime.now()
            db.commit()

            # Auditoría en LogAuditoriaNlp, LogPipelineIngesta y notificación
            try:
                audit_nlp = LogAuditoriaNlp(
                    texto_original=(ent.texto_original or "")[:500],
                    prediccion_beto=(ent.mejor_candidato or ent.tipo_entidad or "")[:200],
                    confianza_ia=float(ent.nivel_confianza or 0.70),
                    correccion_humana=nom_clean[:200],
                    usuario_auditor=user_id,
                )
                db.add(audit_nlp)

                audit_pipe = LogPipelineIngesta(
                    id_documento=ent.id_documento,
                    etapa="HITL_RESOLUCION_INDIVIDUAL",
                    nivel="INFO",
                    modulo="DataOps HITL",
                    mensaje=f"Registro {item_id} resuelto y consolidado en el DW por {user_name}: {nom_clean}.",
                    metadata_json={
                        "item_id": item_id,
                        "accion": "APROBAR",
                        "usuario": user_name,
                        "ci": ci_clean,
                        "nombre": nom_clean,
                        "modulo": payload.get("modulo_resuelto"),
                    }
                )
                db.add(audit_pipe)
                db.commit()

                if not payload.get('aprobacion_en_bloque'):
                    _notificar_revision(db, 'Caso revisado', 'La corrección quedó guardada. Abre Revisión para consultar el resultado.',
                                        orig_doc.id_lote if orig_doc else None)
            except Exception as e_aud_ind:
                logger.warning("No se pudo registrar auditoría de resolución individual: %s", e_aud_ind)

    if not clean_id.isdigit() or not ent:
        raise HTTPException(404, 'El caso no existe.')
    cache_consultas.invalidar()
    return {
        "status": "success",
        "message": f"Registro {item_id} aprobado y consolidado en el Data Warehouse.",
        "id": item_id,
        "resolved_at": datetime.now().isoformat(),
    }


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
