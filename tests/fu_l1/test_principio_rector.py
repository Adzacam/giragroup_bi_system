"""
FU-L1: prueba arquitectónica del principio rector #1 (PLAN_FUENTES_UPLOADS.md).

«Sin nombres de archivo ni de hoja en el código»: recorre backend/ y pipeline/ (sin .venv, tests ni
__pycache__) y falla si un literal de cadena del código es el nombre de un libro o de una hoja de
uploads/data. La lista sale de docs/mediciones/fu_l0_hojas.csv (perfil de FU-L0).

Qué cuenta como uso:
- un literal igual al nombre (o al nombre con su extensión), y
- un literal que contiene un nombre distintivo (con espacio, guion bajo o dígito, de 8 caracteres o más).
Los docstrings y las cadenas sueltas (documentación) no cuentan: no hacen depender el código del nombre.
"""

import ast
import csv
import os
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CSV_HOJAS = RAIZ / "docs" / "mediciones" / "fu_l0_hojas.csv"
CARPETAS = ("backend", "pipeline")
EXCLUIR_DIRS = {".venv", "venv", "tests", "__pycache__", "node_modules", ".pytest_cache"}

# Palabras del dominio que también son nombre de una hoja; como palabra suelta no identifican un libro.
VOCABULARIO_DOMINIO = {
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",  # meses (hojas mensuales antiguas)
    "egresos",  # token de detección de tipo de fuente (también es el nombre de una hoja de egresos)
}

# Lista blanca EXPLÍCITA. Deuda a retirar: cada entrada es código que todavía depende de un libro concreto.
LISTA_BLANCA = {
    # Script legacy de semillas: lee hojas fijas de tres libros (sheet_name=...) para sembrar hechos
    # históricos. No forma parte de la ingesta. Retirar cuando FU-L9 recargue todo por el pipeline.
    "pipeline/analytics/seed_historical_facts.py",
    # Semilla del catálogo financiero: el nombre del libro es el ORIGEN registrado de cada equivalencia
    # (dato del catálogo, no lógica). Cambiarlo altera el contenido de catalog_db.
    "backend/scripts/seed_financial_catalogs.py",
    # Padrón para rescatar CI por nombre (fk_resolver) con ruta por defecto a un libro concreto. Hacerlo
    # agnóstico exige elegir el padrón por contenido o desde dim_estudiante (no trivial; afecta la
    # resolución de identidad). Deuda abierta para FU-L3 / FU-L9.
    "pipeline/normalization/fk_resolver.py",
}


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def _nombres():
    nombres = set()
    with open(CSV_HOJAS, encoding="utf-8") as fh:
        for fila in csv.DictReader(fh):
            nombres.add(_nfc(fila["hoja"]))
            nombres.add(_nfc(os.path.splitext(fila["archivo"])[0]))
    return {n for n in nombres if n and n not in VOCABULARIO_DOMINIO}


def _distintivo(nombre: str) -> bool:
    return len(nombre) >= 8 and any(c in nombre for c in " _") or (len(nombre) >= 8 and any(c.isdigit() for c in nombre))


def _documentacion(arbol):
    """ids de los nodos Constant que son docstrings o cadenas sueltas."""
    ids = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Constant) and isinstance(nodo.value.value, str):
            ids.add(id(nodo.value))
    return ids


def _archivos():
    for carpeta in CARPETAS:
        for dirpath, dirnames, filenames in os.walk(RAIZ / carpeta):
            dirnames[:] = [d for d in dirnames if d not in EXCLUIR_DIRS]
            for f in filenames:
                if f.endswith(".py"):
                    yield Path(dirpath) / f


def _usos(ruta: Path, nombres, distintivos):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    docs = _documentacion(arbol)
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)) or id(nodo) in docs:
            continue
        s = _nfc(nodo.value)
        base = os.path.splitext(s)[0] if s.lower().endswith((".xlsx", ".xls", ".csv")) else s
        if base in nombres:
            yield nodo.lineno, base
            continue
        for n in distintivos:
            if n in s:
                yield nodo.lineno, n
                break


def test_lista_de_nombres_sale_del_perfil():
    nombres = _nombres()
    assert len(nombres) >= 50  # 62 hojas + 10 libros (menos repetidos y vocabulario)


def test_lista_blanca_existe_y_esta_justificada():
    for rel in LISTA_BLANCA:
        assert (RAIZ / rel).exists(), f"entrada de lista blanca obsoleta: {rel}"


def test_backend_y_pipeline_sin_nombres_de_libro_ni_de_hoja():
    nombres = _nombres()
    distintivos = sorted(n for n in nombres if _distintivo(n))
    hallazgos = []
    for ruta in _archivos():
        rel = ruta.relative_to(RAIZ).as_posix()
        if rel in LISTA_BLANCA:
            continue
        for linea, nombre in _usos(ruta, nombres, distintivos):
            hallazgos.append(f"{rel}:{linea} usa {nombre!r}")
    assert not hallazgos, "Nombres de libro u hoja en el código (principio rector #1):\n" + "\n".join(hallazgos)


def test_el_detector_encuentra_un_nombre_quemado(tmp_path):
    """Control: un literal sheet_name con un nombre real del perfil se detecta."""
    nombres = _nombres()
    distintivos = sorted(n for n in nombres if _distintivo(n))
    un_nombre = next(n for n in distintivos)
    ruta = tmp_path / "quemado.py"
    ruta.write_text(f'import pandas as pd\n"""docstring con {un_nombre}"""\ndf = pd.read_excel("x.xlsx", sheet_name="{un_nombre}")\n',
                    encoding="utf-8")
    usos = list(_usos(ruta, nombres, distintivos))
    assert usos == [(3, un_nombre)]  # el docstring no cuenta; el literal sí
