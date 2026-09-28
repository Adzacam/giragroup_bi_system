"""
pipeline/normalization/quality_rules.py
----------------------------------------
Evaluador de reglas de calidad e integridad de datos (GIRA-27).
Determina de forma determinista y transparente si un registro tabular/semántico
cumple con los estándares de certeza institucional o si debe ser marcado con
`requiere_revision = True` para inspección humana antes de persistir en analítica.

Criterios de activación:
1. Confianza probabilística BETO < 0.65 (GIRA-42).
2. Similitud RapidFuzz en catálogos < 80% (GIRA-41).
3. CI no resuelto (Estado C en GIRA-50 o prefijo TEMP-CI-*).
4. Nota numérica fuera de rango válido (< 0 o > 100).
5. Inconsistencias de coherencia académica (ej. reprobado con nota >= 51).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union

from pipeline.config import (
    UMBRAL_REVISION_BETO,
    UMBRAL_REVISION_FUZZY,
    NOTA_MINIMA_VALIDA,
    NOTA_MAXIMA_VALIDA,
    NOTA_APROBACION_MINIMA,
    PATRON_CI_BOLIVIA,
    ASISTENCIA_MINIMA_VALIDA,
    ASISTENCIA_MAXIMA_VALIDA,
    UMBRAL_DESERCION_INCUMPLIMIENTO_PCT,
    UMBRAL_RIESGO_CUOTAS_IMPAGAS,
    ESTADOS_CARTERA_VALIDOS,
)
from pipeline.semantic.ner_schema import ResultadoInferenciaNER, EntidadExtraida


class SeveridadRegla(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ResultadoCalidad:
    """
    Resultado de la evaluación de calidad sobre un registro académico o financiero.
    Preserva todos los datos originales para auditoría o revisión en la interfaz.
    """
    requiere_revision: bool = False
    motivos: List[str] = field(default_factory=list)
    severidad_maxima: SeveridadRegla = SeveridadRegla.INFO
    valores_auditados: Dict[str, Any] = field(default_factory=dict)
    detalles_reglas: List[Dict[str, Any]] = field(default_factory=list)

    def agregar_motivo(
        self,
        motivo: str,
        severidad: SeveridadRegla = SeveridadRegla.WARNING,
        campo: Optional[str] = None,
        valor: Optional[Any] = None
    ) -> None:
        """Agrega un motivo de revisión y actualiza la severidad máxima alcanzada."""
        self.requiere_revision = True
        self.motivos.append(motivo)

        jerarquia = {
            SeveridadRegla.INFO: 0,
            SeveridadRegla.WARNING: 1,
            SeveridadRegla.ERROR: 2,
            SeveridadRegla.CRITICAL: 3,
        }
        if jerarquia.get(severidad, 0) > jerarquia.get(self.severidad_maxima, 0):
            self.severidad_maxima = severidad

        self.detalles_reglas.append({
            "motivo": motivo,
            "severidad": severidad.value,
            "campo": campo,
            "valor": valor,
        })

    def to_dict(self) -> Dict[str, Any]:
        """Serializa a diccionario estándar para persistencia o API."""
        return {
            "requiere_revision": self.requiere_revision,
            "motivos": list(self.motivos),
            "severidad_maxima": self.severidad_maxima.value,
            "total_motivos": len(self.motivos),
            "valores_auditados": dict(self.valores_auditados),
            "detalles_reglas": list(self.detalles_reglas),
        }


class QualityEvaluator:
    """
    Motor de evaluación de integridad y calidad para registros extraídos.
    Aplica las políticas de certeza de GiraGroup BI.
    """

    def __init__(
        self,
        umbral_beto: float = UMBRAL_REVISION_BETO,
        umbral_fuzzy: float = UMBRAL_REVISION_FUZZY,
        nota_min: float = NOTA_MINIMA_VALIDA,
        nota_max: float = NOTA_MAXIMA_VALIDA,
        nota_aprobacion: float = NOTA_APROBACION_MINIMA
    ):
        self.umbral_beto = umbral_beto
        self.umbral_fuzzy = umbral_fuzzy
        self.nota_min = nota_min
        self.nota_max = nota_max
        self.nota_aprobacion = nota_aprobacion

    # ──────────────────────────────────────────────────────────────────────────
    # Validaciones Atómicas de Dominio
    # ──────────────────────────────────────────────────────────────────────────
    def validar_rango_nota(self, nota: Any) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Verifica que la nota sea convertible a numérico y esté en el rango [nota_min, nota_max].
        Aplica unificación de escala institucional: si la nota se encuentra en escala 0-10
        (Apéndice D ítem 7 y Apéndice E ítem 10), se unifica a escala 0-100 multiplicando por 10.
        Retorna: (es_valido, motivo_error_o_none, nota_numerica_o_none)
        """
        if nota is None or str(nota).strip() == "" or str(nota).strip().lower() in ("nan", "none", "null", "-"):
            return False, "NOTA_NULA_O_VACIA", None

        try:
            val_txt = str(nota).strip().replace(",", ".")
            num = float(val_txt)
        except (ValueError, TypeError):
            return False, f"NOTA_NO_NUMERICA: '{nota}'", None

        # Unificación de escala (si viene en rango 0 < num <= 10.0, escalar a 0-100)
        if 0.0 < num <= 10.0:
            num = round(num * 10.0, 2)

        if num < self.nota_min or num > self.nota_max:
            return False, f"NOTA_FUERA_DE_RANGO: {num} (Rango válido [{self.nota_min}, {self.nota_max}])", num

        return True, None, num

    def validar_asistencia(self, asistencia: Any) -> Tuple[bool, Optional[str], Optional[float]]:
        """Valida que el porcentaje de asistencia se ubique en [0, 100]."""
        if asistencia is None or str(asistencia).strip() in ("", "nan", "none", "null", "-"):
            return True, None, None

        try:
            val_txt = str(asistencia).strip().replace(",", ".").replace("%", "")
            num = float(val_txt)
        except (ValueError, TypeError):
            return False, f"ASISTENCIA_NO_NUMERICA: '{asistencia}'", None

        if num < ASISTENCIA_MINIMA_VALIDA or num > ASISTENCIA_MAXIMA_VALIDA:
            return False, f"ASISTENCIA_FUERA_DE_RANGO: {num}% (Rango válido [0, 100])", num

        return True, None, num

    def validar_incumplimiento(self, incumplimiento: Any) -> Tuple[bool, Optional[str], Optional[float], bool]:
        """
        Valida que el incumplimiento esté en [0, 100] y evalúa umbral de deserción (> 30%).
        Retorna: (es_valido, motivo_error_o_none, num, es_alerta_desercion)
        """
        if incumplimiento is None or str(incumplimiento).strip() in ("", "nan", "none", "null", "-"):
            return True, None, None, False

        try:
            val_txt = str(incumplimiento).strip().replace(",", ".").replace("%", "")
            num = float(val_txt)
        except (ValueError, TypeError):
            return False, f"INCUMPLIMIENTO_NO_NUMERICO: '{incumplimiento}'", None, False

        if num < 0.0 or num > 100.0:
            return False, f"INCUMPLIMIENTO_FUERA_DE_RANGO: {num}% (Rango válido [0, 100])", num, False

        es_alerta = (num > UMBRAL_DESERCION_INCUMPLIMIENTO_PCT)
        return True, None, num, es_alerta

    def validar_monto_deuda(self, monto: Any) -> Tuple[bool, Optional[str], Optional[float]]:
        """Valida que el monto de deuda sea numérico y >= 0."""
        if monto is None or str(monto).strip() in ("", "nan", "none", "null", "-"):
            return True, None, None

        try:
            val_txt = str(monto).strip().replace(",", ".").replace("Bs", "").replace("bs", "").strip()
            num = float(val_txt)
        except (ValueError, TypeError):
            return False, f"MONTO_NO_NUMERICO: '{monto}'", None

        if num < 0.0:
            return False, f"MONTO_NEGATIVO: {num:.2f} Bs (posible reversión o error)", num

        return True, None, num

    def validar_cuotas_impagas(self, cuotas: Any) -> Tuple[bool, Optional[str], Optional[int], bool]:
        """
        Valida que las cuotas impagas sean enteras >= 0 y evalúa umbral de riesgo (>= 2).
        Retorna: (es_valido, motivo_error_o_none, num, es_alerta_riesgo)
        """
        if cuotas is None or str(cuotas).strip() in ("", "nan", "none", "null", "-"):
            return True, None, None, False

        try:
            val_txt = str(cuotas).strip().split(".")[0]
            num = int(val_txt)
        except (ValueError, TypeError):
            return False, f"CUOTAS_NO_ENTERO: '{cuotas}'", None, False

        if num < 0:
            return False, f"CUOTAS_NEGATIVAS: {num} (Debe ser >= 0)", num, False

        es_riesgo = (num >= UMBRAL_RIESGO_CUOTAS_IMPAGAS)
        return True, None, num, es_riesgo

    def validar_estado_cartera(self, estado: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """Valida que el estado de cartera pertenezca a: Vigente, Mora, Previsionable."""
        if estado is None or str(estado).strip() in ("", "nan", "none", "null", "-"):
            return True, None, None

        est_txt = str(estado).strip().title()
        validos_dict = {v.lower(): v for v in ESTADOS_CARTERA_VALIDOS}
        if est_txt.lower() in validos_dict:
            return True, None, validos_dict[est_txt.lower()]

        return False, f"ESTADO_CARTERA_INVALIDO: '{estado}' (Valores válidos: {', '.join(ESTADOS_CARTERA_VALIDOS)})", est_txt

    def validar_ci_boliviano(self, ci: Any) -> Tuple[bool, Optional[str]]:
        """Verifica la sintaxis del carnet de identidad boliviano o detección de sintético."""
        if ci is None or not str(ci).strip():
            return False, "CI_FALTANTE_O_VACIO"

        ci_str = str(ci).strip().upper()
        if ci_str.startswith("TEMP-CI-"):
            return False, f"CI_SINTETICO_TEMPORAL: '{ci_str}'"

        # Remover .0 si viene de float de pandas
        if ci_str.endswith(".0"):
            ci_str = ci_str[:-2]
        ci_str = ci_str.replace(".", "").replace(" ", "")

        if PATRON_CI_BOLIVIA.match(ci_str):
            return True, None

        return False, f"CI_FORMATO_INVALIDO: '{ci}'"

    def validar_coherencia_academica(
        self,
        nota_num: Optional[float],
        estado_academico: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifica la coherencia entre la nota numérica y el estado académico descriptivo.
        Por ejemplo: No debe ser 'REPROBADO' con nota >= 51, ni 'APROBADO' con nota < 51.
        """
        if nota_num is None or not estado_academico:
            return True, None

        est = str(estado_academico).strip().upper()

        if "REPROB" in est and nota_num >= self.nota_aprobacion:
            return False, f"INCOHERENCIA_ESTADO_NOTA: Estado '{estado_academico}' incompatible con nota {nota_num} >= {self.nota_aprobacion}"

        if "APROB" in est and nota_num < self.nota_aprobacion:
            return False, f"INCOHERENCIA_ESTADO_NOTA: Estado '{estado_academico}' incompatible con nota {nota_num} < {self.nota_aprobacion}"

        return True, None

    # ──────────────────────────────────────────────────────────────────────────
    # Evaluación Consolidada de Registros Académicos
    # ──────────────────────────────────────────────────────────────────────────
    def evaluar_registro_academico(
        self,
        registro: Dict[str, Any],
        inferencia_ner: Optional[ResultadoInferenciaNER] = None
    ) -> ResultadoCalidad:
        """
        Evalúa integralmente un registro académico tabular y/o enriquecido con PLN.
        Aplica los 5 criterios canónicos de activación de GIRA-27.
        """
        resultado = ResultadoCalidad(valores_auditados=dict(registro))

        # 1. Validación de Nota Numérica (Criterio 4)
        nota_raw = (
            registro.get("nota")
            or registro.get("calificacion")
            or registro.get("nota_final")
            or registro.get("nota_raw")
            or registro.get("calificacion_final")
        )
        nota_num = None
        if nota_raw is not None and str(nota_raw).strip() != "":
            es_valida_nota, motivo_nota, num = self.validar_rango_nota(nota_raw)
            if not es_valida_nota:
                resultado.agregar_motivo(
                    motivo=motivo_nota,
                    severidad=SeveridadRegla.ERROR,
                    campo="nota",
                    valor=nota_raw
                )
            else:
                nota_num = num

        # 1.b Validación de Asistencia e Incumplimiento
        asist_raw = registro.get("asistencia_pct") or registro.get("asistencia")
        if asist_raw is not None:
            es_asist_ok, motivo_asist, num_asist = self.validar_asistencia(asist_raw)
            if not es_asist_ok:
                resultado.agregar_motivo(
                    motivo=motivo_asist,
                    severidad=SeveridadRegla.WARNING,
                    campo="asistencia_pct",
                    valor=asist_raw
                )

        incump_raw = registro.get("incumplimiento_actividades_pct") or registro.get("incumplimiento")
        if incump_raw is not None:
            es_inc_ok, motivo_inc, num_inc, es_alerta_des = self.validar_incumplimiento(incump_raw)
            if not es_inc_ok:
                resultado.agregar_motivo(
                    motivo=motivo_inc,
                    severidad=SeveridadRegla.WARNING,
                    campo="incumplimiento_actividades_pct",
                    valor=incump_raw
                )
            elif es_alerta_des:
                resultado.agregar_motivo(
                    motivo=f"ALERTA_DESERCION_INCUMPLIMIENTO: Incumplimiento {num_inc:.2f}% supera umbral crítico del 30%",
                    severidad=SeveridadRegla.WARNING,
                    campo="incumplimiento_actividades_pct",
                    valor=num_inc
                )

        # 2. Validación de CI y Resolución FK (Criterio 3)
        ci_val = registro.get("ci") or registro.get("carnet") or registro.get("documento")
        fk_res = registro.get("fk_estudiante_resolucion") or {}
        es_sintetico = (
            registro.get("es_sintetico")
            or fk_res.get("es_sintetico")
            or (ci_val and str(ci_val).upper().startswith("TEMP-CI-"))
        )
        requiere_auditoria_fk = (
            registro.get("requiere_auditoria")
            or fk_res.get("requiere_auditoria")
            or fk_res.get("estado_resolucion") == "ESTADO_C_NO_RESUELTO_SINTETICO"
            or fk_res.get("fk_estado") == "C"
        )

        if es_sintetico or requiere_auditoria_fk:
            resultado.agregar_motivo(
                motivo=f"CI_NO_RESUELTO_SINTETICO: Identificador no resuelto en padrón ('{ci_val}')",
                severidad=SeveridadRegla.ERROR,
                campo="ci",
                valor=ci_val
            )
        elif ci_val:
            es_ci_ok, motivo_ci = self.validar_ci_boliviano(ci_val)
            if not es_ci_ok:
                resultado.agregar_motivo(
                    motivo=motivo_ci,
                    severidad=SeveridadRegla.WARNING,
                    campo="ci",
                    valor=ci_val
                )

        # 3. Validación de Score RapidFuzz en Catálogos (Criterio 2)
        score_fuzzy = registro.get("score_matching") or registro.get("score_similitud")
        if score_fuzzy is not None:
            try:
                s_fuzz = float(score_fuzzy)
                if s_fuzz < self.umbral_fuzzy:
                    resultado.agregar_motivo(
                        motivo=f"SCORE_FUZZY_BAJO: {s_fuzz:.4f} < {self.umbral_fuzzy:.2f}",
                        severidad=SeveridadRegla.WARNING,
                        campo="score_matching",
                        valor=s_fuzz
                    )
            except (ValueError, TypeError):
                pass

        # 4. Coherencia Académica (Criterio 5)
        estado_aca = registro.get("estado_academico") or registro.get("estado")
        if nota_num is not None and estado_aca:
            es_coherente, motivo_coh = self.validar_coherencia_academica(nota_num, estado_aca)
            if not es_coherente:
                resultado.agregar_motivo(
                    motivo=motivo_coh,
                    severidad=SeveridadRegla.WARNING,
                    campo="estado_academico",
                    valor=f"{estado_aca} (nota={nota_num})"
                )

        # 5. Validación de Inferencia BETO NER (Corte institucional en 0.85)
        if inferencia_ner and inferencia_ner.entidades:
            for ent in inferencia_ner.entidades:
                if ent.score < self.umbral_beto:
                    nivel_str = "BAJA" if ent.score < 0.60 else "MEDIA"
                    sev = SeveridadRegla.ERROR if ent.score < 0.60 else SeveridadRegla.WARNING
                    resultado.agregar_motivo(
                        motivo=f"BETO_CONF_{nivel_str}: Entidad {ent.tipo} ('{ent.valor}') score {ent.score:.4f} < {self.umbral_beto:.2f}",
                        severidad=sev,
                        campo=ent.tipo.lower(),
                        valor=ent.valor
                    )
        elif "confianza_ia" in registro or "score_beto" in registro:
            conf_ia = registro.get("confianza_ia") or registro.get("score_beto")
            try:
                c_num = float(conf_ia)
                if c_num < self.umbral_beto:
                    nivel_str = "BAJA" if c_num < 0.60 else "MEDIA"
                    sev = SeveridadRegla.ERROR if c_num < 0.60 else SeveridadRegla.WARNING
                    resultado.agregar_motivo(
                        motivo=f"BETO_CONF_{nivel_str}: Inferencia general score {c_num:.4f} < {self.umbral_beto:.2f}",
                        severidad=sev,
                        campo="confianza_ia",
                        valor=c_num
                    )
            except (ValueError, TypeError):
                pass

        return resultado

    # ──────────────────────────────────────────────────────────────────────────
    # Evaluación de Registros Financieros
    # ──────────────────────────────────────────────────────────────────────────
    def evaluar_registro_financiero(
        self,
        registro: Dict[str, Any],
        inferencia_ner: Optional[ResultadoInferenciaNER] = None
    ) -> ResultadoCalidad:
        """
        Evalúa la integridad de un registro financiero (cobranzas, pagos, moras, deuda, cartera).
        """
        resultado = ResultadoCalidad(valores_auditados=dict(registro))

        # 1. Validación de Monto / Monto Deuda
        monto_raw = (
            registro.get("monto_deuda")
            or registro.get("monto")
            or registro.get("importe")
            or registro.get("saldo")
        )
        if monto_raw is not None and str(monto_raw).strip() != "":
            es_monto_ok, motivo_monto, num_monto = self.validar_monto_deuda(monto_raw)
            if not es_monto_ok:
                resultado.agregar_motivo(
                    motivo=motivo_monto,
                    severidad=SeveridadRegla.WARNING,
                    campo="monto_deuda",
                    valor=monto_raw
                )

        # 2. Validación de Cuotas Impagas (Umbral de riesgo >= 2)
        cuotas_raw = registro.get("cuotas_impagas") or registro.get("cuotas")
        if cuotas_raw is not None and str(cuotas_raw).strip() != "":
            es_cuotas_ok, motivo_cuotas, num_cuotas, es_riesgo = self.validar_cuotas_impagas(cuotas_raw)
            if not es_cuotas_ok:
                resultado.agregar_motivo(
                    motivo=motivo_cuotas,
                    severidad=SeveridadRegla.WARNING,
                    campo="cuotas_impagas",
                    valor=cuotas_raw
                )
            elif es_riesgo:
                resultado.agregar_motivo(
                    motivo=f"ALERTA_RIESGO_CUOTAS_IMPAGAS: Registra {num_cuotas} cuotas impagas (umbral de riesgo >= 2)",
                    severidad=SeveridadRegla.WARNING,
                    campo="cuotas_impagas",
                    valor=num_cuotas
                )

        # 3. Validación de Estado de Cartera (Vigente / Mora / Previsionable)
        cartera_raw = registro.get("estado_cartera") or registro.get("cartera")
        if cartera_raw is not None and str(cartera_raw).strip() != "":
            es_cart_ok, motivo_cart, cart_norm = self.validar_estado_cartera(cartera_raw)
            if not es_cart_ok:
                resultado.agregar_motivo(
                    motivo=motivo_cart,
                    severidad=SeveridadRegla.ERROR,
                    campo="estado_cartera",
                    valor=cartera_raw
                )

        # 4. Validación de Identificador de Transacción o Estudiante
        ci_val = registro.get("ci") or registro.get("codigo_alumno")
        if ci_val and str(ci_val).upper().startswith("TEMP-CI-"):
            resultado.agregar_motivo(
                motivo=f"CI_FINANCIERO_SINTETICO: Cobranza vinculada a CI temporal '{ci_val}'",
                severidad=SeveridadRegla.ERROR,
                campo="ci",
                valor=ci_val
            )

        # 5. Validación NER si existe (Corte institucional en 0.85)
        if inferencia_ner and inferencia_ner.entidades:
            for ent in inferencia_ner.entidades:
                if ent.score < self.umbral_beto:
                    nivel_str = "BAJA" if ent.score < 0.60 else "MEDIA"
                    sev = SeveridadRegla.ERROR if ent.score < 0.60 else SeveridadRegla.WARNING
                    resultado.agregar_motivo(
                        motivo=f"BETO_CONF_{nivel_str}_FIN: {ent.tipo} ('{ent.valor}') score {ent.score:.4f} < {self.umbral_beto:.2f}",
                        severidad=sev,
                        campo=ent.tipo.lower(),
                        valor=ent.valor
                    )
        elif "confianza_ia" in registro or "score_beto" in registro:
            conf_ia = registro.get("confianza_ia") or registro.get("score_beto")
            try:
                c_num = float(conf_ia)
                if c_num < self.umbral_beto:
                    nivel_str = "BAJA" if c_num < 0.60 else "MEDIA"
                    sev = SeveridadRegla.ERROR if c_num < 0.60 else SeveridadRegla.WARNING
                    resultado.agregar_motivo(
                        motivo=f"BETO_CONF_{nivel_str}_FIN: Inferencia general score {c_num:.4f} < {self.umbral_beto:.2f}",
                        severidad=sev,
                        campo="confianza_ia",
                        valor=c_num
                    )
            except (ValueError, TypeError):
                pass

        return resultado
