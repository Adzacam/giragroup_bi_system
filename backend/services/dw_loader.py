"""
backend/services/dw_loader.py
------------------------------
Servicio de Carga al Data Warehouse con Resolución Dimensional de Llaves Foráneas.
Resuelve FKs (Estudiante, Docente, Módulo, Tiempo) contra las dimensiones del DW,
persiste los hechos (académicos y financieros) y deriva entidades no resueltas (Estado C)
a la tabla stg_entidad_no_resuelta para gobernanza y revisión asistida.
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from models.dim_estudiante import DimEstudiante
from models.dim_docente import DimDocente
from models.dim_modulo import DimModulo
from models.dim_tiempo import DimTiempo
from models.dim_origen import DimOrigenDocumental
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.staging_entidad import StagingEntidadNoResuelta

logger = logging.getLogger("dw_loader")

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

DIAS_ES = {
    1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves",
    5: "Viernes", 6: "Sábado", 7: "Domingo"
}


class DWLoaderService:
    """Cargador transaccional con resolución de entidades dimensionales."""

    def __init__(self, db: Session):
        self.db = db

    # ── 1. Resolución DimEstudiante ───────────────────────────────────────────
    def resolver_o_crear_estudiante(
        self,
        ci: Optional[str],
        nombre: Optional[str],
        doc_id: Optional[int] = None,
        confianza_ia: Optional[float] = None
    ) -> Tuple[Optional[int], str]:
        """
        Retorna (id_estudiante, fk_estado).
        fk_estado: 'A' (directo CI), 'B' (fuzzy rescatado), 'C' (derivado a staging).
        """
        if not ci and not nombre:
            return None, "C"

        es_sintetico = not ci or ci.startswith("TEMP-CI-") or "TEMP" in (ci or "")

        # Caso 1: CI válido directo
        if ci and not es_sintetico:
            est = self.db.query(DimEstudiante).filter(DimEstudiante.codigo_estudiante == ci.strip()).first()
            if est:
                return est.id_estudiante, "A"
            # Si no existe pero hay CI y nombre, se crea el estudiante
            nuevo_est = DimEstudiante(
                codigo_estudiante=ci.strip(),
                nombre_completo=(nombre or f"Estudiante {ci}").strip()
            )
            self.db.add(nuevo_est)
            self.db.flush()
            return nuevo_est.id_estudiante, "A"

        # Caso 2: CI sintético o ausente -> Búsqueda difusa por nombre en DimEstudiante
        if nombre:
            try:
                from rapidfuzz import fuzz, process
                estudiantes = self.db.query(DimEstudiante).all()
                if estudiantes:
                    nombres_map = {e.nombre_completo: e for e in estudiantes if e.nombre_completo}
                    mejor = process.extractOne(
                        nombre.strip(),
                        list(nombres_map.keys()),
                        scorer=fuzz.token_sort_ratio
                    )
                    if mejor and mejor[1] >= 85.0:
                        est_encontrado = nombres_map[mejor[0]]
                        return est_encontrado.id_estudiante, "B"
                    mejor_candidato = mejor[0] if mejor else None
                    score_fuzzy = round(mejor[1], 2) if mejor else None
                else:
                    mejor_candidato = None
                    score_fuzzy = None
            except Exception as e:
                logger.warning(f"Error en fuzzy matching estudiante: {e}")
                mejor_candidato = None
                score_fuzzy = None

            # Si score < 85 -> Estado C: Se deriva a staging
            stg = StagingEntidadNoResuelta(
                id_documento=doc_id,
                tipo_entidad="ESTUDIANTE",
                texto_original=nombre.strip(),
                ci_temporal=ci,
                mejor_candidato=mejor_candidato,
                score_fuzzy=score_fuzzy,
                fk_estado="C",
                nivel_confianza=confianza_ia,
                resuelto=False
            )
            self.db.add(stg)
            self.db.flush()
            return None, "C"

        return None, "C"

    # ── 2. Resolución DimDocente ─────────────────────────────────────────────
    def resolver_o_crear_docente(
        self,
        nombre_docente: Optional[str],
        doc_id: Optional[int] = None
    ) -> Optional[int]:
        if not nombre_docente or not nombre_docente.strip():
            return None

        clean_nombre = nombre_docente.strip()
        doc = self.db.query(DimDocente).filter(
            func.lower(DimDocente.nombre_completo) == clean_nombre.lower()
        ).first()
        if doc:
            return doc.id_docente

        # Búsqueda difusa
        try:
            from rapidfuzz import fuzz, process
            docentes = self.db.query(DimDocente).all()
            if docentes:
                doc_map = {d.nombre_completo: d for d in docentes if d.nombre_completo}
                mejor = process.extractOne(
                    clean_nombre,
                    list(doc_map.keys()),
                    scorer=fuzz.token_sort_ratio
                )
                if mejor and mejor[1] >= 85.0:
                    return doc_map[mejor[0]].id_docente
        except Exception:
            pass

        # Crear nuevo docente si tiene formato verosímil
        nuevo_doc = DimDocente(nombre_completo=clean_nombre)
        self.db.add(nuevo_doc)
        self.db.flush()
        return nuevo_doc.id_docente

    # ── 3. Resolución DimModulo ──────────────────────────────────────────────
    def resolver_o_crear_modulo(
        self,
        nombre_modulo: Optional[str],
        pos_code: Optional[str] = None,
        doc_id: Optional[int] = None
    ) -> Optional[int]:
        if not nombre_modulo and not pos_code:
            return None

        # Intento 1: Por pos_code
        if pos_code:
            mod = self.db.query(DimModulo).filter(DimModulo.pos_code == pos_code.strip()).first()
            if mod:
                return mod.id_modulo

        # Intento 2: Por nombre
        if nombre_modulo:
            clean_name = nombre_modulo.strip()
            mod = self.db.query(DimModulo).filter(
                func.lower(DimModulo.nombre_modulo) == clean_name.lower()
            ).first()
            if mod:
                return mod.id_modulo

            try:
                from rapidfuzz import fuzz, process
                modulos = self.db.query(DimModulo).all()
                if modulos:
                    mod_map = {m.nombre_modulo: m for m in modulos if m.nombre_modulo}
                    mejor = process.extractOne(
                        clean_name,
                        list(mod_map.keys()),
                        scorer=fuzz.token_sort_ratio
                    )
                    if mejor and mejor[1] >= 80.0:
                        return mod_map[mejor[0]].id_modulo
            except Exception:
                pass

            # Crear nuevo módulo
            nuevo_mod = DimModulo(
                nombre_modulo=clean_name,
                nombre_institucion="GiraGroup",
                pos_code=pos_code or "MOD-GEN"
            )
            self.db.add(nuevo_mod)
            self.db.flush()
            return nuevo_mod.id_modulo

        return None

    # ── 4. Resolución DimTiempo ──────────────────────────────────────────────
    def resolver_o_crear_tiempo(self, fecha_val: Optional[Any] = None) -> int:
        if isinstance(fecha_val, str):
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    fecha_obj = datetime.strptime(fecha_val.strip(), fmt).date()
                    break
                except ValueError:
                    continue
            else:
                fecha_obj = date.today()
        elif isinstance(fecha_val, datetime):
            fecha_obj = fecha_val.date()
        elif isinstance(fecha_val, date):
            fecha_obj = fecha_val
        else:
            fecha_obj = date.today()

        id_tiempo = int(fecha_obj.strftime("%Y%m%d"))
        t_existente = self.db.query(DimTiempo).filter(DimTiempo.id_tiempo == id_tiempo).first()
        if t_existente:
            return t_existente.id_tiempo

        gestion = fecha_obj.year
        mes = fecha_obj.month
        trimestre = (mes - 1) // 3 + 1
        semestre = 1 if mes <= 6 else 2
        dia_semana = fecha_obj.isoweekday()  # 1=Lunes, 7=Domingo
        semana_iso = fecha_obj.isocalendar()[1]
        dia_mes = fecha_obj.day
        nombre_mes = MESES_ES.get(mes, "Desconocido")
        nombre_dia = DIAS_ES.get(dia_semana, "Desconocido")
        es_fin_semana = dia_semana in (6, 7)
        periodo_mes = fecha_obj.strftime("%Y-%m")

        nuevo_tiempo = DimTiempo(
            id_tiempo=id_tiempo,
            fecha=fecha_obj,
            gestion=gestion,
            semestre=semestre,
            trimestre=trimestre,
            mes=mes,
            nombre_mes=nombre_mes,
            semana_iso=semana_iso,
            dia_mes=dia_mes,
            dia_semana=dia_semana,
            nombre_dia=nombre_dia,
            es_fin_semana=es_fin_semana,
            periodo_mes=periodo_mes
        )
        self.db.add(nuevo_tiempo)
        self.db.flush()
        return id_tiempo

    # ── 5. Carga de un Registro Procesado Individual ─────────────────────────
    def cargar_registro(self, registro: Dict[str, Any], id_usuario: Optional[int] = None) -> Dict[str, Any]:
        """
        Procesa una fila estructurada del pipeline y la persiste en el DW.
        Retorna diccionario con el resultado de la carga y el estado FK.
        """
        categoria = (registro.get("categoria") or "academico").lower()
        doc_id = registro.get("doc_id")
        resoluciones = registro.get("resoluciones") or {}
        calidad = registro.get("calidad") or {}

        # 1. Extraer identificadores y nombres
        est_dict = resoluciones.get("estudiante") or {}
        fk_res = est_dict.get("fk_resolucion") or {}
        ci_est = fk_res.get("ci")
        nombre_est = fk_res.get("nombre_resuelto") or est_dict.get("valor_extraido")

        doc_info = resoluciones.get("docente") or {}
        nombre_docente = doc_info.get("valor_extraido") if isinstance(doc_info, dict) else None

        mod_info = resoluciones.get("modulo") or {}
        prog_info = resoluciones.get("programa") or {}
        nombre_modulo = None
        pos_code = None
        if isinstance(mod_info, dict):
            nombre_modulo = mod_info.get("valor_extraido")
        if not nombre_modulo and isinstance(prog_info, dict):
            nombre_modulo = prog_info.get("valor_extraido")
            meta = prog_info.get("metadata") or {}
            pos_code = meta.get("pos_canonico")

        confianza_ia = resoluciones.get("nivel_confianza_ia", 0.85)
        requiere_rev = calidad.get("requiere_revision", False)

        # Buscar fecha en entidades NER si existe
        fecha_encontrada = None
        for ent in registro.get("entidades_ner") or []:
            if ent.get("tipo") == "FECHA":
                fecha_encontrada = ent.get("valor")
                break

        # 2. Resolver FKs
        id_est, fk_estado_est = self.resolver_o_crear_estudiante(
            ci=ci_est,
            nombre=nombre_est,
            doc_id=doc_id,
            confianza_ia=confianza_ia
        )
        id_tiempo = self.resolver_o_crear_tiempo(fecha_encontrada)

        # 3. Persistir Hecho Académico o Financiero
        if categoria == "financiero":
            monto_deuda = resoluciones.get("monto_deuda")
            cuotas_impagas = resoluciones.get("cuotas_impagas")
            estado_cartera = resoluciones.get("estado_cartera") or "Vigente"

            # Si no hay estudiante resuelto, no insertamos en fact_situacion_financiera (queda en staging)
            if not id_est:
                return {
                    "tipo": "financiero",
                    "status": "staged",
                    "fk_estado": "C",
                    "motivo": "Estudiante no resuelto derivado a stg_entidad_no_resuelta"
                }

            # Upsert sobre constraint uq_fact_situacion_financiera_estudiante_tiempo
            existente = self.db.query(FactSituacionFinanciera).filter(
                FactSituacionFinanciera.id_estudiante == id_est,
                FactSituacionFinanciera.id_tiempo == id_tiempo
            ).first()

            if existente:
                existente.monto_deuda = monto_deuda
                existente.cuotas_impagas = cuotas_impagas
                existente.estado_cartera = estado_cartera
                existente.nivel_confianza_ia = confianza_ia
                existente.requiere_revision = requiere_rev or (fk_estado_est == "C")
                existente.fk_estado = fk_estado_est
                if doc_id:
                    existente.id_documento = doc_id
                fact_id = existente.id_hecho_fin
            else:
                nuevo_hecho = FactSituacionFinanciera(
                    id_estudiante=id_est,
                    id_tiempo=id_tiempo,
                    id_documento=doc_id,
                    monto_deuda=monto_deuda,
                    cuotas_impagas=cuotas_impagas,
                    estado_cartera=estado_cartera,
                    tipo_alerta="MORA_CRITICA" if cuotas_impagas and cuotas_impagas >= 2 else "NORMAL",
                    nivel_confianza_ia=confianza_ia,
                    requiere_revision=requiere_rev or (fk_estado_est == "C"),
                    fk_estado=fk_estado_est
                )
                self.db.add(nuevo_hecho)
                self.db.flush()
                fact_id = nuevo_hecho.id_hecho_fin

            return {
                "tipo": "financiero",
                "status": "loaded",
                "id_hecho": fact_id,
                "id_estudiante": id_est,
                "fk_estado": fk_estado_est
            }

        else:
            # Académico
            id_doc = self.resolver_o_crear_docente(nombre_docente, doc_id=doc_id)
            id_mod = self.resolver_o_crear_modulo(nombre_modulo, pos_code=pos_code, doc_id=doc_id)

            if not id_est:
                return {
                    "tipo": "academico",
                    "status": "staged",
                    "fk_estado": "C",
                    "motivo": "Estudiante no resuelto derivado a stg_entidad_no_resuelta"
                }

            # Si no hay módulo, crear uno por defecto para no romper integridad
            if not id_mod:
                id_mod = self.resolver_o_crear_modulo("Módulo General", pos_code="MOD-GEN")

            nota = resoluciones.get("nota_final")
            asistencia = resoluciones.get("asistencia_pct")
            incumplimiento = resoluciones.get("incumplimiento_actividades_pct") or 0.00
            estado_aca = "Aprobado" if (nota and float(nota) >= 51.0) else "Reprobado" if nota else "En Curso"

            # Upsert sobre constraint uq_fact_rendimiento_estudiante_modulo
            existente = self.db.query(FactRendimientoAcademico).filter(
                FactRendimientoAcademico.id_estudiante == id_est,
                FactRendimientoAcademico.id_modulo == id_mod
            ).first()

            if existente:
                existente.nota_final = nota
                existente.asistencia_pct = asistencia
                existente.incumplimiento_actividades_pct = incumplimiento
                existente.nivel_confianza_ia = confianza_ia
                existente.requiere_revision = requiere_rev or (fk_estado_est == "C")
                existente.fk_estado = fk_estado_est
                existente.estado_academico = estado_aca
                if id_doc:
                    existente.id_docente = id_doc
                if doc_id:
                    existente.id_documento = doc_id
                fact_id = existente.id_hecho_aca
            else:
                nuevo_hecho = FactRendimientoAcademico(
                    id_estudiante=id_est,
                    id_docente=id_doc,
                    id_modulo=id_mod,
                    id_tiempo=id_tiempo,
                    id_documento=doc_id,
                    id_usuario_carga=id_usuario,
                    nota_final=nota,
                    asistencia_pct=asistencia,
                    incumplimiento_actividades_pct=incumplimiento,
                    nivel_confianza_ia=confianza_ia,
                    requiere_revision=requiere_rev or (fk_estado_est == "C"),
                    fk_estado=fk_estado_est,
                    estado_academico=estado_aca
                )
                self.db.add(nuevo_hecho)
                self.db.flush()
                fact_id = nuevo_hecho.id_hecho_aca

            return {
                "tipo": "academico",
                "status": "loaded",
                "id_hecho": fact_id,
                "id_estudiante": id_est,
                "id_modulo": id_mod,
                "id_docente": id_doc,
                "fk_estado": fk_estado_est
            }

    # ── 6. Carga Masiva desde Archivo JSONL ──────────────────────────────────
    def cargar_desde_jsonl(self, ruta_jsonl: Path, id_usuario: Optional[int] = None) -> Dict[str, Any]:
        """Lee un archivo JSONL de salida de Sprint 3 y carga todos los registros al DW."""
        if not ruta_jsonl.exists():
            return {"error": f"Archivo {ruta_jsonl} no encontrado", "cargados": 0}

        cargados = 0
        staged = 0
        errores = 0

        with open(ruta_jsonl, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    reg = json.loads(line_str)
                    res = self.cargar_registro(reg, id_usuario=id_usuario)
                    if res.get("status") == "loaded":
                        cargados += 1
                    elif res.get("status") == "staged":
                        staged += 1
                except Exception as e:
                    logger.error(f"Error cargando línea {line_no} de {ruta_jsonl}: {e}")
                    errores += 1

        self.db.commit()
        return {
            "archivo": str(ruta_jsonl),
            "total_cargados": cargados,
            "derivados_a_staging": staged,
            "errores": errores
        }
