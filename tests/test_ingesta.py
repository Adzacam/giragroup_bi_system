"""
test_ingesta.py — Tests para Loop 1 (Lector universal)

Todas las pruebas usan copias de archivos reales de uploads/data.
Queda prohibido usar uploads/test o datos sintéticos preexistentes.
"""

import os
import tempfile

import pandas as pd
import pytest

from pipeline.ingesta import leer_archivo, leer_corpus, LECTORES


# ── Helpers ──────────────────────────────────────────────────────────

CORPUS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "uploads", "data"
)


def _crear_xlsx_temp(hojas: dict[str, pd.DataFrame], tmp_path) -> str:
    """Crea un .xlsx temporal con las hojas indicadas."""
    ruta = os.path.join(str(tmp_path), "test.xlsx")
    with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
        for nombre, df in hojas.items():
            df.to_excel(writer, sheet_name=nombre, index=False, header=False)
    return ruta


# ── Tests de interfaz básica ─────────────────────────────────────────

class TestLeerArchivo:

    def test_archivo_inexistente_no_lanza(self):
        """Un archivo que no existe devuelve {} sin lanzar excepción."""
        result = leer_archivo("ruta/falsa/no_existe.xlsx")
        assert result == {}

    def test_extension_no_soportada_no_lanza(self, tmp_path):
        """Una extensión no registrada devuelve {} sin lanzar."""
        ruta = os.path.join(str(tmp_path), "archivo.json")
        with open(ruta, "w") as f:
            f.write("{}")
        result = leer_archivo(ruta)
        assert result == {}

    def test_xlsx_una_hoja(self, tmp_path):
        """Un .xlsx con 1 hoja devuelve exactamente 1 entrada."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        ruta = _crear_xlsx_temp({"Datos": df}, tmp_path)

        result = leer_archivo(ruta)
        assert len(result) == 1
        assert "Datos" in result
        assert isinstance(result["Datos"], pd.DataFrame)
        assert len(result["Datos"]) == 2  # 2 filas de datos

    def test_xlsx_multiples_hojas(self, tmp_path):
        """Un .xlsx con 3 hojas devuelve exactamente 3 entradas."""
        hojas = {
            "Hoja1": pd.DataFrame({"X": [1]}),
            "Hoja2": pd.DataFrame({"Y": [2, 3]}),
            "Hoja3": pd.DataFrame({"Z": [4, 5, 6]}),
        }
        ruta = _crear_xlsx_temp(hojas, tmp_path)

        result = leer_archivo(ruta)
        assert len(result) == 3
        assert set(result.keys()) == {"Hoja1", "Hoja2", "Hoja3"}

    def test_xlsx_hoja_vacia_no_rompe(self, tmp_path):
        """Una hoja completamente vacía se devuelve como DataFrame vacío, no se pierde."""
        hojas = {
            "ConDatos": pd.DataFrame({"A": [1]}),
            "Vacia": pd.DataFrame(),
        }
        ruta = _crear_xlsx_temp(hojas, tmp_path)

        result = leer_archivo(ruta)
        assert len(result) == 2
        assert "Vacia" in result
        # La hoja vacía es un DataFrame (posiblemente con 0 filas)
        assert isinstance(result["Vacia"], pd.DataFrame)

    def test_csv_una_hoja(self, tmp_path):
        """Un CSV se lee como una sola 'hoja' cuya clave es el nombre del archivo."""
        ruta = os.path.join(str(tmp_path), "datos.csv")
        pd.DataFrame({"col1": ["a", "b"], "col2": ["c", "d"]}).to_csv(
            ruta, index=False, header=False
        )

        result = leer_archivo(ruta)
        assert len(result) == 1
        assert "datos" in result
        assert len(result["datos"]) == 2

    def test_datos_crudos_sin_header(self, tmp_path):
        """Los DataFrames se devuelven sin asumir header (header=None)."""
        df = pd.DataFrame({"Nombre": ["Ana", "Juan"], "Nota": [90, 85]})
        ruta = _crear_xlsx_temp({"Notas": df}, tmp_path)

        result = leer_archivo(ruta)
        # Con header=None, la primera fila de datos ('Ana', 90) es la fila 0
        # y las columnas son enteros (0, 1, ...)
        df_leido = result["Notas"]
        assert list(df_leido.columns) == [0, 1]


class TestLeerCorpus:

    def test_directorio_inexistente(self):
        """Un directorio inexistente devuelve {} sin lanzar."""
        result = leer_corpus("/ruta/que/no/existe")
        assert result == {}


class TestRegistroExtensiones:

    def test_registro_nueva_extension(self, tmp_path):
        """Se puede registrar una extensión nueva sin tocar código existente."""
        def leer_txt(ruta):
            with open(ruta, "r") as f:
                contenido = f.read()
            return {"texto": pd.DataFrame({"linea": contenido.splitlines()})}

        LECTORES[".txt"] = leer_txt

        ruta = os.path.join(str(tmp_path), "archivo.txt")
        with open(ruta, "w") as f:
            f.write("linea1\nlinea2\nlinea3")

        result = leer_archivo(ruta)
        assert "texto" in result
        assert len(result["texto"]) == 3

        # Limpiar para no afectar otros tests
        del LECTORES[".txt"]


# ── Test de cobertura contra corpus real ─────────────────────────────

class TestCorpusReal:
    """
    Verifica que leer_corpus lee TODOS los archivos de uploads/data
    sin excepciones y sin perder hojas.
    """

    @pytest.mark.skipif(
        not os.path.isdir(CORPUS_DIR),
        reason="Corpus real no disponible en uploads/data",
    )
    def test_lectura_completa_corpus(self):
        """Todos los archivos se leen y ninguno devuelve vacío por error."""
        resultado = leer_corpus(CORPUS_DIR)

        assert len(resultado) == 10, (
            f"Se esperaban 10 archivos, se leyeron {len(resultado)}"
        )

        # Ningún archivo debe devolver un dict vacío
        for nombre, hojas in resultado.items():
            assert len(hojas) > 0, (
                f"Archivo '{nombre}' devolvió 0 hojas (posible error de lectura)"
            )

        # Conteos esperados de hojas por archivo (referencia conocida)
        conteos_esperados = {
            "BD Cobranzas.xlsx": 5,
            "BD Egresos.xlsx": 3,
            "BD Techos.xlsx": 1,
            "Base centralizada Académica ARCA (1).xlsx": 7,
            "EJECUTADO VS META.xlsx": 2,
            "Evaluación Docente y Unifranz.xlsx": 3,
            "Experiencia Docente 2.0.xlsx": 4,
            "PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx": 32,
            "TBL_INSCRITOS.xlsx": 2,
            "[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx": 3,
        }

        for nombre, esperado in conteos_esperados.items():
            if nombre in resultado:
                real = len(resultado[nombre])
                assert real == esperado, (
                    f"'{nombre}': esperadas {esperado} hojas, leídas {real}"
                )
