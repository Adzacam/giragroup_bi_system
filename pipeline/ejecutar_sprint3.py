"""
pipeline/ejecutar_sprint3.py
----------------------------
Orquestador del Sprint 3: Procesamiento de Lenguaje Natural (PLN),
Normalización Semántica contra Catálogos y Control de Calidad/Auditoría.

Conecta de extremo a extremo las 10 historias del Sprint 3 (Épica GIRA-22):
- GIRA-40: Formateo semántico estructurado
- GIRA-9 & GIRA-10: Inferencia NER con BETO y agregación de subpalabras
- GIRA-11: Normalización léxica y difusa con RapidFuzz
- GIRA-12: Registro de telemetría de rendimiento (ms/tokens)
- GIRA-27: Evaluador de reglas de calidad y flag requiere_revision
- GIRA-41: Matching semántico contra catálogos 3NF (CatalogRepository)
- GIRA-42: Niveles de confianza probabilística (ALTA, MEDIA, BAJA)
- GIRA-43: Registro y trazabilidad de inconsistencias (AuditLogger)
- GIRA-50: Resolución inteligente de llaves foráneas (FKResolver A/B/C)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Asegurar raíz del proyecto en sys.path para imports absolutos
PROYECTO_RAIZ = Path(__file__).resolve().parent.parent
if str(PROYECTO_RAIZ) not in sys.path:
    sys.path.insert(0, str(PROYECTO_RAIZ))

from pipeline.config import (
    SPRINT2_DOCS_PATH,
    OUTPUT_DIR,
    INCONSISTENCIAS_LOG_PATH,
    DEFAULT_BATCH_SIZE,
    MODELO_BETO_NOMBRE,
    UMBRAL_CONFIANZA_ALTO
)
from pipeline.semantic.formatter import (
    formatear_documento,
    obtener_gazetteer,
    CatalogoGazetteer
)
from pipeline.semantic.ner_engine import NEREngine
from pipeline.semantic.performance_logger import PerformanceLogger
from pipeline.semantic.ner_schema import ResultadoInferenciaNER, TipoEntidad
from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio
from pipeline.normalization.fuzzy_normalizer import FuzzyNormalizer
from pipeline.normalization.fk_resolver import FKResolver
from pipeline.normalization.quality_rules import QualityEvaluator
from pipeline.analytics.audit_logger import AuditLogger, SeveridadInconsistencia


def parse_args():
    parser = argparse.ArgumentParser(description="Orquestador Sprint 3 - Pipeline NLP, Normalización y Calidad")
    parser.add_argument(
        "--input",
        type=Path,
        default=SPRINT2_DOCS_PATH,
        help=f"Ruta del archivo JSONL de entrada (default: {SPRINT2_DOCS_PATH})"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "sprint3_entidades_procesadas.jsonl",
        help="Ruta del archivo JSONL de salida con entidades y resoluciones"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Tamaño del lote para inferencia NER (default: {DEFAULT_BATCH_SIZE})"
    )
    parser.add_argument(
        "--limite-docs",
        type=int,
        default=None,
        help="Límite máximo de documentos a procesar (para pruebas/muestreo)"
    )
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="Forzar ejecución en CPU"
    )
    return parser.parse_args()


class OrquestadorSprint3:
    """
    Ejecuta el pipeline completo de NLP, normalización y aseguramiento de calidad.
    """

    def __init__(self, ruta_inconsistencias: Optional[Path] = None, cpu_only: bool = False):
        print("Inicializando componentes del Sprint 3...")
        self.device = "cpu" if cpu_only else None
        self.gazetteer = obtener_gazetteer()
        self.ner_engine = NEREngine(device=self.device)
        self.perf_logger = self.ner_engine.telemetria
        self.catalog_repo = obtener_catalogo_repositorio()
        self.fk_resolver = FKResolver()
        self.quality_evaluator = QualityEvaluator()
        self.audit_logger = AuditLogger(ruta_log=ruta_inconsistencias)

        print(f"Catálogos cargados: {len(self.catalog_repo.programas)} programas, "
              f"{len(self.catalog_repo.docentes)} docentes, {len(self.catalog_repo.modulos)} módulos.")

    def procesar_documento(self, doc: Dict[str, Any], doc_id: int) -> Dict[str, Any]:
        """
        Procesa un único documento estructurado aplicando PLN, resolución de llaves y auditoría.
        """
        archivo = doc.get("archivo", "desconocido.xlsx")
        hoja = doc.get("hoja", "desconocida")
        bloque_id = doc.get("bloque_id", 0)
        categoria = doc.get("categoria", "GENERAL")
        texto_crudo = doc.get("texto_plano") or doc.get("texto") or ""

        # GIRA-40: Si el documento puede estructurarse en oraciones semánticas, enriquecerlo
        oraciones_info = formatear_documento(doc, gazetteer=self.gazetteer, max_filas=5)
        textos_oraciones = [o["oracion"] for o in oraciones_info if o.get("oracion")]
        if not textos_oraciones:
            textos_oraciones = [texto_crudo[:400]] if texto_crudo else []

        # GIRA-10 & GIRA-12: Inferencia NER por oraciones estructuradas con telemetría integrada
        t_inicio = time.perf_counter()
        if textos_oraciones:
            resultados_lote = self.ner_engine.extraer_lote(textos_oraciones, batch_size=len(textos_oraciones))
        else:
            resultados_lote = []
        t_latencia = (time.perf_counter() - t_inicio) * 1000.0

        # Consolidar entidades extraídas
        todas_entidades = []
        for r in resultados_lote:
            todas_entidades.extend(r.entidades)

        resultado_ner = ResultadoInferenciaNER(
            texto=" ".join(textos_oraciones),
            entidades=todas_entidades,
            tiempo_inferencia_ms=t_latencia,
            modelo=self.ner_engine.model_name,
            dispositivo=self.ner_engine.dispositivo_nombre
        )

        # GIRA-41, GIRA-50 & GIRA-11: Extracción y Enlace Semántico
        resoluciones = {
            "estudiante": None,
            "docente": None,
            "programa": None,
            "modulo": None,
            "nota": None,
            "monto": None
        }

        # Extraer candidatos por tipo de entidad
        for ent in resultado_ner.entidades:
            tipo = ent.tipo.upper()
            val = ent.valor

            if tipo == TipoEntidad.ESTUDIANTE.value and not resoluciones["estudiante"]:
                # GIRA-50: Resolución de Llave Foránea (A/B/C)
                res_fk = self.fk_resolver.resolver_estudiante(nombre=val)
                resoluciones["estudiante"] = {
                    "valor_extraido": val,
                    "score_ner": ent.score,
                    "nivel_confianza": ent.nivel_confianza.value,
                    "fk_resolucion": res_fk
                }
            elif tipo == TipoEntidad.DOCENTE.value and not resoluciones["docente"]:
                # GIRA-41 & GIRA-11: Matching Semántico Docente
                res_doc = self.catalog_repo.enlazar_docente(val)
                resoluciones["docente"] = {
                    "valor_extraido": val,
                    "score_ner": ent.score,
                    "nivel_confianza": ent.nivel_confianza.value,
                    "catalogo_match": res_doc
                }
            elif tipo in (TipoEntidad.PROGRAMA.value, TipoEntidad.POS.value) and not resoluciones["programa"]:
                # GIRA-41: Matching Programa / POS
                res_prg = self.catalog_repo.enlazar_programa(val)
                resoluciones["programa"] = {
                    "valor_extraido": val,
                    "score_ner": ent.score,
                    "nivel_confianza": ent.nivel_confianza.value,
                    "catalogo_match": res_prg
                }
            elif tipo == TipoEntidad.MODULO.value and not resoluciones["modulo"]:
                # GIRA-41: Matching Módulo
                res_mod = self.catalog_repo.enlazar_modulo(val)
                resoluciones["modulo"] = {
                    "valor_extraido": val,
                    "score_ner": ent.score,
                    "nivel_confianza": ent.nivel_confianza.value,
                    "catalogo_match": res_mod
                }
            elif tipo == TipoEntidad.NOTA.value and not resoluciones["nota"]:
                resoluciones["nota"] = {"valor_extraido": val, "score_ner": ent.score}
            elif tipo == TipoEntidad.MONTO.value and not resoluciones["monto"]:
                resoluciones["monto"] = {"valor_extraido": val, "score_ner": ent.score}

        # GIRA-27: Evaluación de Reglas de Calidad e Integridad
        registro_para_calidad = {
            "archivo": archivo,
            "hoja": hoja,
            "bloque_id": bloque_id,
            "estudiante": resoluciones["estudiante"]["valor_extraido"] if resoluciones["estudiante"] else None,
            "ci": (
                resoluciones["estudiante"]["fk_resolucion"]["ci"]
                if resoluciones["estudiante"] and resoluciones["estudiante"].get("fk_resolucion")
                else None
            ),
            "fk_estudiante_resolucion": (
                resoluciones["estudiante"]["fk_resolucion"]
                if resoluciones["estudiante"]
                else None
            ),
            "nota": resoluciones["nota"]["valor_extraido"] if resoluciones["nota"] else None,
            "monto": resoluciones["monto"]["valor_extraido"] if resoluciones["monto"] else None,
            "score_matching": (
                resoluciones["programa"]["catalogo_match"]["score"]
                if resoluciones["programa"] and resoluciones["programa"].get("catalogo_match")
                else None
            ),
        }

        if categoria == "FINANCIERO" or resoluciones["monto"]:
            resultado_calidad = self.quality_evaluator.evaluar_registro_financiero(
                registro_para_calidad,
                inferencia_ner=resultado_ner
            )
        else:
            resultado_calidad = self.quality_evaluator.evaluar_registro_academico(
                registro_para_calidad,
                inferencia_ner=resultado_ner
            )

        # GIRA-43: Si requiere revisión, registrar en auditoría
        if resultado_calidad.requiere_revision:
            self.audit_logger.registrar_desde_evaluacion_calidad(
                resultado_calidad=resultado_calidad,
                archivo=archivo,
                hoja=hoja,
                bloque_id=bloque_id,
                fila=doc_id,
                accion_tomada="MARCADO_PARA_REVISION_HUMANA"
            )

        return {
            "doc_id": doc_id,
            "archivo": archivo,
            "hoja": hoja,
            "bloque_id": bloque_id,
            "categoria": categoria,
            "tiempo_inferencia_ms": round(t_latencia, 2),
            "total_entidades_ner": len(resultado_ner.entidades),
            "entidades_ner": [e.to_dict() for e in resultado_ner.entidades],
            "resoluciones": resoluciones,
            "calidad": resultado_calidad.to_dict(),
        }

    def ejecutar(self, ruta_entrada: Path, ruta_salida: Path, limite_docs: Optional[int] = None) -> Dict[str, Any]:
        """
        Ejecuta el procesamiento en batch sobre el archivo de documentos de Sprint 2.
        """
        if not ruta_entrada.exists():
            raise FileNotFoundError(f"Archivo de entrada no encontrado: {ruta_entrada}")

        print(f"Iniciando ejecución Sprint 3 desde: {ruta_entrada}")
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        docs_procesados = 0
        total_flagged = 0
        t_inicio_total = time.perf_counter()

        with open(ruta_entrada, "r", encoding="utf-8") as f_in,              open(ruta_salida, "w", encoding="utf-8") as f_out:

            for idx, linea in enumerate(f_in):
                if limite_docs is not None and idx >= limite_docs:
                    break

                txt = linea.strip()
                if not txt:
                    continue

                try:
                    doc = json.loads(txt)
                except json.JSONDecodeError:
                    continue

                res_doc = self.procesar_documento(doc, doc_id=idx + 1)
                if res_doc["calidad"]["requiere_revision"]:
                    total_flagged += 1

                f_out.write(json.dumps(res_doc, ensure_ascii=False) + "\n")
                docs_procesados += 1

                if docs_procesados % 25 == 0:
                    print(f"  Procesados: {docs_procesados} documentos (Flagged: {total_flagged})...")

        duracion_seg = time.perf_counter() - t_inicio_total
        metricas_auditoria = self.audit_logger.obtener_resumen_metricas()
        metricas_telemetria = self.perf_logger.obtener_resumen()

        resumen = {
            "documentos_procesados": docs_procesados,
            "documentos_flagged_revision": total_flagged,
            "tasa_revision_pct": round((total_flagged / max(docs_procesados, 1)) * 100.0, 2),
            "duracion_total_seg": round(duracion_seg, 2),
            "ruta_salida": str(ruta_salida),
            "metricas_auditoria": metricas_auditoria,
            "metricas_telemetria": metricas_telemetria
        }

        print("")
        print("==========================================================")
        print("  RESUMEN DE EJECUCION SPRINT 3 (PLN & CALIDAD)")
        print("==========================================================")
        print(f"* Documentos procesados: {docs_procesados}")
        print(f"* Registros que requieren revision: {total_flagged} ({resumen['tasa_revision_pct']}%)")
        print(f"* Inconsistencias auditadas: {metricas_auditoria.get('total_inconsistencias', 0)}")
        print(f"* Latencia promedio NER: {metricas_telemetria.get('latencia_promedio_ms', 0)} ms")
        print(f"* Tiempo total: {resumen['duracion_total_seg']} s")
        print(f"* Archivo generado: {ruta_salida}")
        print("==========================================================")
        print("")

        return resumen


def main():
    args = parse_args()
    orquestador = OrquestadorSprint3(cpu_only=args.cpu_only)
    orquestador.ejecutar(
        ruta_entrada=args.input,
        ruta_salida=args.output,
        limite_docs=args.limite_docs
    )


if __name__ == "__main__":
    main()
