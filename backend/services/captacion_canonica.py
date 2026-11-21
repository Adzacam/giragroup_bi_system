"""
backend/services/captacion_canonica.py
--------------------------------------
FU-L3 (DA6) · Captación de una fila programa x mes por CAMPOS CANÓNICOS (principio rector: sin nombres de archivo,
de hoja ni índices de columna).

Los campos `leads_captacion`, `inscritos_captacion`, `reservas`, `pos`, `programa` y el período (`anio_periodo`,
`mes_periodo`, `fecha_periodo`) se reconocen con los sinónimos de `config/mapeo_fuentes.yaml` (espejo
`pipeline/mapeo_fuentes.json`). Los sinónimos se unen de TODOS los tipos de fuente del catálogo: una hoja de
cualquier tipo con granularidad programa x mes se lee igual; añadir una cabecera nueva es añadir un sinónimo.

Reglas (decisión DA6 de Lean):
- una fila cuenta para el KPI-06 solo con ambos datos y 0 <= inscritos <= leads (migración 014);
- las reservas se guardan y no entran en el KPI;
- el período sale de una fecha, de año + mes o, sin ellos, del período de la hoja (hoja mensual);
- un mismo programa (POS) y mes en varias hojas se cuenta una vez: gana la hoja de menor prioridad
  (`prioridad_de_hoja`), que va de la hoja de detalle mensual visible a la tabla por programa oculta.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

CAMPOS_CAPTACION = ("leads_captacion", "inscritos_captacion", "reservas",
                    "anio_periodo", "mes_periodo", "fecha_periodo", "pos", "programa")
# Campos que, si aparecen en la fila, la convierten en una fila de captación (los de período y programa no bastan).
CAMPOS_METRICA = ("leads_captacion", "inscritos_captacion", "reservas")
PRIORIDAD_DEFECTO = 3


@dataclass
class FilaCaptacion:
    leads: Optional[float] = None
    inscritos: Optional[float] = None
    reservas: Optional[float] = None
    pos: Optional[str] = None
    programa: Optional[str] = None
    periodo: Optional[date] = None        # período de la fila (fecha, año + mes) o de la hoja mensual
    periodo_de_hoja: bool = False         # el período salió de la hoja (no de la fila)

    @property
    def valida(self) -> bool:
        """Ambos datos presentes como enteros y 0 <= inscritos <= leads (la regla de la migración 014)."""
        return es_entero(self.leads) and es_entero(self.inscritos) and 0 <= self.inscritos <= self.leads

    @property
    def conversion_posible(self) -> bool:
        return self.valida and self.leads > 0 and self.periodo is not None and bool(self.pos)


# ── Catálogo ──────────────────────────────────────────────────────────

def _config() -> dict:
    from pipeline.lector_hojas import cargar_config
    return cargar_config()


def _normalizar(texto: Any) -> str:
    from pipeline.lector_hojas import normalizar
    return normalizar(texto)


@lru_cache(maxsize=4096)
def campo_de_cabecera(cabecera: str) -> Optional[Tuple[str, int]]:
    """(campo canónico, prioridad) de una cabecera según los sinónimos de cualquier tipo de fuente, o None."""
    from pipeline.lector_hojas import _coincide
    norma = _normalizar(cabecera)
    mejor: Optional[Tuple[str, int]] = None
    for definicion in (_config().get("tipos_fuente") or {}).values():
        if norma in {_normalizar(x) for x in (definicion.get("no_mapear") or [])}:
            continue
        for campo, espec in (definicion.get("campos") or {}).items():
            if campo not in CAMPOS_CAPTACION:
                continue
            for sin in (espec or {}).get("sinonimos") or []:
                if _coincide(norma, sin):
                    cand = (campo, int(sin.get("prioridad") or 1))
                    if mejor is None or cand[1] < mejor[1]:
                        mejor = cand
    return mejor


def recargar_catalogo() -> None:
    campo_de_cabecera.cache_clear()


def reglas() -> dict:
    return _config().get("captacion") or {}


def prioridad_de_hoja(estado: Optional[str], periodo_dominante: Optional[str]) -> int:
    """
    Prioridad de una hoja como fuente de captación (menor gana). Hoja de detalle mensual = un único mes
    dominante en sus filas; tabla por programa = el mes viene en cada fila. Visible antes que oculta rescatada.
    """
    pri = reglas().get("prioridad_origen") or {}
    oculta = (estado or "visible") != "visible"
    if periodo_dominante:
        return int(pri.get("detalle_mensual_oculta" if oculta else "detalle_mensual_visible", 2 if oculta else 1))
    return int(pri.get("por_programa_oculta" if oculta else "por_programa_visible", 4 if oculta else 3))


def prioridad_sin_metadatos() -> int:
    return int(reglas().get("prioridad_sin_metadatos", PRIORIDAD_DEFECTO))


# ── Lectura de valores ────────────────────────────────────────────────

def es_entero(valor: Any) -> bool:
    try:
        return valor is not None and float(valor) >= 0 and float(valor) == int(float(valor))
    except (TypeError, ValueError):
        return False


def _numero(valor: Optional[str]) -> Optional[float]:
    from pipeline.normalization.montos import parsear_monto
    if valor is None or not str(valor).strip():
        return None
    return parsear_monto(str(valor))


def _pos(valor: Optional[str]) -> Optional[str]:
    """POS normalizado ('POS-5381'); celdas de plantilla (FALSE, 0…) no son un POS."""
    import re
    if valor is None:
        return None
    crudo = str(valor).strip()
    if not crudo or crudo.upper() in ("FALSE", "TRUE", "0", "NONE", "NAN", "-"):
        return None
    m = re.match(r"^(?:POS[\s-]?)?(\d{3,5})(?:\.0+)?$", crudo, re.IGNORECASE)
    return f"POS-{m.group(1)}" if m else crudo[:80]


def leer_periodo(valores: Dict[str, Optional[str]]) -> Optional[date]:
    """Período de la fila: la fecha de período tal cual; si no, el primer día del mes de año + mes (número o nombre)."""
    from services.extraccion_por_encabezado import ANIO_MAX, ANIO_MIN, _mes, parsear_fecha
    f = parsear_fecha(valores.get("fecha_periodo"))
    if f:
        return f
    anio = _numero(valores.get("anio_periodo"))
    mes = _mes(valores.get("mes_periodo"))
    if anio and ANIO_MIN <= anio <= ANIO_MAX and mes:
        return date(int(anio), mes, 1)
    return None


def _por_campo(campos: Dict[str, str]) -> Dict[str, List[Tuple[int, str]]]:
    por_campo: Dict[str, List[Tuple[int, str]]] = {}
    for cab, val in (campos or {}).items():
        res = campo_de_cabecera(cab)
        if res and val is not None and str(val).strip():
            por_campo.setdefault(res[0], []).append((res[1], str(val)))
    return por_campo


def leer_identidad(campos: Dict[str, str], anio_hoja: Optional[int] = None, mes_hoja: Optional[int] = None
                   ) -> Tuple[Optional[str], Optional[str], Optional[date], bool]:
    """(pos normalizado, programa, período, el período salió de la hoja) de una fila, sin exigir datos de captación."""
    por_campo = _por_campo(campos)

    def valor(campo: str) -> Optional[str]:
        return min(por_campo[campo], key=lambda t: t[0])[1] if campo in por_campo else None

    periodo = leer_periodo({c: valor(c) for c in ("fecha_periodo", "anio_periodo", "mes_periodo")})
    de_hoja = False
    if periodo is None and anio_hoja and mes_hoja:
        periodo, de_hoja = date(int(anio_hoja), int(mes_hoja), 1), True
    return _pos(valor("pos")), (valor("programa") or None), periodo, de_hoja


def mes_de(periodo: Optional[date]) -> Optional[date]:
    """Primer día del mes de un período (la unidad de la captación)."""
    return date(periodo.year, periodo.month, 1) if periodo else None


def leer_fila(campos: Dict[str, str], anio_hoja: Optional[int] = None, mes_hoja: Optional[int] = None
              ) -> Optional[FilaCaptacion]:
    """
    Lee una fila {cabecera: valor} por campos canónicos. None si no trae ningún dato de captación (leads,
    inscritos o reservas) del catálogo: entonces no es una fila de captación.
    `anio_hoja`/`mes_hoja`: período de la hoja mensual, solo si la fila no trae su propio período.
    """
    por_campo = _por_campo(campos)
    if not any(c in por_campo for c in CAMPOS_METRICA):
        return None

    def valor(campo: str) -> Optional[str]:
        return min(por_campo[campo], key=lambda t: t[0])[1] if campo in por_campo else None

    pos, programa, periodo, de_hoja = leer_identidad(campos, anio_hoja, mes_hoja)
    return FilaCaptacion(
        leads=_numero(valor("leads_captacion")),
        inscritos=_numero(valor("inscritos_captacion")),
        reservas=_numero(valor("reservas")),
        pos=pos, programa=programa, periodo=mes_de(periodo), periodo_de_hoja=de_hoja,
    )


def metricas_enteras(campos: Dict[str, str]) -> Dict[str, int]:
    """
    {leads, inscritos, reservas}: contadores explícitos enteros no negativos de la fila (sin deducirlos de
    personas ni de inscripciones). Reemplaza la lista fija de cabeceras de `metricas_captacion`.
    """
    fila = leer_fila(campos)
    if fila is None:
        return {}
    out = {}
    for destino, valor in (("leads", fila.leads), ("inscritos", fila.inscritos), ("reservas", fila.reservas)):
        if es_entero(valor):
            out[destino] = int(valor)
    return out


# ── Elección de la hoja ganadora de un programa y mes ─────────────────

def elegir_fuente(candidatos: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Una sola fuente por programa y mes. `candidatos`: filas válidas {hoja, prioridad, leads, inscritos, documento}.
    Gana la hoja de menor prioridad (desempate por nombre de hoja, para que el resultado no dependa del orden de
    carga) y se suman las filas de esa hoja. Si la misma hoja llegó en varios documentos (el libro se volvió a subir con
    cifras corregidas), vale el documento más reciente: la corrección reemplaza, no se suma.
    Devuelve {hoja, prioridad, leads, inscritos, hojas_descartadas}.
    """
    por_hoja: Dict[Tuple[int, str], List[Dict[str, Any]]] = {}
    for c in candidatos:
        k = (int(c.get("prioridad") if c.get("prioridad") is not None else PRIORIDAD_DEFECTO), str(c.get("hoja") or ""))
        por_hoja.setdefault(k, []).append(c)
    if not por_hoja:
        return None
    clave = min(por_hoja)
    filas = por_hoja[clave]
    ultimo = max(int(f.get("documento") or 0) for f in filas)
    vigentes = [f for f in filas if int(f.get("documento") or 0) == ultimo]
    return {"hoja": clave[1], "prioridad": clave[0], "leads": sum(int(f["leads"]) for f in vigentes),
            "inscritos": sum(int(f["inscritos"]) for f in vigentes), "hojas_descartadas": len(por_hoja) - 1}
