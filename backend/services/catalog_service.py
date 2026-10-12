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

    def listar_instituciones(self, busqueda: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        instituciones_db = (
            self.db.query(DimModulo.nombre_institucion)
            .distinct()
            .filter(DimModulo.nombre_institucion.isnot(None))
            .all()
        )
        nombres = [r[0] for r in instituciones_db if r[0]]
        # Catálogo base por defecto si aún no hay muchos registros
        nombres_base = ["GiraGroup S.A.", "UAGRM Business School", "Universidad Mayor de San Andrés (UMSA)", "Universidad Privada Boliviana (UPB)"]
        todos_nombres = list(dict.fromkeys(nombres + nombres_base))

        if busqueda:
            term = busqueda.strip().lower()
            todos_nombres = [n for n in todos_nombres if term in n.lower()]

        items = [
            {
                "id_institucion": idx + 1,
                "nombre": nom,
                "sigla": "".join(w[0] for w in nom.split() if w[0].isupper())[:6],
                "tipo": "Sede / Universidad Aliada",
                "estado": "Activo"
            }
            for idx, nom in enumerate(todos_nombres[:limit])
        ]
        return {
            "status": "success",
            "total": len(items),
            "data": items
        }

    def crear_estudiante(self, data: dict) -> DimEstudiante:
        est = DimEstudiante(
            nombre_completo=data["nombre_completo"],
            codigo_estudiante=data.get("codigo_estudiante") or f"EST-{self.db.query(DimEstudiante).count() + 101}",
            ciudad=data.get("ciudad") or "La Paz",
            nivel_academico=data.get("nivel_academico") or "Pregrado"
        )
        self.db.add(est)
        self.db.commit()
        self.db.refresh(est)
        return est

    def crear_docente(self, data: dict) -> DimDocente:
        doc = DimDocente(
            nombre_completo=data["nombre_completo"],
            area_especialidad=data.get("area_especialidad") or "General"
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def crear_modulo(self, data: dict) -> DimModulo:
        mod = DimModulo(
            nombre_modulo=data["nombre_modulo"],
            nombre_institucion=data.get("nombre_institucion") or "GiraGroup",
            programa=data.get("programa") or "Programa General",
            pos_code=data.get("pos_code") or f"MOD-{self.db.query(DimModulo).count() + 101}"
        )
        self.db.add(mod)
        self.db.commit()
        self.db.refresh(mod)
        return mod

    def eliminar_registro(self, modelo: str, record_id: int) -> bool:
        model_map = {
            "estudiante": (DimEstudiante, DimEstudiante.id_estudiante),
            "docente": (DimDocente, DimDocente.id_docente),
            "modulo": (DimModulo, DimModulo.id_modulo)
        }
        if modelo not in model_map:
            return False
        cls, id_col = model_map[modelo]
        row = self.db.query(cls).filter(id_col == record_id).first()
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

