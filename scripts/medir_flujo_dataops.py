"""Mide el flujo DataOps completo con los 10 archivos del ciclo mensual, por los endpoints reales de los pasos ① a ④:
carga en un lote (con lectura de BETO) → revisión humana simulada → consolidación al Data Warehouse.

Uso (en giragroup_api, DATABASE_URL = base aislada con el DW reiniciado; nunca giragroup_db):
    CICLO_FILAS_SIN_FECHA=0 CICLO_SLICES=/tmp/slices_flujo python scripts/medir_flujo_dataops.py <salida.json>
El tiempo de máquina es real; el de revisión humana es una simulación con supuestos explícitos (ver scripts/simular_revision.py).
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend"), str(ROOT / "scripts")]
import medir_ciclo_mensual as ciclo  # noqa: E402
import simular_revision as rev  # noqa: E402
from sqlalchemy import text  # noqa: E402

BASE = "/api/v1/dataops"
TIPOS = [("TBL_INSCRITOS", "ADMISION"), ("Cobranzas", "COBRANZA"), ("Techos", "MARKETING"), ("EJECUTADO", "RENTABILIDAD"),
         ("Egresos", "RENTABILIDAD"), ("PLANIFICACION", "RENTABILIDAD"), ("ANTIGUO", "EVALUACION_DOCENTE"),
         ("Evaluaci", "EVALUACION_DOCENTE"), ("Experiencia", "ACTA"), ("Base centralizada", "ACTA")]
TABLAS = ["fact_rendimiento_academico", "fact_situacion_financiera", "fact_evaluacion_docente", "fact_marketing", "fact_rentabilidad",
          "fact_techo_convenio", "fact_costo_programa", "dim_origen_documental", "stg_entidad_no_resuelta"]


def tipo_fuente(nombre):
    return next((t for k, t in TIPOS if k.lower() in nombre.lower()), "ACTA")


def conteos():
    from core.database import SessionLocal
    with SessionLocal() as s:
        return {t: s.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in TABLAS}


def main(salida):
    t = {}
    info = [i for i in ciclo.construir_slices() if "slice" in i]
    cli = rev.cliente()
    antes = conteos()

    files, tipos, escalas = [], [], []
    for it in info:
        nombre = Path(it["slice"]).name
        files.append(("files", (nombre, open(it["slice"], "rb").read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")))
        tf = tipo_fuente(nombre)
        tipos.append(tf)
        escalas.append("CENTESIMAL_100" if tf == "ACTA" else "")
    t0 = time.perf_counter()
    r = cli.post(f"{BASE}/upload-batch", files=files, data={"tipos_fuente": tipos, "tipos_escala": escalas, "institucion": "GiraGroup Posgrado"})
    t["carga_y_lectura_s"] = round(time.perf_counter() - t0, 2)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    id_lote = j.get("id_lote")
    resumen_carga = {"http": r.status_code, "id_lote": id_lote, "archivos_exitosos": j.get("archivos_exitosos"), "archivos_fallidos": j.get("archivos_fallidos"),
                     "registros_detectados": j.get("total_registros_detectados"), "errores": (j.get("errores") or j.get("detail"))}
    if not id_lote:
        Path(salida).write_text(json.dumps({"carga": resumen_carga}, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print("La carga no creó un lote:", json.dumps(resumen_carga, ensure_ascii=False, default=str)[:500])
        return 1

    # espera a que termine la lectura de BETO (corre en segundo plano)
    t0 = time.perf_counter()
    estado = None
    while time.perf_counter() - t0 < 1800:
        tarea = cli.get(f"{BASE}/lote/{id_lote}/tarea", params={"tipo": "LECTURA_BETO"}).json()
        estado = (tarea or {}).get("estado")
        if estado != "EN_CURSO":  # sin tarea (lectura ya guardada), COMPLETADA o FALLIDA
            break
        time.sleep(2)
    t["espera_lectura_beto_s"] = round(time.perf_counter() - t0, 2)

    with __import__("core.database", fromlist=["SessionLocal"]).SessionLocal() as ses:
        fila = ses.execute(text("SELECT total, EXTRACT(EPOCH FROM (terminado_en - iniciado_en)) FROM dataops_tarea "
                                "WHERE id_lote = :l AND tipo = 'LECTURA_BETO' ORDER BY id DESC LIMIT 1"), {"l": id_lote}).first()
    if fila and fila[1]:
        t["lectura_beto_s"] = round(float(fila[1]), 2)
        t["lineas_leidas_beto"] = int(fila[0])
        t["lineas_por_s_beto"] = round(int(fila[0]) / float(fila[1]), 2)
        t["carga_s"] = round(t["carga_y_lectura_s"] + t["espera_lectura_beto_s"] - t["lectura_beto_s"], 2)

    t0 = time.perf_counter()
    rc = cli.post(f"{BASE}/confirm-dw-insert", json={"id_lote": id_lote, "en_segundo_plano": False})
    t["consolidacion_s"] = round(time.perf_counter() - t0, 2)

    # los casos de la bandeja se generan al consolidar: la revisión se simula después
    revision = rev.simular(cli, str(id_lote))
    t["revision_maquina_s"] = revision["resumen"]["tiempo_maquina_real_aprobaciones_s"]
    t["revision_humana_simulada_s"] = revision["resumen"]["tiempo_humano_simulado_s"]

    despues = conteos()
    maquina = t["carga_y_lectura_s"] + t["espera_lectura_beto_s"] + t["revision_maquina_s"] + t["consolidacion_s"]
    total = {"tiempo_maquina_s": round(maquina, 2), "tiempo_humano_simulado_s": t["revision_humana_simulada_s"],
             "total_estimado_s": round(maquina + t["revision_humana_simulada_s"], 1),
             "total_estimado_min": round((maquina + t["revision_humana_simulada_s"]) / 60, 2),
             "meta_rnf03_min": 15, "referencia_tesis_min": 9}
    out = {"carga": resumen_carga, "etapas_s": t, "total": total, "consolidacion_http": rc.status_code,
           "consolidacion": {k: v for k, v in (rc.json() if rc.headers.get("content-type", "").startswith("application/json") else {}).items()
                             if not isinstance(v, (list, dict))},
           "revision": revision["resumen"], "revision_eventos": revision["eventos"], "dw_antes": antes, "dw_despues": despues}
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"etapas_s": t, "total": total, "revision": revision["resumen"]}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
