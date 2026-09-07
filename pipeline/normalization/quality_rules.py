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
        Retorna: (es_valido, motivo_error_o_none, nota_numerica_o_none)
        """
        if nota is None or str(nota).strip() == "" or str(nota).strip().lower() in ("nan", "none", "null", "-"):
            return False, "NOTA_NULA_O_VACIA", None

        try:
            val_txt = str(nota).strip().replace(",", ".")
            num = float(val_txt)
        except (ValueError, TypeError):
            return False, f"NOTA_NO_NUMERICA: '{nota}'", None

        if num < self.nota_min or num > self.nota_max:
            return False, f"NOTA_FUERA_DE_RANGO: {num} (Rango válido [{self.nota_min}, {self.nota_max}])", num

        return True, None, num

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

        # 5. Validación de Inferencia BETO NER (Criterio 1)
        if inferencia_ner and inferencia_ner.entidades:
            for ent in inferencia_ner.entidades:
                if ent.score < self.umbral_beto:
                    resultado.agregar_motivo(
                        motivo=f"BETO_CONF_BAJA: Entidad {ent.tipo} ('{ent.valor}') score {ent.score:.4f} < {self.umbral_beto:.2f}",
                        severidad=SeveridadRegla.WARNING,
                        campo=ent.tipo.lower(),
                        valor=ent.valor
                    )
        elif "confianza_ia" in registro or "score_beto" in registro:
            conf_ia = registro.get("confianza_ia") or registro.get("score_beto")
            try:
                c_num = float(conf_ia)
                if c_num < self.umbral_beto:
                    resultado.agregar_motivo(
                        motivo=f"BETO_CONF_BAJA: Inferencia general score {c_num:.4f} < {self.umbral_beto:.2f}",
                        severidad=SeveridadRegla.WARNING,
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
        Evalúa la integridad de un registro financiero (cobranzas, pagos, moras).
        """
        resultado = ResultadoCalidad(valores_auditados=dict(registro))

        monto_raw = registro.get("monto") or registro.get("importe") or registro.get("saldo")
        if monto_raw is not None and str(monto_raw).strip() != "":
            try:
                monto_txt = str(monto_raw).strip().replace(",", ".")
                m_num = float(monto_txt)
                if m_num < 0:
                    resultado.agregar_motivo(
                        motivo=f"MONTO_NEGATIVO: {m_num:.2f} Bs (posible reversión o error)",
                        severidad=SeveridadRegla.WARNING,
                        campo="monto",
                        valor=m_num
                    )
            except (ValueError, TypeError):
                resultado.agregar_motivo(
                    motivo=f"MONTO_NO_NUMERICO: '{monto_raw}'",
                    severidad=SeveridadRegla.ERROR,
                    campo="monto",
                    valor=monto_raw
                )

        # Validación de Identificador de Transacción o Estudiante
        ci_val = registro.get("ci") or registro.get("codigo_alumno")
        if ci_val and str(ci_val).upper().startswith("TEMP-CI-"):
            resultado.agregar_motivo(
                motivo=f"CI_FINANCIERO_SINTETICO: Cobranza vinculada a CI temporal '{ci_val}'",
                severidad=SeveridadRegla.ERROR,
                campo="ci",
                valor=ci_val
            )

        # Validación NER si existe
        if inferencia_ner and inferencia_ner.entidades:
            for ent in inferencia_ner.entidades:
                if ent.score < self.umbral_beto:
                    resultado.agregar_motivo(
                        motivo=f"BETO_CONF_BAJA_FIN: {ent.tipo} ('{ent.valor}') score {ent.score:.4f} < {self.umbral_beto:.2f}",
                        severidad=SeveridadRegla.WARNING,
                        campo=ent.tipo.lower(),
                        valor=ent.valor
                    )

        return resultado
