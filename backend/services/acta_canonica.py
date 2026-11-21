"""
backend/services/acta_canonica.py
---------------------------------
FU-L4 · Lectura de una fila de acta por campos canónicos (principio rector: sin nombres de archivo, de hoja ni
índices de columna). Las cabeceras y los vocabularios salen del catálogo `config/mapeo_fuentes.yaml` (espejo
`pipeline/mapeo_fuentes.json`), sección `tipos_fuente.ACTA`.

Reglas (decisiones de Lean, 2026-11-20):
- DA-FU2: una celda de nota guarda `nota_final` numérica y un RESULTADO canónico por módulo:
    APROBADO, REPROBADO, INASISTENCIA, EXIMIDO, SIN_NOTA.
  Un número >= 70 es APROBADO y uno menor REPROBADO; el texto sale del vocabulario `resultado_nota` («Aprobó» →
  APROBADO; «No asistió» → INASISTENCIA; «EXIMIDA» → EXIMIDO; «SIN NOTAS EN EL ACTA…» → SIN_NOTA).
  Un 0 cuenta como INASISTENCIA cuando el estado del estudiante es Deserción o Abandono; si no, es un 0 real
  (nota_final = 0, REPROBADO). Un número fuera de 0-100 o un texto fuera del vocabulario (apellidos, CI) deja la nota
  en NULL y va a revisión (NOTA_FUERA_DE_RANGO / VALOR_FUERA_DE_CATALOGO), sin publicar el valor.
- DA2-bis: estado_academico (o estado_tutoria) = DESERCION o ABANDONO identifica al desertor.
- CI con complemento o ciudad en el texto ('4892019-1C', '4892019 CBBA'): se separa en número y complemento antes de
  resolver la identidad, de modo que resuelve al mismo estudiante que '4892019'.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

TIPO = "ACTA"

APROBADO, REPROBADO, INASISTENCIA, EXIMIDO, SIN_NOTA = "APROBADO", "REPROBADO", "INASISTENCIA", "EXIMIDO", "SIN_NOTA"
RESULTADOS = (APROBADO, REPROBADO, INASISTENCIA, EXIMIDO, SIN_NOTA)
# Un módulo con estos resultados no entra al promedio (KPI-07). El denominador de la aprobación (KPI-08) deja fuera EXIMIDO y SIN_NOTA.
FUERA_DEL_PROMEDIO = (INASISTENCIA, EXIMIDO, SIN_NOTA)

NOTA_MINIMA_DEFECTO, NOTA_MAXIMA_DEFECTO = 0.0, 100.0
_RE_PREFIJO_CI = re.compile(r"^\s*c\.?\s*i\.?\s*[-:]?\s*(?=\d)", re.IGNORECASE)
_RE_NUMERO_CI = re.compile(r"^(\d{1,3}(?:\.\d{3})+|\d+)(?:\.0+)?(?=$|[^\d])")


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
def campo_de_cabecera(cabecera: str) -> Optional[Tuple[str, int]]:
    """(campo canónico, prioridad) de una cabecera según los sinónimos de ACTA, o None."""
    from pipeline.lector_hojas import _coincide
    norma = _normalizar(cabecera)
    definicion = _definicion()
    if norma in {_normalizar(x) for x in (definicion.get("no_mapear") or [])}:
        return None
    mejor = None
    for campo, espec in (definicion.get("campos") or {}).items():
        for sin in (espec or {}).get("sinonimos") or []:
            if _coincide(norma, sin):
                cand = (campo, int(sin.get("prioridad") or 1))
                if mejor is None or cand[1] < mejor[1]:
                    mejor = cand
    return mejor


@lru_cache(maxsize=1)
def _vocabularios() -> Dict[str, Any]:
    voc = _definicion().get("vocabularios") or {}
    return {
        "desercion": [(codigo, tuple(_normalizar(s) for s in (sins or []))) for codigo, sins in (voc.get("estado_desercion") or {}).items()],
        "resultado": [(res, tuple(_normalizar(s) for s in (sins or []))) for res, sins in (voc.get("resultado_nota") or {}).items()],
        "vacia": frozenset(_normalizar(s) for s in (voc.get("nota_vacia") or [])),
    }


def _calidad(clave: str) -> dict:
    return ((_definicion().get("calidad") or {}).get(clave)) or {}


def motivo(clave: str, por_defecto: str) -> str:
    return _calidad(clave).get("motivo") or por_defecto


def rango_notas() -> Tuple[float, float]:
    c = _calidad("nota_fuera_de_rango")
    return float(c.get("minimo", NOTA_MINIMA_DEFECTO)), float(c.get("maximo", NOTA_MAXIMA_DEFECTO))


def recargar_catalogo() -> None:
    """Vacía las memorias (tras editar el catálogo o en pruebas)."""
    campo_de_cabecera.cache_clear()
    _vocabularios.cache_clear()


# ── Campos de una fila {cabecera normalizada: valor} ──────────────────

def valor_de_campo(campos: Dict[str, str], campo: str) -> Optional[str]:
    """Valor no vacío del sinónimo de menor prioridad del campo canónico presente en la fila."""
    mejor: Optional[Tuple[int, str]] = None
    for cab, val in (campos or {}).items():
        res = campo_de_cabecera(cab)
        if res and res[0] == campo and val is not None and str(val).strip():
            if mejor is None or res[1] < mejor[0]:
                mejor = (res[1], val)
    return mejor[1] if mejor else None


def columnas_modulo(campos: Dict[str, str]) -> Dict[int, str]:
    """{número de módulo: valor crudo} de las columnas que el catálogo reconoce como nota de módulo (campo nota_modulo)."""
    modulos: Dict[int, str] = {}
    for cab, val in (campos or {}).items():
        res = campo_de_cabecera(cab)
        if res and res[0] == "nota_modulo" and val is not None and str(val).strip():
            m = re.search(r"\d+", cab)
            if m:
                modulos.setdefault(int(m.group(0)), val)
    return modulos


def tiene_notas_modulo(campos: Dict[str, str]) -> bool:
    return bool(columnas_modulo(campos))


# ── Estados ───────────────────────────────────────────────────────────

def codigo_estado(valor: Optional[str]) -> Optional[str]:
    """DESERCION / ABANDONO según el vocabulario `estado_desercion`; None para cualquier otro estado."""
    if valor is None or not str(valor).strip():
        return None
    norma = _normalizar(valor)
    for codigo, sinonimos in _vocabularios()["desercion"]:
        if norma in sinonimos:
            return codigo
    return None


def es_desercion(*estados: Optional[str]) -> bool:
    """Alguno de los estados (académico, tutoría) es Deserción o Abandono (DA2-bis)."""
    return any(codigo_estado(e) for e in estados)


# ── Notas ─────────────────────────────────────────────────────────────

@dataclass
class CeldaNota:
    """Lectura de una celda de nota ANTES de aplicar la escala del programa.
    clase: NUMERO (numero válido en 0-100), TEXTO (resultado del vocabulario), FUERA_DE_RANGO, FUERA_DE_CATALOGO, VACIA."""
    clase: str
    numero: Optional[float] = None
    resultado: Optional[str] = None


def _numero(valor: Any) -> Optional[float]:
    from pipeline.normalization.montos import parsear_monto
    return parsear_monto(valor)


def leer_celda(valor: Optional[str]) -> CeldaNota:
    if valor is None or not str(valor).strip() or str(valor).strip().lower() == "nan":
        return CeldaNota("VACIA")
    texto = str(valor).strip()
    norma = _normalizar(texto)
    if norma in _vocabularios()["vacia"]:
        return CeldaNota("VACIA")
    num = _numero(texto)
    if num is not None:
        minimo, maximo = rango_notas()
        if minimo <= num <= maximo:
            return CeldaNota("NUMERO", numero=num)
        return CeldaNota("FUERA_DE_RANGO")
    for resultado, claves in _vocabularios()["resultado"]:
        if any(c and c in norma for c in claves):
            return CeldaNota("TEXTO", resultado=resultado)
    return CeldaNota("FUERA_DE_CATALOGO")


def notas_numericas(campos: Dict[str, str]) -> List[float]:
    """Notas numéricas válidas (0-100) de la fila, sin escalar (para deducir la escala del programa)."""
    celdas = (leer_celda(v) for v in columnas_modulo(campos).values())
    return [c.numero for c in celdas if c.clase == "NUMERO"]


def resultado_de_nota(nota: Optional[float]) -> Optional[str]:
    """APROBADO si la nota (base 100) llega a la nota de aprobación; REPROBADO si no; None sin nota."""
    if nota is None:
        return None
    from pipeline.config import NOTA_APROBACION
    return APROBADO if float(nota) >= NOTA_APROBACION else REPROBADO


def resolver_numero(nota_base100: float, desercion: bool) -> Tuple[Optional[float], str]:
    """(nota_final, resultado) de una nota numérica ya en base 100. Un 0 con Deserción o Abandono es INASISTENCIA
    (nota_final NULL); un 0 sin ese estado es un 0 real (0 y REPROBADO)."""
    if nota_base100 == 0 and desercion:
        return None, INASISTENCIA
    return round(nota_base100, 2), resultado_de_nota(nota_base100)


# ── CI ────────────────────────────────────────────────────────────────

def separar_ci(valor: Optional[Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    (número, complemento) de un CI escrito a mano. '4892019' → ('4892019', None); '4892019.0' (número de Excel) →
    ('4892019', None); '4892019-1C' → ('4892019', '1C'); '4892019 CBBA' → ('4892019', 'CBBA'); '4.892.019 Ch.' →
    ('4892019', 'CH'); 'CI-4892019' → ('4892019', None). Sin dígitos al inicio (CI extranjera 'E-123', basura) → (None, None):
    el llamador conserva su lectura anterior.
    """
    if valor is None:
        return None, None
    texto = _RE_PREFIJO_CI.sub("", str(valor)).strip()
    m = _RE_NUMERO_CI.match(texto)
    if not m:
        return None, None
    numero = m.group(1).replace(".", "")
    resto = texto[m.end():]
    comp = re.sub(r"[^0-9A-Za-zÁÉÍÓÚÑáéíóúñ]", "", resto).upper()[:10]
    return numero, (comp or None)
