"""Parches de prueba para routers.dataops, que ahora está dividido por pasos.

Antes todo vivía en un solo módulo y bastaba parchear `dataops.nombre`. Hoy cada paso importa los nombres que usa,
así que el parche debe aplicarse en cada módulo donde el nombre existe para conservar el mismo comportamiento.
"""
import importlib

_MODULOS = ("", "._comun", ".extraccion", ".evaluacion", ".ingesta", ".lectura", ".revision", ".consolidacion", ".maestros")


def parchear(monkeypatch, nombre, valor):
    aplicados = 0
    for sufijo in _MODULOS:
        modulo = importlib.import_module("routers.dataops" + sufijo)
        if hasattr(modulo, nombre):
            monkeypatch.setattr(modulo, nombre, valor)
            aplicados += 1
    assert aplicados, f"routers.dataops no tiene el nombre {nombre!r}"
