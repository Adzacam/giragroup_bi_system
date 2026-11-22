"""
backend/services/metas_canonica.py
----------------------------------
FU-L6 · Metas y ejecutado financiero por CAMPOS CANÓNICOS (`monto_meta`, `monto_ejecutado`), sin nombres de archivo, de hoja ni
índices de columna. Los sinónimos de columna, la granularidad, la prioridad entre fuentes y los textos «sin dato» salen de
`config/mapeo_fuentes.yaml` (espejo `pipeline/mapeo_fuentes.json`), secciones `metas` y `prioridad_fuentes`.

Dos decisiones de Lean (2026-11-20) viven aquí:

- DA4 · Granularidad de la meta (`MENSUAL` / `ANUAL`) según la FORMA de la fuente, no según el año. Por categoría y año de una hoja se
  cuentan los meses distintos con meta: una sola celda es una meta ANUAL y no se coloca en ningún mes; dos o más son MENSUAL. Una hoja
  que solo cubre un mes no permite deducir nada y sus metas son MENSUALES. `perfilar` mira toda la hoja (todos sus bloques de líneas).
- DA-FU3 · Prioridad por TIPO de fuente y campo (`prioridad_fuentes`): para `monto_meta` y `monto_ejecutado` manda RENTABILIDAD sobre EGRESOS.
  Si dos fuentes de distinto tipo dan otro valor para el mismo campo y mes, gana la de mayor prioridad y el conflicto queda resuelto
  por regla. `decidir` devuelve quién gana; con tipos iguales o fuera de la lista no hay regla (queda pendiente para una persona).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

_DEFECTOS = {
    "columnas": {
        "ejecutado": [r"^ejecutado (\d{4})$"],
        "meta_especifica": [r"^meta por categoria (\d{4})$"],
        "meta_generica": [r"^meta (\d{4})$"],
    },
    "claves_categoria": ["categoria", "tipo de ingreso", "tipo ingreso", "categoria financiera", "serie"],
    "granularidad": {"mensual": "MENSUAL", "anual": "ANUAL", "min_meses_mensual": 2},
    "conflicto": {"motivo": "CONFLICTO_FUENTES", "estado_resuelto": "RESUELTO_REGLA", "estado_pendiente": "PENDIENTE",
                  "regla_origen": "FU-L6:PRIORIDAD_POR_TIPO_DE_FUENTE", "multiplo_aviso": 100000},
}
_PRIORIDAD_DEFECTO = {"monto_meta": ["RENTABILIDAD", "EGRESOS"], "monto_ejecutado": ["RENTABILIDAD", "EGRESOS"],
                      "monto_egreso": ["EGRESOS", "RENTABILIDAD"], "costos": ["EGRESOS", "RENTABILIDAD"]}


# ── Catálogo ──────────────────────────────────────────────────────────

def _config() -> dict:
    from pipeline.lector_hojas import cargar_config
    return cargar_config()


def _metas() -> dict:
    return _config().get("metas") or {}


def _seccion(nombre: str) -> dict:
    return {**_DEFECTOS.get(nombre, {}), **(_metas().get(nombre) or {})}


@lru_cache(maxsize=1)
def _patrones() -> Dict[str, Tuple[re.Pattern, ...]]:
    cols = {**_DEFECTOS["columnas"], **(_metas().get("columnas") or {})}
    return {rol: tuple(re.compile(p, re.IGNORECASE) for p in pats) for rol, pats in cols.items()}


def recargar_catalogo() -> None:
    _patrones.cache_clear()
    _claves_categoria.cache_clear()


def anio_de_columna(cabecera: str, rol: str) -> Optional[int]:
    """Año de una columna de `rol` (`ejecutado`, `meta_especifica`, `meta_generica`) según los sinónimos del catálogo."""
    norma = (cabecera or "").strip()
    for patron in _patrones().get(rol, ()):
        m = patron.match(norma)
        if m:
            try:
                return int(m.group(1))
            except (IndexError, ValueError):
                return None
    return None


@lru_cache(maxsize=1)
def _claves_categoria() -> Tuple[str, ...]:
    claves = _metas().get("claves_categoria") or _DEFECTOS["claves_categoria"]
    return tuple(str(c).upper() for c in claves)


def claves_categoria() -> Tuple[str, ...]:
    """Cabeceras (mayúsculas, sin acentos) que dicen a qué serie pertenece la fila."""
    return _claves_categoria()


def etiquetas_granularidad() -> Tuple[str, str]:
    g = _seccion("granularidad")
    return str(g["mensual"]), str(g["anual"])


def configuracion_conflicto() -> dict:
    return _seccion("conflicto")


def motivo_sin_dato(clave: str, defecto: str = "") -> str:
    return str((_metas().get("motivos_sin_dato") or {}).get(clave) or defecto)


# ── DA4 · granularidad por la forma de la hoja ────────────────────────

@dataclass
class PerfilMetas:
    """Meses con meta por (categoría, año) en una hoja, y meses con alguna fila de la hoja (todas sus columnas)."""
    meses_con_meta: Dict[Tuple[str, int], Set[int]] = field(default_factory=dict)
    meses_hoja: Set[Tuple[int, int]] = field(default_factory=set)   # (año, mes) de las filas con ejecutado o meta

    def granularidad(self, categoria: str, anio: int) -> Optional[str]:
        """`MENSUAL` o `ANUAL` de la meta de (categoría, año); None si la hoja no trae meta de esa serie."""
        mensual, anual = etiquetas_granularidad()
        meses = self.meses_con_meta.get((categoria, anio))
        if not meses:
            return None
        minimo = int(_seccion("granularidad").get("min_meses_mensual", 2))
        if len(meses) >= minimo:
            return mensual
        # Una hoja que solo cubre un mes no distingue una meta anual de una mensual: se lee como mensual.
        meses_del_anio = {m for a, m in self.meses_hoja if a == anio}
        return anual if len(meses_del_anio) >= minimo else mensual


def perfilar(lineas: Iterable[Dict[str, str]]) -> PerfilMetas:
    """Perfil de metas de una hoja a partir de TODAS sus filas (`campos_por_encabezado` de cada línea)."""
    from services.extraccion_por_encabezado import registros_rentabilidad
    perfil = PerfilMetas()
    for campos in lineas:
        for reg in registros_rentabilidad(campos) if campos else []:
            fecha = reg["fecha"]
            perfil.meses_hoja.add((fecha.year, fecha.month))
            if reg.get("monto_meta") is not None:
                perfil.meses_con_meta.setdefault((reg["categoria_financiera"], fecha.year), set()).add(fecha.month)
    return perfil


# ── DA-FU3 · prioridad por tipo de fuente y campo ─────────────────────

def _lista_prioridad(campo: str) -> List[str]:
    cfg = _config().get("prioridad_fuentes") or {}
    lista = cfg.get(campo) or _PRIORIDAD_DEFECTO.get(campo) or []
    return [str(t).upper().strip() for t in lista]


def rango_tipo(campo: str, tipo_fuente: Optional[str]) -> Optional[int]:
    """Posición del tipo de fuente en la prioridad del campo (0 = manda); None si el tipo no figura."""
    tipo = (tipo_fuente or "").upper().strip()
    lista = _lista_prioridad(campo)
    return lista.index(tipo) if tipo in lista else None


def decidir(campo: str, tipo_nuevo: Optional[str], tipo_previo: Optional[str]) -> Optional[bool]:
    """
    True si la fuente NUEVA gana a la ya cargada, False si gana la previa, None si ninguna regla decide
    (mismo tipo o un tipo que la prioridad del campo no menciona).
    """
    a, b = rango_tipo(campo, tipo_nuevo), rango_tipo(campo, tipo_previo)
    if a is None or b is None or a == b:
        return None
    return a < b


def es_multiplo_de_aviso(diferencia: float) -> bool:
    """Una diferencia exacta múltiplo del monto de aviso (100.000) apunta a un error de tipeo: se avisa al área financiera."""
    paso = float(configuracion_conflicto().get("multiplo_aviso") or 0)
    if paso <= 0:
        return False
    d = abs(float(diferencia))
    # tolerancia de un centavo: las fuentes redondean (1.168.196,00 frente a 1.068.196,001 es una diferencia de 100.000)
    return d >= paso - 0.01 and abs(d - round(d / paso) * paso) <= 0.01


def describir_conflicto(categoria: str, id_tiempo: Any, campo: str, tipo_elegido: Optional[str], tipo_descartado: Optional[str],
                        elegido: float, descartado: float) -> str:
    """Texto fijo del conflicto resuelto por regla (el informe lo lee de vuelta; sin nombres de archivo ni datos personales)."""
    dif = round(abs(float(elegido) - float(descartado)), 2)
    return (f"FU-L6 | {categoria} | id_tiempo={id_tiempo} | campo={campo} | elegida={tipo_elegido or '?'} | descartada={tipo_descartado or '?'} "
            f"| elegido={elegido:.2f} | descartado={descartado:.2f} | diferencia={dif:.2f} | multiplo_100000={'si' if es_multiplo_de_aviso(dif) else 'no'}")


def leer_conflicto(descripcion: str) -> Optional[Dict[str, str]]:
    """Inverso de `describir_conflicto`; None si el texto no es de un conflicto resuelto por regla."""
    if not descripcion or not descripcion.startswith("FU-L6 | "):
        return None
    partes = [p.strip() for p in descripcion.split("|")]
    res: Dict[str, str] = {"categoria": partes[1]}
    for p in partes[2:]:
        k, _, v = p.partition("=")
        res[k.strip()] = v.strip()
    return res
