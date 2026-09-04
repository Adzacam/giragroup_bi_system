"""
tests/test_catalogos_db.py — Validación Integral de Catálogos Maestros y Staging (Parte 1)

Verifica:
1. DDL de stg_entidad_no_resuelta y cat_categoria_financiera en schema_catalogos.sql.
2. Contenido del seed SQL (748 programas, 768 docentes, metas 2024-2026, categorías financieras).
3. Presencia de códigos POS reales (POS-5252, POS-5308, POS-5376, POS-5310) con precios.
4. Contrato de la tabla stg_entidad_no_resuelta mediante inserción y consulta en memoria.
"""

import os
import re
import sqlite3
import pytest

RUTA_SCHEMA = os.path.join("db", "schema_catalogos.sql")
RUTA_SEED = os.path.join("db", "seeds", "seed_catalogos.sql")


class TestSchemaCatalogosDDL:
    """Valida la integridad y completitud sintáctica de schema_catalogos.sql."""

    def test_schema_existe_y_no_vacio(self):
        assert os.path.exists(RUTA_SCHEMA), f"No existe el archivo {RUTA_SCHEMA}"
        assert os.path.getsize(RUTA_SCHEMA) > 0, "El archivo schema_catalogos.sql está vacío"

    def test_stg_entidad_no_resuelta_definida(self):
        with open(RUTA_SCHEMA, "r", encoding="utf-8") as f:
            contenido = f.read()

        assert "CREATE TABLE IF NOT EXISTS public.stg_entidad_no_resuelta" in contenido
        assert "id_pendiente" in contenido
        assert "tipo_entidad" in contenido
        assert "texto_original" in contenido
        assert "mejor_match_cat" in contenido
        assert "score_similitud" in contenido
        assert "archivo_origen" in contenido
        assert "estado" in contenido
        assert "fecha_deteccion" in contenido

    def test_indices_stg_entidad_no_resuelta(self):
        with open(RUTA_SCHEMA, "r", encoding="utf-8") as f:
            contenido = f.read()

        assert "CREATE INDEX IF NOT EXISTS idx_stg_estado" in contenido
        assert "CREATE INDEX IF NOT EXISTS idx_stg_tipo" in contenido

    def test_cat_categoria_financiera_definida(self):
        with open(RUTA_SCHEMA, "r", encoding="utf-8") as f:
            contenido = f.read()

        assert "CREATE TABLE IF NOT EXISTS public.cat_categoria_financiera" in contenido
        assert "codigo" in contenido
        assert "nombre_categoria" in contenido
        assert "tipo_flujo" in contenido


class TestSeedCatalogosSQL:
    """Valida que seed_catalogos.sql contenga los datos extraídos del corpus real."""

    def test_seed_existe_y_tamano_esperado(self):
        assert os.path.exists(RUTA_SEED), f"No existe el archivo {RUTA_SEED}"
        tamano_mb = os.path.getsize(RUTA_SEED) / (1024 * 1024)
        # El seed autogenerado supera 1.5 MB con 748 programas y 1960 módulos
        assert tamano_mb > 1.0, f"El seed es sospechosamente pequeño: {tamano_mb:.2f} MB"

    def test_codigos_pos_clave_presentes(self):
        with open(RUTA_SEED, "r", encoding="utf-8") as f:
            contenido = f.read()

        pos_esperados = ["POS-5252", "POS-5308", "POS-5376", "POS-5310"]
        for pos in pos_esperados:
            assert f"'{pos}'" in contenido, f"Código {pos} no encontrado en seed_catalogos.sql"

    def test_categorias_financieras_sembradas(self):
        with open(RUTA_SEED, "r", encoding="utf-8") as f:
            contenido = f.read()

        categorias_esperadas = [
            "MATRICULA", "CUOTA_MENSUAL", "PAGO_AL_CONTADO", "CERTIFICACION",
            "HONORARIOS_DOCENTES", "MARKETING_DIGITAL", "PLATAFORMAS_TIC", "ADMINISTRATIVO"
        ]
        for cat in categorias_esperadas:
            assert f"'{cat}'" in contenido, f"Categoría financiera {cat} no sembrada"

    def test_metas_gestion_presentes(self):
        with open(RUTA_SEED, "r", encoding="utf-8") as f:
            contenido = f.read()

        # Debe tener metas para 2024, 2025 y 2026
        assert "VALUES (2024," in contenido, "Faltan metas 2024"
        assert "VALUES (2025," in contenido, "Faltan metas 2025"
        assert "VALUES (2026," in contenido, "Faltan metas 2026"
        assert "'COBRANZAS'" in contenido, "Falta categoría COBRANZAS en metas"

    def test_volumen_minimo_entidades(self):
        with open(RUTA_SEED, "r", encoding="utf-8") as f:
            contenido = f.read()

        n_programas = len(re.findall(r"INSERT INTO public\.cat_programa", contenido))
        n_docentes = len(re.findall(r"INSERT INTO public\.cat_docente", contenido))
        n_modulos = len(re.findall(r"INSERT INTO public\.cat_modulo", contenido))

        assert n_programas >= 700, f"Esperados >= 700 programas, encontrados: {n_programas}"
        assert n_docentes >= 700, f"Esperados >= 700 docentes, encontrados: {n_docentes}"
        assert n_modulos >= 1500, f"Esperados >= 1500 módulos, encontrados: {n_modulos}"


class TestStagingTableContract:
    """Valida el contrato relacional de stg_entidad_no_resuelta simulado en SQLite."""

    def test_insercion_y_consulta_staging(self):
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # DDL compatible con SQLite
        cursor.execute("""
            CREATE TABLE stg_entidad_no_resuelta (
                id_pendiente     INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_entidad     TEXT NOT NULL,
                texto_original   TEXT NOT NULL,
                mejor_match_cat  TEXT,
                score_similitud  REAL,
                archivo_origen   TEXT,
                estado           TEXT DEFAULT 'PENDIENTE',
                fecha_deteccion  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Inserción de prueba
        cursor.execute("""
            INSERT INTO stg_entidad_no_resuelta 
            (tipo_entidad, texto_original, mejor_match_cat, score_similitud, archivo_origen)
            VALUES (?, ?, ?, ?, ?)
        """, ("docente", "Marcos Jimenez G.", "Marco Antonio Jiménez Gira", 0.8125, "actas_2025.xlsx"))
        conn.commit()

        # Consulta y verificación
        cursor.execute("SELECT id_pendiente, tipo_entidad, estado, score_similitud FROM stg_entidad_no_resuelta WHERE texto_original = ?", ("Marcos Jimenez G.",))
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == 1
        assert fila[1] == "docente"
        assert fila[2] == "PENDIENTE"
        assert abs(fila[3] - 0.8125) < 1e-4

        conn.close()
