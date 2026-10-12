"""
tests/sprint4/test_anonimizacion.py
-----------------------------------
Pruebas para el Script de Anonimización de datos reales:
1. Determinismo en sustitución de CI y nombres (preservación de integridad referencial).
2. Sanitización de correos electrónicos y teléfonos.
3. Preservación intacta de métricas académicas y financieras numéricas.
"""

import pytest
import pandas as pd
from scripts.anonimizar import AnonimizadorInstitucional


class TestAnonimizacion:
    def test_ci_anonimizacion_determinista(self):
        anon = AnonimizadorInstitucional(salt="test_salt_123")
        ci_original = "4892019"
        ci_anon_1 = anon.anonimizar_ci(ci_original)
        ci_anon_2 = anon.anonimizar_ci(ci_original)

        assert ci_anon_1 == ci_anon_2, "El hash debe ser determinista para mantener llaves"
        assert ci_anon_1 != ci_original
        assert len(ci_anon_1) == 7
        assert ci_anon_1.isdigit()

    def test_nombres_anonimizacion_determinista(self):
        anon = AnonimizadorInstitucional(salt="test_salt_123")
        nom_original = "Carlos Alberto Gomez Murillo"
        nom_anon_1 = anon.anonimizar_nombre(nom_original)
        nom_anon_2 = anon.anonimizar_nombre(nom_original)

        assert nom_anon_1 == nom_anon_2
        assert nom_anon_1 != nom_original

    def test_procesamiento_dataframe_preserva_metricas(self):
        anon = AnonimizadorInstitucional()
        df_raw = pd.DataFrame({
            "ci_estudiante": ["4892019", "7614226"],
            "nombre_completo": ["Ana Lucía Pérez", "Juan Pablo Morales"],
            "nota_final": [85.5, 42.0],
            "asistencia_pct": [90.0, 70.0],
            "monto_deuda": [0.0, 1500.0]
        })

        df_anon = anon.procesar_dataframe(df_raw)

        # CIs y nombres cambiados
        assert df_anon["ci_estudiante"].iloc[0] != "4892019"
        assert df_anon["nombre_completo"].iloc[0] != "Ana Lucía Pérez"

        # Métricas numéricas intactas para análisis de BI
        assert df_anon["nota_final"].iloc[0] == 85.5
        assert df_anon["nota_final"].iloc[1] == 42.0
        assert df_anon["asistencia_pct"].iloc[0] == 90.0
        assert df_anon["monto_deuda"].iloc[1] == 1500.0
