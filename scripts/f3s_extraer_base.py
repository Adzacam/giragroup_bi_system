"""S-7 (F3S): extracción R3-1 + cuadre KPI-15 + diagnóstico de matrícula sobre f3s_base (copia tmpfs, solo lectura).
Mismas consultas que scripts/f3r_medir_base.py, con la base, el DSN y los nombres de salida como parámetros.
Uso: python scripts/f3s_extraer_base.py <dsn> <base> <salida_extraccion.json> <salida_kpi15.json> <salida_matricula.json>
"""
import json
import sys
from pathlib import Path

import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parents[1]


def main(dsn, base, s_ext, s_k15, s_mat):
    conn = psycopg2.connect(dsn, options="-c default_transaction_read_only=on")
    cur = conn.cursor()
    cur.execute("SELECT table_schema, table_type, table_name FROM information_schema.tables "
                "WHERE table_schema IN ('public', 'bi') ORDER BY table_schema, table_type, table_name")
    inv = [{"schema": r[0], "type": r[1], "name": r[2]} for r in cur.fetchall()]
    base_tables = [r for r in inv if r["type"] == "BASE TABLE"]
    views = [r for r in inv if r["type"] == "VIEW"]
    conteos = {}
    for t in base_tables:
        cur.execute(f'SELECT count(*) FROM "{t["schema"]}"."{t["name"]}"')
        conteos[f"{t['schema']}.{t['name']}"] = cur.fetchone()[0]

    def tiene(tbl, col):
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=%s", (tbl, col))
        return cur.fetchone() is not None

    fk_estado, fuente_res, por_doc = {}, {}, {}
    for tbl in ("fact_rendimiento_academico", "fact_situacion_financiera", "dim_estudiante", "dim_docente"):
        if tiene(tbl, "fk_estado"):
            cur.execute(f"SELECT fk_estado, count(*) FROM public.{tbl} GROUP BY fk_estado ORDER BY fk_estado")
            fk_estado[tbl] = {str(r[0]): r[1] for r in cur.fetchall()}
    for tbl in ("dim_estudiante", "dim_docente", "fact_rendimiento_academico", "fact_situacion_financiera"):
        if tiene(tbl, "fuente_resolucion"):
            cur.execute(f"SELECT fuente_resolucion, count(*) FROM public.{tbl} GROUP BY fuente_resolucion ORDER BY count(*) DESC")
            fuente_res[tbl] = {str(r[0]): r[1] for r in cur.fetchall()}
    for t in base_tables:
        if t["schema"] == "public" and (t["name"].startswith("fact_") or t["name"] in ("bridge_modulo_docente", "stg_entidad_no_resuelta",
                                                                                      "log_inconsistencias", "carga_fila_origen")) \
                and tiene(t["name"], "id_documento"):
            cur.execute(f"SELECT id_documento, count(*) FROM public.{t['name']} GROUP BY 1 ORDER BY 1")
            filas = {str(r[0]): r[1] for r in cur.fetchall()}
            if filas:
                por_doc[t["name"]] = filas

    cur.execute("SELECT motivo, resuelto, count(*) FROM public.stg_entidad_no_resuelta GROUP BY motivo, resuelto ORDER BY motivo, resuelto")
    stg = [{"motivo": r[0], "resuelto": r[1], "filas": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT tipo_entidad, motivo, count(*) FROM public.stg_entidad_no_resuelta GROUP BY 1, 2 ORDER BY 1, 2")
    stg_tipo = [{"tipo_entidad": r[0], "motivo": r[1], "filas": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT regla_origen, tipo_regla, count(*) FROM public.log_inconsistencias "
                "GROUP BY regla_origen, tipo_regla ORDER BY count(*) DESC, regla_origen, tipo_regla")
    log_inc = [{"regla_origen": r[0], "tipo_regla": r[1], "filas": r[2]} for r in cur.fetchall()]
    cur.execute("SELECT count(*), min(fecha)::text, max(fecha)::text, min(gestion), max(gestion) FROM public.dim_tiempo")
    dt = cur.fetchone()
    cur.execute("SELECT gestion, codigo, valor FROM bi.vw_cmi_valores WHERE codigo IN ('KPI-10','KPI-11','KPI-15','KPI-18') ORDER BY gestion, codigo")
    kpis_vw = [{"gestion": r[0], "codigo": r[1], "valor": float(r[2]) if r[2] is not None else None} for r in cur.fetchall()]
    cur.execute("SELECT id_documento, nombre_archivo, tipo_fuente FROM public.dim_origen_documental ORDER BY 1")
    docs = [{"id": r[0], "archivo": r[1], "tipo_fuente": r[2]} for r in cur.fetchall()]

    ext = {"base_datos": base,
           "inventario": {"total_tablas_base": len(base_tables), "total_vistas": len(views),
                          "tiene_cache_beto_entidades": any(r["name"] == "cache_beto_entidades" for r in inv)},
           "conteos_tablas": conteos, "fk_estado": fk_estado, "fuente_resolucion": fuente_res,
           "stg_entidad_no_resuelta": stg, "stg_entidad_no_resuelta_por_tipo": stg_tipo,
           "log_inconsistencias": log_inc, "log_inconsistencias_total_B9": conteos.get("public.log_inconsistencias"),
           "dim_tiempo": {"filas": dt[0], "fecha_min": dt[1], "fecha_max": dt[2], "anio_min": dt[3], "anio_max": dt[4]},
           "kpis_vw_cmi_valores": kpis_vw, "dim_origen_documental": docs, "filas_por_documento": por_doc}
    Path(s_ext).write_text(json.dumps(ext, indent=2, ensure_ascii=False), encoding="utf-8")

    cur.execute("SELECT estado_cartera, count(*), coalesce(sum(monto_deuda),0), coalesce(sum(monto_pagado),0) "
                "FROM public.fact_situacion_financiera GROUP BY estado_cartera ORDER BY estado_cartera")
    dw_fin = {str(r[0]): {"filas": r[1], "monto_deuda": float(r[2]), "monto_pagado": float(r[3])} for r in cur.fetchall()}
    total = sum(v["filas"] for v in dw_fin.values())
    mora_prev = dw_fin.get("Mora", {}).get("filas", 0) + dw_fin.get("Previsionable", {}).get("filas", 0)
    cur.execute("SELECT id_documento, nombre_archivo, tipo_fuente, periodo FROM public.dim_origen_documental WHERE nombre_archivo ILIKE '%Cobranzas%'")
    docs_cob = [{"id": r[0], "archivo": r[1], "tipo_fuente": r[2], "periodo": r[3]} for r in cur.fetchall()]
    xl = pd.ExcelFile(ROOT / "uploads/data/BD Cobranzas.xlsx")
    hojas = {s: len(pd.read_excel(xl, sheet_name=s).dropna(how="all")) for s in xl.sheet_names}
    k15 = {"base_datos": base, "excel_hojas_no_vacias": hojas, "dim_origen_documental_cobranzas": docs_cob,
           "fact_situacion_financiera_total": total, "por_estado_cartera": dw_fin,
           "kpi_15_formula_mora_mas_previsionable_pct": round(mora_prev / total * 100.0, 2) if total else None,
           "kpi_15_vw_cmi_valores": [k for k in kpis_vw if k["codigo"] == "KPI-15"],
           "desajuste_conteo": 725 - total}
    Path(s_k15).write_text(json.dumps(k15, indent=2, ensure_ascii=False), encoding="utf-8")

    cur.execute("SELECT count(*), count(DISTINCT (t.gestion, t.mes)) FROM public.fact_marketing fm JOIN public.dim_tiempo t ON fm.id_tiempo = t.id_tiempo")
    fm = cur.fetchone()
    cur.execute("SELECT t.gestion, t.mes, count(*), coalesce(sum(fm.inscritos),0) FROM public.fact_marketing fm "
                "JOIN public.dim_tiempo t ON fm.id_tiempo = t.id_tiempo GROUP BY 1, 2 ORDER BY 1, 2")
    meses = [{"gestion": r[0], "mes": r[1], "filas": r[2], "inscritos": int(r[3])} for r in cur.fetchall()]
    Path(s_mat).write_text(json.dumps({"base_datos": base, "fact_marketing_total_filas": fm[0], "meses_distintos_con_filas": fm[1],
                                       "detalle_por_mes": meses}, indent=2, ensure_ascii=False), encoding="utf-8")
    conn.close()
    print(f"[OK] tablas={len(base_tables)} vistas={len(views)} fin={total} kpi15_formula={k15['kpi_15_formula_mora_mas_previsionable_pct']} "
          f"B9={ext['log_inconsistencias_total_B9']} stg={conteos.get('public.stg_entidad_no_resuelta')}")


if __name__ == "__main__":
    main(*sys.argv[1:6])
