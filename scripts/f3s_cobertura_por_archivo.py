"""S-7 (F3S): cobertura por archivo de f3s_base (solo lectura). Reemplaza el script de A-1 (PLAN_F3R_A), que no quedó en el repo:
mismo balance  origen = cargadas + staging/bandeja + log + ruido + sin_explicar,  línea a línea.

Por documento y hoja:
  origen_slice      filas procesables del recorte (criterio de inventario_corpus.py: >= 2 celdas con dato, menos la cabecera)
  leidas            líneas del bloque en staging_registros_crudos (lo que la consolidación recorre)
  ingesta_log       filas descartadas en la ingesta con bitácora (log_inconsistencias tipo SUBTOTAL)
Cada línea leída se clasifica con las mismas funciones que consolidacion.py (categoría de ruteo incluida la corrección D-A4):
  ruido_con_motivo  motivo_fila_sin_entidad(...) != None  (debe cuadrar con log_inconsistencias LINEA_SIN_ENTIDAD)
  bandeja           línea en stg_entidad_no_resuelta sin resolver (texto_original = línea[:250], mismo bloque)
  con_registros     la regla de su categoría produce >= 1 registro (o, en financiero/marketing/admisión, el registro único)
  sin_explicar      no es ruido, no está en bandeja y su regla no produce ningún registro
y se compara registros esperados con hechos en el DW por documento.
Uso (en giragroup_api): DATABASE_URL=<base tmpfs> PYTHONPATH=/app python f3s_cobertura_por_archivo.py <carpeta_slices> <salida.json>
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from services.extraccion_por_encabezado import (campos_por_encabezado, motivo_fila_sin_entidad, registros_academicos,
                                                registros_asignacion_docente, registros_costo_programa, registros_evaluacion,
                                                registros_rentabilidad, registros_techo_convenio)

HECHOS = ["fact_rendimiento_academico", "fact_situacion_financiera", "fact_evaluacion_docente", "fact_rentabilidad",
          "fact_techo_convenio", "fact_costo_programa", "bridge_modulo_docente"]


def categoria_ruteo(tipo_fuente, categoria_stg):
    doc_fuente = (tipo_fuente or "ACTA").upper().strip()
    if (categoria_stg or "").strip().lower() == "evaluacion_docente":  # D-A4 (consolidacion.py:181)
        doc_fuente = "EVALUACION_DOCENTE"
    return ("financiero" if doc_fuente == "COBRANZA" else "rentabilidad" if doc_fuente in ("EGRESOS", "TECHOS", "RENTABILIDAD")
            else "evaluacion_docente" if doc_fuente == "EVALUACION_DOCENTE" else "marketing" if doc_fuente == "MARKETING"
            else "admision" if doc_fuente == "ADMISION" else "academico")


def registros(campos, cat):
    if not campos:
        return 0, None
    if cat == "academico":
        return len(registros_asignacion_docente(campos)) + len(registros_academicos(campos, None)), "academico"
    if cat == "evaluacion_docente":
        return len(registros_evaluacion(campos)), "fact_evaluacion_docente"
    if cat == "rentabilidad":
        r = registros_rentabilidad(campos)
        if r:
            return len(r), "fact_rentabilidad"
        c = registros_costo_programa(campos)
        if c:
            return len(c), "fact_costo_programa"
        return len(registros_techo_convenio(campos)), "fact_techo_convenio"
    if cat in ("marketing", "admision") and registros_techo_convenio(campos):
        return len(registros_techo_convenio(campos)), "fact_techo_convenio"
    return 1, {"financiero": "fact_situacion_financiera"}.get(cat, "fact_marketing")


def origen_slice(path):
    out = {}
    for h, df in pd.read_excel(path, sheet_name=None, header=None).items():
        df = df.dropna(how="all").dropna(axis=1, how="all")
        out[h] = 0 if df.empty else max(int((df.notna().sum(1) >= 2).sum()) - 1, 0)
    return out


def main(carpeta, salida):
    eng = create_engine(os.environ["DATABASE_URL"], connect_args={"options": "-c default_transaction_read_only=on"})
    res = {"base": os.environ["DATABASE_URL"].rsplit("/", 1)[-1], "criterio_origen": "inventario_corpus.py (>=2 celdas, menos cabecera)",
           "documentos": {}}
    with eng.connect() as c:
        docs = c.execute(text("SELECT id_documento, nombre_archivo, tipo_fuente FROM dim_origen_documental ORDER BY 1")).all()
        for id_doc, archivo, tipo in docs:
            slice_p = next((p for p in Path(carpeta).glob("*.xlsx")
                            if p.name.replace("[", "_").replace("]", "_").replace("`", "_") == archivo or p.name == archivo), None)
            org = origen_slice(slice_p) if slice_p else {}
            stg_unres = {}
            for rid, txt in c.execute(text("SELECT registro_origen_id, texto_original FROM stg_entidad_no_resuelta "
                                           "WHERE id_documento=:d AND NOT resuelto"), {"d": id_doc}):
                stg_unres.setdefault(rid, set()).add(txt)
            hojas, tot = {}, dict(origen_slice=sum(org.values()), leidas=0, ruido_con_motivo=0, bandeja=0, con_registros=0, sin_explicar=0)
            esperados, motivos, ejemplos_sin = {}, {}, []
            for bid, hoja, cat_stg, txt, fila_ini in c.execute(text(
                    "SELECT id, hoja, categoria, texto_plano, fila_inicio FROM staging_registros_crudos WHERE id_documento=:d ORDER BY id"),
                    {"d": id_doc}):
                cat = categoria_ruteo(tipo, cat_stg)
                lines = [l.strip() for l in (txt or "").split("\n") if l.strip()]
                h = hojas.setdefault(hoja, dict(categoria_staging=cat_stg, categoria_ruteo=cat, origen_slice=org.get(hoja),
                                                leidas=0, ruido_con_motivo=0, bandeja=0, con_registros=0, sin_explicar=0))
                for k, l in enumerate(lines):
                    h["leidas"] += 1
                    campos = campos_por_encabezado([x.strip() for x in l.split("|")])
                    m = motivo_fila_sin_entidad(campos, cat)
                    if m:
                        h["ruido_con_motivo"] += 1
                        motivos[m] = motivos.get(m, 0) + 1
                    elif l[:250] in stg_unres.get(bid, ()) or l in stg_unres.get(bid, ()):
                        h["bandeja"] += 1
                    else:
                        n, tabla = registros(campos, cat)
                        if n > 0:
                            h["con_registros"] += 1
                            esperados[tabla] = esperados.get(tabla, 0) + n
                        else:
                            h["sin_explicar"] += 1
                            if len(ejemplos_sin) < 5:
                                ejemplos_sin.append({"hoja": hoja, "fila_origen": (fila_ini or 0) + k, "linea_md5": hashlib.md5(l.encode()).hexdigest()})
            for h in hojas.values():
                for k in ("leidas", "ruido_con_motivo", "bandeja", "con_registros", "sin_explicar"):
                    tot[k] += h[k]
            for hoja, n in org.items():
                hojas.setdefault(hoja, dict(origen_slice=n, leidas=0, nota="hoja del recorte sin bloque en staging"))
            hechos = {}
            for t in HECHOS:
                n = c.execute(text(f"SELECT count(*) FROM {t} WHERE id_documento=:d"), {"d": id_doc}).scalar()
                if n:
                    hechos[t] = n
            if id_doc and c.execute(text("SELECT count(*) FROM carga_fila_origen WHERE id_documento=:d AND tabla='fact_marketing'"), {"d": id_doc}).scalar():
                hechos["fact_marketing(carga_fila_origen)"] = c.execute(text(
                    "SELECT count(*) FROM carga_fila_origen WHERE id_documento=:d AND tabla='fact_marketing'"), {"d": id_doc}).scalar()
            log = dict(c.execute(text("SELECT tipo_regla, count(*) FROM log_inconsistencias WHERE id_documento=:d GROUP BY 1"), {"d": id_doc}).all())
            stg = dict(c.execute(text("SELECT motivo || CASE WHEN resuelto THEN ' (resuelto)' ELSE '' END, count(*) FROM stg_entidad_no_resuelta "
                                      "WHERE id_documento=:d GROUP BY 1"), {"d": id_doc}).all())
            stg_tipo = dict(c.execute(text("SELECT tipo_entidad, count(*) FROM stg_entidad_no_resuelta WHERE id_documento=:d AND NOT resuelto GROUP BY 1"),
                                      {"d": id_doc}).all())
            tot["ingesta_log_subtotal"] = log.get("SUBTOTAL", 0)
            tot["diferencia_origen_vs_leidas_mas_ingesta"] = tot["origen_slice"] - tot["leidas"] - tot["ingesta_log_subtotal"]
            res["documentos"][str(id_doc)] = {
                "archivo": archivo, "tipo_fuente": tipo, "slice_sha256": hashlib.sha256(slice_p.read_bytes()).hexdigest() if slice_p else None,
                "balance": tot, "balance_ok": tot["leidas"] == tot["ruido_con_motivo"] + tot["bandeja"] + tot["con_registros"] + tot["sin_explicar"],
                "ruido_por_motivo": motivos, "log_inconsistencias": log, "log_LINEA_SIN_ENTIDAD_vs_ruido": [log.get("LINEA_SIN_ENTIDAD", 0), tot["ruido_con_motivo"]],
                "stg_entidad_no_resuelta": stg, "bandeja_por_tipo_entidad": stg_tipo,
                "registros_esperados_por_regla": esperados, "hechos_en_dw": hechos, "por_hoja": hojas, "ejemplos_sin_explicar": ejemplos_sin}
    res["totales"] = {k: sum(d["balance"][k] for d in res["documentos"].values())
                      for k in ("origen_slice", "leidas", "ingesta_log_subtotal", "ruido_con_motivo", "bandeja", "con_registros", "sin_explicar")}
    s = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True, default=str)
    Path(salida).write_text(s, encoding="utf-8")
    print("md5", hashlib.md5(s.encode()).hexdigest(), json.dumps(res["totales"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
