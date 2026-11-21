"""
backend/services/regla_mora.py
------------------------------
Regla única de mora (DA3, decisión de Lean, 2026-11-20): un hecho de situación financiera está en mora
si `cuotas_impagas >= 2`. La misma regla rige en las vistas `bi` (migración 022) y en los servicios
(KPIService, risk_service, dw_loader). El estado de cartera que trae la fuente (`estado_cartera_fuente`)
es solo descriptivo y no decide la mora.

El umbral se lee del catálogo de mapeo (`tipos_fuente.COBRANZA.regla_mora.umbral_cuotas`); si el
catálogo no responde, vale 2.
"""

from __future__ import annotations

from typing import Optional

UMBRAL_POR_DEFECTO = 2

ESTADO_MORA = "Mora"
ESTADO_VIGENTE = "Vigente"


def _umbral_catalogo() -> int:
    try:
        from pipeline.lector_hojas import cargar_config
        cfg = cargar_config()
        valor = (((cfg.get("tipos_fuente") or {}).get("COBRANZA") or {}).get("regla_mora") or {}).get("umbral_cuotas")
        return int(valor) if valor is not None else UMBRAL_POR_DEFECTO
    except Exception:  # catálogo ausente o ilegible: rige el valor de DA3
        return UMBRAL_POR_DEFECTO


UMBRAL_CUOTAS_MORA = _umbral_catalogo()


def es_mora(cuotas_impagas: Optional[int], umbral: Optional[int] = None) -> bool:
    """True si las cuotas impagas del hecho alcanzan el umbral de DA3. None (sin dato) no es mora."""
    if cuotas_impagas is None:
        return False
    return int(cuotas_impagas) >= (UMBRAL_CUOTAS_MORA if umbral is None else int(umbral))


def estado_cartera_da3(cuotas_impagas: Optional[int]) -> Optional[str]:
    """Estado derivado por DA3 ('Mora' / 'Vigente'). None si el hecho no trae cuotas (p. ej. un pago mensual)."""
    if cuotas_impagas is None:
        return None
    return ESTADO_MORA if es_mora(cuotas_impagas) else ESTADO_VIGENTE
