"""
test_bloques_detector.py — Tests para Loop 2 (Detección de islas tabulares)

Valida la segmentación de bloques de datos dentro de hojas de forma
INDEPENDIENTE a la extracción o categorización (que es Loop 3).

Todas las pruebas con corpus real usan uploads/data.
Queda prohibido usar uploads/test o datos sintéticos preexistentes.
"""

import os

import numpy as np
import pandas as pd
import pytest

from pipeline.ingesta import detectar_islas, segmentar_archivo, leer_archivo


CORPUS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "uploads", "data"
)


# ── Tests con DataFrames controlados (copias manipuladas, no sintéticos preexistentes) ──

class TestDetectarIslas:

    def test_dataframe_vacio(self):
        """Un DataFrame vacío devuelve lista vacía de islas."""
        df = pd.DataFrame()
        islas = detectar_islas(df)
        assert islas == []

    def test_bloque_unico_sin_gaps(self):
        """Una hoja con datos continuos (sin filas vacías) es 1 sola isla."""
        df = pd.DataFrame({
            0: ["POS", "POS-001", "POS-002", "POS-003"],
            1: ["Nombre", "Ana", "Juan", "María"],
        })
        islas = detectar_islas(df)
        assert len(islas) == 1
        assert islas[0]["fila_inicio"] == 0
        assert islas[0]["fila_fin"] == 3
        assert islas[0]["n_filas"] == 4
        assert islas[0]["es_ruido"] is False

    def test_dos_islas_separadas_por_gap(self):
        """Dos tablas separadas por ≥2 filas vacías se detectan como 2 islas."""
        # Tabla 1: filas 0-2, gap en filas 3-4, Tabla 2: filas 5-7
        filas = [
            ["POS", "Nombre"],
            ["POS-001", "Ana"],
            ["POS-002", "Juan"],
            [np.nan, np.nan],      # gap fila 3
            [np.nan, np.nan],      # gap fila 4
            ["Módulo", "Nota"],
            ["Matemáticas", "90"],
            ["Física", "85"],
        ]
        df = pd.DataFrame(filas)
        islas = detectar_islas(df)

        assert len(islas) == 2
        # Isla 0
        assert islas[0]["fila_inicio"] == 0
        assert islas[0]["fila_fin"] == 2
        assert islas[0]["n_filas"] == 3
        assert islas[0]["es_ruido"] is False
        # Isla 1
        assert islas[1]["fila_inicio"] == 5
        assert islas[1]["fila_fin"] == 7
        assert islas[1]["n_filas"] == 3
        assert islas[1]["es_ruido"] is False

    def test_gap_de_1_fila_no_separa(self):
        """Una sola fila vacía NO es suficiente para cortar (gap_threshold=2)."""
        filas = [
            ["A", "B"],
            ["1", "2"],
            [np.nan, np.nan],  # 1 sola fila vacía
            ["3", "4"],
        ]
        df = pd.DataFrame(filas)
        islas = detectar_islas(df)

        assert len(islas) == 1, "Un gap de 1 fila no debería separar"
        assert islas[0]["n_filas"] == 4  # incluye la fila vacía intermedia

    def test_bloque_de_1_fila_es_ruido(self):
        """Un bloque con menos de MIN_FILAS_ISLA filas se marca como ruido."""
        filas = [
            ["Encabezado suelto"],
            [np.nan],
            [np.nan],
            ["Dato 1"],
            ["Dato 2"],
            ["Dato 3"],
        ]
        df = pd.DataFrame(filas)
        islas = detectar_islas(df)

        assert len(islas) == 2
        assert islas[0]["n_filas"] == 1
        assert islas[0]["es_ruido"] is True
        assert islas[1]["n_filas"] == 3
        assert islas[1]["es_ruido"] is False

    def test_tres_islas_con_gaps_variables(self):
        """Tres bloques con gaps de distinto tamaño (todos ≥2)."""
        filas = [
            ["A1"], ["A2"],                 # isla 0
            [np.nan], [np.nan],             # gap=2
            ["B1"], ["B2"], ["B3"],          # isla 1
            [np.nan], [np.nan], [np.nan],   # gap=3
            ["C1"], ["C2"],                 # isla 2
        ]
        df = pd.DataFrame(filas)
        islas = detectar_islas(df)

        assert len(islas) == 3
        assert islas[0]["n_filas"] == 2
        assert islas[1]["n_filas"] == 3
        assert islas[2]["n_filas"] == 2

    def test_filas_solo_whitespace_son_vacias(self):
        """Filas con solo espacios/tabs se consideran vacías."""
        filas = [
            ["Dato real"],
            ["   ", "\t"],      # whitespace
            ["", "  "],         # whitespace
            ["Otro dato real"],
        ]
        df = pd.DataFrame(filas)
        islas = detectar_islas(df)

        assert len(islas) == 2
        assert islas[0]["n_filas"] == 1
        assert islas[1]["n_filas"] == 1

    def test_hoja_completamente_vacia(self):
        """Una hoja donde todas las filas son vacías devuelve 0 islas."""
        df = pd.DataFrame({
            0: [np.nan, np.nan, np.nan],
            1: [np.nan, np.nan, np.nan],
        })
        islas = detectar_islas(df)
        assert islas == []

    def test_subdataframes_tienen_datos_correctos(self):
        """Los sub-DataFrames de cada isla contienen exactamente los datos esperados."""
        filas = [
            ["X", "10"],
            ["Y", "20"],
            [np.nan, np.nan],
            [np.nan, np.nan],
            ["Z", "30"],
        ]
        df = pd.DataFrame(filas)
        islas = detectar_islas(df)

        assert len(islas) == 2
        # Isla 0: filas con X,Y
        df0 = islas[0]["df"]
        assert list(df0.iloc[0]) == ["X", "10"]
        assert list(df0.iloc[1]) == ["Y", "20"]
        # Isla 1: fila con Z
        df1 = islas[1]["df"]
        assert list(df1.iloc[0]) == ["Z", "30"]

    def test_gap_al_inicio_y_al_final(self):
        """Filas vacías al inicio y al final de la hoja no generan islas fantasma."""
        filas = [
            [np.nan, np.nan],
            [np.nan, np.nan],
            ["Dato", "1"],
            ["Dato", "2"],
            [np.nan, np.nan],
            [np.nan, np.nan],
        ]
        df = pd.DataFrame(filas)
        islas = detectar_islas(df)

        assert len(islas) == 1
        assert islas[0]["fila_inicio"] == 2
        assert islas[0]["fila_fin"] == 3
        assert islas[0]["n_filas"] == 2


class TestSegmentarArchivo:

    def test_multiples_hojas(self):
        """segmentar_archivo procesa todas las hojas del dict."""
        hojas = {
            "Hoja1": pd.DataFrame([["A"], [np.nan], [np.nan], ["B"]]),
            "Hoja2": pd.DataFrame([["C"], ["D"]]),
        }
        resultado = segmentar_archivo(hojas)

        assert "Hoja1" in resultado
        assert "Hoja2" in resultado
        assert len(resultado["Hoja1"]) == 2  # 2 islas
        assert len(resultado["Hoja2"]) == 1  # 1 isla


# ── Test de validación contra corpus real ────────────────────────────

class TestCorpusRealBloques:
    """
    Verifica la detección de islas sobre hojas reales conocidas.
    Centralizado_Mensual en PLANIFICACION es la hoja más compleja
    del corpus — tiene múltiples islas apiladas verticalmente.
    """

    @pytest.mark.skipif(
        not os.path.isdir(CORPUS_DIR),
        reason="Corpus real no disponible en uploads/data",
    )
    def test_centralizado_mensual_tiene_multiples_islas(self):
        """La hoja Centralizado_Mensual debe tener >1 isla."""
        ruta = os.path.join(
            CORPUS_DIR,
            "PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx",
        )
        hojas = leer_archivo(ruta)
        assert "Centralizado_Mensual" in hojas

        islas = detectar_islas(hojas["Centralizado_Mensual"])
        assert len(islas) > 1, (
            f"Centralizado_Mensual debería tener múltiples islas, "
            f"pero se detectaron {len(islas)}"
        )

        # Al menos una isla debe ser válida (no ruido)
        validas = [i for i in islas if not i["es_ruido"]]
        assert len(validas) >= 1

        # Reportar las islas detectadas para verificación manual
        for isla in islas:
            print(
                f"  Isla {isla['indice']}: "
                f"filas {isla['fila_inicio']}-{isla['fila_fin']}, "
                f"{isla['n_filas']} filas, "
                f"ruido={isla['es_ruido']}"
            )

    @pytest.mark.skipif(
        not os.path.isdir(CORPUS_DIR),
        reason="Corpus real no disponible en uploads/data",
    )
    def test_hojas_simples_son_1_isla(self):
        """Hojas con datos continuos (sin gaps) deben dar exactamente 1 isla."""
        ruta = os.path.join(CORPUS_DIR, "BD Techos.xlsx")
        hojas = leer_archivo(ruta)
        assert len(hojas) == 1

        nombre_hoja = list(hojas.keys())[0]
        islas = detectar_islas(hojas[nombre_hoja])
        assert len(islas) == 1, (
            f"BD Techos (hoja simple) debería tener 1 isla, "
            f"pero se detectaron {len(islas)}"
        )
        assert islas[0]["es_ruido"] is False

    @pytest.mark.skipif(
        not os.path.isdir(CORPUS_DIR),
        reason="Corpus real no disponible en uploads/data",
    )
    def test_ninguna_hoja_del_corpus_falla(self):
        """La detección de islas no lanza excepciones en ningún archivo del corpus."""
        from pipeline.ingesta import leer_corpus

        corpus = leer_corpus(CORPUS_DIR)
        total_islas = 0
        total_ruido = 0

        for nombre_archivo, hojas in corpus.items():
            bloques = segmentar_archivo(hojas)
            for nombre_hoja, islas in bloques.items():
                for isla in islas:
                    total_islas += 1
                    if isla["es_ruido"]:
                        total_ruido += 1

        assert total_islas > 0, "El corpus debería producir al menos 1 isla"
        print(
            f"\nCorpus completo: {total_islas} isla(s) detectada(s), "
            f"{total_ruido} ruido, "
            f"{total_islas - total_ruido} válida(s)"
        )
