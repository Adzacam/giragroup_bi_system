"""
backend/services/catalog_service.py
------------------------------------
Servicio de consulta para catálogos dimensionales: Estudiantes, Docentes y Módulos.
Aplica filtrado por Mínimo Privilegio (PoLP) en la vista de detalle.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from models.dim_estudiante import DimEstudiante
from models.dim_docente import DimDocente
from models.dim_modulo import DimModulo
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera


class CatalogService:
    def __init__(self, db: Session):
        self.db = db

    def listar_estudiantes(self, busqueda: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        query = self.db.query(DimEstudiante)
        if busqueda:
            termino = f"%{busqueda.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(DimEstudiante.nombre_completo).like(termino),
                    func.lower(DimEstudiante.codigo_estudiante).like(termino)
                )
            )
        total = query.count()
        estudiantes = query.order_by(DimEstudiante.nombre_completo).offset(offset).limit(limit).all()
        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": estudiantes
        }

    def detalle_estudiante(self, id_estudiante: int, rol_usuario: str) -> Optional[Dict[str, Any]]:
        est = self.db.query(DimEstudiante).filter(DimEstudiante.id_estudiante == id_estudiante).first()
        if not est:
            return None

        # Historial académico
        hechos_aca = (
            self.db.query(FactRendimientoAcademico, DimModulo.nombre_modulo)
            .outerjoin(DimModulo, FactRendimientoAcademico.id_modulo == DimModulo.id_modulo)
            .filter(FactRendimientoAcademico.id_estudiante == id_estudiante)
            .all()
        )
        historial = [
            {
                "modulo": mod_nombre or "Módulo no asignado",
                "nota_final": float(h.nota_final) if h.nota_final is not None else None,
                "asistencia_pct": float(h.asistencia_pct) if h.asistencia_pct is not None else None,
                "estado_academico": h.estado_academico
            }
            for h, mod_nombre in hechos_aca
        ]

        # Situación financiera (SOLO para ADMIN y ANALISTA_FINANCIERO por PoLP)
        fin_resumen = None
        if rol_usuario in ("ADMIN", "ANALISTA_FINANCIERO"):
            hecho_fin = (
                self.db.query(FactSituacionFinanciera)
                .filter(FactSituacionFinanciera.id_estudiante == id_estudiante)
                .order_by(FactSituacionFinanciera.fecha_registro.desc())
                .first()
            )
            if hecho_fin:
                fin_resumen = {
                    "monto_deuda": float(hecho_fin.monto_deuda) if hecho_fin.monto_deuda is not None else 0.0,
                    "cuotas_impagas": hecho_fin.cuotas_impagas or 0,
                    "estado_cartera": hecho_fin.estado_cartera or "Vigente",
                    "tipo_alerta": hecho_fin.tipo_alerta
                }

        return {
            "id_estudiante": est.id_estudiante,
            "nombre_completo": est.nombre_completo,
            "codigo_estudiante": est.codigo_estudiante,
            "ciudad": est.ciudad,
            "nivel_academico": est.nivel_academico,
            "historial_academico": historial,
            "situacion_financiera": fin_resumen
        }

    def listar_docentes(self, busqueda: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        query = self.db.query(DimDocente)
        if busqueda:
            termino = f"%{busqueda.strip().lower()}%"
            query = query.filter(func.lower(DimDocente.nombre_completo).like(termino))
        docentes = query.order_by(DimDocente.nombre_completo).limit(limit).all()
        return {
            "status": "success",
            "total": len(docentes),
            "data": docentes
        }

    def listar_modulos(self, busqueda: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        query = self.db.query(DimModulo)
        if busqueda:
            termino = f"%{busqueda.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(DimModulo.nombre_modulo).like(termino),
                    func.lower(DimModulo.pos_code).like(termino)
                )
            )
        modulos = query.order_by(DimModulo.nombre_modulo).limit(limit).all()
        return {
            "status": "success",
            "total": len(modulos),
            "data": modulos
        }
