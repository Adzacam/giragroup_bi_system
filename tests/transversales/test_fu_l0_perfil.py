"""
Pruebas de FU-L0: perfil de fuentes sin PII y catálogo config/mapeo_fuentes.yaml.

Los libros de prueba se crean en tmp_path con datos ficticios. No se lee uploads/data.
"""

import importlib.util
import json
import re
from pathlib import Path

import openpyxl
import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
RUTA_SCRIPT = BASE_DIR / "scripts" / "auditoria_fuentes" / "perfil_fuentes.py"
RUTA_MAPEO = BASE_DIR / "config" / "mapeo_fuentes.yaml"

# Datos ficticios: deben desaparecer de cualquier salida del perfil.
CORREOS_FICTICIOS = ["persona.ficticia1@ejemplo.test", "persona.ficticia2@ejemplo.test"]
CIS_FICTICIOS = ["1234567", "7654321"]
NOMBRES_FICTICIOS = ["Ana Ficticia Ruiz", "Luis Prueba Gomez"]


def cargar_script():
    spec = importlib.util.spec_from_file_location("perfil_fuentes", RUTA_SCRIPT)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def perfil_mod():
    return cargar_script()


@pytest.fixture
def libro_sintetico(tmp_path):
    """Libro con una hoja visible (cabecera en fila 3, subtotal, fantasma, combinada, fórmula,
    duplicada y columnas personales) y una hoja oculta."""
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws["A1"] = "Reporte de prueba"
    ws.merge_cells("A1:E1")
    # Cabecera en la fila 3; una columna se llama con un correo para probar el enmascarado.
    cabecera = ["Nombre", "CI", "Programa", "Nota", CORREOS_FICTICIOS[0]]
    for col, texto in enumerate(cabecera, start=1):
        ws.cell(row=3, column=col, value=texto)
    filas = [
        (NOMBRES_FICTICIOS[0], CIS_FICTICIOS[0], "Programa A", 80, "x"),
        (NOMBRES_FICTICIOS[1], CIS_FICTICIOS[1], "Programa B", "Aprobó", "y"),
        (NOMBRES_FICTICIOS[0], CIS_FICTICIOS[0], "Programa A", 80, "x"),  # duplicada exacta de la primera
        ("TOTAL", None, None, "=SUM(D4:D6)", None),                       # subtotal con fórmula
        (None, None, None, None, None),                                    # fila vacía
        ("Ana Prueba", "9999999", "Programa C", 90, "z"),
    ]
    for i, fila in enumerate(filas, start=4):
        for col, valor in enumerate(fila, start=1):
            if valor is not None:
                ws.cell(row=i, column=col, value=valor)

    oculta = wb.create_sheet("Copia de Datos")
    oculta["A1"] = "Copia"
    oculta["A2"] = "x"
    oculta.sheet_state = "hidden"

    ruta = entrada / "sintetico.xlsx"
    wb.save(ruta)
    return entrada


def test_perfil_cuenta_hojas_y_estados(perfil_mod, libro_sintetico):
    resultado, filas = perfil_mod.perfilar_directorio(libro_sintetico)
    assert resultado["n_libros"] == 1
    assert resultado["n_hojas"] == 2
    assert resultado["estados"]["visible"] == 1
    assert resultado["estados"]["hidden"] == 1
    assert len(filas) == 2


def test_perfil_detecta_cabecera_subtotal_combinada_formula_y_duplicada(perfil_mod, libro_sintetico):
    resultado, _ = perfil_mod.perfilar_directorio(libro_sintetico)
    hojas = {h["hoja"]: h for h in resultado["hojas"]}
    datos = hojas["Datos"]
    assert datos["estado"] == "visible"
    assert datos["cabecera_fila"] == 3
    assert datos["n_combinadas"] == 1
    assert datos["n_formulas"] == 1
    assert datos["n_formulas_sin_valor"] == 1
    assert datos["filas_subtotal"] == 1
    assert datos["filas_vacias"] == 1
    assert datos["filas_duplicadas"] == 1
    assert datos["n_filas_datos"] == 4  # 6 filas - 1 subtotal - 1 vacía

    oculta = hojas["Copia de Datos"]
    assert oculta["estado"] == "hidden"


def test_columnas_personales_no_tienen_vocabulario_y_programa_si(perfil_mod, libro_sintetico):
    resultado, _ = perfil_mod.perfilar_directorio(libro_sintetico)
    datos = next(h for h in resultado["hojas"] if h["hoja"] == "Datos")
    columnas = {c["nombre"]: c for c in datos["columnas"]}
    assert columnas["Nombre"]["pii"] is True
    assert columnas["Nombre"]["vocabulario"] is None
    assert columnas["CI"]["pii"] is True
    assert columnas["CI"]["vocabulario"] is None
    assert columnas["Programa"]["pii"] is False
    assert set(columnas["Programa"]["vocabulario"]) == {"Programa A", "Programa B", "Programa C"}
    assert columnas["Nota"]["tipos_mezclados"] is True


def test_cabecera_con_correo_se_enmascara(perfil_mod, libro_sintetico):
    resultado, _ = perfil_mod.perfilar_directorio(libro_sintetico)
    datos = next(h for h in resultado["hojas"] if h["hoja"] == "Datos")
    assert CORREOS_FICTICIOS[0] not in datos["cabecera_nombres"]
    assert any(n.startswith("<enmascarado_col_") for n in datos["cabecera_nombres"])


def test_json_con_claves_esperadas_y_sin_pii(perfil_mod, libro_sintetico, tmp_path):
    salida = tmp_path / "salida"
    codigo = perfil_mod.main(["--entrada", str(libro_sintetico), "--salida", str(salida)])
    assert codigo == 0

    ruta_json = salida / "fu_l0_perfil.json"
    ruta_csv = salida / "fu_l0_hojas.csv"
    assert ruta_json.exists() and ruta_csv.exists()

    texto = ruta_json.read_text(encoding="utf-8")
    datos = json.loads(texto)
    for clave in ("entrada", "fecha_perfil", "n_libros", "n_hojas", "estados", "errores_lectura", "reglas", "hojas"):
        assert clave in datos
    hoja = datos["hojas"][0]
    for clave in ("archivo", "hoja", "estado", "filas_x_columnas", "cabecera_fila", "cabecera_nombres",
                  "n_combinadas", "n_formulas", "filas_vacias", "filas_subtotal", "filas_duplicadas",
                  "columnas"):
        assert clave in hoja
    assert {"nombre", "pct_nulos", "tipos", "pii", "vocabulario"} <= set(hoja["columnas"][0].keys())

    for valor in CORREOS_FICTICIOS + CIS_FICTICIOS + NOMBRES_FICTICIOS:
        assert valor not in texto, "el perfil publica un dato personal de prueba"
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texto)

    filas_csv = ruta_csv.read_text(encoding="utf-8").strip().splitlines()
    assert len(filas_csv) == 3  # cabecera + 2 hojas


def test_script_no_contiene_nombres_de_libro_ni_de_hoja():
    codigo = RUTA_SCRIPT.read_text(encoding="utf-8")
    for nombre in ("BD Cobranzas", "COBRANZAS 2024", "TBL_INSCRITOS", "EJECUTADO VS META", "ACTAS DE NOTAS"):
        assert nombre not in codigo


def test_mapeo_fuentes_carga_y_cada_tipo_tiene_campos_canonicos():
    assert RUTA_MAPEO.exists()
    datos = yaml.safe_load(RUTA_MAPEO.read_text(encoding="utf-8"))
    tipos = datos["tipos_fuente"]
    esperados = {"COBRANZA", "ACTA", "EVALUACION_DOCENTE", "MARKETING", "EGRESOS",
                 "RENTABILIDAD", "TECHOS", "PLANIFICACION"}
    assert set(tipos) == esperados

    canonicos = set(datos["campos_canonicos"])
    minimos = {"estado_cartera_fuente", "cuotas_en_mora", "dias_mora", "monto_pago_mes", "estado_academico",
               "nota_modulo", "leads_captacion", "inscritos_captacion", "reservas", "puntuacion",
               "escala_max", "monto_meta", "monto_ejecutado", "ci", "pos", "programa", "genero"}
    assert minimos <= canonicos

    for tipo, spec in tipos.items():
        assert spec.get("campos"), f"{tipo} sin campos canónicos"
        for campo, cfg in spec["campos"].items():
            assert campo in canonicos, f"{tipo}.{campo} no está en campos_canonicos"
            for sin in cfg.get("sinonimos", []):
                assert ("texto" in sin) != ("patron" in sin), f"{tipo}.{campo}: un sinónimo necesita texto o patron"
                if "patron" in sin:
                    re.compile(sin["patron"])
                if "texto" in sin:
                    assert sin["texto"] == sin["texto"].lower(), "los sinónimos van normalizados en minúsculas"

    cubiertos = {c for spec in tipos.values() for c in spec["campos"]}
    assert minimos <= cubiertos | {"escala_max"}


def test_hoja_de_una_sola_fila_no_publica_su_contenido(perfil_mod, tmp_path):
    """Una hoja con una fila y sin cuerpo es un registro residual: solo se publica su ancho."""
    entrada = tmp_path / "entrada_residual"
    entrada.mkdir()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Residual"
    registro = [NOMBRES_FICTICIOS[0], "Zona ficticia calle 1 nro 10", "1986-09-13", "Programa A", "ACTIVO"]
    for col, valor in enumerate(registro, start=1):
        ws.cell(row=1, column=col, value=valor)
    wb.save(entrada / "residual.xlsx")

    resultado, _ = perfil_mod.perfilar_directorio(entrada)
    hoja = resultado["hojas"][0]
    texto = json.dumps(resultado, ensure_ascii=False)
    for valor in registro:
        assert valor not in texto
    assert len(hoja["cabecera_nombres"]) == len(registro)
    assert hoja["n_filas_datos"] == 0
