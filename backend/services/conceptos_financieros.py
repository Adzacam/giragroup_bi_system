"""
Cabecera de una columna financiera -> concepto canónico (EGRESO_ANTERIOR, EGRESO_REAL, INGRESO, RENTABILIDAD).

No depende de un archivo: combina reglas por palabra clave con los sinónimos de
cat_historico_equivalencia (giragroup_catalog_db), de modo que una cabecera nueva se aprende
agregando su sinónimo al catálogo, sin tocar código.

Las columnas en moneda secundaria (DOLARES, USD, $us) y los porcentajes son derivadas: no se mapean.
"""

import os
import unicodedata
from functools import lru_cache
from typing import Dict, Optional

CONCEPTOS_COSTO = ("EGRESO_ANTERIOR", "EGRESO_REAL", "INGRESO", "RENTABILIDAD")

# Orden importa: 'EGRESO ANTERIOR' antes que 'EGRESO'
_REGLAS = (
    ("EGRESO_ANTERIOR", ("EGRESO ANTERIOR", "GASTO ANTERIOR", "COSTO ANTERIOR")),
    ("EGRESO_REAL", ("EGRESO REAL", "EGRESO", "EGRESOS", "GASTO REAL", "GASTO EJECUTADO", "COSTO EJECUTADO")),
    ("INGRESO", ("INGRESO", "INGRESOS", "RECAUDACION", "RECAUDADO")),
    ("RENTABILIDAD", ("RENTABILIDAD", "UTILIDAD", "MARGEN")),
)
_MARCAS_DERIVADA = ("DOLAR", "USD", "$US", "US$", "%", "PORCENTAJE", "TIPO DE CAMBIO")
# Concepto del catálogo -> concepto de costo (TOTAL_PAGADO no: también nombra pagos de estudiantes)
_CATALOGO_A_CONCEPTO = {"EGRESO_ANTERIOR": "EGRESO_ANTERIOR", "EGRESO_REAL": "EGRESO_REAL", "RENTABILIDAD": "RENTABILIDAD"}


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.upper().split())


@lru_cache(maxsize=1)
def _sinonimos_catalogo() -> Dict[str, str]:
    """termino_origen normalizado -> concepto, desde cat_historico_equivalencia. Vacío si el catálogo no responde."""
    if os.getenv("TESTING") == "true" or os.getenv("APP_ENV") == "test":
        return {}
    try:
        from core.database import CatalogSessionLocal
        from models.catalogos import CatConceptoFinanciero, CatHistoricoEquivalencia
    except Exception:
        return {}
    sinonimos: Dict[str, str] = {}
    db = CatalogSessionLocal()
    try:
        filas = (
            db.query(CatHistoricoEquivalencia.termino_origen, CatConceptoFinanciero.nombre_canonico)
            .join(CatConceptoFinanciero, CatConceptoFinanciero.id_concepto == CatHistoricoEquivalencia.id_concepto)
            .all()
        )
        for termino, canonico in filas:
            concepto = _CATALOGO_A_CONCEPTO.get(canonico)
            t = _normalizar(termino)
            if concepto and not any(m in t for m in _MARCAS_DERIVADA):
                sinonimos[t] = concepto
    except Exception:
        return {}
    finally:
        db.close()
    return sinonimos


def concepto_de_cabecera(encabezado: str) -> Optional[str]:
    """Concepto de costo de una cabecera, o None si no es una columna de costo en moneda base."""
    h = _normalizar(encabezado)
    if not h or any(m in h for m in _MARCAS_DERIVADA):
        return None
    if h in _sinonimos_catalogo():
        return _sinonimos_catalogo()[h]
    for concepto, claves in _REGLAS:
        if any(h == k or h.startswith(k + " ") for k in claves):
            return concepto
    return None
