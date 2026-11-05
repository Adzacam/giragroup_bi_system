"""
backend/services/dw_loader.py
------------------------------
Servicio de Carga al Data Warehouse con Resolución Dimensional de Llaves Foráneas.
Resuelve FKs (Estudiante, Docente, Módulo, Tiempo) contra las dimensiones del DW,
persiste los hechos (académicos y financieros) ruteando determinísticamente por
dim_origen_documental.tipo_fuente, y deriva entidades no resueltas (Estado C)
a la tabla stg_entidad_no_resuelta para gobernanza y revisión asistida.
"""

import json
import logging
import re
import unicodedata
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
from models.dim_categoria_financiera import DimCategoriaFinanciera
from models.fact_rendimiento import FactRendimientoAcademico
from models.fact_financiero import FactSituacionFinanciera
from models.fact_costo_programa import FactCostoPrograma
from models.bridge_modulo_docente import BridgeModuloDocente
from models.fact_techo_convenio import FactTechoConvenio
from models.log_inconsistencia import LogInconsistencia
from models.staging_entidad import StagingEntidadNoResuelta
from models.catalogos import CatInstitucion
from pipeline.config import NOTA_APROBACION
try:
    from models.fact_evaluacion import FactEvaluacionDocente
    from models.fact_rentabilidad import FactRentabilidad
    from models.fact_marketing import FactMarketing
except ImportError:
    try:
        from backend.models.fact_evaluacion import FactEvaluacionDocente
        from backend.models.fact_rentabilidad import FactRentabilidad
        from backend.models.fact_marketing import FactMarketing
    except ImportError:
        FactEvaluacionDocente = None
        FactRentabilidad = None
        FactMarketing = None

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


def normalizar_ci(ci_raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae (ci_numero, ci_complemento) a partir de un CI crudo.
    Ejemplo: '4892019 LP' -> ('4892019', 'LP'), '4892019' -> ('4892019', None).
    """
    if not ci_raw:
        return None, None
    clean = ci_raw.strip().upper()
    if clean.startswith("TEMP") or "TEMP-CI" in clean:
        return None, None
    parts = re.split(r"[\s\-]+", clean)
    digits = re.sub(r"[^0-9]", "", parts[0]) if parts else ""
    if not digits:
        m = re.search(r"\d{5,12}", clean)
        digits = m.group(0) if m else ""
    if not digits:
        return None, None
    comp = " ".join(parts[1:]).strip()[:10] if len(parts) > 1 else None
    return digits, comp or None


def normalizar_nota_base_100(nota_val: Optional[Any], tipo_escala: Optional[str]) -> Optional[float]:
    """
    Normaliza una calificación a escala base 0-100 según tipo_escala:
    - DECIMAL_10 -> x10
    - VIGESIMAL_20 -> x5
    - CENTESIMAL_100 (o None) -> x1
    """
    if nota_val is None or nota_val == "":
        return None
    try:
        n = float(nota_val)
    except (ValueError, TypeError):
        return None
    escala = (tipo_escala or "CENTESIMAL_100").upper().strip()
    if escala == "DECIMAL_10" and n <= 10.0:
        return round(n * 10.0, 2)
    if escala == "VIGESIMAL_20" and n <= 20.0:
        return round(n * 5.0, 2)
    return round(n, 2)


def calcular_tipo_alerta_financiera(cuotas_impagas: Optional[int]) -> str:
    """
    Regla determinista de alerta de mora (#9):
    - cuotas_impagas >= 2 -> 'RIESGO_CARTERA'
    - cuotas_impagas == 1 -> 'MORA_TEMPRANA'
    - cuotas_impagas == 0 -> 'NORMAL'
    """
    c = int(cuotas_impagas or 0)
    if c >= 2:
        return "RIESGO_CARTERA"
    if c == 1:
        return "MORA_TEMPRANA"
    return "NORMAL"


# Títulos y grados que acompañan al nombre del docente ('Fabian Mendivil Mgr.', 'Lic. Ana Pérez'): no son parte
# del nombre; sin quitarlos, la misma persona queda como dos docentes
_TITULOS_GRADO = {
    "MGR": "Magister", "MG": "Magister", "MSC": "Magister", "MAGISTER": "Magister", "MBA": "Magister",
    "DR": "Doctor", "DRA": "Doctor", "PHD": "Doctor", "DOCTOR": "Doctor",
    "LIC": "Licenciado", "LICDA": "Licenciado", "LICENCIADO": "Licenciado", "LICENCIADA": "Licenciado",
    "ING": "Ingeniero", "INGENIERO": "Ingeniero", "INGENIERA": "Ingeniero",
    "ARQ": "Arquitecto", "ABG": "Abogado", "ABOG": "Abogado",
}


def separar_grado(nombre: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """'Fabian Mendivil Mgr.' -> ('Fabian Mendivil', 'Magister'). Quita títulos al inicio o al final."""
    if not nombre:
        return nombre, None
    tokens = nombre.replace(",", " ").split()
    grado = None

    def _clave(t: str) -> str:
        return t.replace(".", "").upper()

    while tokens and _clave(tokens[0]) in _TITULOS_GRADO:
        titulo = _TITULOS_GRADO[_clave(tokens.pop(0))]  # pop siempre, aunque ya haya grado
        grado = grado or titulo
    while tokens and _clave(tokens[-1]) in _TITULOS_GRADO:
        titulo = _TITULOS_GRADO[_clave(tokens.pop())]
        grado = grado or titulo
    return (" ".join(tokens) or None), grado


def _tokens_nombre(nombre: str) -> set:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", nombre or "") if unicodedata.category(c) != "Mn")
    return set(sin_tildes.upper().split())


def _es_nombre_incompleto(guardado: str, entrante: str) -> bool:
    """True si el nombre guardado es un subconjunto estricto del entrante ('ROBERTO JOSE' ⊂ 'ROBERTO JOSE VARGAS')."""
    t_guardado, t_entrante = _tokens_nombre(guardado), _tokens_nombre(entrante)
    return bool(t_guardado) and t_guardado < t_entrante


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

    def _resolver_id_institucion(self, institucion: Optional[str]) -> Optional[int]:
        if not institucion:
            return None
        try:
            cat = self.db.query(CatInstitucion).filter(
                func.lower(CatInstitucion.nombre_institucion) == institucion.strip().lower()
            ).first()
            if cat:
                return cat.id_institucion
        except Exception:
            pass
        return None

    # ── 1. Resolución DimEstudiante ───────────────────────────────────────────
    def resolver_o_crear_estudiante(
        self,
        ci: Optional[str],
        nombre: Optional[str],
        doc_id: Optional[int] = None,
        confianza_ia: Optional[float] = None,
        institucion: Optional[str] = "GiraGroup Posgrado",
        programa: Optional[str] = None,
        forzar_resolucion_humana: bool = False,
    ) -> Tuple[Optional[int], str]:
        """
        Retorna (id_estudiante, fk_estado).
        fk_estado: 'A' (directo CI), 'B' (fuzzy rescatado/TEMP), 'C' (derivado a HITL/staging).
        Alineado por ci_numero normalizado, institución y detección de homonimia por programa.
        """
        if not ci and not nombre:
            return None, "C"

        es_sintetico = not ci or ci.startswith("TEMP-CI-") or "TEMP" in (ci or "")
        ci_num, ci_comp = normalizar_ci(ci) if not es_sintetico else (None, None)

        if ci and not es_sintetico:
            ci_clean = ci.strip()
            if ci_num:
                ci_cond = (
                    (DimEstudiante.ci_numero == ci_num)
                    | (DimEstudiante.ci == ci_clean)
                    | (DimEstudiante.codigo_estudiante == ci_clean)
                    | (DimEstudiante.codigo_estudiante == ci_num)
                )
            else:
                ci_cond = (
                    (DimEstudiante.ci == ci_clean)
                    | (DimEstudiante.codigo_estudiante == ci_clean)
                )

            est = self.db.query(DimEstudiante).filter(
                DimEstudiante.deprecado == False,
                ci_cond
            ).first()

            if est:
                # Mismo CI con nombre guardado incompleto (solo nombres de pila): misma persona, se completa
                if nombre and est.nombre_completo and _es_nombre_incompleto(est.nombre_completo, nombre):
                    est.nombre_completo = nombre.strip()
                # Regla CI_NOMBRE_DISCORDANTE: si el nombre no coincide léxicamente (WRatio < 70) -> HITL
                elif not forzar_resolucion_humana and nombre and est.nombre_completo:
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
                            motivo="CI_NOMBRE_DISCORDANTE",
                            nivel_confianza=confianza_ia,
                            resuelto=False
                        )
                        self.db.add(stg)
                        self.db.flush()
                        return None, "C"

                if not est.ci:
                    est.ci = ci_clean
                if ci_num and not est.ci_numero:
                    est.ci_numero = ci_num
                if ci_comp and not est.ci_complemento:
                    est.ci_complemento = ci_comp
                if programa and not est.programa_origen:
                    est.programa_origen = programa
                self.db.flush()
                return est.id_estudiante, "A"

            # Si no existe pero hay CI y nombre, se crea el estudiante
            id_inst = self._resolver_id_institucion(institucion)
            nuevo_est = DimEstudiante(
                ci=ci_clean,
                ci_numero=ci_num,
                ci_complemento=ci_comp,
                codigo_estudiante=ci_num or ci_clean,
                nombre_completo=(nombre or f"Estudiante {ci_clean}").strip(),
                identidad_verificada=True,
                id_institucion=id_inst,
                programa_origen=programa,
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
            if len(candidatos_validos) >= 2 and not forzar_resolucion_humana:
                stg = StagingEntidadNoResuelta(
                    id_documento=doc_id,
                    tipo_entidad="ESTUDIANTE",
                    texto_original=nombre_clean,
                    ci_temporal=ci,
                    mejor_candidato=candidatos_validos[0][0].nombre_completo,
                    score_fuzzy=candidatos_validos[0][1],
                    fk_estado="C",
                    motivo="HOMONIMIA",
                    nivel_confianza=confianza_ia,
                    resuelto=False
                )
                self.db.add(stg)
                self.db.flush()
                return None, "C"

            # 2b. Si hay al menos un candidato >= 90%:
            if len(candidatos_validos) >= 1:
                est_encontrado = candidatos_validos[0][0]
                if programa and not forzar_resolucion_humana:
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
                            motivo="HOMONIMIA",
                            nivel_confianza=confianza_ia,
                            resuelto=False
                        )
                        self.db.add(stg)
                        self.db.flush()
                        return None, "C"

                return est_encontrado.id_estudiante, "B"

            # 2c. Ningún candidato >= 90%: Si la confianza IA es baja (< 0.85), derivar a HITL / Estado C
            # Solo < 0.60 va a staging: la banda [0.60, 0.85) se carga como hecho con requiere_revision
            if confianza_ia is not None and confianza_ia < 0.60 and not forzar_resolucion_humana:
                stg = StagingEntidadNoResuelta(
                    id_documento=doc_id,
                    tipo_entidad="ESTUDIANTE",
                    texto_original=nombre_clean,
                    ci_temporal=ci,
                    mejor_candidato=None,
                    score_fuzzy=None,
                    fk_estado="C",
                    motivo="BAJA_CONFIANZA_IA",
                    nivel_confianza=confianza_ia,
                    resuelto=False
                )
                self.db.add(stg)
                self.db.flush()
                return None, "C"

            # De lo contrario (alta confianza >= 0.85), crear id_temporal determinista por institución
            import hashlib
            inst_clean = (institucion or "GiraGroup Posgrado").strip().lower()
            norm_str = "".join(nombre_clean.lower().split()) + "_" + "".join(inst_clean.split())
            hash_temp = f"TEMP-{hashlib.sha256(norm_str.encode()).hexdigest()[:12]}"
            id_inst = self._resolver_id_institucion(institucion)
            nuevo_est = DimEstudiante(
                nombre_completo=nombre_clean,
                id_temporal=hash_temp,
                codigo_estudiante=hash_temp,
                id_institucion=id_inst,
                programa_origen=programa,
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
        Resuelve conflictos de unicidad en facts conservando el hecho más reciente o de mayor confianza.
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
                FactRendimientoAcademico.id_modulo == hecho.id_modulo
            ).first()
            if colision:
                conflictos_resueltos += 1
                if (hecho.nivel_confianza_ia or 0) > (colision.nivel_confianza_ia or 0):
                    colision.nota_final = hecho.nota_final
                    colision.nivel_confianza_ia = hecho.nivel_confianza_ia
                self.db.delete(hecho)
            else:
                hecho.id_estudiante = id_destino

        # 2. Traspasar hechos financieros resolviendo colisiones sobre (id_estudiante, COALESCE(id_modulo, 0), id_tiempo)
        hechos_fin = self.db.query(FactSituacionFinanciera).filter(
            FactSituacionFinanciera.id_estudiante == id_origen
        ).all()
        for h_fin in hechos_fin:
            colision_fin = self.db.query(FactSituacionFinanciera).filter(
                FactSituacionFinanciera.id_estudiante == id_destino,
                func.coalesce(FactSituacionFinanciera.id_modulo, 0) == (h_fin.id_modulo or 0),
                FactSituacionFinanciera.id_tiempo == h_fin.id_tiempo
            ).first()
            if colision_fin:
                conflictos_resueltos += 1
                if (h_fin.nivel_confianza_ia or 0) > (colision_fin.nivel_confianza_ia or 0):
                    colision_fin.monto_deuda = h_fin.monto_deuda
                    colision_fin.monto_pagado = h_fin.monto_pagado
                    colision_fin.cuotas_impagas = h_fin.cuotas_impagas
                    colision_fin.tipo_alerta = h_fin.tipo_alerta
                self.db.delete(h_fin)
            else:
                h_fin.id_estudiante = id_destino

        # 3. Marcar origen como deprecado y fusionado_en destino (liberar ci_numero de origen para índice único)
        ci_origen = est_origen.ci
        ci_num_origen = est_origen.ci_numero
        ci_comp_origen = est_origen.ci_complemento

        est_origen.deprecado = True
        est_origen.fusionado_en = id_destino
        self.db.flush()

        # Si origen tenía CI y destino no, migrar CI
        if ci_origen and not est_destino.ci:
            est_destino.ci = ci_origen
            est_destino.ci_numero = ci_num_origen
            est_destino.ci_complemento = ci_comp_origen
            if not est_destino.codigo_estudiante or est_destino.codigo_estudiante.startswith("TEMP-"):
                est_destino.codigo_estudiante = ci_num_origen or ci_origen

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

        clean_nombre, _ = separar_grado(nombre_docente.strip())
        if not clean_nombre:
            return None
        doc = self.db.query(DimDocente).filter(
            func.lower(DimDocente.nombre_completo) == clean_nombre.lower()
        ).first()
        if doc:
            return doc.id_docente

        docentes = self.db.query(DimDocente).all()
        if docentes:
            doc_map = {d.nombre_completo: d for d in docentes if d.nombre_completo}
            mejor_cand, score_fuzz = _fuzzy_best_match(clean_nombre, list(doc_map.keys()))
            if mejor_cand and score_fuzz is not None and score_fuzz >= 85.0:
                return doc_map[mejor_cand].id_docente

        nuevo_doc = DimDocente(nombre_completo=clean_nombre)
        self.db.add(nuevo_doc)
        self.db.flush()
        return nuevo_doc.id_docente

    # ── 3. Resolución DimModulo ──────────────────────────────────────────────
    def resolver_o_crear_modulo(
        self,
        nombre_modulo: Optional[str],
        pos_code: Optional[str] = None,
        doc_id: Optional[int] = None,
        institucion: Optional[str] = "GiraGroup Posgrado",
        programa: Optional[str] = None,
    ) -> Optional[int]:
        if not nombre_modulo and not pos_code:
            return None

        if pos_code:
            mod = self.db.query(DimModulo).filter(DimModulo.pos_code == pos_code.strip()).first()
            if mod:
                return mod.id_modulo
            if nombre_modulo:
                # El código POS es autoritativo: sin él, el fuzzy fusionaba 'POS-X · Módulo 1' con 'Módulo 2'
                nuevo_mod = DimModulo(
                    nombre_modulo=nombre_modulo.strip(),
                    nombre_institucion=institucion or "GiraGroup Posgrado",
                    id_institucion=self._resolver_id_institucion(institucion),
                    pos_code=pos_code.strip(),
                    programa=programa,
                )
                self.db.add(nuevo_mod)
                self.db.flush()
                return nuevo_mod.id_modulo

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

            id_inst = self._resolver_id_institucion(institucion)
            nuevo_mod = DimModulo(
                nombre_modulo=clean_name,
                nombre_institucion=institucion or "GiraGroup Posgrado",
                id_institucion=id_inst,
                pos_code=pos_code or "MOD-GEN"
            )
            self.db.add(nuevo_mod)
            self.db.flush()
            return nuevo_mod.id_modulo

        return None

    def _docente_unico_del_modulo(self, id_modulo: Optional[int]) -> Optional[int]:
        """
        Docente de un módulo: el de bridge_modulo_docente (hoja MODULOS) si hay uno solo, o el único TITULAR si hay
        varios; si no, el de los hechos académicos ya cargados. None si no se sabe o es ambiguo.
        """
        if not id_modulo:
            return None
        asignados = self.db.query(BridgeModuloDocente.id_docente, BridgeModuloDocente.tipo_docente).filter(
            BridgeModuloDocente.id_modulo == id_modulo
        ).all()
        if len(asignados) == 1:
            return asignados[0][0]
        titulares = [d for d, t in asignados if (t or "").upper().startswith("TITULAR")]
        if len(titulares) == 1:
            return titulares[0]
        if asignados:
            return None  # varios docentes sin un titular claro: no se adivina
        ids = [
            r[0] for r in self.db.query(FactRendimientoAcademico.id_docente)
            .filter(FactRendimientoAcademico.id_modulo == id_modulo, FactRendimientoAcademico.id_docente.isnot(None))
            .distinct().limit(2).all()
        ]
        return ids[0] if len(ids) == 1 else None

    def _cargar_asignacion_docente(self, resoluciones, nombre_docente, pos_code, doc_id, institucion) -> Dict[str, Any]:
        """
        Registra qué docente dictó el módulo POS-XXXX-MNN (idempotente) y completa el docente de las notas y
        evaluaciones de ese módulo que se cargaron antes sin él.
        """
        if not pos_code or not nombre_docente:
            return {"tipo": "asignacion_docente", "status": "staged", "motivo": "Asignación sin POS o sin docente"}
        nombre_real = resoluciones.get("nombre_modulo_real")
        id_mod = self.resolver_o_crear_modulo(
            nombre_real or f"{pos_code}", pos_code=pos_code, doc_id=doc_id, institucion=institucion,
            programa=pos_code.rsplit("-M", 1)[0],
        )
        mod = self.db.query(DimModulo).get(id_mod)
        if mod and nombre_real and "· Módulo" in (mod.nombre_modulo or ""):
            mod.nombre_modulo = nombre_real[:200]  # el acta lo creó con un nombre provisional
        id_doc = self.resolver_o_crear_docente(nombre_docente, doc_id=doc_id)
        _, grado = separar_grado(nombre_docente)

        asig = self.db.query(BridgeModuloDocente).filter_by(id_modulo=id_mod, id_docente=id_doc).first()
        if asig is None:
            asig = BridgeModuloDocente(id_modulo=id_mod, id_docente=id_doc)
            self.db.add(asig)
        asig.id_documento = doc_id
        asig.tipo_docente = resoluciones.get("tipo_docente") or asig.tipo_docente
        asig.grado_academico = grado or asig.grado_academico
        for campo in ("horas_modulo", "pago_docente", "fecha_inicio", "fecha_fin"):
            if resoluciones.get(campo) is not None:
                setattr(asig, campo, resoluciones[campo])
        self.db.flush()

        # Notas y evaluaciones del módulo que llegaron antes que esta hoja: ahora se sabe su docente
        completadas = {"notas": 0, "evaluaciones": 0}
        id_doc_modulo = self._docente_unico_del_modulo(id_mod)
        if id_doc_modulo:
            completadas["notas"] = self.db.query(FactRendimientoAcademico).filter(
                FactRendimientoAcademico.id_modulo == id_mod, FactRendimientoAcademico.id_docente.is_(None)
            ).update({FactRendimientoAcademico.id_docente: id_doc_modulo}, synchronize_session=False)
            if FactEvaluacionDocente is not None:
                completadas["evaluaciones"] = self.db.query(FactEvaluacionDocente).filter(
                    FactEvaluacionDocente.id_modulo == id_mod,
                    FactEvaluacionDocente.id_docente.is_(None),
                    FactEvaluacionDocente.tipo_pregunta == "DOCENTE",
                ).update({FactEvaluacionDocente.id_docente: id_doc_modulo}, synchronize_session=False)
        return {
            "tipo": "asignacion_docente",
            "status": "loaded",
            "id_modulo": id_mod,
            "id_docente": id_doc,
            "pos_code": pos_code,
            **{f"{k}_completadas": v for k, v in completadas.items()},
        }

    def _cargar_techo_convenio(self, resoluciones, nombre_modulo, nombre_programa, pos_code, doc_id, institucion,
                               id_tiempo, calidad) -> Dict[str, Any]:
        """Fila de convenio de un programa con una institución; idempotente por clave_convenio."""
        from services.instituciones_convenio import canonizar_institucion

        if not pos_code or not resoluciones.get("institucion_cliente"):
            return {"tipo": "techo_convenio", "status": "staged", "motivo": "Convenio sin POS o sin institución"}
        id_mod = self.resolver_o_crear_modulo(
            nombre_modulo or pos_code, pos_code=pos_code, doc_id=doc_id, institucion=institucion,
            programa=nombre_programa,
        )
        existentes = [n for (n,) in self.db.query(FactTechoConvenio.institucion).distinct().all()]
        canon, id_conv, score = canonizar_institucion(resoluciones["institucion_cliente"], existentes)
        fecha_ini = resoluciones.get("fecha_inicio")
        # Fila repetida tal cual -> mismo hecho; otro pago del mismo convenio (otro monto) -> otro hecho
        import hashlib
        clave = hashlib.sha1("|".join(str(x) for x in (
            pos_code, canon.upper(), fecha_ini, resoluciones.get("monto_convenio"), resoluciones.get("n_inscritos"),
        )).encode("utf-8")).hexdigest()

        hecho = self.db.query(FactTechoConvenio).filter(FactTechoConvenio.clave_convenio == clave).first()
        if hecho is None:
            hecho = FactTechoConvenio(clave_convenio=clave, id_modulo=id_mod, institucion=canon, fecha_inicio=fecha_ini)
            self.db.add(hecho)
        hecho.id_convenio_catalogo = id_conv
        hecho.id_tiempo = id_tiempo
        hecho.id_documento = doc_id
        for campo in ("monto_convenio", "n_inscritos", "gestion", "fecha_fin"):
            setattr(hecho, campo, resoluciones.get(campo))
        motivos = [m for m in (resoluciones.get("motivo_techo"),) if m]
        if score < 100.0:
            motivos.append(f"INSTITUCION_FUZZY: '{resoluciones['institucion_cliente']}' -> '{canon}' ({score:.0f})")
        hecho.requiere_revision = bool(resoluciones.get("motivo_techo")) or bool(calidad.get("requiere_revision"))
        hecho.motivo_revision = ("; ".join(motivos) or None) and "; ".join(motivos)[:300]
        self.db.flush()
        return {
            "tipo": "techo_convenio",
            "status": "loaded",
            "id_hecho": hecho.id_hecho_techo,
            "institucion": canon,
            "monto_convenio": resoluciones.get("monto_convenio"),
        }

    # ── 4. Resolución DimTiempo ──────────────────────────────────────────────
    def resolver_o_crear_tiempo(self, fecha_val: Optional[Any] = None) -> Optional[int]:
        """
        id_tiempo (AAAAMMDD) de la fecha de la fila. Sin fecha válida retorna None: el hecho queda sin
        tiempo y con requiere_revision (antes se asignaba 20260501 a todo lo que no traía fecha).
        """
        from services.extraccion_por_encabezado import parsear_fecha

        f = parsear_fecha(fecha_val)
        if f is None:
            return None
        id_tiempo = int(f"{f.year}{f.month:02d}{f.day:02d}")

        t_existente = self.db.query(DimTiempo).filter(DimTiempo.id_tiempo == id_tiempo).first()
        if t_existente:
            return t_existente.id_tiempo

        iso = f.isocalendar()
        self.db.add(DimTiempo(
            id_tiempo=id_tiempo,
            fecha=f,
            gestion=f.year,
            semestre=1 if f.month <= 6 else 2,
            trimestre=(f.month - 1) // 3 + 1,
            mes=f.month,
            nombre_mes=MESES_ES[f.month],
            semana_iso=iso[1],
            dia_mes=f.day,
            dia_semana=iso[2],
            nombre_dia=DIAS_ES[iso[2]],
            es_fin_semana=iso[2] >= 6,
            periodo_mes=f"{f.year}-{f.month:02d}",
        ))
        self.db.flush()
        return id_tiempo

    # ── 5. Carga de un Registro Procesado Individual ─────────────────────────
    def cargar_registro(self, registro: Dict[str, Any], id_usuario: Optional[int] = None) -> Dict[str, Any]:
        """
        Procesa una fila estructurada del pipeline y la persiste en el DW.
        El ruteo es determinista según dim_origen_documental.tipo_fuente (#8):
        - COBRANZA -> fact_situacion_financiera
        - ACTA / MOODLE -> fact_rendimiento_academico
        - ADMISION -> dim_estudiante
        """
        doc_id = registro.get("doc_id")
        origen_doc = None
        if doc_id:
            origen_doc = self.db.query(DimOrigenDocumental).filter(
                DimOrigenDocumental.id_documento == doc_id
            ).first()

        tipo_fuente = (
            registro.get("tipo_fuente")
            or (origen_doc.tipo_fuente if origen_doc else None)
            or ""
        ).upper().strip()

        tipo_escala = (
            registro.get("tipo_escala")
            or (origen_doc.tipo_escala if origen_doc else None)
        )
        institucion = (
            registro.get("institucion")
            or (origen_doc.institucion if origen_doc else None)
            or "GiraGroup Posgrado"
        )

        # Determinar categoría determinísticamente desde tipo_fuente si existe
        if tipo_fuente == "COBRANZA":
            categoria = "financiero"
        elif tipo_fuente in ("ACTA", "MOODLE", "PLANIFICACION"):
            categoria = "academico"
        elif tipo_fuente == "EVALUACION_DOCENTE":
            categoria = "evaluacion_docente"
        elif tipo_fuente in ("EGRESOS", "TECHOS", "RENTABILIDAD"):
            categoria = "rentabilidad"
        elif tipo_fuente in ("MARKETING", "ADMISION"):
            categoria = "marketing" if tipo_fuente == "MARKETING" else "admision"
        else:
            categoria = (registro.get("categoria") or "academico").lower()

        resoluciones = registro.get("resoluciones") or {}
        calidad = registro.get("calidad") or {}

        # 1. Extraer identificadores y nombres
        est_dict = resoluciones.get("estudiante") or {}
        fk_res = est_dict.get("fk_resolucion") or {}
        ci_est = fk_res.get("ci") or resoluciones.get("ci")
        nombre_est = fk_res.get("nombre_resuelto") or est_dict.get("valor_extraido") or resoluciones.get("nombre_estudiante")

        doc_info = resoluciones.get("docente") or {}
        nombre_docente = doc_info.get("valor_extraido") if isinstance(doc_info, dict) else (doc_info if isinstance(doc_info, str) else None)

        mod_info = resoluciones.get("modulo") or {}
        prog_info = resoluciones.get("programa") or {}
        nombre_modulo = None
        nombre_programa = None
        pos_code = None
        if isinstance(mod_info, dict):
            nombre_modulo = mod_info.get("valor_extraido")
        elif isinstance(mod_info, str):
            nombre_modulo = mod_info

        if isinstance(prog_info, dict):
            nombre_programa = prog_info.get("valor_extraido")
            meta = prog_info.get("metadata") or {}
            pos_code = meta.get("pos_canonico")
        elif isinstance(prog_info, str):
            nombre_programa = prog_info

        if not nombre_modulo and nombre_programa:
            nombre_modulo = nombre_programa

        confianza_ia = resoluciones.get("nivel_confianza_ia", 0.85)
        requiere_rev = calidad.get("requiere_revision", False)
        es_resuelto_humano = bool(
            calidad.get("resuelto_por_humano")
            or registro.get("forzar_resolucion_humana")
        )

        # Buscar fecha en entidades NER si existe
        fecha_encontrada = resoluciones.get("fecha")
        if not fecha_encontrada:
            for ent in registro.get("entidades_ner") or []:
                if ent.get("tipo") == "FECHA":
                    fecha_encontrada = ent.get("valor")
                    break

        # 2. Resolver FKs
        id_est, fk_estado_est = self.resolver_o_crear_estudiante(
            ci=ci_est,
            nombre=nombre_est,
            doc_id=doc_id,
            confianza_ia=confianza_ia,
            institucion=institucion,
            programa=nombre_programa or nombre_modulo,
            forzar_resolucion_humana=es_resuelto_humano,
        )
        id_tiempo = self.resolver_o_crear_tiempo(fecha_encontrada)
        if id_tiempo is None:
            requiere_rev = True  # hecho sin fecha: no se le asigna un período inventado

        # 3a. Ruteo ADMISION -> DimEstudiante
        if categoria == "admision":
            if not id_est:
                return {
                    "tipo": "admision",
                    "status": "staged",
                    "fk_estado": "C",
                    "motivo": "Postulante no resuelto derivado a Cola de Revisión Humana"
                }
            return {
                "tipo": "admision",
                "status": "loaded",
                "id_estudiante": id_est,
                "fk_estado": fk_estado_est
            }

        # 3b. Ruteo COBRANZA -> FactSituacionFinanciera (#8, #9)
        if categoria == "financiero":
            monto_deuda = float(resoluciones.get("monto_deuda") or 0.0)
            monto_pagado = float(resoluciones.get("monto_pagado") or 0.0)
            concepto = resoluciones.get("concepto") or resoluciones.get("concepto_financiero")
            cuotas_impagas = int(resoluciones.get("cuotas_impagas") or 0)
            estado_cartera = resoluciones.get("estado_cartera") or ("En Mora" if cuotas_impagas > 0 else "Vigente")
            tipo_alerta_fin = calcular_tipo_alerta_financiera(cuotas_impagas)

            if not id_est:
                return {
                    "tipo": "financiero",
                    "status": "staged",
                    "fk_estado": "C",
                    "motivo": "Estudiante no resuelto derivado a Cola de Revisión Humana"
                }

            id_mod_fin = self.resolver_o_crear_modulo(
                nombre_modulo, pos_code=pos_code, doc_id=doc_id, institucion=institucion
            ) if nombre_modulo else None

            # Upsert sobre índice único (id_estudiante, COALESCE(id_modulo, 0), id_tiempo)
            existente = self.db.query(FactSituacionFinanciera).filter(
                FactSituacionFinanciera.id_estudiante == id_est,
                func.coalesce(FactSituacionFinanciera.id_modulo, 0) == (id_mod_fin or 0),
                FactSituacionFinanciera.id_tiempo == id_tiempo
            ).first()

            if existente:
                existente.monto_deuda = monto_deuda
                existente.monto_pagado = monto_pagado
                existente.concepto = concepto or existente.concepto
                existente.cuotas_impagas = cuotas_impagas
                existente.estado_cartera = estado_cartera
                existente.tipo_alerta = tipo_alerta_fin
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
                    concepto=concepto,
                    monto_deuda=monto_deuda,
                    monto_pagado=monto_pagado,
                    cuotas_impagas=cuotas_impagas,
                    estado_cartera=estado_cartera,
                    tipo_alerta=tipo_alerta_fin,
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
                "tipo_alerta": tipo_alerta_fin,
                "fk_estado": fk_estado_est
            }

        # 3c. Ruteo EVALUACION_DOCENTE -> FactEvaluacionDocente (una fila por respuesta)
        if categoria == "evaluacion_docente" and FactEvaluacionDocente:
            puntuacion_raw = resoluciones.get("puntuacion")
            if puntuacion_raw is None:
                puntuacion_raw = resoluciones.get("rating")
            puntuacion = float(puntuacion_raw) if puntuacion_raw is not None else None
            escala_max = resoluciones.get("escala_max") or (5 if puntuacion is not None else None)
            comentario = resoluciones.get("comentario")
            comentario_str = str(comentario)[:1000] if comentario else None
            if puntuacion is None and not comentario_str:
                # Sin puntaje ni comentario no hay respuesta que guardar: nunca un 5.0 de relleno
                return {"tipo": "evaluacion_docente", "status": "skipped", "motivo": "RESPUESTA_VACIA"}
            pregunta = str(resoluciones.get("pregunta_bloque") or resoluciones.get("criterio") or "Evaluación de desempeño docente")[:500]
            tipo_preg = resoluciones.get("tipo_pregunta") or "DOCENTE"

            id_mod_eval = self.resolver_o_crear_modulo(
                nombre_modulo, pos_code=pos_code, doc_id=doc_id, institucion=institucion
            ) or self.resolver_o_crear_modulo("Módulo General", pos_code="MOD-GEN", institucion=institucion)
            id_doc_eval = None
            if tipo_preg == "DOCENTE":  # plataforma, atención y NPS no son del docente
                id_doc_eval = self.resolver_o_crear_docente(nombre_docente, doc_id=doc_id) \
                    or self._docente_unico_del_modulo(id_mod_eval)
            if resoluciones.get("anonima") or not (ci_est or nombre_est):
                id_est = None  # respuesta anónima: sin estudiante, no se crea uno ficticio

            clave = resoluciones.get("clave_respuesta")
            existente_eval = self.db.query(FactEvaluacionDocente).filter(
                FactEvaluacionDocente.clave_respuesta == clave
            ).first() if clave else None
            valores = dict(
                id_docente=id_doc_eval,
                id_modulo=id_mod_eval,
                id_estudiante=id_est,
                id_tiempo=id_tiempo,
                pregunta_bloque=pregunta,
                tipo_pregunta=tipo_preg,
                puntuacion=puntuacion,
                escala_max=escala_max,
                comentario=comentario_str,
            )
            if existente_eval:  # mismo archivo subido otra vez: se actualiza, no se duplica
                for k, v in valores.items():
                    setattr(existente_eval, k, v)
                hecho_eval = existente_eval
            else:
                hecho_eval = FactEvaluacionDocente(clave_respuesta=clave, **valores)
                self.db.add(hecho_eval)
            self.db.flush()
            return {
                "tipo": "evaluacion_docente",
                "status": "loaded",
                "id_hecho": hecho_eval.id_hecho_eval,
                "id_docente": id_doc_eval,
                "puntuacion": puntuacion,
                "escala_max": escala_max,
            }

        # 3d''. Ruteo CONVENIO / TECHO -> FactTechoConvenio (institución cliente canónica)
        # Por contenido de la fila, no por cómo se clasificó el documento (BD Techos puede llegar como MARKETING)
        if resoluciones.get("techo_convenio"):
            return self._cargar_techo_convenio(resoluciones, nombre_modulo, nombre_programa, pos_code, doc_id,
                                               institucion, id_tiempo, calidad)

        # 3d'. Ruteo COSTO POR PROGRAMA -> FactCostoPrograma (egreso/ingreso/rentabilidad de un POS)
        if resoluciones.get("costo_programa"):
            if not pos_code:
                return {"tipo": "costo_programa", "status": "staged", "motivo": "Fila de costos sin POS"}
            id_mod_costo = self.resolver_o_crear_modulo(
                nombre_modulo or pos_code, pos_code=pos_code, doc_id=doc_id, institucion=institucion,
                programa=nombre_programa,
            )
            motivo_costo = resoluciones.get("motivo_costo")
            valores = {
                k: (float(resoluciones[k]) if resoluciones.get(k) is not None else None)
                for k in ("egreso_anterior", "egreso_real", "ingreso", "rentabilidad")
            }
            hecho_costo = self.db.query(FactCostoPrograma).filter(FactCostoPrograma.id_modulo == id_mod_costo).first()
            if hecho_costo is None:
                hecho_costo = FactCostoPrograma(id_modulo=id_mod_costo)
                self.db.add(hecho_costo)
            for k, v in valores.items():  # recargar el libro actualiza, no duplica
                setattr(hecho_costo, k, v)
            hecho_costo.id_documento = doc_id
            # Los costos por POS no tienen fecha: no se marca revisión por falta de id_tiempo
            hecho_costo.requiere_revision = bool(motivo_costo) or bool(calidad.get("requiere_revision"))
            hecho_costo.motivo_revision = (motivo_costo or "")[:300] or None
            self.db.flush()
            return {
                "tipo": "costo_programa",
                "status": "loaded",
                "id_hecho": hecho_costo.id_hecho_costo,
                "pos_code": pos_code,
                **valores,
            }

        # 3d. Ruteo RENTABILIDAD -> FactRentabilidad
        if categoria == "rentabilidad" and FactRentabilidad:
            id_mod_rent = self.resolver_o_crear_modulo(
                nombre_modulo, pos_code=pos_code, doc_id=doc_id, institucion=institucion
            ) or self.resolver_o_crear_modulo("Administración General", pos_code="ADM-GEN", institucion=institucion)

            id_cat = None
            cat_nom = resoluciones.get("categoria_financiera") or "Operativo"
            cat_db = self.db.query(DimCategoriaFinanciera).filter(
                func.lower(DimCategoriaFinanciera.nombre_categoria) == cat_nom.lower()
            ).first()
            if not cat_db and resoluciones.get("categoria_financiera"):
                # Categoría de la fila (PROGRAMAS, TECHOS_CERRADOS): se crea en vez de caer en otra ajena
                cat_db = DimCategoriaFinanciera(nombre_categoria=cat_nom, tipo="INGRESO")
                self.db.add(cat_db)
                self.db.flush()
            if cat_db:
                id_cat = cat_db.id_categoria
            else:
                cat_first = self.db.query(DimCategoriaFinanciera).first()
                id_cat = cat_first.id_categoria if cat_first else None

            def _monto(*claves):
                return next((float(resoluciones[k]) for k in claves if resoluciones.get(k) is not None), None)

            m_ejec = _monto("monto_ejecutado", "gasto", "egreso")
            m_meta = _monto("monto_meta", "presupuesto", "techo")

            existente_rent = self.db.query(FactRentabilidad).filter(
                FactRentabilidad.id_categoria == id_cat,
                FactRentabilidad.id_tiempo == id_tiempo
            ).first()

            if existente_rent:
                # Misma categoría y mes: el valor nuevo reemplaza al anterior (recargar el libro no duplica montos).
                # Si otra fuente ya había cargado otra cifra para ese mes, queda registrado para revisión.
                for campo, nuevo in (("monto_ejecutado", m_ejec), ("monto_meta", m_meta)):
                    previo = getattr(existente_rent, campo)
                    if nuevo == 0 and previo not in (None, 0):
                        # Un 0 de otra fuente es un mes aún no ejecutado, no una cifra: no pisa el monto real
                        if campo == "monto_ejecutado":
                            m_ejec = None
                        else:
                            m_meta = None
                        nuevo = None
                    if nuevo is not None and previo not in (None, 0) and abs(float(previo) - nuevo) > max(1.0, 0.01 * abs(float(previo))):
                        self.db.add(LogInconsistencia(
                            id_documento=doc_id,
                            campo_afectado=f"fact_rentabilidad.{campo}",
                            valor_recibido=str(nuevo),
                            valor_esperado=str(previo),
                            tipo_regla="CONFLICTO_FUENTES",
                            severidad="MEDIA",
                            estado_resolucion="PENDIENTE",
                            descripcion=f"{cat_nom} id_tiempo={id_tiempo}: la fuente nueva reemplaza {previo} por {nuevo}",
                        ))
                if m_ejec is not None:
                    existente_rent.monto_ejecutado = m_ejec
                if m_meta is not None:
                    existente_rent.monto_meta = m_meta
                self.db.flush()
                return {
                    "tipo": "rentabilidad",
                    "status": "loaded",
                    "id_hecho": existente_rent.id_hecho_rent,
                    "monto_ejecutado": existente_rent.monto_ejecutado,
                    "monto_meta": existente_rent.monto_meta
                }
            else:
                nuevo_rent = FactRentabilidad(
                    id_modulo=id_mod_rent,
                    id_tiempo=id_tiempo,
                    id_categoria=id_cat,
                    monto_ejecutado=m_ejec,  # mes solo con meta (2026): ejecutado vacío, no 0 inventado
                    monto_meta=m_meta
                )
                self.db.add(nuevo_rent)
                self.db.flush()
                return {
                    "tipo": "rentabilidad",
                    "status": "loaded",
                    "id_hecho": nuevo_rent.id_hecho_rent,
                    "monto_ejecutado": m_ejec,
                    "monto_meta": m_meta
                }

        # 3e. Ruteo MARKETING -> FactMarketing
        if categoria == "marketing" and FactMarketing:
            id_mod_mkt = self.resolver_o_crear_modulo(
                nombre_modulo, pos_code=pos_code, doc_id=doc_id, institucion=institucion
            ) or self.resolver_o_crear_modulo("Difusión Institucional", pos_code="MKT-GEN", institucion=institucion)

            reservas = int(resoluciones.get("reservas") or 0)
            inscritos = int(resoluciones.get("inscritos") or (1 if id_est else 0))
            # Todo inscrito proviene de un lead: evita conversiones > 100 % por fila
            leads = max(int(resoluciones.get("leads") or 1), inscritos)
            costo_prog = float(resoluciones.get("costo_programa") or 0.0)

            existente_mkt = self.db.query(FactMarketing).filter(
                FactMarketing.id_modulo == id_mod_mkt,
                FactMarketing.id_tiempo == id_tiempo
            ).first()

            if existente_mkt:
                existente_mkt.leads = (existente_mkt.leads or 0) + leads
                existente_mkt.reservas = (existente_mkt.reservas or 0) + reservas
                existente_mkt.inscritos = (existente_mkt.inscritos or 0) + inscritos
                self.db.flush()
                return {
                    "tipo": "marketing",
                    "status": "loaded",
                    "id_hecho": existente_mkt.id_hecho_mkt,
                    "leads": existente_mkt.leads,
                    "inscritos": existente_mkt.inscritos
                }
            else:
                nuevo_mkt = FactMarketing(
                    id_modulo=id_mod_mkt,
                    id_tiempo=id_tiempo,
                    leads=leads,
                    reservas=reservas,
                    inscritos=inscritos,
                    costo_programa=costo_prog
                )
                self.db.add(nuevo_mkt)
                self.db.flush()
                return {
                    "tipo": "marketing",
                    "status": "loaded",
                    "id_hecho": nuevo_mkt.id_hecho_mkt,
                    "leads": leads,
                    "inscritos": inscritos
                }

        # 3f'. Asignación docente-módulo (hoja MODULOS) -> dim_modulo + bridge_modulo_docente
        if resoluciones.get("asignacion_docente"):
            return self._cargar_asignacion_docente(resoluciones, nombre_docente, pos_code, doc_id, institucion)

        # 3f. Ruteo ACTA / MOODLE -> FactRendimientoAcademico
        id_doc = self.resolver_o_crear_docente(nombre_docente, doc_id=doc_id)
        id_mod = self.resolver_o_crear_modulo(
            nombre_modulo, pos_code=pos_code, doc_id=doc_id, institucion=institucion, programa=nombre_programa
        )

        if not id_est:
            return {
                "tipo": "academico",
                "status": "staged",
                "fk_estado": "C",
                "motivo": "Estudiante no resuelto derivado a Cola de Revisión Humana"
            }

        if not id_mod:
            id_mod = self.resolver_o_crear_modulo("Módulo General", pos_code="MOD-GEN", institucion=institucion)
            requiere_rev = True  # sin módulo identificado
        if not id_doc:
            id_doc = self._docente_unico_del_modulo(id_mod)  # el acta no nombra al docente; la hoja MODULOS sí

        nota_raw = resoluciones.get("nota_final")
        if resoluciones.get("nota_ya_normalizada"):
            nota = float(nota_raw) if nota_raw is not None else None
        else:
            nota = normalizar_nota_base_100(nota_raw, tipo_escala)
        if nota is not None and not (0.0 <= float(nota) <= 100.0):
            nota = None  # no es una nota en base 100 (desbordaba numeric(5,2) y abortaba toda la consolidación)
        if nota is None:
            requiere_rev = True  # fila sin nota: queda null, nunca un valor de relleno

        def _pct_valido(v):
            try:
                return float(v) if v is not None and 0.0 <= float(v) <= 100.0 else None
            except (TypeError, ValueError):
                return None

        asistencia = _pct_valido(resoluciones.get("asistencia_pct"))
        incumplimiento = _pct_valido(resoluciones.get("incumplimiento_actividades_pct")) or 0.00
        # El estado del acta (Participó, Deserción, En curso…) manda; solo sin estado en la fuente se deduce de la nota
        estado_aca = resoluciones.get("estado_academico") or (
            "Aprobado" if (nota is not None and float(nota) >= NOTA_APROBACION) else "Reprobado" if nota is not None else "En curso"
        )
        estado_tut = resoluciones.get("estado_tutoria")
        estado_arca = resoluciones.get("estado_arca")
        if resoluciones.get("estado_motivo"):
            requiere_rev = True  # estado fuera de catálogo o combinación no admitida por CRITERIOS
        tipo_alerta_aca = (
            "RIESGO_CRITICO" if (nota is not None and float(nota) < 51.0)
            else "RIESGO_ACADEMICO" if (nota is not None and float(nota) <= 70.0)
            else "NORMAL"
        )

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
            existente.estado_tutoria = estado_tut
            existente.estado_arca = estado_arca
            existente.tipo_alerta = tipo_alerta_aca
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
                estado_academico=estado_aca,
                estado_tutoria=estado_tut,
                estado_arca=estado_arca,
                tipo_alerta=tipo_alerta_aca
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
            "nota_normalizada": nota,
            "tipo_alerta": tipo_alerta_aca,
            "estado_academico": estado_aca,
            "estado_motivo": resoluciones.get("estado_motivo"),
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
