"""Evaluación de lotes: resolución de documentos, lectura de BETO guardada, caché y estado del flujo."""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.fact_costo_programa import FactCostoPrograma
from models.fact_evaluacion import FactEvaluacionDocente
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_rentabilidad import FactRentabilidad
from models.fact_financiero import FactSituacionFinanciera
from models.fact_techo_convenio import FactTechoConvenio
from fastapi import HTTPException, status
from models.log_pipeline import LogPipelineIngesta
from models.lote import Lote
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from services import beto_integracion, cache_consultas, cache_lectura, tareas_dataops
from services.dataops_evaluation_service import calcular_porcentajes_mayor_residuo, cis_en_entidades, enmascarar_ci, entidad_sin_ci, texto_sin_ci
from services.revision_hechos import contar_hechos_en_revision
from sqlalchemy import func
from pipeline.config import MOTIVO_DESACUERDO_REGLA_BETO
from ._comun import UMBRAL_INDICE_REGISTRO
from .extraccion import _docentes_con_contexto, _es_encabezado_no_estudiante, extract_entities_from_line, fila_sin_entidad

logger = logging.getLogger(__name__)


# =============================================================================
# RESOLUCIÓN DE LOTES MULTI-ARCHIVO Y EVALUACIÓN SERVER-SIDE (#1, #2, #12, #17)
# =============================================================================

def _resolver_documentos_lote(
    db: Session,
    id_lote_or_doc: Optional[Union[int, str]] = None,
    doc_id_filter: Optional[int] = None,
) -> Tuple[Optional[Lote], List[DimOrigenDocumental], List[DimOrigenDocumental]]:
    """
    Resuelve un identificador de lote (o de documento individual por retrocompatibilidad)
    hacia (lote_obj, todos_los_docs_del_lote, docs_filtrados_para_vista).
    Soporta 'latest' o '0' para obtener el último lote activo.
    """
    lote_obj: Optional[Lote] = None
    docs_lote: List[DimOrigenDocumental] = []

    # Sanitización defensiva de id_lote_or_doc y doc_id_filter contra Query objects o strings
    if hasattr(id_lote_or_doc, "default"):
        id_lote_or_doc = "latest"

    clean_doc_id: Optional[int] = None
    if doc_id_filter is not None and not hasattr(doc_id_filter, "default"):
        try:
            clean_doc_id = int(doc_id_filter)
        except (ValueError, TypeError):
            clean_doc_id = None
    doc_id_filter = clean_doc_id

    raw_id_str = str(id_lote_or_doc).strip().lower() if id_lote_or_doc is not None else "latest"

    if raw_id_str in ("latest", "0", "none", "", "null", "undefined"):
        lote_obj = db.query(Lote).order_by(Lote.id_lote.desc()).first()
        if lote_obj:
            docs_lote = (
                db.query(DimOrigenDocumental)
                .filter(DimOrigenDocumental.id_lote == lote_obj.id_lote)
                .order_by(DimOrigenDocumental.id_documento.asc())
                .all()
            )
        if not docs_lote:
            last_doc = db.query(DimOrigenDocumental).order_by(DimOrigenDocumental.id_documento.desc()).first()
            if last_doc:
                if last_doc.id_lote:
                    lote_obj = db.query(Lote).filter(Lote.id_lote == last_doc.id_lote).first()
                    docs_lote = (
                        db.query(DimOrigenDocumental)
                        .filter(DimOrigenDocumental.id_lote == last_doc.id_lote)
                        .order_by(DimOrigenDocumental.id_documento.asc())
                        .all()
                    )
                else:
                    docs_lote = [last_doc]
    elif raw_id_str.isdigit():
        num_id = int(raw_id_str)
        # 1. Buscar primero como id_lote en tabla lote / dim_origen_documental
        lote_obj = db.query(Lote).filter(Lote.id_lote == num_id).first()
        docs_by_lote = (
            db.query(DimOrigenDocumental)
            .filter(DimOrigenDocumental.id_lote == num_id)
            .order_by(DimOrigenDocumental.id_documento.asc())
            .all()
        )
        if docs_by_lote:
            docs_lote = docs_by_lote
        else:
            # 2. Fallback: interpretar num_id como id_documento individual
            doc_single = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento == num_id).first()
            if doc_single:
                if doc_single.id_lote:
                    lote_obj = db.query(Lote).filter(Lote.id_lote == doc_single.id_lote).first()
                    docs_lote = (
                        db.query(DimOrigenDocumental)
                        .filter(DimOrigenDocumental.id_lote == doc_single.id_lote)
                        .order_by(DimOrigenDocumental.id_documento.asc())
                        .all()
                    )
                    if doc_id_filter is None and not lote_obj:
                        doc_id_filter = doc_single.id_documento
                else:
                    docs_lote = [doc_single]

    if doc_id_filter is not None:
        docs_filtrados = [d for d in docs_lote if d.id_documento == doc_id_filter]
        if not docs_filtrados:
            doc_extra = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento == doc_id_filter).first()
            if doc_extra:
                docs_filtrados = [doc_extra]
    else:
        docs_filtrados = list(docs_lote)

    return lote_obj, docs_lote, docs_filtrados


def _serializar_archivos_lote(db: Session, docs_lote: List[DimOrigenDocumental]) -> List[Dict[str, Any]]:
    """Construye la lista de pestañas de archivos del lote para Paso ②, ③ y ④ (#17)."""
    salida = []
    for d in docs_lote:
        stgs = db.query(StagingRegistroCrudo).filter(
            StagingRegistroCrudo.id_documento == d.id_documento,
            StagingRegistroCrudo.es_ruido == False,
            StagingRegistroCrudo.registro_origen_id.is_(None),
        ).all()
        n_tuplas = 0
        for s in stgs:
            lines = [l.strip() for l in (s.texto_plano or "").split("\n") if l.strip()]
            n_tuplas += len(lines)
        salida.append({
            "id_documento": d.id_documento,
            "id_lote": d.id_lote,
            "nombre_archivo": d.nombre_archivo,
            "tipo_documento": d.tipo_documento,
            "tipo_fuente": d.tipo_fuente or "ACTA",
            "tipo_escala": d.tipo_escala,
            "institucion": d.institucion or "GiraGroup Posgrado",
            "periodo": d.periodo or "2026-1",
            "total_registros": n_tuplas,
        })
    return salida


def _cerrar_transaccion_lectura(db: Session) -> None:
    """
    Termina la transacción de lectura sin descartar los objetos ya cargados. El análisis de BETO pasa minutos
    calculando en Python: con la transacción abierta ('idle in transaction') bloqueaba TRUNCATE, ALTER y
    cualquier operación que pida un lock exclusivo sobre staging o las dimensiones. Los objetos siguen
    utilizables y una escritura posterior abre una transacción nueva.
    """
    previo = db.expire_on_commit
    db.expire_on_commit = False
    try:
        db.commit()
    finally:
        db.expire_on_commit = previo


def _evaluar_documentos_lote(
    db: Session,
    docs: List[DimOrigenDocumental],
    persistir_staging: bool = True,
    tarea_id: Optional[int] = None,
    aplicar_resoluciones: bool = True,
) -> Dict[str, Any]:
    """
    Evalúa todas las tuplas de los documentos indicados, actualiza `staging_registros_crudos`
    como fuente única de verdad (#12) y retorna tanto las tuplas detalladas como los conteos
    exactos de partición (`autoCount + auditCount + inconsistenciasCount == totalTuplas`).
    """
    if not docs:
        return {
            "totalDocumentos": 0,
            "totalTuplas": 0,
            "totalEntidades": 0,
            "autoCount": 0,
            "auditCount": 0,
            "inconsistenciasCount": 0,
            "indiceMedio": 0.0,
            "autoPct": 0.0,
            "auditPct": 0.0,
            "inconsistenciasPct": 0.0,
            "detalles": [],
        }

    estudiantes = db.query(DimEstudiante).filter(DimEstudiante.deprecado == False).all()
    docentes = _docentes_con_contexto(db)
    modulos = db.query(DimModulo).all()

    doc_map = {d.id_documento: d for d in docs}
    doc_ids = list(doc_map.keys())

    stg_records = (
        db.query(StagingRegistroCrudo)
        .filter(
            StagingRegistroCrudo.id_documento.in_(doc_ids),
            StagingRegistroCrudo.es_ruido == False,
        )
        .order_by(StagingRegistroCrudo.id.asc())
        .all()
    )

    # Precargar entidades no resueltas existentes en lote para evitar N+1 queries dentro del bucle de líneas
    hitl_records = (
        db.query(StagingEntidadNoResuelta)
        .filter(StagingEntidadNoResuelta.id_documento.in_(doc_ids))
        .all()
    )
    _cerrar_transaccion_lectura(db)  # lo que sigue es cálculo en memoria (minutos en lotes grandes)

    hitl_map: Dict[Tuple[int, str], StagingEntidadNoResuelta] = {}
    if not aplicar_resoluciones:
        hitl_records = []  # lectura base: las resoluciones se superponen al leer (_superponer_resoluciones)
    for h in hitl_records:
        if h.registro_origen_id and h.texto_original:
            hitl_map[(h.registro_origen_id, h.texto_original)] = h
            if len(h.texto_original) > 250:
                hitl_map[(h.registro_origen_id, h.texto_original[:250])] = h

    detalles: List[Dict[str, Any]] = []
    auto_count = 0
    audit_count = 0
    inc_count = 0
    total_entidades = 0
    suma_indices = 0
    lineas_hechas = 0
    tareas_dataops.avanzar(tarea_id, 0, sum(len([l for l in (s_reg.texto_plano or "").splitlines() if l.strip()])
                                            for s_reg in stg_records), forzar=True)
    # Flags BETO_CASCADA_FINAL / BETO_ACUERDO_QC (services/beto_integracion.py); apagados: camino original
    cliente_beto, contadores_beto = None, beto_integracion.Contadores()
    if beto_integracion.necesita_refinar():
        cliente_beto = beto_integracion.ClienteBeto(contadores=contadores_beto)

    for stg in stg_records:
        orig_doc = doc_map.get(stg.id_documento)
        doc_fuente = (orig_doc.tipo_fuente if orig_doc and orig_doc.tipo_fuente else "ACTA").upper()
        doc_escala = orig_doc.tipo_escala if orig_doc else "CENTESIMAL_100"
        if doc_fuente in ("COBRANZA", "ADMISION"):
            doc_escala = None
        elif not doc_escala:
            doc_escala = "CENTESIMAL_100"

        raw_text = (stg.texto_plano or "").strip()
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        if not lines:
            continue

        tuplas_bloque_payload = []
        peor_motivo_bloque = None
        peor_score_bloque = 1.0
        bloque_requiere_rev = False

        refinadas = None
        if cliente_beto is not None:
            refinadas = beto_integracion.refinar_lineas(
                lines,
                lambda l, **kw: extract_entities_from_line(
                    l, estudiantes, docentes, modulos, tipo_escala=doc_escala, tipo_fuente=doc_fuente,
                    apariciones_lote=max(1, len(lines)), **kw),
                tipo_fuente=doc_fuente, cliente=cliente_beto, contadores=contadores_beto,
                archivo=orig_doc.nombre_archivo if orig_doc else None,
                omitir=lambda l: fila_sin_entidad(l, doc_fuente), excluir_celda=_es_encabezado_no_estudiante)

        for line_idx, line in enumerate(lines):
            lineas_hechas += 1
            tareas_dataops.avanzar(tarea_id, lineas_hechas)
            r_beto = refinadas[line_idx] if refinadas is not None else None
            if r_beto is not None:
                ents, score, req_rev = r_beto.tupla
            else:
                ents, score, req_rev = extract_entities_from_line(
                    line,
                    estudiantes,
                    docentes,
                    modulos,
                    tipo_escala=doc_escala,
                    tipo_fuente=doc_fuente,
                    apariciones_lote=max(1, len(lines)),
                )
            total_entidades += len(ents)
            indice_num = int(round(score * 100))
            suma_indices += indice_num

            ent_est = next((e for e in ents if e.get("label") == "ESTUDIANTE"), None)
            ent_mod = next((e for e in ents if e.get("label") == "MÓDULO"), None)
            ent_doc = next((e for e in ents if e.get("label") == "DOCENTE"), None)
            ent_ci = next((e for e in ents if e.get("label") == "DOCUMENTO / CI"), None)
            ent_cal = next((e for e in ents if e.get("label") == "CALIFICACIÓN"), None)
            ent_mon = next((e for e in ents if e.get("label") == "MONTO"), None)
            ent_con = next((e for e in ents if e.get("label") == "CONCEPTO_FINANCIERO"), None)

            ci_val = ent_ci.get("token") if ent_ci else None
            if ci_val == "No provisto":
                ci_val = None
            ci_masked = enmascarar_ci(ci_val)
            # Lo que viaja al navegador nunca lleva el CI completo (ni en la línea, ni en las entidades)
            cis_linea = cis_en_entidades(ents, ci_val)
            ents_pub = [entidad_sin_ci(e, cis_linea) for e in ents]
            line_pub = texto_sin_ci(line, cis_linea)

            ci_dudosa = bool(ci_val and ("?" in ci_val or len(re.sub(r"[^0-9]", "", ci_val)) < 5))
            nota_invalida = bool(
                ent_cal and ent_cal.get("canonicalId") in ("ESCALA_AMBIGUA", "NOTA_FUERA_ESCALA")
            )
            escala_ambigua = bool(ent_cal and ent_cal.get("canonicalId") == "ESCALA_AMBIGUA")

            # Búsqueda instantánea O(1) en memoria precargada en lugar de query N+1
            exists_hitl = hitl_map.get((stg.id, line)) or hitl_map.get((stg.id, line[:250]))

            # Determinar partición tripartita mutuamente excluyente (#1, #2):
            # 1) INCONSISTENCIA DURA (regla determinista fallida)
            # 2) AUDITORÍA HUMANA (baja confianza < 85, entidad nueva u homonimia)
            # 3) APROBADO AUTOMÁTICO (índice >= 85 y sin falla de regla, o ya resuelto por humano)
            if exists_hitl and exists_hitl.resuelto:
                estado_res_row = exists_hitl.estado_resolucion or "RESUELTO_HUMANO"
                if estado_res_row == "DESCARTADO":
                    categoria_particion = "INCONSISTENCIA"
                    estado_reg = "INCONSISTENCIA"
                    motivo_codigo = exists_hitl.motivo or "DESCARTADO"
                    motivo_decision = "Registro descartado formalmente en auditoría humana."
                    inc_count += 1
                else:
                    categoria_particion = "AUTOMATICO"
                    estado_reg = "AUTOMATICO"
                    motivo_codigo = "RESUELTO_HUMANO"
                    motivo_decision = "Registro revisado y conciliado por auditor humano."
                    auto_count += 1
            elif ci_dudosa:
                categoria_particion = "INCONSISTENCIA"
                estado_reg = "INCONSISTENCIA"
                estado_res_row = "PENDIENTE"
                motivo_codigo = "CI_DUDOSA"
                motivo_decision = f"El CI '{ci_masked}' presenta caracteres dudosos (?) o longitud inválida."
                inc_count += 1
            elif escala_ambigua:
                categoria_particion = "INCONSISTENCIA"
                estado_reg = "INCONSISTENCIA"
                estado_res_row = "PENDIENTE"
                motivo_codigo = "ESCALA_AMBIGUA"
                motivo_decision = "Archivo académico sin escala de calificación declarada."
                inc_count += 1
            elif nota_invalida:
                categoria_particion = "INCONSISTENCIA"
                estado_reg = "INCONSISTENCIA"
                estado_res_row = "PENDIENTE"
                motivo_codigo = "NOTA_FUERA_ESCALA"
                motivo_decision = f"La calificación excede el rango permitido por la escala {doc_escala}."
                inc_count += 1
            elif req_rev or indice_num < UMBRAL_INDICE_REGISTRO:
                categoria_particion = "REVISION"
                estado_reg = "REVISION"
                estado_res_row = "PENDIENTE"
                if r_beto is not None and r_beto.degradada_por_acuerdo:
                    motivo_codigo = MOTIVO_DESACUERDO_REGLA_BETO
                    motivo_decision = "Las reglas encontraron una persona que BETO no reconoce en ese tramo; la confianza bajó un escalón."
                elif indice_num < UMBRAL_INDICE_REGISTRO:
                    motivo_codigo = "BAJA_CONFIANZA"
                    motivo_decision = f"Índice del registro ({indice_num}) inferior al umbral de pase directo ({UMBRAL_INDICE_REGISTRO})."
                elif ent_mod and ent_mod.get("es_nuevo_perfil"):
                    motivo_codigo = "ENTIDAD_NUEVA"
                    motivo_decision = "Módulo no catalogado; requiere confirmación en revisión humana."
                else:
                    motivo_codigo = "HOMONIMIA"
                    motivo_decision = "Ambigüedad semántica detectada para validación humana."
                audit_count += 1
            else:
                categoria_particion = "AUTOMATICO"
                estado_reg = "AUTOMATICO"
                estado_res_row = "APROBADO_AUTOMATICO"
                motivo_codigo = "APROBADO_AUTOMATICO"
                motivo_decision = f"Todos los elementos superan el umbral ({UMBRAL_INDICE_REGISTRO}) y cumplen las reglas."
                auto_count += 1

            if score < peor_score_bloque:
                peor_score_bloque = score
            if estado_reg != "AUTOMATICO":
                bloque_requiere_rev = True
                if not peor_motivo_bloque or categoria_particion == "INCONSISTENCIA":
                    peor_motivo_bloque = motivo_codigo

            # Explicabilidad por elemento con terminología unificada (#3, #6)
            confianza_elementos = []
            if ent_est:
                lect_est = int(round(ent_est.get("lecturaModelo", 0.88) * 100))
                bono_cat_e = int(round(ent_est.get("bonoCatalogo", 0.0) * 100))
                bono_rep_e = int(round(ent_est.get("bonoRepetido", 0.0) * 100))
                ind_est = int(round(ent_est.get("betoConfidence", 0.88) * 100))
                confianza_elementos.append({
                    "elemento": "Estudiante",
                    "valor": ent_est.get("token"),
                    "indice": ind_est,
                    "lectura_modelo": lect_est,
                    "bono_catalogo": bono_cat_e,
                    "bono_repetido": bono_rep_e,
                    "explicacion": f"Lectura del modelo: {lect_est} + bono catálogo: +{bono_cat_e} + bono repetido: +{bono_rep_e}",
                })
            if ent_mod:
                lect_mod = int(round(ent_mod.get("lecturaModelo", 0.85) * 100))
                bono_cat_m = int(round(ent_mod.get("bonoCatalogo", 0.0) * 100))
                bono_rep_m = int(round(ent_mod.get("bonoRepetido", 0.0) * 100))
                ind_mod = int(round(ent_mod.get("betoConfidence", 0.85) * 100))
                confianza_elementos.append({
                    "elemento": "Módulo",
                    "valor": ent_mod.get("matchedCanonical") or ent_mod.get("token"),
                    "indice": ind_mod,
                    "lectura_modelo": lect_mod,
                    "bono_catalogo": bono_cat_m,
                    "bono_repetido": bono_rep_m,
                    "explicacion": f"Lectura del modelo: {lect_mod} + bono catálogo: +{bono_cat_m} + bono repetido: +{bono_rep_m}",
                })
            if ent_doc:
                lect_doc = int(round(ent_doc.get("lecturaModelo", 0.85) * 100))
                bono_cat_d = int(round(ent_doc.get("bonoCatalogo", 0.0) * 100))
                bono_rep_d = int(round(ent_doc.get("bonoRepetido", 0.0) * 100))
                ind_doc = int(round(ent_doc.get("betoConfidence", 0.85) * 100))
                confianza_elementos.append({
                    "elemento": "Docente",
                    "valor": ent_doc.get("matchedCanonical") or ent_doc.get("token"),
                    "indice": ind_doc,
                    "lectura_modelo": lect_doc,
                    "bono_catalogo": bono_cat_d,
                    "bono_repetido": bono_rep_d,
                    "explicacion": f"Lectura del modelo: {lect_doc} + bono catálogo: +{bono_cat_d} + bono repetido: +{bono_rep_d}",
                })

            reglas = {
                "ci": {
                    "valido": not ci_dudosa,
                    "valor_enmascarado": ci_masked,
                    "motivo": "Formato válido" if not ci_dudosa else "CI dudoso o ilegible",
                },
                "nota": {
                    "valido": not nota_invalida,
                    "original": ent_cal.get("notaOriginal") if ent_cal else None,
                    "normalizada": ent_cal.get("notaNormalizada") if ent_cal else None,
                    "escala": doc_escala,
                    "motivo": (
                        f"Convertida a base 100 según escala {doc_escala}"
                        if (ent_cal and not nota_invalida)
                        else ("No aplica (Fuente no académica)" if doc_fuente in ("COBRANZA", "ADMISION") else "Sin nota o fuera de escala")
                    ),
                },
                "monto": {
                    "valido": True,
                    "valor": ent_mon.get("valorNumerico") if ent_mon else None,
                    "cuotas_impagas": ent_mon.get("cuotasImpagas") if ent_mon else 0,
                },
            }

            tokens_visuales = [
                {
                    "text": e.get("token"),
                    "tag": e.get("label"),
                    "conll_tag": e.get("conllTag", "O"),
                    "icon": (
                        "user"
                        if e.get("label") == "ESTUDIANTE"
                        else ("book" if e.get("label") == "MÓDULO" else ("award" if e.get("label") == "CALIFICACIÓN" else "file"))
                    ),
                    "color": (
                        "#3b82f6"
                        if e.get("label") == "ESTUDIANTE"
                        else ("#10b981" if e.get("label") == "MÓDULO" else ("#f59e0b" if e.get("label") == "CALIFICACIÓN" else "#8b5cf6"))
                    ),
                }
                for e in ents_pub
            ]

            ent_prog = next((e for e in ents if e.get("label") == "PROGRAMA"), None)
            ent_asist = next((e for e in ents if e.get("label") == "ASISTENCIA"), None)
            es_comercial = doc_fuente in ("ADMISION", "COMERCIAL", "INSCRIPCIONES", "LEADS") or "INSCRIPCI" in doc_fuente or "META" in line.upper() or "CANAL" in line.upper()
            es_financiero = (doc_fuente in ("COBRANZA", "FINANCIERO", "PAGOS") or ent_mon is not None or (ent_con and "PAGO" in ent_con.get("token", "").upper())) and not es_comercial
            area_reg = "comercial" if es_comercial else ("financiera" if es_financiero else "academica")

            es_nuevo_cat = bool(ent_mod and ent_mod.get("es_nuevo_perfil"))
            en_calidad = (estado_reg != "AUTOMATICO") or es_nuevo_cat or ci_dudosa or nota_invalida

            row_id = f"REG_{stg.id}_{line_idx + 1}"
            tupla_item = {
                "id": row_id,
                "stg_id": stg.id,
                "id_documento": stg.id_documento,
                "nombre_archivo": orig_doc.nombre_archivo if orig_doc else f"Archivo_{stg.id_documento}",
                "tipo_fuente": doc_fuente,
                "tipo_escala": doc_escala,
                "line_number": line_idx + 1,
                "raw_text": line_pub,
                "estado": estado_reg,
                "categoria_particion": categoria_particion,
                "estado_resolucion": estado_res_row,
                "motivo": motivo_codigo,
                "indice_registro": indice_num,
                "estudiante": ent_est.get("token") if ent_est else "No detectado",
                "ci": ci_masked,
                "ci_enmascarado": ci_masked,
                "modulo": (ent_mod.get("matchedCanonical") or ent_mod.get("token")) if ent_mod else (ent_con.get("token") if ent_con else "No detectado"),
                "nota_original": ent_cal.get("notaOriginal") if ent_cal else None,
                # Nota sólo de una calificación; el monto va aparte (antes la bandeja mostraba 'Nota: Bs. 135/100')
                "nota_normalizada": (ent_cal.get("notaNormalizada") or ent_cal.get("matchedCanonical")) if ent_cal else None,
                "monto": ent_mon.get("matchedCanonical") if ent_mon else None,
                "area": area_reg,
                "en_calidad": en_calidad,
                "es_nuevo_catalogo": es_nuevo_cat,
                "alerta_abandono": False,
                "lectura": {
                    "texto": line_pub,
                    "tokens": tokens_visuales,
                    "entidades": ents_pub,
                },
                "confianza_elementos": confianza_elementos,
                "verificacion_reglas": reglas,
                "decision": {
                    "indice_mas_bajo": indice_num,
                    "estado": estado_reg,
                    "motivo_llano": motivo_decision,
                    "motivo_codigo": motivo_codigo,
                },
            }
            detalles.append(tupla_item)

            tuplas_bloque_payload.append({
                "id": row_id,
                "line_number": line_idx + 1,
                "raw_line": line,
                "ci_real": ci_val,
                "ci_enmascarado": ci_masked,
                "estudiante": ent_est.get("token") if ent_est else None,
                "modulo": (ent_mod.get("matchedCanonical") or ent_mod.get("token")) if ent_mod else None,
                "nota_original": ent_cal.get("notaOriginal") if ent_cal else None,
                "nota_normalizada": ent_cal.get("notaNormalizada") if ent_cal else None,
                "monto_deuda": ent_mon.get("valorNumerico") if ent_mon else None,
                "monto_pagado": ent_mon.get("montoPagado") if ent_mon else None,
                "cuotas_impagas": ent_mon.get("cuotasImpagas") if ent_mon else 0,
                "concepto": ent_con.get("token") if ent_con else None,
                "indice_registro": indice_num,
                "motivo": motivo_codigo,
                "motivo_llano": motivo_decision,
                "estado_resolucion": estado_res_row,
            })

            if persistir_staging and estado_reg != "AUTOMATICO" and not exists_hitl:
                try:
                    new_hitl = StagingEntidadNoResuelta(
                        id_documento=stg.id_documento,
                        tipo_entidad="ESTUDIANTE" if ent_est else ("MODULO" if ent_mod else ("CONCEPTO_FINANCIERO" if ent_con else "CALIFICACION")),
                        texto_original=line,
                        ci_temporal=ci_val,
                        mejor_candidato=(
                            ent_est.get("matchedCanonical")
                            if ent_est
                            else ((ent_mod.get("matchedCanonical") or ent_mod.get("token")) if ent_mod else None)
                        ),
                        score_fuzzy=float(indice_num),
                        fk_estado="C",
                        nivel_confianza=float(round(score, 2)),
                        resuelto=False,
                        motivo=motivo_codigo,
                        payload_json={
                            "id": row_id,
                            "raw_line": line,
                            "estudiante": ent_est.get("token") if ent_est else None,
                            "ci_real": ci_val,
                            "ci_enmascarado": ci_masked,
                            "modulo": (ent_mod.get("matchedCanonical") or ent_mod.get("token")) if ent_mod else None,
                            "nota_original": ent_cal.get("notaOriginal") if ent_cal else None,
                            "nota_normalizada": ent_cal.get("notaNormalizada") if ent_cal else None,
                            "monto_deuda": ent_mon.get("valorNumerico") if ent_mon else None,
                            "cuotas_impagas": ent_mon.get("cuotasImpagas") if ent_mon else 0,
                            "tipo_fuente": doc_fuente,
                            "tipo_escala": doc_escala,
                            "motivo_llano": motivo_decision,
                        },
                        registro_origen_id=stg.id,
                        estado_resolucion="PENDIENTE",
                    )
                    db.add(new_hitl)
                except Exception as ex_stg:
                    logger.warning("No se pudo persistir en stg_entidad_no_resuelta: %s", ex_stg)

        if persistir_staging:
            stg.motivo = peor_motivo_bloque or "APROBADO_AUTOMATICO"
            stg.score_confianza = round(peor_score_bloque, 4)
            stg.requiere_revision = bloque_requiere_rev
            if stg.estado_resolucion not in ("RESUELTO_HUMANO", "DESCARTADO"):
                stg.estado_resolucion = "PENDIENTE" if bloque_requiere_rev else "APROBADO_AUTOMATICO"
            stg.payload_json = {
                "tipo_fuente": doc_fuente,
                "tipo_escala": doc_escala,
                "tuplas": tuplas_bloque_payload,
            }

    if persistir_staging:
        try:
            db.commit()
        except Exception as e_com:
            db.rollback()
    # Mapeo de estudiantes para corroboración multifuente y detección de umbral de abandono
    estudiantes_map: Dict[str, Dict[str, list]] = {}
    for item in detalles:
        c_key = item.get("ci")
        nom_key = item.get("estudiante")
        ident = c_key if (c_key and "••" not in c_key) else (nom_key if nom_key and nom_key != "No detectado" else None)
        if not ident:
            continue
        ident_norm = ident.strip().lower()
        if ident_norm not in estudiantes_map:
            estudiantes_map[ident_norm] = {"academico": [], "financiero": []}
        if item.get("area") == "academica":
            estudiantes_map[ident_norm]["academico"].append(item)
        elif item.get("area") == "financiera":
            estudiantes_map[ident_norm]["financiero"].append(item)

    # Señales de mora e inasistencia por identidad: dependen solo de la identidad, no de la línea. Antes se
    # recorrían todas las líneas de la identidad por cada línea (cuadrático: minutos con miles de líneas por persona).
    senales_por_ident: Dict[str, Tuple] = {}

    def _senales(ident_norm: str) -> Tuple:
        if ident_norm in senales_por_ident:
            return senales_por_ident[ident_norm]
        est_cross = estudiantes_map.get(ident_norm) or {"academico": [], "financiero": []}
        has_mora, mora_ref, mora_cuotas = False, None, 0
        for fin in est_cross["financiero"]:
            cuotas = fin.get("verificacion_reglas", {}).get("monto", {}).get("cuotas_impagas", 0)
            if cuotas >= 2 or "MORA" in fin.get("raw_text", "").upper():
                has_mora = True
                mora_ref = fin.get("id")
                mora_cuotas = max(mora_cuotas, cuotas or 2)
        has_inasist, inasist_ref, inasist_pct = False, None, 0
        for acad in est_cross["academico"]:
            asist_e = next((e for e in acad.get("lectura", {}).get("entidades", []) if e.get("label") == "ASISTENCIA"), None)
            if asist_e and (asist_e.get("inasistenciaPct", 0) >= 20.0 or asist_e.get("asistenciaPct", 100) <= 80.0):
                has_inasist = True
                inasist_ref = acad.get("id")
                inasist_pct = asist_e.get("inasistenciaPct", 35)
        senales_por_ident[ident_norm] = (has_mora, mora_ref, mora_cuotas, has_inasist, inasist_ref, inasist_pct)
        return senales_por_ident[ident_norm]

    # Identificar quiénes cruzan alerta de abandono y estructurar desglose relacional BETO
    for item in detalles:
        ident_norm = (item.get("ci") or item.get("estudiante") or "").strip().lower()
        has_mora, mora_ref, mora_cuotas, has_inasist, inasist_ref, inasist_pct = _senales(ident_norm)

        reg_asist_e = next((e for e in item.get("lectura", {}).get("entidades", []) if e.get("label") == "ASISTENCIA"), None)
        reg_inasist = reg_asist_e and reg_asist_e.get("inasistenciaPct", 0) >= 20.0
        reg_cuotas = item.get("verificacion_reglas", {}).get("monto", {}).get("cuotas_impagas", 0) >= 2 or "MORA" in item.get("raw_text", "").upper()

        alerta_abandono = (has_mora and (has_inasist or reg_inasist)) or (has_inasist and (has_mora or reg_cuotas)) or (reg_inasist and reg_cuotas)

        cruce_dict = {
            "activo": bool(alerta_abandono),
            "tipo": "ALERTA_UMBRAL_ABANDONO" if alerta_abandono else "CONCILIACION_NORMAL",
            "detalle": (
                f"Cruce multifuente: El estudiante registra {mora_cuotas or 2} cuotas impagas en registros financieros y {inasist_pct or 35}% de inasistencia en actas académicas -> Alerta de Umbral de Abandono."
                if alerta_abandono
                else "Relaciones corroboradas sin alertas críticas entre fuentes del lote."
            ),
            "archivo_cruzado": (docs[1].nombre_archivo if len(docs) > 1 else docs[0].nombre_archivo) if docs else "archivo_fuente.xlsx",
            "ref_cruzada": mora_ref or inasist_ref or "S/R",
        }

        ent_mod = next((e for e in item.get("lectura", {}).get("entidades", []) if e.get("label") == "MÓDULO"), None)
        ent_prog = next((e for e in item.get("lectura", {}).get("entidades", []) if e.get("label") == "PROGRAMA"), None)
        es_nuevo_cat = bool(ent_mod and ent_mod.get("es_nuevo_perfil"))

        prog_nom = ent_prog.get("token") if ent_prog else (item.get("programa") or "Programa Curricular")
        mod_nom = (ent_mod.get("matchedCanonical") or ent_mod.get("token")) if ent_mod else (item.get("modulo") or "Módulo Académico")

        arancel_calc = "14.500 Bs" if "MAESTR" in str(prog_nom).upper() else ("1.500 Bs por módulo" if ent_mod else "Arancel según catálogo")

        desglose_relacional = {
            "oracion_texto_plano": item.get("raw_text"),
            "tokens": item.get("lectura", {}).get("tokens", []),
            "catalogo_guia": {
                "programa": prog_nom,
                "modulo": mod_nom,
                "modulo_codigo": ent_mod.get("canonicalId", "MOD-ACT") if ent_mod else "MOD-ACT",
                "arancel_base": arancel_calc,
                "estado_catalogo": "SUGERENCIA_NUEVO_PARAMETRO" if es_nuevo_cat else "VALIDADO_EN_CATALOGO",
                "mensaje": (
                    "No existe en Catálogo Guía Maestro · Sugerido para incorporación como nuevo curso/módulo Cero-PII."
                    if es_nuevo_cat
                    else "Parámetro validado contra Catálogo Guía Institucional (Cero-PII)."
                ),
            },
            "cruce_multifuente": cruce_dict,
        }

        item["alerta_abandono"] = bool(alerta_abandono)
        item["desglose_relacional"] = desglose_relacional
        item["cruce_multifuente"] = cruce_dict
        if alerta_abandono:
            item["en_calidad"] = True

    total_tuplas = len(detalles)
    indice_medio = round(suma_indices / total_tuplas, 1) if total_tuplas > 0 else 0.0
    auto_pct, audit_pct, inc_pct = calcular_porcentajes_mayor_residuo(auto_count, audit_count, inc_count)

    return {
        "totalDocumentos": len(docs),
        "totalTuplas": total_tuplas,
        "totalEntidades": total_entidades,
        "autoCount": auto_count,
        "auditCount": audit_count,
        "inconsistenciasCount": inc_count,
        "indiceMedio": indice_medio,
        "autoPct": auto_pct,
        "auditPct": audit_pct,
        "inconsistenciasPct": inc_pct,
        "detalles": detalles,
        **({"beto": contadores_beto.como_dict()} if cliente_beto is not None else {}),
    }


def _evaluar_lote_en_segundo_plano(doc_ids: List[int], id_lote: Optional[int], tarea_id: Optional[int] = None) -> None:
    """
    Evaluación post-ingesta con su propia sesión (la del request ya se cerró al responder). Registra su avance
    (LECTURA_BETO), deja el resultado en la caché de disco para que el paso ③ abra al instante desde cualquier
    worker y avisa cuando el lote está listo para revisar.
    """
    db_bg = SessionLocal()
    tarea_id = tarea_id or tareas_dataops.crear("LECTURA_BETO", id_lote)
    try:
        docs = db_bg.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento.in_(doc_ids)).all()
        if not docs:
            tareas_dataops.terminar(tarea_id, {})
            return
        res = _evaluar_documentos_lote(db_bg, docs, persistir_staging=True, tarea_id=tarea_id)
        # Tras persistir sólo se agregan casos sin resolver, que no cambian la lectura: el mismo resultado sirve
        # como lectura del lote con su huella nueva
        ids = sorted(d.id_documento for d in docs)
        clave = ("evaluacion_lectura", tuple(ids), _huella_evaluacion(db_bg, ids))
        if cache_lectura.guardar(clave, res) is False:
            raise RuntimeError("No se pudieron guardar los resultados de la lectura. Inténtalo de nuevo.")
        tareas_dataops.terminar(tarea_id, {"total_tuplas": res.get("totalTuplas"), **({"beto": res["beto"]} if "beto" in res else {})})
    except Exception as e_eval_batch:
        db_bg.rollback()
        logger.warning("No se pudo evaluar lote %s post-ingesta: %s", id_lote, e_eval_batch)
        tareas_dataops.fallar(tarea_id, str(e_eval_batch))
    finally:
        lote = db_bg.query(Lote).filter_by(id_lote=id_lote).first()
        if lote and lote.estado == "REINTENTANDO":
            lote.estado = "PROCESADO"
            db_bg.commit()
        db_bg.close()


TTL_EVALUACION_LECTURA_SEG = 1800


def _huella_evaluacion(db: Session, doc_ids: List[int]) -> Tuple:
    """
    Lo que cambia la lectura de BETO de un lote: su staging (textos y bloques). Consulta barata.
    Las resoluciones de la bandeja no entran: se superponen en cada lectura (_superponer_resoluciones), así
    revisar un caso o consolidar al DW no obliga a releer el lote entero (minutos con 100 mil registros).
    """
    stg = db.query(
        func.count(StagingRegistroCrudo.id), func.max(StagingRegistroCrudo.id)
    ).filter(StagingRegistroCrudo.id_documento.in_(doc_ids)).one()
    return ("v2",) + tuple(stg)


def _superponer_resoluciones(db: Session, base: Dict[str, Any], doc_ids: List[int]) -> Dict[str, Any]:
    """
    Aplica a la lectura base los casos ya resueltos en la bandeja: aprobado -> AUTOMATICO (RESUELTO_HUMANO),
    descartado -> INCONSISTENCIA. Misma regla que _evaluar_documentos_lote con exists_hitl.resuelto, pero en
    memoria y sin volver a leer con BETO. Devuelve un resultado nuevo; la base cacheada no se modifica.
    """
    resueltos = (
        db.query(StagingEntidadNoResuelta.registro_origen_id, StagingEntidadNoResuelta.texto_original,
                 StagingEntidadNoResuelta.estado_resolucion, StagingEntidadNoResuelta.motivo)
        .filter(StagingEntidadNoResuelta.id_documento.in_(doc_ids), StagingEntidadNoResuelta.resuelto == True)  # noqa: E712
        .all()
    )
    if not resueltos:
        return base
    mapa: Dict[Tuple[int, str], Tuple[str, Optional[str]]] = {}
    for rid, texto, estado, motivo in resueltos:
        if rid and texto:
            mapa[(rid, texto)] = (estado or "RESUELTO_HUMANO", motivo)
            mapa.setdefault((rid, texto[:250]), (estado or "RESUELTO_HUMANO", motivo))

    detalles, auto_c, audit_c, inc_c = [], 0, 0, 0
    for d in base.get("detalles", []):
        r = mapa.get((d.get("stg_id"), d.get("raw_text"))) or mapa.get((d.get("stg_id"), (d.get("raw_text") or "")[:250]))
        if r:
            estado_res, motivo = r
            d = dict(d)
            descartado = estado_res == "DESCARTADO"
            estado = "INCONSISTENCIA" if descartado else "AUTOMATICO"
            d.update({
                "estado": estado, "categoria_particion": estado, "estado_resolucion": estado_res,
                "motivo": (motivo or "DESCARTADO") if descartado else "RESUELTO_HUMANO",
            })
            d["decision"] = {**(d.get("decision") or {}), "estado": estado, "motivo_codigo": d["motivo"],
                             "motivo_llano": ("Registro descartado formalmente en auditoría humana." if descartado
                                              else "Registro revisado y conciliado por auditor humano.")}
            d["en_calidad"] = descartado or bool(d.get("es_nuevo_catalogo") or d.get("alerta_abandono"))
        cat = d.get("categoria_particion")
        auto_c += cat == "AUTOMATICO"
        audit_c += cat == "REVISION"
        inc_c += cat == "INCONSISTENCIA"
        detalles.append(d)
    auto_pct, audit_pct, inc_pct = calcular_porcentajes_mayor_residuo(auto_c, audit_c, inc_c)
    return {**base, "detalles": detalles, "autoCount": auto_c, "auditCount": audit_c, "inconsistenciasCount": inc_c,
            "autoPct": auto_pct, "auditPct": audit_pct, "inconsistenciasPct": inc_pct}


def _evaluacion_lectura(db: Session, docs: List[DimOrigenDocumental]) -> Optional[Dict[str, Any]]:
    """Consulta pura: nunca ejecuta BETO, espera tareas ni registra cálculos en un GET."""
    doc_ids = sorted(d.id_documento for d in docs)
    if not doc_ids:
        return None
    clave = ("evaluacion_lectura", tuple(doc_ids), _huella_evaluacion(db, doc_ids))
    base = cache_consultas.consultar(clave)
    if base is None:
        base = cache_lectura.leer(clave)
        if base is not None:
            cache_consultas.obtener(clave, TTL_EVALUACION_LECTURA_SEG, lambda: base)
    return _superponer_resoluciones(db, base, doc_ids) if base is not None else None


def _lote_consolidado_en_dw(db: Session, ids_docs: List[int]) -> bool:
    """
    True si el lote ya pasó por una consolidación al DW: hechos cargados, o una consolidación exitosa registrada.
    Lo segundo cubre las fuentes que no generan hechos (ADMISION carga estudiantes a dim_estudiante).
    """
    if not ids_docs:
        return False
    hay_hechos = any(db.query(modelo).filter(modelo.id_documento.in_(ids_docs)).first() is not None
                     for modelo in (FactRendimientoAcademico, FactSituacionFinanciera,
                                    FactEvaluacionDocente, FactRentabilidad, FactTechoConvenio, FactCostoPrograma))
    if hay_hechos:
        return True
    return db.query(LogPipelineIngesta.id).filter(
        LogPipelineIngesta.id_documento.in_(ids_docs),
        LogPipelineIngesta.etapa == "DW_CONSOLIDACION",
        LogPipelineIngesta.nivel == "SUCCESS",
    ).first() is not None


def _estado_flujo_lote(db: Session, ids_docs: List[int], pendientes_revision: int) -> str:
    """
    Fuente única del ciclo de vida del lote: 'CONSOLIDADO' cuando ya hay hechos en el DW y no quedan
    casos por revisar (entidades sin resolver + hechos del DW marcados en revisión); en cualquier otro caso
    'EN_CURSO' (la bandeja ④ sigue consolidando casos sueltos).
    """
    if ids_docs and pendientes_revision == 0 and contar_hechos_en_revision(db, ids_docs) == 0             and _lote_consolidado_en_dw(db, ids_docs):
        return "CONSOLIDADO"
    return "EN_CURSO"


def _asegurar_lote_editable(db: Session, id_lote: Optional[int]) -> None:
    """409 si el lote ya está CONSOLIDADO (flujo cerrado, solo lectura)."""
    if not id_lote:
        return
    docs = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_lote == int(id_lote)).all()
    ids_docs = [d.id_documento for d in docs]
    if not ids_docs:
        return
    pendientes = (
        db.query(func.count(StagingEntidadNoResuelta.id_staging))  # no .count(): su subconsulta pide id_homonimo (migración 016)
        .filter(StagingEntidadNoResuelta.id_documento.in_(ids_docs), StagingEntidadNoResuelta.resuelto == False)
        .scalar()
    )
    if _estado_flujo_lote(db, ids_docs, pendientes) == "CONSOLIDADO":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"mensaje": "El lote ya fue consolidado y está en modo solo lectura.", "estado_flujo": "CONSOLIDADO"},
        )
