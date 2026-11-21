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


# ── FU-L1b: libro de planificación con hojas ocultas ──────────────────

CABECERAS_PLAN = ["N°", "AÑO", "MES", "POS", "PROGRAMA", "ESTADO", "N° INSCRITOS", "LEADS"]


def _hoja_plan_mensual(ws, anio: int, mes: int, n: int, base_pos: int) -> None:
    for c, v in enumerate(CABECERAS_PLAN, start=1):
        ws.cell(row=1, column=c, value=v)
    for i in range(n):
        r = 2 + i
        for c, v in enumerate([i + 1, anio, mes, base_pos + i, f"DIPLOMADO FICTICIO {base_pos + i}",
                               "Inicio Confirmado", 2 + i, 20 + 3 * i], start=1):
            ws.cell(row=r, column=c, value=v)


def _hoja_informe_metas(ws, gestion: int) -> None:
    ws.cell(row=1, column=1, value=f"GESTIÓN {gestion}")
    cab = ["MES", "META (PROGRAMAS REGULARES Y TECHOS)", "INGRESO PROYECTADO TECHOS", "META"]
    for c, v in enumerate(cab, start=1):
        ws.cell(row=2, column=c, value=v)
    for i, mes in enumerate(["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO"]):
        for c, v in enumerate([mes, 100000 + 1000 * i, 5000 + 100 * i, 3 + i], start=1):
            ws.cell(row=3 + i, column=c, value=v)


@dataclass
class RecetaPlan:
    archivo: str
    visible: str          # período 2027-03, visible
    oculta_libre: str     # período 2027-01, oculta, sin hoja visible -> se usa
    oculta_cubierta: str  # período 2027-03, oculta, ya cubierto por la visible -> se ignora como duplicada
    oculta_borrador: str  # período 2027-02, oculta y borrador -> se ignora
    oculta_informe: str   # informe de metas oculto -> se usa


PLAN_ORIGINAL = RecetaPlan(archivo="plan_ficticio.xlsx", visible="Marzo-2027", oculta_libre="Enero-2027",
                           oculta_cubierta="Marzo-2027 (2)", oculta_borrador="Febrero-2027 borrador",
                           oculta_informe="Informe anual")
PLAN_VARIANTE = RecetaPlan(archivo="Seguimiento captación v3.xlsx", visible="Programas del trimestre",
                           oculta_libre="respaldo enero", oculta_cubierta="tercer mes viejo",
                           oculta_borrador="feb boor", oculta_informe="Metas de la gestión")


def construir_plan(receta: RecetaPlan, carpeta: Path) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = receta.visible
    _hoja_plan_mensual(ws, 2027, 3, 5, 9300)
    for titulo, mes, n, base in ((receta.oculta_libre, 1, 4, 9100), (receta.oculta_cubierta, 3, 5, 9300),
                                 (receta.oculta_borrador, 2, 3, 9200)):
        wo = wb.create_sheet(titulo)
        _hoja_plan_mensual(wo, 2027, mes, n, base)
        wo.sheet_state = "hidden"
    wi = wb.create_sheet(receta.oculta_informe)
    _hoja_informe_metas(wi, 2027)
    wi.sheet_state = "hidden"
    return _guardar(wb, carpeta / receta.archivo)


# ── FU-L2: libro de cobranza con mora, cartera y pagos por mes (datos ficticios) ──────────────────

# Campo canónico -> cabecera del libro ORIGINAL. Las tres columnas «MORA» del original son
# DIAS DE MORA, RANGO MORA y TOTAL CUOTAS EN MORA; solo la última es un conteo de cuotas.
CAB_L2_ORIGINAL = {
    "pos": "POS", "programa": "NOMBRE DEL PROGRAMA", "ci": "CI", "nombres": "NOMBRES", "paterno": "PATERNO",
    "dias_mora": "DIAS DE MORA", "inicio": "FECHA INICIO DIPLOMADO", "estado": "TIPO DE CARTERA",
    "deuda": "DEUDA TOTAL", "rango": "RANGO MORA", "cuotas": "TOTAL CUOTAS EN MORA",
    "total_pagado": "TOTAL PAGADO HASTA LA FECHA", "a_cobrar": "MONTO A COBRAR DESPUÉS DE DESCUENTO",
}
# Variante: sinónimos del catálogo y una cabecera «MORA» suelta con valores que, de usarse como cuotas,
# cambiarían el resultado (la ambigua no debe pisar a la específica).
CAB_L2_VARIANTE = {
    "pos": "POS", "programa": "NOMBRE DEL PROGRAMA", "ci": "CI", "nombres": "NOMBRES", "paterno": "PATERNO",
    "dias_mora": "DIAS EN MORA", "inicio": "FECHA DE INICIO", "estado": "ESTADO DE CARTERA",
    "deuda": "SALDO DEUDOR", "rango": "RANGO MORA", "cuotas": "CUOTAS IMPAGAS",
    "total_pagado": "TOTAL PAGADO", "a_cobrar": "MONTO A COBRAR DESPUÉS DE DESCUENTO",
}
MESES_L2 = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE",
            "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]


# CI y nombres ficticios y distintos entre sí (CI consecutivos se confundirían con una variante de escritura, regla 85 %)
CIS_L2 = ["4100123", "5230987", "6340456", "7451789", "8562012", "3673345", "2784678", "1895901", "9016234", "1127567"]
NOMBRES_L2 = [("ANA", "FICTICIA"), ("LUIS", "PRUEBAS"), ("EVA", "MUESTRAL"), ("JUAN", "EJEMPLAR"), ("RUTH", "SIMULADA"),
              ("OMAR", "FALSETTI"), ("INES", "IMAGINARIA"), ("PAUL", "VIRTUALES"), ("LEA", "SUPUESTA"), ("TITO", "INVENTADO")]


def filas_cobranza_l2() -> List[Dict[str, object]]:
    """10 estudiantes ficticios, uno por regla. `pagos` = {(año, mes): monto}; `preliminar` = pago que no se carga."""
    from datetime import datetime

    def f(i, estado, cuotas, deuda, inicio, pagos, dias=None, rango="", preliminar=None):
        return {"pos": f"POS-{9300 + i}", "programa": f"DIPLOMADO FICTICIO {i}",
                "ci": CIS_L2[i - 1], "nombres": NOMBRES_L2[i - 1][0], "paterno": NOMBRES_L2[i - 1][1], "dias_mora": dias,
                "inicio": inicio, "estado": estado, "deuda": deuda, "rango": rango, "cuotas": cuotas,
                "pagos": pagos, "a_cobrar": 7777 + i, "preliminar": preliminar or {}}

    return [
        f(1, "CARTERA VIGENTE", 0, 500, datetime(2024, 3, 4), {(2024, 3): 100, (2024, 4): 100}),
        f(2, "CARTERA CERRADA", 3, 0, datetime(2024, 5, 6), {(2024, 5): 250, (2025, 1): 50}, dias=0, rango="Sin mora"),
        f(3, "CARTERA EN MORA", 2, 1200, datetime(2025, 2, 10), {(2025, 2): 300, (2025, 3): 300}, dias=45, rango="b) 31 a 60"),
        f(4, "CARTERA PREVISIONABLE", 1, 900, datetime(2025, 6, 2), {(2025, 6): 120}, dias=120, rango="d) Mayor 90"),
        f(5, "CARTERA INCOBRABLE", 5, 2000, datetime(2026, 1, 15), {(2026, 1): 80}, dias=400),
        f(6, "CARTERA VIGENTE", -4, 100, datetime(2026, 2, 3), {(2026, 2): 60}),                 # cuotas negativas -> 0
        f(7, "CARTERA VIGENTE", "1s", 100, datetime(2026, 3, 9), {(2026, 3): 40}),                # texto «1s» -> 1
        f(8, "CARTERA CERRADA", 0, -300, datetime(2025, 8, 12), {(2025, 8): 700}),                # sobrepago -> deuda 0
        f(9, "CARTERA RARA", 2, 400, datetime(2025, 9, 1), {(2025, 9): 10}),                      # fuera de catálogo
        f(10, "CARTERA VIGENTE", 0, 50, datetime(2024, 11, 20), {(2024, 11): 25}, preliminar={(2025, 9): 999}),
    ]


# Lo que debe cargarse (cifras de la receta, calculadas a mano): pagos por año del MES DE PAGO (sin PRELIMINAR)
PAGOS_ESPERADOS_L2 = {2024: 100 + 100 + 250 + 25, 2025: 50 + 300 + 300 + 120 + 700 + 10, 2026: 80 + 60 + 40}
# Situaciones en mora (cuotas >= 2, DA3) por año de inicio: filas 2 (2024), 3 y 9 (2025), 5 (2026)
MORA_ESPERADA_L2 = {2024: 1, 2025: 2, 2026: 1}
ESTADOS_FUENTE_ESPERADOS_L2 = {"VIGENTE": 4, "CERRADA": 2, "EN MORA": 1, "PREVISIONABLE": 1, "INCOBRABLE": 1, None: 1}


@dataclass
class RecetaCobranzaL2:
    archivo: str
    hoja_datos: str
    hoja_oculta: str
    cabeceras: Dict[str, str]
    prefijo_mes: str                      # «MONTO» o «PAGO»
    orden: List[str]                      # orden de los campos y de las columnas «mes:AAAA-MM» / «prelim:AAAA-MM»
    con_mora_suelta: bool = False
    filas_basura: int = 25
    hoja_extra: str = ""                  # hoja visible de resumen (no es tabla de datos)


ORIGINAL_L2 = RecetaCobranzaL2(
    archivo="cobranza_ficticia.xlsx", hoja_datos="Cartera por estudiante", hoja_oculta="Cartera previa",
    cabeceras=CAB_L2_ORIGINAL, prefijo_mes="MONTO",
    orden=["pos", "programa", "ci", "nombres", "paterno", "dias_mora", "inicio", "estado", "a_cobrar", "deuda",
           "mes:2024-03", "mes:2024-04", "mes:2024-05", "mes:2024-11", "mes:2025-01", "mes:2025-02",
           "mes:2025-03", "mes:2025-06", "mes:2025-08", "mes:2025-09", "mes:2026-01", "mes:2026-02", "mes:2026-03",
           "prelim:2025-09", "total_pagado", "rango", "cuotas"],
    hoja_extra="Resumen mensual",
)

VARIANTE_L2 = RecetaCobranzaL2(
    archivo="Libro de Cobros (copia final).xlsx", hoja_datos="Base deudores 24-26", hoja_oculta="respaldo viejo",
    cabeceras=CAB_L2_VARIANTE, prefijo_mes="PAGO", con_mora_suelta=True, filas_basura=70,
    orden=["cuotas", "mes:2026-03", "ci", "estado", "prelim:2025-09", "pos", "mes:2025-06", "deuda",
           "mes:2024-04", "paterno", "mes:2026-01", "mes:2025-01", "inicio", "total_pagado", "mes:2025-09",
           "programa", "mes:2024-03", "a_cobrar", "rango", "mes:2025-02", "mes:2024-05", "nombres",
           "mes:2026-02", "mes:2024-11", "dias_mora", "mes:2025-03", "mes:2025-08"],
    hoja_extra="Totales por mes",
)


def _cabecera_l2(receta: RecetaCobranzaL2, clave: str) -> str:
    if clave.startswith(("mes:", "prelim:")):
        tipo, periodo = clave.split(":")
        anio, mes = periodo.split("-")
        base = f"{receta.prefijo_mes} {MESES_L2[int(mes) - 1]} {anio}"
        return base + (" (PRELIMINAR)" if tipo == "prelim" else "")
    return receta.cabeceras[clave]


def _celda_l2(fila: Dict[str, object], clave: str):
    if clave.startswith("mes:"):
        anio, mes = clave.split(":")[1].split("-")
        return fila["pagos"].get((int(anio), int(mes)))
    if clave.startswith("prelim:"):
        anio, mes = clave.split(":")[1].split("-")
        return fila["preliminar"].get((int(anio), int(mes)))
    if clave == "total_pagado":
        return sum(fila["pagos"].values())
    return fila.get(clave)


def construir_cobranza_l2(receta: RecetaCobranzaL2, carpeta: Path) -> Path:
    """Libro de cobranza FU-L2: hoja de datos (con subtotal y filas basura), hoja oculta con otras cifras y un resumen."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    filas = filas_cobranza_l2()
    ws = wb.create_sheet(receta.hoja_datos)
    columnas = list(receta.orden)
    cabeceras = [_cabecera_l2(receta, c) for c in columnas]
    if receta.con_mora_suelta:
        columnas.insert(3, "mora_suelta")
        cabeceras.insert(3, "MORA")
    for c, nombre in enumerate(cabeceras, start=1):
        ws.cell(row=1, column=c, value=nombre)
    r = 1
    for fila in filas:
        r += 1
        for c, clave in enumerate(columnas, start=1):
            valor = 99 if clave == "mora_suelta" else _celda_l2(fila, clave)
            if valor is not None:
                ws.cell(row=r, column=c, value=valor)
    r += 1
    ws.cell(row=r, column=columnas.index("programa") + 1, value="TOTAL GENERAL")
    for k in range(receta.filas_basura):   # filas fantasma: casilla FALSE suelta
        r += 1
        ws.cell(row=r, column=len(columnas), value=False if k % 2 else None)
    wo = wb.create_sheet(receta.hoja_oculta)   # misma forma, otras cifras: no debe sumar
    for c, nombre in enumerate(cabeceras, start=1):
        wo.cell(row=1, column=c, value=nombre)
    for k, fila in enumerate(filas[:3], start=2):
        for c, clave in enumerate(columnas, start=1):
            valor = 55555 if clave.startswith("mes:") else (99 if clave in ("cuotas", "mora_suelta") else _celda_l2(fila, clave))
            if valor is not None:
                wo.cell(row=k, column=c, value=valor)
    wo.sheet_state = "hidden"
    wr = wb.create_sheet(receta.hoja_extra)
    for c, v in enumerate(["MES", "TOTAL"], start=1):
        wr.cell(row=1, column=c, value=v)
    for k, mes in enumerate(MESES_L2[:4], start=2):
        wr.cell(row=k, column=1, value=mes)
        wr.cell(row=k, column=2, value=f"Bs{k * 1000}")
    return _guardar(wb, carpeta / receta.archivo)
