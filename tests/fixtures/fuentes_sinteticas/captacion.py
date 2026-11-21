"""
FU-L3: libros sintéticos de captación (leads, inscritos y reservas por programa y mes) con datos ficticios.

El mismo contenido se escribe con dos «recetas»: el ORIGINAL y una VARIANTE con otro nombre de archivo y de hoja,
columnas en otro orden y otros sinónimos de cabecera (Interesados / Inscritos). El resultado en la DW debe ser el mismo.

Contenido (todos los POS y programas son ficticios):
- hoja mensual VISIBLE 2027-03: 5 programas; uno sin inscritos (no cuenta), uno con más inscritos que leads (no cuenta);
- hoja mensual OCULTA 2027-01, sin hoja visible para ese mes: se rescata (FU-L1b) y cuenta;
- hoja mensual OCULTA 2027-03 repetida: período ya cubierto, se ignora;
- hoja BORRADOR oculta: se ignora;
- tabla por programa («IBP»): el mes va en cada fila; repite 3 programas de 2027-03 con OTRAS cifras (gana la hoja de detalle
  visible) y trae 2027-04 y 2027-05 (solo ahí). Va en el mismo libro o, como en la fuente real, dentro de un libro de actas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import openpyxl

# (pos, leads, inscritos, reservas); None = celda vacía
MENSUAL_2027_03 = [
    (9300, 100, 10, 4),
    (9301, 50, 5, 2),
    (9302, 80, None, 3),       # sin inscritos: no cuenta
    (9303, 20, 25, 1),         # más inscritos que leads: no cuenta
    (9304, 40, 0, 0),          # cero inscritos es una conversión real de 0
]
MENSUAL_2027_01_OCULTA = [(9100, 60, 6, 1), (9101, 40, 2, 0)]
REPETIDA_2027_03_OCULTA = [(9300, 7777, 777, 7), (9301, 8888, 88, 8)]     # no debe contar
IBP = [   # (pos, año, mes, leads, inscritos)
    (9300, 2027, 3, 900, 90),      # ya cubierto por la hoja de detalle visible -> no cuenta
    (9301, 2027, 3, 600, 60),      # ídem
    (9302, 2027, 3, 70, 7),        # el detalle visible no tiene inscritos de 9302: aquí sí hay un par válido -> cuenta
    (9400, 2027, 4, 200, 20),
    (9401, 2027, 4, 100, 5),
    (9400, 2027, 5, 300, 12),
    (9500, 2027, 6, 90, None),     # sin inscritos: no cuenta
]

# Resultado esperado por (pos, 'AAAA-MM'): (leads, inscritos)
ESPERADO: Dict[tuple, tuple] = {
    ("POS-9300", "2027-03"): (100, 10), ("POS-9301", "2027-03"): (50, 5),
    ("POS-9304", "2027-03"): (40, 0), ("POS-9302", "2027-03"): (70, 7),
    ("POS-9100", "2027-01"): (60, 6), ("POS-9101", "2027-01"): (40, 2),
    ("POS-9400", "2027-04"): (200, 20), ("POS-9401", "2027-04"): (100, 5),
    ("POS-9400", "2027-05"): (300, 12),
}
# Por mes: (leads, inscritos)
ESPERADO_MES = {
    "2027-01": (100, 8), "2027-03": (260, 22), "2027-04": (300, 25), "2027-05": (300, 12),
}


@dataclass
class RecetaCaptacion:
    archivo_plan: str
    archivo_acta: str
    visible: str
    oculta_rescatada: str
    oculta_repetida: str
    oculta_borrador: str
    por_programa: str
    hoja_actas: str
    cab_mensual: List[str]       # N, AÑO, MES, POS, PROGRAMA, ESTADO, INSCRITOS, LEADS, RESERVAS (otro orden y otros sinónimos)
    cab_ibp: List[str]           # POS, PROGRAMA, MES, AÑO, INSCRITOS, LEADS
    rotulos: Dict[str, str]


ORIGINAL = RecetaCaptacion(
    archivo_plan="plan_captacion.xlsx", archivo_acta="actas_y_ibp.xlsx",
    visible="Marzo-2027", oculta_rescatada="Enero-2027", oculta_repetida="Marzo-2027 (2)", oculta_borrador="Febrero-2027 borrador",
    por_programa="IBP", hoja_actas="ACTAS",
    cab_mensual=["N°", "AÑO", "MES", "POS", "PROGRAMA", "ESTADO", "N° INSCRITOS", "RESERVAS", "LEADS"],
    cab_ibp=["N°", "POS - IBP", "NOMBRE DEL PROGRAMA", "MES IBP", "AÑO IBP", "N° DE INSCRITOS", "LEADS"],
    rotulos={},
)
VARIANTE = RecetaCaptacion(
    archivo_plan="Seguimiento de interesados v2.xlsx", archivo_acta="Libro de calificaciones.xlsx",
    visible="Trimestre actual", oculta_rescatada="respaldo enero", oculta_repetida="copia del trimestre", oculta_borrador="feb boor",
    por_programa="Planificación por programa", hoja_actas="Notas",
    cab_mensual=["LEADS", "PROGRAMA", "POS", "Reservas", "Total inscritos", "MES", "N°", "ESTADO", "GESTION"][::-1][::-1],
    cab_ibp=["LEADS", "AÑO IBP", "POS - IBP", "Inscritos", "MES IBP", "NOMBRE DEL PROGRAMA"],
    rotulos={"LEADS": "INTERESADOS"},
)
# La variante cambia de sitio y de sinónimo: interesados / total inscritos / inscritos
VARIANTE.cab_mensual = ["N°", "GESTION", "MES", "POS", "PROGRAMA", "ESTADO", "Total inscritos", "Reservas", "Interesados"]
VARIANTE.cab_ibp = ["Interesados", "AÑO IBP", "POS - IBP", "Inscritos", "MES IBP", "NOMBRE DEL PROGRAMA"]


def _valor_mensual(cab: str, i: int, anio: int, mes: int, pos: int, leads, ins, res):
    c = cab.upper()
    if c.startswith("N°") and "INSCR" not in c:
        return i + 1
    if c in ("AÑO", "GESTION"):
        return anio
    if c == "MES":
        return mes
    if c == "POS":
        return pos
    if c == "PROGRAMA":
        return f"DIPLOMADO FICTICIO {pos}"
    if c == "ESTADO":
        return "Inicio Confirmado"
    if "INSCRITOS" in c:
        return ins
    if c == "RESERVAS":
        return res
    return leads     # LEADS / Interesados


def _hoja_mensual(ws, cab: List[str], anio: int, mes: int, filas) -> None:
    for c, v in enumerate(cab, start=1):
        ws.cell(row=1, column=c, value=v)
    for i, (pos, leads, ins, res) in enumerate(filas):
        for c, v in enumerate(cab, start=1):
            ws.cell(row=2 + i, column=c, value=_valor_mensual(v, i, anio, mes, pos, leads, ins, res))


def _hoja_ibp(ws, cab: List[str], filas=IBP) -> None:
    for c, v in enumerate(cab, start=1):
        ws.cell(row=1, column=c, value=v)
    for i, (pos, anio, mes, leads, ins) in enumerate(filas):
        for c, v in enumerate(cab, start=1):
            u = v.upper()
            valor = (i + 1 if u.startswith("N°") and "INSCR" not in u else pos if u == "POS - IBP" else
                     f"DIPLOMADO FICTICIO {pos}" if u == "NOMBRE DEL PROGRAMA" else mes if u == "MES IBP" else
                     anio if u == "AÑO IBP" else ins if "INSCRITOS" in u else leads)
            ws.cell(row=2 + i, column=c, value=valor)


def _hoja_actas(ws) -> None:
    """Un acta mínima ficticia: sirve para que el libro sea de tipo ACTA y la tabla por programa tome su propio tipo."""
    for c, v in enumerate(["CI", "NOMBRES", "PATERNO", "POS", "MÓDULO 1", "ESTADO ACADÉMICO"], start=1):
        ws.cell(row=1, column=c, value=v)
    for i, (ci, nom, pat) in enumerate([("9200001", "ANA", "FICTICIA"), ("9200002", "LUIS", "PRUEBAS")]):
        for c, v in enumerate([ci, nom, pat, 9300, 80 + i, "Aprobado"], start=1):
            ws.cell(row=2 + i, column=c, value=v)


def construir_plan(receta: RecetaCaptacion, carpeta: Path, con_ibp: bool = True) -> Path:
    """Libro de planificación: mensual visible, mensual oculta rescatada, repetida y borrador ocultas y (opcional) la tabla por programa."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = receta.visible
    _hoja_mensual(ws, receta.cab_mensual, 2027, 3, MENSUAL_2027_03)
    for titulo, mes, filas in ((receta.oculta_rescatada, 1, MENSUAL_2027_01_OCULTA),
                               (receta.oculta_repetida, 3, REPETIDA_2027_03_OCULTA),
                               (receta.oculta_borrador, 2, [(9200, 5, 5, 0)])):
        wo = wb.create_sheet(titulo)
        _hoja_mensual(wo, receta.cab_mensual, 2027, mes, filas)
        wo.sheet_state = "hidden"
    if con_ibp:
        _hoja_ibp(wb.create_sheet(receta.por_programa), receta.cab_ibp)
    ruta = carpeta / receta.archivo_plan
    wb.save(ruta)
    return ruta


def construir_acta_con_ibp(receta: RecetaCaptacion, carpeta: Path) -> Path:
    """Libro de actas que, como la fuente real, trae también la tabla de planificación por programa (con el mes en cada fila)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = receta.hoja_actas
    _hoja_actas(ws)
    _hoja_ibp(wb.create_sheet(receta.por_programa), receta.cab_ibp)
    ruta = carpeta / receta.archivo_acta
    wb.save(ruta)
    return ruta


# ── Inscripciones individuales (una fila por inscripción) ───────────────

INSCRIPCIONES = [   # (CI ficticio, nombres, paterno, POS, fecha de inscripción 'AAAA-MM-DD')
    ("9300001", "ANA", "FICTICIA", "POS-9300", "2027-03-02"),
    ("9300002", "LUIS", "PRUEBAS", "POS-9300", "2027-03-02"),
    ("9300003", "EVA", "MUESTRAL", "POS-9300", "2027-03-15"),
    ("9300004", "JUAN", "EJEMPLAR", "POS-9301", "2027-03-15"),
    ("9300005", "RUTH", "SIMULADA", "POS-9301", "2027-04-01"),
    ("9300006", "MARCO", "DEMOSTRADO", "POS-9302", "2027-04-20"),
    ("12", "SIN", "VALIDAR", "POS-9302", "2027-04-21"),     # CI incompleta: la inscripción existe y suma 1
    ("9300008", "OLGA", "MILIS", "POS-9301", "2027-04-22 09:17:19.521000"),     # marca temporal con milisegundos
]
INSCRITOS_POR_ANIO = {2027: len(INSCRIPCIONES)}


def construir_inscripciones(carpeta: Path, nombre: str = "tabla_inscritos.xlsx", variante: bool = False) -> Path:
    """Tabla de inscripciones: UNA fila por inscripción. La variante cambia nombres de columna, orden y hoja."""
    wb = openpyxl.Workbook()
    ws = wb.active
    if variante:
        ws.title = "Altas"
        cab = ["CI", "NOMBRE DEL PROGRAMA", "NUMEROPROYECTO", "MARCA TEMPORAL", "NOMBRES", "PATERNO", "ESTADO DEL INSCRITO"]
    else:
        ws.title = "TBL_X"
        cab = ["MARCA TEMPORAL", "NUMEROPROYECTO", "NOMBRE DEL PROGRAMA", "CI", "NOMBRES", "PATERNO", "ESTADO DEL INSCRITO"]
    for c, v in enumerate(cab, start=1):
        ws.cell(row=1, column=c, value=v)
    for i, (ci, nom, pat, pos, fecha) in enumerate(INSCRIPCIONES):
        vals = {"MARCA TEMPORAL": fecha if len(fecha) > 10 else f"{fecha} 10:00:00", "NUMEROPROYECTO": pos, "NOMBRE DEL PROGRAMA": f"DIPLOMADO FICTICIO {pos[-4:]}",
                "CI": ci, "NOMBRES": nom, "PATERNO": pat, "ESTADO DEL INSCRITO": "ACTIVO"}
        for c, v in enumerate(cab, start=1):
            ws.cell(row=2 + i, column=c, value=vals[v])
    ruta = carpeta / nombre
    wb.save(ruta)
    return ruta
