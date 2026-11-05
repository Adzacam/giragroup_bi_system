"""
backend/services/revision_hechos.py
-----------------------------------
Hechos cargados con requiere_revision = True (índice 0,60–0,85, nota o fecha faltante) en la bandeja HITL
(HU-06 / RF-06). Cada hecho es un caso: se acepta tal cual, o se corrige y aprueba, por separado.
Al aprobar: requiere_revision = False y registro en la bitácora (log_auditoria_nlp + log_pipeline_ingesta).
Al rechazar: se elimina el hecho y queda el registro en la bitácora.

Identificadores de caso: HECHO-ACA-<id_hecho_aca> y HECHO-FIN-<id_hecho_fin>.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.dim_tiempo import DimTiempo
from models.fact_financiero import FactSituacionFinanciera
from models.fact_rendimiento import FactRendimientoAcademico
from models.log_auditoria_nlp import LogAuditoriaNlp
from models.log_pipeline import LogPipelineIngesta
from pipeline.config import NOTA_APROBACION

MOTIVO_HECHO = "HECHO_EN_REVISION"
PREFIJO_ACA, PREFIJO_FIN = "HECHO-ACA-", "HECHO-FIN-"


def es_caso_hecho(item_id: Any) -> bool:
    return str(item_id).startswith((PREFIJO_ACA, PREFIJO_FIN))


def _faltantes_aca(h: FactRendimientoAcademico) -> List[str]:
    return [campo for campo, ok in (("estudiante", h.id_estudiante), ("módulo", h.id_modulo),
                                    ("nota", h.nota_final is not None), ("fecha", h.id_tiempo)) if not ok]


def _faltantes_fin(h: FactSituacionFinanciera) -> List[str]:
    return [campo for campo, ok in (("estudiante", h.id_estudiante), ("fecha", h.id_tiempo),
                                    ("monto", h.monto_deuda is not None or h.monto_pagado is not None)) if not ok]


def _por_que(confianza: Optional[float], faltantes: List[str]) -> str:
    partes = []
    if confianza is not None and float(confianza) < 0.85:
        partes.append(f"Índice del registro {float(confianza):.2f} en la banda de revisión (0,60–0,85).")
    if faltantes:
        partes.append(f"Falta: {', '.join(faltantes)}.")
    return " ".join(partes) or "Marcado para revisión en la carga."


def items_hechos_en_revision(db: Session, doc_ids: Optional[Sequence[int]] = None) -> List[Dict[str, Any]]:
    """Casos de la bandeja para los hechos en revisión (de los documentos dados, o de todos)."""
    estudiantes = {e.id_estudiante: e for e in db.query(DimEstudiante).all()}
    modulos = {m.id_modulo: m for m in db.query(DimModulo).all()}
    docs = {d.id_documento: d for d in db.query(DimOrigenDocumental).all()}
    fechas = {t.id_tiempo: t.fecha for t in db.query(DimTiempo.id_tiempo, DimTiempo.fecha).all()}

    def _q(modelo, col_id):
        q = db.query(modelo).filter(modelo.requiere_revision == True)  # noqa: E712
        if doc_ids is not None:
            q = q.filter(modelo.id_documento.in_(list(doc_ids)))
        return q.order_by(col_id).all()

    items = []
    for h in _q(FactRendimientoAcademico, FactRendimientoAcademico.id_hecho_aca):
        est, mod, doc = estudiantes.get(h.id_estudiante), modulos.get(h.id_modulo), docs.get(h.id_documento)
        faltan = _faltantes_aca(h)
        items.append(_item(f"{PREFIJO_ACA}{h.id_hecho_aca}", "academica", doc, est, h.nivel_confianza_ia, faltan, {
            "modulo_detectado": mod.nombre_modulo if mod else "",
            "nota_final": float(h.nota_final) if h.nota_final is not None else None,
            "fecha": str(fechas.get(h.id_tiempo) or ""),
            **_mes_gestion(fechas.get(h.id_tiempo)),
            "que_vio": f"{est.nombre_completo if est else 'Sin estudiante'} · {mod.nombre_modulo if mod else 'Sin módulo'} · "
                       f"nota {h.nota_final if h.nota_final is not None else '—'} · {fechas.get(h.id_tiempo) or 'sin fecha'}",
            "destino_dw": "Rendimiento Académico",
        }))
    for h in _q(FactSituacionFinanciera, FactSituacionFinanciera.id_hecho_fin):
        est, doc = estudiantes.get(h.id_estudiante), docs.get(h.id_documento)
        faltan = _faltantes_fin(h)
        items.append(_item(f"{PREFIJO_FIN}{h.id_hecho_fin}", "financiera", doc, est, h.nivel_confianza_ia, faltan, {
            "monto_deuda": float(h.monto_deuda) if h.monto_deuda is not None else None,
            "cuotas_impagas": int(h.cuotas_impagas or 0),
            "fecha": str(fechas.get(h.id_tiempo) or ""),
            **_mes_gestion(fechas.get(h.id_tiempo)),
            "que_vio": f"{est.nombre_completo if est else 'Sin estudiante'} · deuda {h.monto_deuda} · "
                       f"pagado {h.monto_pagado} · cuotas {h.cuotas_impagas} · {fechas.get(h.id_tiempo) or 'sin fecha'}",
            "destino_dw": "Situación Financiera y Cobranzas",
        }))
    return items


def _mes_gestion(fecha) -> Dict[str, Any]:
    return {"mes": fecha.month if fecha else None, "gestion": fecha.year if fecha else None}


def _item(item_id, area, doc, est, confianza, faltan, extra) -> Dict[str, Any]:
    nombre = est.nombre_completo if est else ""
    return {
        "id": item_id, "db_id": item_id, "motivo": MOTIVO_HECHO, "motivo_label": "Hecho en revisión",
        "tipo_entidad": "HECHO", "tipo_fuente": (doc.tipo_fuente if doc else "") or "",
        "por_que_detuvo": _por_que(confianza, faltan),
        # El hecho ya trae su entidad resuelta: se acepta con un clic si no falta ningún campo; si falta, se corrige
        "sugerencia": nombre, "sugerencia_catalogo": nombre, "estudiante": nombre,
        "un_clic": not faltan, "campos_faltantes": faltan,
        "similitud_nombre_completo": 100.0 if nombre else 0.0,
        "ci": "", "ci_enmascarado": "", "ner_confidence": float(confianza) if confianza is not None else None,
        "estado_resolucion": "PENDIENTE", "estado": "REQUIERE_REVISION", "area": area,
        "id_documento": doc.id_documento if doc else None, "archivo_origen": doc.nombre_archivo if doc else "",
        "locked": False, "en_calidad": False, "es_nuevo_catalogo": False, **extra,
    }


def _cargar(db: Session, item_id: str) -> Tuple[Any, str]:
    sid = str(item_id)
    if sid.startswith(PREFIJO_ACA):
        return db.query(FactRendimientoAcademico).get(int(sid[len(PREFIJO_ACA):])), "academico"
    return db.query(FactSituacionFinanciera).get(int(sid[len(PREFIJO_FIN):])), "financiero"


def resolver_caso_hecho(db: Session, item_id: str, payload: Dict[str, Any], user_id: Optional[int], user_name: str) -> Dict[str, Any]:
    """
    APROBAR (con correcciones opcionales: nota_final, monto_deuda, cuotas_impagas, estudiante_resuelto,
    mes + gestion) o DESCARTAR. Con aprobacion_en_bloque = True la bitácora registra "Aprobación en bloque".
    """
    hecho, tipo = _cargar(db, item_id)
    if hecho is None:
        return {"status": "error", "message": f"Caso {item_id} no existe."}
    if not hecho.requiere_revision:
        return {"status": "success", "message": f"Caso {item_id} ya estaba resuelto.", "item_id": item_id}

    accion = (payload.get("accion") or "APROBAR").upper()
    en_bloque = bool(payload.get("aprobacion_en_bloque"))
    antes = _resumen(hecho, tipo)
    correcciones = {}
    if "DESCARTAR" in accion:
        db.delete(hecho)
        resultado = "Descartado"
    else:
        correcciones = _aplicar_correcciones(db, hecho, tipo, payload)
        hecho.requiere_revision = False
        resultado = ("Aprobación en bloque" if en_bloque else "Aprobado") + (
            f" con corrección ({', '.join(correcciones)})" if correcciones else " sin cambios")

    db.add(LogAuditoriaNlp(
        texto_original=f"{item_id}: {antes}"[:500], prediccion_beto=f"Hecho {tipo} en revisión"[:200],
        confianza_ia=float(hecho.nivel_confianza_ia) if hecho.nivel_confianza_ia is not None else None,
        correccion_humana=resultado[:200], usuario_auditor=user_id,
    ))
    db.add(LogPipelineIngesta(
        id_documento=hecho.id_documento, etapa="HITL_APROBACION_EN_BLOQUE" if en_bloque else "HITL_RESOLUCION_INDIVIDUAL",
        nivel="WARNING" if "DESCARTAR" in accion else "SUCCESS", modulo="Bandeja HITL",
        mensaje=f"{user_name} resolvió {item_id}: {resultado}.",
        metadata_json={"item_id": item_id, "accion": "APROBACION_EN_BLOQUE" if en_bloque else accion, "usuario": user_name,
                       "antes": antes, "correcciones": correcciones,
                       "nota_auditor": payload.get("nota_auditor")},
    ))
    db.commit()
    return {"status": "success", "message": f"Caso {item_id}: {resultado}.", "item_id": item_id, "accion": accion}


def _aplicar_correcciones(db: Session, hecho, tipo: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    cambios = {}
    nombre = (payload.get("estudiante_resuelto") or "").strip()
    if nombre:
        est = db.query(DimEstudiante).filter(DimEstudiante.nombre_completo.ilike(nombre)).first()
        if est and est.id_estudiante != hecho.id_estudiante:
            hecho.id_estudiante = est.id_estudiante
            cambios["estudiante"] = est.nombre_completo
    if tipo == "academico" and payload.get("nota_final") not in (None, ""):
        nota = float(payload["nota_final"])
        if nota != (float(hecho.nota_final) if hecho.nota_final is not None else None):
            hecho.nota_final = nota
            if not (hecho.estado_tutoria or hecho.estado_arca):  # estado de acta ARCA: lo fija la fuente, no la nota
                hecho.estado_academico = "Aprobado" if nota >= NOTA_APROBACION else "Reprobado"
            cambios["nota_final"] = nota
    fecha = _fecha_corregida(payload)
    if fecha is not None:
        from services.dw_loader import DWLoaderService
        id_tiempo = DWLoaderService(db).resolver_o_crear_tiempo(fecha)
        if id_tiempo and id_tiempo != hecho.id_tiempo:
            hecho.id_tiempo = id_tiempo
            cambios["fecha"] = fecha.isoformat()
    if tipo == "financiero":
        for campo, conv in (("monto_deuda", float), ("cuotas_impagas", int)):
            if payload.get(campo) not in (None, ""):
                valor = conv(payload[campo])
                actual = getattr(hecho, campo)
                if actual is None or conv(actual) != valor:
                    setattr(hecho, campo, valor)
                    cambios[campo] = valor
    return cambios


def _fecha_corregida(payload: Dict[str, Any]) -> Optional[date]:
    """Mes y gestión del formulario (los hechos sin fecha de Moodle y Cobranzas): primer día de ese mes."""
    mes, gestion = payload.get("mes"), payload.get("gestion")
    if mes in (None, "") or gestion in (None, ""):
        return None
    mes, gestion = int(mes), int(gestion)
    if not (1 <= mes <= 12 and 2000 <= gestion <= 2100):
        raise ValueError(f"Fecha inválida: mes {mes}, gestión {gestion}")
    return date(gestion, mes, 1)


def _resumen(hecho, tipo: str) -> str:
    if tipo == "academico":
        return f"estudiante={hecho.id_estudiante} modulo={hecho.id_modulo} nota={hecho.nota_final} tiempo={hecho.id_tiempo}"
    return f"estudiante={hecho.id_estudiante} deuda={hecho.monto_deuda} cuotas={hecho.cuotas_impagas} tiempo={hecho.id_tiempo}"
