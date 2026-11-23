"""
backend/services/validacion_relaciones.py
----------------------------------------
BA-L6: Validación de relaciones antes de insertar en el DW.
Las reglas (a)-(f) y sus parámetros se leen desde `cat_regla_relacion` en `giragroup_catalog_db`
(configurables en catálogo, no en el código).
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

logger = logging.getLogger("validacion_relaciones")

MOTIVO_RELACION_INCOHERENTE = "RELACION_INCOHERENTE"


def _norm(s: Optional[str]) -> str:
    if not s:
        return ""
    s = "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.upper().strip())


def _extraer_pos(val: Any) -> Optional[str]:
    if not val:
        return None
    m = re.search(r"\bPOS[-\s]?(\d{3,5})\b", str(val).upper())
    return f"POS-{m.group(1)}" if m else None


def _extraer_anio(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.year
    if isinstance(val, int):
        return val if 100 <= val <= 9999 else None
    s = str(val).strip()
    m = re.match(r"^(\d{4})[-/]", s) or re.search(r"[-/](\d{4})$", s)
    if m:
        return int(m.group(1))
    if re.fullmatch(r"\d{4}", s):
        return int(s)
    return None


@dataclass
class ReglaRelacion:
    codigo_regla: str
    nombre_regla: str
    descripcion: str
    activa: bool = True
    severidad: str = "ALTA"
    parametros: Dict[str, Any] = field(default_factory=dict)
    acciones_sugeridas: List[str] = field(default_factory=list)


@dataclass
class FalloRelacion:
    regla: str
    nombre_regla: str
    valor: str
    detalle: str
    acciones: List[str] = field(default_factory=list)

    def a_dict(self) -> Dict[str, Any]:
        return {
            "regla": self.regla,
            "nombre_regla": self.nombre_regla,
            "valor": self.valor,
            "detalle": self.detalle,
            "acciones": list(self.acciones),
        }


@dataclass
class ContextoRelaciones:
    reglas: Dict[str, ReglaRelacion] = field(default_factory=dict)
    pos_validos: Set[str] = field(default_factory=set)
    modulos_por_pos: Dict[str, Set[int]] = field(default_factory=dict)
    periodos_por_pos: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    bridge_docente_pos: Set[Tuple[str, str]] = field(default_factory=set)
    bridge_docente_modulo: Set[Tuple[str, str, int]] = field(default_factory=set)
    inscripciones_est_pos: Set[Tuple[str, str]] = field(default_factory=set)


def cargar_reglas_desde_catalogo(catalog_url: Optional[str] = None) -> Dict[str, ReglaRelacion]:
    """Lee las reglas activas de `cat_regla_relacion` en `giragroup_catalog_db`."""
    url = catalog_url or os.getenv("CATALOG_DATABASE_URL")
    if not url:
        return {}
    try:
        from sqlalchemy import create_engine, text
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as conn:
            rows = conn.execute(text("""
                SELECT codigo_regla, nombre_regla, descripcion, activa, severidad,
                       parametros_json, acciones_sugeridas
                  FROM public.cat_regla_relacion
                 WHERE activa = TRUE
            """)).fetchall()
        reglas = {}
        for r in rows:
            reglas[r.codigo_regla] = ReglaRelacion(
                codigo_regla=r.codigo_regla,
                nombre_regla=r.nombre_regla,
                descripcion=r.descripcion,
                activa=bool(r.activa),
                severidad=r.severidad or "ALTA",
                parametros=dict(r.parametros_json or {}),
                acciones_sugeridas=list(r.acciones_sugeridas or []),
            )
        return reglas
    except Exception as exc:
        logger.warning("No se pudo leer cat_regla_relacion (%s); validación de relaciones omitida.", exc)
        return {}


def cargar_contexto_relaciones(dw_db=None, catalog_url: Optional[str] = None) -> ContextoRelaciones:
    """Construye el contexto en memoria una sola vez por pasada de consolidación (sin N+1)."""
    ctx = ContextoRelaciones()
    ctx.reglas = cargar_reglas_desde_catalogo(catalog_url)
    if not ctx.reglas:
        return ctx

    url = catalog_url or os.getenv("CATALOG_DATABASE_URL")
    if url:
        try:
            from sqlalchemy import create_engine, text
            eng = create_engine(url, pool_pre_ping=True)
            with eng.connect() as conn:
                for (pos,) in conn.execute(text("SELECT pos_code FROM public.cat_programa WHERE pos_code IS NOT NULL")):
                    p = _extraer_pos(pos) or _norm(pos)
                    if p:
                        ctx.pos_validos.add(p)
                for pos, num in conn.execute(text("""
                    SELECT p.pos_code, m.nro_modulo
                      FROM public.cat_modulo m
                      JOIN public.cat_programa p ON p.id_programa = m.id_programa
                     WHERE p.pos_code IS NOT NULL AND m.nro_modulo IS NOT NULL
                """)):
                    p = _extraer_pos(pos) or _norm(pos)
                    if p:
                        ctx.modulos_por_pos.setdefault(p, set()).add(int(num))
        except Exception as exc:
            logger.warning("No se pudo cargar cat_programa/cat_modulo para relaciones: %s", exc)

    if dw_db is not None:
        try:
            from sqlalchemy import text
            for (pos, nom_mod) in dw_db.execute(text("SELECT pos_code, nombre_modulo FROM public.dim_modulo WHERE pos_code IS NOT NULL")):
                p = _extraer_pos(pos) or _norm(pos)
                if p:
                    ctx.pos_validos.add(p)
                    m_num = re.search(r"\bM[ÓO]DULO\s*(\d{1,2})\b", str(nom_mod or "").upper())
                    if m_num:
                        ctx.modulos_por_pos.setdefault(p, set()).add(int(m_num.group(1)))
            for (doc_nom, pos, nom_mod) in dw_db.execute(text("""
                SELECT DISTINCT d.nombre_completo, m.pos_code, m.nombre_modulo
                  FROM public.bridge_modulo_docente b
                  JOIN public.dim_docente d ON d.id_docente = b.id_docente
                  JOIN public.dim_modulo m ON m.id_modulo = b.id_modulo
                 WHERE d.nombre_completo IS NOT NULL AND m.pos_code IS NOT NULL
            """)):
                p = _extraer_pos(pos) or _norm(pos)
                if p and doc_nom:
                    ctx.bridge_docente_pos.add((_norm(doc_nom), p))
                    m_num = re.search(r"\bM[ÓO]DULO\s*(\d{1,2})\b", str(nom_mod or "").upper())
                    if m_num:
                        ctx.bridge_docente_modulo.add((_norm(doc_nom), p, int(m_num.group(1))))
            for (pos, ini, fin) in dw_db.execute(text("""
                SELECT pos_code_fuente,
                       MIN(EXTRACT(YEAR FROM fecha_inicio_plan))::int AS ini,
                       MAX(EXTRACT(YEAR FROM fecha_fin_plan))::int AS fin
                  FROM public.fact_planificacion_programa
                 WHERE pos_code_fuente IS NOT NULL
                   AND fecha_inicio_plan IS NOT NULL
                   AND fecha_fin_plan IS NOT NULL
                 GROUP BY pos_code_fuente
            """)):
                p = _extraer_pos(pos) or _norm(pos)
                if p and ini is not None and fin is not None:
                    ctx.periodos_por_pos[p] = (int(ini), int(fin))
            for (est_nom, prog) in dw_db.execute(text("""
                SELECT nombre_completo, programa_origen
                  FROM public.dim_estudiante
                 WHERE deprecado = FALSE AND nombre_completo IS NOT NULL AND programa_origen IS NOT NULL
            """)):
                p = _extraer_pos(prog) or _norm(prog)
                if p and est_nom:
                    ctx.inscripciones_est_pos.add((_norm(est_nom), p))
        except Exception as exc:
            logger.warning("No se pudo cargar contexto DW de relaciones: %s", exc)

    return ctx


def validar_registro(reg_item: Dict[str, Any], ctx: ContextoRelaciones) -> List[FalloRelacion]:
    """Valida las reglas activas de `ctx.reglas` sobre un registro listo para `dw.cargar_registro`."""
    if not ctx or not ctx.reglas:
        return []

    fallos: List[FalloRelacion] = []
    res = reg_item.get("resoluciones") or {}
    categoria = (reg_item.get("categoria") or "").lower()

    prog_raw = (res.get("programa") or {}).get("valor_extraido") if isinstance(res.get("programa"), dict) else res.get("programa")
    pos_meta = ((res.get("programa") or {}).get("metadata") or {}).get("pos_canonico") if isinstance(res.get("programa"), dict) else None
    mod_raw = (res.get("modulo") or {}).get("valor_extraido") if isinstance(res.get("modulo"), dict) else res.get("modulo")
    pos_code = _extraer_pos(pos_meta) or _extraer_pos(prog_raw) or _extraer_pos(mod_raw)
    num_mod = res.get("numero_modulo")
    if num_mod is None and mod_raw:
        m_mod = re.search(r"\bM[ÓO]DULO\s*(\d{1,2})\b", str(mod_raw).upper())
        if m_mod:
            num_mod = int(m_mod.group(1))

    est_obj = res.get("estudiante")
    est_nom = (est_obj.get("valor_extraido") or (est_obj.get("fk_resolucion") or {}).get("nombre_resuelto")) if isinstance(est_obj, dict) else est_obj
    doc_obj = res.get("docente")
    doc_nom = doc_obj.get("valor_extraido") if isinstance(doc_obj, dict) else doc_obj

    fecha_val = res.get("fecha") or res.get("gestion") or res.get("anio")
    anio = _extraer_anio(fecha_val)

    # (a) Estudiante <-> Programa / Módulo y período
    if (r := ctx.reglas.get("ESTUDIANTE_PROGRAMA_PERIODO")) and r.activa:
        if r.parametros.get("validar_pos", True) and pos_code and ctx.pos_validos and pos_code not in ctx.pos_validos:
            fallos.append(FalloRelacion(
                regla=r.codigo_regla, nombre_regla=r.nombre_regla, valor=pos_code,
                detalle=f"El programa {pos_code} no existe en el catálogo institucional.",
                acciones=r.acciones_sugeridas,
            ))
        elif r.parametros.get("validar_periodo", True) and pos_code and anio and pos_code in ctx.periodos_por_pos:
            ini, fin = ctx.periodos_por_pos[pos_code]
            tol_anios = int(r.parametros.get("tolerancia_meses", 0) or 0) // 12
            if not ((ini - tol_anios) <= anio <= (fin + tol_anios)):
                fallos.append(FalloRelacion(
                    regla=r.codigo_regla, nombre_regla=r.nombre_regla, valor=f"{pos_code} ({anio})",
                    detalle=f"La gestión {anio} cae fuera del período del programa {pos_code} ({ini}–{fin}).",
                    acciones=r.acciones_sugeridas,
                ))

    # (b) Módulo <-> Programa
    if (r := ctx.reglas.get("MODULO_EN_PROGRAMA")) and r.activa:
        if pos_code and num_mod is not None and pos_code in ctx.modulos_por_pos:
            if int(num_mod) not in ctx.modulos_por_pos[pos_code]:
                fallos.append(FalloRelacion(
                    regla=r.codigo_regla, nombre_regla=r.nombre_regla, valor=f"{pos_code} · Mód. {num_mod}",
                    detalle=f"El módulo {num_mod} no existe para el programa {pos_code}.",
                    acciones=r.acciones_sugeridas,
                ))

    # (c) Docente <-> Módulo (bridge_modulo_docente)
    if (r := ctx.reglas.get("DOCENTE_MODULO_BRIDGE")) and r.activa:
        if doc_nom and pos_code:
            sin_vincular = False
            if num_mod is not None and ctx.bridge_docente_modulo:
                sin_vincular = (_norm(doc_nom), pos_code, int(num_mod)) not in ctx.bridge_docente_modulo
            elif ctx.bridge_docente_pos:
                sin_vincular = (_norm(doc_nom), pos_code) not in ctx.bridge_docente_pos
            if sin_vincular:
                motivo_sv = r.parametros.get("motivo_sin_vincular", "DOCENTE_SIN_VINCULAR")
                val_rel = f"{doc_nom} · {pos_code}" + (f" · Mód. {num_mod}" if num_mod is not None else "")
                fallos.append(FalloRelacion(
                    regla=r.codigo_regla, nombre_regla=r.nombre_regla, valor=val_rel,
                    detalle=f"{motivo_sv}: El docente '{doc_nom}' no figura vinculado en bridge_modulo_docente para {pos_code}.",
                    acciones=r.acciones_sugeridas,
                ))

    # (d) Pago <-> Inscripción
    if (r := ctx.reglas.get("PAGO_INSCRIPCION_PROGRAMA")) and r.activa:
        cats = [c.lower() for c in r.parametros.get("categorias", ["financiero"])]
        if categoria in cats and est_nom and pos_code and ctx.inscripciones_est_pos:
            if (_norm(est_nom), pos_code) not in ctx.inscripciones_est_pos:
                fallos.append(FalloRelacion(
                    regla=r.codigo_regla, nombre_regla=r.nombre_regla, valor=f"{est_nom} · {pos_code}",
                    detalle=f"El estudiante no tiene inscripción registrada en {pos_code} para el pago.",
                    acciones=r.acciones_sugeridas,
                ))

    # (e) Respuesta <-> Escala
    if (r := ctx.reglas.get("RESPUESTA_ESCALA_PREGUNTA")) and r.activa:
        punt = res.get("puntuacion") if res.get("puntuacion") is not None else res.get("valor_respuesta")
        escala_max = res.get("escala_max")
        escala_min = float(r.parametros.get("escala_min", 1))
        if punt is not None and escala_max is not None:
            try:
                p_val = float(punt)
                e_max = float(escala_max)
                if p_val < escala_min or p_val > e_max:
                    fallos.append(FalloRelacion(
                        regla=r.codigo_regla, nombre_regla=r.nombre_regla, valor=f"{p_val} (escala {escala_min:g}–{e_max:g})",
                        detalle=f"La puntuación {p_val} no cabe en la escala [{escala_min:g}, {e_max:g}].",
                        acciones=r.acciones_sugeridas,
                    ))
            except (TypeError, ValueError):
                pass

    # (f) Fecha <-> Gestión válida
    if (r := ctx.reglas.get("FECHA_GESTION_VALIDA")) and r.activa:
        if anio is not None:
            anios_inv = set(int(x) for x in r.parametros.get("anios_invalidos", [205, 2580, 3035]))
            anio_min = int(r.parametros.get("anio_min", 2015))
            anio_max = int(r.parametros.get("anio_max", 2030))
            if anio in anios_inv or anio < anio_min or anio > anio_max:
                fallos.append(FalloRelacion(
                    regla=r.codigo_regla, nombre_regla=r.nombre_regla, valor=str(fecha_val),
                    detalle=f"La gestión {anio} está fuera de rango válido ({anio_min}–{anio_max}).",
                    acciones=r.acciones_sugeridas,
                ))

    return fallos
