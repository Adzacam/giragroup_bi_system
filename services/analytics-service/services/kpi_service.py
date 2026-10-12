"""
backend/services/kpi_service.py
--------------------------------
Servicio de cálculo y consolidación de Indicadores Clave de Desempeño (KPIs)
del Cuadro de Mando Integral (CMI) y analítica institucional.
"""

from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.dim_origen import DimOrigenDocumental
from models.staging_entidad import StagingEntidadNoResuelta


class KPIService:
    def __init__(self, db: Session):
        self.db = db

    def obtener_kpis_academicos(self) -> Dict[str, Any]:
        total_eval = self.db.query(func.count(FactRendimientoAcademico.id_hecho_aca)).scalar() or 0
        if total_eval == 0:
            return {
                "promedio_general_notas": 0.0,
                "tasa_aprobacion_pct": 0.0,
                "tasa_reprobacion_pct": 0.0,
                "estudiantes_en_riesgo_academico": 0,
                "estudiantes_en_riesgo_desercion": 0,
                "total_evaluaciones_registradas": 0
            }

        avg_nota = self.db.query(func.avg(FactRendimientoAcademico.nota_final)).filter(
            FactRendimientoAcademico.nota_final.isnot(None)
        ).scalar() or 0.0

        aprobados = self.db.query(func.count(FactRendimientoAcademico.id_hecho_aca)).filter(
            FactRendimientoAcademico.nota_final >= 51.0
        ).scalar() or 0

        riesgo_aca = self.db.query(func.count(FactRendimientoAcademico.id_hecho_aca)).filter(
            FactRendimientoAcademico.nota_final.isnot(None),
            FactRendimientoAcademico.nota_final <= 70.0
        ).scalar() or 0

        riesgo_des = self.db.query(func.count(FactRendimientoAcademico.id_hecho_aca)).filter(
            FactRendimientoAcademico.incumplimiento_actividades_pct > 30.0
        ).scalar() or 0

        tasa_apr = round((aprobados / total_eval) * 100.0, 2)
        tasa_rep = round(100.0 - tasa_apr, 2)

        return {
            "promedio_general_notas": round(float(avg_nota), 2),
            "tasa_aprobacion_pct": tasa_apr,
            "tasa_reprobacion_pct": tasa_rep,
            "estudiantes_en_riesgo_academico": int(riesgo_aca),
            "estudiantes_en_riesgo_desercion": int(riesgo_des),
            "total_evaluaciones_registradas": int(total_eval)
        }

    def obtener_kpis_financieros(self) -> Dict[str, Any]:
        total_fin = self.db.query(func.count(FactSituacionFinanciera.id_hecho_fin)).scalar() or 0
        if total_fin == 0:
            return {
                "monto_total_deuda_bs": 0.0,
                "estudiantes_con_cuotas_impagas": 0,
                "total_cuotas_impagas": 0,
                "estudiantes_cartera_previsionable": 0,
                "estudiantes_cartera_mora": 0,
                "estudiantes_cartera_vigente": 0
            }

        total_deuda = self.db.query(func.sum(FactSituacionFinanciera.monto_deuda)).scalar() or 0.0
        con_mora = self.db.query(func.count(FactSituacionFinanciera.id_hecho_fin)).filter(
            FactSituacionFinanciera.cuotas_impagas > 0
        ).scalar() or 0

        sum_cuotas = self.db.query(func.sum(FactSituacionFinanciera.cuotas_impagas)).scalar() or 0

        previsionable = self.db.query(func.count(FactSituacionFinanciera.id_hecho_fin)).filter(
            FactSituacionFinanciera.estado_cartera == "Previsionable"
        ).scalar() or 0

        mora = self.db.query(func.count(FactSituacionFinanciera.id_hecho_fin)).filter(
            FactSituacionFinanciera.estado_cartera == "Mora"
        ).scalar() or 0

        vigente = self.db.query(func.count(FactSituacionFinanciera.id_hecho_fin)).filter(
            FactSituacionFinanciera.estado_cartera == "Vigente"
        ).scalar() or 0

        return {
            "monto_total_deuda_bs": round(float(total_deuda), 2),
            "estudiantes_con_cuotas_impagas": int(con_mora),
            "total_cuotas_impagas": int(sum_cuotas),
            "estudiantes_cartera_previsionable": int(previsionable),
            "estudiantes_cartera_mora": int(mora),
            "estudiantes_cartera_vigente": int(vigente)
        }

    def obtener_kpis_pipeline(self) -> Dict[str, Any]:
        docs_proc = self.db.query(func.count(DimOrigenDocumental.id_documento)).scalar() or 0

        avg_conf = self.db.query(func.avg(FactRendimientoAcademico.nivel_confianza_ia)).filter(
            FactRendimientoAcademico.nivel_confianza_ia.isnot(None)
        ).scalar() or 0.85

        req_rev = self.db.query(func.count(FactRendimientoAcademico.id_hecho_aca)).filter(
            FactRendimientoAcademico.requiere_revision == True
        ).scalar() or 0

        stg_count = self.db.query(func.count(StagingEntidadNoResuelta.id_staging)).filter(
            StagingEntidadNoResuelta.resuelto == False
        ).scalar() or 0

        total_hechos = self.db.query(func.count(FactRendimientoAcademico.id_hecho_aca)).scalar() or 1
        tasa_calidad = round(max(0.0, 100.0 - ((req_rev / max(1, total_hechos)) * 100.0)), 2)

        return {
            "total_documentos_procesados": int(docs_proc),
            "promedio_confianza_ia": round(float(avg_conf), 4),
            "registros_requieren_revision": int(req_rev),
            "entidades_no_resueltas_staging": int(stg_count),
            "tasa_calidad_nlp_pct": tasa_calidad
        }

    def obtener_consolidado_general(self) -> Dict[str, Any]:
        return {
            "status": "success",
            "fecha_calculo_iso": datetime.now().isoformat(),
            "academicos": self.obtener_kpis_academicos(),
            "financieros": self.obtener_kpis_financieros(),
            "pipeline_calidad": self.obtener_kpis_pipeline()
        }
