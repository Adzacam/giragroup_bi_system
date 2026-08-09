"""
pipeline_orchestrator.py — Orquestación del Pipeline
Componente unificador que secuencia la ejecución de las fases previas
de forma lineal y retorna el contrato de salida simplificado.
"""

import logging
from typing import Optional

import pandas as pd

from pipeline.normalization.text_cleaner import preparar_payload_beto, normalizar_nombre
from pipeline.normalization.ner_engine import BetoNerEngine
from pipeline.normalization.normalizer import (
    resolver_dimension_estudiante,
    resolver_dimension_docente,
    asociar_entidad_fuzzy,
)
from pipeline.normalization.validator import validar_rango_temporal, detectar_nulos_criticos
from pipeline.normalization.error_logger import ErrorLogger
from pipeline.analytics.confidence_engine import ConfidenceEngine

logger = logging.getLogger(__name__)


def ejecutar_pipeline_completo(
    resultado_ingesta: dict,
    catalogo_estudiantes_df: Optional[pd.DataFrame] = None,
    catalogo_docentes_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Orquesta la ejecución secuencial de todas las fases del Sprint 3.

    Args:
        resultado_ingesta: dict del dispatcher con claves:
            - nombre_archivo: str
            - fuente_tipo: str ("SHEET" | "MOODLE" | "FORMS")
            - data: pd.DataFrame (datos crudos)
            - gestion: int (año de gestión, opcional)
        catalogo_estudiantes_df: DataFrame del catálogo de estudiantes existente.
        catalogo_docentes_df: DataFrame del catálogo de docentes existente.

    Returns:
        Contrato de salida consolidado:
        {
            "nombre_archivo": str,
            "fuente_tipo": str,
            "registros_procesados": int,
            "indice_confianza_global": float,
            "estado_dashboard": str,
            "payload_listo_para_orm": list[dict],
        }
    """
    nombre_archivo = resultado_ingesta.get("nombre_archivo", "desconocido")
    fuente_tipo = resultado_ingesta.get("fuente_tipo", "SHEET")
    df = resultado_ingesta.get("data", pd.DataFrame())
    gestion = resultado_ingesta.get("gestion")

    error_logger = ErrorLogger(nombre_archivo)

    if catalogo_estudiantes_df is None:
        catalogo_estudiantes_df = pd.DataFrame(
            columns=["id_estudiante", "codigo_estudiante", "nombre_completo"]
        )
    if catalogo_docentes_df is None:
        catalogo_docentes_df = pd.DataFrame(
            columns=["id_docente", "nombre_completo"]
        )

    logger.info("=== Pipeline iniciado para: %s (%s) ===", nombre_archivo, fuente_tipo)

    # -------------------------------------------------------
    # PASO 1: Preparar payload de texto para BETO (Sprint 2)
    # -------------------------------------------------------
    payload_beto = preparar_payload_beto(df, fuente_tipo, nombre_archivo)
    textos_limpios = [p["texto_limpio"] for p in payload_beto]

    # -------------------------------------------------------
    # PASO 2: Extraer entidades NER con BETO (Fase 1)
    # -------------------------------------------------------
    ner_engine = BetoNerEngine()
    resultados_ner = []
    if textos_limpios:
        resultados_ner = ner_engine.extraer_entidades_lote(textos_limpios)

    # Construir mapa de confianza NER por fila
    mapa_confianza_ner = {}
    for payload_item, ner_result in zip(payload_beto, resultados_ner):
        fila_id = payload_item.get("id_fila")
        mapa_confianza_ner[fila_id] = ner_result.get("confianza_ner", 0.0)

    # -------------------------------------------------------
    # PASO 3: Resolución de dimensiones fuzzy (Fase 2)
    # -------------------------------------------------------
    payload_orm = []

    for idx, fila in df.iterrows():
        registro = fila.to_dict()

        # Validación temporal (Fase 3)
        gestion_fila = registro.get("gestion", gestion)
        if gestion_fila is not None and not validar_rango_temporal(gestion_fila):
            error_logger.registrar_error(idx, f"Gestión fuera de rango: {gestion_fila}")

        # Detección de nulos críticos (Fase 3)
        nulos = detectar_nulos_criticos(registro)
        for campo_nulo in nulos:
            error_logger.registrar_error(idx, f"Llave natural nula: {campo_nulo}")

        # Resolución de estudiante
        ci_crudo = registro.get("ci") or registro.get("codigo_estudiante") or registro.get("codigo")
        nombre_est_crudo = registro.get("nombre_completo") or registro.get("nombre_estudiante") or registro.get("nombre")
        resolucion_est = resolver_dimension_estudiante(
            ci_crudo, nombre_est_crudo, catalogo_estudiantes_df
        )

        # Resolución de docente
        nombre_doc_crudo = registro.get("nombre_docente") or registro.get("docente")
        resolucion_doc = resolver_dimension_docente(
            nombre_doc_crudo, catalogo_docentes_df
        )

        # -------------------------------------------------------
        # PASO 4: Motor de confianza (Fase 4)
        # -------------------------------------------------------
        confianza_ner = mapa_confianza_ner.get(idx, 0.0)
        score_fuzzy = resolucion_est.get("distancia_fuzzy_minima", 0.0)

        resultado_confianza = ConfidenceEngine.calcular_confianza_registro(
            confianza_ner=confianza_ner,
            score_fuzzy_matching=score_fuzzy,
        )

        # Construir registro para ORM
        registro_orm = {
            "id_estudiante": resolucion_est.get("id_resuelto"),
            "id_docente": resolucion_doc.get("id_resuelto"),
            "id_modulo": registro.get("id_modulo"),
            "id_tiempo": registro.get("id_tiempo"),
            "nota_final": registro.get("nota_final"),
            "asistencia_pct": registro.get("asistencia_pct"),
            "incumplimiento_actividades_pct": registro.get("incumplimiento_actividades_pct", 0),
            "estado_academico": registro.get("estado_academico"),
            "nivel_confianza_ia": resultado_confianza["nivel_confianza_ia"],
            "requiere_revision": resultado_confianza["requiere_revision"],
        }

        payload_orm.append(registro_orm)

    # -------------------------------------------------------
    # PASO 5: Dashboard global (Fase 4)
    # -------------------------------------------------------
    confianzas = [r["nivel_confianza_ia"] for r in payload_orm]
    estado_dashboard = ConfidenceEngine.calcular_estado_dashboard(confianzas)

    # -------------------------------------------------------
    # Contrato de salida (Fase 6)
    # -------------------------------------------------------
    contrato = {
        "nombre_archivo": nombre_archivo,
        "fuente_tipo": fuente_tipo,
        "registros_procesados": len(payload_orm),
        "indice_confianza_global": estado_dashboard["indice_confianza_global"],
        "estado_dashboard": estado_dashboard["estado_dashboard"],
        "payload_listo_para_orm": payload_orm,
    }

    logger.info(
        "=== Pipeline completado: %s | Registros: %d | Confianza: %.4f | Estado: %s ===",
        nombre_archivo,
        contrato["registros_procesados"],
        contrato["indice_confianza_global"],
        contrato["estado_dashboard"],
    )

    if error_logger.total_errores > 0:
        logger.warning(
            "Errores detectados: %d — ver reporte con error_logger.exportar_reporte()",
            error_logger.total_errores,
        )

    return contrato
