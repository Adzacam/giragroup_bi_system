"""
backend/routers/pipeline.py
----------------------------
Endpoint unificado para ejecución del pipeline integral de procesamiento de datos:
Dispatcher / Ingesta -> Formateo & BETO NER -> Reglas de Calidad -> Carga a DW con resolución FK.
Protegido por RBAC (AUDITOR_CALIDAD, ADMIN).
"""

import os
import re
import sys
import hashlib
import time
import tempfile
import logging
import unicodedata
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import require_roles
from models.user import User
from models.dim_origen import DimOrigenDocumental
from models.staging_registro import StagingRegistroCrudo
from services.ingestion_service import IngestionService
from services.dw_loader import DWLoaderService
from services import cache_consultas
from services.confianza_service import obtener_indices, indices_en_cache, banda_de
from services.extraccion_por_encabezado import (
    parsear_fecha,
    campos_por_encabezado, es_encabezado_metadato_pos, estudiante_de_fila, fecha_de_fila, registros_academicos, registros_evaluacion, registros_rentabilidad, registros_costo_programa, registros_asignacion_docente, registros_techo_convenio,
    factores_escala_por_programa,
)
from models.staging_entidad import StagingEntidadNoResuelta
from models.log_inconsistencia import LogInconsistencia
from pipeline.semantic.indice_confianza import BANDA_REVISION, BANDA_STAGING
from schemas.pipeline_schemas import PipelineExecutionResponse

logger = logging.getLogger("pipeline_router")

router = APIRouter(prefix="/api/v1/pipeline", tags=["Pipeline Integrado"])


# Encabezados de cobranza reconocidos (sin tildes, mayúsculas). Sin ellos, la heurística
# posicional tomaba el CI como deuda y el celular como CI, y nunca asignaba monto_pagado.
_ENCABEZADOS_FINANCIEROS: Dict[str, tuple] = {
    "ci": ("CI", "CEDULA DE IDENTIDAD", "DOC_IDENTIDAD/CI", "CI_ESTUDIANTE"),
    "monto_deuda": ("DEUDA TOTAL", "MONTO_DEUDA", "SALDO DEUDOR", "SALDO", "DEUDA"),
    "monto_pagado": ("TOTAL PAGADO HASTA LA FECHA", "TOTAL PAGADO", "MONTO PAGADO", "MONTO_PAGADO", "PAGADO"),
    "cuotas_impagas": ("TOTAL CUOTAS EN MORA", "CUOTAS EN MORA", "CUOTAS IMPAGAS", "CUOTAS_IMPAGAS"),
    "nombre_completo": ("NOMBRE COMPLETO", "ESTUDIANTE"),
    "nombres": ("NOMBRES",),
    "paterno": ("PATERNO",),
    "materno": ("MATERNO",),
    "programa": ("NOMBRE DEL PROGRAMA", "PROGRAMA"),
}


def _normalizar_encabezado(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.upper().split())


def _campos_financieros_por_encabezado(celdas: List[str]) -> Optional[Dict[str, str]]:
    """
    Lee celdas 'ENCABEZADO: valor' (formato del ingestor; las celdas vacías se omiten, por lo
    que la posición no es fiable). Retorna:
      - {campo: valor} si la fila trae al menos un monto (deuda, pagado o cuotas en mora);
      - {} si trae encabezados pero ningún monto (resúmenes, tablas de referencia,
        congelados): no es un hecho financiero y no debe pasar por la heurística posicional;
      - None si la fila no trae encabezados (texto sin formato: aplica la heurística).
    """
    por_encabezado = {}
    for c in celdas:
        hdr, sep, val = c.partition(": ")
        if sep:
            por_encabezado.setdefault(_normalizar_encabezado(hdr), val.strip())
    if not por_encabezado:
        return None
    campos = {}
    for campo, alias in _ENCABEZADOS_FINANCIEROS.items():
        for a in alias:
            if por_encabezado.get(a):
                campos[campo] = por_encabezado[a]
                break
    tiene_monto = any(k in campos for k in ("monto_deuda", "monto_pagado", "cuotas_impagas"))
    return campos if tiene_monto else {}


def _a_numero(valor: Optional[str]) -> Optional[float]:
    from pipeline.normalization.montos import parsear_monto
    return parsear_monto(valor)


def _resolver_fila_financiera(campos: Dict[str, str]) -> Dict[str, Any]:
    """Construye las resoluciones financieras a partir de los campos leídos por encabezado."""
    def celda(campo: str) -> Optional[str]:
        val = (campos.get(campo) or "").strip()
        return val if val and val.lower() != "nan" else None

    ci_raw = celda("ci")
    ci = "".join(ch for ch in ci_raw if ch.isalnum()) if ci_raw else None
    nombre = celda("nombre_completo") or " ".join(
        p for p in (celda("nombres"), celda("paterno"), celda("materno")) if p
    ) or None
    cuotas = _a_numero(celda("cuotas_impagas"))
    programa = celda("programa")

    estudiante = None
    if ci or nombre:
        estudiante = {
            "valor_extraido": nombre or ci,
            "fk_resolucion": {
                "ci": ci,
                "fk_estado": "A" if ci else "B",
                "nombre_resuelto": nombre or f"Estudiante CI {ci}",
            },
        }

    return {
        "estudiante": estudiante,
        "monto_deuda": _a_numero(celda("monto_deuda")),
        "monto_pagado": _a_numero(celda("monto_pagado")),
        "cuotas_impagas": int(cuotas) if cuotas is not None else None,
        "programa": {"valor_extraido": programa} if programa else None,
    }


def _resolver_fila_sin_encabezados(
    celdas: List[str], categoria: str, base: Dict[str, Any], entidades_fila: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Heurística posicional para texto sin encabezados. Las celdas 'POS…: valor' son metadato del programa."""
    res = dict(base)
    for c in celdas:
        hdr, sep, _ = c.partition(": ")
        if sep and es_encabezado_metadato_pos(hdr):
            continue
        # CI numérico típico boliviano (6 a 8 dígitos)
        if c.isdigit() and 5 <= len(c) <= 9:
            res["estudiante"] = {
                "valor_extraido": c,
                "fk_resolucion": {"ci": c, "fk_estado": "A", "nombre_resuelto": f"Estudiante CI {c}"}
            }
            entidades_fila.append({"tipo": "CI", "valor": c})
        elif any(car.isalpha() for car in c) and len(c) > 6 and not res["estudiante"]:
            res["estudiante"] = {
                "valor_extraido": c,
                "fk_resolucion": {"ci": None, "fk_estado": "B", "nombre_resuelto": c}
            }
            entidades_fila.append({"tipo": "ESTUDIANTE", "valor": c})

        try:
            val_num = float(c.replace(",", "."))
            if 0.0 <= val_num <= 100.0 and categoria == "academico" and res["nota_final"] is None:
                res["nota_final"] = val_num * 10.0 if 0.0 < val_num <= 10.0 else val_num  # escala 10 -> base 100
            elif val_num >= 0.0 and categoria == "financiero" and res["monto_deuda"] is None:
                res["monto_deuda"] = val_num
        except ValueError:
            pass
    return res



_ENCABEZADOS_NUMERACION = {"N°", "Nº", "NRO", "N", "ID", "#", "NUMERO", "NÚMERO", "NO", "NO."}


def _motivo_no_aplicable(celdas):
    """Línea sin hecho posible: solo numeración ('N°: 1498') o texto libre sin ningún 'ENCABEZADO: valor'. None si no aplica."""
    con_valor = [c for c in celdas if c.strip()]
    pares = [c.partition(": ") for c in con_valor]
    estructuradas = [(h.strip(), v.strip()) for h, sep, v in pares if sep and h.strip() and v.strip()]
    if not estructuradas:
        return "TEXTO_LIBRE_SIN_ENCABEZADO"
    if all(h.upper() in _ENCABEZADOS_NUMERACION for h, _ in estructuradas) and len(estructuradas) == len(con_valor):
        return "SOLO_NUMERACION"
    genericos = [h for h, v in estructuradas if re.match(r"^(col_\d+|unnamed.*|true|false|informaci[oó]n b[aá]sica.*)$", h.strip(), re.I)]
    if len(genericos) * 2 >= len(estructuradas):
        return "ENCABEZADO_GENERICO"  # fila de títulos de columna o de casillas sin nombre: no es un registro
    return None


def _resolver_linea(categoria, celdas, campos, campos_fin, factores_escala):
    """Resoluciones de una línea por las reglas (cascada por encabezado). Devuelve (resoluciones, entidades, por_reglas):
    por_reglas es True si las reglas dejaron resueltos los campos que necesita el hecho (no hace falta BETO)."""
    base = {
        "categoria": categoria,
        "nota_final": None,
        "asistencia_pct": None,
        "incumplimiento_actividades_pct": None,
        "monto_deuda": None,
        "cuotas_impagas": None,
        "estado_cartera": "Vigente",
        "nivel_confianza_ia": None,
        "estudiante": None,
        "docente": None,
        "modulo": None,
        "fecha": fecha_de_fila(campos, categoria) if campos else None,
    }
    entidades_fila = []
    resoluciones_lista = []
    por_reglas = False
    if campos_fin is not None:
        fila_fin = _resolver_fila_financiera(campos_fin)
        resoluciones_lista.append({**base, **fila_fin, "estado_cartera": None})  # el loader deriva la cartera
        if fila_fin["estudiante"]:
            entidades_fila.append({"tipo": "CI", "valor": fila_fin["estudiante"]["fk_resolucion"]["ci"]})
        por_reglas = bool(fila_fin["estudiante"])
    elif campos and categoria == "academico":
        for reg in registros_asignacion_docente(campos):
            reg.pop("requiere_revision")
            resoluciones_lista.append({**base, **reg, "_revision_fila": False})
        for reg in registros_academicos(campos, factores_escala):
            revision_fila = reg.pop("requiere_revision")
            resoluciones_lista.append({**base, **reg, "_revision_fila": revision_fila})
            if reg["estudiante"]:
                entidades_fila.append({"tipo": "ESTUDIANTE", "valor": reg["estudiante"]["valor_extraido"]})
        por_reglas = bool(entidades_fila)
    elif campos and categoria == "rentabilidad" and (
        registros_rentabilidad(campos) or registros_costo_programa(campos) or registros_techo_convenio(campos)
    ):
        for reg in (registros_rentabilidad(campos) or registros_costo_programa(campos)
                    or registros_techo_convenio(campos)):
            revision_fila = reg.pop("requiere_revision", False)
            resoluciones_lista.append({**base, **reg, "_revision_fila": revision_fila})
        por_reglas = True
    elif campos and categoria == "evaluacion_docente":
        for reg in registros_evaluacion(campos):
            revision_fila = reg.pop("requiere_revision")
            resoluciones_lista.append({
                **base, **reg, "estudiante": reg["estudiante"] or {},
                "anonima": reg["estudiante"] is None, "_revision_fila": revision_fila,
            })
            if reg["estudiante"]:
                entidades_fila.append({"tipo": "ESTUDIANTE", "valor": reg["estudiante"]["valor_extraido"]})
        por_reglas = bool(resoluciones_lista) and any(r.get("modulo") or r.get("programa") for r in resoluciones_lista)
    elif campos and categoria in ("marketing", "admision") and registros_techo_convenio(campos):
        for reg in registros_techo_convenio(campos):  # convenio en un documento clasificado como marketing
            revision_fila = reg.pop("requiere_revision", False)
            resoluciones_lista.append({**base, **reg, "_revision_fila": revision_fila})
        por_reglas = True
    elif campos and (categoria == "admision" or (categoria == "marketing" and "MARCA TEMPORAL" in campos)):
        # Inscripción (TBL_INSCRITOS): MARCA TEMPORAL es la fecha del inscrito y NUMEROPROYECTO el programa
        resoluciones_lista.append({
            **base, "estudiante": estudiante_de_fila(campos),
            "fecha": parsear_fecha((campos.get("MARCA TEMPORAL") or "")[:10]) or base["fecha"],
            "programa": {"valor_extraido": campos.get("NOMBRE DEL PROGRAMA"),
                         "metadata": {"pos_canonico": campos.get("NUMEROPROYECTO")}},
        })
        por_reglas = bool(resoluciones_lista[0]["estudiante"]) or bool(campos.get("NUMEROPROYECTO"))
    else:
        resoluciones_lista.append(_resolver_fila_sin_encabezados(celdas, categoria, base, entidades_fila))
    return resoluciones_lista, entidades_fila, por_reglas


@router.post(
    "/process",
    response_model=PipelineExecutionResponse,
    summary="Ejecutar pipeline completo (Ingesta -> NLP -> Calidad -> Carga DW)"
)
def process_pipeline(
    file: Optional[UploadFile] = File(None),
    doc_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["AUDITOR_CALIDAD", "ADMIN"]))
):
    """
    Procesa un archivo documental o un documento ya cargado en staging:
    1. Ingesta, limpieza y detección de bloques tabulares
    2. Extracción semántica y normalización de columnas
    3. Resolución dimensional de LLaves Foráneas (Estudiante, Docente, Módulo, Tiempo)
    4. Carga a tablas de hechos del Data Warehouse o derivación a stg_entidad_no_resuelta
    """
    inicio = time.time()

    if not file and not doc_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar un archivo (file) o un ID de documento existente (doc_id)."
        )

    nombre_archivo = "documento_existente"
    t_lectura_ms = 0.0
    t_beto_ms = t_carga_ms = 0.0

    # Paso 1: Si hay archivo, procesarlo a través de IngestionService
    if file:
        nombre_archivo = file.filename or "archivo_sin_nombre"
        ext = os.path.splitext(nombre_archivo)[1].lower()
        if ext not in (".xlsx", ".xls", ".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formato no soportado: '{ext}'. Formatos válidos: .xlsx, .xls, .csv"
            )

        t_lectura0 = time.perf_counter()
        contenido = file.file.read()
        res_ingesta = IngestionService.procesar_archivo(
            db=db,
            ruta_o_bytes=contenido,
            filename=nombre_archivo
        )
        doc_id = res_ingesta.get("id_documento") or res_ingesta.get("doc_id")
        t_lectura_ms = (time.perf_counter() - t_lectura0) * 1000.0
    else:
        # Verificar que el doc_id exista
        doc = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento == doc_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con ID {doc_id} no encontrado en el registro de Origen Documental y Lotes."
            )
        nombre_archivo = doc.nombre_archivo

    # Paso 2: Obtener bloques de staging para este documento
    bloques_stg = (
        db.query(StagingRegistroCrudo)
        .filter(StagingRegistroCrudo.id_documento == doc_id, StagingRegistroCrudo.es_ruido == False)
        .all()
    )

    dw_loader = DWLoaderService(db)
    dw_loader.diferir_eval = True  # evaluación docente: inserción en bloque al final del documento
    _doc_origen = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_documento == doc_id).first()
    hash_archivo = (_doc_origen.hash_sha256 if _doc_origen and _doc_origen.hash_sha256 else nombre_archivo)
    detalles_carga = []
    cargados_dw = 0
    staged_entidades = 0
    total_filas = 0
    total_entidades = 0
    confianzas = []
    cargados_revision = 0
    beto_lineas = 0
    reglas_lineas = 0
    lineas_no_aplicables = 0

    # Importes tolerantes para PLN / Calidad
    try:
        from pipeline.semantic.formatter import formatear_fila_dinamica, obtener_gazetteer
        from pipeline.normalization.quality_rules import QualityEvaluator
        from pipeline.normalization.fk_resolver import FKResolver
        pln_disponible = True
        gazetteer = obtener_gazetteer()
        evaluator = QualityEvaluator()
        fk_resolver = FKResolver()
    except Exception as e:
        logger.warning(f"Módulos semánticos de pipeline no disponibles directamente: {e}")
        pln_disponible = False

    for b in bloques_stg:
        texto_lineas = (b.texto_plano or "").split("\n")
        total_filas += len(texto_lineas)
        categoria = b.categoria or "academico"

        lineas = []
        for linea in texto_lineas:
            linea_str = linea.strip()
            if not linea_str:
                continue
            celdas = [c.strip() for c in linea_str.split("|")]
            campos_fin = _campos_financieros_por_encabezado(celdas) if categoria == "financiero" else None
            if campos_fin == {}:
                continue  # fila con encabezados pero sin montos: no es un hecho financiero
            lineas.append((linea_str, celdas, campos_fin))

        # Escala de notas por programa en el archivo (un acta mezcla programas sobre 20 y sobre 100)
        factores_escala = factores_escala_por_programa(
            [campos_por_encabezado(c) for _, c, _ in lineas]) if categoria == "academico" else None

        # Pasada 1 (reglas): cada línea se resuelve con la cascada de reglas antes de consultar BETO
        preparadas = []
        no_aplicables = {}
        for k_orig, (linea_str, celdas, campos_fin) in enumerate(lineas):
            campos = campos_por_encabezado(celdas)
            res_l, ents_l, por_reglas = _resolver_linea(categoria, celdas, campos, campos_fin, factores_escala)
            if not por_reglas:
                motivo_na = _motivo_no_aplicable(celdas)
                if motivo_na:  # ni BETO ni bandeja: no hay hecho ni entidad que resolver; queda un registro agregado en el log
                    no_aplicables[motivo_na] = no_aplicables.get(motivo_na, 0) + 1
                    continue
            preparadas.append((linea_str, celdas, campos_fin, campos, res_l, ents_l, por_reglas, k_orig))
        for motivo_na, n_na in no_aplicables.items():
            db.add(LogInconsistencia(id_documento=doc_id, campo_afectado=b.hoja or "", valor_recibido=str(n_na), tipo_regla="LINEAS_NO_APLICABLES",
                                     severidad="BAJA", estado_resolucion="REGISTRADO",
                                     descripcion=f"{n_na} líneas sin hecho posible ({motivo_na}) en la hoja '{b.hoja}'; no pasan por BETO ni por la bandeja"))
            lineas_no_aplicables += n_na

        # Pasada 2 (BETO): solo las líneas que las reglas no resolvieron; las demás reutilizan el índice de la caché si existe
        # (nunca se calcula uno nuevo para ellas). Banda: >= 0.85 hecho, [0.60, 0.85) hecho en revisión, < 0.60 staging
        t_b0 = time.perf_counter()
        indices = [None] * len(preparadas)
        necesitan = [k for k, pr in enumerate(preparadas) if not pr[6]]
        if necesitan:
            for k, v in zip(necesitan, obtener_indices([preparadas[k][0] for k in necesitan])):
                indices[k] = v
        resueltas = [k for k, pr in enumerate(preparadas) if pr[6]]
        if resueltas:
            for k, v in zip(resueltas, indices_en_cache([preparadas[k][0] for k in resueltas])):
                indices[k] = v
        t_beto_ms += (time.perf_counter() - t_b0) * 1000.0
        beto_lineas += len(necesitan)
        reglas_lineas += len(resueltas)

        for ((linea_str, celdas, campos_fin, campos, resoluciones_lista, entidades_fila, por_reglas, k_fila), indice) in zip(preparadas, indices):
            # Clave de idempotencia por fila de origen: hash de archivo + hoja + fila + contenido
            clave_origen = hashlib.sha256(
                f"{hash_archivo}|{b.hoja}|{(b.fila_inicio or 0) + k_fila}|{linea_str}".encode("utf-8")).hexdigest()
            if indice is not None:
                confianzas.append(indice)
            if por_reglas:
                # Las reglas resolvieron los campos que necesita el hecho: se carga; la baja confianza (caché) queda en el log
                banda = "CONSOLIDADO"
                if indice is not None and indice < 0.60:
                    db.add(LogInconsistencia(
                        id_documento=doc_id, fila_origen=(b.fila_inicio or 0) + k_fila, campo_afectado="indice_confianza_beto",
                        valor_recibido=str(indice), valor_esperado=">= 0.60", tipo_regla="BAJA_CONFIANZA_CARGADA", severidad="BAJA",
                        estado_resolucion="REGISTRADO", descripcion="Campos resueltos por reglas; el hecho se cargó pese al índice BETO bajo"))
            else:
                banda = banda_de(indice)
            if banda == BANDA_STAGING:
                db.add(StagingEntidadNoResuelta(
                    id_documento=doc_id,
                    tipo_entidad="ESTUDIANTE",
                    texto_original=linea_str[:2000],
                    fk_estado="C",
                    motivo="BAJA_CONFIANZA_IA",
                    nivel_confianza=indice,
                    resuelto=False,
                ))
                staged_entidades += 1
                continue
            en_revision = banda == BANDA_REVISION
            for r_l in resoluciones_lista:
                r_l["nivel_confianza_ia"] = indice

            total_entidades += len(entidades_fila)
            for resoluciones_fila in resoluciones_lista:
                revision_fila = resoluciones_fila.pop("_revision_fila", False)
                reg_simulado = {
                    "doc_id": doc_id,
                    "categoria": categoria,
                    "entidades_ner": entidades_fila,
                    "resoluciones": resoluciones_fila,
                    "calidad": {"requiere_revision": en_revision or revision_fila},
                    "clave_origen": clave_origen,
                }
                t_c0 = time.perf_counter()
                res_carga = dw_loader.cargar_registro(reg_simulado, id_usuario=current_user.id)
                t_carga_ms += (time.perf_counter() - t_c0) * 1000.0
                detalles_carga.append(res_carga)
                if res_carga.get("status") == "loaded":
                    cargados_dw += 1
                    if reg_simulado["calidad"]["requiere_revision"]:
                        cargados_revision += 1
                elif res_carga.get("status") == "staged":
                    staged_entidades += 1

    t_f0 = time.perf_counter()
    dw_loader.finalizar_cargas()
    t_carga_ms += (time.perf_counter() - t_f0) * 1000.0
    db.commit()
    cache_consultas.invalidar()  # el DW cambió: alertas, CMI y forecast se recalculan

    tiempo_total_ms = round((time.time() - inicio) * 1000.0, 2)
    prom_confianza = round(sum(confianzas) / max(1, len(confianzas)), 4)
    requiere_rev = staged_entidades > 0 or cargados_revision > 0

    return {
        "status": "success",
        "id_documento": doc_id,
        "nombre_archivo": nombre_archivo,
        "total_bloques_detectados": len(bloques_stg),
        "total_filas_procesadas": total_filas,
        "total_entidades_extraidas": total_entidades,
        "hechos_cargados_dw": cargados_dw,
        "hechos_en_revision": cargados_revision,
        "entidades_derivadas_staging": staged_entidades,
        "nivel_confianza_promedio": prom_confianza,
        "requiere_revision_humana": requiere_rev,
        "tiempo_total_ms": tiempo_total_ms,
        "tiempos_etapa_ms": {
            "lectura_e_ingesta": round(t_lectura_ms, 1), "beto": round(t_beto_ms, 1), "carga_dw": round(t_carga_ms, 1),
            "reglas_y_resto": round(tiempo_total_ms - t_lectura_ms - t_beto_ms - t_carga_ms, 1),
        },
        "lineas_beto": beto_lineas,
        "lineas_resueltas_por_reglas": reglas_lineas,
        "lineas_no_aplicables": lineas_no_aplicables,
        "detalles_carga": detalles_carga[:20]  # Primeros 20 para no sobrecargar el payload
    }
