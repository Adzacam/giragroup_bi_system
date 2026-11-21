"""
Líneas que la consolidación descartaría como LINEA_SIN_ENTIDAD, antes y después de FU-L1 (solo lectura).

Reproduce sin base de datos el camino genérico de la ingesta (bloques -> líneas 'ENCABEZADO: valor')
y aplica la misma regla de descarte de la consolidación (motivo_fila_sin_entidad), una vez con el
lector anterior (todas las hojas, sin cortes) y otra con el de FU-L1 (hojas usadas, sin filas fantasma
ni subtotales y con el tipo propio de la hoja). El tipo del libro es el detectado por cabeceras.
Los libros cuyo camino es el extractor de planificación se marcan y no se simulan.

Sin PII: solo nombres de hoja y conteos.

Uso:
    python scripts/auditoria_fuentes/descartes_antes_despues.py --entrada uploads/data \
        --salida docs/mediciones/fu_l1_descartes_antes_despues.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import warnings
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for p in (RAIZ, RAIZ / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

warnings.simplefilter("ignore")
logging.disable(logging.WARNING)

from pipeline.ingesta import detectar_bloques, es_encuesta_likert, leer_archivo_con_metadatos  # noqa: E402
from pipeline.lector_hojas import CATEGORIA_POR_TIPO, enmascarar_texto, tipo_de_hoja_distinto  # noqa: E402
from routers.dataops._comun import categoria_ruteo  # noqa: E402
from services.extraccion_por_encabezado import campos_por_encabezado, motivo_fila_sin_entidad  # noqa: E402
from services.ingestion_service import IngestionService, detectar_tipo_fuente_por_cabeceras  # noqa: E402


def _contar(df, tipo_doc, transparentes=None, tipo_hoja=None) -> Counter:
    c = Counter()
    for b in detectar_bloques(df, filas_transparentes=transparentes):
        if b.attrs.get("es_ruido") or len(b) < 2:
            continue
        cat = "evaluacion_docente" if es_encuesta_likert(b) else (CATEGORIA_POR_TIPO.get(tipo_hoja) if tipo_hoja else None)
        if cat == "planificacion":
            c["planificacion"] += len([l for l in IngestionService.serializar_bloque_con_encabezados(b).splitlines() if l.strip()])
            continue
        ruteo = categoria_ruteo(tipo_doc, cat)
        for linea in IngestionService.serializar_bloque_con_encabezados(b).splitlines():
            if linea.strip():
                motivo = motivo_fila_sin_entidad(campos_por_encabezado([x.strip() for x in linea.split("|")]), ruteo)
                c["descartada" if motivo else "con_entidad"] += 1
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", required=True, type=Path)
    ap.add_argument("--salida", required=True, type=Path)
    args = ap.parse_args(argv)
    filas = []
    for ruta in sorted(p for p in args.entrada.glob("*.xlsx") if not p.name.startswith("~$")):
        libro = leer_archivo_con_metadatos(str(ruta))
        sugeridos = [h.meta.tipo_sugerido for h in libro.values() if h.usada]
        extractor = bool(sugeridos) and sugeridos.count("PLANIFICACION") * 2 > len(sugeridos)
        tipo_antes = detectar_tipo_fuente_por_cabeceras({n: h.df for n, h in libro.items()}, ruta.name)
        tipo_despues = detectar_tipo_fuente_por_cabeceras({n: h.df_recortado() for n, h in libro.items() if h.usada}, ruta.name)
        for nombre, h in libro.items():
            fila = {"archivo": ruta.name, "hoja": enmascarar_texto(nombre), "estado": h.meta.estado,
                    "decision": h.clasificacion.decision, "regla": h.clasificacion.regla,
                    "tipo_libro_antes": tipo_antes, "tipo_libro_despues": tipo_despues}
            if extractor:
                fila.update({"camino": "extractor_planificacion"})
                filas.append(fila)
                continue
            antes = _contar(h.df, tipo_antes)
            if h.usada:
                tipo_h = tipo_de_hoja_distinto(h.meta, tipo_despues)
                despues = _contar(h.df_recortado(), tipo_despues, set(h.meta.filas_descartadas) or None, tipo_h)
            else:
                tipo_h, despues = None, Counter()
            fila.update({
                "camino": "generico", "tipo_hoja": tipo_h or "",
                "lineas_con_entidad_antes": antes["con_entidad"], "lineas_descartadas_antes": antes["descartada"],
                "lineas_planificacion_antes": antes["planificacion"],
                "lineas_con_entidad_despues": despues["con_entidad"], "lineas_descartadas_despues": despues["descartada"],
                "lineas_planificacion_despues": despues["planificacion"],
                "registro_hoja_ignorada": 0 if h.usada else 1,
            })
            filas.append(fila)
    campos = ["archivo", "hoja", "estado", "decision", "regla", "camino", "tipo_libro_antes", "tipo_libro_despues",
              "tipo_hoja", "lineas_con_entidad_antes", "lineas_descartadas_antes", "lineas_planificacion_antes",
              "lineas_con_entidad_despues", "lineas_descartadas_despues", "lineas_planificacion_despues",
              "registro_hoja_ignorada"]
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)
    gen = [f for f in filas if f["camino"] == "generico"]
    total = {k: sum(int(f.get(k) or 0) for f in gen) for k in campos[9:]}
    print(json.dumps(total, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
