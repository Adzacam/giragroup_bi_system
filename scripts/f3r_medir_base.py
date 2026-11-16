"""R3-1 (extraccion SQL f3r_base), R3-2 (cuadre KPI-15) y R3-4 (diagnostico matricula f3r_base)."""
import json
import os
from pathlib import Path
import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
DSN = os.environ.get("F3R_BASE_DSN", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/f3r_base")


def main():
    conn = psycopg2.connect(DSN, options="-c default_transaction_read_only=on")
    cur = conn.cursor()

    # --- R3-1: Extraccion f3r_base ---
    cur.execute(
        "SELECT table_schema, table_type, table_name "
        "FROM information_schema.tables "
        "WHERE table_schema IN ('public', 'bi') "
        "ORDER BY table_schema, table_type, table_name"
    )
    inv = [{"schema": r[0], "type": r[1], "name": r[2]} for r in cur.fetchall()]
    base_tables = [r for r in inv if r["type"] == "BASE TABLE"]
    views = [r for r in inv if r["type"] == "VIEW"]
    has_cache_beto_entidades = any(r["name"] == "cache_beto_entidades" for r in inv)

    conteos_tablas = {}
    for t in base_tables:
        cur.execute(f"SELECT count(*) FROM {t['schema']}.{t['name']}")
        conteos_tablas[f"{t['schema']}.{t['name']}"] = cur.fetchone()[0]

    fk_estado = {}
    for tbl in (
        "fact_rendimiento_academico",
        "fact_situacion_financiera",
        "dim_estudiante",
        "dim_docente",
    ):
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s AND column_name='fk_estado'",
            (tbl,),
        )
        if cur.fetchone():
            cur.execute(f"SELECT fk_estado, count(*) FROM public.{tbl} GROUP BY fk_estado ORDER BY fk_estado")
            fk_estado[tbl] = {str(r[0]): r[1] for r in cur.fetchall()}

    fuente_res = {}
    for tbl in ("dim_estudiante", "dim_docente", "fact_rendimiento_academico", "fact_situacion_financiera"):
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=%s AND column_name='fuente_resolucion'",
            (tbl,),
        )
        if cur.fetchone():
            cur.execute(
                f"SELECT fuente_resolucion, count(*) FROM public.{tbl} GROUP BY fuente_resolucion ORDER BY count(*) DESC"
            )
            fuente_res[tbl] = {str(r[0]): r[1] for r in cur.fetchall()}

    cur.execute(
        "SELECT motivo, resuelto, count(*) FROM public.stg_entidad_no_resuelta "
        "GROUP BY motivo, resuelto ORDER BY motivo, resuelto"
    )
    stg = [{"motivo": r[0], "resuelto": r[1], "filas": r[2]} for r in cur.fetchall()]

    cur.execute(
        "SELECT regla_origen, tipo_regla, count(*) FROM public.log_inconsistencias "
        "GROUP BY regla_origen, tipo_regla ORDER BY count(*) DESC, regla_origen, tipo_regla"
    )
    log_inc = [{"regla_origen": r[0], "tipo_regla": r[1], "filas": r[2]} for r in cur.fetchall()]

    cur.execute("SELECT count(*), min(fecha)::text, max(fecha)::text, min(gestion), max(gestion) FROM public.dim_tiempo")
    dt = cur.fetchone()

    cur.execute(
        "SELECT gestion, codigo, valor FROM bi.vw_cmi_valores "
        "WHERE codigo IN ('KPI-10','KPI-11','KPI-15','KPI-18') ORDER BY gestion, codigo"
    )
    kpis_vw = [
        {"gestion": r[0], "codigo": r[1], "valor": float(r[2]) if r[2] is not None else None}
        for r in cur.fetchall()
    ]

    extraccion = {
        "base_datos": "f3r_base",
        "inventario": {
            "total_tablas_base": len(base_tables),
            "total_vistas": len(views),
            "tiene_cache_beto_entidades": has_cache_beto_entidades,
        },
        "conteos_tablas": conteos_tablas,
        "fk_estado": fk_estado,
        "fuente_resolucion": fuente_res,
        "stg_entidad_no_resuelta": stg,
        "log_inconsistencias": log_inc,
        "dim_tiempo": {"filas": dt[0], "fecha_min": dt[1], "fecha_max": dt[2], "anio_min": dt[3], "anio_max": dt[4]},
        "kpis_vw_cmi_valores": kpis_vw,
    }
    (ROOT / "docs/mediciones/f3r_extraccion_f3base.json").write_text(
        json.dumps(extraccion, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- R3-2: KPI-15 cuadre ---
    cur.execute(
        "SELECT estado_cartera, count(*), coalesce(sum(monto_deuda),0), coalesce(sum(monto_pagado),0) "
        "FROM public.fact_situacion_financiera GROUP BY estado_cartera ORDER BY estado_cartera"
    )
    dw_fin = {
        str(r[0]): {"filas": r[1], "monto_deuda": float(r[2]), "monto_pagado": float(r[3])}
        for r in cur.fetchall()
    }
    total_dw = sum(v["filas"] for v in dw_fin.values())
    mora_prev = dw_fin.get("Mora", {}).get("filas", 0) + dw_fin.get("Previsionable", {}).get("filas", 0)

    cur.execute(
        "SELECT id_documento, nombre_archivo, tipo_fuente, periodo "
        "FROM public.dim_origen_documental WHERE nombre_archivo ILIKE '%Cobranzas%'"
    )
    docs_cob = [{"id": r[0], "archivo": r[1], "tipo_fuente": r[2], "periodo": r[3]} for r in cur.fetchall()]

    xl = pd.ExcelFile(ROOT / "uploads/data/BD Cobranzas.xlsx")
    hojas = {s: len(pd.read_excel(xl, sheet_name=s).dropna(how="all")) for s in xl.sheet_names}

    cuadre = {
        "base_datos": "f3r_base",
        "excel_hojas_no_vacias": hojas,
        "dim_origen_documental_cobranzas": docs_cob,
        "fact_situacion_financiera_total": total_dw,
        "por_estado_cartera": dw_fin,
        "kpi_15_formula_mora_mas_previsionable_pct": round(mora_prev / total_dw * 100.0, 2) if total_dw else None,
        "desajuste_conteo": 725 - total_dw,
    }
    (ROOT / "docs/mediciones/f3r_kpi15_cuadre.json").write_text(
        json.dumps(cuadre, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # --- R3-4: Diagnostico matricula en f3r_base ---
    cur.execute(
        "SELECT count(*), count(DISTINCT (t.gestion, t.mes)) "
        "FROM public.fact_marketing fm JOIN public.dim_tiempo t ON fm.id_tiempo = t.id_tiempo"
    )
    fm_row = cur.fetchone()
    cur.execute(
        "SELECT t.gestion, t.mes, count(*), coalesce(sum(fm.inscritos),0) "
        "FROM public.fact_marketing fm JOIN public.dim_tiempo t ON fm.id_tiempo = t.id_tiempo "
        "GROUP BY t.gestion, t.mes ORDER BY t.gestion, t.mes"
    )
    fm_meses = [{"gestion": r[0], "mes": r[1], "filas": r[2], "inscritos": int(r[3])} for r in cur.fetchall()]
    cur.execute("SELECT count(*) FROM public.fact_marketing WHERE inscritos IS NOT NULL AND inscritos > 0")
    fm_pos = cur.fetchone()[0]

    mat = {
        "base_datos": "f3r_base",
        "fact_marketing_total_filas": fm_row[0],
        "meses_distintos_con_filas": fm_row[1],
        "filas_con_inscritos_mayor_0": fm_pos,
        "detalle_por_mes": fm_meses,
        "diagnostico": (
            f"En f3r_base fact_marketing tiene {fm_row[0]} filas distribuidas en {fm_row[1]} meses distintos "
            f"(minimo requerido por Holt-Winters: >=24 observaciones mensuales). Por eso ALUMNOS_GLOBAL reporta n_obs=0/sin_datos en f3r_base. "
            "Por Decision 1 (base mixta declarada), la Seccion E (HW de matricula) se calcula sobre snapshot_dw_20261110_1201 en R3-6 (n_obs=43)."
        ),
    }
    (ROOT / "docs/mediciones/f3r_matricula_lote.json").write_text(
        json.dumps(mat, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    conn.close()
    print(
        f"[OK] R3-1 tablas={len(base_tables)} vistas={len(views)} cache_beto_entidades={has_cache_beto_entidades} | "
        f"R3-2 fin={total_dw} kpi15={cuadre['kpi_15_formula_mora_mas_previsionable_pct']}% | "
        f"R3-4 fm_filas={fm_row[0]} meses={fm_row[1]}"
    )


if __name__ == "__main__":
    main()
