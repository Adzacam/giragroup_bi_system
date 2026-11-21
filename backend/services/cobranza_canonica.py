"""
backend/services/cobranza_canonica.py
-------------------------------------
FU-L2 · Lectura de una fila de cobranza por campos canónicos (principio rector: sin nombres de archivo,
de hoja ni índices de columna). Las cabeceras se resuelven con los sinónimos del catálogo
`config/mapeo_fuentes.yaml` (espejo `pipeline/mapeo_fuentes.json`), sección `tipos_fuente.COBRANZA`.

Una fila de la fuente (estudiante × programa) produce:
- un hecho de **situación** en la fecha de inicio del programa: deuda, cuotas en mora, días de mora y
  estado de cartera de la fuente (descriptivo; la mora la decide DA3 en `regla_mora`);
- un hecho de **pago** por cada columna de pago mensual con monto, en el mes del pago (las columnas
  «(PRELIMINAR)» quedan fuera por la regla `excluir` del catálogo).

Reglas de calidad (avisos que el cargador registra de forma agregada, sin PII):
- cuotas negativas -> 0 (CUOTAS_NEGATIVAS); texto con número inicial ('1s') -> ese número (CUOTAS_CON_TEXTO);
- deuda negativa -> 0 (SOBREPAGO); días de mora negativos -> 0;
- estado de cartera fuera del vocabulario -> sin estado de fuente y a revisión (VALOR_FUERA_DE_CATALOGO).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

TIPO = "COBRANZA"
CONCEPTO_PAGO_MES = "PAGO_MES"
CONCEPTO_SITUACION = "SITUACION_CARTERA"

# Campos que, si aparecen en la fila, la hacen una fila de cobranza leíble por catálogo.
CAMPOS_COBRANZA = ("estado_cartera_fuente", "cuotas_en_mora", "dias_mora", "monto_pago_mes",
                   "monto_deuda", "monto_pagado_total")

_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_RE_MES = re.compile(r"\b(" + "|".join(_MESES) + r")\b")
_RE_ANIO = re.compile(r"\b(20\d{2})\b")
_RE_NUM_INICIAL = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)")


@dataclass
class Aviso:
    motivo: str
    campo: str
    valor: str          # valor de la fuente (no personal: conteos, estados, montos)


@dataclass
class FilaCobranza:
    estado_cartera_fuente: Optional[str] = None
    cuotas_impagas: Optional[int] = None
    dias_mora: Optional[int] = None
    monto_deuda: Optional[float] = None
    monto_pagado_total: Optional[float] = None
    fecha_inicio: Optional[date] = None
    pagos: List[Tuple[date, float]] = field(default_factory=list)
    avisos: List[Aviso] = field(default_factory=list)
    revision: bool = False   # un valor fuera de catálogo manda el hecho de situación a revisión


# ── Catálogo ──────────────────────────────────────────────────────────

def _config() -> dict:
    from pipeline.lector_hojas import cargar_config
    return cargar_config()


def _definicion() -> dict:
    return ((_config().get("tipos_fuente") or {}).get(TIPO)) or {}


def _normalizar(texto: Any) -> str:
    from pipeline.lector_hojas import normalizar
    return normalizar(texto)


@lru_cache(maxsize=4096)
def campo_de_cabecera(cabecera: str) -> Optional[Tuple[str, int, bool]]:
    """(campo canónico, prioridad, ambiguo) de una cabecera según los sinónimos de COBRANZA, o None."""
    from pipeline.lector_hojas import _coincide
    norma = _normalizar(cabecera)
    definicion = _definicion()
    if norma in {_normalizar(x) for x in (definicion.get("no_mapear") or [])}:
        return None
    mejor = None
    for campo, espec in (definicion.get("campos") or {}).items():
        for sin in (espec or {}).get("sinonimos") or []:
            if _coincide(norma, sin):
                cand = (campo, int(sin.get("prioridad") or 1), bool(sin.get("ambiguo")))
                if mejor is None or cand[1] < mejor[1]:
                    mejor = cand
    return mejor


@lru_cache(maxsize=1)
def _vocabulario_cartera() -> Dict[str, str]:
    voc = ((_definicion().get("vocabularios") or {}).get("estado_cartera_fuente")) or {}
    return {_normalizar(s): canon for canon, sinonimos in voc.items() for s in (sinonimos or [])}


def _motivo(clave: str, por_defecto: str) -> str:
    return (((_definicion().get("calidad") or {}).get(clave)) or {}).get("motivo") or por_defecto


def recargar_catalogo() -> None:
    """Vacía las memorias (tras editar el catálogo o en pruebas)."""
    campo_de_cabecera.cache_clear()
    _vocabulario_cartera.cache_clear()


# ── Lectura de valores ────────────────────────────────────────────────

def _numero(valor: Optional[str]) -> Optional[float]:
    from pipeline.normalization.montos import parsear_monto
    return parsear_monto(valor)


def normalizar_estado_cartera(valor: Optional[str]) -> Tuple[Optional[str], bool]:
    """(estado canónico, está en catálogo). Vacío -> (None, True)."""
    if valor is None or not str(valor).strip():
        return None, True
    canon = _vocabulario_cartera().get(_normalizar(valor))
    return canon, canon is not None


def leer_cuotas(valor: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
    """(cuotas >= 0, motivo de aviso o None). Negativo -> 0; '1s' -> 1; texto sin número -> 0."""
    if valor is None or not str(valor).strip():
        return None, None
    num = _numero(valor)
    motivo = None
    if num is None:
        m = _RE_NUM_INICIAL.match(str(valor))
        if not m:
            return 0, _motivo("cuotas_no_numericas", "CUOTAS_NO_NUMERICAS")
        num = _numero(m.group(1))
        motivo = _motivo("cuotas_con_texto", "CUOTAS_CON_TEXTO")
        if num is None:
            return 0, _motivo("cuotas_no_numericas", "CUOTAS_NO_NUMERICAS")
    if num < 0:
        return 0, _motivo("cuotas_negativas", "CUOTAS_NEGATIVAS")
    return int(num), motivo


def mes_de_columna(cabecera: str) -> Optional[Tuple[int, int]]:
    """(año, mes) de una cabecera de pago mensual ('MONTO ENERO 2024' -> (2024, 1)); None si no lo trae."""
    norma = _normalizar(cabecera)
    m_mes, m_anio = _RE_MES.search(norma), _RE_ANIO.search(norma)
    if not (m_mes and m_anio):
        return None
    return int(m_anio.group(1)), _MESES[m_mes.group(1)]


# ── Fila ──────────────────────────────────────────────────────────────

def leer_fila(campos: Dict[str, str]) -> Optional[FilaCobranza]:
    """
    Lee una fila {cabecera: valor} por campos canónicos. None si la fila no trae ningún campo de cobranza
    del catálogo (entonces rige el camino genérico).
    """
    from services.extraccion_por_encabezado import parsear_fecha

    por_campo: Dict[str, List[Tuple[int, bool, str, str]]] = {}
    for cab, val in (campos or {}).items():
        res = campo_de_cabecera(cab)
        if res:
            campo, prioridad, ambiguo = res
            por_campo.setdefault(campo, []).append((prioridad, ambiguo, cab, val))
    if not any(c in por_campo for c in CAMPOS_COBRANZA):
        return None

    def valor(campo: str) -> Optional[str]:
        candidatos = por_campo.get(campo) or []
        especificos = [c for c in candidatos if not c[1]]
        elegidos = especificos or candidatos   # un sinónimo ambiguo solo si no hay uno específico
        return min(elegidos)[3] if elegidos else None

    fila = FilaCobranza()

    estado_raw = valor("estado_cartera_fuente")
    fila.estado_cartera_fuente, en_catalogo = normalizar_estado_cartera(estado_raw)
    if not en_catalogo:
        fila.revision = True
        fila.avisos.append(Aviso(_motivo("valor_fuera_de_catalogo", "VALOR_FUERA_DE_CATALOGO"),
                                 "estado_cartera_fuente", str(estado_raw)[:60]))

    fila.cuotas_impagas, motivo = leer_cuotas(valor("cuotas_en_mora"))
    if motivo:
        fila.avisos.append(Aviso(motivo, "cuotas_en_mora", str(valor("cuotas_en_mora"))[:30]))
    if fila.cuotas_impagas is None:
        fila.cuotas_impagas = 0   # fila de cartera sin dato de cuotas: no está en mora

    dias = _numero(valor("dias_mora"))
    if dias is not None:
        if dias < 0:
            fila.avisos.append(Aviso(_motivo("dias_mora_negativos", "DIAS_MORA_NEGATIVOS"), "dias_mora", str(dias)))
            dias = 0
        fila.dias_mora = int(dias)

    deuda = _numero(valor("monto_deuda"))
    if deuda is not None and deuda < 0:
        fila.avisos.append(Aviso(_motivo("deuda_negativa", "SOBREPAGO"), "monto_deuda", f"{deuda:.2f}"))
        deuda = 0.0
    fila.monto_deuda = deuda
    fila.monto_pagado_total = _numero(valor("monto_pagado_total"))
    fila.fecha_inicio = parsear_fecha(valor("fecha_inicio"))

    acumulado: Dict[date, float] = {}
    for _prioridad, _amb, cab, val in por_campo.get("monto_pago_mes") or []:
        periodo = mes_de_columna(cab)
        monto = _numero(val)
        if periodo is None or monto is None or monto == 0:
            continue
        mes = date(periodo[0], periodo[1], 1)
        acumulado[mes] = acumulado.get(mes, 0.0) + monto
    fila.pagos = sorted(acumulado.items())
    return fila


def registros_cobranza(campos: Dict[str, str], fecha_respaldo: Optional[date] = None
                       ) -> Optional[Tuple[List[Dict[str, Any]], FilaCobranza]]:
    """
    Resoluciones parciales de los hechos de una fila de cobranza: primero la situación (fecha de inicio o,
    sin ella, `fecha_respaldo`) y después un pago por mes. None si la fila no es de cobranza por catálogo.
    Cada pago lleva `subclave_fila` para que `carga_fila_origen` tenga una clave por fila y mes.
    """
    fila = leer_fila(campos)
    if fila is None:
        return None
    fecha_sit = fila.fecha_inicio or fecha_respaldo
    con_pagos_mensuales = bool(fila.pagos)
    situacion = {
        "monto_deuda": fila.monto_deuda if fila.monto_deuda is not None else 0.0,
        # Con columnas de pago mensual, lo pagado va a cada mes; si no, la fila trae solo el total.
        "monto_pagado": 0.0 if con_pagos_mensuales else (fila.monto_pagado_total or 0.0),
        "cuotas_impagas": fila.cuotas_impagas,
        "dias_mora": fila.dias_mora,
        "estado_cartera_fuente": fila.estado_cartera_fuente,
        "concepto": CONCEPTO_SITUACION,
        "fecha": fecha_sit,
        "fecha_identidad": fecha_sit,
        "tipo_hecho_fin": "SITUACION",
        "_revision_fila": fila.revision,
        "avisos_cobranza": [(a.motivo, a.campo, a.valor) for a in fila.avisos],
    }
    registros = [situacion]
    for mes, monto in fila.pagos:
        registros.append({
            "monto_deuda": None,
            "monto_pagado": round(monto, 2),
            "cuotas_impagas": None,
            "dias_mora": None,
            "estado_cartera_fuente": None,
            "concepto": CONCEPTO_PAGO_MES,
            "fecha": mes,
            "fecha_identidad": fecha_sit,
            "tipo_hecho_fin": "PAGO_MES",
            "subclave_fila": f"PAGO|{mes.year}-{mes.month:02d}",
            "_revision_fila": False,
            "avisos_cobranza": [],
        })
    return registros, fila
