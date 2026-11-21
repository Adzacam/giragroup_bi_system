"""Consolidación de los registros aprobados en el Data Warehouse."""
import hashlib
import logging
import re
import threading
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from pipeline.semantic.indice_confianza import BANDA_CONSOLIDADO, BANDA_REVISION, BANDA_STAGING
from services.clave_fila import ContadorOcurrencias, clave_contenido
from services.dw_loader import DWLoaderService, normalizar_nota_base_100
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.dim_origen import DimOrigenDocumental
from models.log_pipeline import LogPipelineIngesta
from sqlalchemy.orm import Session
from core.database import SessionLocal, get_db
from models.staging_entidad import StagingEntidadNoResuelta
from models.staging_registro import StagingRegistroCrudo
from models.user import User
from services.confianza_service import banda_de, indices_cascada, obtener_indices
from services import beto_integracion, cache_consultas, tareas_dataops
from services.cobranza_canonica import registros_cobranza
from services.extraccion_por_encabezado import campos_por_encabezado, factores_escala_por_programa, fecha_de_fila, fila_resuelta_por_regla, metricas_captacion, MOTIVOS_A_BANDEJA, motivo_fila_sin_entidad, normalizar_encabezado, registro_planificacion, registros_academicos, registros_asignacion_docente, registros_costo_programa, registros_evaluacion, registros_rentabilidad, registros_techo_convenio
from datetime import datetime
from services.dataops_evaluation_service import enmascarar_ci, strip_accents
from core.security import require_roles
from ._comun import ConfirmDwInsertRequest, UMBRAL_INDICE_REGISTRO_DEC, categoria_ruteo as resolver_categoria_ruteo
from .revision import _bloquear_documentos_editables, resolve_review_item
from .extraccion import EXCLUIR_CELDA_BETO, _docentes_con_contexto, extract_entities_from_line
from models.log_inconsistencia import LogInconsistencia
from pipeline.config import MOTIVO_DESACUERDO_REGLA_BETO
from .evaluacion import _asegurar_lote_editable, _resolver_documentos_lote

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/preparar-revision")
def preparar_revision(
    payload: ConfirmDwInsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """Fase A (W-5): ejecuta resolución de identidad y crea casos HITL en stg_entidad_no_resuelta sin cargar hechos."""
    payload.solo_revision = True
    return confirm_dw_insert(payload=payload, db=db, current_user=current_user)


@router.post("/confirm-dw-insert")
def confirm_dw_insert(
    payload: ConfirmDwInsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["ADMIN", "AUDITOR_CALIDAD"])),
):
    """
    Confirma e inserta transaccionalmente los registros aprobados en el Data Warehouse (#8, #9, #10):
    - Si recibe `resolved_item_id`, delega la resolución individual a `resolve_review_item`.
    - Ruteo determinista leyendo `dim_origen_documental.tipo_fuente`:
      * 'COBRANZA' -> `fact_situacion_financiera` (con cálculo de `tipo_alerta = 'RIESGO_CARTERA'` si `cuotas_impagas >= 2`)
      * 'ACTA' / 'MOODLE' -> `fact_rendimiento_academico` (con `nota_final` normalizada a base 100)
      * 'ADMISION' -> `dim_estudiante`
    - Devuelve `inserted_dw = inserted_academico + inserted_financiero` y `desglose: { inserted_academico, inserted_financiero }`.
    """
    if payload.resolved_item_id is not None:
        return resolve_review_item(
            str(payload.resolved_item_id),
            payload={
                "accion": payload.accion or "APROBAR",
                "motivo": payload.motivo,
                "texto_editado": payload.texto_editado,
            },
            db=db,
            current_user=current_user,
        )
    from services import revision_consulta as revision
    if payload.en_segundo_plano and not payload.id_lote:
        raise HTTPException(422, 'Selecciona un lote para consolidar.')
    if payload.id_lote:
        _asegurar_lote_editable(db, payload.id_lote)
    docs = revision.documentos(db, payload.id_lote, payload.doc_id) if (payload.id_lote or payload.doc_id) else []
    _bloquear_documentos_editables(db, docs)
    if not payload.en_segundo_plano:
        return _consolidar(payload, db, current_user)
    tipo_tarea = 'PREPARACION_REVISION' if payload.solo_revision else 'CONSOLIDACION'
    if payload.solo_revision and payload.id_lote:
        for tipo_done in ('PREPARACION_REVISION', 'CONSOLIDACION'):
            prev_done = tareas_dataops.ultima_en_sesion(db, payload.id_lote, tipo_done)
            if prev_done and prev_done['estado'] == 'COMPLETADA':
                return {'status': 'already_prepared', 'tarea_id': prev_done['id'], 'tarea': prev_done}
    for tipo in ('INGESTA', 'LECTURA_BETO', 'PREPARACION_REVISION', 'CONSOLIDACION'):
        previa = tareas_dataops.ultima_en_sesion(db, payload.id_lote, tipo)
        if previa and previa['estado'] == 'EN_CURSO':
            if tipo == tipo_tarea:
                return {'status': 'accepted', 'tarea_id': previa['id'], 'tarea': previa}
            if tipo in ('PREPARACION_REVISION', 'CONSOLIDACION'):
                raise HTTPException(409, 'Espera a que termine la preparación de revisión o consolidación del lote.')
            raise HTTPException(409, 'Espera a que termine la carga y lectura del lote.')
    try:
        tarea_id = tareas_dataops.crear_en_sesion(db, tipo_tarea, payload.id_lote)
        if not tarea_id:
            raise RuntimeError('No se reservó una tarea')
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(503, 'No se pudo iniciar la consolidación. Inténtalo de nuevo.') from exc
    user_id = current_user.id

    def _en_segundo_plano():
        db_tarea = SessionLocal()
        try:
            usuario = db_tarea.query(User).filter(User.id == user_id).first()
            resultado = _consolidar(payload, db_tarea, usuario, tarea_id=tarea_id)
            tareas_dataops.terminar(tarea_id, resultado)
        except Exception as e_tarea:
            db_tarea.rollback()
            logger.exception("Consolidación en segundo plano falló (tarea %s)", tarea_id)
            tareas_dataops.fallar(tarea_id, getattr(e_tarea, "detail", None) or str(e_tarea))
        finally:
            db_tarea.close()

    threading.Thread(target=_en_segundo_plano, name=f"consolidacion-{tarea_id}", daemon=True).start()
    return {"status": "accepted", "tarea_id": tarea_id, "tarea": tareas_dataops.obtener(tarea_id)}


def _consolidar(payload: ConfirmDwInsertRequest, db: Session, current_user: Optional[User],
                tarea_id: Optional[int] = None) -> Dict[str, Any]:
    if payload.id_lote:
        _bloquear_documentos_editables(db, db.query(DimOrigenDocumental).filter_by(id_lote=payload.id_lote).all())
    solo_revision = bool(getattr(payload, "solo_revision", False))
    dw = DWLoaderService(db)
    dw.diferir_eval = not solo_revision  # evaluación docente (decenas de miles de respuestas): inserción en bloque al final, no un INSERT por fila
    dw.solo_revision = solo_revision
    if tarea_id:
        dw.al_latir = lambda: tareas_dataops.latir(tarea_id)  # escrituras en bloque: la tarea sigue viva sin avanzar líneas
    thresh = payload.threshold or UMBRAL_INDICE_REGISTRO_DEC

    effective_doc_id = payload.doc_id
    if effective_doc_id is None and payload.id_documento is not None:
        if payload.id_lote is None or payload.id_documento != payload.id_lote:
            effective_doc_id = payload.id_documento

    query = db.query(StagingRegistroCrudo).filter(StagingRegistroCrudo.es_ruido == False)
    if payload.record_ids:
        query = query.filter(StagingRegistroCrudo.id.in_(payload.record_ids))
    elif effective_doc_id:
        query = query.filter(StagingRegistroCrudo.id_documento == effective_doc_id)
    elif payload.id_lote:
        _, docs_lote, _ = _resolver_documentos_lote(db, payload.id_lote)
        if not docs_lote:
            raise HTTPException(404, 'El lote no existe.')
        query = query.filter(StagingRegistroCrudo.id_documento.in_([d.id_documento for d in docs_lote]))

    stg_records = query.order_by(StagingRegistroCrudo.id.asc()).all()  # orden fijo: el resultado no depende del orden físico de la tabla

    estudiantes = db.query(DimEstudiante).filter(DimEstudiante.deprecado == False).all()
    docentes = _docentes_con_contexto(db)
    modulos = db.query(DimModulo).all()

    inserted_academico = 0
    inserted_financiero = 0
    inserted_admision = 0
    sent_hitl = 0
    inserted_revision = 0
    descartados_ruido = 0
    enviados_a_bandeja_sin_identidad = 0
    descartes_por_regla = {}

    doc_ids_stg = {s.id_documento for s in stg_records if s.id_documento}
    origenes_map = {
        o.id_documento: o
        for o in db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento.in_(doc_ids_stg)).all()
    } if doc_ids_stg else {}
    if not solo_revision and doc_ids_stg:
        dw.casos_existentes_fase_a = Counter(
            db.query(
                StagingEntidadNoResuelta.id_documento,
                StagingEntidadNoResuelta.motivo,
                StagingEntidadNoResuelta.texto_original,
            )
            .filter(
                StagingEntidadNoResuelta.id_documento.in_(doc_ids_stg),
                StagingEntidadNoResuelta.tipo_entidad != "RUIDO",
            )
            .all()
        )

    # Escala de notas por programa en cada archivo: un acta mezcla programas sobre 20 y sobre 100
    filas_por_doc: Dict[Any, List[Dict[str, str]]] = {}
    for s_reg in stg_records:
        for l in (s_reg.texto_plano or "").splitlines():
            if "MODULO" in normalizar_encabezado(l):
                filas_por_doc.setdefault(s_reg.id_documento, []).append(
                    campos_por_encabezado([c.strip() for c in l.split("|")]))
    factores_por_doc = {
        d: factores_escala_por_programa(filas, (origenes_map.get(d).tipo_escala if origenes_map.get(d) else None))
        for d, filas in filas_por_doc.items()
    }
    total_lineas = sum(len([l for l in (s_reg.texto_plano or "").splitlines() if l.strip()]) for s_reg in stg_records)
    # Avance con el total real de líneas (sin ×2 al reutilizar cache_indice_beto)
    lineas_hechas = 0
    tareas_dataops.avanzar(tarea_id, 0, total_lineas, forzar=True)

    def _al_indexar(n):
        pass  # el avance real se reporta por bloque en el ciclo principal

    # Precargar una sola vez por documento los registros ya existentes en stg_entidad_no_resuelta
    ruido_visto_por_doc: Dict[Any, set] = {}
    if doc_ids_stg:
        for d_id, reg_id, txt in db.query(
            StagingEntidadNoResuelta.id_documento,
            StagingEntidadNoResuelta.registro_origen_id,
            StagingEntidadNoResuelta.texto_original,
        ).filter(StagingEntidadNoResuelta.id_documento.in_(doc_ids_stg)).all():
            ruido_visto_por_doc.setdefault((d_id, reg_id), set()).add(txt)

    ocurrencias = ContadorOcurrencias()
    # Flags BETO_CASCADA_FINAL / BETO_ACUERDO_QC (services/beto_integracion.py); apagados: camino original
    contadores_beto = beto_integracion.Contadores()
    cliente_beto = beto_integracion.ClienteBeto(contadores=contadores_beto) if beto_integracion.necesita_refinar() else None
    sugeridor = None
    if beto_integracion.activo("BETO_SUGERENCIA_HITL"):   # opción 3: candidatos ordenados en la bandeja; solo ordena
        sugeridor = beto_integracion.hacer_sugeridor(cliente_beto or beto_integracion.ClienteBeto(contadores=contadores_beto), estudiantes)
        dw.sugeridor = sugeridor
    for stg in stg_records:
        orig_doc = origenes_map.get(stg.id_documento) if stg.id_documento else None
        doc_fuente = (orig_doc.tipo_fuente if (orig_doc and orig_doc.tipo_fuente) else "ACTA").upper().strip()
        # D-A4: una hoja Likert queda en staging como 'evaluacion_docente' aunque el libro esté como ACTA (el contenido del
        # bloque manda sobre el tipo del documento, ingestion_service). La consolidación respeta la categoría de la hoja.
        if (stg.categoria or "").strip().lower() == "evaluacion_docente":
            doc_fuente = "EVALUACION_DOCENTE"
        doc_escala = orig_doc.tipo_escala if orig_doc else "CENTESIMAL_100"
        if doc_fuente in ("COBRANZA", "ADMISION"):
            doc_escala = None
        elif not doc_escala:
            doc_escala = "CENTESIMAL_100"
        factores_escala = factores_por_doc.get(stg.id_documento)

        institucion = (orig_doc.institucion if orig_doc else None) or "GiraGroup Posgrado"

        raw_text = (stg.texto_plano or "").strip()
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        if not lines and raw_text:
            lines = [raw_text]

        stg_cat = (stg.categoria or "").strip().lower()
        if stg_cat in ("planificacion", "planificacion_meta") or doc_fuente == "PLANIFICACION":
            sha_doc = (orig_doc.hash_sha256 if orig_doc and orig_doc.hash_sha256 else str(stg.id_documento))
            payload_stg = stg.payload_json if isinstance(stg.payload_json, dict) else {}
            if stg_cat == "planificacion_meta":
                for idx_m, meta in enumerate(payload_stg.get("metas_planificacion") or []):
                    lineas_hechas += 1
                    c_orig = hashlib.sha256(f"{sha_doc}|{meta.get('celda_origen', idx_m)}".encode("utf-8")).hexdigest()
                    c_cont = hashlib.sha256(
                        f"{meta.get('categoria')}|{meta.get('gestion')}|{meta.get('mes')}|{meta.get('tipo_programa')}|{meta.get('monto_meta')}".encode("utf-8")
                    ).hexdigest()
                    res = dw.cargar_registro({
                        "doc_id": stg.id_documento,
                        "categoria": "planificacion_meta",
                        "clave_origen": c_orig,
                        "clave_contenido": c_cont,
                        "resoluciones": meta,
                        "calidad": {"requiere_revision": False},
                    })
                    if res.get("status") == "loaded":
                        inserted_academico += 1
                continue

            filas_excel = payload_stg.get("filas_excel") or []
            anio_hoja = payload_stg.get("anio_hoja")
            mes_hoja = payload_stg.get("mes_hoja")
            for k_fila, line in enumerate(lines):
                lineas_hechas += 1
                if lineas_hechas % 250 == 0:
                    tareas_dataops.avanzar(tarea_id, lineas_hechas)
                campos_linea = campos_por_encabezado([c.strip() for c in line.split("|")])
                fila_ex = filas_excel[k_fila] if k_fila < len(filas_excel) else ((stg.fila_inicio or 0) + k_fila)
                reg_plan = registro_planificacion(
                    campos_linea, hoja=stg.hoja or "", anio_hoja=anio_hoja, mes_hoja=mes_hoja
                )
                reg_plan["fila_excel"] = fila_ex
                c_orig = hashlib.sha256(f"{sha_doc}|{stg.hoja}|{fila_ex}|{line}".encode("utf-8")).hexdigest()
                c_cont = clave_contenido(doc_fuente, stg.hoja or "", line, ocurrencias.siguiente(stg.hoja or "", line))
                res = dw.cargar_registro({
                    "doc_id": stg.id_documento,
                    "categoria": "planificacion",
                    "clave_origen": c_orig,
                    "clave_contenido": c_cont,
                    "resoluciones": reg_plan,
                    "calidad": {"requiere_revision": False},
                })
                if res.get("status") == "loaded":
                    inserted_academico += 1
            continue

        categoria_ruteo = resolver_categoria_ruteo(doc_fuente, stg.categoria)

        # Índice final real (BETO local) por línea: >= 0.85 hecho, [0.60, 0.85) hecho en revisión, < 0.60 staging
        # D-A8a: las filas que una regla ya resolvió (rentabilidad: categoría + mes) no van a BETO ni caen a staging por su índice
        campos_por_linea = [campos_por_encabezado([c.strip() for c in l.split("|")]) for l in lines]
        resueltas_regla = [fila_resuelta_por_regla(c, categoria_ruteo) for c in campos_por_linea]
        indices_linea = indices_cascada(lines, resueltas_regla, obtener_indices, al_avanzar=_al_indexar)
        refinadas = None
        if cliente_beto is not None:
            refinadas = beto_integracion.refinar_lineas(
                lines,
                lambda l, **kw: extract_entities_from_line(l, estudiantes, docentes, modulos, tipo_escala=doc_escala, tipo_fuente=doc_fuente, **kw),
                tipo_fuente=doc_fuente, cliente=cliente_beto, contadores=contadores_beto,
                archivo=orig_doc.nombre_archivo if orig_doc else None,
                omitir=lambda l: bool(motivo_fila_sin_entidad(campos_por_encabezado([c.strip() for c in l.split("|")]), categoria_ruteo)),
                excluir_celda=EXCLUIR_CELDA_BETO)
        logs_descarte_stg = []
        stg_descarte_stg = []
        unres_stg = []
        ruido_visto_stg = ruido_visto_por_doc.setdefault((stg.id_documento, stg.id), set())
        for k_fila, (line, indice, campos_linea) in enumerate(zip(lines, indices_linea, campos_por_linea)):
            lineas_hechas += 1
            if lineas_hechas % 250 == 0:
                tareas_dataops.avanzar(tarea_id, lineas_hechas)
            motivo_ruido = motivo_fila_sin_entidad(campos_linea, categoria_ruteo)
            if motivo_ruido:
                if not solo_revision:
                    # Sin entidad que enlazar (hoja de estados, catálogo, fila agregada): acumula en lote sin autoflush (F3-1)
                    _registrar_descarte_ruido(
                        db, stg, line, indice, motivo_ruido, doc_fuente,
                        fila_origen=(stg.fila_inicio or 0) + k_fila,
                        logs_out=logs_descarte_stg, stg_out=stg_descarte_stg, ruido_visto=ruido_visto_stg,
                        pendiente=motivo_ruido in MOTIVOS_A_BANDEJA,
                    )
                if motivo_ruido in MOTIVOS_A_BANDEJA:
                    # ADW-L8 (DA7): sin estudiante pero con dinero o sin patrón claro: no se descarta, la ve una persona
                    enviados_a_bandeja_sin_identidad += 1
                    continue
                descartados_ruido += 1
                descartes_por_regla[motivo_ruido] = descartes_por_regla.get(motivo_ruido, 0) + 1
                continue
            r_beto = refinadas[k_fila] if refinadas is not None else None
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
                )
            banda = BANDA_CONSOLIDADO if resueltas_regla[k_fila] else banda_de(indice)
            is_approved = banda != BANDA_STAGING
            # Lecturas dudosas del extractor (CI con '?', escala ambigua) no se descartan: quedan en revisión
            en_revision = banda == BANDA_REVISION or req_rev
            if indice is not None:
                score = indice
            if r_beto is not None and r_beto.acuerdo == beto_integracion.DESACUERDO and is_approved:
                # Opción 2: las reglas ven una persona que BETO no ve. La confianza baja un escalón y el hecho queda en revisión
                score = beto_integracion.bajar_un_escalon(score)
                en_revision = True
                if not solo_revision:
                    db.add(LogInconsistencia(
                        id_documento=stg.id_documento, fila_origen=(stg.fila_inicio or 0) + k_fila, campo_afectado="persona",
                        valor_recibido=str(next((e.get("token") for e in ents if e.get("label") in ("ESTUDIANTE", "DOCENTE") and e.get("acuerdo_beto") == beto_integracion.DESACUERDO), ""))[:2000],
                        valor_esperado="BETO: sin entidad persona en ese tramo", tipo_regla=MOTIVO_DESACUERDO_REGLA_BETO, severidad="BAJA",
                        estado_resolucion="PENDIENTE", descripcion="La regla resolvió una persona que BETO etiqueta como O; confianza bajada un escalón y hecho en revisión"))

            ci_tok = next((e["token"] for e in ents if "CI" in e.get("label", "")), None)
            if ci_tok == "No provisto":
                ci_tok = None
            ci_clean = ci_tok.replace("?", "").strip() if ci_tok else None

            nombre_est = next((e.get("matchedCanonical") or e.get("token") for e in ents if e.get("label") in ("ESTUDIANTE", "ALUMNO")), None)
            nombre_doc = next((e.get("matchedCanonical") or e.get("token") for e in ents if e.get("label") == "DOCENTE"), None)
            nombre_mod = next((e.get("matchedCanonical") or e.get("token") for e in ents if e.get("label") == "MÓDULO"), None)
            nombre_prog = next((e.get("matchedCanonical") or e.get("token") for e in ents if e.get("label") == "PROGRAMA"), None)

            grade_ent = next((e for e in ents if e.get("label") == "CALIFICACIÓN"), None)
            grade_norm = grade_ent.get("notaNormalizada") if grade_ent else None
            if grade_norm is None and grade_ent:
                num_m = re.search(r"[0-9]+(?:\.[0-9]+)?", str(grade_ent.get("token", "")))
                if num_m:
                    grade_norm = normalizar_nota_base_100(float(num_m.group(0)), doc_escala)

            monto_ent = next((e for e in ents if e.get("label") == "MONTO"), None)
            concepto_ent = next((e for e in ents if e.get("label") == "CONCEPTO_FINANCIERO"), None)

            monto_deuda_val = monto_ent.get("valorNumerico") if monto_ent else 0.0
            monto_pagado_val = monto_ent.get("montoPagado") if monto_ent else 0.0
            cuotas_impagas_val = monto_ent.get("cuotasImpagas") if monto_ent else 0
            concepto_str = concepto_ent.get("token") if concepto_ent else None

            # Si las etiquetas de la fila contienen CUOTAS_IMPAGAS o MORA directamente
            for ch in line.split("|"):
                if ":" in ch:
                    k_ch, v_ch = ch.split(":", 1)
                    k_up = strip_accents(k_ch).upper().strip()
                    if k_up in ("CUOTAS_IMPAGAS", "MORA", "CUOTAS_MORA"):
                        m_c = re.search(r"\d+", v_ch)
                        if m_c:
                            cuotas_impagas_val = int(m_c.group(0))
                    elif k_up in ("MONTO_DEUDA", "SALDO", "DEUDA", "MONTO"):
                        m_d = re.search(r"[0-9]+(?:\.[0-9]+)?", v_ch)
                        if m_d:
                            monto_deuda_val = float(m_d.group(0))
                    elif k_up in ("MONTO_PAGADO", "PAGADO", "ABONO"):
                        m_p = re.search(r"[0-9]+(?:\.[0-9]+)?", v_ch)
                        if m_p:
                            monto_pagado_val = float(m_p.group(0))
                    elif k_up in ("CONCEPTO", "CONCEPTO_FINANCIERO"):
                        concepto_str = v_ch.strip()

            if is_approved:
                fecha_linea = fecha_de_fila(campos_linea, categoria_ruteo) if campos_linea else None
                reg_dict = {
                    **({"beto_texto": beto_integracion.texto_para_beto(line)} if sugeridor is not None else {}),
                    "categoria": categoria_ruteo,
                    "tipo_fuente": doc_fuente,
                    "tipo_escala": doc_escala,
                    "institucion": institucion,
                    "doc_id": stg.id_documento,
                    "clave_contenido": clave_contenido(doc_fuente, stg.hoja, line, ocurrencias.siguiente(stg.hoja, line)),
                    "clave_origen": hashlib.sha256(
                        f"{(orig_doc.hash_sha256 or orig_doc.nombre_archivo) if orig_doc else stg.id_documento}|{stg.hoja}|{(stg.fila_inicio or 0) + k_fila}|{line}".encode("utf-8")).hexdigest(),
                    "resoluciones": {
                        "estudiante": {
                            "fk_resolucion": {
                                "ci": ci_clean,
                                "nombre_resuelto": nombre_est,
                            },
                            "valor_extraido": nombre_est,
                        },
                        "docente": {"valor_extraido": nombre_doc},
                        "modulo": {"valor_extraido": nombre_mod},
                        "programa": {"valor_extraido": nombre_prog},
                        "nota_final": grade_norm,
                        "nota_ya_normalizada": True,
                        "monto_deuda": monto_deuda_val,
                        "monto_pagado": monto_pagado_val,
                        "cuotas_impagas": cuotas_impagas_val,
                        "estado_cartera": (
                            derivar_estado_cartera(campos_linea, cuotas_impagas_val)
                            if categoria_ruteo == "financiero"
                            else None
                        ),
                        "concepto": concepto_str,
                        "nivel_confianza_ia": score,
                        "fecha": fecha_linea,
                    },
                    "calidad": {"requiere_revision": en_revision},
                }
                registros_linea = [reg_dict]
                if categoria_ruteo == "academico" and campos_linea:
                    # Acta con columnas MÓDULO 1..12 (ARCA): un hecho por módulo con su nota real
                    registros_linea = []
                    # Hoja de asignaciones (POS + módulo + docente, sin estudiante): docente de cada módulo
                    for reg_asig in registros_asignacion_docente(campos_linea):
                        reg_asig.pop("requiere_revision")
                        registros_linea.append({
                            **reg_dict,
                            "resoluciones": {**reg_dict["resoluciones"], **reg_asig},
                            "calidad": {"requiere_revision": en_revision},
                        })
                    for reg_aca in registros_academicos(campos_linea, factores_escala):
                        revision_fila = reg_aca.pop("requiere_revision")
                        registros_linea.append({
                            **reg_dict,
                            "resoluciones": {
                                **reg_dict["resoluciones"],
                                **{k: v for k, v in reg_aca.items() if v is not None or k in ("nota_final", "fecha")},
                            },
                            "calidad": {"requiere_revision": en_revision or revision_fila},
                        })
                elif categoria_ruteo == "evaluacion_docente" and campos_linea:
                    # Encuesta: un hecho por pregunta respondida. La identidad sale de las columnas, no del NER:
                    # una respuesta anónima queda sin estudiante en vez de crear 'ENTRADA ANONIMA - PERSONA 5'
                    registros_linea = []
                    for reg_eval in registros_evaluacion(campos_linea):
                        revision_fila = reg_eval.pop("requiere_revision")
                        registros_linea.append({
                            **reg_dict,
                            "resoluciones": {
                                **reg_dict["resoluciones"],
                                **reg_eval,
                                "estudiante": reg_eval["estudiante"] or {},
                                "anonima": reg_eval["estudiante"] is None,
                                "docente": reg_eval["docente"] or reg_dict["resoluciones"].get("docente"),
                                "modulo": reg_eval["modulo"] or reg_dict["resoluciones"].get("modulo"),
                                "programa": reg_eval["programa"] or reg_dict["resoluciones"].get("programa"),
                            },
                            "calidad": {"requiere_revision": en_revision or revision_fila},
                        })
                elif categoria_ruteo == "financiero" and campos_linea and (lectura_cob := registros_cobranza(campos_linea, fecha_linea)) is not None:
                    # FU-L2: fila de cobranza leída por campos canónicos del catálogo (sin nombres de columna en el
                    # código): un hecho de situación en la fecha de inicio y un pago por mes, cada uno con su clave
                    registros_linea = []
                    for reg_cob in lectura_cob[0]:
                        revision_fila = reg_cob.pop("_revision_fila")
                        registros_linea.append({
                            **reg_dict,
                            "resoluciones": {**reg_dict["resoluciones"], **reg_cob, "estado_cartera": None,
                                             "_revision_fila": revision_fila},
                            "calidad": {"requiere_revision": en_revision or revision_fila},
                        })
                elif categoria_ruteo in ("marketing", "admision") and campos_linea and registros_techo_convenio(campos_linea):
                    # Convenio con institución en un documento clasificado como marketing (p. ej. BD Techos):
                    # el contenido de la fila decide el hecho, no la clasificación del documento
                    registros_linea = []
                    for reg_techo in registros_techo_convenio(campos_linea):
                        revision_fila = reg_techo.pop("requiere_revision")
                        registros_linea.append({
                            **reg_dict,
                            "resoluciones": {**reg_dict["resoluciones"], **reg_techo},
                            "calidad": {"requiere_revision": en_revision or revision_fila},
                        })
                elif categoria_ruteo == "rentabilidad" and campos_linea:
                    # EJECUTADO VS META: un hecho por año con dato, con la categoría y el mes de la fila
                    registros_rent = registros_rentabilidad(campos_linea)
                    if registros_rent:
                        registros_linea = [
                            {**reg_dict, "resoluciones": {**reg_dict["resoluciones"], **reg_rent}}
                            for reg_rent in registros_rent
                        ]
                    else:
                        # Costos por programa (egreso, ingreso, rentabilidad por POS): un hecho por programa
                        registros_linea = []
                        # Costos por programa o, si no, convenios con instituciones (techos)
                        for reg_costo in (registros_costo_programa(campos_linea) or registros_techo_convenio(campos_linea)):
                            revision_fila = reg_costo.pop("requiere_revision")
                            registros_linea.append({
                                **reg_dict,
                                "resoluciones": {**reg_dict["resoluciones"], **reg_costo},
                                "calidad": {"requiere_revision": en_revision or revision_fila},
                            })
                if categoria_ruteo == "marketing" and campos_linea:
                    for reg_item in registros_linea:
                        reg_item["resoluciones"].update(metricas_captacion(campos_linea))
                for reg_item in registros_linea:
                    res = dw.cargar_registro(reg_item)
                    if res.get("status") in ("skipped", "skipped_solo_revision"):  # respuesta vacía o Fase A sin carga de hechos
                        continue
                    if res.get("status") != "loaded":
                        sent_hitl += 1
                        continue
                    if reg_item["calidad"]["requiere_revision"]:
                        inserted_revision += 1
                    tipo_loaded = res.get("tipo")
                    if tipo_loaded == "financiero":
                        inserted_financiero += 1
                    elif tipo_loaded == "admision":
                        inserted_admision += 1
                    else:
                        inserted_academico += 1  # académicos, evaluación docente, rentabilidad y marketing
            else:
                sent_hitl += 1
                motivo_canonico = "BAJA_CONFIANZA_IA"
                if ci_tok and "?" in ci_tok:
                    motivo_canonico = "CI_DUDOSA"
                elif grade_ent and grade_ent.get("canonicalId") in ("ESCALA_AMBIGUA", "NOTA_FUERA_ESCALA"):
                    motivo_canonico = grade_ent.get("canonicalId")

                exists_unres = (line in ruido_visto_stg) or (line[:250] in ruido_visto_stg)
                if not exists_unres:
                    ruido_visto_stg.add(line[:250])
                    stg_unresolved = StagingEntidadNoResuelta(
                        id_documento=stg.id_documento,
                        tipo_entidad="CONCEPTO_FINANCIERO" if doc_fuente == "COBRANZA" else "ESTUDIANTE",
                        texto_original=line[:250],
                        ci_temporal=ci_clean,
                        mejor_candidato=nombre_est or nombre_mod,
                        score_fuzzy=round(score * 100, 2),
                        fk_estado="C",
                        nivel_confianza=score,
                        resuelto=False,
                        motivo=motivo_canonico,
                        payload_json={
                            "raw_line": line,
                            "ci_real": ci_clean,
                            "ci_enmascarado": enmascarar_ci(ci_clean),
                            "entities": ents,
                            "score": score,
                            "tipo_fuente": doc_fuente,
                            "tipo_escala": doc_escala,
                            **({"sugerencias": sugeridor(nombre_est, None, beto_integracion.texto_para_beto(line))}
                               if (sugeridor is not None and nombre_est) else {}),
                        },
                        registro_origen_id=stg.id,
                        estado_resolucion="PENDIENTE",
                    )
                    unres_stg.append(stg_unresolved)

        if logs_descarte_stg:
            db.add_all(logs_descarte_stg)
        if stg_descarte_stg:
            db.add_all(stg_descarte_stg)
        if unres_stg:
            db.add_all(unres_stg)

    tareas_dataops.avanzar(tarea_id, total_lineas, total_lineas, forzar=True)
    if not solo_revision:
        dw.finalizar_cargas()
    db.commit()
    if not solo_revision:
        cache_consultas.invalidar()  # el DW cambió: alertas, CMI y forecast se recalculan
    inserted_total = inserted_academico + inserted_financiero

    # Registrar auditoría en LogPipelineIngesta y emitir notificación de consolidación DW
    try:
        user_name = current_user.username if current_user else "Auditor Calidad"
        doc_ref_id = effective_doc_id or (stg_records[0].id_documento if stg_records else None)
        audit_pipe = LogPipelineIngesta(
            id_documento=doc_ref_id,
            etapa="PREPARACION_REVISION" if solo_revision else "DW_CONSOLIDACION",
            nivel="SUCCESS",
            modulo="DataOps Pipeline",
            mensaje=(
                f"Preparación de revisión (Fase A) por {user_name}: {sent_hitl} casos detectados, 0 hechos cargados."
                if solo_revision else
                f"Consolidación exitosa en Data Warehouse por {user_name}: {inserted_total} registros (+{inserted_academico} académicos, +{inserted_financiero} financieros)."
            ),
            metadata_json={
                "id_lote": payload.id_lote,
                "inserted_total": inserted_total,
                "inserted_academico": inserted_academico,
                "inserted_financiero": inserted_financiero,
                "sent_hitl": sent_hitl,
                "inserted_revision": inserted_revision,
                "usuario": user_name,
                **({"beto": contadores_beto.como_dict()} if cliente_beto is not None else {}),
            }
        )
        db.add(audit_pipe)
        db.commit()

    except Exception as e_aud_dw:
        logger.warning("No se pudo registrar auditoría/notificación de consolidación DW: %s", e_aud_dw)

    resp = {
        "status": "success",
        "solo_revision": solo_revision,
        "message": (
            f"Revisión preparada (Fase A): {sent_hitl} casos derivados a Revisión Humana, 0 hechos cargados."
            if solo_revision else
            f"Transacción completada: {inserted_total} hechos persistidos en Data Warehouse "
            f"({inserted_academico} académicos, {inserted_financiero} financieros), "
            f"{sent_hitl} derivados a Revisión Humana."
        ),
        "inserted_dw": inserted_total,
        "desglose": {
            "inserted_academico": inserted_academico,
            "inserted_financiero": inserted_financiero,
        },
        "inserted_academico": inserted_academico,
        "inserted_financiero": inserted_financiero,
        "inserted_admision": inserted_admision,
        "inserted_revision": inserted_revision,
        "sent_hitl": sent_hitl,
        "descartados_ruido": descartados_ruido,
        "descartes_por_regla": descartes_por_regla,
        "enviados_a_bandeja_sin_identidad": enviados_a_bandeja_sin_identidad,
        **({"beto": contadores_beto.como_dict()} if cliente_beto is not None else {}),
    }
    dw.liberar_memoria()
    from .extraccion import _MEMO_CATALOGOS, _MEMO_LOCK
    with _MEMO_LOCK:
        _MEMO_CATALOGOS.clear()
    import gc
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass
    return resp


def derivar_estado_cartera(campos_linea: Optional[dict], cuotas_impagas: int = 0) -> str:
    """
    Estado de cartera del hecho por la regla única DA3 (decisión de Lean, 2026-11-20): 'Mora' si
    cuotas_impagas >= 2, si no 'Vigente'. Los días de mora, el rango de mora y el tipo de cartera de la fuente
    ya no deciden la mora (antes un día de atraso o un rango 'd) Mayor 361' bastaban: KPI-05 ≈ 94 %); el tipo de
    cartera se guarda aparte como estado_cartera_fuente (FU-L2). `campos_linea` se mantiene por compatibilidad.
    """
    from services.regla_mora import estado_cartera_da3
    return estado_cartera_da3(int(cuotas_impagas or 0))


def _registrar_descarte_ruido(
    db: Session,
    stg,
    line: str,
    indice,
    motivo: str,
    doc_fuente: str,
    fila_origen: Optional[int] = None,
    logs_out: Optional[list] = None,
    stg_out: Optional[list] = None,
    ruido_visto: Optional[set] = None,
    pendiente: bool = False,
) -> None:
    """Deja constancia de una línea descartada como ruido: en log_inconsistencias (1:1 por línea) y en stg_entidad_no_resuelta.
    Con `pendiente=True` (ADW-L8, DA7) la línea no se descarta: queda PENDIENTE en la bandeja de revisión humana."""
    from core.esquema_opcional import valores_si_existen

    log_obj = LogInconsistencia(
        id_documento=stg.id_documento,
        fila_origen=fila_origen,
        campo_afectado=(stg.hoja or "")[:100],
        valor_recibido=(line or "")[:500],
        tipo_regla="LINEA_SIN_IDENTIDAD" if pendiente else "LINEA_SIN_ENTIDAD",
        **valores_si_existen(db, "log_inconsistencias", regla_origen=(motivo or "")[:80]),
        severidad="MEDIA" if pendiente else "BAJA",
        estado_resolucion="PENDIENTE" if pendiente else "DESCARTADO",
        descripcion=(f"Línea sin identidad reconocible enviada a revisión ({motivo}) en hoja '{stg.hoja}'" if pendiente
                     else f"Línea descartada por regla ({motivo}) en hoja '{stg.hoja}'"),
    )
    if logs_out is not None:
        logs_out.append(log_obj)
    else:
        db.add(log_obj)

    clave_txt = line[:250]
    if ruido_visto is not None:
        if clave_txt in ruido_visto:
            return
        ruido_visto.add(clave_txt)
    else:
        ya_registrada = db.query(StagingEntidadNoResuelta.id_staging).filter(
            StagingEntidadNoResuelta.id_documento == stg.id_documento,
            StagingEntidadNoResuelta.registro_origen_id == stg.id,
            StagingEntidadNoResuelta.texto_original == clave_txt,
        ).first()
        if ya_registrada:
            return

    stg_obj = StagingEntidadNoResuelta(
        id_documento=stg.id_documento,
        tipo_entidad="ESTUDIANTE" if pendiente else "RUIDO",
        texto_original=clave_txt,
        fk_estado="C",
        nivel_confianza=indice,
        resuelto=not pendiente,
        resuelto_en=None if pendiente else datetime.utcnow(),
        motivo=motivo,
        estado_resolucion="PENDIENTE" if pendiente else "DESCARTADO",
        payload_json={"raw_line": line, "tipo_fuente": doc_fuente, **({} if pendiente else {"descarte": "RUIDO"})},
        registro_origen_id=stg.id,
    )
    if stg_out is not None:
        stg_out.append(stg_obj)
    else:
        db.add(stg_obj)
