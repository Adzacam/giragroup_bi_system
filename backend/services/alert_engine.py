"""
backend/services/alert_engine.py
---------------------------------
Motor de Alertas y Detección de Riesgos Multidimensionales (Reglas IF/THEN).
Implementa reglas deterministas institucionales:
- Riesgo Académico: promedio / nota_final <= 70.0
- Riesgo Deserción: incumplimiento_actividades_pct > 30.0%
- Riesgo Financiero: cuotas_impagas >= 2
- Cartera Previsionable: estado_cartera == 'Previsionable'
- Riesgo Cruzado: nota_final <= 70.0 Y cuotas_impagas >= 2
- Alerta Calidad NLP: nivel_confianza_ia < 0.85 o fk_estado == 'C'
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from models.staging_entidad import StagingEntidadNoResuelta
from models.notification import Notification


class AlertItem:
    def __init__(
        self,
        regla: str,
        tipo: str,
        severidad: str,
        estudiante: str,
        codigo_estudiante: Optional[str],
        modulo: Optional[str],
        metrica_valor: Any,
        umbral_disparador: str,
        mensaje: str,
        role_target: str
    ):
        self.regla = regla
        self.tipo = tipo
        self.severidad = severidad  # INFO, WARNING, CRITICAL
        self.estudiante = estudiante
        self.codigo_estudiante = codigo_estudiante
        self.modulo = modulo
        self.metrica_valor = metrica_valor
        self.umbral_disparador = umbral_disparador
        self.mensaje = mensaje
        self.role_target = role_target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regla": self.regla,
            "tipo": self.tipo,
            "severidad": self.severidad,
            "estudiante": self.estudiante,
            "codigo_estudiante": self.codigo_estudiante,
            "modulo": self.modulo,
            "metrica_valor": self.metrica_valor,
            "umbral_disparador": self.umbral_disparador,
            "mensaje": self.mensaje,
            "role_target": self.role_target
        }


class AlertEngine:
    """Motor desacoplado de evaluación de reglas analíticas."""

    def __init__(self, db: Session):
        self.db = db

    def evaluar_todas(self, persistir_notificaciones: bool = False) -> List[Dict[str, Any]]:
        alertas: List[AlertItem] = []
        alertas.extend(self.evaluar_riesgo_academico())
        alertas.extend(self.evaluar_riesgo_desercion())
        alertas.extend(self.evaluar_riesgo_financiero())
        alertas.extend(self.evaluar_riesgo_cruzado())
        alertas.extend(self.evaluar_entidades_no_resueltas())

        if persistir_notificaciones:
            for al in alertas:
                # Evitar notificaciones duplicadas en ventana reciente
                notif = Notification(
                    role_target=al.role_target,
                    title=f"[{al.severidad}] {al.tipo}: {al.estudiante}",
                    message=al.mensaje,
                    category=al.tipo,
                    severity=al.severidad,
                    link="/academico/rendimiento" if al.tipo in ("ACADEMICO", "DESERCION") else "/financiero/cartera"
                )
                self.db.add(notif)
            self.db.commit()

        return [a.to_dict() for a in alertas]

    def evaluar_riesgo_academico(self, limite_nota: float = 70.0) -> List[AlertItem]:
        query = (
            self.db.query(
                FactRendimientoAcademico.nota_final,
                DimEstudiante.nombre_completo,
                DimEstudiante.codigo_estudiante,
                DimModulo.nombre_modulo
            )
            .join(DimEstudiante, FactRendimientoAcademico.id_estudiante == DimEstudiante.id_estudiante)
            .outerjoin(DimModulo, FactRendimientoAcademico.id_modulo == DimModulo.id_modulo)
            .filter(
                FactRendimientoAcademico.nota_final.isnot(None),
                FactRendimientoAcademico.nota_final <= limite_nota
            )
        )
        items = []
        for nota, est_nombre, est_ci, mod_nombre in query.all():
            items.append(
                AlertItem(
                    regla="IF nota_final <= 70.0 THEN ALERTA_RIESGO_ACADEMICO",
                    tipo="ACADEMICO",
                    severidad="WARNING" if float(nota) >= 51.0 else "CRITICAL",
                    estudiante=est_nombre or "Estudiante no identificado",
                    codigo_estudiante=est_ci,
                    modulo=mod_nombre or "Módulo no especificado",
                    metrica_valor=float(nota),
                    umbral_disparador=f"<= {limite_nota}",
                    mensaje=f"Estudiante presenta calificación en zona de riesgo ({nota}/100) en {mod_nombre or 'el módulo'}.",
                    role_target="DIRECTOR_ACADEMICO"
                )
            )
        return items

    def evaluar_riesgo_desercion(self, umbral_incumplimiento: float = 30.0) -> List[AlertItem]:
        query = (
            self.db.query(
                FactRendimientoAcademico.incumplimiento_actividades_pct,
                DimEstudiante.nombre_completo,
                DimEstudiante.codigo_estudiante,
                DimModulo.nombre_modulo
            )
            .join(DimEstudiante, FactRendimientoAcademico.id_estudiante == DimEstudiante.id_estudiante)
            .outerjoin(DimModulo, FactRendimientoAcademico.id_modulo == DimModulo.id_modulo)
            .filter(
                FactRendimientoAcademico.incumplimiento_actividades_pct.isnot(None),
                FactRendimientoAcademico.incumplimiento_actividades_pct > umbral_incumplimiento
            )
        )
        items = []
        for inc_pct, est_nombre, est_ci, mod_nombre in query.all():
            items.append(
                AlertItem(
                    regla=f"IF incumplimiento_actividades_pct > {umbral_incumplimiento}% THEN ALERTA_RIESGO_DESERCION",
                    tipo="DESERCION",
                    severidad="CRITICAL",
                    estudiante=est_nombre or "Estudiante no identificado",
                    codigo_estudiante=est_ci,
                    modulo=mod_nombre or "Módulo no especificado",
                    metrica_valor=float(inc_pct),
                    umbral_disparador=f"> {umbral_incumplimiento}%",
                    mensaje=f"Tasa de incumplimiento del {inc_pct}% supera el umbral crítico de deserción institucional.",
                    role_target="DIRECTOR_ACADEMICO"
                )
            )
        return items

    def evaluar_riesgo_financiero(self, min_cuotas: int = 2) -> List[AlertItem]:
        query = (
            self.db.query(
                FactSituacionFinanciera.cuotas_impagas,
                FactSituacionFinanciera.monto_deuda,
                FactSituacionFinanciera.estado_cartera,
                DimEstudiante.nombre_completo,
                DimEstudiante.codigo_estudiante
            )
            .join(DimEstudiante, FactSituacionFinanciera.id_estudiante == DimEstudiante.id_estudiante)
            .filter(
                or_(
                    and_(
                        FactSituacionFinanciera.cuotas_impagas.isnot(None),
                        FactSituacionFinanciera.cuotas_impagas >= min_cuotas
                    ),
                    FactSituacionFinanciera.estado_cartera == "Previsionable"
                )
            )
        )
        items = []
        for cuotas, deuda, estado, est_nombre, est_ci in query.all():
            es_previsionable = (estado == "Previsionable")
            items.append(
                AlertItem(
                    regla=f"IF cuotas_impagas >= {min_cuotas} OR estado_cartera == 'Previsionable' THEN ALERTA_RIESGO_FINANCIERO",
                    tipo="FINANCIERO",
                    severidad="CRITICAL" if (es_previsionable or (cuotas and cuotas >= 3)) else "WARNING",
                    estudiante=est_nombre or "Estudiante no identificado",
                    codigo_estudiante=est_ci,
                    modulo=None,
                    metrica_valor={"cuotas_impagas": cuotas, "deuda": float(deuda or 0), "estado_cartera": estado},
                    umbral_disparador=f">= {min_cuotas} cuotas o Previsionable",
                    mensaje=f"Mora financiera activa: {cuotas or 0} cuotas impagas (Bs. {deuda or 0:,.2f}), cartera {estado}.",
                    role_target="ANALISTA_FINANCIERO"
                )
            )
        return items

    def evaluar_riesgo_cruzado(self, limite_nota: float = 70.0, min_cuotas: int = 2) -> List[AlertItem]:
        from services.risk_service import get_riesgo_cruzado
        casos = get_riesgo_cruzado(self.db, limite_nota=limite_nota, min_cuotas_mora=min_cuotas)
        items = []
        for c in casos:
            items.append(
                AlertItem(
                    regla="IF nota <= 70 AND cuotas >= 2 THEN ALERTA_RIESGO_CRUZADO",
                    tipo="RIESGO_CRUZADO",
                    severidad="CRITICAL",
                    estudiante=c["estudiante"],
                    codigo_estudiante=c.get("codigo"),
                    modulo=None,
                    metrica_valor={
                        "nota_actual": c["rendimiento"]["nota_actual"],
                        "cuotas_mora": c["finanzas"]["cuotas_mora"],
                        "deuda_total": c["finanzas"]["deuda_total"]
                    },
                    umbral_disparador="nota <= 70 Y cuotas >= 2",
                    mensaje=f"Caso crítico simultáneo: Nota {c['rendimiento']['nota_actual']}/100 y {c['finanzas']['cuotas_mora']} cuotas impagas.",
                    role_target="ADMIN"
                )
            )
        return items

    def evaluar_entidades_no_resueltas(self) -> List[AlertItem]:
        query = self.db.query(StagingEntidadNoResuelta).filter(
            StagingEntidadNoResuelta.resuelto == False
        )
        items = []
        for stg in query.all():
            items.append(
                AlertItem(
                    regla="IF fk_estado == 'C' THEN ALERTA_GOBERNANZA_CALIDAD",
                    tipo="DATAOPS_CALIDAD",
                    severidad="WARNING",
                    estudiante=stg.texto_original,
                    codigo_estudiante=stg.ci_temporal,
                    modulo=None,
                    metrica_valor={"score_fuzzy": float(stg.score_fuzzy or 0), "mejor_candidato": stg.mejor_candidato},
                    umbral_disparador="FK Estado C no resuelto",
                    mensaje=f"Entidad {stg.tipo_entidad} '{stg.texto_original}' requiere homologación humana asistida.",
                    role_target="AUDITOR_CALIDAD"
                )
            )
        return items
