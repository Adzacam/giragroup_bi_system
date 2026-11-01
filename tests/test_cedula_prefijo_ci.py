"""
tests/test_cedula_prefijo_ci.py
-------------------------------
Google Forms escribe la cédula como 'CI-4892019'. estudiante_de_fila la dejaba en 'CI4892019', que no es
una CI válida: el registro caía en estado C (sin CI) aunque la cédula estuviera en la fila.
"""

import pytest

from pipeline.normalization.fk_resolver import FKResolver
from services.extraccion_por_encabezado import campos_por_encabezado, estudiante_de_fila

LINEA_FORMS = ("Marca temporal: 2026-08-02 09:05:11 | Nombre Completo: Adriano Daza Camargo | "
               "Cédula de Identidad: {ci} | Teléfono: 72345678 | Ciudad: Cochabamba")


def _ci(valor):
    est = estudiante_de_fila(campos_por_encabezado(LINEA_FORMS.format(ci=valor).split(" | ")))
    return est["fk_resolucion"]["ci"]


@pytest.mark.parametrize("valor", ["CI-4892019", "ci-4892019", "CI 4892019", "Ci4892019", "C.I. 4892019", "ci: 4892019", "4892019"])
def test_prefijo_ci_no_forma_parte_de_la_cedula(valor):
    assert _ci(valor) == "4892019"


def test_extension_departamental_se_conserva():
    assert _ci("CI-4892019-LP") == "4892019LP"


def test_cedula_de_forms_queda_en_estado_a():
    res = FKResolver.__new__(FKResolver)  # sin padrón: solo la regla de CI válida
    res.padron_nombres, res.nombres_originales = {}, {}
    assert res.resolver_estudiante(nombre="Adriano Daza Camargo", ci_candidato=_ci("CI-4892019"))["fk_estado"] == "A"
