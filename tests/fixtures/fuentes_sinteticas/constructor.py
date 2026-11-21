"""
Constructor de libros sintéticos para FU-L1 (datos ficticios, sin PII real).

Cada libro se arma con openpyxl a partir de una «receta» (roles de hoja), de modo que el
libro original y su variante tengan los mismos datos con:
- otro nombre de archivo y de hoja,
- columnas de la tabla de datos en otro orden,
- hojas basura con otros nombres (oculta, borrador, copia, tabla dinámica, hoja numerada,
  resumen con montos en texto), en otro orden dentro del libro,
- subtotales, filas fantasma (casillas FALSE arrastradas y filas con solo el número de orden)
  y una fórmula sin valor guardado (openpyxl nunca guarda el valor calculado).

Criterio de aceptación de FU-L1: el resultado del lector (hojas usadas, filas leídas, hojas
ignoradas con motivo) es idéntico para el original y para la variante.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import openpyxl

# Personas y correos ficticios: deben desaparecer de cualquier registro o salida.
CORREO_FICTICIO = "persona.ficticia@ejemplo.test"
CIS_FICTICIOS = ["9100001", "9100002", "9100003", "9100004", "9100005", "9100006"]
NOMBRES_FICTICIOS = ["ANA FICTICIA RUIZ", "LUIS PRUEBA GOMEZ", "EVA MUESTRA SOLIS",
                     "JUAN EJEMPLO VACA", "RUTH SIMULADA PAZ", "OMAR FALSO LIMA"]

CABECERAS_COBRANZA = ["N°", "POS", "NOMBRE DEL PROGRAMA", "CI", "NOMBRES", "TIPO DE CARTERA",
                      "TOTAL CUOTAS EN MORA", "DIAS DE MORA", "MONTO ENERO 2025", "MONTO FEBRERO 2025",
                      "TOTAL PAGADO", "VALIDADO"]


def filas_cobranza() -> List[Dict[str, object]]:
    filas = []
    for i, (ci, nombre) in enumerate(zip(CIS_FICTICIOS, NOMBRES_FICTICIOS), start=1):
        filas.append({
            "N°": i, "POS": f"POS-{9000 + i}", "NOMBRE DEL PROGRAMA": f"DIPLOMADO FICTICIO {i}",
            "CI": ci, "NOMBRES": nombre, "TIPO DE CARTERA": "VIGENTE" if i % 2 else "CARTERA CERRADA",
            "TOTAL CUOTAS EN MORA": i % 3, "DIAS DE MORA": 10 * (i % 3),
            "MONTO ENERO 2025": 500 + i, "MONTO FEBRERO 2025": 400 + i,
            "TOTAL PAGADO": None,  # se escribe como fórmula (sin valor guardado)
            "VALIDADO": True,
        })
    return filas


@dataclass
class Receta:
    """Nombres de cada rol de hoja y orden de columnas; el contenido es el mismo en todas las variantes."""
    archivo: str
    hoja_datos: str
    hoja_oculta: str
    hoja_borrador: str
    hoja_copia: str
    hoja_dinamica: str
    hoja_numerada: str
    hoja_resumen: str
    orden_columnas: List[str] = field(default_factory=lambda: list(CABECERAS_COBRANZA))
    orden_hojas: List[str] = field(default_factory=lambda: [
        "datos", "oculta", "borrador", "copia", "dinamica", "numerada", "resumen"])
    filas_fantasma: int = 60
    con_correo_en_cabecera: bool = False


ORIGINAL = Receta(
    archivo="cartera_original.xlsx", hoja_datos="Cartera 2025", hoja_oculta="Cartera vieja",
    hoja_borrador="Cartera borrador", hoja_copia="Copia de Cartera 2025", hoja_dinamica="Tabla dinámica 1",
    hoja_numerada="Hoja 3", hoja_resumen="Totales",
)

VARIANTE = Receta(
    archivo="Libro Cobros (v2) final.xlsx", hoja_datos="Base de deudores", hoja_oculta="respaldo",
    hoja_borrador="Deudores boor", hoja_copia="Copia de Base de deudores", hoja_dinamica="Tabla dinámica 7",
    hoja_numerada="Hoja 11", hoja_resumen="Resumen anual",
    orden_columnas=["TIPO DE CARTERA", "CI", "MONTO FEBRERO 2025", "NOMBRES", "POS", "N°", "DIAS DE MORA",
                    "NOMBRE DEL PROGRAMA", "MONTO ENERO 2025", "VALIDADO", "TOTAL CUOTAS EN MORA", "TOTAL PAGADO"],
    orden_hojas=["resumen", "numerada", "datos", "copia", "dinamica", "oculta", "borrador"],
    filas_fantasma=140,
)


def _escribir_tabla(ws, columnas: List[str], filas: List[Dict[str, object]], fila_cab: int = 1,
                    con_formula: bool = True, subtotal: bool = True, fantasma: int = 0) -> None:
    for c, nombre in enumerate(columnas, start=1):
        ws.cell(row=fila_cab, column=c, value=nombre)
    r = fila_cab
    for fila in filas:
        r += 1
        for c, nombre in enumerate(columnas, start=1):
            valor = fila.get(nombre)
            if nombre == "TOTAL PAGADO" and con_formula:
                c_ene = openpyxl.utils.get_column_letter(columnas.index("MONTO ENERO 2025") + 1)
                c_feb = openpyxl.utils.get_column_letter(columnas.index("MONTO FEBRERO 2025") + 1)
                valor = f"={c_ene}{r}+{c_feb}{r}"
            ws.cell(row=r, column=c, value=valor)
    if subtotal:
        r += 1
        primera_texto = next(c for c, n in enumerate(columnas, start=1) if n not in ("N°",))
        ws.cell(row=r, column=primera_texto, value="TOTAL GENERAL")
        c_ene = columnas.index("MONTO ENERO 2025") + 1
        ws.cell(row=r, column=c_ene, value=sum(int(f["MONTO ENERO 2025"]) for f in filas))
    # Filas fantasma: casilla FALSE arrastrada en «VALIDADO» y número de orden sin datos
    c_val = columnas.index("VALIDADO") + 1 if "VALIDADO" in columnas else None
    c_ord = columnas.index("N°") + 1 if "N°" in columnas else None
    for k in range(fantasma):
        r += 1
        if c_val and k % 2 == 0:
            ws.cell(row=r, column=c_val, value=False)
        elif c_ord:
            ws.cell(row=r, column=c_ord, value=len(filas) + k + 1)


def construir(receta: Receta, carpeta: Path) -> Path:
    """Escribe el libro de la receta en `carpeta` y devuelve su ruta."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    filas = filas_cobranza()
    for rol in receta.orden_hojas:
        if rol == "datos":
            ws = wb.create_sheet(receta.hoja_datos)
            cols = list(receta.orden_columnas)
            _escribir_tabla(ws, cols, filas, fantasma=receta.filas_fantasma)
            if receta.con_correo_en_cabecera:
                ws.cell(row=1, column=len(cols) + 1, value=CORREO_FICTICIO)
                for r in range(2, 2 + len(filas)):
                    ws.cell(row=r, column=len(cols) + 1, value=r)
        elif rol == "oculta":
            ws = wb.create_sheet(receta.hoja_oculta)
            _escribir_tabla(ws, list(receta.orden_columnas), filas[:4], subtotal=False)
            ws.sheet_state = "hidden"
        elif rol == "borrador":
            ws = wb.create_sheet(receta.hoja_borrador)
            _escribir_tabla(ws, list(receta.orden_columnas), filas[:3], subtotal=False)
        elif rol == "copia":
            ws = wb.create_sheet(receta.hoja_copia)
            _escribir_tabla(ws, list(receta.orden_columnas), filas[:5], subtotal=False)
        elif rol == "dinamica":
            wb.create_sheet(receta.hoja_dinamica)  # vacía, como una tabla dinámica sin refrescar
        elif rol == "numerada":
            ws = wb.create_sheet(receta.hoja_numerada)
            for c, v in enumerate(["POS", "NOMBRE DEL PROGRAMA", "INSCRITOS"], start=1):
                ws.cell(row=1, column=c, value=v)
            for r in range(2, 9):
                ws.cell(row=r, column=1, value=f"POS-{9000 + r}")
                ws.cell(row=r, column=2, value=f"DIPLOMADO FICTICIO {r}")
                ws.cell(row=r, column=3, value=r * 3)
        elif rol == "resumen":
            ws = wb.create_sheet(receta.hoja_resumen)
            for c, v in enumerate(["MES", "EJECUTADO 2024", "EJECUTADO 2025", "META 2025"], start=1):
                ws.cell(row=1, column=c, value=v)
            for r, mes in enumerate(["ENERO", "FEBRERO", "MARZO", "ABRIL"], start=2):
                ws.cell(row=r, column=1, value=mes)
                for c in (2, 3, 4):
                    ws.cell(row=r, column=c, value=f"Bs{(r * c * 1000):,}".replace(",", "."))
    ruta = carpeta / receta.archivo
    wb.save(ruta)
    return ruta


def construir_libro_mixto(carpeta: Path, nombre: str = "acta_mixta.xlsx",
                          hoja_actas: str = "Notas", hoja_plan: str = "Planificación por POS") -> Path:
    """Libro de actas con una hoja de planificación por POS (leads e inscritos) y una de encuesta por módulo
    con cabecera en dos niveles y filas fantasma de solo número de orden al final."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = hoja_actas
    cab = ["POS - ACTAS", "CEDULA DE IDENTIDAD", "NOMBRES", "MÓDULO 1", "MÓDULO 2", "ESTADO ACADEMICO"]
    for c, v in enumerate(cab, start=1):
        ws.cell(row=1, column=c, value=v)
    for r, (ci, nom) in enumerate(zip(CIS_FICTICIOS[:3], NOMBRES_FICTICIOS[:3]), start=2):
        for c, v in enumerate(["POS-9876", ci, nom, 80 + r, 70 + r, "Aprobado"], start=1):
            ws.cell(row=r, column=c, value=v)

    wp = wb.create_sheet(hoja_plan)
    cab_p = ["N°", "POS - PLAN", "NOMBRE DEL PROGRAMA", "ESTADO PROGRAMA", "META 2025", "N° DE INSCRITOS", "LEADS"]
    for c, v in enumerate(cab_p, start=1):
        wp.cell(row=1, column=c, value=v)
    for r in range(2, 8):
        for c, v in enumerate([r - 1, f"POS-{9100 + r}", f"DIPLOMADO FICTICIO {r}", "Inicio Confirmado",
                               1000 * r, r, 10 * r], start=1):
            wp.cell(row=r, column=c, value=v)
    return _guardar(wb, carpeta / nombre)


def construir_encuesta_por_modulo(carpeta: Path, nombre: str = "encuesta_modulos.xlsx",
                                  hoja: str = "Evaluación por módulo", n_respuestas: int = 6,
                                  fantasma: int = 40) -> Path:
    """Encuesta con fila de grupo combinada, cabecera en la fila 2 y una cola de filas con solo «N°»."""
    preguntas = ["El contenido del módulo fue pertinente para mi campo profesional.",
                 "La metodología empleada favoreció la reflexión crítica del tema.",
                 "Las actividades prácticas conectaron la teoría con la realidad profesional."]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = hoja
    ws.cell(row=1, column=1, value="Información básica")
    ws.cell(row=1, column=5, value="Bloque 1. Pertinencia")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=4)
    cab = ["N°", "Nombre completo del usuario", "Fecha", "Programa - POS", "Número del modulo"] + preguntas
    for c, v in enumerate(cab, start=1):
        ws.cell(row=2, column=c, value=v)
    etiquetas = ["5/Totalmente de acuerdo", "4/De acuerdo", "3/Neutral"]
    for i in range(n_respuestas):
        r = 3 + i
        valores = [i + 1, NOMBRES_FICTICIOS[i % len(NOMBRES_FICTICIOS)], f"0{1 + i % 9}/03/2026",
                   "POS-9876", 1 + i % 2] + [etiquetas[(i + j) % 3] for j in range(len(preguntas))]
        for c, v in enumerate(valores, start=1):
            ws.cell(row=r, column=c, value=v)
    for k in range(fantasma):
        ws.cell(row=3 + n_respuestas + k, column=1, value=n_respuestas + k + 1)
    return _guardar(wb, carpeta / nombre)


def _guardar(wb, ruta: Path) -> Path:
    wb.save(ruta)
    return ruta


def construir_par(carpeta: Path, receta_a: Optional[Receta] = None, receta_b: Optional[Receta] = None):
    return construir(receta_a or ORIGINAL, carpeta), construir(receta_b or VARIANTE, carpeta)
