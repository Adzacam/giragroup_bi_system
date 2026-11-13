"""Huella del resultado de una consolidación, para comparar dos versiones del código sobre la misma entrada.

Por tabla de hechos, dimensiones y staging: conteo y md5 de las filas ordenadas (sin la clave sustituta ni las marcas de
tiempo, que dependen del momento de la carga). Además la bandeja (casos, grupos, grupos manuales) y los KPI del CMI
que dependen de la consolidación (KPI-10 confianza, KPI-11 automatización, KPI-18).

Uso (en giragroup_api, DATABASE_URL = copia aislada ya consolidada): python scripts/huella_dw.py <salida.json> [gestion]
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend"), str(ROOT / "scripts")]

TABLAS = {
    "fact_rendimiento_academico": ["id_hecho_aca", "created_at"],
    "fact_situacion_financiera": ["id_hecho_fin", "fecha_registro"],
    "fact_evaluacion_docente": ["id_hecho_eval"],
    "fact_marketing": ["id_hecho_mkt"],
    "fact_rentabilidad": ["id_hecho_rent"],
    "fact_techo_convenio": ["id_hecho_techo", "actualizado_en"],
    "fact_costo_programa": ["id_hecho_costo", "actualizado_en"],
    "stg_entidad_no_resuelta": ["id_staging", "created_at", "resuelto_en", "lock_expira", "payload_json"],
    "dim_estudiante": [],
    "dim_modulo": [],
    "dim_docente": [],
    "dim_tiempo": [],
    "carga_fila_origen": ["creado_en"],
    "log_inconsistencias": ["id_inconsistencia", "detectado_en", "resuelto_en"],
}
KPIS = ("KPI-10", "KPI-11", "KPI-18")


def huella_tabla(db, tabla, excluir):
    from sqlalchemy import text
    cols = [c[0] for c in db.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"),
        {"t": tabla}) if c[0] not in excluir]
    if not cols:
        return {"filas": None, "md5": None}
    lista = ", ".join(f'"{c}"' for c in cols)
    filas = db.execute(text(f"SELECT {lista} FROM public.{tabla} ORDER BY {lista}")).fetchall()
    h = hashlib.md5()
    for f in filas:
        h.update(("|".join("" if v is None else str(v) for v in f) + "\n").encode("utf-8"))
    return {"filas": len(filas), "md5": h.hexdigest(), "columnas": cols}


def main(salida, gestion=None):
    import simular_revision as rev
    from core.database import SessionLocal
    out = {"tablas": {}}
    with SessionLocal() as db:
        for t, ex in TABLAS.items():
            try:
                out["tablas"][t] = huella_tabla(db, t, ex)
            except Exception as e:  # tabla ausente en esta base
                db.rollback()
                out["tablas"][t] = {"error": str(e)[:120]}
    cli = rev.cliente()
    primera, grupos = rev._todos_los_grupos(cli, {})
    out["bandeja"] = {"casos": primera["total_casos"], "grupos": primera["total_grupos"],
                      "manuales": sum(1 for g in grupos if (g.get("accion_grupo") or "MANUAL") == "MANUAL"),
                      "casos_manuales": sum(g["n"] for g in grupos if (g.get("accion_grupo") or "MANUAL") == "MANUAL"),
                      "firma": [(g["clave"][:16], g.get("accion_grupo") or "MANUAL", g["n"]) for g in grupos]}
    params = {"gestion": gestion} if gestion else {}
    sc = cli.get("/api/v1/cmi/scorecard", params=params).json()
    kpis = {k["codigo"]: k.get("valor") for p in sc.get("perspectivas", []) for k in p.get("kpis", [])}
    out["kpis"] = {c: kpis.get(c) for c in KPIS}
    out["kpis_todos"] = kpis
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"tablas": {t: (v.get("filas"), (v.get("md5") or "")[:10]) for t, v in out["tablas"].items()},
                      "bandeja": {k: v for k, v in out["bandeja"].items() if k != "firma"}, "kpis": out["kpis"]}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
