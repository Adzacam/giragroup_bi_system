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


def _fuzzy_best_match(query_str: str, candidates: list):
    """Búsqueda difusa compatible con rapidfuzz o difflib como fallback."""
    if not query_str or not candidates:
        return None, None
    try:
        from rapidfuzz import fuzz, process
        mejor = process.extractOne(query_str, candidates, scorer=fuzz.token_sort_ratio)
        if mejor:
            return mejor[0], round(mejor[1], 2)
    except Exception:
        pass
    from difflib import SequenceMatcher
    q_lower = query_str.lower()
    best_cand = None
    best_ratio = 0.0
    for cand in candidates:
        ratio = SequenceMatcher(None, q_lower, str(cand).lower()).ratio() * 100.0
        if ratio > best_ratio:
            best_ratio = ratio
            best_cand = cand
    if best_cand:
        return best_cand, round(best_ratio, 2)
    return None, None


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
        confianza_ia: Optional[float] = None,
        institucion: Optional[str] = "GiraGroup",
        programa: Optional[str] = None
    ) -> Tuple[Optional[int], str]:
        """
        Retorna (id_estudiante, fk_estado).
        fk_estado: 'A' (directo CI), 'B' (fuzzy rescatado/TEMP), 'C' (derivado a HITL/staging).
        Alineado por institución y detección de homonimia por programa.
        """
        if not ci and not nombre:
            return None, "C"

        es_sintetico = not ci or ci.startswith("TEMP-CI-") or "TEMP" in (ci or "")

        # Caso 1: CI válido directo
        if ci and not es_sintetico:
            ci_clean = ci.strip()
            est = self.db.query(DimEstudiante).filter(
                (DimEstudiante.ci == ci_clean) | (DimEstudiante.codigo_estudiante == ci_clean),
                DimEstudiante.deprecado == False
            ).first()
            if est:
                # Regla CI_NOMBRE_DISCORDANTE: si el nombre no coincide léxicamente (WRatio < 70) -> HITL
                if nombre and est.nombre_completo:
                    match_ratio = _fuzzy_best_match(nombre.strip(), [est.nombre_completo])[1] or 0.0
                    if match_ratio < 70.0:
                        stg = StagingEntidadNoResuelta(
                            id_documento=doc_id,
                            tipo_entidad="ESTUDIANTE",
                            texto_original=f"CI: {ci_clean} | Nombre: {nombre.strip()} (Discordante con: {est.nombre_completo})",
                            ci_temporal=ci_clean,
                            mejor_candidato=est.nombre_completo,
                            score_fuzzy=match_ratio,
                            fk_estado="C",
                            nivel_confianza=confianza_ia,
                            resuelto=False
                        )
                        self.db.add(stg)
                        self.db.flush()
                        return None, "C"

                if not est.ci:
                    est.ci = ci_clean
                    self.db.flush()
                return est.id_estudiante, "A"

            # Si no existe pero hay CI y nombre, se crea el estudiante
            nuevo_est = DimEstudiante(
                ci=ci_clean,
                codigo_estudiante=ci_clean,
                nombre_completo=(nombre or f"Estudiante {ci_clean}").strip(),
                deprecado=False
            )
            self.db.add(nuevo_est)
            self.db.flush()
            return nuevo_est.id_estudiante, "A"

        # Caso 2: CI sintético o ausente -> Búsqueda con RapidFuzz para homonimia
        if nombre:
            nombre_clean = nombre.strip()
            estudiantes = self.db.query(DimEstudiante).filter(
                DimEstudiante.deprecado == False
            ).all()
            candidatos_validos = []
            if estudiantes:
                for e in estudiantes:
                    if e.nombre_completo:
                        ratio = _fuzzy_best_match(nombre_clean, [e.nombre_completo])[1] or 0.0
                        if ratio >= 90.0:
                            candidatos_validos.append((e, ratio))

            # 2a. Si hay 2 o más candidatos >= 90% -> Conflicto de Homonimia detectado -> Derivación forzada a HITL
            if len(candidatos_validos) >= 2:
                stg = StagingEntidadNoResuelta(
                    id_documento=doc_id,
                    tipo_entidad="ESTUDIANTE",
                    texto_original=nombre_clean,
                    ci_temporal=ci,
                    mejor_candidato=candidatos_validos[0][0].nombre_completo,
                    score_fuzzy=candidatos_validos[0][1],
                    fk_estado="C",
                    nivel_confianza=confianza_ia,
                    resuelto=False
                )
                self.db.add(stg)
                self.db.flush()
                return None, "C"

            # 2b. Si hay un único candidato >= 90%:
            if len(candidatos_validos) == 1:
                est_encontrado = candidatos_validos[0][0]
                # Homonimia por programa: si el alumno encontrado ya tiene hechos en un programa DIFERENTE sin CI -> HITL
                if programa:
                    hecho_otro_prog = self.db.query(FactRendimientoAcademico).join(
                        DimModulo, FactRendimientoAcademico.id_modulo == DimModulo.id_modulo
                    ).filter(
                        FactRendimientoAcademico.id_estudiante == est_encontrado.id_estudiante,
                        DimModulo.programa.isnot(None),
                        DimModulo.programa != programa
                    ).first()
                    if hecho_otro_prog:
                        stg = StagingEntidadNoResuelta(
                            id_documento=doc_id,
                            tipo_entidad="ESTUDIANTE",
                            texto_original=f"{nombre_clean} (Programa entrante: {programa})",
                            ci_temporal=ci,
                            mejor_candidato=est_encontrado.nombre_completo,
                            score_fuzzy=candidatos_validos[0][1],
                            fk_estado="C",
                            nivel_confianza=confianza_ia,
                            resuelto=False
                        )
                        self.db.add(stg)
                        self.db.flush()
                        return None, "C"

                return est_encontrado.id_estudiante, "B"

            # 2c. Ningún candidato >= 90% -> Alta directa creando id_temporal determinista por institución
            import hashlib
            inst_clean = (institucion or "GiraGroup").strip().lower()
            norm_str = "".join(nombre_clean.lower().split()) + "_" + "".join(inst_clean.split())
            hash_temp = f"TEMP-{hashlib.sha256(norm_str.encode()).hexdigest()[:12]}"
            nuevo_est = DimEstudiante(
                nombre_completo=nombre_clean,
                id_temporal=hash_temp,
                codigo_estudiante=hash_temp,
                deprecado=False
            )
            self.db.add(nuevo_est)
            self.db.flush()
            return nuevo_est.id_estudiante, "B"

        return None, "C"

    # ── 1b. Fusión Atómica de Estudiantes (Deduplicación & Unicidad) ─────────
    def fusionar_estudiantes(
        self,
        id_origen: int,
        id_destino: int,
        usuario_id: Optional[int] = None,
        resolver_conflicto: str = "CONSERVAR_RECIENTE"
    ) -> Dict[str, Any]:
        """
        Fusiona un estudiante duplicado/deprecado (id_origen) hacia un registro canónico (id_destino)
        en una sola transacción atómica auditada.
        Resuelve conflictos de unicidad en facts conservando el hecho más reciente o derivando a HITL.
        """
        if id_origen == id_destino:
            return {"status": "error", "message": "No se puede fusionar un estudiante consigo mismo"}

        est_origen = self.db.query(DimEstudiante).filter(DimEstudiante.id_estudiante == id_origen).first()
        est_destino = self.db.query(DimEstudiante).filter(DimEstudiante.id_estudiante == id_destino).first()
        if not est_origen or not est_destino:
            return {"status": "error", "message": "Estudiante origen o destino no encontrado"}

        # 1. Traspasar hechos de rendimiento académico resolviendo conflictos de unicidad
        hechos_origen = self.db.query(FactRendimientoAcademico).filter(
            FactRendimientoAcademico.id_estudiante == id_origen
        ).all()
        conflictos_resueltos = 0
        for hecho in hechos_origen:
            colision = self.db.query(FactRendimientoAcademico).filter(
                FactRendimientoAcademico.id_estudiante == id_destino,
                FactRendimientoAcademico.id_modulo == hecho.id_modulo,
                FactRendimientoAcademico.id_tiempo == hecho.id_tiempo
            ).first()
            if colision:
                conflictos_resueltos += 1
                if (hecho.nivel_confianza_ia or 0) > (colision.nivel_confianza_ia or 0):
                    colision.nota_final = hecho.nota_final
                    colision.nivel_confianza_ia = hecho.nivel_confianza_ia
                self.db.delete(hecho)
            else:
                hecho.id_estudiante = id_destino

        # 2. Traspasar hechos financieros
        hechos_fin = self.db.query(FactSituacionFinanciera).filter(
            FactSituacionFinanciera.id_estudiante == id_origen
        ).all()
        for h_fin in hechos_fin:
            h_fin.id_estudiante = id_destino

        # 3. Marcar origen como deprecado y fusionado_en destino
        est_origen.deprecado = True
        est_origen.fusionado_en = id_destino

        # Si origen tenía CI y destino no, migrar CI
        if est_origen.ci and not est_destino.ci:
            est_destino.ci = est_origen.ci
            if not est_destino.codigo_estudiante or est_destino.codigo_estudiante.startswith("TEMP-"):
                est_destino.codigo_estudiante = est_origen.ci

        self.db.flush()
        return {
            "status": "success",
            "id_origen": id_origen,
            "id_destino": id_destino,
            "conflictos_resueltos": conflictos_resueltos,
            "hechos_movidos": len(hechos_origen) + len(hechos_fin)
        }

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
        docentes = self.db.query(DimDocente).all()
        if docentes:
            doc_map = {d.nombre_completo: d for d in docentes if d.nombre_completo}
            mejor_cand, score_fuzz = _fuzzy_best_match(clean_nombre, list(doc_map.keys()))
            if mejor_cand and score_fuzz is not None and score_fuzz >= 85.0:
                return doc_map[mejor_cand].id_docente

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

            modulos = self.db.query(DimModulo).all()
            if modulos:
                mod_map = {m.nombre_modulo: m for m in modulos if m.nombre_modulo}
                mejor_cand, score_fuzz = _fuzzy_best_match(clean_name, list(mod_map.keys()))
                if mejor_cand and score_fuzz is not None and score_fuzz >= 80.0:
                    return mod_map[mejor_cand].id_modulo

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
        gestion = 2026
        semestre = 1
        mes_num = 5
        mes_nombre = "Mayo"
        id_tiempo = 20260501

        if isinstance(fecha_val, (date, datetime)):
            gestion = fecha_val.year
            semestre = 1 if fecha_val.month <= 6 else 2
            mes_num = fecha_val.month
            mes_nombre = MESES_ES.get(fecha_val.month, "Mayo")
            dia = getattr(fecha_val, "day", 1)
            id_tiempo = int(f"{gestion}{fecha_val.month:02d}{dia:02d}")
        elif isinstance(fecha_val, str) and fecha_val.strip():
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
                try:
                    f_obj = datetime.strptime(fecha_val.strip(), fmt).date()
                    gestion = f_obj.year
                    semestre = 1 if f_obj.month <= 6 else 2
                    mes_num = f_obj.month
                    mes_nombre = MESES_ES.get(f_obj.month, "Mayo")
                    id_tiempo = int(f"{gestion}{f_obj.month:02d}{f_obj.day:02d}")
                    break
                except ValueError:
                    continue

        t_existente = self.db.query(DimTiempo).filter(DimTiempo.id_tiempo == id_tiempo).first()
        if t_existente:
            return t_existente.id_tiempo

        periodo_mes = f"{gestion}-{mes_num:02d}"
        nuevo_tiempo = DimTiempo(
            id_tiempo=id_tiempo,
            gestion=gestion,
            semestre=semestre,
            mes=mes_num,
            nombre_mes=mes_nombre,
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

            id_mod_fin = self.resolver_o_crear_modulo(nombre_modulo, pos_code=pos_code, doc_id=doc_id)
            if existente:
                existente.monto_deuda = monto_deuda
                existente.cuotas_impagas = cuotas_impagas
                existente.estado_cartera = estado_cartera
                existente.nivel_confianza_ia = confianza_ia
                existente.requiere_revision = requiere_rev or (fk_estado_est == "C")
                existente.fk_estado = fk_estado_est
                if id_mod_fin:
                    existente.id_modulo = id_mod_fin
                if doc_id:
                    existente.id_documento = doc_id
                fact_id = existente.id_hecho_fin
            else:
                nuevo_hecho = FactSituacionFinanciera(
                    id_estudiante=id_est,
                    id_modulo=id_mod_fin,
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
