"""
Clasificación de hojas de solo lectura (FU-L1).

Corre el lector de la ingesta (pipeline.ingesta.leer_archivo_con_metadatos) sobre los libros
de un directorio y escribe una fila por hoja: estado, decisión (usar / ignorar) y motivo,
filas leídas, filas fantasma y subtotales cortados, y fórmulas sin valor guardado.
Si se da el contrato (docs/fuentes/CONTRATO_FUENTES.md), compara cada decisión con su tabla.

Reglas: genérico (sin nombres de libro ni de hoja), sin PII (solo nombres de hoja, conteos y
motivos) y de solo lectura (no toca los libros ni la base de datos).

Uso:
    python scripts/auditoria_fuentes/clasificar_hojas.py --entrada uploads/data \
        --salida docs/mediciones/fu_l1_hojas_clasificadas.csv --contrato docs/fuentes/CONTRATO_FUENTES.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for p in (RAIZ, RAIZ / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from pipeline.ingesta import leer_archivo_con_metadatos  # noqa: E402
from pipeline.lector_hojas import enmascarar_texto  # noqa: E402

CAMPOS = ["archivo", "hoja", "estado", "decision", "regla", "motivo", "filas_leidas",
          "filas_fantasma_cortadas", "subtotales_cortados", "formulas", "formulas_sin_valor",
          "tipo_sugerido", "aviso", "decision_contrato", "coincide_contrato"]


def _nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto).strip()


def leer_contrato(ruta: Path) -> dict:
    """{(archivo, hoja): decisión} de la tabla «Hojas (N): decisión y motivo» del contrato."""
    decisiones = {}
    en_tabla = False
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.startswith("| archivo | hoja |"):
            en_tabla = True
            continue
        if en_tabla:
            if not linea.startswith("|"):
                break
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if len(celdas) < 4 or set(celdas[0]) <= {"-"}:
                continue
            decisiones[(_nfc(celdas[0]), _nfc(celdas[1]))] = celdas[3]
    return decisiones


def conflictos_planificacion(ruta: Path, libro: dict) -> list[dict]:
    """
    Hojas que el clasificador ignora pero que el extractor de planificación (camino propio de los libros
    tipo PLANIFICACION en la ingesta) sí lee. Solo para libros cuya mayoría de hojas usadas sugiere ese tipo.
    """
    sugeridos = [h.meta.tipo_sugerido for h in libro.values() if h.usada]
    if not sugeridos or sugeridos.count("PLANIFICACION") * 2 <= len(sugeridos):
        return []
    from services.planificacion_extractor import extraer_libro_planificacion
    # Igual que la ingesta (FU-L1b): el extractor recibe las hojas que el clasificador ignora
    datos = extraer_libro_planificacion(str(ruta), hojas_excluidas={n for n, h in libro.items() if not h.usada})
    sin_excluir = extraer_libro_planificacion(str(ruta))
    EXTRACTOR.append({
        "archivo": ruta.name,
        "filas_con_clasificador": len(datos["filas"]), "metas_con_clasificador": len(datos["metas"]),
        "filas_sin_clasificador": len(sin_excluir["filas"]), "metas_sin_clasificador": len(sin_excluir["metas"]),
        "filas_de_ocultas_rescatadas": sum(1 for f in datos["filas"] if libro[f["hoja"]].meta.estado != "visible"),
        "metas_de_ocultas_rescatadas": sum(1 for m in datos["metas"]
                                           if libro[str(m.get("celda_origen", "")).split("!")[0]].meta.estado != "visible"),
    })
    filas_por_hoja = {}
    for f in datos["filas"]:
        filas_por_hoja[f["hoja"]] = filas_por_hoja.get(f["hoja"], 0) + 1
    metas_por_hoja = {}
    for m in datos["metas"]:
        hoja = str(m.get("celda_origen", "")).split("!")[0]
        metas_por_hoja[hoja] = metas_por_hoja.get(hoja, 0) + 1
    salida = []
    for nombre, h in libro.items():
        n_f, n_m = filas_por_hoja.get(nombre, 0), metas_por_hoja.get(nombre, 0)
        if not h.usada and (n_f or n_m):
            salida.append({"archivo": ruta.name, "hoja": enmascarar_texto(nombre), "estado": h.meta.estado,
                           "regla": h.clasificacion.regla, "filas_extractor": n_f, "metas_extractor": n_m})
        elif h.usada and not (n_f or n_m):
            salida.append({"archivo": ruta.name, "hoja": enmascarar_texto(nombre), "estado": h.meta.estado,
                           "regla": "usada_sin_filas_en_extractor", "filas_extractor": 0, "metas_extractor": 0})
    return salida


CONFLICTOS: list[dict] = []
EXTRACTOR: list[dict] = []


def clasificar_directorio(entrada: Path) -> list[dict]:
    filas = []
    for libro in sorted(p for p in entrada.glob("*.xlsx") if not p.name.startswith("~$")):
        leido = leer_archivo_con_metadatos(str(libro))
        CONFLICTOS.extend(conflictos_planificacion(libro, leido))
        for nombre, h in leido.items():
            filas.append({
                "archivo": libro.name,
                "hoja": enmascarar_texto(nombre),
                "estado": h.meta.estado,
                "decision": h.clasificacion.decision,
                "regla": h.clasificacion.regla,
                "motivo": h.clasificacion.motivo,
                "filas_leidas": h.meta.filas_datos if h.usada else 0,
                "filas_fantasma_cortadas": h.meta.filas_fantasma,
                "subtotales_cortados": h.meta.filas_subtotal,
                "formulas": h.meta.n_formulas,
                "formulas_sin_valor": h.meta.n_formulas_sin_valor,
                "tipo_sugerido": h.meta.tipo_sugerido or "",
                "aviso": h.clasificacion.aviso or "",
            })
    return filas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Clasificación de hojas sin PII (FU-L1).")
    ap.add_argument("--entrada", required=True, type=Path)
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--contrato", type=Path)
    ap.add_argument("--resumen", type=Path, help="JSON con conteos y diferencias contra el contrato")
    args = ap.parse_args(argv)
    t0 = time.perf_counter()
    filas = clasificar_directorio(args.entrada)
    contrato = leer_contrato(args.contrato) if args.contrato else {}
    difs = []
    for f in filas:
        esperado = contrato.get((_nfc(f["archivo"]), _nfc(f["hoja"])), "")
        f["decision_contrato"] = esperado
        f["coincide_contrato"] = "" if not esperado else ("si" if esperado == f["decision"] else "no")
        if f["coincide_contrato"] == "no":
            difs.append(f)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    resumen = {
        "hojas": len(filas),
        "usar": sum(f["decision"] == "usar" for f in filas),
        "ignorar": sum(f["decision"] == "ignorar" for f in filas),
        "en_contrato": sum(bool(f["decision_contrato"]) for f in filas),
        "diferencias_contrato": [(f["archivo"], f["hoja"], f["decision"], f["decision_contrato"]) for f in difs],
        "filas_leidas": sum(int(f["filas_leidas"]) for f in filas),
        "filas_fantasma_cortadas_hojas_usadas": sum(int(f["filas_fantasma_cortadas"]) for f in filas if f["decision"] == "usar"),
        "subtotales_cortados_hojas_usadas": sum(int(f["subtotales_cortados"]) for f in filas if f["decision"] == "usar"),
        "formulas_sin_valor_hojas_usadas": sum(int(f["formulas_sin_valor"]) for f in filas if f["decision"] == "usar"),
        "conflictos_extractor_planificacion": CONFLICTOS,
        "extractor_planificacion": EXTRACTOR,
        "ocultas_usadas": [(f["archivo"], f["hoja"], f["motivo"]) for f in filas if f["estado"] != "visible" and f["decision"] == "usar"],
        "por_regla": {r: sum(f["regla"] == r for f in filas) for r in sorted({f["regla"] for f in filas})},
        "segundos": round(time.perf_counter() - t0, 1),
    }
    if args.resumen:
        args.resumen.write_text(json.dumps(resumen, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
