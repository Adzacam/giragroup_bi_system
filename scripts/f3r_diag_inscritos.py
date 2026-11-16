"""Diagnostico solo lectura de TBL_INSCRITOS.xlsx y fact_marketing en f3r_base."""
import json
from pathlib import Path
import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
DSN = "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/f3r_base"


def main():
    conn = psycopg2.connect(DSN, options="-c default_transaction_read_only=on")
    cur = conn.cursor()

    # 1. Documentos en dim_origen_documental
    cur.execute(
        "SELECT id_documento, nombre_archivo, tipo_documento, tipo_fuente, periodo, fecha_procesamiento::text "
        "FROM public.dim_origen_documental ORDER BY id_documento"
    )
    docs = [
        {
            "id_documento": r[0],
            "nombre_archivo": r[1],
            "tipo_documento": r[2],
            "tipo_fuente": r[3],
            "periodo": r[4],
            "fecha_procesamiento": r[5],
        }
        for r in cur.fetchall()
    ]
    docs_inscritos = [d for d in docs if "INSCRITOS" in (d["nombre_archivo"] or "").upper()]
    ids_inscritos = [d["id_documento"] for d in docs_inscritos]

    # 2. carga_fila_origen por documento y tabla
    cur.execute(
        "SELECT c.id_documento, d.nombre_archivo, c.tabla, count(*) "
        "FROM public.carga_fila_origen c "
        "LEFT JOIN public.dim_origen_documental d ON d.id_documento = c.id_documento "
        "GROUP BY c.id_documento, d.nombre_archivo, c.tabla "
        "ORDER BY count(*) DESC"
    )
    carga_por_doc = [
        {"id_documento": r[0], "nombre_archivo": r[1], "tabla": r[2], "filas": r[3]}
        for r in cur.fetchall()
    ]

    # 3. fact_marketing: conteo por mes y muestra de modulos/programas
    cur.execute(
        "SELECT t.gestion, t.mes, t.fecha::text, count(*), coalesce(sum(fm.leads),0), "
        "coalesce(sum(fm.reservas),0), coalesce(sum(fm.inscritos),0) "
        "FROM public.fact_marketing fm "
        "JOIN public.dim_tiempo t ON fm.id_tiempo = t.id_tiempo "
        "GROUP BY t.gestion, t.mes, t.fecha "
        "ORDER BY t.gestion, t.mes, t.fecha"
    )
    fm_por_fecha = [
        {
            "gestion": r[0],
            "mes": r[1],
            "fecha": r[2],
            "filas": r[3],
            "leads": int(r[4]),
            "reservas": int(r[5]),
            "inscritos": int(r[6]),
        }
        for r in cur.fetchall()
    ]

    cur.execute(
        "SELECT fm.id_hecho_mkt, m.nombre_modulo, t.fecha::text, fm.leads, fm.reservas, fm.inscritos, fm.costo_programa "
        "FROM public.fact_marketing fm "
        "LEFT JOIN public.dim_modulo m ON fm.id_modulo = m.id_modulo "
        "LEFT JOIN public.dim_tiempo t ON fm.id_tiempo = t.id_tiempo "
        "ORDER BY fm.id_hecho_mkt LIMIT 5"
    )
    fm_muestra = [
        {
            "id_hecho_mkt": r[0],
            "nombre_modulo": r[1],
            "fecha": r[2],
            "leads": r[3],
            "reservas": r[4],
            "inscritos": r[5],
            "costo_programa": float(r[6]) if r[6] is not None else None,
        }
        for r in cur.fetchall()
    ]

    # 4. stg_entidad_no_resuelta para TBL_INSCRITOS
    if ids_inscritos:
        cur.execute(
            "SELECT id_documento, tipo_entidad, motivo, estado_resolucion, resuelto, count(*) "
            "FROM public.stg_entidad_no_resuelta "
            "WHERE id_documento = ANY(%s) "
            "GROUP BY id_documento, tipo_entidad, motivo, estado_resolucion, resuelto "
            "ORDER BY count(*) DESC",
            (ids_inscritos,),
        )
        stg_inscritos = [
            {
                "id_documento": r[0],
                "tipo_entidad": r[1],
                "motivo": r[2],
                "estado_resolucion": r[3],
                "resuelto": r[4],
                "filas": r[5],
            }
            for r in cur.fetchall()
        ]
        cur.execute(
            "SELECT id_staging, id_documento, tipo_entidad, texto_original, motivo, payload_json "
            "FROM public.stg_entidad_no_resuelta "
            "WHERE id_documento = ANY(%s) "
            "ORDER BY id_staging LIMIT 5",
            (ids_inscritos,),
        )
        stg_muestra = [
            {
                "id_staging": r[0],
                "id_documento": r[1],
                "tipo_entidad": r[2],
                "texto_original": r[3],
                "motivo": r[4],
                "payload_json": r[5],
            }
            for r in cur.fetchall()
        ]
    else:
        stg_inscritos = []
        stg_muestra = []

    # 5. log_pipeline_ingesta y log_inconsistencias para TBL_INSCRITOS
    if ids_inscritos:
        cur.execute(
            "SELECT etapa, nivel, modulo, mensaje, tiempo_ms, metadata "
            "FROM public.log_pipeline_ingesta "
            "WHERE id_documento = ANY(%s) ORDER BY id",
            (ids_inscritos,),
        )
        logs_ingesta = [
            {"etapa": r[0], "nivel": r[1], "modulo": r[2], "mensaje": r[3], "tiempo_ms": r[4], "metadata": r[5]}
            for r in cur.fetchall()
        ]
        cur.execute(
            "SELECT regla_origen, tipo_regla, count(*) "
            "FROM public.log_inconsistencias WHERE id_documento = ANY(%s) "
            "GROUP BY regla_origen, tipo_regla ORDER BY count(*) DESC",
            (ids_inscritos,),
        )
        logs_inc = [{"regla_origen": r[0], "tipo_regla": r[1], "filas": r[2]} for r in cur.fetchall()]
    else:
        logs_ingesta = []
        logs_inc = []

    # 6. Primeras 5 filas de TBL_INSCRITOS.xlsx (MARCA TEMPORAL)
    df_ins = pd.read_excel(ROOT / "uploads/data/TBL_INSCRITOS.xlsx", sheet_name="TBL_INSCRITOS")
    cols_mt = [c for c in df_ins.columns if "MARCA" in str(c).upper() or "FECHA" in str(c).upper()]
    muestra_excel = []
    for idx, row in df_ins.head(5).iterrows():
        muestra_excel.append(
            {
                "fila_excel": int(idx) + 2,
                "marca_temporal_original": str(row.get(cols_mt[0])) if cols_mt else None,
                "columnas_fecha_encontradas": cols_mt,
                "programa_o_pos": str(row.get("PROGRAMA", row.get("POSGRADO", row.iloc[1] if len(row) > 1 else ""))),
            }
        )

    out = {
        "base_datos": "f3r_base",
        "docs_inscritos": docs_inscritos,
        "todos_documentos": docs,
        "carga_fila_origen_por_documento": carga_por_doc,
        "fact_marketing_por_fecha": fm_por_fecha,
        "fact_marketing_muestra_5": fm_muestra,
        "stg_entidad_no_resuelta_tbl_inscritos": stg_inscritos,
        "stg_tbl_inscritos_muestra_5": stg_muestra,
        "log_pipeline_ingesta_tbl_inscritos": logs_ingesta,
        "log_inconsistencias_tbl_inscritos": logs_inc,
        "tbl_inscritos_excel_total_filas": len(df_ins),
        "tbl_inscritos_excel_muestra_5": muestra_excel,
    }
    (ROOT / "docs/mediciones/f3r_diag_inscritos.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    conn.close()
    print(
        f"[OK] docs_inscritos={len(docs_inscritos)} carga_por_doc={len(carga_por_doc)} "
        f"stg_inscritos={sum(x['filas'] for x in stg_inscritos)} fm_fechas={len(fm_por_fecha)}"
    )


if __name__ == "__main__":
    main()
