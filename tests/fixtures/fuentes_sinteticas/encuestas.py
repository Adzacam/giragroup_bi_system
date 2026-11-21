"""
FU-L5: libros sintéticos de encuestas (evaluación docente y experiencia institucional) con datos ficticios.

El mismo contenido se escribe con dos «recetas»: el ORIGINAL y una VARIANTE con otro nombre de archivo y de hoja, columnas en otro
orden, otros nombres de las columnas de identificación, una hoja oculta repetida y una hoja borrador. El resultado en la DW debe ser
el mismo.

Hoja A (una respuesta por fila, encabezado de dos niveles con celdas combinadas), POS y estudiantes ficticios:
  P1 acuerdo con «n/Etiqueta» · P2 acuerdo con etiqueta sin número · P3 satisfacción 1-10 · P4 recomendación (NPS) 0-10 · P6 acuerdo · P5 comentario
  fila 1  5/Totalmente de acuerdo · De acuerdo · 9 · 10 · comentario                      → 5, 4, 9/10, NPS 10/10, comentario
  fila 2  4/De acuerdo · Totalmente de acuerdo · 8 · 0                                    → 4, 5, 8/10, NPS 0 (el 0 del NPS vale)
  fila 3  0/Sin Información · Neutral · 7 · 6                                             → NULL (0), 3, 7/10, NPS 6
  fila 4  4/Fácil · Satisfecho · 5/Totalmente de acuerdo · 8                              → 3 respuestas cruzadas (NULL), NPS 8
  fila 5  8 (fuera de 1-5) · texto de otra pregunta · 10 · 9                              → fuera de escala, cruzada, 10/10, NPS 9
  fila 6  3/Neutral · «Estupendo» (etiqueta que no está en el diccionario) · 9 · 9         → 3, fuera de catálogo, 9/10, NPS 9
  fila 7  columna del módulo con «4/De acuerdo» · 5/Totalmente de acuerdo · Muy de acuerdo · 6 · 7 → módulo sin número; 5, 5, 6/10, NPS 7
  filas 8-12 respuestas normales
Hoja B (dos columnas por pregunta: texto «n/Etiqueta» y número; una columna de promedio calculada; comentario con «0/Sin Información»).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import openpyxl

PREG = {
    "p1": "El contenido del módulo fue pertinente para mi campo profesional.",
    "p2": "El/la docente fue clave para mi aprendizaje en este módulo.",
    "p3": "¿Qué tan satisfecho/a está con su experiencia general en este módulo?",
    "p4": "¿Qué tan probable es que recomiende este módulo a un colega o amigo/a?",
    "p5": "¿Qué aspecto podría mejorarse en este módulo?",
    "p6": "La metodología empleada favoreció la reflexión crítica del tema.",
}
LARGO = "Esta es una respuesta larga que pertenece a otra pregunta distinta del formulario"

# (n, nombre, fecha, pos, módulo, p1, p2, p3, p4, p6, p5)
FILAS_A = [
    (1, "ANA FICTICIA RUIZ", "2027-03-10 10:00:00", "POS-9801", 1, "5/Totalmente de acuerdo", "De acuerdo", 9, 10, "4/De acuerdo", "Más casos prácticos"),
    (2, "LUIS PRUEBA GOMEZ", "2027-03-10 10:05:00", "POS-9801", 1, "4/De acuerdo", "Totalmente de acuerdo", 8, 0, "5/Totalmente de acuerdo", None),
    (3, "EVA MUESTRA SOLIS", "2027-03-11 09:00:00", "POS-9801", 2, "0/Sin Información", "Neutral", 7, 6, "4/De acuerdo", None),
    (4, "JUAN EJEMPLO VACA", "2027-03-11 09:10:00", "POS-9801", 2, "4/Fácil", "Satisfecho", "5/Totalmente de acuerdo", 8, "3/Neutral", None),
    (5, "RUTH SIMULADA PAZ", "2027-03-12 08:00:00", "POS-9802", 1, 8, LARGO, 10, 9, "4/De acuerdo", None),
    (6, "OMAR FALSO LIMA", "2027-03-12 08:20:00", "POS-9802", 1, "3/Neutral", "Estupendo", 9, 9, "5/Totalmente de acuerdo", None),
    (7, "NORA INVENTADA CRUZ", "2027-03-12 08:40:00", "POS-9802", "4/De acuerdo", "5/Totalmente de acuerdo", "Muy de acuerdo", 6, 7, "4/De acuerdo", None),
    (8, "PABLO IMAGINARIO SUAREZ", "2027-03-13 10:00:00", "POS-9801", 1, "4/De acuerdo", "De acuerdo", 8, 9, "5/Totalmente de acuerdo", None),
    (9, "TERESA SIMULADA ROJAS", "2027-03-13 10:30:00", "POS-9801", 2, "5/Totalmente de acuerdo", "Totalmente de acuerdo", 10, 10, "4/De acuerdo", "Todo claro"),
    (10, "MARIO FICTICIO PAZ", "2027-03-14 11:00:00", "POS-9802", 1, "4/De acuerdo", "De acuerdo", 7, 8, "5/Totalmente de acuerdo", None),
    (11, "LAURA PRUEBA DIAZ", "2027-03-14 11:30:00", "POS-9802", 1, "5/Totalmente de acuerdo", "De acuerdo", 9, 9, "4/De acuerdo", None),
    (12, "DIEGO MUESTRA LIMA", "2027-03-15 12:00:00", "POS-9801", 1, "3/Neutral", "Neutral", 6, 7, "3/Neutral", None),
]
COLS_A = ["n", "nombre", "correo", "fecha", "pos", "mod", "p1", "p2", "p3", "p4", "p6", "p5"]

# (n, nombre, fecha, pos, módulo, a1_txt, a1_num, a2_txt, a2_num, a4_txt, a4_num, comentario)
FILAS_B = [
    (1, "ANA FICTICIA RUIZ", "2027-04-02 09:00:00", "POS-9803", 1, "5/Totalmente de acuerdo", 5, "5/Muy satisfecho", 5, "3/Adecuada", 3, "Buen curso"),
    (2, "LUIS PRUEBA GOMEZ", "2027-04-02 09:10:00", "POS-9803", 1, "4/De acuerdo", 4, "0/Sin Información", 0, "4/Pesada", 4, "0/Sin Información"),
    (3, "EVA MUESTRA SOLIS", "2027-04-03 10:00:00", "POS-9803", 1, "3/Neutral", 3, "0/Sin Información", 0, "3/Adecuada", 3, "0/Sin Información"),
    (4, "JUAN EJEMPLO VACA", "2027-04-03 10:15:00", "POS-9803", 1, "0/Sin Información", 0, "0/Sin Información", 0, "0/Sin Información", 0, "0/Sin Información"),
    (5, "RUTH SIMULADA PAZ", "2027-04-04 11:00:00", "POS-9803", 1, "5/Totalmente de acuerdo", 5, "4/Satisfecho", 4, "2/Ligera", 2, "Más práctica"),
    (6, "OMAR FALSO LIMA", "2027-04-04 11:30:00", "POS-9803", 1, "4/De acuerdo", 4, "3/Neutral", 3, "3/Adecuada", 3, "0/Sin Información"),
]
PREG_B = {
    "a1": "¿El docente explica con claridad los conceptos?",
    "a2": "¿Qué tan satisfecho/a está con el trato del personal administrativo?",
    "a4": "¿La carga de actividades asignadas es?",
    "com": "¿Qué comentario tiene sobre el curso?",
}

# Resultado esperado por (módulo, pregunta): lista ordenada de (puntuación, escala_max, tipo_pregunta). El módulo es el que arma la ingesta.
M1, M2, M3 = "POS-9801 · Módulo 1", "POS-9801 · Módulo 2", "POS-9802 · Módulo 1"
M_SIN_NUMERO = "POS-9802"
ESPERADO_A = [   # (módulo, pregunta, puntuación, escala, tipo)
    (M1, PREG["p1"], 5, 5, "DOCENTE"), (M1, PREG["p2"], 4, 5, "DOCENTE"), (M1, PREG["p3"], 9, 10, "DOCENTE"), (M1, PREG["p4"], 10, 10, "NPS"),
    (M1, PREG["p1"], 4, 5, "DOCENTE"), (M1, PREG["p2"], 5, 5, "DOCENTE"), (M1, PREG["p3"], 8, 10, "DOCENTE"), (M1, PREG["p4"], 0, 10, "NPS"),
    (M2, PREG["p2"], 3, 5, "DOCENTE"), (M2, PREG["p3"], 7, 10, "DOCENTE"), (M2, PREG["p4"], 6, 10, "NPS"),
    (M2, PREG["p4"], 8, 10, "NPS"),
    (M3, PREG["p3"], 10, 10, "DOCENTE"), (M3, PREG["p4"], 9, 10, "NPS"),
    (M3, PREG["p1"], 3, 5, "DOCENTE"), (M3, PREG["p3"], 9, 10, "DOCENTE"), (M3, PREG["p4"], 9, 10, "NPS"),
    (M_SIN_NUMERO, PREG["p1"], 5, 5, "DOCENTE"), (M_SIN_NUMERO, PREG["p2"], 5, 5, "DOCENTE"), (M_SIN_NUMERO, PREG["p3"], 6, 10, "DOCENTE"),
    (M_SIN_NUMERO, PREG["p4"], 7, 10, "NPS"),
    (M1, PREG["p1"], 4, 5, "DOCENTE"), (M1, PREG["p2"], 4, 5, "DOCENTE"), (M1, PREG["p3"], 8, 10, "DOCENTE"), (M1, PREG["p4"], 9, 10, "NPS"),
    (M2, PREG["p1"], 5, 5, "DOCENTE"), (M2, PREG["p2"], 5, 5, "DOCENTE"), (M2, PREG["p3"], 10, 10, "DOCENTE"), (M2, PREG["p4"], 10, 10, "NPS"),
    (M3, PREG["p1"], 4, 5, "DOCENTE"), (M3, PREG["p2"], 4, 5, "DOCENTE"), (M3, PREG["p3"], 7, 10, "DOCENTE"), (M3, PREG["p4"], 8, 10, "NPS"),
    (M3, PREG["p1"], 5, 5, "DOCENTE"), (M3, PREG["p2"], 4, 5, "DOCENTE"), (M3, PREG["p3"], 9, 10, "DOCENTE"), (M3, PREG["p4"], 9, 10, "NPS"),
    (M1, PREG["p1"], 3, 5, "DOCENTE"), (M1, PREG["p2"], 3, 5, "DOCENTE"), (M1, PREG["p3"], 6, 10, "DOCENTE"), (M1, PREG["p4"], 7, 10, "NPS"),
    # P6 (acuerdo con «n/Etiqueta»), una respuesta por fila
    (M1, PREG["p6"], 4, 5, "DOCENTE"), (M1, PREG["p6"], 5, 5, "DOCENTE"), (M2, PREG["p6"], 4, 5, "DOCENTE"), (M2, PREG["p6"], 3, 5, "DOCENTE"), (M3, PREG["p6"], 4, 5, "DOCENTE"), (M3, PREG["p6"], 5, 5, "DOCENTE"), (M_SIN_NUMERO, PREG["p6"], 4, 5, "DOCENTE"), (M1, PREG["p6"], 5, 5, "DOCENTE"), (M2, PREG["p6"], 4, 5, "DOCENTE"), (M3, PREG["p6"], 5, 5, "DOCENTE"), (M3, PREG["p6"], 4, 5, "DOCENTE"), (M1, PREG["p6"], 3, 5, "DOCENTE"),
]
# Comentarios esperados de la hoja A (módulo, pregunta, texto)
COMENTARIOS_A = [(M1, PREG["p5"], "Más casos prácticos"), (M2, PREG["p5"], "Todo claro")]
M_B = "POS-9803 · Módulo 1"
ESPERADO_B = [
    (M_B, PREG_B["a1"], 5, 5, "DOCENTE"), (M_B, PREG_B["a1"], 4, 5, "DOCENTE"), (M_B, PREG_B["a1"], 3, 5, "DOCENTE"),
    (M_B, PREG_B["a1"], 5, 5, "DOCENTE"), (M_B, PREG_B["a1"], 4, 5, "DOCENTE"),
    (M_B, PREG_B["a2"], 5, 5, "INSTITUCIONAL"), (M_B, PREG_B["a2"], 4, 5, "INSTITUCIONAL"), (M_B, PREG_B["a2"], 3, 5, "INSTITUCIONAL"),
    (M_B, PREG_B["a4"], 3, 5, "DOCENTE"), (M_B, PREG_B["a4"], 4, 5, "DOCENTE"), (M_B, PREG_B["a4"], 3, 5, "DOCENTE"),
    (M_B, PREG_B["a4"], 2, 5, "DOCENTE"), (M_B, PREG_B["a4"], 3, 5, "DOCENTE"),
]
COMENTARIOS_B = [(M_B, PREG_B["com"], "Buen curso"), (M_B, PREG_B["com"], "Más práctica")]
# Cabeceras de la hoja B tal como las normaliza la ingesta (el prefijo «A 1.» y el marcador «N°» no cuentan para la pregunta)
# Avisos esperados: (motivo, nº de respuestas) agregados por la suma de las dos hojas
AVISOS_ESPERADOS = {
    "SIN_INFORMACION": 1 + 1 + 3 + 1,          # hoja A: P1 fila 3 · hoja B: A1 fila 4, A2 filas 2-4, A4 fila 4 (el comentario «0/Sin…» no cuenta)
    "RESPUESTA_EN_COLUMNA_EQUIVOCADA": 3 + 1 + 1,   # hoja A: fila 4 (3), fila 5 (texto largo) y la columna del módulo de la fila 7
    "PUNTUACION_FUERA_DE_ESCALA": 1,            # hoja A: fila 5, P1 = 8
    "VALOR_FUERA_DE_CATALOGO": 1,               # hoja A: fila 6, P2 = «Estupendo»
}


@dataclass
class RecetaEncuesta:
    archivo: str
    hoja_a: str
    hoja_b: str
    hoja_oculta: str
    hoja_borrador: str
    cab_identidad: Dict[str, str] = field(default_factory=dict)     # cabecera original -> cabecera de la receta
    barajar: bool = False                                           # columnas de preguntas e identificación en otro orden


ORIGINAL = RecetaEncuesta(archivo="encuesta_original.xlsx", hoja_a="Evaluación por módulo", hoja_b="Experiencia con dos columnas",
                          hoja_oculta="Respuestas viejas", hoja_borrador="Encuesta borrador")
VARIANTE = RecetaEncuesta(
    archivo="Respuestas del formulario (v3).xlsx", hoja_a="Resultados", hoja_b="Cursos", hoja_oculta="respaldo", hoja_borrador="Resultados boor",
    cab_identidad={"Nombre completo del usuario": "Estudiante", "Programa - POS": "Programa", "Número del modulo": "Módulo",
                   "Dirección de correo": "Email"},
    barajar=True,
)


def _fecha(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


CORREO_FICTICIO = "persona.ficticia@ejemplo.test"


def _hoja_a(ws, receta: RecetaEncuesta, filas) -> None:
    # La cabecera «Dirección de correo» (como la de un reporte de Moodle) no debe hacer pasar la encuesta por libro de calificaciones
    ident = ["N°", "Nombre completo del usuario", "Dirección de correo", "Fecha", "Programa - POS", "Número del modulo"]
    cols = ident + [PREG[k] for k in ("p1", "p2", "p3", "p4", "p6", "p5")]
    claves = COLS_A
    orden = list(range(len(cols)))
    if receta.barajar:
        random.Random(7).shuffle(orden)
    ws.cell(row=1, column=1, value="Información básica: nombre, correo y programa de las encuestas")
    ws.cell(row=1, column=len(cols), value="Bloque 1. Por favor, califique el contenido del módulo")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3)
    for c, i in enumerate(orden, start=1):
        ws.cell(row=2, column=c, value=receta.cab_identidad.get(cols[i], cols[i]))
    for r, fila in enumerate(filas, start=3):
        valores = dict(zip([k for k in claves if k != "correo"], fila))
        valores["correo"] = CORREO_FICTICIO
        for c, i in enumerate(orden, start=1):
            v = valores[claves[i]]
            ws.cell(row=r, column=c, value=_fecha(v) if claves[i] == "fecha" else v)
    for k in range(30):   # filas fantasma: solo el número de orden
        ws.cell(row=3 + len(filas) + k, column=orden.index(0) + 1, value=len(filas) + k + 1)


def _hoja_b(ws, receta: RecetaEncuesta, filas) -> None:
    ident = ["Respuesta número", "Nombre completo del usuario", "Dirección de correo", "Fecha", "Programa POS", "Módulo"]
    preguntas = []
    for k in ("a1", "a2"):
        preguntas += [f"A {k[1]}. {PREG_B[k]}", f"A {k[1]}. N°{PREG_B[k]}"]
    preguntas += ["Experiencia cualitativa promedio docente", "Experiencia promedio docente"]
    preguntas += [f"A 4. {PREG_B['a4']}", f"A 4. N°{PREG_B['a4']}", f"A 3. {PREG_B['com']}", f"A 3. N°{PREG_B['com']}"]
    cols = ident + preguntas
    orden = list(range(len(cols)))
    if receta.barajar:
        random.Random(11).shuffle(orden)
    for c, i in enumerate(orden, start=1):
        ws.cell(row=1, column=c, value=receta.cab_identidad.get(cols[i], cols[i]))
    for r, f in enumerate(filas, start=2):
        n, nombre, fecha, pos, mod, a1t, a1n, a2t, a2n, a4t, a4n, com = f
        valores = [n, nombre, CORREO_FICTICIO, _fecha(fecha), pos, mod, a1t, a1n, a2t, a2n, "De Acuerdo", 4, a4t, a4n, com, None]
        for c, i in enumerate(orden, start=1):
            ws.cell(row=r, column=c, value=valores[i])


def construir(receta: RecetaEncuesta, carpeta: Path, con_hoja_b: bool = True) -> Path:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    _hoja_a(wb.create_sheet(receta.hoja_a), receta, FILAS_A)
    if con_hoja_b:
        _hoja_b(wb.create_sheet(receta.hoja_b), receta, FILAS_B)
    ws_o = wb.create_sheet(receta.hoja_oculta)
    _hoja_a(ws_o, receta, FILAS_A[:4])
    ws_o.sheet_state = "hidden"
    _hoja_a(wb.create_sheet(receta.hoja_borrador), receta, FILAS_A[:3])
    ruta = carpeta / receta.archivo
    wb.save(ruta)
    return ruta
