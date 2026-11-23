"""
backend/services/revision_acciones_ejecutor.py
--------------------------------------------
Ejecución modular de acciones contextuales de revisión humana (DF-L2 / DD2 / DF-L8):
- Despacha cada acción de `acciones[]` con auditoría completa (usuario, fecha, valor_anterior, valor_nuevo).
- Soporta `reabrir` mientras el lote no esté consolidado, deshaciendo perfiles C, módulos o sinónimos creados.
- Expone y resuelve los avisos de `log_inconsistencias` (`/review-tray/avisos`).
"""
import logging
import math
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status
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
from models.staging_registro import StagingRegistroCrudo
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
from services.revision_acciones_descriptor import construir_acciones
from services.revision_formularios import validar_payload_correccion

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
    elif accion in ("VINCULAR_CANDIDATO", "VINCULAR_PERSONA", "VINCULAR_ESTUDIANTE"):
        id_cand = payload.get("id_estudiante_candidato") or payload.get("id_estudiante_destino")
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
    elif accion in ("VINCULAR_MODULO", "VINCULAR_RELACION"):
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
    elif accion == "CORREGIR_FECHA":
        mes = payload.get("mes")
        gestion = payload.get("gestion")
        if mes is None or gestion is None:
            raise HTTPException(422, "Indica mes y gestión válidos.")
        mes_i, gestion_i = int(mes), int(gestion)
        if not (1 <= mes_i <= 12) or not (2015 <= gestion_i <= 2030):
            raise HTTPException(422, "Mes (1–12) o gestión (2015–2030) fuera de rango.")
        p["mes"] = mes_i
        p["gestion"] = gestion_i
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
    if accion == "CREAR_MODULO":
        if (user_role or "").upper() not in ("ADMIN", "AUDITOR_CALIDAD"):
            raise HTTPException(403, "Solo ADMIN o AUDITOR_CALIDAD pueden crear módulos.")
        nom_mod = (payload.get("modulo_resuelto") or aviso.valor_recibido or "").strip()
        cod_pos = (payload.get("codigo_pos") or "").strip()
        prog = (payload.get("programa_resuelto") or "").strip()
        if not nom_mod or not cod_pos:
            raise HTTPException(422, "Indica código POS y nombre del módulo.")
        mod = db.query(DimModulo).filter(DimModulo.pos_code == cod_pos).first()
        if not mod:
            mod = DimModulo(pos_code=cod_pos, nombre_modulo=nom_mod, programa=prog or None)
            db.add(mod)
            db.flush()
    elif accion == "VINCULAR_MODULO":
        id_mod = payload.get("id_modulo_destino")
        if not id_mod:
            raise HTTPException(422, "Selecciona un módulo destino.")
        mod = db.query(DimModulo).filter(DimModulo.id_modulo == int(id_mod)).first()
        if not mod:
            raise HTTPException(404, "Módulo destino no encontrado.")
    elif accion == "ASIGNAR_CANONICO" and payload.get("recordar_sinonimo"):
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


def validar_numericos_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Valida y normaliza campos numéricos y de fecha de un payload de resolución."""
    for campo, minimo, maximo in (
        ('nota_final', 0, 100),
        ('monto_deuda', 0, None),
        ('monto_convenio', 0, None),
        ('cuotas_impagas', 0, None),
        ('mes', 1, 12),
        ('gestion', 2000, 2100),
        ('numero_modulo', 1, None),
    ):
        valor = payload.get(campo)
        if valor not in (None, ''):
            try:
                numero = float(valor)
                if (
                    not math.isfinite(numero)
                    or numero < minimo
                    or (maximo is not None and numero > maximo)
                    or (campo in ('cuotas_impagas', 'mes', 'gestion', 'numero_modulo') and not numero.is_integer())
                ):
                    raise ValueError()
            except (ValueError, TypeError):
                raise HTTPException(422, 'Revisa los valores numéricos y la fecha de la corrección.')
            payload[campo] = int(numero) if campo in ('cuotas_impagas', 'mes', 'gestion', 'numero_modulo') else numero
    return payload


def _descartar_entidad_legacy(
    db: Session,
    ent: StagingEntidadNoResuelta,
    item_id: str,
    payload: Dict[str, Any],
    user_id: Optional[int],
    user_name: str,
    notificar_cb: Optional[Callable[..., None]] = None,
) -> Dict[str, Any]:
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

    try:
        db.add(LogAuditoriaNlp(
            texto_original=(ent.texto_original or "")[:500],
            prediccion_beto=(ent.mejor_candidato or ent.tipo_entidad or "")[:200],
            confianza_ia=float(ent.nivel_confianza or 0.70),
            correccion_humana="Descartado",
            usuario_auditor=user_id,
        ))
        db.add(LogPipelineIngesta(
            id_documento=ent.id_documento,
            etapa="HITL_RESOLUCION_INDIVIDUAL",
            nivel="WARNING",
            modulo="DataOps HITL",
            mensaje=f"Registro {item_id} descartado por {user_name}.",
            metadata_json={"item_id": item_id, "accion": "DESCARTAR", "usuario": user_name, "motivo": payload.get("motivo_descarte")},
        ))
        db.commit()
    except Exception as e_desc_aud:
        logger.warning("No se pudo auditar descarte de item %s: %s", item_id, e_desc_aud)

    if not payload.get('aprobacion_en_bloque') and notificar_cb:
        notificar_cb(db, 'Caso descartado', 'El descarte y su motivo quedaron guardados en Revisión.')
    cache_consultas.invalidar()
    return {
        "status": "success",
        "message": f"Registro {item_id} descartado.",
        "id": item_id,
        "estado_resolucion": "DESCARTADO",
    }


def resolver_entidad_legacy(
    db: Session,
    ent: StagingEntidadNoResuelta,
    item_id: str,
    payload: Dict[str, Any],
    current_user: Any,
    *,
    dw_loader_cls: Any,
    notificar_cb: Optional[Callable[..., None]] = None,
) -> Dict[str, Any]:
    """Ejecuta la rama legacy APROBAR / DESCARTAR de resolve_review_item (extraída en DF-L8 a)."""
    from routers.dataops._comun import categoria_ruteo as resolver_categoria_ruteo
    from services.revision_consulta import datos_payload, presupuesto_manual

    doc_caso = db.query(DimOrigenDocumental).filter_by(id_documento=ent.id_documento).first()
    cat_caso = resolver_categoria_ruteo(doc_caso.tipo_fuente if doc_caso else None)
    fila_presupuesto = presupuesto_manual(doc_caso, ent.texto_original) or presupuesto_manual(doc_caso, datos_payload(ent).get('raw_line'))
    accion = (payload.get("accion") or "APROBAR").upper()
    if accion != 'DESCARTAR' and fila_presupuesto and cat_caso != 'rentabilidad':
        raise HTTPException(422, 'Esta fila de presupuesto requiere corregir su clasificación antes de aprobarla como persona.')

    user_name = current_user.username if (current_user and hasattr(current_user, "username")) else "Auditor Calidad"
    user_id = current_user.id if (current_user and hasattr(current_user, "id")) else None

    if "DESCARTAR" in accion:
        return _descartar_entidad_legacy(db, ent, item_id, payload, user_id, user_name, notificar_cb)

    orig_doc = db.query(DimOrigenDocumental).filter_by(id_documento=ent.id_documento).first() if ent.id_documento else None
    stg_parent = db.query(StagingRegistroCrudo).filter_by(id=ent.registro_origen_id).first() if ent.registro_origen_id else None
    doc_fuente = (orig_doc.tipo_fuente if orig_doc and orig_doc.tipo_fuente else "ACTA").upper().strip()
    categoria_ruteo = resolver_categoria_ruteo(doc_fuente, stg_parent.categoria if stg_parent else None)
    validar_payload_correccion(categoria_ruteo, getattr(ent, "motivo", None), payload)
    if categoria_ruteo == "evaluacion_docente":
        doc_fuente = "EVALUACION_DOCENTE"
    doc_escala = orig_doc.tipo_escala if orig_doc else "CENTESIMAL_100"
    p_json = ent.payload_json if isinstance(ent.payload_json, dict) else {}

    ci_corregida = payload.get("ci_corregido") or payload.get("ci_opcional") or payload.get("ci_corregida")
    if ci_corregida and '•' in str(ci_corregida):
        ci_corregida = None
    est_resuelto = (
        payload.get("nombre_completo")
        or payload.get("estudiante_resuelto")
        or payload.get("texto_editado")
        or p_json.get("estudiante")
    )

    otra_persona = str(payload.get("confirmar_identidad") or "").strip().lower().startswith("no")
    ci_raw = ci_corregida if otra_persona else (ci_corregida or ent.ci_temporal or p_json.get("ci_real"))
    if not ci_raw or str(ci_raw).strip().lower() in ("no especificado", "no provisto", "none", "null", ""):
        ci_clean = f"TEMP-{ent.id_staging}"
    else:
        ci_clean = str(ci_raw).replace("?", "").strip()

    if categoria_ruteo in ("evaluacion_docente", "marketing", "rentabilidad") and not est_resuelto:
        nom_clean = ""
    elif not est_resuelto and getattr(ent, "motivo", None) in ("POS_NO_EN_DIM_MODULO", "FECHA_INSCRIPCION_INVALIDA"):
        nom_clean = ""
    else:
        nom_clean = (est_resuelto or ent.texto_original or '').strip()
        if not nom_clean:
            raise HTTPException(422, 'Indica el nombre del estudiante antes de aprobar.')
        if len(nom_clean) > 200:
            db.rollback()
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El caso trae la línea completa; indique el nombre del estudiante en texto_editado.",
            )

    modulo_def = (
        payload.get("modulo_resuelto")
        or (f"Módulo {payload.get('numero_modulo')}" if payload.get("numero_modulo") not in (None, "") else None)
        or p_json.get("modulo")
        or "Módulo Académico"
    )
    try:
        dw = dw_loader_cls(db)
        base_registro = {
            "categoria": categoria_ruteo,
            "tipo_fuente": doc_fuente,
            "tipo_escala": doc_escala,
            "doc_id": ent.id_documento,
            "calidad": {"requiere_revision": False, "resuelto_por_humano": True},
        }
        estudiante_res = (
            {"fk_resolucion": {"ci": ci_clean, "nombre_resuelto": nom_clean}, "valor_extraido": nom_clean}
            if nom_clean else {}
        )
        linea_origen = p_json.get("raw_line") or (ent.texto_original if "|" in (ent.texto_original or "") else None)
        campos_linea = campos_por_encabezado([c.strip() for c in linea_origen.split("|")]) if linea_origen else {}
        fecha_linea = fecha_de_fila(campos_linea, categoria_ruteo) if campos_linea else None
        programa_def = payload.get("programa_resuelto") or payload.get("programa") or payload.get("codigo_pos") or p_json.get("programa")
        fecha_mes_gestion = (
            date(int(payload["gestion"]), int(payload["mes"]), 1).isoformat()
            if payload.get("mes") not in (None, "") and payload.get("gestion") not in (None, "")
            else None
        )
        fecha_def = payload.get("fecha_inscripcion") or fecha_mes_gestion or fecha_linea or payload.get("fecha") or p_json.get("fecha")
        escala_def = 10 if str(payload.get("escala_respuesta") or "").strip() == "1 a 10" else (
            5 if str(payload.get("escala_respuesta") or "").strip() == "1 a 5" else (payload.get("escala_max") or p_json.get("escala_max") or 5)
        )

        res_load = {}
        if categoria_ruteo == "academico":
            registros_acta = registros_academicos(campos_linea) if (campos_linea and payload.get("nota_final") is None) else []
            if registros_acta:
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
                    "modulo": {"valor_extraido": modulo_def},
                    "nota_final": nota_payload if nota_payload not in (None, "") else p_json.get("nota_normalizada"),
                    "fecha": fecha_mes_gestion or fecha_linea or payload.get("fecha") or p_json.get("fecha"),
                    "nivel_confianza_ia": 0.99,
                }})
                if res_load.get('status') != 'loaded':
                    raise RuntimeError('La corrección no pudo incorporarse.')

        elif categoria_ruteo == "evaluacion_docente":
            texto_stg = getattr(stg_parent, "texto_plano", None) if stg_parent else None
            perfil_eval = encuesta_canonica.perfil_de_texto(texto_stg, clave=("stg", getattr(stg_parent, "id", None))) if (texto_stg and campos_linea) else None
            regs_eval = registros_evaluacion(campos_linea, perfil_eval) if campos_linea else []
            if regs_eval:
                cargados_eval = 0
                for reg_eval in regs_eval:
                    reg_eval.pop("requiere_revision", None)
                    doc_val = payload.get("docente_resuelto") or reg_eval.get("docente") or p_json.get("docente")
                    est_eval = estudiante_res if nom_clean else (reg_eval.get("estudiante") or {})
                    res_load = dw.cargar_registro({**base_registro, "resoluciones": {
                        **reg_eval,
                        "estudiante": est_eval,
                        "anonima": not bool(est_eval),
                        "docente": doc_val,
                        "modulo": payload.get("modulo_resuelto") or (f"Módulo {payload.get('numero_modulo')}" if payload.get("numero_modulo") not in (None, "") else None) or reg_eval.get("modulo") or p_json.get("modulo"),
                        "programa": programa_def or reg_eval.get("programa") or p_json.get("programa"),
                        "escala_max": reg_eval.get("escala_max") or escala_def,
                        "nivel_confianza_ia": 0.99,
                    }})
                    if res_load.get("status") == "loaded":
                        cargados_eval += 1
                    elif res_load.get("status") != "skipped":
                        raise RuntimeError('La corrección no pudo incorporarse.')
                if cargados_eval == 0:
                    res_load = {"status": "loaded", "tipo": "evaluacion_docente"}
            else:
                puntuacion_val = payload.get("puntuacion") if payload.get("puntuacion") is not None else p_json.get("puntuacion")
                comentario_val = payload.get("comentario") or payload.get("justificacion") or payload.get("nota_auditor") or p_json.get("comentario")
                res_load = dw.cargar_registro({**base_registro, "resoluciones": {
                    "estudiante": estudiante_res,
                    "anonima": not bool(nom_clean),
                    "docente": payload.get("docente_resuelto") or p_json.get("docente"),
                    "modulo": modulo_def,
                    "programa": programa_def,
                    "puntuacion": puntuacion_val,
                    "escala_max": escala_def,
                    "comentario": comentario_val,
                    "fecha": fecha_def,
                    "nivel_confianza_ia": 0.99,
                }})
                if res_load.get("status") not in ("loaded", "skipped"):
                    raise RuntimeError('La corrección no pudo incorporarse.')

        elif categoria_ruteo == "rentabilidad":
            regs_rent = (
                (registros_rentabilidad(campos_linea) or registros_costo_programa(campos_linea) or registros_techo_convenio(campos_linea))
                if campos_linea else []
            )
            if regs_rent:
                for reg_r in regs_rent:
                    reg_r.pop("requiere_revision", None)
                    res_load = dw.cargar_registro({**base_registro, "resoluciones": {**reg_r, "nivel_confianza_ia": 0.99}})
                    if res_load.get("status") != "loaded":
                        raise RuntimeError('La corrección no pudo incorporarse.')
            else:
                res_load = dw.cargar_registro({**base_registro, "resoluciones": {
                    "modulo": {"valor_extraido": modulo_def},
                    "categoria_financiera": payload.get("categoria_financiera") or p_json.get("categoria_financiera") or "Operativo",
                    "monto_ejecutado": payload.get("monto_ejecutado") if payload.get("monto_ejecutado") is not None else p_json.get("monto_ejecutado"),
                    "monto_meta": payload.get("monto_meta") if payload.get("monto_meta") is not None else p_json.get("monto_meta"),
                    "fecha": fecha_linea or payload.get("fecha") or p_json.get("fecha"),
                    "nivel_confianza_ia": 0.99,
                }})
                if res_load.get("status") != "loaded":
                    raise RuntimeError('La corrección no pudo incorporarse.')

        elif categoria_ruteo == "marketing":
            regs_techo = registros_techo_convenio(campos_linea) if campos_linea else []
            if regs_techo:
                for reg_t in regs_techo:
                    reg_t.pop("requiere_revision", None)
                    res_load = dw.cargar_registro({**base_registro, "resoluciones": {**reg_t, "nivel_confianza_ia": 0.99}})
                    if res_load.get("status") != "loaded":
                        raise RuntimeError('La corrección no pudo incorporarse.')
            else:
                extra_mkt = metricas_captacion(campos_linea) if campos_linea else {}
                res_load = dw.cargar_registro({**base_registro, "resoluciones": {
                    "estudiante": estudiante_res,
                    "modulo": {"valor_extraido": modulo_def},
                    "institucion": payload.get("institucion") or p_json.get("institucion"),
                    "clave_convenio": payload.get("clave_convenio") or p_json.get("clave_convenio"),
                    "monto_convenio": payload.get("monto_convenio") if payload.get("monto_convenio") is not None else p_json.get("monto_convenio"),
                    "fecha": fecha_def,
                    **extra_mkt,
                    "nivel_confianza_ia": 0.99,
                }})
                if res_load.get("status") != "loaded":
                    raise RuntimeError('La corrección no pudo incorporarse.')

        else:
            programa_adm = (
                {"valor_extraido": programa_def, "metadata": {"pos_canonico": str(payload["codigo_pos"]).strip()}}
                if payload.get("codigo_pos") else programa_def
            )
            res_load = dw.cargar_registro({**base_registro, "resoluciones": {
                "estudiante": estudiante_res,
                "modulo": {"valor_extraido": modulo_def},
                "programa": programa_adm,
                "nota_final": payload.get("nota_final") if payload.get("nota_final") not in (None, "") else p_json.get("nota_normalizada"),
                "monto_deuda": payload.get("monto_deuda") if payload.get("monto_deuda") is not None else p_json.get("monto_deuda"),
                "monto_pagado": payload.get("monto_pagado") if payload.get("monto_pagado") is not None else p_json.get("monto_pagado"),
                "cuotas_impagas": payload.get("cuotas_impagas") if payload.get("cuotas_impagas") is not None else (p_json.get("cuotas_impagas") or 0),
                "concepto": payload.get("concepto") or p_json.get("concepto"),
                "fecha": fecha_def,
                "nivel_confianza_ia": 0.99,
            }})
            if res_load.get('status') != 'loaded':
                raise RuntimeError('La corrección no pudo incorporarse.')
        ent.id_dimension_resuelta = res_load.get("id_estudiante")
    except Exception as e_res:
        db.rollback()
        logger.exception("No se pudo guardar el caso %s", item_id)
        raise HTTPException(503, 'No se pudo guardar el caso. Continúa pendiente; inténtalo de nuevo.') from e_res

    estado_final = "APROBACION_BLOQUE" if payload.get("aprobacion_en_bloque") else "RESUELTO_HUMANO"
    ent.resuelto = True
    ent.estado_resolucion = estado_final
    ent.resuelto_en = datetime.now()
    if ent.registro_origen_id:
        stg_parent = db.query(StagingRegistroCrudo).filter_by(id=ent.registro_origen_id).first()
        if stg_parent:
            stg_parent.resuelto = True
            stg_parent.estado_resolucion = estado_final
            stg_parent.resuelto_en = datetime.now()
    db.commit()

    try:
        db.add(LogAuditoriaNlp(
            texto_original=(ent.texto_original or "")[:500],
            prediccion_beto=(ent.mejor_candidato or ent.tipo_entidad or "")[:200],
            confianza_ia=float(ent.nivel_confianza or 0.70),
            correccion_humana="APROBACION_BLOQUE" if payload.get("aprobacion_en_bloque") else nom_clean[:200],
            usuario_auditor=user_id,
        ))
        db.add(LogPipelineIngesta(
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
                "modulo": payload.get("modulo_resuelto") or modulo_def,
                "justificacion": payload.get("justificacion") or payload.get("nota_auditor"),
            },
        ))
        db.commit()
        if not payload.get('aprobacion_en_bloque') and notificar_cb:
            notificar_cb(
                db, 'Caso revisado',
                'La corrección quedó guardada. Abre Revisión para consultar el resultado.',
                orig_doc.id_lote if orig_doc else None,
            )
    except Exception as e_aud_ind:
        logger.warning("No se pudo registrar auditoría de resolución individual: %s", e_aud_ind)

    cache_consultas.invalidar()
    return {
        "status": "success",
        "message": f"Registro {item_id} aprobado y consolidado en el Data Warehouse.",
        "id": item_id,
        "resolved_at": datetime.now().isoformat(),
    }
