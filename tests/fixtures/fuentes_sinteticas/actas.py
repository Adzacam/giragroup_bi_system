"""
FU-L4: libros sintéticos de actas (nota por módulo en formato ancho) con datos ficticios.

El mismo contenido se escribe con dos «recetas»: el ORIGINAL y una VARIANTE con otro nombre de archivo y de hoja, columnas en
otro orden, sinónimos de cabecera (CI, Condición académica, Mod. 1, Estado de tutoría), una hoja oculta repetida, una hoja
borrador y estados escritos con otras mayúsculas y acentos. El resultado en la DW debe ser el mismo.

Casos (CI, POS y nombres ficticios):
 A 9100001  85 / 70 / 55 · Aprobado → APROBADO, APROBADO, REPROBADO
 B 9100002  «Aprobó» / 0 / vacío · Deserción → APROBADO (texto), INASISTENCIA (0 con deserción, nota NULL)
 C 9100003  0 / 60 · Reprobado (insuficiencia) → 0 real (nota 0, REPROBADO), REPROBADO
 D 9100004  «EXIMIDA» / «No asistió a clases» / «SIN NOTAS EN EL ACTA…» · Participó + Abandono → EXIMIDO, INASISTENCIA, SIN_NOTA
 E 9100005  3481044 (CI pegado) / apellido / 90 · Aprobado → 2 celdas sin hecho (NULL) y aviso; fila a revisión; módulo 3 APROBADO
 F 9100006-1C (CI con complemento) POS-9001  80 · Aprobado
 G 9100006 (el mismo CI sin complemento) POS-9002  75 · Aprobado → mismo estudiante que F (estado A)
 H 9100007  0 · Aprobado → 0 real de un aprobado (sin deserción)
 I 9100008  Egresado (estado fuera de catálogo) 80 → se guarda y va a revisión
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import openpyxl

CABECERAS = ["N°", "POS - ACTAS", "CÉDULA DE IDENTIDAD", "MES INICO", "AÑO INCIO", "NOMBRES", "APELLIDO PATERNO",
             "MÓDULO 1", "MÓDULO 2", "MÓDULO 3", "ESTADO ACADEMICO", "ESTADO TUTORIA", "ESTADO ARCA"]

# (ci, pos, nombres, apellido, m1, m2, m3, estado_academico, estado_tutoria, estado_arca, mes, año)
FILAS = [
    ("9100001", "POS-9001", "ANA", "FICTICIA", 85, 70, 55, "Aprobado", "Aprobado", "Titulado", 3, 2027),
    ("9100002", "POS-9001", "LUIS", "PRUEBA", "Aprobó", 0, None, "Deserción", "Deserción", "No Titulado", 3, 2027),
    ("9100003", "POS-9001", "EVA", "MUESTRA", 0, 60, None, "Reprobado", "Insuficiencia académica", "No Titulado", 3, 2027),
    ("9100004", "POS-9001", "JUAN", "EJEMPLO", "EXIMIDA", "No asistió a clases", "SIN NOTAS EN EL ACTA DE NOTAS", "Participó",
     "Abandono", "No Titulado", 3, 2027),
    ("9100005", "POS-9001", "RUTH", "SIMULADA", 3481044, "LOZADA", 90, "Aprobado", "Aprobado", "Titulado", 3, 2027),
    ("9100006-1C", "POS-9001", "OMAR", "FALSO", 80, None, None, "Aprobado", "Aprobado", "Titulado", 3, 2027),
    ("9100006", "POS-9002", "OMAR", "FALSO", 75, None, None, "Aprobado", "Aprobado", "Titulado", 4, 2027),
    ("9100007", "POS-9002", "NORA", "INVENTADA", 0, None, None, "Aprobado", "Aprobado", "Titulado", 4, 2027),
    ("9100008", "POS-9002", "PABLO", "IMAGINARIO", 80, None, None, "Egresado", None, None, 4, 2027),
]
COLS_FILA = ["ci", "pos", "nombres", "apellido", "m1", "m2", "m3", "ea", "et", "ear", "mes", "anio"]

# Esperado en la DW (módulo = «<POS> · Módulo n»): (ci_numero, módulo) -> (nota_final, resultado)
ESPERADO: Dict[tuple, tuple] = {
    ("9100001", "POS-9001 · Módulo 1"): (85, "APROBADO"),
    ("9100001", "POS-9001 · Módulo 2"): (70, "APROBADO"),
    ("9100001", "POS-9001 · Módulo 3"): (55, "REPROBADO"),
    ("9100002", "POS-9001 · Módulo 1"): (None, "APROBADO"),
    ("9100002", "POS-9001 · Módulo 2"): (None, "INASISTENCIA"),
    ("9100003", "POS-9001 · Módulo 1"): (0, "REPROBADO"),
    ("9100003", "POS-9001 · Módulo 2"): (60, "REPROBADO"),
    ("9100004", "POS-9001 · Módulo 1"): (None, "EXIMIDO"),
    ("9100004", "POS-9001 · Módulo 2"): (None, "INASISTENCIA"),
    ("9100004", "POS-9001 · Módulo 3"): (None, "SIN_NOTA"),
    ("9100005", "POS-9001 · Módulo 3"): (90, "APROBADO"),
    ("9100006", "POS-9001 · Módulo 1"): (80, "APROBADO"),
    ("9100006", "POS-9002 · Módulo 1"): (75, "APROBADO"),
    ("9100007", "POS-9002 · Módulo 1"): (0, "REPROBADO"),
    ("9100008", "POS-9002 · Módulo 1"): (80, "APROBADO"),
}


@dataclass
class RecetaActa:
    archivo: str
    hoja_datos: str
    hoja_oculta: str
    hoja_borrador: str
    cabeceras: Dict[str, str] = field(default_factory=dict)      # cabecera original -> cabecera de la receta
    orden: List[str] = field(default_factory=lambda: list(CABECERAS))
    estado_en_otro_caso: bool = False                            # estados escritos con otras mayúsculas, acentos y espacios


ORIGINAL = RecetaActa(archivo="acta_original.xlsx", hoja_datos="Notas 2027", hoja_oculta="Notas viejas", hoja_borrador="Notas borrador")

VARIANTE = RecetaActa(
    archivo="Registro de calificaciones (v3).xlsx", hoja_datos="Calificaciones", hoja_oculta="respaldo", hoja_borrador="Calif boor",
    cabeceras={"CÉDULA DE IDENTIDAD": "CI", "ESTADO ACADEMICO": "CONDICION ACADEMICA", "ESTADO TUTORIA": "Estado de tutoría",
               "MÓDULO 1": "Mod. 1", "MÓDULO 2": "Mod. 2", "MÓDULO 3": "Mod. 3"},
    orden=["ESTADO ARCA", "N°", "MÓDULO 3", "NOMBRES", "ESTADO ACADEMICO", "AÑO INCIO", "CÉDULA DE IDENTIDAD", "MÓDULO 1",
           "APELLIDO PATERNO", "ESTADO TUTORIA", "MES INICO", "MÓDULO 2", "POS - ACTAS"],
    estado_en_otro_caso=True,
)


def _otro_caso(v):
    if not isinstance(v, str):
        return v
    return {"Deserción": " DESERCIÓN", "Reprobado": "reprobado", "Aprobado": "APROBADO ", "Abandono": "abandono",
            "Participó": "PARTICIPO", "No Titulado": "no titulado", "Titulado": "TITULADO",
            "Insuficiencia académica": "insuficiencia academica"}.get(v, v)


def _valor(fila: dict, columna: str, n: int, receta: RecetaActa):
    if columna == "N°":
        return n
    if columna in ("ESTADO ACADEMICO", "ESTADO TUTORIA", "ESTADO ARCA"):
        v = fila[{"ESTADO ACADEMICO": "ea", "ESTADO TUTORIA": "et", "ESTADO ARCA": "ear"}[columna]]
        return _otro_caso(v) if receta.estado_en_otro_caso else v
    return {"POS - ACTAS": fila["pos"], "CÉDULA DE IDENTIDAD": fila["ci"], "MES INICO": fila["mes"], "AÑO INCIO": fila["anio"],
            "NOMBRES": fila["nombres"], "APELLIDO PATERNO": fila["apellido"], "MÓDULO 1": fila["m1"], "MÓDULO 2": fila["m2"],
            "MÓDULO 3": fila["m3"]}[columna]


def _escribir(ws, receta: RecetaActa, filas: List[dict], fantasma: int = 0) -> None:
    cols = list(receta.orden)
    for c, nombre in enumerate(cols, start=1):
        ws.cell(row=1, column=c, value=receta.cabeceras.get(nombre, nombre))
    r = 1
    for n, fila in enumerate(filas, start=1):
        r += 1
        for c, nombre in enumerate(cols, start=1):
            ws.cell(row=r, column=c, value=_valor(fila, nombre, n, receta))
    ordinal = cols.index("N°") + 1
    for k in range(fantasma):
        r += 1
        ws.cell(row=r, column=ordinal, value=len(filas) + k + 1)


def construir(receta: RecetaActa, carpeta: Path, filas: Optional[List[tuple]] = None, con_estados: bool = True) -> Path:
    """Escribe el libro de la receta; `con_estados=False` quita las tres columnas de estado (acta sin estado académico)."""
    registros = [dict(zip(COLS_FILA, f)) for f in (filas or FILAS)]
    rec = receta
    if not con_estados:
        rec = RecetaActa(**{**receta.__dict__, "orden": [c for c in receta.orden if not c.startswith("ESTADO")]})
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet(rec.hoja_datos)
    _escribir(ws, rec, registros, fantasma=40)
    ws_o = wb.create_sheet(rec.hoja_oculta)
    _escribir(ws_o, rec, registros[:3])
    ws_o.sheet_state = "hidden"
    ws_b = wb.create_sheet(rec.hoja_borrador)
    _escribir(ws_b, rec, registros[:2])
    ruta = carpeta / rec.archivo
    wb.save(ruta)
    return ruta
