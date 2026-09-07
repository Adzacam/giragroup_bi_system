"""
pipeline/semantic/ner_engine.py
--------------------------------
Motor de inferencia NER (Named Entity Recognition) basado en BETO para GiraGroup BI.
Carga localmente el modelo especializado en español y ejecuta la extracción
y desambiguación de entidades académicas y financieras con agregación de subtérminos
(wordpiece aggregation) y telemetría de inferencia.
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional, Union

import torch
from transformers import pipeline

from pipeline.config import (
    MODELO_BETO_NOMBRE,
    MODELO_BETO_BASE,
    DEFAULT_BATCH_SIZE,
    UMBRAL_CONFIANZA_ALTO,
    UMBRAL_CONFIANZA_MEDIO,
    PATRON_POS_STRICT,
    TITULOS_PERSONA_TUPLA
)
from pipeline.semantic.ner_schema import (
    TipoEntidad,
    EntidadExtraida,
    ResultadoInferenciaNER
)
from pipeline.semantic.formatter import CatalogoGazetteer
from pipeline.semantic.performance_logger import PerformanceLogger

logger = logging.getLogger("ner_engine")

# Patrones regex semánticos de dominio para entidades de valor y formato
PATRON_POS = PATRON_POS_STRICT
PATRON_NOTA = re.compile(
    r'\b(?:con\s+la\s+nota|nota|calificaci[oó]n|puntaje)\s*(?:de|:)?\s*([0-9]{1,3}(?:[.,][0-9]{1,2})?)\b',
    re.IGNORECASE
)
PATRON_MONTO = re.compile(
    r'(?:\b(?:cobranza|monto|pago|total)(?:\s+de)?\s+)?\b([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?)\s*(?:bs\.?|bob|bolivianos)\b',
    re.IGNORECASE
)

PATRON_CI = re.compile(
    r'\b(?:c\.?i\.?|carnet|c[eé]dula)\s*(?:n[o°]?)?\s*([0-9]{5,9}(?:-[0-9A-Za-z]+)?)\b',
    re.IGNORECASE
)
PATRON_MODULO = re.compile(
    r'\bm[oó]dulo\s+([A-Za-zÁÉÍÓÚáéíóúñÑüÜ0-9\-_]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúñÑüÜ0-9\-_]+){0,6}?)(?=\s+(?:con\s+la\s+nota|evalu[oó]|en\s+fecha|\.|\,|$))',
    re.IGNORECASE
)
PATRON_FACTURA = re.compile(
    r'\b(?:factura|recibo|nro\s+factura)\s*(?:n[o°]?)?\s*([A-Za-z0-9\-_]+)\b',
    re.IGNORECASE
)
PATRON_FECHA = re.compile(
    r'\b(?:fecha\s+)?(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b',
    re.IGNORECASE
)



class BetoNEREngine:
    """
    Motor principal de extracción NER para textos tabulados y oraciones semánticas.
    Combina modelo de lenguaje BETO (transformers) con reglas léxico-sintácticas
    y el gazetteer de catálogo de GiraGroup.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        gazetteer: Optional[CatalogoGazetteer] = None,
        device: Optional[Union[str, int]] = None,
        auto_load: bool = True
    ):
        self.model_name = model_name or MODELO_BETO_NOMBRE
        self.gazetteer = gazetteer or CatalogoGazetteer()
        self.telemetria = PerformanceLogger()
        
        if device is None:
            self.device_id = 0 if torch.cuda.is_available() else -1
            self.dispositivo_nombre = f"cuda:{self.device_id}" if self.device_id >= 0 else "cpu"
        elif isinstance(device, str):
            if "cuda" in device.lower() and torch.cuda.is_available():
                self.device_id = 0
                self.dispositivo_nombre = "cuda:0"
            else:
                self.device_id = -1
                self.dispositivo_nombre = "cpu"
        else:
            self.device_id = int(device)
            self.dispositivo_nombre = f"cuda:{self.device_id}" if self.device_id >= 0 else "cpu"

        self._nlp_pipeline = None
        if auto_load:
            self._inicializar_modelo()


    def _inicializar_modelo(self):
        """Carga perezosa del pipeline de transformers en memoria."""
        if self._nlp_pipeline is not None:
            return

        t0 = time.time()
        logger.info(f"Cargando modelo NER '{self.model_name}' en dispositivo '{self.dispositivo_nombre}'...")
        try:
            self._nlp_pipeline = pipeline(
                "ner",
                model=self.model_name,
                aggregation_strategy="simple",
                device=self.device_id
            )
            duracion = time.time() - t0
            logger.info(f"Modelo cargado exitosamente en {duracion:.2f}s.")
        except Exception as e:
            logger.warning(
                f"No se pudo cargar '{self.model_name}' ({e}). Intentando cargar modelo base o fallback..."
            )
            try:
                self._nlp_pipeline = pipeline(
                    "ner",
                    model=MODELO_BETO_BASE,
                    aggregation_strategy="simple",
                    device=self.device_id
                )
            except Exception as e_base:
                logger.error(f"Falla crítica al inicializar pipeline NER: {e_base}")
                self._nlp_pipeline = None

    def extraer_entidades(self, texto: str) -> ResultadoInferenciaNER:
        """
        Ejecuta la inferencia sobre una oración de texto plano individual.
        Retorna un ResultadoInferenciaNER tipado con todas las entidades extraídas.
        """
        if not texto or not str(texto).strip():
            return ResultadoInferenciaNER(
                texto=texto or "",
                entidades=[],
                tiempo_inferencia_ms=0.0,
                modelo=self.model_name,
                dispositivo=self.dispositivo_nombre
            )

        texto_limpio = str(texto).strip()
        t_inicio = time.perf_counter()

        # 1. Inferencia con Modelo BETO si está disponible
        entidades_beto = []
        if self._nlp_pipeline is not None:
            try:
                predicciones = self._nlp_pipeline(texto_limpio)
                entidades_beto = self._procesar_predicciones_beto(texto_limpio, predicciones)
            except Exception as err:
                logger.error(f"Error durante inferencia BETO sobre '{texto_limpio[:50]}...': {err}")

        # 2. Extracción complementaria con reglas semánticas de dominio (regex)
        entidades_reglas = self._extraer_entidades_por_reglas(texto_limpio)

        # 3. Consolidación y resolución de solapamientos
        entidades_consolidadas = self._consolidar_entidades(texto_limpio, entidades_beto, entidades_reglas)

        # 4. Enriquecimiento con Catálogo Gazetteer
        entidades_finales = self._enriquecer_con_catalogo(entidades_consolidadas)

        t_fin = time.perf_counter()
        tiempo_ms = (t_fin - t_inicio) * 1000.0

        return ResultadoInferenciaNER(
            texto=texto_limpio,
            entidades=entidades_finales,
            tiempo_inferencia_ms=tiempo_ms,
            modelo=self.model_name,
            dispositivo=self.dispositivo_nombre
        )

    def extraer_lote(
        self,
        textos: List[str],
        batch_size: int = DEFAULT_BATCH_SIZE
    ) -> List[ResultadoInferenciaNER]:
        """
        Procesa un lote de oraciones aprovechando procesamiento optimizado en pipeline.
        Registra automáticamente telemetría de rendimiento (latencia, tokens/s, entidades).
        """
        if not textos:
            return []

        t_inicio = time.perf_counter()
        resultados: List[ResultadoInferenciaNER] = []
        for i in range(0, len(textos), batch_size):
            chunk = textos[i : i + batch_size]
            for t in chunk:
                resultados.append(self.extraer_entidades(t))

        t_total_ms = (time.perf_counter() - t_inicio) * 1000.0
        try:
            self.telemetria.registrar_lote(resultados, tiempo_total_ms=t_total_ms)
        except Exception as e_tel:
            logger.warning(f"No se pudo registrar telemetría del lote: {e_tel}")

        return resultados


    def _procesar_predicciones_beto(
        self,
        texto: str,
        predicciones: List[Dict[str, Any]]
    ) -> List[EntidadExtraida]:
        """
        Transforma y desambigua los outputs del pipeline de BETO (PER, LOC, ORG, MISC)
        hacia las categorías de GiraGroup (DOCENTE, ESTUDIANTE, PROGRAMA).
        """
        entidades: List[EntidadExtraida] = []
        for pred in predicciones:
            etiqueta = pred.get("entity_group", "MISC").upper()
            start = int(pred.get("start", 0))
            end = int(pred.get("end", 0))
            score = float(pred.get("score", 0.0))
            palabra = texto[start:end]

            # Ajuste de bordes si hay espacios accidentales
            while palabra and palabra[0].isspace():
                start += 1
                palabra = texto[start:end]
            while palabra and palabra[-1].isspace():
                end -= 1
                palabra = texto[start:end]

            if not palabra or len(palabra) < 2:
                continue

            # Desambiguación semántica de entidades PER
            tipo_final = TipoEntidad.OTRO
            if etiqueta == "PER":
                tipo_final = self._desambiguar_persona(texto, start, end)
            elif etiqueta in ("MISC", "ORG"):
                palabra_limpia = palabra.strip().upper()
                # Excluir siglas y palabras de control de ser confundidas con programas
                if palabra_limpia in ("CI", "C.I.", "BS", "BS.", "BOB", "NRO", "NRO.", "FECHA", "FACTURA", "RECIBO"):
                    tipo_final = TipoEntidad.OTRO
                # Verificar si parece un programa académico
                elif any(w in palabra.lower() for w in ["diplomado", "experto", "curso", "maestria", "licenciatura", "programa"]):
                    tipo_final = TipoEntidad.PROGRAMA
                elif self.gazetteer.buscar_por_alias(palabra):
                    tipo_final = TipoEntidad.PROGRAMA
                elif "programa" in texto[:start].lower() and len(palabra) > 3:
                    tipo_final = TipoEntidad.PROGRAMA
                else:
                    tipo_final = TipoEntidad.OTRO
            elif etiqueta == "LOC":

                tipo_final = TipoEntidad.OTRO

            if tipo_final != TipoEntidad.OTRO:
                entidades.append(
                    EntidadExtraida(
                        tipo=tipo_final,
                        valor=palabra,
                        start_char=start,
                        end_char=end,
                        score=score,
                        origen="BETO_NER",
                        metadata={"etiqueta_original": etiqueta}
                    )
                )

        return entidades

    def _desambiguar_persona(self, texto: str, start: int, end: int) -> TipoEntidad:
        """
        Analiza el contexto léxico izquierdo y derecho del span para discriminar
        con precisión entre DOCENTE y ESTUDIANTE usando proximidad inmediata de tokens.
        """
        # Contexto inmediato anterior (hasta 40 caracteres antes)
        izq_raw = texto[max(0, start - 40) : start].lower()
        # Contexto inmediato posterior (hasta 40 caracteres después)
        der_raw = texto[end : min(len(texto), end + 40)].lower()

        tokens_izq = [t for t in re.split(r'[\s,;:()]+', izq_raw) if t]
        ultimo_token_izq = tokens_izq[-1] if tokens_izq else ""
        penultimo_token_izq = tokens_izq[-2] if len(tokens_izq) >= 2 else ""

        # 1. Regla de máxima prioridad: token inmediato precedente
        if ultimo_token_izq in ("estudiante", "alumno", "postulante", "inscrito", "participante"):
            return TipoEntidad.ESTUDIANTE
        if penultimo_token_izq in ("estudiante", "alumno") and ultimo_token_izq in ("de", "del", "al"):
            return TipoEntidad.ESTUDIANTE

        if ultimo_token_izq in TITULOS_PERSONA_TUPLA:
            return TipoEntidad.DOCENTE
        if penultimo_token_izq in ("docente", "profesor") and ultimo_token_izq in ("de", "del", "el"):
            return TipoEntidad.DOCENTE

        # 2. Búsqueda de palabras clave en el segmento izquierdo más cercano
        # Revisamos desde el más cercano hacia atrás
        for tok in reversed(tokens_izq):
            if tok in ("estudiante", "alumno", "postulante", "inscrito"):
                return TipoEntidad.ESTUDIANTE
            if tok in TITULOS_PERSONA_TUPLA:
                return TipoEntidad.DOCENTE

        # 3. Posición respecto a verbos evaluativos ("evaluó", "calificó")
        # Si dice "... evaluó al ..." y estamos después, típicamente es el evaluado (estudiante)
        if "evaluó al" in izq_raw or "evaluo al" in izq_raw or "calificó al" in izq_raw or "califico al" in izq_raw:
            return TipoEntidad.ESTUDIANTE

        if "evaluó" in der_raw or "evaluo" in der_raw or "calificó" in der_raw or "califico" in der_raw:
            return TipoEntidad.DOCENTE

        # 4. Fallback si el nombre está en el catálogo de docentes
        if self.gazetteer.es_docente_conocido(texto[start:end]):
            return TipoEntidad.DOCENTE

        return TipoEntidad.ESTUDIANTE


    def _extraer_entidades_por_reglas(self, texto: str) -> List[EntidadExtraida]:
        """
        Extrae entidades con patrones sintácticos fuertes (POS, NOTA, MONTO, CI, FECHA, FACTURA).
        """
        entidades: List[EntidadExtraida] = []

        # 1. Códigos POS
        for m in PATRON_POS.finditer(texto):
            entidades.append(
                EntidadExtraida(
                    tipo=TipoEntidad.POS,
                    valor=m.group(0),
                    start_char=m.start(0),
                    end_char=m.end(0),
                    score=0.99,
                    origen="REGEX_SEMANTICO",
                    metadata={"codigo_pos": m.group(1)}
                )
            )

        # 2. Notas / Calificaciones
        for m in PATRON_NOTA.finditer(texto):
            valor_nota = m.group(1)
            start_val = m.start(1)
            end_val = m.end(1)
            try:
                num = float(valor_nota.replace(",", "."))
                if 0.0 <= num <= 100.0:
                    entidades.append(
                        EntidadExtraida(
                            tipo=TipoEntidad.NOTA,
                            valor=valor_nota,
                            start_char=start_val,
                            end_char=end_val,
                            score=0.98,
                            origen="REGEX_SEMANTICO",
                            metadata={"valor_numerico": num}
                        )
                    )
            except ValueError:
                pass

        # 3. Montos monetarios (Bs)
        for m in PATRON_MONTO.finditer(texto):
            valor_monto = m.group(1)
            start_val = m.start(1)
            end_val = m.end(1)
            entidades.append(
                EntidadExtraida(
                    tipo=TipoEntidad.MONTO,
                    valor=valor_monto,
                    start_char=start_val,
                    end_char=end_val,
                    score=0.97,
                    origen="REGEX_SEMANTICO",
                    metadata={"moneda": "BOB"}
                )
            )

        # 4. Cédula de Identidad (CI)
        for m in PATRON_CI.finditer(texto):
            valor_ci = m.group(1)
            start_val = m.start(1)
            end_val = m.end(1)
            entidades.append(
                EntidadExtraida(
                    tipo=TipoEntidad.CI,
                    valor=valor_ci,
                    start_char=start_val,
                    end_char=end_val,
                    score=0.96,
                    origen="REGEX_SEMANTICO"
                )
            )

        # 5. Módulo
        for m in PATRON_MODULO.finditer(texto):
            valor_mod = m.group(1).strip()
            if valor_mod:
                entidades.append(
                    EntidadExtraida(
                        tipo=TipoEntidad.MODULO,
                        valor=valor_mod,
                        start_char=m.start(1),
                        end_char=m.start(1) + len(valor_mod),
                        score=0.90,
                        origen="REGEX_SEMANTICO"
                    )
                )

        # 6. Factura
        for m in PATRON_FACTURA.finditer(texto):
            valor_fac = m.group(1)
            entidades.append(
                EntidadExtraida(
                    tipo=TipoEntidad.FACTURA,
                    valor=valor_fac,
                    start_char=m.start(1),
                    end_char=m.end(1),
                    score=0.92,
                    origen="REGEX_SEMANTICO"
                )
            )

        # 7. Fecha
        for m in PATRON_FECHA.finditer(texto):
            valor_fec = m.group(1)
            entidades.append(
                EntidadExtraida(
                    tipo=TipoEntidad.FECHA,
                    valor=valor_fec,
                    start_char=m.start(1),
                    end_char=m.end(1),
                    score=0.95,
                    origen="REGEX_SEMANTICO"
                )
            )

        return entidades

    def _consolidar_entidades(
        self,
        texto: str,
        entidades_beto: List[EntidadExtraida],
        entidades_reglas: List[EntidadExtraida]
    ) -> List[EntidadExtraida]:
        """
        Une predicciones de BETO y reglas semánticas, resolviendo colisiones espaciales
        a favor de la entidad con mayor score o mayor especificidad.
        """
        todas = entidades_beto + entidades_reglas
        if not todas:
            return []

        # Ordenar por posición inicial y longitud descendente
        todas.sort(key=lambda e: (e.start_char, -(e.end_char - e.start_char), -e.score))

        consolidadas: List[EntidadExtraida] = []
        for cand in todas:
            # Validar integridad estricta del offset
            if texto[cand.start_char : cand.end_char] != cand.valor:
                # Ajuste de seguridad si difiere por whitespace
                sub = texto[cand.start_char : cand.end_char]
                if sub.strip() == cand.valor.strip():
                    cand.valor = sub

            # Verificar solapamiento con las ya aceptadas
            solapada = False
            for ac in consolidadas:
                # Condición de intersección no vacía: max(start) < min(end)
                if max(cand.start_char, ac.start_char) < min(cand.end_char, ac.end_char):
                    solapada = True
                    break

            if not solapada:
                consolidadas.append(cand)

        # Reordenar cronológicamente por aparición en el texto
        consolidadas.sort(key=lambda e: e.start_char)
        return consolidadas

    def _enriquecer_con_catalogo(
        self,
        entidades: List[EntidadExtraida]
    ) -> List[EntidadExtraida]:
        """
        Cruza las entidades extraídas con el catálogo en memoria de programas.
        Eleva la confianza probabilística a 0.99 si existe match exacto o canónico.
        """
        for ent in entidades:
            if ent.tipo == TipoEntidad.POS:
                info_pos = self.gazetteer.buscar_por_pos(ent.valor)
                if info_pos:
                    ent.score = max(ent.score, 0.99)
                    nom_prog = info_pos.get("nombre_programa") or info_pos.get("nombre")
                    ent.metadata["programa_asociado"] = nom_prog
            elif ent.tipo == TipoEntidad.PROGRAMA:

                info_prog = self.gazetteer.buscar_por_alias(ent.valor)
                if info_prog:
                    ent.score = max(ent.score, 0.98)
                    ent.metadata["id_programa"] = info_prog.get("id")
                    ent.metadata["pos_canonico"] = info_prog.get("pos")

        return entidades


# Alias canónico
NEREngine = BetoNEREngine
