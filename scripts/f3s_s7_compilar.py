"""S-7 (F3S): compila los resúmenes de docs/mediciones/ a partir de output/f3s/s7/ (solo lectura de lo ya medido).
Salidas: f3s_base.json (+ .huella.json), f3s_b7_corridas.json, f3s_klm.json, f3s_cambios_vs_f3r.json.
"""
import hashlib
import json
import shutil
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.agregar_flujo_repetido as afr  # noqa: E402

S7 = ROOT / "output" / "f3s" / "s7"
MED = ROOT / "docs" / "mediciones"
J = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))  # noqa: E731


def ajeno(rec):
    v = [s["host_cpu_pct"] - sum(float(x["cpu"].rstrip("%")) for x in s.values() if isinstance(x, dict)) / 24 for s in rec]
    return round(st.mean(v), 1), round(max(v), 1)


def huella_sha(h):
    return hashlib.sha256(json.dumps({k: h[k] for k in ("tablas", "bandeja", "kpis_todos")}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def corrida(e):
    d, m, h, rec = J(S7 / f"{e}.json"), J(S7 / f"{e}.meta.json"), J(S7 / f"{e}.huella_v2.json"), J(S7 / f"{e}.recursos.json")
    a = ajeno(rec)
    return {"etiqueta": e, "returncode": m["returncode"], "duracion_pared_s": m["duracion_pared_s"],
            "tiempo_maquina_s": d["total"]["tiempo_maquina_s"], "etapas_s": d["etapas_s"],
            "cache_indice_beto_al_iniciar": m["cache_indice_beto_al_iniciar"],
            "host_cpu_avg_pct": m["host_cpu_avg_pct"], "host_cpu_max_pct": m["host_cpu_max_pct"],
            "cpu_ajena_a_docker_avg_pct": a[0], "cpu_ajena_a_docker_max_pct": a[1], "n_muestras": m["n_muestras"],
            "huella_v2_sha256": huella_sha(h), "bandeja": {k: v for k, v in h["bandeja"].items() if k != "firma"}, "kpis": h["kpis"]}


def ms(v):
    return {"valores": v, "mediana": round(st.median(v), 2), "media": round(st.mean(v), 2), "de": round(st.stdev(v), 2) if len(v) > 1 else 0.0,
            "min": min(v), "max": max(v)}


def main():
    ia, idp = J(S7 / "integridad_antes.json"), J(S7 / "integridad_despues.json")
    r1, r2 = J(S7 / "base_r1.huella_v2.json"), J(S7 / "base_r2.huella_v2.json")
    shutil.copy2(S7 / "base_r1.huella_v2.json", MED / "f3s_base.json.huella.json")
    f3r_h = J(MED / "f3r_base_reproducida.json.huella.json")
    f3r_b = J(MED / "f3r_base_reproducida.json")
    base = J(S7 / "base_r1.json")
    base.pop("revision_eventos", None)
    vacio = J(S7 / "dw_vacio_conteos.json")
    base.update({
        "etiqueta": "F3S, S-7", "base_datos": "f3s_base (tmpfs beto_pg_s7:55632, clon de dw_vacio + 016, cache_indice_beto vacía)",
        "commit_codigo": "7fab72a (beto-integracion); /app = backend del árbol de trabajo (solo backend/routers/powerbi.py difiere de HEAD, fuera del flujo)",
        "recorte": "output/backups/f0_lote/slices/ (ciclo mensual 2026-03), CICLO_REUSAR_SLICES=1, CICLO_SLICES=/tmp/slices_s7",
        "entorno": {"PYTHONHASHSEED": "0", "BETO_CASCADA_FINAL": "0", "BETO_ACUERDO_QC": "0", "BETO_SUGERENCIA_HITL": "0", "BETO_VENTANA": "0",
                    "CATALOG_DATABASE_URL": "catalogo_copia en la tmpfs (copia del catálogo; nunca catalog_db)"},
        "integridad": {"antes": ia, "despues": idp,
                       "snapshot_igual": ia["snapshot_sha256"] == idp["snapshot_sha256"] == "14d45f5a128f44543927911dc0ad453f681d524ac05037203f5c0c2787e3a2eb",
                       "modelo_igual": ia["modelo_beto_sha256"] == idp["modelo_beto_sha256"] and ia["modelo_beto_sha256"].startswith("9ff7fb9d"),
                       "lote_igual": ia["lote_sha256_recalculado"] == idp["lote_sha256_recalculado"] == ia["lote_sha256_manifiesto"]},
        "dw_vacio_antes_de_clonar": {"conteos": vacio,
                                     "hechos_staging_logs_carga_en_0": all(v == 0 for k, v in vacio.items() if any(
                                         s in k for s in ("fact_", "stg_", "log_", "carga_fila_origen", "staging_registros_crudos", "dim_origen_documental", "cache_indice_beto")))},
        "dos_corridas": {"r1": corrida("base_r1"), "r2": corrida("base_r2"),
                         "huella_identica": r1["tablas"] == r2["tablas"] and r1["bandeja"] == r2["bandeja"] and r1["kpis_todos"] == r2["kpis_todos"]},
        "extraccion_R3_1": {"archivo": "docs/mediciones/f3s_extraccion_f3base.json", "kpi15": "docs/mediciones/f3s_kpi15_cuadre.json"},
        "md5_distinto_con_mismo_conteo_vs_f3r": {
            "log_pipeline_ingesta": {"veredicto": "diferencia real, consecuencia de D-A4/D-A8a",
                                     "evidencia": "al sustituir en la fila DW_CONSOLIDACION de f3s_base los conteos de la consolidación de F3R (inserted_total 78750, inserted_revision 15703, inserted_academico 78025, sent_hitl 33) el md5 da 38126b84e1ec00d2ab6323c0b65ab91b = md5 de F3R; las otras 71 filas son idénticas",
                                     "script": "output/f3s/s7/md5_variantes.py"},
            "fact_costo_programa": {"veredicto": "diferencia real atribuible a D-A8a (requiere_revision), no ruido de entorno",
                                    "evidencia": "consolidacion.py:208 y :257 (commit 4b8dedc): las filas de costo por programa (registros_costo_programa) ya resueltas por regla toman banda CONSOLIDADO y no van a BETO; antes su banda salía del índice BETO y las de banda REVISION quedaban requiere_revision=True. En f3s_base las 1.371 filas tienen requiere_revision=False y motivo NULL; md5 idéntico en las 5 corridas de S-7 (determinista). No se reconstruye la fila exacta de F3R: la base f3r_base no se conservó; la hipótesis 'todas True' tampoco da el md5 de F3R (subconjunto).",
                                    "filas_requiere_revision_f3s": {"False": 1371}},
            "schema_migrations": {"veredicto": "ruido de entorno",
                                  "evidencia": "13 versiones 001..014 iguales; 014_conversion_captacion_comprobable.sql tiene applied_at = momento en que 'aislada_tmpfs.sh vacio' la aplicó en esta tmpfs (output/f3s/s7/schema_migrations_f3s_base.txt); igual en las 5 corridas de S-7 porque todas clonan el mismo dw_vacio"}},
        "protocolo_desviaciones": ["plan de energía 'Equilibrado' (no 'Alto rendimiento'); equipo en AC; no se cambia por ser configuración del sistema",
                                   "proceso ajeno de usuario activo durante todas las corridas (juego, ~4,5 núcleos de 24): CPU ajena a Docker 34-40 % de media, bajo el umbral de descarte del protocolo (45 %)",
                                   "a las 15:42 (durante base_r1) apareció docs/evidencias/matriz_confusion_ner.json y graficos_v2/grafico_3_1/3_3 (no generados por S-7): hubo otro proceso en paralelo"],
    })
    (MED / "f3s_base.json").write_text(json.dumps(base, indent=1, ensure_ascii=False, default=str), encoding="utf-8")

    vac = [corrida(f"b7_vacia_r{i}") for i in (1, 2, 3)]
    ev = [{"accion": a, "casos": n} for _, a, n in r1["bandeja"]["firma"]]
    res_klm = {}
    for nom, w in (("W_0", 0.0), ("W_10", 10.0)):
        afr.W_DESHACER = w
        t, dsg = afr.klm(ev, con_espera=True)
        res_klm[nom] = {"W_s": w, "klm_s": t, "desglose_s": dsg}
    med_v = round(st.median([x["tiempo_maquina_s"] for x in vac]), 2)
    rnf = {"maquina_cache_vacia_mediana_s": med_v, "maquina_cache_vacia_mediana_min": round(med_v / 60, 2),
           "vacia_mas_klm_W_0_s": round(med_v + res_klm["W_0"]["klm_s"], 2), "vacia_mas_klm_W_0_min": round((med_v + res_klm["W_0"]["klm_s"]) / 60, 2),
           "vacia_mas_klm_W_10_s": round(med_v + res_klm["W_10"]["klm_s"], 2), "vacia_mas_klm_W_10_min": round((med_v + res_klm["W_10"]["klm_s"]) / 60, 2),
           "cumple_15_min": False, "cumple_20_min": med_v + res_klm["W_0"]["klm_s"] <= 1200,
           "veredicto": "RNF-03 > 20 min: ya la mediana de solo máquina con caché vacía supera 1.200 s; se detiene S-7 según PLAN_F3S (Riesgos) y se avisa a Lean"}
    (MED / "f3s_b7_corridas.json").write_text(json.dumps({
        "etiqueta": "F3S, S-7 (B-7)", "protocolo": "docs/mediciones/f2r_g6_protocolo_b7.md", "tmpfs": "beto_pg_s7:55632",
        "lote_sha256": ia["lote_sha256_manifiesto"], "modelo_beto_sha256": ia["modelo_beto_sha256"],
        "corridas": {"vacia": vac, "llena": []},
        "llena_no_ejecutada": "detenida tras las 3 corridas con caché vacía: la mediana supera 20 min (condición de parada de PLAN_F3S). cache exportada en output/f3s/s7/cache_f3s_base.sql",
        "descartes": [], "criterio_descarte": "CPU ajena a Docker > 45 % de media o pico >= 95 % sostenido: ninguna corrida lo cumple (34-40 % de media)",
        "resumen": {"vacia": {"n": 3, "tiempo_maquina_s": ms([x["tiempo_maquina_s"] for x in vac]),
                              "consolidacion_s": ms([x["etapas_s"]["consolidacion_s"] for x in vac]),
                              "lectura_beto_s": ms([x["etapas_s"]["lectura_beto_s"] for x in vac]),
                              "carga_s": ms([x["etapas_s"]["carga_s"] for x in vac]),
                              "huellas_identicas_a_f3s_base": all(x["huella_v2_sha256"] == huella_sha(r1) for x in vac)},
                    "base_r1_r2_mismo_procedimiento_s": [corrida("base_r1")["tiempo_maquina_s"], corrida("base_r2")["tiempo_maquina_s"]]},
        "rnf03": rnf}, indent=1, ensure_ascii=False), encoding="utf-8")

    (MED / "f3s_klm.json").write_text(json.dumps({
        "etiqueta": "F3S, S-7 (KLM)", "fuente_formula": "scripts/agregar_flujo_repetido.py::klm (D3B, f2r_g3_klm_conciliacion.json)",
        "bandeja": {k: v for k, v in r1["bandeja"].items() if k != "firma"}, "eventos": "un evento por grupo de la firma de f3s_base.json.huella.json (mismo resultado que la construcción de R3-8: verificado 221,3 s con la bandeja de F3R)",
        "W_medido": None, "W_medido_pendiente": "no medido: Locust no se ejecutó porque S-7 se detuvo por RNF-03 > 20 min",
        "sensibilidad_W_0": res_klm["W_0"], "sensibilidad_W_10": res_klm["W_10"], "rnf03": rnf}, indent=1, ensure_ascii=False), encoding="utf-8")

    # Cambios frente a F3R (solo para el CIERRE)
    cambios = []
    def c(campo, ant, nue, f_ant, f_nue):
        if ant != nue:
            cambios.append({"cifra": campo, "anterior": ant, "nueva": nue, "fuente_anterior": f_ant, "fuente_nueva": f_nue})
    for t in sorted(set(f3r_h["tablas"]) | set(r1["tablas"])):
        a, b = f3r_h["tablas"].get(t, {}), r1["tablas"].get(t, {})
        if a.get("filas") != b.get("filas"):
            c(f"filas {t}", a.get("filas"), b.get("filas"), "f3r_base_reproducida.json.huella.json", "f3s_base.json.huella.json")
        elif a.get("md5") != b.get("md5"):
            c(f"md5 {t} (mismo conteo {b.get('filas')})", a.get("md5"), b.get("md5"), "f3r_base_reproducida.json.huella.json", "f3s_base.json.huella.json")
    for k in ("casos", "grupos", "manuales", "casos_manuales"):
        c(f"bandeja.{k}", f3r_h["bandeja"][k], r1["bandeja"][k], "f3r_base_reproducida.json.huella.json", "f3s_base.json.huella.json")
    for k in sorted(set(f3r_h["kpis_todos"]) | set(r1["kpis_todos"])):
        c(f"scorecard {k}", f3r_h["kpis_todos"].get(k), r1["kpis_todos"].get(k), "f3r_base_reproducida.json.huella.json", "f3s_base.json.huella.json")
    for k in ("inserted_dw", "inserted_academico", "inserted_revision", "sent_hitl", "descartados_ruido"):
        c(f"consolidacion.{k}", f3r_b["consolidacion"][k], base["consolidacion"][k], "f3r_base_reproducida.json", "f3s_base.json")
    c("tiempo_maquina_s f3_base (1 corrida)", f3r_b["total"]["tiempo_maquina_s"], base["total"]["tiempo_maquina_s"], "f3r_base_reproducida.json", "f3s_base.json")
    ex_a, ex_b = J(MED / "f3r_extraccion_f3base.json"), J(MED / "f3s_extraccion_f3base.json")
    sa = {f"{x['motivo']}|{x['resuelto']}": x["filas"] for x in ex_a["stg_entidad_no_resuelta"]}
    sb = {f"{x['motivo']}|{x['resuelto']}": x["filas"] for x in ex_b["stg_entidad_no_resuelta"]}
    for k in sorted(set(sa) | set(sb)):
        c(f"stg_entidad_no_resuelta {k}", sa.get(k), sb.get(k), "f3r_extraccion_f3base.json", "f3s_extraccion_f3base.json")
    la = {f"{x['regla_origen']}|{x['tipo_regla']}": x["filas"] for x in ex_a["log_inconsistencias"]}
    lb = {f"{x['regla_origen']}|{x['tipo_regla']}": x["filas"] for x in ex_b["log_inconsistencias"]}
    for k in sorted(set(la) | set(lb)):
        c(f"B-9 log_inconsistencias {k}", la.get(k), lb.get(k), "f3r_extraccion_f3base.json", "f3s_extraccion_f3base.json")
    va = {f"{x['gestion']}|{x['codigo']}": x["valor"] for x in ex_a["kpis_vw_cmi_valores"]}
    vb = {f"{x['gestion']}|{x['codigo']}": x["valor"] for x in ex_b["kpis_vw_cmi_valores"]}
    for k in sorted(set(va) | set(vb)):
        c(f"vw_cmi_valores {k}", va.get(k), vb.get(k), "f3r_extraccion_f3base.json", "f3s_extraccion_f3base.json")
    b7_ant = J(MED / "f3r_klm_w_medido.json")
    c("B-7 maquina caché vacía (F3R media / F3S mediana) s", b7_ant["rnf03_totales_s"]["maquina_cache_vacia_s"], med_v, "f3r_klm_w_medido.json", "f3s_b7_corridas.json")
    c("KLM W=0 s", b7_ant["klm"]["sensibilidad_W_0"]["klm_s"], res_klm["W_0"]["klm_s"], "f3r_klm_w_medido.json", "f3s_klm.json")
    c("KLM W=10 s", b7_ant["klm"]["sensibilidad_W_10"]["klm_s"], res_klm["W_10"]["klm_s"], "f3r_klm_w_medido.json", "f3s_klm.json")
    c("vacía + KLM W=0 s", b7_ant["rnf03_totales_s"]["vacia_mas_klm_W_0_s"], rnf["vacia_mas_klm_W_0_s"], "f3r_klm_w_medido.json", "f3s_klm.json")
    c("vacía + KLM W=10 s", b7_ant["rnf03_totales_s"]["vacia_mas_klm_W_10_s"], rnf["vacia_mas_klm_W_10_s"], "f3r_klm_w_medido.json", "f3s_klm.json")
    lote_igual = (MED / "f3r_lote_1387.json").read_bytes() == (MED / "f3s_lote_1387.json").read_bytes() == (MED / "f3s_lote_1387_r2.json").read_bytes()
    sin_cambio = {"lote_1387": "f3s_lote_1387.json y _r2 idénticos byte a byte a f3r_lote_1387.json" if lote_igual else "DIFIERE",
                  "kpi15_cuadre": "Mora 500 / Previsionable 7 / Vigente 218, fórmula 69,93 %, desajuste 0: igual a f3r_kpi15_cuadre.json",
                  "kpi_10_11_scorecard": "None en f3r y f3s (KPI-10/11 por gestión iguales en vw_cmi_valores)",
                  "inventario": "50 tablas, 9 vistas bi"}
    (MED / "f3s_cambios_vs_f3r.json").write_text(json.dumps({
        "uso": "solo para CIERRE_F3S.md; no para la SFV", "base_anterior": "f3r_base (F3R)", "base_nueva": "f3s_base (S-7)",
        "cambios": cambios, "sin_cambio": sin_cambio,
        "no_medido_en_S7": ["B-7 caché llena", "Locust y W medido", "KLM con W medido"],
        "motivo_no_medido": "S-7 detenido: RNF-03 > 20 min"}, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print("cambios", len(cambios), "rnf03", rnf)


if __name__ == "__main__":
    main()
