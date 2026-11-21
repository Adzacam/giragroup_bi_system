"""
Perfil de solo lectura de libros fuente (FU-L0).

Recorre los .xlsx de un directorio y describe cada hoja: estado (visible,
hidden, veryHidden), dimensiones, cabecera detectada por contenido, celdas
combinadas, fórmulas, nulos, tipos mezclados, rangos, vocabularios cortos,
filas vacías, subtotales y duplicadas.

Reglas:
- Genérico: no contiene nombres de libro ni de hoja. Entrada y salida por argumento.
- Sin PII: las cabeceras se guardan; los valores de columnas personales NO.
  Los vocabularios se suprimen en columnas personales y en valores con patrón
  de correo o de 7 o más dígitos.
- Solo lectura: el libro original no se modifica.

Uso:
    python scripts/auditoria_fuentes/perfil_fuentes.py --entrada uploads/data --salida docs/mediciones
Salida:
    <salida>/fu_l0_perfil.json   detalle por hoja y columna
    <salida>/fu_l0_hojas.csv     una fila por hoja
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import sys
import unicodedata
import warnings
from collections import Counter
from pathlib import Path

import openpyxl
import pandas as pd

# Tokens de cabecera que marcan una columna como personal (no se publica vocabulario).
PII_TOKENS = frozenset({
    "nombre", "nombres", "apellido", "apellidos", "ci", "correo", "mail", "email",
    "celular", "cel", "telefono", "tel", "nit", "direccion", "identidad",
    "pasaporte", "asesor", "responsable", "encargado",
    # Roles de persona: su columna puede traer nombres propios (sin vocabulario).
    "docente", "profesor", "relator", "instructor", "coordinador", "asistente",
    "consultor", "contacto", "representante", "cliente", "alumno", "estudiante",
    "postulante", "persona",
})

PATRON_CORREO = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PATRON_DIGITOS_LARGOS = re.compile(r"\d{7,}")
PATRON_SUBTOTAL = re.compile(r"^(sub\s*)?total(es)?\b")

MAX_DISTINTOS_VOCABULARIO = 15
FILAS_BUSQUEDA_CABECERA = 40
MAX_LARGO_VALOR_SUBTOTAL = 40
PROPORCION_CASI_VACIA = 0.10

ESTADOS_VALIDOS = ("visible", "hidden", "veryHidden")


def normalizar(texto) -> str:
    """Minúsculas, sin acentos y con espacios colapsados."""
    t = unicodedata.normalize("NFKD", str(texto))
    t = t.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", t).strip()


def es_pii_cabecera(nombre) -> bool:
    tokens = re.findall(r"[a-z0-9]+", normalizar(nombre))
    return any(tok in PII_TOKENS for tok in tokens)


def es_texto_numerico(valor) -> bool:
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return True
    if isinstance(valor, str):
        try:
            float(valor.replace(",", "").strip())
            return True
        except ValueError:
            return False
    return False


def tipo_valor(valor) -> str:
    if isinstance(valor, bool):
        return "booleano"
    if isinstance(valor, (int, float)):
        return "numero"
    if isinstance(valor, (dt.datetime, dt.date, dt.time, dt.timedelta)):
        return "fecha"
    if isinstance(valor, str):
        return "texto"
    return "otro"


def vacio(valor) -> bool:
    return valor is None or (isinstance(valor, str) and valor.strip() == "")


def dato_sensible(valor) -> bool:
    """Correo o secuencia de 7 o más dígitos: nunca se publica como cabecera ni como vocabulario."""
    if valor is None or isinstance(valor, (dt.datetime, dt.date, dt.time, dt.timedelta, bool)):
        return False
    texto = str(valor)
    if isinstance(valor, float) and valor.is_integer():
        texto = str(int(valor))
    return bool(PATRON_CORREO.search(texto) or PATRON_DIGITOS_LARGOS.search(texto))


def detectar_cabecera(filas: list[tuple]) -> int | None:
    """Fila de cabecera por contenido: más textos distintos no numéricos, ponderados por proporción.
    Los nombres con patrón sensible se enmascaran después (perfilar_hoja)."""
    mejor_score, mejor_idx = 0.0, None
    for i, fila in enumerate(filas[:FILAS_BUSQUEDA_CABECERA]):
        no_vacios = [v for v in fila if not vacio(v)]
        if len(no_vacios) < 2:
            continue
        textos = [str(v).strip() for v in no_vacios
                  if isinstance(v, str) and not es_texto_numerico(v)]
        if not textos:
            continue
        distintos = len({normalizar(t) for t in textos})
        score = distintos * (len(textos) / len(no_vacios))
        if score > mejor_score:
            mejor_score, mejor_idx = score, i
    return mejor_idx


def es_subtotal(fila: tuple) -> bool:
    primeros = [v for v in fila if not vacio(v)][:2]
    for v in primeros:
        if isinstance(v, str) and len(v.strip()) <= MAX_LARGO_VALOR_SUBTOTAL:
            if PATRON_SUBTOTAL.search(normalizar(v)):
                return True
    return False


def perfilar_columna(serie: pd.Series, nombre: str, posicion: int) -> dict:
    total = len(serie)
    no_nulos = serie[serie.map(lambda v: not vacio(v))]
    tipos = Counter(tipo_valor(v) for v in no_nulos)
    numeros = [float(v) for v in no_nulos if tipo_valor(v) == "numero" and not math.isnan(float(v))]
    anios = [v.year for v in no_nulos if tipo_valor(v) == "fecha" and hasattr(v, "year")]
    textos_norm = Counter(normalizar(v) for v in no_nulos)
    pii = es_pii_cabecera(nombre) or str(nombre).startswith("<enmascarado_col_")

    vocabulario = None
    suprimidos = 0
    if not pii and not vacio(nombre) and 0 < len(textos_norm) <= MAX_DISTINTOS_VOCABULARIO:
        vocabulario = {}
        for v in no_nulos:
            clave = str(v).strip()
            if dato_sensible(v):
                suprimidos += 1
                continue
            vocabulario[clave] = vocabulario.get(clave, 0) + 1
        vocabulario = dict(sorted(vocabulario.items(), key=lambda kv: (-kv[1], kv[0])))

    return {
        "posicion": posicion,
        "nombre": "" if nombre is None else str(nombre),
        "cabecera_vacia": vacio(nombre),
        "pii": pii,
        "n_datos": total,
        "n_no_nulos": int(len(no_nulos)),
        "pct_nulos": round(100 * (total - len(no_nulos)) / total, 2) if total else None,
        "tipos": dict(tipos),
        "tipos_mezclados": len(tipos) > 1,
        "min": min(numeros) if numeros else None,
        "max": max(numeros) if numeros else None,
        "anio_min": min(anios) if anios else None,
        "anio_max": max(anios) if anios else None,
        "n_distintos": len(textos_norm),
        "vocabulario": vocabulario,
        "vocabulario_suprimido_patron": suprimidos,
    }


def perfilar_hoja(archivo: str, nombre_hoja: str, ws_f, ws_v, estado: str) -> tuple[dict, dict]:
    """Devuelve (detalle_hoja, fila_csv)."""
    combinadas = len(ws_f.merged_cells.ranges)

    n_formulas = 0
    n_formulas_sin_valor = 0
    for fila_f, fila_v in zip(ws_f.iter_rows(), ws_v.iter_rows()):
        for cf, cv in zip(fila_f, fila_v):
            if cf.data_type == "f" or (isinstance(cf.value, str) and cf.value.startswith("=")):
                n_formulas += 1
                if cv.value is None:
                    n_formulas_sin_valor += 1

    filas = [tuple(r) for r in ws_v.iter_rows(values_only=True)]
    max_fila = len(filas)
    max_col = max((len(r) for r in filas), default=0)

    h = detectar_cabecera(filas)
    if h is None:
        cabecera_nombres: list = []
        cuerpo: list[tuple] = []
    else:
        cabecera_nombres = list(filas[h])[:max_col]
        cabecera_nombres += [None] * (max_col - len(cabecera_nombres))
        # Defensa en profundidad: un nombre con patrón sensible se enmascara.
        cabecera_nombres = [f"<enmascarado_col_{p + 1}>" if dato_sensible(v) else v
                            for p, v in enumerate(cabecera_nombres)]
        # Cabecera convertida a texto para que los nombres numéricos se publiquen como texto.
        cabecera_nombres = [v if v is None or isinstance(v, str) else str(v) for v in cabecera_nombres]
        cuerpo = filas[h + 1:]
        # Una hoja con una sola fila y sin cuerpo no tiene cabecera real: es un registro
        # residual que puede traer nombres, fechas de nacimiento o domicilios. Solo se
        # publica su ancho; nunca el contenido.
        if not any(not vacio(v) for fila in cuerpo for v in fila):
            cabecera_nombres = [None if vacio(v) else f"<fila_sin_cuerpo_col_{p + 1}>"
                                for p, v in enumerate(cabecera_nombres)]

    vacias = casi_vacias = subtotales = 0
    datos: list[tuple] = []
    umbral_casi = max(1, math.ceil(PROPORCION_CASI_VACIA * max_col)) if max_col else 1
    for fila in cuerpo:
        fila = tuple(list(fila) + [None] * (max_col - len(fila)))
        n_nv = sum(1 for v in fila if not vacio(v))
        if n_nv == 0:
            vacias += 1
            continue
        if es_subtotal(fila):
            subtotales += 1
            continue
        if n_nv <= umbral_casi:
            casi_vacias += 1
        datos.append(fila)

    firmas = [hashlib.sha1(repr([normalizar(v) if isinstance(v, str) else v for v in f]).encode()).hexdigest()
              for f in datos]
    duplicadas = len(firmas) - len(set(firmas))

    columnas = []
    if datos and h is not None:
        df = pd.DataFrame(datos, columns=range(max_col), dtype=object)
        for pos in range(max_col):
            nombre = cabecera_nombres[pos]
            columnas.append(perfilar_columna(df[pos], nombre, pos + 1))

    pct_medio = (round(sum(c["pct_nulos"] for c in columnas) / len(columnas), 2)
                 if columnas else None)
    detalle = {
        "archivo": archivo,
        "hoja": nombre_hoja,
        "estado": estado,
        "max_fila": max_fila,
        "max_columna": max_col,
        "filas_x_columnas": f"{max_fila}x{max_col}",
        "cabecera_fila": (h + 1) if h is not None else None,
        "filas_previas_cabecera": h if h is not None else None,
        "cabecera_nombres": ["" if v is None else str(v) for v in cabecera_nombres],
        "n_cabeceras_vacias": sum(1 for v in cabecera_nombres if vacio(v)),
        "n_combinadas": combinadas,
        "n_formulas": n_formulas,
        "n_formulas_sin_valor": n_formulas_sin_valor,
        "n_filas_datos": len(datos),
        "filas_vacias": vacias,
        "filas_casi_vacias": casi_vacias,
        "filas_subtotal": subtotales,
        "filas_duplicadas": duplicadas,
        "pct_nulos_medio": pct_medio,
        "columnas": columnas,
    }
    fila_csv = {
        "archivo": archivo,
        "hoja": nombre_hoja,
        "estado": estado,
        "filas_x_columnas": detalle["filas_x_columnas"],
        "cabecera_fila": detalle["cabecera_fila"],
        "n_cabeceras_vacias": detalle["n_cabeceras_vacias"],
        "n_combinadas": combinadas,
        "n_formulas": n_formulas,
        "n_formulas_sin_valor": n_formulas_sin_valor,
        "n_filas_datos": len(datos),
        "filas_vacias": vacias,
        "filas_casi_vacias": casi_vacias,
        "filas_subtotal": subtotales,
        "filas_duplicadas": duplicadas,
        "pct_nulos_medio": pct_medio,
        "columnas_mezcla_tipos": sum(1 for c in columnas if c["tipos_mezclados"]),
        "columnas_pii": sum(1 for c in columnas if c["pii"]),
        "columnas_con_vocabulario": sum(1 for c in columnas if c["vocabulario"] is not None),
    }
    return detalle, fila_csv


def perfilar_libro(ruta: Path) -> tuple[list[dict], list[dict], str | None]:
    """Devuelve (hojas_detalle, filas_csv, error)."""
    archivo = ruta.name
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb_f = openpyxl.load_workbook(ruta, read_only=False, data_only=False)
            wb_v = openpyxl.load_workbook(ruta, read_only=False, data_only=True)
    except Exception as exc:  # noqa: BLE001 - solo se registra el tipo de error
        return [], [], type(exc).__name__

    detalles, filas_csv = [], []
    for idx, nombre_hoja in enumerate(wb_f.sheetnames):
        ws_f = wb_f.worksheets[idx]
        ws_v = wb_v.worksheets[idx]
        estado = ws_f.sheet_state if ws_f.sheet_state in ESTADOS_VALIDOS else str(ws_f.sheet_state)
        det, fila = perfilar_hoja(archivo, nombre_hoja, ws_f, ws_v, estado)
        detalles.append(det)
        filas_csv.append(fila)
    wb_f.close()
    wb_v.close()
    return detalles, filas_csv, None


def perfilar_directorio(entrada: Path) -> dict:
    libros = sorted(p for p in entrada.glob("*.xlsx") if not p.name.startswith("~$"))
    hojas: list[dict] = []
    filas_csv: list[dict] = []
    errores: list[dict] = []
    for libro in libros:
        det, fil, err = perfilar_libro(libro)
        if err:
            errores.append({"archivo": libro.name, "error": err})
        hojas.extend(det)
        filas_csv.extend(fil)

    conteo_estados = Counter(h["estado"] for h in hojas)
    return {
        "entrada": entrada.name,
        "fecha_perfil": dt.date.today().isoformat(),
        "n_libros": len(libros),
        "n_hojas": len(hojas),
        "estados": {e: conteo_estados.get(e, 0) for e in ESTADOS_VALIDOS},
        "errores_lectura": errores,
        "reglas": {
            "tokens_pii_cabecera": sorted(PII_TOKENS),
            "max_distintos_vocabulario": MAX_DISTINTOS_VOCABULARIO,
            "patron_suprime_vocabulario": ["correo", "7 o mas digitos"],
            "vocabulario_solo_con_cabecera": True,
            "cabecera": "fila con mas textos distintos no numericos, ponderados por proporcion",
            "filas_casi_vacias": f"1 a max(1, ceil({PROPORCION_CASI_VACIA} * columnas)) celdas no vacias",
        },
        "hojas": hojas,
    }, filas_csv


def escribir_salidas(resultado: dict, filas_csv: list[dict], salida: Path) -> tuple[Path, Path]:
    salida.mkdir(parents=True, exist_ok=True)
    ruta_json = salida / "fu_l0_perfil.json"
    ruta_csv = salida / "fu_l0_hojas.csv"
    ruta_json.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    if filas_csv:
        with ruta_csv.open("w", newline="", encoding="utf-8") as fh:
            escritor = csv.DictWriter(fh, fieldnames=list(filas_csv[0].keys()))
            escritor.writeheader()
            escritor.writerows(filas_csv)
    else:
        ruta_csv.write_text("", encoding="utf-8")
    return ruta_json, ruta_csv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Perfil sin PII de libros fuente (FU-L0).")
    parser.add_argument("--entrada", required=True, type=Path, help="Directorio con los .xlsx")
    parser.add_argument("--salida", default=Path("docs/mediciones"), type=Path,
                        help="Directorio de salida (fu_l0_perfil.json y fu_l0_hojas.csv)")
    args = parser.parse_args(argv)
    if not args.entrada.is_dir():
        print("La entrada no es un directorio", file=sys.stderr)
        return 2
    resultado, filas_csv = perfilar_directorio(args.entrada)
    ruta_json, ruta_csv = escribir_salidas(resultado, filas_csv, args.salida)
    print(f"libros={resultado['n_libros']} hojas={resultado['n_hojas']} estados={resultado['estados']}")
    print(f"json={ruta_json}")
    print(f"csv={ruta_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
