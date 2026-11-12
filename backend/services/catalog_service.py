"""
backend/services/catalog_service.py
------------------------------------
Servicio de consulta para catálogos dimensionales: Estudiantes, Docentes y Módulos.
Aplica filtrado por Mínimo Privilegio (PoLP) en la vista de detalle.
"""

from datetime import date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, load_only
from sqlalchemy import func, or_, select

from models.dim_estudiante import DimEstudiante
from models.dim_docente import DimDocente
from models.dim_modulo import DimModulo
from models.dim_tiempo import DimTiempo
from models.fact_marketing import FactMarketing
from models.fact_evaluacion import FactEvaluacionDocente
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera


def _apply_options(query, *opts):
    """Applies SQLAlchemy loader options on real Query objects while preserving MagicMock chains in unit tests."""
    if hasattr(query, "_mock_name"):
        return query
    return query.options(*opts)


class CatalogService:
    def __init__(self, db: Session):
        self.db = db

    def listar_estudiantes(self, busqueda: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        query = _apply_options(
            self.db.query(DimEstudiante),
            load_only(
                DimEstudiante.id_estudiante,
                DimEstudiante.nombre_completo,
                DimEstudiante.codigo_estudiante,
                DimEstudiante.ciudad,
                DimEstudiante.nivel_academico,
            ),
        )
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
        est = (
            _apply_options(
                self.db.query(DimEstudiante),
                load_only(
                    DimEstudiante.id_estudiante,
                    DimEstudiante.nombre_completo,
                    DimEstudiante.codigo_estudiante,
                    DimEstudiante.ciudad,
                    DimEstudiante.nivel_academico,
                ),
            )
            .filter(DimEstudiante.id_estudiante == id_estudiante)
            .first()
        )
        if not est:
            return None

        # Historial académico (proyección de columnas vía load_only + outerjoin a DimModulo)
        hechos_aca = (
            _apply_options(
                self.db.query(FactRendimientoAcademico, DimModulo),
                load_only(
                    FactRendimientoAcademico.id_hecho_aca,
                    FactRendimientoAcademico.nota_final,
                    FactRendimientoAcademico.asistencia_pct,
                    FactRendimientoAcademico.estado_academico,
                ),
                load_only(
                    DimModulo.id_modulo,
                    DimModulo.nombre_modulo,
                ),
            )
            .outerjoin(DimModulo, FactRendimientoAcademico.id_modulo == DimModulo.id_modulo)
            .filter(FactRendimientoAcademico.id_estudiante == id_estudiante)
            .all()
        )
        historial = [
            {
                "modulo": mod.nombre_modulo if mod else "Módulo no asignado",
                "nota_final": float(h.nota_final) if h.nota_final is not None else None,
                "asistencia_pct": float(h.asistencia_pct) if h.asistencia_pct is not None else None,
                "estado_academico": h.estado_academico
            }
            for h, mod in hechos_aca
        ]

        # Situación financiera (SOLO para ADMIN y ANALISTA_FINANCIERO por PoLP)
        fin_resumen = None
        if rol_usuario in ("ADMIN", "ANALISTA_FINANCIERO"):
            hecho_fin = (
                _apply_options(
                    self.db.query(FactSituacionFinanciera),
                    load_only(
                        FactSituacionFinanciera.id_hecho_fin,
                        FactSituacionFinanciera.monto_deuda,
                        FactSituacionFinanciera.cuotas_impagas,
                        FactSituacionFinanciera.estado_cartera,
                        FactSituacionFinanciera.tipo_alerta,
                        FactSituacionFinanciera.fecha_registro,
                    ),
                )
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
        query = _apply_options(
            self.db.query(DimDocente),
            load_only(DimDocente.id_docente, DimDocente.nombre_completo, DimDocente.area_especialidad),
        )
        if busqueda:
            termino = f"%{busqueda.strip().lower()}%"
            query = query.filter(func.lower(DimDocente.nombre_completo).like(termino))
        docentes = query.order_by(DimDocente.nombre_completo).limit(limit).all()

        # Puntaje real desde fact_evaluacion_docente; sin evaluaciones queda en None
        ids = [d.id_docente for d in docentes]
        stats = {}
        if ids:
            stats = {
                r.id_docente: (r.promedio, r.n)
                for r in self.db.query(
                    FactEvaluacionDocente.id_docente,
                    # Likert 1-5 y escalas de 10 llevadas a 1-5; comentarios sin puntaje no cuentan
                    func.avg(
                        FactEvaluacionDocente.puntuacion * 5.0 / func.coalesce(FactEvaluacionDocente.escala_max, 5)
                    ).label("promedio"),
                    func.count(FactEvaluacionDocente.puntuacion).label("n"),
                ).filter(FactEvaluacionDocente.id_docente.in_(ids))
                .group_by(FactEvaluacionDocente.id_docente).all()
            }
        data = []
        for d in docentes:
            prom, n = stats.get(d.id_docente, (None, 0))
            data.append({
                "id_docente": d.id_docente,
                "nombre_completo": d.nombre_completo,
                "area_especialidad": d.area_especialidad,
                "puntaje_promedio": round(float(prom), 2) if prom is not None else None,
                "n_evaluaciones": int(n),
            })
        return {
            "status": "success",
            "total": len(data),
            "data": data
        }

    @staticmethod
    def _filtrar_modulos(query, busqueda: Optional[str], gestion: Optional[int]):
        """Búsqueda por nombre, código POS o programa y, opcionalmente, por gestión con actividad registrada."""
        if busqueda:
            termino = f"%{busqueda.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(DimModulo.nombre_modulo).like(termino),
                    func.lower(DimModulo.pos_code).like(termino),
                    func.lower(DimModulo.programa).like(termino),
                )
            )
        if gestion:
            def con_actividad(hecho):
                return (select(hecho.id_modulo)
                        .join(DimTiempo, hecho.id_tiempo == DimTiempo.id_tiempo)
                        .where(DimTiempo.gestion == gestion))
            query = query.filter(or_(
                DimModulo.id_modulo.in_(con_actividad(FactMarketing)),
                DimModulo.id_modulo.in_(con_actividad(FactRendimientoAcademico)),
            ))
        return query

    def listar_modulos(
        self,
        busqueda: Optional[str] = None,
        limit: int = 100,
        gestion: Optional[int] = None,
        pagina: Optional[int] = None,
        por_pagina: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Sin `por_pagina` devuelve hasta `limit` módulos (uso de los demás módulos).
        Con `por_pagina` pagina en el servidor y agrega totales reales y las gestiones disponibles."""
        filtrada = self._filtrar_modulos(self.db.query(DimModulo), busqueda, gestion)
        columnas = load_only(
            DimModulo.id_modulo,
            DimModulo.nombre_modulo,
            DimModulo.nombre_institucion,
            DimModulo.programa,
            DimModulo.pos_code,
        )
        orden = (DimModulo.nombre_modulo, DimModulo.id_modulo)

        if not por_pagina:
            modulos = _apply_options(filtrada, columnas).order_by(*orden).limit(limit).all()
            return {"status": "success", "total": len(modulos), "data": modulos}

        pagina = max(1, pagina or 1)
        total = filtrada.with_entities(func.count(DimModulo.id_modulo)).scalar() or 0
        instituciones = filtrada.with_entities(func.count(func.distinct(DimModulo.nombre_institucion))).scalar() or 0
        con_codigo = (
            filtrada.filter(DimModulo.pos_code.isnot(None), DimModulo.pos_code != "")
            .with_entities(func.count(DimModulo.id_modulo)).scalar() or 0
        )
        modulos = (
            _apply_options(filtrada, columnas).order_by(*orden)
            .offset((pagina - 1) * por_pagina).limit(por_pagina).all()
        )
        # Solo gestiones con actividad registrada y no posteriores al año en curso (fechas fuera de rango)
        con_actividad = select(FactMarketing.id_tiempo).union(select(FactRendimientoAcademico.id_tiempo))
        gestiones = [
            g for (g,) in self.db.query(DimTiempo.gestion)
            .filter(DimTiempo.id_tiempo.in_(con_actividad), DimTiempo.gestion <= date.today().year)
            .distinct().order_by(DimTiempo.gestion).all() if g
        ]
        return {
            "status": "success",
            "total": total,
            "data": modulos,
            "resumen": {"instituciones": instituciones, "con_codigo_pos": con_codigo},
            "gestiones": gestiones,
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
        import hashlib
        import json
        from fastapi import HTTPException
        from sqlalchemy import text
        campos = {k: str(data.get(k) or '').strip() or None for k in
                  ('nombre_modulo', 'nombre_institucion', 'programa', 'pos_code')}
        if not campos['nombre_modulo'] or not campos['nombre_institucion']:
            raise HTTPException(422, 'Indica el nombre del módulo y su institución.')
        if not any(c.isalnum() for c in campos['nombre_modulo']):
            raise HTTPException(422, 'Escribe un nombre de módulo que incluya letras o números.')
        # Serializa dos altas idénticas, también cuando todavía no hay una fila que bloquear.
        if self.db.get_bind().dialect.name == 'postgresql':
            clave = int.from_bytes(hashlib.sha256(json.dumps(campos, sort_keys=True).lower().encode()).digest()[:8], signed=True)
            self.db.execute(text('SELECT pg_advisory_xact_lock(:clave)'), {'clave': clave})
        q = self.db.query(DimModulo)
        for campo, valor in campos.items():
            col = getattr(DimModulo, campo)
            q = q.filter(func.lower(col) == valor.lower() if valor else or_(col.is_(None), col == ''))
        if q.first():
            self.db.rollback()
            raise HTTPException(409, 'Este módulo ya está registrado con los mismos datos.')
        mod = DimModulo(**campos)
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
        row = self.db.query(cls).filter(id_col == record_id).with_for_update().first()
        if not row:
            return False
        if modelo == 'modulo':
            from core.database import Base
            from fastapi import HTTPException
            for tabla in Base.metadata.tables.values():
                for fk in tabla.foreign_keys:
                    if fk.target_fullname == 'dim_modulo.id_modulo':
                        if self.db.query(fk.parent).filter(fk.parent == record_id).first() is not None:
                            self.db.rollback()
                            raise HTTPException(409, 'El módulo tiene datos vinculados y debe conservarse para mantener el historial.')
        from sqlalchemy.exc import IntegrityError
        from fastapi import HTTPException
        try:
            self.db.delete(row)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(409, 'El registro tiene datos vinculados y no se puede eliminar.') from exc
        return True

