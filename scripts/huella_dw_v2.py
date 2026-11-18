"""Huella v2 del DW (F3-3): cubre las 50 tablas (public + bi), excluye registro_origen_id y PK/timestamps,
redondea a 4 decimales score_fuzzy/nivel_confianza/nivel_confianza_ia, y registra PYTHONHASHSEED=0 en .meta.
No modifica huella_dw.py ni las .huella.json anteriores.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend"), str(ROOT / "scripts")]

EXCLUIR_GLOBAL = ["registro_origen_id"]
EXCLUIR_POR_TABLA = {
    "public.fact_rendimiento_academico": ["id_hecho_aca", "created_at"],
    "public.fact_situacion_financiera": ["id_hecho_fin", "fecha_registro"],
    "public.fact_evaluacion_docente": ["id_hecho_eval"],
    "public.fact_marketing": ["id_hecho_mkt"],
    "public.fact_rentabilidad": ["id_hecho_rent"],
    "public.fact_techo_convenio": ["id_hecho_techo", "actualizado_en"],
    "public.fact_costo_programa": ["id_hecho_costo", "actualizado_en"],
    "public.fact_planificacion_programa": ["id_planificacion"],
    "public.stg_entidad_no_resuelta": ["id_staging", "created_at", "resuelto_en", "lock_expira", "payload_json"],
    "public.carga_fila_origen": ["creado_en"],
    "public.log_inconsistencias": ["id_inconsistencia", "detectado_en", "resuelto_en"],
    "public.log_pipeline_ingesta": ["id", "mensaje", "tiempo_ms", "created_at"],
    "public.log_auditoria_nlp": ["id_log", "created_at"],
    "public.lote": ["creado_en", "actualizado_en"],
    "public.dataops_tarea": ["creado_en", "actualizado_en", "iniciado_en", "terminado_en"],
    "public.dim_origen_documental": ["fecha_procesamiento"],
    "public.staging_registros_crudos": ["id", "created_at"],
    "public.cache_indice_beto": ["creado_en"],
    "public.notifications": ["id", "created_at"],
}
REDONDEAR_4 = {"score_fuzzy", "nivel_confianza", "nivel_confianza_ia"}
KPIS = ("KPI-10", "KPI-11", "KPI-18")


def _fmt_val(col: str, val) -> str:
    if val is None:
        return ""
    if col in REDONDEAR_4:
        try:
            return f"{round(float(val), 4):.4f}"
        except (TypeError, ValueError):
            return str(val)
    return str(val)


def huella_tabla_v2(db, schema: str, tabla: str, excluir: set) -> dict:
    from sqlalchemy import text

    cols = [
        c[0]
        for c in db.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema=:s AND table_name=:t ORDER BY ordinal_position"
            ),
            {"s": schema, "t": tabla},
        )
        if c[0] not in excluir
    ]
    if not cols:
        return {"filas": 0, "md5": hashlib.md5(b"").hexdigest(), "columnas": []}
    lista = ", ".join(f'"{c}"' for c in cols)
    filas = db.execute(text(f'SELECT {lista} FROM "{schema}"."{tabla}" ORDER BY {lista}')).fetchall()
    h = hashlib.md5()
    for f in filas:
        h.update(("|".join(_fmt_val(c, v) for c, v in zip(cols, f)) + "\n").encode("utf-8"))
    return {"filas": len(filas), "md5": h.hexdigest(), "columnas": cols}


def main(salida: str, gestion=None) -> None:
    import simular_revision as rev
    from sqlalchemy import text
    from core.database import SessionLocal

    out = {
        "version_huella": "v2",
        "meta": {
            "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
            "columnas_excluidas_global": EXCLUIR_GLOBAL,
            "columnas_excluidas_por_tabla": EXCLUIR_POR_TABLA,
            "columnas_redondeadas_4dec": sorted(REDONDEAR_4),
        },
        "tablas": {},
    }
    with SessionLocal() as db:
        tablas_bd = db.execute(
            text(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema IN ('public', 'bi') AND table_type = 'BASE TABLE' "
                "ORDER BY table_schema, table_name"
            )
        ).fetchall()
        for sch, tbl in tablas_bd:
            fq = f"{sch}.{tbl}"
            ex = set(EXCLUIR_GLOBAL) | set(EXCLUIR_POR_TABLA.get(fq, []))
            key = tbl if sch == "public" else fq
            out["tablas"][key] = huella_tabla_v2(db, sch, tbl, ex)

    cli = rev.cliente()
    primera, grupos = rev._todos_los_grupos(cli, {})
    out["bandeja"] = {
        "casos": primera["total_casos"],
        "grupos": primera["total_grupos"],
        "manuales": sum(1 for g in grupos if (g.get("accion_grupo") or "MANUAL") == "MANUAL"),
        "casos_manuales": sum(g["n"] for g in grupos if (g.get("accion_grupo") or "MANUAL") == "MANUAL"),
        "firma": [(g["clave"][:16], g.get("accion_grupo") or "MANUAL", g["n"]) for g in grupos],
    }
    params = {"gestion": gestion} if gestion else {}
    sc = cli.get("/api/v1/cmi/scorecard", params=params).json()
    kpis = {k["codigo"]: k.get("valor") for p in sc.get("perspectivas", []) for k in p.get("kpis", [])}
    out["kpis"] = {c: kpis.get(c) for c in KPIS}
    out["kpis_todos"] = kpis

    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                "n_tablas": len(out["tablas"]),
                "bandeja": {k: v for k, v in out["bandeja"].items() if k != "firma"},
                "kpis": out["kpis"],
            },
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
