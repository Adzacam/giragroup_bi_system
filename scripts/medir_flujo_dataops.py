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
         ("Egresos", "RENTABILIDAD"), ("PLANIFICACION", "PLANIFICACION"), ("ANTIGUO", "EVALUACION_DOCENTE"),
         ("Evaluaci", "EVALUACION_DOCENTE"), ("Experiencia", "ACTA"), ("Base centralizada", "ACTA")]
TABLAS = ["fact_rendimiento_academico", "fact_situacion_financiera", "fact_evaluacion_docente", "fact_marketing", "fact_rentabilidad",
          "fact_techo_convenio", "fact_costo_programa", "fact_planificacion_programa", "dim_origen_documental", "stg_entidad_no_resuelta"]


def tipo_fuente(nombre):
    return next((t for k, t in TIPOS if k.lower() in nombre.lower()), "ACTA")


def conteos():
    from core.database import SessionLocal
    with SessionLocal() as s:
        return {t: s.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in TABLAS}


def esperar_tarea(cli, id_lote, tipo):
    """Espera el mismo estado terminal que consulta la interfaz de DataOps."""
    fin = time.monotonic() + 3600
    while time.monotonic() < fin:
        respuesta = cli.get(f"{BASE}/lote/{id_lote}/tarea", params={"tipo": tipo})
        respuesta.raise_for_status()
        tarea = respuesta.json() or {}
        estado = tarea.get("estado")
        if estado == "COMPLETADA":
            return tarea
        if estado and estado != "EN_CURSO":
            raise RuntimeError(f"La tarea {tipo} terminó en {estado}")
        time.sleep(2)
    raise TimeoutError(f"Tiempo agotado esperando {tipo}")


def tiempos_bd(id_lote):
    from core.database import SessionLocal
    with SessionLocal() as db:
        tareas = db.execute(text("""
            SELECT tipo, total, iniciado_en, terminado_en,
                   EXTRACT(EPOCH FROM (terminado_en - iniciado_en)) AS duracion
            FROM dataops_tarea WHERE id_lote = :lote
            AND tipo IN ('LECTURA_BETO', 'PREPARACION_REVISION', 'CONSOLIDACION')
            AND estado = 'COMPLETADA' ORDER BY id
        """), {"lote": id_lote}).mappings().all()
    if [t["tipo"] for t in tareas] != ["LECTURA_BETO", "PREPARACION_REVISION", "CONSOLIDACION"]:
        raise RuntimeError("Secuencia inesperada de tareas completadas")
    for anterior, posterior in zip(tareas, tareas[1:]):
        if anterior["terminado_en"] > posterior["iniciado_en"]:
            raise RuntimeError("Lectura, preparación o consolidación se solaparon")
    return tareas


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

    espera_prep = 0.0
    if os.environ.get("FLUJO_ESPERAR_PREPARACION") == "1":
        t0 = time.perf_counter()
        esperar_tarea(cli, id_lote, "LECTURA_BETO")
        t["espera_lectura_beto_s"] = round(time.perf_counter() - t0, 2)
        t0 = time.perf_counter()
        esperar_tarea(cli, id_lote, "PREPARACION_REVISION")
        espera_prep = round(time.perf_counter() - t0, 2)
        t["espera_preparacion_revision_s"] = espera_prep
        t0 = time.perf_counter()
        rc = cli.post(f"{BASE}/confirm-dw-insert", json={"id_lote": id_lote, "en_segundo_plano": True})
        rc.raise_for_status()
        if rc.json().get("status") != "accepted":
            raise RuntimeError("La API no aceptó la consolidación del lote")
        tarea = esperar_tarea(cli, id_lote, "CONSOLIDACION")
        t["consolidacion_s"] = round(time.perf_counter() - t0, 2)
        lectura, preparacion, consolidacion = tiempos_bd(id_lote)
        t["lectura_beto_s"] = round(float(lectura["duracion"]), 2)
        t["preparacion_revision_s"] = round(float(preparacion["duracion"]), 2)
        t["consolidacion_tarea_s"] = round(float(consolidacion["duracion"]), 2)
        t["lineas_leidas_beto"] = int(lectura["total"])
        t["lineas_por_s_beto"] = round(int(lectura["total"]) / float(lectura["duracion"]), 2)
        # TestClient participa en la tarea de fondo antes de retornar del POST de carga.
        t["carga_s"] = round(t["carga_y_lectura_s"] + t["espera_lectura_beto_s"] + espera_prep
                              - t["lectura_beto_s"] - t["preparacion_revision_s"], 2)
        rj = tarea.get("resultado") or {}
    else:
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 1800:
            tarea = cli.get(f"{BASE}/lote/{id_lote}/tarea", params={"tipo": "LECTURA_BETO"}).json()
            if (tarea or {}).get("estado") != "EN_CURSO":
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
        rj = rc.json() if rc.headers.get("content-type", "").startswith("application/json") else {}
    import huella_dw  # huella del resultado antes de la revisión simulada (que resuelve casos de la bandeja)
    huella_dw.main(str(salida) + ".huella.json")

    # los casos de la bandeja se generan al consolidar: la revisión se simula después
    if os.environ.get("FLUJO_SIN_REVISION") == "1":  # deja la bandeja pendiente (p. ej. para revisarla en la pantalla)
        revision = {"resumen": {"tiempo_maquina_real_aprobaciones_s": 0.0, "tiempo_humano_simulado_s": 0.0, "omitida": True}, "eventos": []}
    else:
        revision = rev.simular(cli, str(id_lote))
    t["revision_maquina_s"] = revision["resumen"]["tiempo_maquina_real_aprobaciones_s"]
    t["revision_humana_simulada_s"] = revision["resumen"]["tiempo_humano_simulado_s"]

    despues = conteos()
    maquina = t["carga_y_lectura_s"] + t["espera_lectura_beto_s"] + espera_prep + t["revision_maquina_s"] + t["consolidacion_s"]
    total = {"tiempo_maquina_s": round(maquina, 2), "tiempo_humano_simulado_s": t["revision_humana_simulada_s"],
             "total_estimado_s": round(maquina + t["revision_humana_simulada_s"], 1),
             "total_estimado_min": round((maquina + t["revision_humana_simulada_s"]) / 60, 2),
             "meta_rnf03_min": 15, "referencia_tesis_min": 9}
    with __import__("core.database", fromlist=["SessionLocal"]).SessionLocal() as ses:
        fila_beto = ses.execute(text("SELECT resultado FROM dataops_tarea WHERE id_lote = :l AND tipo = 'LECTURA_BETO' ORDER BY id DESC LIMIT 1"), {"l": id_lote}).scalar()
    out = {"lectura_beto_contadores": ((fila_beto or {}) if isinstance(fila_beto, dict) else json.loads(fila_beto or "{}")).get("beto"),
           "consolidacion_beto_contadores": rj.get("beto"), "carga": resumen_carga, "etapas_s": t, "total": total, "consolidacion_http": rc.status_code,
           "consolidacion": {k: v for k, v in rj.items()
                             if not isinstance(v, (list, dict))},
           "revision": revision["resumen"], "revision_eventos": revision["eventos"], "dw_antes": antes, "dw_despues": despues}
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"etapas_s": t, "total": total, "revision": revision["resumen"]}, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
