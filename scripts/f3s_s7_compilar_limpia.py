"""S-7 (F3S), repetición limpia de B-7 por decisión de Lean: 1 corrida con caché vacía + 1 con caché llena + Locust sobre tmpfs.
Solo lee lo medido en output/f3s/s7/ y docs/mediciones/. No toca f3s_base.json (la base no se volvió a medir).
Salidas: docs/mediciones/f3s_b7_corridas.json, f3s_klm.json, f3s_cambios_vs_f3r.json (f3s_locust.json lo escribe f3s_locust.py).
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.agregar_flujo_repetido as afr  # noqa: E402
from scripts.f3s_s7_compilar import J, MED, S7, corrida, huella_sha, ms  # noqa: E402

HUELLA_REF = "c8e10263c38a3c1da0301888ac595e56141f810a4efdc23498e6ffd6773b0153"


def estado(nombre):
    e = J(S7 / f"estado_{nombre}.json")
    return {k: e[k] for k in ("fecha", "reposo_s", "cpu_host_reposo_media_pct", "cpu_host_reposo_max_pct", "nucleos_logicos",
                              "pesados_ajenos", "otros_procesos_con_cpu_ge_3pct", "discord_presente", "contenedores",
                              "plan_energia", "plan_energia_cambiado", "en_corriente_ac", "apto", "criterio_apto")} | {
        "top5_procesos_cpu": e["top_procesos_cpu"][:5], "archivo": f"output/f3s/s7/estado_{nombre}.json"}


def huella_check(e, ref_h):
    h = J(S7 / f"{e}.huella_v2.json")
    sha = huella_sha(h)
    h2 = copy.deepcopy(h)
    h2["tablas"]["schema_migrations"] = ref_h["tablas"]["schema_migrations"]
    difs = [t for t in sorted(set(h["tablas"]) | set(ref_h["tablas"])) if h["tablas"].get(t) != ref_h["tablas"].get(t)]
    return {"huella_v2_sha256": sha, "coincide_c8e10263": sha == HUELLA_REF, "tablas_distintas_de_f3s_base": difs,
            "bandeja_igual": h["bandeja"] == ref_h["bandeja"], "kpis_todos_igual": h["kpis_todos"] == ref_h["kpis_todos"],
            "huella_v2_sha256_reponiendo_schema_migrations_de_f3s_base": huella_sha(h2),
            "equivalente_salvo_applied_at": huella_sha(h2) == HUELLA_REF}


def klm_para(ev, w):
    afr.W_DESHACER = w
    t, dsg = afr.klm(ev, con_espera=True)
    return {"W_s": w, "klm_s": t, "desglose_s": dsg}


def veredicto(s):
    return "< 15 min" if s < 900 else ("< 20 min (aceptable)" if s < 1200 else ">= 20 min")


def main():
    ref_h = J(S7 / "base_r1.huella_v2.json")
    vac, lle = corrida("b7_limpia_vacia_r1"), corrida("b7_limpia_llena_r1")
    for x, e in ((vac, "b7_limpia_vacia_r1"), (lle, "b7_limpia_llena_r1")):
        x["huella"] = huella_check(e, ref_h)
    vac["estado_maquina_antes"], vac["estado_maquina_despues"] = estado("antes_b7_limpia_vacia"), estado("despues_b7_limpia_vacia")
    lle["estado_maquina_antes"], lle["estado_maquina_despues"] = estado("antes_b7_limpia_llena"), estado("despues_b7_limpia_llena")
    contaminadas = [corrida(f"b7_vacia_r{i}") for i in (1, 2, 3)]

    loc = J(MED / "f3s_locust.json")
    pe = loc["por_endpoint"]
    loc["parametros"]["base_datos"] = "b7_limpia_llena (tmpfs beto_pg_s7, resultado de la corrida limpia con caché llena; nunca la DW viva)"
    loc["estado_maquina"] = {"antes": estado("antes_locust"), "despues": estado("despues_locust"),
                             "nota": "después: MsMpEng (Defender) ~6,9 % al terminar; antes de empezar apto (reposo 4,6 %)"}
    loc["csv"] = ["docs/mediciones/f3s_locust_stats.csv", "docs/mediciones/f3s_locust_stats_history.csv",
                  "docs/mediciones/f3s_locust_failures.csv", "docs/mediciones/f3s_locust_exceptions.csv"]
    (MED / "f3s_locust.json").write_text(json.dumps(loc, indent=2, ensure_ascii=False), encoding="utf-8")
    p95_g = pe.get("GET /api/v1/dataops/review-tray/grupos", {}).get("p95_ms")
    p95_a = pe.get("POST /api/v1/dataops/review-tray/approve-group", {}).get("p95_ms")
    w_med = round(max(p95_g, p95_a) / 1000.0, 4)
    h = J(S7 / "b7_limpia_vacia_r1.huella_v2.json")
    ev = [{"accion": a, "casos": n} for _, a, n in h["bandeja"]["firma"]]
    k = {"W_medido": klm_para(ev, w_med), "W_0": klm_para(ev, 0.0), "W_10": klm_para(ev, 10.0)}
    mv, ml = vac["tiempo_maquina_s"], lle["tiempo_maquina_s"]
    tot = {}
    for nom, kk in k.items():
        tot[f"vacia_mas_klm_{nom}_s"] = round(mv + kk["klm_s"], 2)
        tot[f"llena_mas_klm_{nom}_s"] = round(ml + kk["klm_s"], 2)
    tot_min = {kk.replace("_s", "_min") if kk.endswith("_s") else kk: round(v / 60, 2) for kk, v in tot.items()}
    rnf = {"n_corridas": 1, "dispersion": "no disponible: 1 corrida por condición (decisión de Lean: repetir limpio y solo una)",
           "maquina_cache_vacia_s": mv, "maquina_cache_vacia_min": round(mv / 60, 2),
           "maquina_cache_llena_s": ml, "maquina_cache_llena_min": round(ml / 60, 2),
           "vacia_mas_klm_W_medido_s": tot["vacia_mas_klm_W_medido_s"], "vacia_mas_klm_W_medido_min": tot_min["vacia_mas_klm_W_medido_min"],
           "veredicto_maquina_vacia": veredicto(mv), "veredicto_vacia_mas_klm_W_medido": veredicto(tot["vacia_mas_klm_W_medido_s"]),
           "veredicto_vacia_mas_klm_W_10": veredicto(tot["vacia_mas_klm_W_10_s"]),
           "umbral": "RNF-03 < 15 min (900 s); aceptable < 20 min (1.200 s)"}

    nota_contaminadas = {
        "estado": "DESCARTADA como cifra final; se conserva como evidencia",
        "motivo": "un juego (VALORANT, ~4,5 de 24 núcleos) corrió durante las 3 corridas y hubo actividad ajena durante la base (decisión de Lean: repetir limpio y solo una)",
        "tiempo_maquina_s": [x["tiempo_maquina_s"] for x in contaminadas],
        "resumen_tiempo_maquina_s": ms([x["tiempo_maquina_s"] for x in contaminadas]),
        "cpu_ajena_a_docker_avg_pct": [x["cpu_ajena_a_docker_avg_pct"] for x in contaminadas],
        "huellas": [x["huella_v2_sha256"] for x in contaminadas],
        "detalle": contaminadas, "archivos": "output/f3s/s7/b7_vacia_r{1,2,3}.*"}

    b7 = {
        "etiqueta": "F3S, S-7 (B-7), repetición limpia", "protocolo": "docs/mediciones/f2r_g6_protocolo_b7.md",
        "tmpfs": "beto_pg_s7:55632 (recreada para esta repetición: aislada_tmpfs.sh up + vacio)",
        "lote_sha256": J(S7 / "integridad_limpia_antes.json")["lote_sha256_manifiesto"],
        "modelo_beto_sha256": J(S7 / "integridad_limpia_antes.json")["modelo_beto_sha256"],
        "integridad": {"antes": J(S7 / "integridad_limpia_antes.json"), "despues": J(S7 / "integridad_limpia_despues.json")},
        "orden": "estado de máquina (40 s) -> corrida caché vacía (clon dw_vacio + 016, cache_indice_beto vacía, reposo 30 s) -> "
                 "estado (20 s) -> estado (40 s) -> corrida caché llena (misma preparación + output/f3s/s7/cache_f3s_base.sql, reposo 30 s) -> estado (20 s)",
        "monitoreo_cpu_ajena": "mismo método que la serie anterior: psutil host + docker stats cada 5 s; ajena = host - suma(CPU contenedores)/24",
        "corridas": {"vacia": [vac], "llena": [lle]},
        "intentos_fallidos_infraestructura": [{
            "etiqueta": "b7_limpia_vacia_r1 (intento 1)", "duracion_pared_s": 3.56,
            "causa": "faltaban los originales en /tmp/flujo_s7/uploads/data dentro de giragroup_api (la tmpfs y la carpeta se recrearon); upload-batch 422 'files Field required'. Sin medición. Se copiaron output/backups/f0_lote/originales (sha256 = manifiesto) y se repitió",
            "archivos": "output/f3s/s7/fallidas/"}],
        "desviaciones": [
            "plan de energía 'Equilibrado' (el protocolo pide Alto rendimiento); no se cambia por ser ajuste del sistema; equipo en AC",
            "huella v2: la sha256 no es c8e10263…0153 solo porque schema_migrations.applied_at de 014 es la hora de recreación de la tmpfs (ruido de entorno ya documentado en f3s_base.json); reponiendo esa fila de f3s_base da exactamente c8e10263…0153; las demás tablas, bandeja y kpis_todos son idénticos",
            "1 corrida por condición: no hay media ni desviación estándar (el protocolo pide 3)"],
        "serie_3_corridas_contaminadas": nota_contaminadas,
        "rnf03": rnf | {"totales_s": tot, "totales_min": tot_min, "klm": "docs/mediciones/f3s_klm.json"},
    }
    (MED / "f3s_b7_corridas.json").write_text(json.dumps(b7, indent=1, ensure_ascii=False), encoding="utf-8")

    (MED / "f3s_klm.json").write_text(json.dumps({
        "etiqueta": "F3S, S-7 (KLM), repetición limpia", "fuente_formula": "scripts/agregar_flujo_repetido.py::klm",
        "bandeja": {kk: v for kk, v in h["bandeja"].items() if kk != "firma"},
        "eventos": "un evento por grupo de la firma de la huella de b7_limpia_vacia_r1 (igual a f3s_base)",
        "fuente_w": "max(p95 GET /api/v1/dataops/review-tray/grupos, p95 POST /api/v1/dataops/review-tray/approve-group) de f3s_locust.json (mismo criterio que f3r_klm_w_medido.json)",
        "p95_grupos_ms": p95_g, "p95_approve_group_ms": p95_a, "W_medido_s": w_med,
        "klm": {"W_medido": k["W_medido"], "sensibilidad_W_0": k["W_0"], "sensibilidad_W_10": k["W_10"]},
        "maquina_s": {"vacia": mv, "llena": ml, "fuente": "f3s_b7_corridas.json (1 corrida por condición)"},
        "totales_s": tot, "totales_min": tot_min, "rnf03": rnf,
        "anterior_descartado": "la versión previa de este archivo usaba la mediana de 3 corridas contaminadas (1.203,28 s) y no tenía W medido"},
        indent=1, ensure_ascii=False), encoding="utf-8")

    # cambios vs F3R: se conserva la lista de diferencias de datos ya calculada y se reemplazan las de tiempo
    prev = J(MED / "f3s_cambios_vs_f3r.json")
    tiempo = ("B-7", "KLM", "vacía + KLM", "llena + KLM")
    cambios = [x for x in prev["cambios"] if not x["cifra"].startswith(tiempo)]
    f3r = J(MED / "f3r_klm_w_medido.json")
    def c(campo, ant, nue, f_nue):
        cambios.append({"cifra": campo, "anterior": ant, "nueva": nue, "fuente_anterior": "f3r_klm_w_medido.json", "fuente_nueva": f_nue})
    c("B-7 máquina caché vacía s (F3R media / F3S 1 corrida limpia)", f3r["rnf03_totales_s"]["maquina_cache_vacia_s"], mv, "f3s_b7_corridas.json")
    c("B-7 máquina caché llena s (F3R media / F3S 1 corrida limpia)", f3r["rnf03_totales_s"]["maquina_cache_llena_s"], ml, "f3s_b7_corridas.json")
    c("W medido s", f3r["W_medido_s"], w_med, "f3s_klm.json")
    for nom, kf in (("W_medido", "W_medido"), ("W_0", "sensibilidad_W_0"), ("W_10", "sensibilidad_W_10")):
        c(f"KLM {nom} s", f3r["klm"][kf]["klm_s"], k[nom]["klm_s"], "f3s_klm.json")
        for m in ("vacia", "llena"):
            c(f"{'vacía' if m == 'vacia' else 'llena'} + KLM {nom} s", f3r["rnf03_totales_s"][f"{m}_mas_klm_{nom}_s"], tot[f"{m}_mas_klm_{nom}_s"], "f3s_klm.json")
    f3r_loc = J(MED / "f3r_locust.json") if (MED / "f3r_locust.json").exists() else None
    if f3r_loc:
        for ep in ("GET /api/v1/dataops/review-tray/grupos", "POST /api/v1/dataops/review-tray/approve-group"):
            c(f"Locust p95 {ep} ms", f3r_loc["por_endpoint"].get(ep, {}).get("p95_ms"), pe.get(ep, {}).get("p95_ms"), "f3s_locust.json")
        c("Locust agregado p95 ms", (f3r_loc.get("agregado") or {}).get("p95_ms"), (loc.get("agregado") or {}).get("p95_ms"), "f3s_locust.json")
        c("Locust agregado fallos", (f3r_loc.get("agregado") or {}).get("failures"), (loc.get("agregado") or {}).get("failures"), "f3s_locust.json")
    for x in cambios:
        if x.get("fuente_anterior") == "f3r_klm_w_medido.json" and x["cifra"].startswith("Locust"):
            x["fuente_anterior"] = "f3r_locust.json"
    prev.update({"cambios": cambios, "no_medido_en_S7": [], "motivo_no_medido": None,
                 "tiempos": "repetición limpia de S-7 (1 corrida por condición); la serie de 3 corridas contaminadas queda descartada como cifra final (evidencia en f3s_b7_corridas.json)"})
    prev.pop("motivo_no_medido", None)
    (MED / "f3s_cambios_vs_f3r.json").write_text(json.dumps(prev, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"vacia": mv, "llena": ml, "W": w_med, "klm": {n: v["klm_s"] for n, v in k.items()}, "tot": tot, "rnf": rnf}, ensure_ascii=False))


if __name__ == "__main__":
    main()
