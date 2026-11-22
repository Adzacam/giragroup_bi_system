"""
backend/services/revision_acciones_ejecutor.py
--------------------------------------------
Ejecución modular de acciones contextuales de revisión humana (DF-L2 / DD2 / DF-L8):
- Despacha cada acción de `acciones[]` con auditoría completa (usuario, fecha, valor_anterior, valor_nuevo).
- Soporta `reabrir` mientras el lote no esté consolidado, deshaciendo perfiles C, módulos o sinónimos creados.
- Expone y resuelve los avisos de `log_inconsistencias` (`/review-tray/avisos`).
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.log_auditoria_nlp import LogAuditoriaNlp
from models.log_inconsistencia import LogInconsistencia
from models.log_pipeline import LogPipelineIngesta
from models.lote import Lote
from models.staging_entidad import StagingEntidadNoResuelta
from services.revision_acciones_descriptor import construir_acciones

logger = logging.getLogger(__name__)


def _asegurar_no_consolidado(db: Session, id_documento: Optional[int]) -> None:
    if not id_documento:
        return
    doc = db.query(DimOrigenDocumental).filter_by(id_documento=id_documento).first()
    if doc and doc.id_lote:
        lote = db.query(Lote).filter_by(id_lote=doc.id_lote).first()
        if lote and lote.estado == "CONSOLIDADO":
            raise HTTPException(409, "El lote ya está consolidado; no se puede modificar ni reabrir el caso.")


def _registrar_auditoria(
    db: Session,
    *,
    id_documento: Optional[int],
    accion: str,
    usuario: str,
    valor_anterior: Any,
    valor_nuevo: Any,
    origen_caso: str,
    user_id: Optional[int] = None,
) -> None:
    try:
        es_bloque = isinstance(valor_nuevo, dict) and valor_nuevo.get("estado_resolucion") == "APROBACION_BLOQUE"
        db.add(
            LogAuditoriaNlp(
                texto_original=f"{origen_caso}: {str(valor_anterior)[:420]}",
                prediccion_beto=str(accion)[:200],
                confianza_ia=1.0,
                correccion_humana="APROBACION_BLOQUE" if es_bloque else str(valor_nuevo)[:200],
                usuario_auditor=user_id,
            )
        )
        db.add(
            LogPipelineIngesta(
                id_documento=id_documento,
                etapa="HITL_APROBACION_EN_BLOQUE" if es_bloque else "HITL_RESOLUCION_INDIVIDUAL",
                nivel="INFO",
                modulo="DataOps HITL",
                mensaje=f"{usuario} ejecutó {accion} en {origen_caso}.",
                metadata_json={
                    "origen": origen_caso,
                    "accion": accion,
                    "usuario": usuario,
                    "valor_anterior": valor_anterior,
                    "valor_nuevo": valor_nuevo,
                    "fecha": datetime.utcnow().isoformat(),
                },
            )
        )
    except Exception as exc:
        logger.warning("No se pudo registrar auditoría para %s: %s", origen_caso, exc)


def _registrar_sinonimo_catalogo(valor_recibido: str, valor_canonico: str, campo_objetivo: str = "modulo") -> Optional[Dict[str, Any]]:
    """Persiste un sinónimo en el catálogo (PostgreSQL catalog_db o en memoria) para que futuras cargas lo resuelvan."""
    if not valor_recibido or not valor_canonico:
        return None
    try:
        from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio
        repo = obtener_catalogo_repositorio()
        if hasattr(repo, "registrar_sinonimo"):
            repo.registrar_sinonimo(valor_recibido, valor_canonico, campo_objetivo)
    except Exception:
        pass
    try:
        from core.database import engine_catalog
        if engine_catalog is not None:
            with engine_catalog.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO public.cat_mapeo_columna (columna_origen, campo_canonico, activo) "
                        "VALUES (:orig, :can, TRUE) ON CONFLICT DO NOTHING"
                    ),
                    {"orig": str(valor_recibido)[:150], "can": str(valor_canonico)[:150]},
                )
    except Exception as exc:
        logger.debug("cat_mapeo_columna opcional no disponible: %s", exc)
    return {"valor_recibido": str(valor_recibido), "valor_canonico": str(valor_canonico), "campo": campo_objetivo}


def _deshacer_sinonimo_catalogo(info: Dict[str, Any]) -> None:
    if not isinstance(info, dict):
        return
    try:
        from core.database import engine_catalog
        if engine_catalog is not None:
            with engine_catalog.begin() as conn:
                conn.execute(
                    text(
                        "DELETE FROM public.cat_mapeo_columna WHERE columna_origen = :orig AND campo_canonico = :can"
                    ),
                    {"orig": str(info.get("valor_recibido", ""))[:150], "can": str(info.get("valor_canonico", ""))[:150]},
                )
    except Exception as exc:
        logger.debug("No se pudo revertir cat_mapeo_columna: %s", exc)


def ejecutar_accion_contextual(
    db: Session,
    ent: StagingEntidadNoResuelta,
    payload: Dict[str, Any],
    user_name: str,
    user_role: str,
) -> Dict[str, Any]:
    """Ejecuta acciones específicas de DF-L2 sobre StagingEntidadNoResuelta."""
    accion = str(payload.get("accion") or "").strip().upper()
    rol = (user_role or "").strip().upper()
    if accion in ("CREAR_PERFIL_C", "CREAR_MODULO") and rol not in ("ADMIN", "AUDITOR_CALIDAD"):
        raise HTTPException(403, "Solo ADMIN o AUDITOR_CALIDAD pueden crear perfiles o módulos.")
    if accion == "CAMBIAR_FUENTE_PRIORITARIA" and rol != "ADMIN":
        raise HTTPException(403, "Solo ADMIN puede cambiar la regla de fuente prioritaria.")

    _asegurar_no_consolidado(db, ent.id_documento)
    p = dict(ent.payload_json or {}) if isinstance(ent.payload_json, dict) else {}
    valor_anterior = {
        "estado_resolucion": ent.estado_resolucion,
        "mejor_candidato": ent.mejor_candidato,
        "ci_temporal": ent.ci_temporal,
    }
    creado_undo: Dict[str, Any] = {}
    es_bloque = bool(payload.get("aprobacion_en_bloque"))

    if accion in ("DESCARTAR", "DESCARTAR_VACIA", "MARCAR_SIN_DATO", "MARCAR_SIN_RESPUESTA", "ANULAR_VALOR", "MARCAR_INASISTENCIA"):
        ent.resuelto = True
        ent.estado_resolucion = "APROBACION_BLOQUE" if es_bloque else "DESCARTADO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = accion
        p["motivo_descarte"] = payload.get("motivo_descarte") or payload.get("justificacion") or accion
    elif accion == "REGISTRAR_VARIANTE":
        ent.resuelto = True
        ent.estado_resolucion = "APROBACION_BLOQUE" if es_bloque else "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = "REGISTRAR_VARIANTE"
    elif accion == "ACTUALIZAR_NOMBRE_PADRON":
        nuevo_nombre = (payload.get("nombre_completo") or "").strip()
        if not nuevo_nombre:
            raise HTTPException(422, "Indica el nuevo nombre para el padrón.")
        if ent.ci_temporal:
            est = db.query(DimEstudiante).filter(
                (DimEstudiante.ci == ent.ci_temporal) | (DimEstudiante.ci_numero == ent.ci_temporal)
            ).first()
            if est:
                creado_undo["nombre_padron_anterior"] = est.nombre_completo
                creado_undo["id_estudiante_actualizado"] = est.id_estudiante
                est.nombre_completo = nuevo_nombre
        ent.mejor_candidato = nuevo_nombre
        ent.resuelto = True
        ent.estado_resolucion = "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = accion
    elif accion in ("VINCULAR_CANDIDATO", "VINCULAR_PERSONA"):
        id_cand = payload.get("id_estudiante_candidato")
        if not id_cand:
            raise HTTPException(422, "Selecciona un candidato o persona del padrón.")
        est = db.query(DimEstudiante).filter(DimEstudiante.id_estudiante == int(id_cand)).first()
        if not est:
            raise HTTPException(404, "La persona seleccionada no existe en el padrón.")
        est_ci = est.ci or est.ci_numero
        ent.mejor_candidato = est.nombre_completo
        ent.ci_temporal = est_ci or ent.ci_temporal
        ent.fk_estado = "A" if est_ci else "B"
        ent.resuelto = True
        ent.estado_resolucion = "APROBACION_BLOQUE" if es_bloque else "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["id_estudiante_vinculado"] = est.id_estudiante
        p["accion_aplicada"] = accion
    elif accion == "CREAR_PERFIL_C":
        nombre = (payload.get("nombre_completo") or "").strip()
        if not nombre:
            raise HTTPException(422, "Indica el nombre completo para crear el perfil.")
        ci_opt = (payload.get("ci_opcional") or "").strip() or None
        nuevo_est = DimEstudiante(
            nombre_completo=nombre,
            ci=ci_opt,
            ci_numero=ci_opt,
            fk_estado="C",
        )
        db.add(nuevo_est)
        db.flush()
        creado_undo["id_estudiante_creado"] = nuevo_est.id_estudiante
        ent.mejor_candidato = nombre
        ent.fk_estado = "C"
        ent.resuelto = True
        ent.estado_resolucion = "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["id_estudiante_creado"] = nuevo_est.id_estudiante
        p["accion_aplicada"] = accion
    elif accion == "PERFIL_TEMP_B":
        ent.fk_estado = "B"
        ent.resuelto = True
        ent.estado_resolucion = "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = accion
    elif accion == "CORREGIR_CI":
        ci_num = (payload.get("ci_corregido") or payload.get("ci_numero") or "").strip()
        ci_comp = (payload.get("ci_complemento") or "").strip()
        if not ci_num or len(ci_num) < 4:
            raise HTTPException(422, "Ingresa un número de CI válido.")
        ci_final = f"{ci_num} {ci_comp}".strip()
        ent.ci_temporal = ci_final
        p["ci_real"] = ci_final
        ent.resuelto = True
        ent.estado_resolucion = "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = accion
    elif accion == "CREAR_MODULO":
        cod_pos = (payload.get("codigo_pos") or "").strip()
        nom_mod = (payload.get("modulo_resuelto") or "").strip()
        prog = (payload.get("programa_resuelto") or "").strip()
        if not cod_pos or not nom_mod:
            raise HTTPException(422, "Código POS y nombre de módulo son obligatorios.")
        nuevo_mod = DimModulo(pos_code=cod_pos, nombre_modulo=nom_mod, programa=prog or None)
        db.add(nuevo_mod)
        db.flush()
        creado_undo["id_modulo_creado"] = nuevo_mod.id_modulo
        p["modulo"] = nom_mod
        p["codigo_pos"] = cod_pos
        p["programa"] = prog
        ent.resuelto = True
        ent.estado_resolucion = "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = accion
    elif accion == "VINCULAR_MODULO":
        id_mod = payload.get("id_modulo_destino")
        if not id_mod:
            raise HTTPException(422, "Selecciona un módulo existente.")
        mod = db.query(DimModulo).filter(DimModulo.id_modulo == int(id_mod)).first()
        if not mod:
            raise HTTPException(404, "El módulo seleccionado no existe.")
        p["modulo"] = mod.nombre_modulo
        p["id_modulo_vinculado"] = mod.id_modulo
        ent.resuelto = True
        ent.estado_resolucion = "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = accion
    elif accion == "ASIGNAR_CANONICO":
        canon = (payload.get("valor_canonico") or "").strip()
        if not canon:
            raise HTTPException(422, "Indica el valor canónico.")
        p["valor_canonico"] = canon
        if payload.get("recordar_sinonimo"):
            if rol not in ("ADMIN", "AUDITOR_CALIDAD"):
                raise HTTPException(403, "Solo ADMIN o AUDITOR_CALIDAD pueden guardar sinónimos en el catálogo.")
            orig = p.get("valor_recibido") or ent.texto_original or ""
            sin_info = _registrar_sinonimo_catalogo(orig, canon)
            if sin_info:
                creado_undo["sinonimo"] = sin_info
        ent.resuelto = True
        ent.estado_resolucion = "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = accion
    else:
        # CONFIRMAR_ENTIDADES, CORREGIR_ENTIDAD, COMPLETAR_DATOS, MOVER_A_PREGUNTA, CORREGIR_VALOR, CAMBIAR_FUENTE_PRIORITARIA
        for k in ("modulo_resuelto", "nota_final", "valor_corregido", "pregunta_destino", "entidad_tipo", "entidad_texto", "fuente_prioritaria"):
            if payload.get(k) not in (None, ""):
                p[k] = payload[k]
        ent.resuelto = True
        ent.estado_resolucion = "APROBACION_BLOQUE" if es_bloque else "RESUELTO_HUMANO"
        ent.resuelto_en = datetime.utcnow()
        p["accion_aplicada"] = accion or "APROBAR"

    if creado_undo:
        p["_undo"] = creado_undo
    p["_prev_state"] = valor_anterior
    ent.payload_json = p
    _registrar_auditoria(
        db,
        id_documento=ent.id_documento,
        accion=accion or "APROBAR",
        usuario=user_name,
        valor_anterior=valor_anterior,
        valor_nuevo={"estado_resolucion": ent.estado_resolucion, "accion": accion},
        origen_caso=f"caso {ent.id_staging}",
    )
    db.commit()
    return {"status": "success", "id": ent.id_staging, "estado_resolucion": ent.estado_resolucion, "accion": accion}


def reabrir_caso(db: Session, item_id: str, user_name: str) -> Dict[str, Any]:
    """Reabre un caso resuelto mientras el lote no esté consolidado y deshace creaciones de DD2 si no tienen referencias."""
    if not str(item_id).isdigit():
        raise HTTPException(400, "Solo se pueden reabrir casos de la bandeja de revisión.")
    ent = db.query(StagingEntidadNoResuelta).filter_by(id_staging=int(item_id)).first()
    if not ent:
        raise HTTPException(404, "Caso no encontrado.")
    _asegurar_no_consolidado(db, ent.id_documento)
    if not ent.resuelto:
        return {"status": "success", "id": ent.id_staging, "estado_resolucion": "PENDIENTE"}

    p = dict(ent.payload_json or {}) if isinstance(ent.payload_json, dict) else {}
    undo = p.pop("_undo", None) or {}
    valor_anterior = {"estado_resolucion": ent.estado_resolucion, "accion_aplicada": p.get("accion_aplicada")}

    if undo.get("id_estudiante_creado"):
        est = db.query(DimEstudiante).filter_by(id_estudiante=int(undo["id_estudiante_creado"])).first()
        if est:
            try:
                with db.begin_nested():
                    db.delete(est)
                    db.flush()
            except Exception:
                pass
    if undo.get("id_estudiante_actualizado") and undo.get("nombre_padron_anterior"):
        est = db.query(DimEstudiante).filter_by(id_estudiante=int(undo["id_estudiante_actualizado"])).first()
        if est:
            est.nombre_completo = undo["nombre_padron_anterior"]
    if undo.get("id_modulo_creado"):
        mod = db.query(DimModulo).filter_by(id_modulo=int(undo["id_modulo_creado"])).first()
        if mod:
            try:
                with db.begin_nested():
                    db.delete(mod)
                    db.flush()
            except Exception:
                pass
    if undo.get("sinonimo"):
        _deshacer_sinonimo_catalogo(undo["sinonimo"])

    ent.resuelto = False
    ent.estado_resolucion = "PENDIENTE"
    ent.resuelto_en = None
    p.pop("accion_aplicada", None)
    ent.payload_json = p
    _registrar_auditoria(
        db,
        id_documento=ent.id_documento,
        accion="REABRIR_CASO",
        usuario=user_name,
        valor_anterior=valor_anterior,
        valor_nuevo={"estado_resolucion": "PENDIENTE"},
        origen_caso=f"caso {ent.id_staging}",
    )
    db.commit()
    return {"status": "success", "id": ent.id_staging, "estado_resolucion": "PENDIENTE"}


def consultar_avisos(
    db: Session,
    doc_ids: List[int],
    estado: str = "PENDIENTE",
    rol_usuario: Optional[str] = None,
) -> Dict[str, Any]:
    q = db.query(LogInconsistencia)
    if doc_ids:
        q = q.filter(LogInconsistencia.id_documento.in_(doc_ids))
    if estado and estado != "TODOS":
        q = q.filter(LogInconsistencia.estado_resolucion == estado)
    rows = q.order_by(LogInconsistencia.id_inconsistencia.desc()).limit(200).all()
    items = []
    for r in rows:
        mot = (r.tipo_regla or "REVISION_GENERAL").upper()
        datos = {
            "campo_afectado": r.campo_afectado,
            "valor_recibido": r.valor_recibido,
        }
        items.append({
            "id": r.id_inconsistencia,
            "id_documento": r.id_documento,
            "fila_origen": r.fila_origen,
            "campo_afectado": r.campo_afectado,
            "valor_recibido": r.valor_recibido,
            "tipo_regla": mot,
            "severidad": r.severidad,
            "estado_resolucion": r.estado_resolucion,
            "acciones": construir_acciones(mot, "academico", datos, rol_usuario=rol_usuario),
        })
    return {"status": "success", "total": len(items), "items": items}


def resolver_aviso(
    db: Session,
    aviso_id: int,
    payload: Dict[str, Any],
    user_name: str,
    user_role: str,
) -> Dict[str, Any]:
    aviso = db.query(LogInconsistencia).filter_by(id_inconsistencia=aviso_id).first()
    if not aviso:
        raise HTTPException(404, "Aviso no encontrado.")
    accion = str(payload.get("accion") or "DESCARTAR").upper()
    estado_anterior = aviso.estado_resolucion
    if accion == "ASIGNAR_CANONICO" and payload.get("recordar_sinonimo"):
        if (user_role or "").upper() not in ("ADMIN", "AUDITOR_CALIDAD"):
            raise HTTPException(403, "Solo ADMIN o AUDITOR_CALIDAD pueden guardar sinónimos.")
        _registrar_sinonimo_catalogo(aviso.valor_recibido or "", str(payload.get("valor_canonico") or ""))
    aviso.estado_resolucion = "DESCARTADO" if "DESCARTAR" in accion else "RESUELTO_HUMANO"
    _registrar_auditoria(
        db,
        id_documento=aviso.id_documento,
        accion=accion,
        usuario=user_name,
        valor_anterior={"estado_resolucion": estado_anterior, "valor": aviso.valor_recibido},
        valor_nuevo={"estado_resolucion": aviso.estado_resolucion, "payload": payload},
        origen_caso=f"aviso {aviso_id}",
    )
    db.commit()
    return {"status": "success", "id": aviso_id, "estado_resolucion": aviso.estado_resolucion}
