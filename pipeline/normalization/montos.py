"""
pipeline/normalization/montos.py
--------------------------------
Lectura de montos y números escritos a mano en planillas: 'Bs1.171.260', 'Bs 3,000.00', '2,730.00',
'1.234,56', '$us 500', '4,5', '#VALUE!'.

Regla de separadores (sin depender de un archivo concreto):
- Con '.' y ',' a la vez: el último que aparece es el decimal; el otro, de miles.
- Varios '.' o varias ',': son de miles ('1.171.260', '1,171,260').
- Un solo separador seguido de exactamente 3 dígitos ('679.446', '2,730'): es de miles solo si el texto
  traía prefijo de moneda o es una coma; un punto suelto sin moneda ('1.261') se deja como decimal, porque
  así serializa Excel/pandas los porcentajes y razones.
- Cualquier otro caso de un solo separador: decimal ('4454.4', '4,5').
"""

import re
from typing import Any, Optional

_RE_MONEDA = re.compile(r"^\s*(?:BS\.?|BOB|\$US|\$|USD|US\$)\s*", re.IGNORECASE)
_RE_MONEDA_FINAL = re.compile(r"\s*(?:BS\.?|BOB|\$US|USD)\s*$", re.IGNORECASE)  # '1500.50 Bs'
_VACIOS ={"", "nan", "none", "null", "-", "n/a", "na", "s/d"}
_RE_NUMERO = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


def parsear_monto(valor: Any) -> Optional[float]:
    """Número de una celda, o None si está vacía, es un error de Excel (#VALUE!, #REF!…) o no es numérica."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return None if valor != valor else float(valor)  # NaN -> None
    texto = str(valor).strip().replace(" ", " ")
    if texto.lower() in _VACIOS or texto.startswith("#"):
        return None

    con_moneda = bool(_RE_MONEDA.match(texto) or _RE_MONEDA_FINAL.search(texto))
    v = _RE_MONEDA_FINAL.sub("", _RE_MONEDA.sub("", texto)).replace(" ", "")
    negativo = v.startswith("(") and v.endswith(")")  # (1.500) contable
    v = v.strip("()")

    puntos, comas = v.count("."), v.count(",")
    if puntos and comas:
        decimal = "." if v.rfind(".") > v.rfind(",") else ","
        miles = "," if decimal == "." else "."
        v = v.replace(miles, "").replace(decimal, ".")
    elif puntos > 1:
        v = v.replace(".", "")
    elif comas > 1:
        v = v.replace(",", "")
    elif comas == 1:
        entero, frac = v.split(",")
        v = entero + frac if (len(frac) == 3 and entero.lstrip("+-")) else f"{entero}.{frac}"
    elif puntos == 1:
        entero, frac = v.split(".")
        if con_moneda and len(frac) == 3 and entero.lstrip("+-"):
            v = entero + frac

    if not _RE_NUMERO.match(v):
        return None
    num = float(v)
    return -num if negativo else num
