"""
tests/test_pipeline_financiero.py
---------------------------------
Regresión de la carga de cobranzas (BD_Cobranzas_giraGroup.xlsx):
1. El serializador toma como encabezado la primera fila con ≥ 2 celdas (no el título de hoja).
2. Los campos financieros se leen por encabezado, aunque se omitan celdas vacías.
3. Antes, la heurística posicional cargaba el CI como deuda y nunca asignaba monto_pagado.
"""

import pandas as pd

from services.ingestion_service import IngestionService
from routers.pipeline import _campos_financieros_por_encabezado, _resolver_fila_financiera
from services.dw_loader import _es_nombre_incompleto


def _bloque_cobranzas() -> pd.DataFrame:
    return pd.DataFrame([
        ["giraGroup — BD COBRANZAS", None, None, None, None, None, None, None],
        ["POS", "NOMBRE DEL PROGRAMA", "CI", "NOMBRES", "PATERNO", "DEUDA TOTAL", "TOTAL PAGADO HASTA LA FECHA", "TOTAL CUOTAS EN MORA"],
        ["POS-4939", "CURSO EXCEL", "13441152", "ROBERTO JOSE", "VARGAS", 1250, 1250, 3],
        ["POS-4940", None, "5437923", "VERONICA", "ROJAS", 750, None, 0],  # celdas vacías
    ])


def _filas(texto: str):
    resultado = []
    for linea in texto.split("\n"):
        campos = _campos_financieros_por_encabezado([c.strip() for c in linea.split("|")])
        if campos:
            resultado.append(_resolver_fila_financiera(campos))
    return resultado


class TestSerializacionConEncabezados:
    def test_salta_fila_de_titulo(self):
        texto = IngestionService.serializar_bloque_con_encabezados(_bloque_cobranzas())
        lineas = texto.split("\n")

        assert len(lineas) == 2
        assert "giraGroup" not in texto
        assert "CI: 13441152" in lineas[0]
        assert "DEUDA TOTAL: 1250" in lineas[0]


class TestResolucionFinanciera:
    def test_campos_por_encabezado(self):
        filas = _filas(IngestionService.serializar_bloque_con_encabezados(_bloque_cobranzas()))

        primera = filas[0]
        assert primera["estudiante"]["fk_resolucion"]["ci"] == "13441152"
        assert primera["estudiante"]["fk_resolucion"]["nombre_resuelto"] == "ROBERTO JOSE VARGAS"
        assert primera["monto_deuda"] == 1250.0
        assert primera["monto_pagado"] == 1250.0
        assert primera["cuotas_impagas"] == 3
        assert primera["programa"] == {"valor_extraido": "CURSO EXCEL"}

    def test_celdas_vacias_no_desplazan_campos(self):
        segunda = _filas(IngestionService.serializar_bloque_con_encabezados(_bloque_cobranzas()))[1]

        assert segunda["estudiante"]["fk_resolucion"]["ci"] == "5437923"
        assert segunda["monto_deuda"] == 750.0
        assert segunda["monto_pagado"] is None
        assert segunda["programa"] is None

    def test_fila_sin_encabezados_usa_heuristica(self):
        assert _campos_financieros_por_encabezado(["POS-1", "13441152", "1250"]) is None

    def test_fila_con_encabezados_sin_montos_se_omite(self):
        """Hojas de congelados o resúmenes: traen CI y nombre, pero no son hechos financieros."""
        celdas = ["POS: POS-5239", "CI: 10651174", "NOMBRES: ROBERTO JOSE", "INSCRITOS: 31"]
        assert _campos_financieros_por_encabezado(celdas) == {}


class TestNombreIncompleto:
    def test_nombre_de_pila_guardado_es_la_misma_persona(self):
        assert _es_nombre_incompleto("ROBERTO JOSE", "ROBERTO JOSE VARGAS PORTUGAL")
        assert _es_nombre_incompleto("Sofía Alejandra", "SOFIA ALEJANDRA MENDOZA MONTAÑO")

    def test_nombre_distinto_o_igual_no_se_considera_incompleto(self):
        assert not _es_nombre_incompleto("RODRIGO MEDINA", "PEDRO PABLO CONDORI PEREZ")
        assert not _es_nombre_incompleto("ROBERTO JOSE", "ROBERTO JOSE")
        assert not _es_nombre_incompleto("", "ROBERTO JOSE")
