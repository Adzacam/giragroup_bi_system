"""L4-0: inventario de metas y ejecucion en EJECUTADO VS META.xlsx y BD Egresos.xlsx.

Solo lectura. Imprime hashes, hojas, cabeceras, formulas y comparaciones entre hojas.
No imprime nombres ni datos personales (los archivos financieros no los contienen en estas hojas).
Uso: python -I adw_l4_0_fuentes_metas.py <carpeta_con_los_dos_xlsx> [csv_dw_rentabilidad]
"""
import csv
import hashlib
import os
import re
import sys

import openpyxl

EVM = "EJECUTADO VS META.xlsx"
EGR = "BD Egresos.xlsx"
CANDIDATOS = [
    "backend/docs/evidencias/ciclo_mensual_slices",
    "uploads/data",
    "output/backups/f0_lote/originales",
    "output/backups/f0_lote/slices",
    "output/backups/f0_lote/generador/uploads/data",
    "output/backups/f0_lote/corridas/f0_a0_llena_r1_interrumpida/landing/1",
    "output/lote1387_archivos",
]
MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO",
         "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
MONEDA_TXT = re.compile(r"^Bs\s*(\d{1,3}(\.\d{3})+|\d+)(,\d+)?$")


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def num(v):
    """Convierte numero, texto 'Bs1.198.653' o vacio. Otros textos -> None."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if MONEDA_TXT.match(s):
        s = s.replace("Bs", "").strip()
        if re.match(r"^\d{1,3}(\.\d{3})+$", s):
            return float(s.replace(".", ""))
        return float(s.replace(".", "").replace(",", "."))
    try:
        return float(s)
    except ValueError:
        return None


def hojas_resumen(ruta):
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}


def formulas(ruta):
    wb = openpyxl.load_workbook(ruta, read_only=False, data_only=False)
    out = {}
    for ws in wb.worksheets:
        n = 0
        for fila in ws.iter_rows():
            for c in fila:
                if isinstance(c.value, str) and c.value.startswith("="):
                    n += 1
        out[ws.title] = n
    return out


def paso_inventario(raiz):
    print("## 1. Hashes (sha256) y candidatos")
    for rel in CANDIDATOS:
        for nombre in (EVM, EGR):
            ruta = os.path.join(raiz, rel, nombre)
            if os.path.exists(ruta):
                print(f"{rel}/{nombre} | {sha256(ruta)} | {os.path.getsize(ruta)} bytes")
    print()


def paso_hojas(ruta, nombre):
    print(f"## 2. Hojas de {nombre}")
    datos = hojas_resumen(ruta)
    for hoja, filas in datos.items():
        no_vacias = [i for i, r in enumerate(filas, 1) if any(c not in (None, "") for c in r)]
        print(f"- hoja `{hoja}`: filas={len(filas)}, filas_no_vacias={len(no_vacias)}, "
              f"rango_no_vacio=({no_vacias[0] if no_vacias else '-'}..{no_vacias[-1] if no_vacias else '-'})")
        print(f"  cabecera: {[c for c in filas[0] if c not in (None, '')] if filas else []}")
    print("- formulas por hoja:", formulas(ruta))
    print()
    return datos


def tabla_evm(datos):
    filas = datos["EJECUTADO"]
    hdr = filas[0]
    idx = {str(h).strip(): i for i, h in enumerate(hdr) if h}
    print("## 3. EJECUTADO VS META / hoja EJECUTADO (filas por categoria y mes)")
    cols = ["EJECUTADO 2023", "META POR CATEGORIA 2024", "EJECUTADO 2024", "EJECUTADO 2025",
            "META POR CATEGORIA 2025", "EJEC. 2025", "META 2025", "EJECUTADO 2026",
            "META POR CATEGORIA 2026", "META 2026", "META 2025 2DO SEMESTRE", "PROYECCI�N MAESTRIAS"]
    print("| categoria | mes | " + " | ".join(c for c in cols if c in idx) + " |")
    print("|---|---|" + "---|" * sum(1 for c in cols if c in idx))
    for r in filas[1:]:
        if not r or r[0] in (None, ""):
            continue
        vals = []
        for c in cols:
            if c in idx:
                v = num(r[idx[c]]) if idx[c] < len(r) else None
                vals.append("" if v is None else f"{v:,.2f}")
        print(f"| {r[0]} | {r[1]} | " + " | ".join(vals) + " |")
    print()
    return filas, idx


def tabla_gestiones(datos, nombre_hoja, etiqueta):
    filas = datos[nombre_hoja]
    print(f"## {etiqueta} / hoja {nombre_hoja}")
    print("| fila | " + " | ".join(str(c) for c in filas[0] if c not in (None, "")) + " |")
    for r in filas[1:]:
        if any(c not in (None, "") for c in r):
            print("| " + " | ".join("" if c is None else str(c) for c in r[:8]) + " |")
    print()


def comparar_meta_2025(evm_filas, evm_idx, egr_datos):
    """Compara META 2025 por mes: detalle EJECUTADO (PROG+TECHOS) vs EVM GESTIONES vs Egresos Gestiones y acumulados."""
    print("## 4. META 2025 por mes: tres fuentes (Bs)")
    det = {}
    for r in evm_filas[1:]:
        if r and r[0] in ("PROGRAMAS", "TECHOS/CERRADOS"):
            m = MESES.index(str(r[1]).strip()) + 1
            v = num(r[evm_idx["META 2025"]])
            det[m] = det.get(m, 0.0) + (v or 0.0)
    gest_evm = {}
    for r in hojas_gest["GESTIONES"][1:]:
        if r and r[0] in MESES:
            gest_evm[MESES.index(r[0]) + 1] = num(r[4])
    egr_prog = {}
    egr_tech = {}
    for r in egr_datos["Gestiones"][1:]:
        if not r or r[0] is None:
            continue
        m = MESES.index(str(r[1]).strip()) + 1
        if r[0] == "POR PROGRAMAS":
            egr_prog[m] = num(r[6])
        elif r[0] == "POR TECHOS/CERRADOS":
            egr_tech[m] = num(r[6])
    acum = {}
    for r in egr_datos["acumulados"][1:]:
        if r and r[0] is not None:
            acum[int(float(r[0]))] = num(r[5])
    print("| mes | detalle EVM (PROG+TECH) | EVM GESTIONES | Egresos Gestiones (PROG+TECH) | Egresos acumulados | dif detalle-EVM_GEST |")
    print("|---|---|---|---|---|---|")
    difs = []
    for m in range(1, 13):
        a = det.get(m)
        b = gest_evm.get(m)
        c = (egr_prog.get(m) or 0.0) + (egr_tech.get(m) or 0.0)
        d = acum.get(m)
        dif = None if (a is None or b is None) else round(a - b, 2)
        print(f"| {MESES[m-1]} | {a:,.2f} | {b:,.2f} | {c:,.2f} | {d:,.2f} | {dif if dif is not None else 'n/d'} |")
        if dif is not None and abs(dif) > 1:
            difs.append((m, dif))
    print(f"- meses con dif > 1 Bs entre detalle EVM y GESTIONES EVM: {len(difs)} -> {difs}")
    print()


def comparar_ejec_2025(evm_filas, evm_idx, egr_datos):
    print("## 5. EJECUTADO 2025 por mes: detalle EVM vs resumenes")
    det = {}
    for r in evm_filas[1:]:
        if r and r[0] in ("PROGRAMAS", "TECHOS/CERRADOS"):
            m = MESES.index(str(r[1]).strip()) + 1
            det[m] = det.get(m, 0.0) + (num(r[evm_idx["EJECUTADO 2025"]]) or 0.0)
    gest = {}
    for r in hojas_gest["GESTIONES"][1:]:
        if r and r[0] in MESES:
            gest[MESES.index(r[0]) + 1] = num(r[3])
    print("| mes | EVM detalle EJECUTADO 2025 (PROG+TECH) | EVM GESTIONES | Egresos acumulados |")
    print("|---|---|---|---|")
    acum = {}
    for r in egr_datos["acumulados"][1:]:
        if r and r[0] is not None:
            acum[int(float(r[0]))] = num(r[4])
    for m in range(1, 13):
        print(f"| {MESES[m-1]} | {det.get(m, 0):,.2f} | {gest.get(m)} | {acum.get(m)} |")
    print()


def comparar_con_dw(evm_filas, evm_idx, csv_dw):
    print("## 6. Cruce con docs/mediciones/adw_l0_rentabilidad.csv (meta y ejecucion, PROG+TECH)")
    fuente = {}
    for r in evm_filas[1:]:
        if r and r[0] in ("PROGRAMAS", "TECHOS/CERRADOS"):
            m = MESES.index(str(r[1]).strip()) + 1
            for gestion, col in ((2023, "EJECUTADO 2023"), (2024, "EJECUTADO 2024"), (2025, "EJECUTADO 2025"),
                                 (2026, "EJECUTADO 2026")):
                v = num(r[evm_idx[col]]) if col in evm_idx else None
                k = (gestion, m)
                fuente.setdefault(k, {"ejec": 0.0, "meta": 0.0, "ejec_n": 0, "meta_n": 0})
                if v is not None:
                    fuente[k]["ejec"] += v
                    fuente[k]["ejec_n"] += 1
            for gestion, col in ((2024, "META POR CATEGORIA 2024"), (2025, "META POR CATEGORIA 2025"),
                                 (2026, "META POR CATEGORIA 2026")):
                v = num(r[evm_idx[col]]) if col in evm_idx else None
                k = (gestion, m)
                fuente.setdefault(k, {"ejec": 0.0, "meta": 0.0, "ejec_n": 0, "meta_n": 0})
                if v is not None:
                    fuente[k]["meta"] += v
                    fuente[k]["meta_n"] += 1
    coincide_m = coincide_e = total = 0
    print("| gestion | mes | DW ejec | EVM ejec | DW meta | EVM meta | nota |")
    print("|---|---|---|---|---|---|---|")
    for r in csv_dw:
        g, m = int(r["gestion"]), int(r["mes"])
        dw_e = float(r["ejecutado_bs"]) if r["ejecutado_bs"] else None
        dw_m = float(r["meta_bs"]) if r["meta_bs"] else None
        f = fuente.get((g, m), {"ejec": None, "meta": None, "ejec_n": 0, "meta_n": 0})
        ev_e = f["ejec"] if f["ejec_n"] else None
        ev_m = f["meta"] if f["meta_n"] else None
        total += 1
        ok_e = (dw_e is None and ev_e is None) or (dw_e is not None and ev_e is not None and abs(dw_e - ev_e) < 1)
        ok_m = (dw_m is None and ev_m is None) or (dw_m is not None and ev_m is not None and abs(dw_m - ev_m) < 1)
        coincide_e += ok_e
        coincide_m += ok_m
        nota = []
        if not ok_m:
            nota.append("meta distinta")
        if not ok_e:
            nota.append("ejec distinta")
        if dw_e is None and ev_e is None:
            nota.append("sin ejec")
        print(f"| {g} | {m} | {dw_e if dw_e is not None else ''} | {round(ev_e,2) if ev_e is not None else ''} | "
              f"{dw_m if dw_m is not None else ''} | {round(ev_m,2) if ev_m is not None else ''} | {'; '.join(nota)} |")
    print(f"- filas DW={total}; ejecutado coincide={coincide_e}; meta coincide={coincide_m}")
    print()


def kpi02(csv_dw):
    print("## 7. KPI-02 2024 con las tres opciones (Dic-2024 = ultimo mes con ejecucion)")
    dic = [r for r in csv_dw if r["gestion"] == "2024" and r["mes"] == "12"][0]
    ejec = float(dic["ejecutado_bs"])
    meta_anual = float(dic["meta_bs"])
    prorr = meta_anual / 12
    print(f"- ejecutado Dic-2024 (DW, PROG+TECH) = {ejec:,.2f}")
    print(f"- meta anual 2024 (celda TECHOS/CERRADOS, DICIEMBRE, columna META POR CATEGORIA 2024) = {meta_anual:,.2f}")
    print(f"- opcion excluir 2024: sin dato")
    print(f"- opcion prorratear (partes iguales, SUPOSICION): {meta_anual:,.2f} / 12 = {prorr:,.2f}; "
          f"KPI-02 = {ejec:,.2f} / {prorr:,.2f} = {ejec/prorr*100:.2f} %")
    print(f"- KPI-02 actual DW (meta anual en Dic): {ejec:,.2f} / {meta_anual:,.2f} = {ejec/meta_anual*100:.2f} %")
    print(f"- opcion cargar meta mensual real: no determinado (no existe meta mensual 2024 en el archivo)")
    print()


if __name__ == "__main__":
    carpeta_raiz = sys.argv[1]
    csv_ruta = sys.argv[2] if len(sys.argv) > 2 else None
    evm_ruta = os.path.join(carpeta_raiz, "uploads", "data", EVM)
    egr_ruta = os.path.join(carpeta_raiz, "uploads", "data", EGR)
    paso_inventario(carpeta_raiz)
    hojas_evm = paso_hojas(evm_ruta, EVM)
    hojas_egr = paso_hojas(egr_ruta, EGR)
    hojas_gest = {"GESTIONES": hojas_evm["GESTIONES"]}
    evm_filas, evm_idx = tabla_evm(hojas_evm)
    tabla_gestiones(hojas_evm, "GESTIONES", "3b. EJECUTADO VS META / resumen GESTIONES")
    tabla_gestiones(hojas_egr, "Gestiones", "3c. BD Egresos / Gestiones")
    tabla_gestiones(hojas_egr, "acumulados", "3d. BD Egresos / acumulados")
    comparar_meta_2025(evm_filas, evm_idx, hojas_egr)
    comparar_ejec_2025(evm_filas, evm_idx, hojas_egr)
    if csv_ruta:
        with open(csv_ruta, encoding="utf-8") as f:
            csv_dw = list(csv.DictReader(f))
        comparar_con_dw(evm_filas, evm_idx, csv_dw)
        kpi02(csv_dw)
