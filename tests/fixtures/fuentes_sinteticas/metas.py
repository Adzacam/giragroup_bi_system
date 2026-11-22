"""
FU-L6: libros sintéticos de metas y ejecutado (categoría x mes) con datos ficticios.

Dos tipos de fuente con la misma forma de tabla que las reales, pero con otros nombres de archivo y de hoja y columnas en otro orden:
- RENTABILIDAD: CATEGORIA, MES, MES NUMERICO, EJECUTADO <año>, META POR CATEGORIA <año> (una fila por categoría y mes);
- EGRESOS (resumen mensual): TIPO DE INGRESO, MES, MES NUMERICO, EJECUTADO <año>, META <año>.

Gestiones del libro de RENTABILIDAD (años ficticios lejos de los reales):
- 2030: ejecutado de 12 meses y NINGUNA meta (gestión sin meta);
- 2031: ejecutado de 12 meses y una SOLA celda de meta (TECHOS_CERRADOS, diciembre): meta ANUAL;
- 2032: ejecutado de 12 meses y meta de los 12 meses en las dos categorías: meta MENSUAL;
- 2033: ejecutado de enero a mayo (el mes de corte es mayo, parcial: 2033-05 trae solo una fracción) y meta mensual completa.

El libro de EGRESOS trae solo 2032 (ejecutado y meta por tipo de ingreso) y difiere del de RENTABILIDAD en tres celdas:
- meta de abril de PROGRAMAS: +100.000 (múltiplo de 100.000: se avisa al área financiera);
- meta de junio de PROGRAMAS: +12.345 (diferencia que no es múltiplo);
- ejecutado de marzo de PROGRAMAS: -5.000.
Además trae un 0 donde RENTABILIDAD trae ejecutado (mes sin ejecutar de otra fuente: no es una cifra y no es conflicto).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import openpyxl

MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
CATEGORIAS = ["PROGRAMAS", "TECHOS/CERRADOS"]
CATEGORIA_CANONICA = {"PROGRAMAS": "PROGRAMAS", "TECHOS/CERRADOS": "TECHOS_CERRADOS"}
TIPO_INGRESO = {"PROGRAMAS": "POR PROGRAMAS", "TECHOS/CERRADOS": "POR TECHOS/CERRADOS"}


def ejecutado(cat: str, anio: int, mes: int) -> float:
    base = 100_000 if cat == "PROGRAMAS" else 10_000
    return float(base + (anio - 2000) * 1_000 + mes * 100)


def meta_mensual(cat: str, anio: int, mes: int) -> float:
    base = 120_000 if cat == "PROGRAMAS" else 12_000
    return float(base + (anio - 2000) * 1_000 + mes * 100)


META_ANUAL_2031 = 6_000_000.0
EJECUTADO_PARCIAL_2033_05 = 500.0     # fracción de un mes completo (el mes de corte)


def celda_ejecutado(cat: str, anio: int, mes: int) -> Optional[float]:
    if anio in (2030, 2031, 2032):
        return ejecutado(cat, anio, mes)
    if anio == 2033:
        if mes <= 4:
            return ejecutado(cat, anio, mes)
        if mes == 5:
            return EJECUTADO_PARCIAL_2033_05
    return None


def celda_meta(cat: str, anio: int, mes: int) -> Optional[float]:
    if anio == 2031:
        return META_ANUAL_2031 if (cat == "TECHOS/CERRADOS" and mes == 12) else None
    if anio in (2032, 2033):
        return meta_mensual(cat, anio, mes)
    return None


# Esperado en fact_rentabilidad tras cargar el libro de RENTABILIDAD: (categoría canónica, año, mes) -> (ejecutado, meta, granularidad)
def esperado_rentabilidad() -> Dict[Tuple[str, int, int], Tuple[Optional[float], Optional[float], Optional[str]]]:
    esp = {}
    for cat in CATEGORIAS:
        for anio in (2030, 2031, 2032, 2033):
            for mes in range(1, 13):
                e, m = celda_ejecutado(cat, anio, mes), celda_meta(cat, anio, mes)
                if e is None and m is None:
                    continue
                gran = None if m is None else ("ANUAL" if anio == 2031 else "MENSUAL")
                esp[(CATEGORIA_CANONICA[cat], anio, mes)] = (e, m, gran)
    return esp


@dataclass
class RecetaMetas:
    archivo_rent: str
    hoja_rent: str
    archivo_egr: str
    hoja_egr: str
    cab_rent: List[str]
    cab_egr: List[str]


ORIGINAL = RecetaMetas(
    archivo_rent="cumplimiento_ingresos.xlsx", hoja_rent="Detalle", archivo_egr="resumen_ingresos_mensual.xlsx", hoja_egr="Mensual",
    cab_rent=["CATEGORIA", "MES", "MES NUMERICO", "EJECUTADO 2030", "EJECUTADO 2031", "META POR CATEGORIA 2031",
              "EJECUTADO 2032", "META POR CATEGORIA 2032", "EJECUTADO 2033", "META POR CATEGORIA 2033"],
    cab_egr=["TIPO DE INGRESO", "MES", "MES NUMERICO", "EJECUTADO 2032", "META 2032"],
)

VARIANTE = RecetaMetas(
    archivo_rent="Ingresos vs presupuesto (versión final).xlsx", hoja_rent="Cuadro 1", archivo_egr="Libro de gestiones 2032.xlsx", hoja_egr="Resumen",
    cab_rent=["META POR CATEGORIA 2033", "EJECUTADO 2031", "MES NUMERICO", "EJECUTADO 2033", "CATEGORIA", "META POR CATEGORIA 2032",
              "META POR CATEGORIA 2031", "MES", "EJECUTADO 2032", "EJECUTADO 2030"],
    cab_egr=["META 2032", "MES", "TIPO DE INGRESO", "EJECUTADO 2032", "MES NUMERICO"],
)


def _celda_rent(cab: str, cat: str, mes: int) -> object:
    if cab == "CATEGORIA":
        return cat
    if cab == "MES":
        return MESES[mes - 1]
    if cab == "MES NUMERICO":
        return float(mes)
    tipo, anio = cab.rsplit(" ", 1)
    anio = int(anio)
    return celda_ejecutado(cat, anio, mes) if tipo == "EJECUTADO" else celda_meta(cat, anio, mes)


def construir_rentabilidad(carpeta: Path, receta: RecetaMetas) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = receta.hoja_rent
    ws.append(receta.cab_rent)
    for cat in CATEGORIAS:
        for mes in range(1, 13):
            ws.append([_celda_rent(c, cat, mes) for c in receta.cab_rent])
    ruta = carpeta / receta.archivo_rent
    wb.save(ruta)
    return ruta


# Celdas del libro de EGRESOS que difieren del de RENTABILIDAD (todas de 2032)
DIF_META_ABRIL_PROGRAMAS = 100_000.0
DIF_META_JUNIO_PROGRAMAS = 12_345.0
DIF_EJEC_MARZO_PROGRAMAS = -5_000.0


def _celda_egr(cab: str, cat: str, mes: int) -> object:
    if cab == "TIPO DE INGRESO":
        return TIPO_INGRESO[cat]
    if cab == "MES":
        return MESES[mes - 1]
    if cab == "MES NUMERICO":
        return float(mes)
    if cab == "EJECUTADO 2032":
        if cat == "PROGRAMAS" and mes == 3:
            return ejecutado(cat, 2032, mes) + DIF_EJEC_MARZO_PROGRAMAS
        if cat == "TECHOS/CERRADOS" and mes == 7:
            return 0.0      # otra fuente trae 0 donde RENTABILIDAD trae una cifra: no es una cifra ni un conflicto
        return ejecutado(cat, 2032, mes)
    if cab == "META 2032":
        extra = DIF_META_ABRIL_PROGRAMAS if (cat == "PROGRAMAS" and mes == 4) else DIF_META_JUNIO_PROGRAMAS if (cat == "PROGRAMAS" and mes == 6) else 0.0
        return meta_mensual(cat, 2032, mes) + extra
    raise KeyError(cab)


def construir_egresos(carpeta: Path, receta: RecetaMetas) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = receta.hoja_egr
    ws.append(receta.cab_egr)
    for cat in CATEGORIAS:
        for mes in range(1, 13):
            ws.append([_celda_egr(c, cat, mes) for c in receta.cab_egr])
    ruta = carpeta / receta.archivo_egr
    wb.save(ruta)
    return ruta


# Conflictos esperados entre los dos libros: (campo, categoría canónica, mes) -> (valor elegido de RENTABILIDAD, valor descartado de EGRESOS)
def conflictos_esperados() -> Dict[Tuple[str, str, int], Tuple[float, float]]:
    return {
        ("monto_ejecutado", "PROGRAMAS", 3): (ejecutado("PROGRAMAS", 2032, 3), ejecutado("PROGRAMAS", 2032, 3) + DIF_EJEC_MARZO_PROGRAMAS),
        ("monto_meta", "PROGRAMAS", 4): (meta_mensual("PROGRAMAS", 2032, 4), meta_mensual("PROGRAMAS", 2032, 4) + DIF_META_ABRIL_PROGRAMAS),
        ("monto_meta", "PROGRAMAS", 6): (meta_mensual("PROGRAMAS", 2032, 6), meta_mensual("PROGRAMAS", 2032, 6) + DIF_META_JUNIO_PROGRAMAS),
    }
