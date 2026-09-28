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
from pipeline.pipeline_logger import registrar_log_ejecucion

# Importes tolerantes para persistencia en Postgres
try:
    try:
        from core.database import SessionLocal
        from models.fact_rendimiento import FactRendimientoAcademico
        from models.fact_financiero import FactSituacionFinanciera
        from models.log_auditoria_nlp import LogAuditoriaNlp
    except ImportError:
        from backend.core.database import SessionLocal
        from backend.models.fact_rendimiento import FactRendimientoAcademico
        from backend.models.fact_financiero import FactSituacionFinanciera
        from backend.models.log_auditoria_nlp import LogAuditoriaNlp
    DB_MODELS_DISPONIBLES = True
except Exception:
    DB_MODELS_DISPONIBLES = False


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

        # Extraer candidatos por tipo de entidad desde inferencia NER
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

        # Extraer valores tabulares de cabecera normalizada entregados por sheet_reader
        cols_fila: Dict[str, str] = {}
        for o in oraciones_info:
            meta_orig = o.get("metadatos_origen", {})
            if "row_dict" in meta_orig and isinstance(meta_orig["row_dict"], dict):
                cols_fila.update(meta_orig["row_dict"])

        def _buscar_en_cols(claves: List[str]) -> Optional[str]:
            for k, v in cols_fila.items():
                k_clean = str(k).strip().lower()
                for c in claves:
                    if c in k_clean:
                        v_str = str(v).strip()
                        if v_str and v_str.lower() not in ("nan", "none", "null", "-", ""):
                            return v_str
            return None

        # 1. Nota final con unificación de escala institucional (0-10 -> 0-100)
        nota_col = _buscar_en_cols(["nota final", "calificacion final", "nota", "calificacion", "puntaje"])
        nota_final = None
        if nota_col:
            try:
                num_n = float(nota_col.replace(",", "."))
                if 0.0 < num_n <= 10.0:
                    num_n = round(num_n * 10.0, 2)
                if 0.0 <= num_n <= 100.0:
                    nota_final = num_n
            except ValueError:
                pass

        # Fallback a regex sobre texto libre solo si no vino en cabecera
        if nota_final is None and resoluciones.get("nota"):
            try:
                val_n = float(str(resoluciones["nota"]["valor_extraido"]).replace(",", "."))
                if 0.0 < val_n <= 10.0:
                    val_n = round(val_n * 10.0, 2)
                if 0.0 <= val_n <= 100.0:
                    nota_final = val_n
            except (ValueError, TypeError):
                pass

        # 2. Asistencia % (0-100)
        asist_col = _buscar_en_cols(["asistencia", "% asistencia", "asistencia_pct"])
        asistencia_pct = None
        if asist_col:
            try:
                asistencia_pct = float(asist_col.replace(",", ".").replace("%", ""))
            except ValueError:
                pass

        # 3. Incumplimiento de actividades % (0-100)
        incump_col = _buscar_en_cols(["incumplimiento", "% incumplimiento", "incumplimiento_actividades_pct"])
        incumplimiento_pct = None
        if incump_col:
            try:
                incumplimiento_pct = float(incump_col.replace(",", ".").replace("%", ""))
            except ValueError:
                pass

        # 4. Monto de deuda (>= 0)
        deuda_col = _buscar_en_cols(["monto_deuda", "deuda", "saldo deudor", "saldo"])
        monto_deuda = None
        if deuda_col:
            try:
                monto_deuda = float(deuda_col.replace(",", ".").replace("Bs", "").replace("bs", "").strip())
            except ValueError:
                pass
        if monto_deuda is None and resoluciones.get("monto"):
            try:
                monto_deuda = float(str(resoluciones["monto"]["valor_extraido"]).replace(",", ".").replace("Bs", "").replace("bs", "").strip())
            except (ValueError, TypeError):
                pass

        # 5. Cuotas impagas (entero >= 0)
        cuotas_col = _buscar_en_cols(["cuotas_impagas", "cuotas impagas", "cuotas"])
        cuotas_impagas = None
        if cuotas_col:
            try:
                cuotas_impagas = int(cuotas_col.split(".")[0])
            except ValueError:
                pass

        # 6. Estado de cartera ('Vigente', 'Mora', 'Previsionable')
        cartera_col = _buscar_en_cols(["estado_cartera", "cartera"])
        estado_cartera = cartera_col.strip().title() if cartera_col else None

        # GIRA-42: Cálculo formal de nivel_confianza_ia
        if resultado_ner.entidades:
            confianzas = [e.score for e in resultado_ner.entidades]
            nivel_confianza_ia = round(sum(confianzas) / len(confianzas), 4)
        else:
            nivel_confianza_ia = 0.95

        # Estado de resolución FK (A: CI directo, B: difuso padrón, C: sintético temporal)
        fk_est = "A"
        if resoluciones.get("estudiante") and resoluciones["estudiante"].get("fk_resolucion"):
            fk_est = resoluciones["estudiante"]["fk_resolucion"].get("fk_estado", "A")

        # Consolidar campos reales en resoluciones
        resoluciones["nota_final"] = nota_final
        resoluciones["asistencia_pct"] = asistencia_pct
        resoluciones["incumplimiento_actividades_pct"] = incumplimiento_pct
        resoluciones["monto_deuda"] = monto_deuda
        resoluciones["cuotas_impagas"] = cuotas_impagas
        resoluciones["estado_cartera"] = estado_cartera
        resoluciones["nivel_confianza_ia"] = nivel_confianza_ia
        resoluciones["fk_estado"] = fk_est

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
            "nota": nota_final if nota_final is not None else (resoluciones["nota"]["valor_extraido"] if resoluciones["nota"] else None),
            "asistencia_pct": asistencia_pct,
            "incumplimiento_actividades_pct": incumplimiento_pct,
            "monto": monto_deuda if monto_deuda is not None else (resoluciones["monto"]["valor_extraido"] if resoluciones["monto"] else None),
            "monto_deuda": monto_deuda,
            "cuotas_impagas": cuotas_impagas,
            "estado_cartera": estado_cartera,
            "confianza_ia": nivel_confianza_ia,
            "score_matching": (
                resoluciones["programa"]["catalogo_match"]["score"]
                if resoluciones["programa"] and resoluciones["programa"].get("catalogo_match")
                else None
            ),
        }

        if categoria.upper() == "FINANCIERO" or resoluciones["monto_deuda"] is not None:
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

    # ──────────────────────────────────────────────────────────────────────────
    # POST-PASOS SÍNCRONOS INSTITUCIONALES (Sprint 3)
    # ──────────────────────────────────────────────────────────────────────────
    def persistir_telemetria(self, registros: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Post-paso 1: Persiste telemetría de rendimiento y registros de hechos en Postgres
        (fact_rendimiento_academico y fact_situacion_financiera), incluyendo nivel_confianza_ia,
        requiere_revision y fk_estado ('A', 'B', 'C').
        Garantiza fallback graceful persistiendo simultáneamente en JSONL local.
        """
        ruta_facts_jsonl = OUTPUT_DIR / "sprint3_fact_persistidos.jsonl"
        total_persistidos_archivo = 0
        total_persistidos_db = 0
        db_disponible = False

        db = None
        if DB_MODELS_DISPONIBLES:
            try:
                db = SessionLocal()
                # Test de conectividad rápido
                db.execute("SELECT 1")
                db_disponible = True
            except Exception:
                db_disponible = False
                if db:
                    db.close()
                    db = None

        with open(ruta_facts_jsonl, "w", encoding="utf-8") as f_facts:
            for reg in registros:
                res = reg.get("resoluciones", {})
                cal = reg.get("calidad", {})
                cat = str(reg.get("categoria", "")).lower()

                fact_data = {
                    "doc_id": reg.get("doc_id"),
                    "archivo": reg.get("archivo"),
                    "categoria": cat,
                    "estudiante_ci": res.get("estudiante", {}).get("fk_resolucion", {}).get("ci") if res.get("estudiante") else None,
                    "fk_estado": res.get("fk_estado", "A"),
                    "nivel_confianza_ia": res.get("nivel_confianza_ia", 0.95),
                    "requiere_revision": cal.get("requiere_revision", False),
                    "nota_final": res.get("nota_final"),
                    "asistencia_pct": res.get("asistencia_pct"),
                    "incumplimiento_actividades_pct": res.get("incumplimiento_actividades_pct"),
                    "monto_deuda": res.get("monto_deuda"),
                    "cuotas_impagas": res.get("cuotas_impagas"),
                    "estado_cartera": res.get("estado_cartera")
                }
                f_facts.write(json.dumps(fact_data, ensure_ascii=False) + "\n")
                total_persistidos_archivo += 1

                # Si Postgres está conectado, persistir en la tabla correspondiente
                if db_disponible and db:
                    try:
                        if cat == "financiero":
                            fact_obj = FactSituacionFinanciera(
                                monto_deuda=fact_data["monto_deuda"],
                                cuotas_impagas=fact_data["cuotas_impagas"],
                                estado_cartera=fact_data["estado_cartera"],
                                nivel_confianza_ia=fact_data["nivel_confianza_ia"],
                                requiere_revision=fact_data["requiere_revision"],
                                fk_estado=fact_data["fk_estado"]
                            )
                        else:
                            fact_obj = FactRendimientoAcademico(
                                nota_final=fact_data["nota_final"],
                                asistencia_pct=fact_data["asistencia_pct"],
                                incumplimiento_actividades_pct=fact_data["incumplimiento_actividades_pct"] or 0.00,
                                nivel_confianza_ia=fact_data["nivel_confianza_ia"],
                                requiere_revision=fact_data["requiere_revision"],
                                fk_estado=fact_data["fk_estado"]
                            )
                        db.add(fact_obj)
                        db.commit()
                        total_persistidos_db += 1
                    except Exception:
                        if db:
                            db.rollback()

        if db:
            db.close()

        modo = "postgres_y_jsonl" if db_disponible else "jsonl_local"
        print(f"[Post-Paso 1] Telemetría y Hechos persistidos: {total_persistidos_archivo} registros ({modo}).")

        return {
            "persistidos_archivo": total_persistidos_archivo,
            "persistidos_db": total_persistidos_db,
            "modo": modo,
            "ruta_archivo": str(ruta_facts_jsonl)
        }

    def volcar_inconsistencias(self, registros: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Post-paso 2: Consolida el volcado de inconsistencias detectadas en
        output/inconsistencias_sprint3.jsonl y en log_auditoria_nlp (Postgres)
        si la base de datos está disponible.
        """
        flagged = [r for r in registros if r.get("calidad", {}).get("requiere_revision")]
        db = None
        db_disponible = False
        inconsistencias_guardadas_db = 0

        if DB_MODELS_DISPONIBLES:
            try:
                db = SessionLocal()
                db.execute("SELECT 1")
                db_disponible = True
            except Exception:
                db_disponible = False
                if db:
                    db.close()
                    db = None

        if db_disponible and db:
            for r in flagged:
                try:
                    cal = r.get("calidad", {})
                    res = r.get("resoluciones", {})
                    log_entry = LogAuditoriaNlp(
                        texto_original=str(r.get("archivo", ""))[:450],
                        prediccion_beto=", ".join(cal.get("motivos", []))[:180],
                        confianza_ia=res.get("nivel_confianza_ia", 0.50),
                        correccion_humana="PENDIENTE_REVISION"
                    )
                    db.add(log_entry)
                    db.commit()
                    inconsistencias_guardadas_db += 1
                except Exception:
                    if db:
                        db.rollback()
            db.close()

        total_inconsistencias = len(flagged)
        modo = "postgres_y_jsonl" if db_disponible else "jsonl_local"
        print(f"[Post-Paso 2] Inconsistencias volcadas: {total_inconsistencias} eventos ({modo}).")

        return {
            "total_inconsistencias": total_inconsistencias,
            "inconsistencias_db": inconsistencias_guardadas_db,
            "modo": modo,
            "ruta_log": str(self.audit_logger.ruta_log)
        }

    def ejecutar(self, ruta_entrada: Path, ruta_salida: Path, limite_docs: Optional[int] = None) -> Dict[str, Any]:
        """
        Ejecuta el procesamiento en batch sobre el archivo de documentos de Sprint 2,
        seguido de la ejecución directa de los dos post-pasos institucionales.
        """
        if not ruta_entrada.exists():
            raise FileNotFoundError(f"Archivo de entrada no encontrado: {ruta_entrada}")

        print(f"Iniciando ejecución Sprint 3 desde: {ruta_entrada}")
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        docs_procesados = 0
        total_flagged = 0
        t_inicio_total = time.perf_counter()
        todos_registros: List[Dict[str, Any]] = []

        with open(ruta_entrada, "r", encoding="utf-8") as f_in, \
             open(ruta_salida, "w", encoding="utf-8") as f_out:

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
                req_rev = res_doc["calidad"]["requiere_revision"]
                if req_rev:
                    total_flagged += 1

                registrar_log_ejecucion(
                    archivo=res_doc.get("archivo", "desconocido"),
                    hoja=res_doc.get("hoja"),
                    bloque_id=res_doc.get("bloque_id"),
                    total_entidades=res_doc.get("total_entidades_ner", 0),
                    nivel_confianza=res_doc.get("resoluciones", {}).get("nivel_confianza_ia", 0.85),
                    requiere_revision=req_rev,
                    tiempo_ms=res_doc.get("tiempo_inferencia_ms", 0.0)
                )

                f_out.write(json.dumps(res_doc, ensure_ascii=False) + "\n")
                todos_registros.append(res_doc)
                docs_procesados += 1

                if docs_procesados % 25 == 0:
                    print(f"  Procesados: {docs_procesados} documentos (Flagged: {total_flagged})...")

        duracion_seg = time.perf_counter() - t_inicio_total

        # Ejecución directa y síncrona de los dos post-pasos
        resultado_telemetria = self.persistir_telemetria(todos_registros)
        resultado_inconsistencias = self.volcar_inconsistencias(todos_registros)

        metricas_auditoria = self.audit_logger.obtener_resumen_metricas()
        metricas_telemetria = self.perf_logger.obtener_resumen()

        resumen = {
            "documentos_procesados": docs_procesados,
            "documentos_flagged_revision": total_flagged,
            "tasa_revision_pct": round((total_flagged / max(docs_procesados, 1)) * 100.0, 2),
            "duracion_total_seg": round(duracion_seg, 2),
            "ruta_salida": str(ruta_salida),
            "metricas_auditoria": metricas_auditoria,
            "metricas_telemetria": metricas_telemetria,
            "post_paso_telemetria": resultado_telemetria,
            "post_paso_inconsistencias": resultado_inconsistencias
        }

        print("")
        print("==========================================================")
        print("  RESUMEN DE EJECUCION SPRINT 3 (PLN & CALIDAD)")
        print("==========================================================")
        print(f"* Documentos procesados: {docs_procesados}")
        print(f"* Registros que requieren revision: {total_flagged} ({resumen['tasa_revision_pct']}%)")
        print(f"* Inconsistencias auditadas: {metricas_auditoria.get('total_inconsistencias', 0)}")
        print(f"* Latencia promedio NER: {metricas_telemetria.get('latencia_promedio_ms', 0)} ms")
        print(f"* Persistencia telemetría hechos: {resultado_telemetria['persistidos_archivo']} regs ({resultado_telemetria['modo']})")
        print(f"* Volcado inconsistencias: {resultado_inconsistencias['total_inconsistencias']} eventos")
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
